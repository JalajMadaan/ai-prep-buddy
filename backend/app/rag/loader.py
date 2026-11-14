"""Load knowledge-base notes from disk, parsing YAML front matter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# backend/app/rag/loader.py -> parents[3] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
NOTES_DIR = _REPO_ROOT / "content" / "notes"


@dataclass(frozen=True)
class LoadedNote:
    source_key: str
    title: str
    topic_ids: list[str] = field(default_factory=list)
    source_url: str | None = None
    licence: str = "original"
    source_type: str = "note"
    body: str = ""
    raw: str = ""


def parse_front_matter(raw: str) -> tuple[dict[str, object], str]:
    """Split a ``---`` YAML front-matter block from the markdown body."""
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front) or {}
        return meta, body.lstrip("\n")
    return {}, raw


def load_notes(notes_dir: Path = NOTES_DIR) -> list[LoadedNote]:
    """Load every ``*.md`` note under ``notes_dir`` (sorted for determinism)."""
    notes: list[LoadedNote] = []
    for path in sorted(notes_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        raw_topics = meta.get("topic_ids")
        topic_ids = [str(t) for t in raw_topics] if isinstance(raw_topics, list) else []
        raw_url = meta.get("source_url")
        notes.append(
            LoadedNote(
                source_key=f"notes/{path.name}",
                title=str(meta.get("title", path.stem)),
                topic_ids=topic_ids,
                source_url=str(raw_url) if raw_url else None,
                licence=str(meta.get("licence", "original")),
                source_type="note",
                body=body,
                raw=raw,
            )
        )
    return notes
