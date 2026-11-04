"""Smoke test: proves the package imports and the test runner works."""

from app import version


def test_version_is_semver_string() -> None:
    v = version()
    assert isinstance(v, str)
    assert v.count(".") == 2
