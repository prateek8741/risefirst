import pytest

from risefirst.domain.eligibility import combine_with_ai, decide_by_rules
from risefirst.domain.enums import Category, ClassifiedBy, Eligibility, EmploymentType, WorkMode
from risefirst.domain.models import EligibilityDecision, Enrichment, ExperienceRange

E, R, X = Eligibility.ELIGIBLE, Eligibility.REVIEW_REQUIRED, Eligibility.REJECTED


@pytest.mark.parametrize(
    ("title", "experience", "expected"),
    [
        ("Software Engineering Intern", ExperienceRange(), E),
        ("Graduate Trainee - Finance", ExperienceRange(), E),
        ("Senior Software Engineer", ExperienceRange(), X),
        ("Staff Engineer", ExperienceRange(0, 2), X),
        ("Software Engineer II", ExperienceRange(), X),
        ("Software Engineer", ExperienceRange(3, None), X),
        ("Software Engineer", ExperienceRange(0, 2), E),
        ("Analyst", ExperienceRange(1, 3), E),
        ("Analyst", ExperienceRange(1, 4), R),
        ("Business Analyst", ExperienceRange(freshers_mentioned=True), E),
        ("Software Engineer", ExperienceRange(2, None), R),
        ("Software Engineer", ExperienceRange(), R),
        ("Associate Product Manager", ExperienceRange(), R),
        ("Intern - Data (requires 3+ years)", ExperienceRange(3, None), X),
    ],
)
def test_rules(title: str, experience: ExperienceRange, expected: Eligibility) -> None:
    assert decide_by_rules(title, experience).eligibility is expected


def _ai(fresher: bool, confidence: float = 0.9, experience_min: float | None = None) -> Enrichment:
    return Enrichment(
        category=Category.SOFTWARE, skills=("Python",), employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ONSITE, experience_min=experience_min, experience_max=None,
        fresher_friendly=fresher, confidence=confidence, summary="Build things.", model="test",
    )


REVIEW = EligibilityDecision(R, "Experience not stated")
ELIGIBLE = EligibilityDecision(E, "Intern title")
REJECTED = EligibilityDecision(X, "Senior title")


def test_ai_promotes_review_when_confident() -> None:
    result = combine_with_ai(REVIEW, _ai(fresher=True))
    assert result.eligibility is E and result.classified_by is ClassifiedBy.AI


def test_ai_low_confidence_changes_nothing() -> None:
    assert combine_with_ai(REVIEW, _ai(fresher=True, confidence=0.5)) == REVIEW


def test_ai_never_overrides_rejection() -> None:
    assert combine_with_ai(REJECTED, _ai(fresher=True)) == REJECTED


def test_ai_disagreement_demotes_eligible_to_review() -> None:
    assert combine_with_ai(ELIGIBLE, _ai(fresher=False)).eligibility is R


def test_ai_can_reject_review_when_experience_required() -> None:
    assert combine_with_ai(REVIEW, _ai(fresher=False, experience_min=4)).eligibility is X


def test_no_ai_keeps_rules() -> None:
    assert combine_with_ai(REVIEW, None) == REVIEW
