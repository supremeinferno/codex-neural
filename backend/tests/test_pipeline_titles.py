import pytest

from backend.pipeline import (
    REPORT_TITLE_MAX_LENGTH,
    _fallback_report_title,
    _parse_report_output,
)


def test_parse_report_title_and_body():
    title, report = _parse_report_output(
        "prompt",
        "TITLE:  A Useful Title  \nREPORT:\n# Findings\nDetails",
    )

    assert title == "A Useful Title"
    assert report == "# Findings\nDetails"


def test_long_title_is_limited_to_eighty_characters():
    title, report = _parse_report_output(
        "prompt",
        f"TITLE: {'long title ' * 12}\nREPORT:\nBody",
    )

    assert len(title) <= REPORT_TITLE_MAX_LENGTH
    assert title.endswith("…")
    assert report == "Body"


@pytest.mark.parametrize(
    "generated_output",
    ["unstructured output", "TITLE: A title\nREPORT:\n", "TITLE:\nREPORT:\nBody"],
)
def test_invalid_writer_format_falls_back_to_prompt_title(generated_output):
    title, report = _parse_report_output("  # Prompt-derived title  \ncontext", generated_output)

    assert title == "Prompt-derived title"
    assert report == generated_output.strip()


def test_empty_topic_uses_generic_fallback_title():
    assert _fallback_report_title("\n \n") == "Research report"
