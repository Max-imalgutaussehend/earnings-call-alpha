from pathlib import Path

from src.nlp.segment import (
    _is_analyst,
    extract_analysts_from_operator_lines,
    parse_transcript,
    segment_transcript,
    whole_transcript_text,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transcript.txt"


def load_fixture() -> str:
    return FIXTURE.read_text()


def test_parse_transcript_extracts_turns():
    turns = parse_transcript(load_fixture())
    speakers = {s for s, _ in turns}
    assert any("Jane Smith" in s for s in speakers)
    assert any("Operator" in s for s in speakers)
    assert len(turns) >= 6


def test_segment_transcript_splits_prepared_remarks_and_qa():
    segments = segment_transcript(load_fixture())
    kinds = {s.kind for s in segments}
    assert "prepared_remarks" in kinds
    assert "qa_exchange" in kinds

    qa_segments = [s for s in segments if s.kind == "qa_exchange"]
    assert len(qa_segments) >= 2
    assert any("Q (" in s.text and "A:" in s.text for s in qa_segments)


def test_core_segment_keyword_isolates_cloud_discussion():
    segments = segment_transcript(load_fixture())
    cloud_segments = [s for s in segments if "cloud" in s.text.lower()]
    hardware_segments = [s for s in segments if "hardware" in s.text.lower()]
    assert cloud_segments
    assert hardware_segments
    # sanity: the two topics should be in different segments, not merged into one blob
    assert cloud_segments[0].text != hardware_segments[0].text


def test_whole_transcript_text_is_concatenated():
    text = whole_transcript_text(load_fixture())
    assert "cloud" in text.lower()
    assert "hardware" in text.lower()
    assert len(text.split()) > 50


def test_multi_executive_answer_stays_one_segment():
    """A question answered by two executives in sequence (CFO then CEO
    chiming in) must produce ONE qa_exchange segment containing both answers
    and the original question text -- not an orphaned answer-only segment
    for the second executive with no question attached.
    """
    transcript = (
        "Operator: We will now begin the question-and-answer session.\n\n"
        "Analyst (Sarah Lee, Morgan Stanley): What is driving the margin expansion this quarter?\n\n"
        "John Doe, CFO: Pricing actions across the portfolio were the primary driver.\n\n"
        "Jane Smith, CEO: I would just add that mix shift toward premium products also helped.\n\n"
        "John Doe, CFO: And to be clear, we expect this to continue next quarter.\n"
    )
    segments = segment_transcript(transcript)
    qa_segments = [s for s in segments if s.kind == "qa_exchange"]
    assert len(qa_segments) == 1
    text = qa_segments[0].text
    assert "margin expansion" in text
    assert "Pricing actions" in text
    assert "mix shift" in text
    assert "continue next quarter" in text


def test_is_analyst_does_not_match_executive_surname_inside_firm_word():
    """A sell-side firm word must not false-positive on an executive whose
    surname happens to be a substring of it -- e.g. ExxonMobil's CEO Darren
    Woods was previously misclassified as an analyst because "woods" (from
    "Keefe, Bruyette & Woods") matched his surname.
    """
    assert _is_analyst("Darren Woods") is False
    assert _is_analyst("Chris McGratty, Keefe, Bruyette, & Woods") is True


def test_extract_analysts_from_operator_lines():
    turns = [
        ("Operator", "The next question comes from Betty Jiang with Barclays."),
        ("Betty Jiang", "Thanks, good morning."),
        ("Operator", "The next question is from Neil Mehta of Goldman Sachs."),
        ("Neil Mehta", "Appreciate the color."),
    ]
    names = extract_analysts_from_operator_lines(turns)
    assert names == {"Betty Jiang", "Neil Mehta"}
