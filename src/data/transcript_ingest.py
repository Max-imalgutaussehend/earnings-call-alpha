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
