"""Build the per-call feature table: whole-transcript sentiment vs. segment dispersion."""
from __future__ import annotations

from dataclasses import dataclass

from src.nlp.finbert import score_text
from src.nlp.segment import Segment, segment_transcript, whole_transcript_text


@dataclass
class CallFeatures:
    ticker: str
    call_date: str
    whole_sentiment: float
    segment_scores: list[float]
    max_segment: float
    min_segment: float
    dispersion: float  # max - min
    core_segment_sentiment: float | None
    n_segments: int


def _is_core_segment(segment: Segment, keywords: list[str]) -> bool:
    text_lower = segment.text.lower()
    return any(kw in text_lower for kw in keywords)


def compute_call_features(
    ticker: str, call_date: str, raw_transcript: str, core_keywords: list[str]
) -> CallFeatures:
    whole_score = score_text(whole_transcript_text(raw_transcript)).score

    segments = segment_transcript(raw_transcript)
    seg_scores = [score_text(seg.text).score for seg in segments if len(seg.text.split()) >= 15]

    core_scores = [
        score_text(seg.text).score
        for seg in segments
        if len(seg.text.split()) >= 15 and _is_core_segment(seg, core_keywords)
    ]
    core_sentiment = sum(core_scores) / len(core_scores) if core_scores else None

    if seg_scores:
        max_s, min_s = max(seg_scores), min(seg_scores)
        dispersion = max_s - min_s
    else:
        max_s = min_s = dispersion = None

    return CallFeatures(
        ticker=ticker,
        call_date=call_date,
        whole_sentiment=whole_score,
        segment_scores=seg_scores,
        max_segment=max_s,
        min_segment=min_s,
        dispersion=dispersion,
        core_segment_sentiment=core_sentiment,
        n_segments=len(seg_scores),
    )
