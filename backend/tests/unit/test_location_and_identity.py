from risefirst.domain.classification import category_of, employment_type_of
from risefirst.domain.enums import Category, EmploymentType, WorkMode
from risefirst.domain.identity import fingerprint, normalize_company, slugify
from risefirst.domain.location import cities_in, is_in_india, work_mode_of


def test_city_aliases_normalise() -> None:
    assert cities_in("Bangalore, Karnataka") == ["Bengaluru"]
    assert cities_in("Gurugram | Noida") == ["Delhi NCR"]
    assert cities_in("Bombay; Pune") == ["Mumbai", "Pune"]


def test_india_detection() -> None:
    assert is_in_india("Remote - India")
    assert is_in_india("Hyderabad")
    assert not is_in_india("Indianapolis, IN")
    assert not is_in_india("San Francisco, CA")


def test_work_mode() -> None:
    assert work_mode_of("Remote, India") is WorkMode.REMOTE
    assert work_mode_of("Bengaluru (Hybrid)") is WorkMode.HYBRID
    assert work_mode_of("Pune") is WorkMode.ONSITE
    assert work_mode_of("India", hint="remote") is WorkMode.REMOTE
    assert work_mode_of("India") is WorkMode.UNKNOWN


def test_category_and_employment_type() -> None:
    assert category_of("Data Engineer") is Category.DATA_AI
    assert category_of("Backend Developer") is Category.SOFTWARE
    assert category_of("Talent Acquisition Intern") is Category.HR
    assert employment_type_of("Marketing Intern", hint="Full-time") is EmploymentType.INTERNSHIP
    assert employment_type_of("Analyst", hint="Full-time") is EmploymentType.FULL_TIME


def test_duplicate_fingerprint_ignores_noise() -> None:
    a = fingerprint("Razorpay Software Private Limited", "Sr. Analyst (Remote)", ["Bengaluru"])
    b = fingerprint("Razorpay", "Senior Analyst", ["Bengaluru"])
    assert a == b
    assert a != fingerprint("Razorpay", "Senior Analyst", ["Mumbai"])


def test_normalise_and_slug() -> None:
    assert normalize_company("Hevo Data Inc.") == "hevo data"
    assert slugify("CRED", "SDE Intern – 2026") == "cred-sde-intern-2026"
