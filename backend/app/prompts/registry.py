"""Prompt registry: load and render versioned prompt files.

Prompts live at ``app/prompts/<name>/v<N>.md`` with YAML front matter (model
alias, temperature, description) and a Jinja2 body. Code refers to a prompt by
(name, version); a change means a NEW version file, never an in-place edit, so
every prompt change is a reviewable diff and independently evaluable.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from app.core.errors import AppError

PROMPTS_DIR = Path(__file__).parent

# StrictUndefined: rendering with a missing variable raises instead of silently
# producing an empty string — we want prompt bugs to fail loudly.
_env = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)


class PromptNotFoundError(AppError):
    code = "PROMPT_NOT_FOUND"
    status_code = 500


class PromptMeta(BaseModel):
    model: str
    temperature: float = 0.2
    description: str = ""


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    meta: PromptMeta
    template: str

    def render(self, /, **variables: object) -> str:
        """Render the Jinja2 body; a missing variable raises."""
        return _env.from_string(self.template).render(**variables)


def _parse_front_matter(raw: str) -> tuple[dict[str, object], str]:
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front) or {}
        return meta, body.lstrip("\n")
    return {}, raw


@lru_cache
def load_prompt(name: str, version: int) -> Prompt:
    """Load and parse a prompt by name and version (cached)."""
    path = PROMPTS_DIR / name / f"v{version}.md"
    if not path.exists():
        raise PromptNotFoundError(f"Prompt '{name}' v{version} not found at {path}")
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    return Prompt(name=name, version=version, meta=PromptMeta.model_validate(meta), template=body)


def render_prompt(name: str, version: int, /, **variables: object) -> str:
    """Load and render a prompt in one call."""
    return load_prompt(name, version).render(**variables)


def iter_prompt_files() -> list[Path]:
    """Return every ``v<N>.md`` prompt file under the prompts directory."""
    return sorted(PROMPTS_DIR.glob("*/v*.md"))
