"""Split an earnings call transcript into segments.

Two segmentation modes, matching the paper's contrast:
- whole: the entire transcript as one block (baseline)
- segmented: prepared-remarks topic blocks + individual analyst Q&A exchanges

Transcripts are expected as plain text with speaker labels, e.g.:

    Operator: ...
    Tim Cook: ...
    Analyst (Jane Doe, Morgan Stanley): ...

This is intentionally simple/regex-based rather than a learned segmenter:
the sample is small and curated, so a transparent rule-based splitter is
easier to audit than a black-box one, and audit-ability is the point of
this stage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SPEAKER_LINE = re.compile(r"^(?P<speaker>[^:]{2,80}):\s*(?P<text>.*)$")
# Matched as a whole word against the speaker LABEL (name + role/company),
# e.g. "Glenn Schorr, Analyst, Evercore ISI". Deliberately narrow: a plain
# substring match on firm names (e.g. "morgan") would also match executives
# at "JPMorganChase" and misclassify them as analysts.
ANALYST_ROLE_WORD = re.compile(r"\banalyst\b", re.IGNORECASE)
# Fallback for transcripts that label analysts by firm only (e.g. Microsoft's
# "KARL KEIRSTEAD, UBS") -- matched as whole words to avoid the same
# false-positive-on-substring problem (e.g. "BofA" inside another word).
SELL_SIDE_FIRM_WORDS = re.compile(
    r"\b(ubs|jefferies|bernstein|evercore|autonomous|truist|wells fargo|"
    # "woods" dropped as a standalone word -- it matched executives literally
    # named Woods (e.g. ExxonMobil's CEO Darren Woods); "keefe"/"bruyette"
    # alone are unambiguous enough to still catch Keefe, Bruyette & Woods.
    r"seaport|rbc|keefe|bruyette|bofa|barclays|citi|citigroup|"
    r"jmp|piper|oppenheimer|wolfe|mizuho|baird|kbw|deutsche bank|"
    r"morgan stanley|goldman sachs)\b",
    re.IGNORECASE,
)


@dataclass
class Segment:
    kind: str  # "prepared_remarks" | "qa_exchange"
    speaker: str
    text: str
    is_analyst_question: bool = False


def parse_transcript(raw_text: str) -> list[tuple[str, str]]:
    """Return list of (speaker, text) turns from speaker-labeled plain text."""
    turns = []
    current_speaker, buf = None, []
    for line in raw_text.splitlines():
        m = SPEAKER_LINE.match(line.strip())
        if m and len(m.group("speaker").split()) <= 12:
            if current_speaker is not None:
                turns.append((current_speaker, " ".join(buf).strip()))
            current_speaker = m.group("speaker")
            buf = [m.group("text")]
        else:
            buf.append(line.strip())
    if current_speaker is not None:
        turns.append((current_speaker, " ".join(buf).strip()))
    return [(s, t) for s, t in turns if t]


# Operator hand-off lines reliably name the analyst and firm even when the
# analyst's own speaker label carries neither (e.g. ExxonMobil's transcripts
# label turns with a bare "First Last" and put the firm only in the
# operator's introduction) -- e.g. "The next question comes from Betty Jiang
# with Barclays." / "...from Neil Mehta of Goldman Sachs."
_OPERATOR_ANALYST_INTRO = re.compile(
    r"(?:from|is)\s+([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3})\s+(?:with|of)\s+([A-Z][A-Za-z0-9&.,' -]+?)(?:\.|,|\s+Your line)",
)


def extract_analysts_from_operator_lines(turns: list[tuple[str, str]]) -> set[str]:
    """Scan Operator turns for "next question comes from X with/of Y"
    hand-offs and return the set of analyst first+last names found. Used as
    a fallback when a transcript's own speaker labels carry no role/firm
    info (see normalize_bare_name_pdf-adjacent sources like ExxonMobil's).
    """
    names = set()
    for speaker, text in turns:
        if speaker.strip().lower() != "operator":
            continue
        for m in _OPERATOR_ANALYST_INTRO.finditer(text):
            names.add(m.group(1).strip())
    return names


def _is_analyst(speaker: str, known_analyst_names: frozenset[str] = frozenset()) -> bool:
    if speaker.strip() in known_analyst_names:
        return True
    return bool(ANALYST_ROLE_WORD.search(speaker) or SELL_SIDE_FIRM_WORDS.search(speaker))


def segment_transcript(raw_text: str, qa_start_marker: str = "question-and-answer") -> list[Segment]:
    """Split into prepared-remarks blocks and Q&A exchanges (question+answer paired)."""
    turns = parse_transcript(raw_text)
    known_analysts = frozenset(extract_analysts_from_operator_lines(turns))

    # Find the turn that itself carries the Q&A section marker (as speaker or
    # text), rather than a raw character offset into the original text --
    # offsets drift once the source has been normalized/reformatted, but a
    # marker turn survives normalization since normalize_streetevents_pdf
    # inserts a dedicated SECTION_MARKER turn (see src/data/transcript_ingest.py).
    qa_marker_turn_idx = next(
        (i for i, (speaker, text) in enumerate(turns) if qa_start_marker in f"{speaker} {text}".lower()),
        None,
    )

    segments: list[Segment] = []
    in_qa = qa_marker_turn_idx is None  # no marker found: fall back to speaker-based heuristic below

    # One segment per analyst question, gathering ALL subsequent executive
    # turns (however many executives take part) until the next analyst
    # question starts. Earlier versions paired a question with only the
    # first answering turn, so a question answered by two executives in
    # sequence (e.g. CFO then CEO) produced an orphaned answer-only segment
    # with no question text -- that's what caused the wall of near-duplicate
    # "Q (...)" bars in the segment heatmap.
    pending_question: tuple[str, str] | None = None
    pending_answers: list[tuple[str, str]] = []

    def _flush():
        if pending_question is None:
            return
        q_speaker, q_text = pending_question
        answer_text = " ".join(f"{spk}: {txt}" for spk, txt in pending_answers)
        combined = f"Q ({q_speaker}): {q_text}\nA: {answer_text}" if answer_text else f"Q ({q_speaker}): {q_text}"
        answer_speaker = pending_answers[-1][0] if pending_answers else q_speaker
        segments.append(Segment(kind="qa_exchange", speaker=answer_speaker, text=combined, is_analyst_question=True))

    for idx, (speaker, text) in enumerate(turns):
        if qa_marker_turn_idx is not None:
            if idx == qa_marker_turn_idx:
                in_qa = True
                continue  # the marker turn itself carries no content
            if idx < qa_marker_turn_idx:
                in_qa = False

        if not in_qa:
            segments.append(Segment(kind="prepared_remarks", speaker=speaker, text=text))
            continue

        # The operator only moderates ("next question comes from...") and is
        # neither an analyst asking a question nor an executive answering
        # one -- skip its turns entirely rather than let it break a pending
        # question/answer pairing.
        if speaker.strip().lower() == "operator":
            continue

        if _is_analyst(speaker, known_analysts):
            if pending_question is not None and pending_question[0] == speaker and not pending_answers:
                # A same-analyst follow-up remark before any answer arrived
                # extends the question rather than starting a new one.
                q_speaker, q_text = pending_question
                pending_question = (q_speaker, f"{q_text} {text}")
            else:
                _flush()
                pending_question = (speaker, text)
                pending_answers = []
        else:
            if pending_question is not None:
                pending_answers.append((speaker, text))
            else:
                segments.append(Segment(kind="qa_exchange", speaker=speaker, text=text))

    _flush()
    return segments


def whole_transcript_text(raw_text: str) -> str:
    return " ".join(t for _, t in parse_transcript(raw_text))
