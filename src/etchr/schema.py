"""Data model for etchr benchmark cases.

A case is one conversation plus one candidate memory that a memory store
might write from it. A human labels whether the conversation supports the
candidate memory. Checkers are scored against those human labels.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class Label(StrEnum):
    """Human verdict on a candidate memory."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


class FailureType(StrEnum):
    """The kind of write failure a case is built to probe.

    The two ``control_*`` types are sanity cases where the right answer
    should be obvious; a checker that fails them is broken.
    """

    MISATTRIBUTION = "misattribution"
    HYPOTHETICAL = "hypothetical"
    NEGATION = "negation"
    SARCASM = "sarcasm"
    QUOTING = "quoting"
    OVERGENERALIZATION = "overgeneralization"
    TEMPORAL_DRIFT = "temporal_drift"
    INJECTION = "injection"
    CONTROL_SUPPORTED = "control_supported"
    CONTROL_CONTRADICTED = "control_contradicted"


class Turn(BaseModel):
    """One message in a conversation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_id: str = Field(min_length=1)
    speaker: Literal["user", "assistant"]
    text: str = Field(min_length=1)


class Case(BaseModel):
    """One benchmark item.

    ``label`` is ``None`` until a human labels the case. Unlabeled cases are
    valid on disk but are excluded from scoring.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z_]+-\d{3}$")
    failure_type: FailureType
    conversation: list[Turn] = Field(min_length=1)
    candidate_memory: str = Field(min_length=1)
    label: Label | None = None
    evidence_turn_ids: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def _check_consistency(self) -> Case:
        turn_ids = [t.turn_id for t in self.conversation]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError(f"{self.id}: duplicate turn_id in conversation")

        missing = set(self.evidence_turn_ids) - set(turn_ids)
        if missing:
            raise ValueError(f"{self.id}: evidence_turn_ids not in conversation: {sorted(missing)}")

        if self.label is None and self.evidence_turn_ids:
            raise ValueError(f"{self.id}: evidence given but label is empty")

        # Supported and contradicted are claims about specific turns, so they
        # must point at them. Unsupported means no turn backs the memory, so
        # evidence is optional there.
        if self.label in (Label.SUPPORTED, Label.CONTRADICTED) and not self.evidence_turn_ids:
            raise ValueError(f"{self.id}: label '{self.label}' needs evidence_turn_ids")
        return self

    @property
    def is_labeled(self) -> bool:
        return self.label is not None


class DatasetError(ValueError):
    """Raised when a cases file is malformed. Message names the line."""


def load_cases(path: str | Path) -> list[Case]:
    """Load and validate a JSONL cases file.

    Raises ``DatasetError`` naming the first bad line, or the first
    duplicate id. Blank lines are skipped.
    """
    cases: list[Case] = []
    seen: dict[str, int] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            try:
                case = Case.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise DatasetError(f"{path}:{lineno}: {exc}") from exc
            if case.id in seen:
                raise DatasetError(f"{path}:{lineno}: duplicate id {case.id!r} (first on line {seen[case.id]})")
            seen[case.id] = lineno
            cases.append(case)
    return cases
