import pytest

from risefirst.domain.experience import parse_experience


@pytest.mark.parametrize(
    ("text", "minimum", "maximum"),
    [
        ("We need 0-2 years of experience in Python.", 0, 2),
        ("Experience: 0 to 1 yrs", 0, 1),
        ("1–3 years of relevant experience", 1, 3),
        ("Up to 2 years of experience with SQL", 0, 2),
        ("Minimum 2 years of experience required", 2, None),
        ("At least 5 years experience building APIs", 5, None),
        ("3+ years of experience in sales", 3, None),
        ("5 years of hands-on experience with Kubernetes", 5, None),
        ("0-2 years experience in Python. 4+ years of overall experience.", 4, 2),
    ],
)
def test_parses_stated_experience(text: str, minimum: float, maximum: float | None) -> None:
    result = parse_experience(text)
    assert result.min_years == minimum
    assert result.max_years == maximum


def test_ignores_numbers_outside_experience_sentences() -> None:
    result = parse_experience("Founded 10 years ago. 5 years warranty. Join our team!")
    assert result.min_years is None


def test_detects_freshers_wording() -> None:
    assert parse_experience("Freshers are welcome to apply.").freshers_mentioned
    assert parse_experience("Open to recent graduates").freshers_mentioned
    assert not parse_experience("We value fresh ideas").freshers_mentioned


def test_empty_description() -> None:
    result = parse_experience("")
    assert result.min_years is None and not result.freshers_mentioned
