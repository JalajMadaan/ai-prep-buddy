"""Question-bank YAML format and loader (validated with Pydantic)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class DimensionSpec(BaseModel):
    key: str
    description: str = ""
    weight: float = 1.0


class RubricSpec(BaseModel):
    name: str
    version: int = 1
    dimensions: list[DimensionSpec] = Field(default_factory=list)
    anchors: dict[str, Any] = Field(default_factory=dict)


class QuestionSpec(BaseModel):
    key: str | None = None  # explicit import key; otherwise derived from the text
    kind: Literal["mcq", "short", "flashcard", "interview"]
    text: str
    topic_ids: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=3, ge=1, le=5)
    options: list[Any] = Field(default_factory=list)
    answer: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = None
    rubric: str | None = None  # rubric name
    round: str | None = None
    status: Literal["draft", "approved", "retired"] = "approved"

    def ext_key(self) -> str:
        if self.key:
            return self.key
        return "q_" + hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:28]


class BankSpec(BaseModel):
    rubrics: list[RubricSpec] = Field(default_factory=list)
    questions: list[QuestionSpec] = Field(default_factory=list)


def load_bank(path: Path) -> BankSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return BankSpec.model_validate(data)
