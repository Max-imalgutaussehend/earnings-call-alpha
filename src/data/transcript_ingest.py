"""Normalize first-party transcript sources (PDF-extracted or HTML-copied)
into the `Speaker: text` plain-text format expected by src.nlp.segment.

Two known input shapes so far, both first-party (see docs/data_sources.md):

1. "streetevents-style" PDF transcripts (e.g. JPMorganChase's published
   earnings-call PDFs): pdftotext extraction yields blocks of
       Q            (or A)
       <blank>
       Speaker Name
       Speaker Title
       <blank>
       ...paragraph text spanning multiple lines...
       ........(dotted rule)........
   This function collapses each block into one `Speaker Name: text` line.

2. "inline-caps" HTML transcripts (e.g. Microsoft's investor-relations page):
   speaker turns appear as "SPEAKER NAME: \"quoted remarks\"" or
   "SPEAKER NAME, FIRM: \"...\"" directly in the page text -- this shape
   already matches the target format closely and needs only light cleanup
   (stripping the surrounding quote marks).

3. "bare-name-line" PDF transcripts (e.g. Bank of America's published
   earnings-call PDFs): pdftotext extraction yields a "Participants" roster
   near the top (presenters and analysts, one per line, "Name - Firm" or
   "Name -- Company, Title"), then the body alternates
       Speaker Name
       ...paragraph text spanning multiple lines...
       Speaker Name
       ...
   with NO delimiter between a speaker-name line and the following text --
   the only way to tell them apart is to know the roster in advance. This
   is why the roster is parsed first and used as the source of truth for
   which bare lines are speaker turns.

4. "caret-delimited" PDF transcripts (e.g. Caterpillar's published
   earnings-call PDFs): pdftotext extraction yields explicit
   "CORPORATE SPEAKERS:" / "PARTICIPANTS:" roster blocks (each entry as
   "Name\nFirm; Role"), then the body uses "Speaker Name^ text..." as an
   unambiguous inline delimiter -- no roster lookup needed to find turn
   boundaries, only to build the full "Name, Role, Firm" label.
"""
from __future__ import annotations

import re

_DOTTED_RULE = re.compile(r"^\.{10,}$")
_PAGE_NUM = re.compile(r"^\d{1,4}$")
_QA_MARKER = re.compile(r"^[QA]$")


def normalize_streetevents_pdf(raw_text: str) -> str:
    lines = [l.rstrip() for l in raw_text.splitlines()]
    # drop header/footer noise
    lines = [l for l in lines if not _DOTTED_RULE.match(l.strip())]

    out_lines: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()

        if line.upper().startswith("QUESTION AND ANSWER SECTION"):
            # preserve this as an explicit marker line so downstream
            # segmentation (src.nlp.segment, which looks for the literal
            # substring "question-and-answer") can find the MD/Q&A boundary
            # -- the speaker-turn collapsing below would otherwise drop it.
            out_lines.append("SECTION_MARKER: question-and-answer section")
            i += 1
            continue

        if _QA_MARKER.match(line):
            i += 1
            while i < n and lines[i].strip() == "":
                i += 1
            if i >= n:
                break
            speaker = lines[i].strip()
            i += 1
            # capture the title line (role, company) -- needed downstream to
            # tell analysts apart from executives (segment.py's _is_analyst
            # heuristic matches on words like "Analyst"/firm names)
            title = ""
            if i < n and lines[i].strip() and not _PAGE_NUM.match(lines[i].strip()):
                title = lines[i].strip()
                i += 1
            speaker_label = f"{speaker}, {title}" if title else speaker
            # skip blank lines
            while i < n and lines[i].strip() == "":
                i += 1
            # collect paragraph text until we hit a blank line or the next Q/A marker
            text_parts = []
            while i < n and lines[i].strip() != "" and not _QA_MARKER.match(lines[i].strip()):
                if _PAGE_NUM.match(lines[i].strip()):
                    i += 1
                    continue
                text_parts.append(lines[i].strip())
                i += 1
            text = " ".join(text_parts)
            if speaker and text:
                out_lines.append(f"{speaker_label}: {text}")
            continue

        # Operator interjections and MD-section body appear as plain
        # "Speaker\nTitle\n\n<text>" blocks too (management discussion),
        # or as "Operator: ..." single lines. Handle the single-line case:
        m = re.match(r"^(Operator):\s*(.+)$", line)
        if m:
            out_lines.append(f"{m.group(1)}: {m.group(2)}")
            i += 1
            continue

        # Fallback: "Name\nTitle, Company\n\n<paragraph...>" blocks in the
        # management-discussion section (no leading Q/A marker there).
        if line and i + 2 < n and lines[i + 1].strip() and lines[i + 2].strip() == "":
            speaker = line
            title = lines[i + 1].strip()
            j = i + 3
            text_parts = []
            while j < n and lines[j].strip() != "" and not _QA_MARKER.match(lines[j].strip()) and ":" not in lines[j][:20]:
                if _PAGE_NUM.match(lines[j].strip()):
                    j += 1
                    continue
                text_parts.append(lines[j].strip())
                j += 1
            text = " ".join(text_parts)
            # heuristic guard: only treat as a speaker block if title looks like a role line
            if text and any(k in title for k in ("Chief", "Officer", "President", "Chairman", "Analyst", "Director")):
                out_lines.append(f"{speaker}: {text}")
                i = j
                continue

        i += 1

    return "\n\n".join(out_lines)


