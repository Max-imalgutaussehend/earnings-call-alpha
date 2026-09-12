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
ANALYST_MARKERS = ("analyst", "research", "securities", "capital", "partners", "bank", "morgan", "goldman")


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
        if m and len(m.group("speaker").split()) <= 6:
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
    s = speaker.lower()
    return any(marker in s for marker in ANALYST_MARKERS)


def segment_transcript(raw_text: str, qa_start_marker: str = "question-and-answer") -> list[Segment]:
    """Split into prepared-remarks blocks and Q&A exchanges (question+answer paired)."""
    turns = parse_transcript(raw_text)
    lower_full = raw_text.lower()
    qa_start = lower_full.find(qa_start_marker)

    segments: list[Segment] = []
    in_qa = qa_start == -1  # if no marker found, fall back to speaker-based heuristic below

    pending_question = None
    running_offset = 0
    for speaker, text in turns:
        running_offset += len(speaker) + len(text)
        if qa_start != -1 and running_offset >= qa_start:
            in_qa = True

        if not in_qa:
            segments.append(Segment(kind="prepared_remarks", speaker=speaker, text=text))
            continue

        if _is_analyst(speaker):
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
