"""Checks on the committed benchmark file itself."""

from collections import Counter
from pathlib import Path

from etchr.schema import FailureType, load_cases

CASES = Path(__file__).resolve().parents[1] / "data" / "cases.jsonl"


def test_cases_file_loads():
    # load_cases validates every line and rejects duplicate ids.
    assert len(load_cases(CASES)) > 0


def test_every_failure_type_is_covered():
    counts = Counter(c.failure_type for c in load_cases(CASES))
    missing = [ft.value for ft in FailureType if counts[ft] == 0]
    assert not missing, f"no cases for: {missing}"


def test_case_ids_match_failure_type():
    for case in load_cases(CASES):
        assert case.id.rsplit("-", 1)[0] == case.failure_type.value, case.id
