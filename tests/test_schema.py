import json

import pytest
from pydantic import ValidationError

from etchr.schema import Case, DatasetError, FailureType, Label, load_cases


def make(**overrides):
    base = {
        "id": "negation-001",
        "failure_type": "negation",
        "conversation": [
            {"turn_id": "t1", "speaker": "user", "text": "I don't eat meat anymore."},
        ],
        "candidate_memory": "User eats meat.",
    }
    base.update(overrides)
    return base


def test_unlabeled_case_is_valid():
    case = Case.model_validate(make())
    assert case.label is None
    assert not case.is_labeled


def test_labeled_case_is_valid():
    case = Case.model_validate(make(label="contradicted", evidence_turn_ids=["t1"]))
    assert case.label is Label.CONTRADICTED
    assert case.failure_type is FailureType.NEGATION


def test_unsupported_may_have_no_evidence():
    Case.model_validate(make(label="unsupported"))


@pytest.mark.parametrize("label", ["supported", "contradicted"])
def test_supported_and_contradicted_need_evidence(label):
    with pytest.raises(ValidationError, match="needs evidence_turn_ids"):
        Case.model_validate(make(label=label))


def test_evidence_must_exist_in_conversation():
    with pytest.raises(ValidationError, match="not in conversation"):
        Case.model_validate(make(label="contradicted", evidence_turn_ids=["t9"]))


def test_evidence_without_label_rejected():
    with pytest.raises(ValidationError, match="label is empty"):
        Case.model_validate(make(evidence_turn_ids=["t1"]))


def test_duplicate_turn_ids_rejected():
    turn = {"turn_id": "t1", "speaker": "user", "text": "hi"}
    with pytest.raises(ValidationError, match="duplicate turn_id"):
        Case.model_validate(make(conversation=[turn, turn]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "Negation-1"},
        {"failure_type": "typo"},
        {"label": "maybe"},
        {"candidate_memory": ""},
        {"conversation": []},
        {"surprise_field": 1},
        {"conversation": [{"turn_id": "t1", "speaker": "system", "text": "x"}]},
    ],
)
def test_bad_fields_rejected(overrides):
    with pytest.raises(ValidationError):
        Case.model_validate(make(**overrides))


def test_load_cases_reports_line_number(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(make()) + "\n\n" + "{not json}\n", encoding="utf-8")
    with pytest.raises(DatasetError, match=r":3:"):
        load_cases(path)


def test_load_cases_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "cases.jsonl"
    line = json.dumps(make())
    path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="duplicate id"):
        load_cases(path)