_PRESENTER_LINE = re.compile(r"^([A-Z][A-Za-z.’' -]+?)\s*[–—-]\s*(.+)$")


def _parse_bare_name_roster(lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse the "Participants" / "Presenters" roster block at the top of a
    bare-name-line transcript. Returns {short_name: full_label} (short_name
    is how the name appears standalone in the body, e.g. "Brian Moynihan";
    full_label includes the role/firm, e.g. "Brian Moynihan, Chair and CEO,
    Bank of America") and the line index where the roster block ends.
    """
    roster: dict[str, str] = {}
    end_idx = 0
    in_roster = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in ("Presenters", "Participants"):
            in_roster = True
            end_idx = i + 1
            continue
        if not in_roster:
            continue
        if stripped == "" or stripped == "Presentation" or stripped == "Q&A":
            if roster:
                end_idx = i
                if stripped in ("Presentation", "Q&A"):
                    break
            continue
        m = _PRESENTER_LINE.match(stripped)
        if m:
            name, rest = m.group(1).strip(), m.group(2).strip()
            roster[name] = f"{name}, {rest}"
            end_idx = i + 1
        else:
            # a non-matching, non-blank line after we've already collected
            # some names means the roster block ended
            if roster:
                break
    return roster, end_idx


def normalize_bare_name_pdf(raw_text: str) -> str:
    lines = [l.rstrip() for l in raw_text.splitlines()]
    roster, body_start = _parse_bare_name_roster(lines)
    if not roster:
        raise ValueError("Could not parse a Participants/Presenters roster from this transcript.")

    out_lines: list[str] = []
    current_speaker: str | None = None
    buf: list[str] = []

    def _flush():
        if current_speaker is not None and buf:
            text = " ".join(b for b in buf if b)
            if text:
                out_lines.append(f"{roster[current_speaker]}: {text}")

    for line in lines[body_start:]:
        stripped = line.strip()
        if stripped.upper() == "Q&A".upper():
            out_lines.append("SECTION_MARKER: question-and-answer section")
            continue
        if stripped in roster:
            _flush()
            current_speaker = stripped
            buf = []
            continue
        if stripped == "Operator":
            _flush()
            current_speaker = "__operator__"
            roster.setdefault("__operator__", "Operator")
            buf = []
            continue
        if _PAGE_NUM.match(stripped):
            continue
        # page footer/header noise: "Second Quarter 2026 Earnings..." repeats
        if stripped.endswith("Earnings Announcement") or re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$", stripped):
            continue
        buf.append(stripped)

    _flush()
    return "\n\n".join(out_lines)


def _parse_caret_roster(lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse "CORPORATE SPEAKERS:" / "PARTICIPANTS:" blocks, each entry as
    "Name" then "Firm; Role" (the role line can wrap onto a second line, so
    keep consuming indented continuation lines until a new all-caps section
    header or another name-looking line appears).
    """
    roster: dict[str, str] = {}
    body_start = 0
    i = 0
    n = len(lines)
    section = None
    while i < n:
        stripped = lines[i].strip()
        if stripped.upper() in ("CORPORATE SPEAKERS:", "PARTICIPANTS:"):
            section = stripped.upper()
            i += 1
            continue
        if stripped.upper() == "PRESENTATION:":
            body_start = i + 1
            break
        if section and stripped:
            name = stripped
            i += 1
            role_parts = []
            seen_semicolon = False
            # Role-continuation words that a wrapped "Firm; Role" line can
            # end on mid-title (e.g. "...Incoming Chief" / "Financial
            # Officer") -- a bare line consisting only of these, with no
            # semicolon, is still part of the role, not the next name.
            role_continuation_words = {
                "officer", "president", "director", "chairman", "manager",
                "chief", "vice", "senior", "financial", "executive", "relations",
            }
            while i < n and lines[i].strip() and lines[i].strip().upper() not in ("CORPORATE SPEAKERS:", "PARTICIPANTS:", "PRESENTATION:"):
                candidate = lines[i].strip()
                looks_like_role_continuation = seen_semicolon and all(
                    w.lower().strip(",") in role_continuation_words for w in candidate.split()
                )
                if seen_semicolon and ";" not in candidate and not looks_like_role_continuation:
                    break
                if ";" in candidate:
                    seen_semicolon = True
                role_parts.append(candidate)
                i += 1
            roster[name] = f"{name}, {' '.join(role_parts)}" if role_parts else name
            continue
        i += 1
    return roster, body_start


def normalize_caret_delimited_pdf(raw_text: str) -> str:
    lines = [l.rstrip() for l in raw_text.splitlines()]
    roster, body_start = _parse_caret_roster(lines)
    if not roster:
        raise ValueError("Could not parse a CORPORATE SPEAKERS/PARTICIPANTS roster from this transcript.")

    # Longest-name-first so "Joseph Creed" isn't shadowed by a shorter
    # partial match when scanning for the "Name^" delimiter.
    names_by_length = sorted(roster.keys(), key=len, reverse=True)
    turn_start = re.compile(
        r"^(" + "|".join(re.escape(n) for n in names_by_length) + r"|Operator)\^\s?(.*)$"
    )

    analyst_names = {name for name, label in roster.items() if "analyst" in label.lower()}

    out_lines: list[str] = []
    current_speaker: str | None = None
    buf: list[str] = []
    qa_marker_inserted = False

    def _flush():
        if current_speaker is not None:
            text = " ".join(b for b in buf if b)
            if text:
                label = roster.get(current_speaker, current_speaker)
                out_lines.append(f"{label}: {text}")

    for line in lines[body_start:]:
        stripped = line.strip()
        m = turn_start.match(stripped)
        if m:
            _flush()
            # This transcript shape has no explicit "QUESTION AND ANSWER"
            # header (unlike normalize_streetevents_pdf's source) -- the
            # first analyst turn is the only reliable Q&A boundary signal,
            # so insert the marker segment_transcript looks for right there.
            if not qa_marker_inserted and m.group(1) in analyst_names:
                out_lines.append("SECTION_MARKER: question-and-answer section")
                qa_marker_inserted = True
            current_speaker = m.group(1)
            buf = [m.group(2)] if m.group(2) else []
            continue
        if stripped.upper().startswith("QUESTION AND ANSWER") or stripped == "Q&A":
            _flush()
            current_speaker = None
            out_lines.append("SECTION_MARKER: question-and-answer section")
            qa_marker_inserted = True
            continue
        if _PAGE_NUM.match(stripped) or not stripped:
            continue
        if current_speaker is not None:
            buf.append(stripped)

    _flush()
    return "\n\n".join(out_lines)


def normalize_inline_caps_html_text(raw_text: str) -> str:
    """Microsoft-style: 'SPEAKER NAME: \"...\"' or 'SPEAKER NAME, FIRM: \"...\"' turns."""
    pattern = re.compile(r'([A-Z][A-Z .\'-]{3,60}(?:,\s*[A-Za-z0-9 .&\'-]{2,60})?):\s*"([^"]+)"')
    matches = pattern.findall(raw_text)
    return "\n\n".join(f"{speaker.strip()}: {text.strip()}" for speaker, text in matches)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    src = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "streetevents"
    raw = src.read_text()
    normalized = normalize_streetevents_pdf(raw) if mode == "streetevents" else normalize_inline_caps_html_text(raw)
    print(normalized[:3000])
    print(f"\n\n[...{len(normalized)} chars total]")
