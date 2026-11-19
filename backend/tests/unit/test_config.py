import pytest

from risefirst.config import Settings


@pytest.mark.parametrize(
    "given",
    [
        "postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        "postgres://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
    ],
)
def test_hosted_postgres_urls_get_the_psycopg_driver(given: str) -> None:
    url = Settings(database_url=given, _env_file=None).database_url
    assert url == ("postgresql+psycopg://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb"
                   "?sslmode=require&channel_binding=require")


def test_explicit_driver_is_kept() -> None:
    assert Settings(database_url="postgresql+psycopg://localhost/x", _env_file=None).database_url == (
        "postgresql+psycopg://localhost/x")
