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
    r"seaport|rbc|keefe|bruyette|woods|bofa|barclays|citi|citigroup|"
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


def _is_analyst(speaker: str) -> bool:
    return bool(ANALYST_ROLE_WORD.search(speaker) or SELL_SIDE_FIRM_WORDS.search(speaker))


def segment_transcript(raw_text: str, qa_start_marker: str = "question-and-answer") -> list[Segment]:
    """Split into prepared-remarks blocks and Q&A exchanges (question+answer paired)."""
    turns = parse_transcript(raw_text)

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

    pending_question = None
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

        if _is_analyst(speaker):
            # A follow-up question from the same analyst (or a second remark
            # before an executive replies) should extend, not silently
            # discard, the pending question.
            if pending_question is not None and pending_question[0] == speaker:
                q_speaker, q_text = pending_question
                pending_question = (q_speaker, f"{q_text} {text}")
            else:
                pending_question = (speaker, text)
        else:
            if pending_question is not None:
                q_speaker, q_text = pending_question
                combined = f"Q ({q_speaker}): {q_text}\nA ({speaker}): {text}"
                segments.append(Segment(kind="qa_exchange", speaker=speaker, text=combined, is_analyst_question=True))
                pending_question = None
            else:
                segments.append(Segment(kind="qa_exchange", speaker=speaker, text=text))

    return segments


def whole_transcript_text(raw_text: str) -> str:
    return " ".join(t for _, t in parse_transcript(raw_text))
