"""
Shared pytest configuration.

Puts ``src/`` on ``sys.path`` so the suite runs without an editable install,
and exposes the fixture directory. Previously every test file hand-rolled its
own ``sys.path.insert`` block; those are now redundant.
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402  (import after sys.path setup, deliberately)


@pytest.fixture(scope="session")
def fixtures_dir() -> pathlib.Path:
    """Directory holding sample documents used by parser integration tests."""
    return FIXTURES


@pytest.fixture(scope="session")
def sample_pptx(fixtures_dir: pathlib.Path) -> pathlib.Path:
    """Path to the generated sample deck (scripts/generate_sample.py)."""
    return fixtures_dir / "sample_test_presentation.pptx"
