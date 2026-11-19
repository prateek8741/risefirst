"""Who counts as a fresher role. Rules decide first; AI may only settle the uncertain middle.

Policy:
- Senior titles or 3+ years required -> REJECTED. AI never overrides a rejection.
- Intern/trainee/graduate titles, 0-1 year minimum (max <= 3), or "freshers" -> ELIGIBLE.
- Anything else (2 years, junior title without years, neutral title) -> REVIEW_REQUIRED.
- AI can promote REVIEW_REQUIRED to ELIGIBLE (or REJECTED) only when it is confident, and
  can demote ELIGIBLE to REVIEW_REQUIRED when it confidently disagrees.
"""

from __future__ import annotations

import re

from risefirst.domain.enums import ClassifiedBy, Eligibility
from risefirst.domain.models import EligibilityDecision, Enrichment, ExperienceRange

AI_CONFIDENCE_THRESHOLD = 0.7
FRESHER_MAX_MIN_YEARS = 1.0
FRESHER_MAX_MAX_YEARS = 3.0
REJECT_MIN_YEARS = 3.0

_STRONG_FRESHER_TITLE = re.compile(
    r"\b(intern|internship|trainee|apprentice|apprenticeship|graduate|fresher|freshers|campus|"
    r"entry[- ]level|new grad|early career|university grad|pass[- ]?outs?)\b"
    r"|\b20(?:2[5-7])\s*(?:grad|batch|pass)",
    re.IGNORECASE,
)
_SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|director|head|vp|vice president|architect|chief|avp|"
    r"ii|iii|iv|expert)\b",
    re.IGNORECASE,
)
# "Associate Product Manager" is a classic entry-level role despite containing "Manager".
_JUNIOR_FRIENDLY_EXCEPTION = re.compile(r"associate product manager|\bapm\b", re.IGNORECASE)


def decide_by_rules(title: str, experience: ExperienceRange) -> EligibilityDecision:
    senior = _SENIOR_TITLE.search(title) and not _JUNIOR_FRIENDLY_EXCEPTION.search(title)
    fresher_title = _STRONG_FRESHER_TITLE.search(title)

    if senior and not fresher_title:
        return EligibilityDecision(Eligibility.REJECTED, "Senior title")
    if experience.min_years is not None and experience.min_years >= REJECT_MIN_YEARS:
        return EligibilityDecision(Eligibility.REJECTED, f"Requires {experience.min_years:g}+ years")
    if fresher_title:
        return EligibilityDecision(Eligibility.ELIGIBLE, "Internship / trainee / graduate role")
    if (
        experience.min_years is not None
        and experience.min_years <= FRESHER_MAX_MIN_YEARS
        and (experience.max_years is None or experience.max_years <= FRESHER_MAX_MAX_YEARS)
    ):
        stated = (f"{experience.min_years:g}-{experience.max_years:g}" if experience.max_years is not None
                  else f"{experience.min_years:g}+")
        return EligibilityDecision(Eligibility.ELIGIBLE, f"Asks for {stated} years")
    if experience.min_years is None and experience.freshers_mentioned:
        return EligibilityDecision(Eligibility.ELIGIBLE, "Freshers mentioned")
    if experience.min_years is not None:
        return EligibilityDecision(Eligibility.REVIEW_REQUIRED, f"Borderline: {experience.min_years:g}+ years")
    return EligibilityDecision(Eligibility.REVIEW_REQUIRED, "Experience not stated")


def combine_with_ai(rules: EligibilityDecision, enrichment: Enrichment | None) -> EligibilityDecision:
    if enrichment is None or rules.eligibility is Eligibility.REJECTED:
        return rules
    if enrichment.confidence < AI_CONFIDENCE_THRESHOLD:
        return rules

    ai_min = enrichment.experience_min
    ai_requires_experience = ai_min is not None and ai_min >= REJECT_MIN_YEARS

    if rules.eligibility is Eligibility.ELIGIBLE:
        if ai_requires_experience or not enrichment.fresher_friendly:
            return EligibilityDecision(
                Eligibility.REVIEW_REQUIRED, f"Rules and AI disagree ({rules.reason})", ClassifiedBy.AI
            )
        return rules

    # rules said REVIEW_REQUIRED: AI settles it only when confident.
    if ai_requires_experience:
        return EligibilityDecision(Eligibility.REJECTED, f"AI: requires {ai_min:g}+ years", ClassifiedBy.AI)
    if enrichment.fresher_friendly and (ai_min is None or ai_min <= FRESHER_MAX_MIN_YEARS):
        return EligibilityDecision(Eligibility.ELIGIBLE, "AI: suitable for freshers", ClassifiedBy.AI)
    return rules
