"""FinBERT-based sentiment scoring, per segment or whole transcript.

Uses ProsusAI/finbert (finance-domain BERT fine-tuned for positive/negative/
neutral sentiment classification on financial text). Chosen over a general-
purpose LLM as the *primary* scorer for three reasons, documented here rather
than assumed:

1. Determinism: same input -> same score, every run. Needed for a reproducible
   backtest; an LLM's output can vary run to run unless heavily constrained.
2. Cost/scale: scoring ~30 calls x ~40 segments each is trivial for a local
   ~440M-parameter model, whereas hitting an LLM API for every segment adds
   cost and a rate-limit dependency for a project whose core claim should not
   hinge on API availability.
3. Domain fit: FinBERT is trained on financial-domain text, avoiding the
   generic-sentiment-classifier failure mode where "beat guidance but issued
   cautious outlook" gets misread as strongly positive or negative.

A general LLM-based scorer is used only as a secondary robustness check
(see nlp/llm_check.py) — precisely the baseline-vs-alternative comparison
that a purely-LLM pipeline would lack.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "ProsusAI/finbert"
MAX_TOKENS = 512


@dataclass
class SentimentScore:
    label: str  # "positive" | "negative" | "neutral"
    score: float  # signed scalar in [-1, 1]: P(positive) - P(negative)
    p_positive: float
    p_negative: float
    p_neutral: float


@lru_cache(maxsize=1)
def _load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()
    return tokenizer, model


def score_text(text: str) -> SentimentScore:
    tokenizer, model = _load_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_TOKENS)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0].tolist()
    # ProsusAI/finbert label order: 0=positive, 1=negative, 2=neutral
    p_pos, p_neg, p_neu = probs
    label = ["positive", "negative", "neutral"][probs.index(max(probs))]
    return SentimentScore(label=label, score=p_pos - p_neg, p_positive=p_pos, p_negative=p_neg, p_neutral=p_neu)


def score_texts(texts: list[str]) -> list[SentimentScore]:
    return [score_text(t) for t in texts]


if __name__ == "__main__":
    examples = [
        "Revenue grew 12% year over year, well ahead of guidance, and we are raising our full-year outlook.",
        "We are seeing significant softness in demand and expect margins to remain under pressure next quarter.",
        "Results were in line with expectations for the quarter.",
    ]
    for ex in examples:
        s = score_text(ex)
        print(f"{s.label:>8} ({s.score:+.3f})  {ex[:60]}...")
