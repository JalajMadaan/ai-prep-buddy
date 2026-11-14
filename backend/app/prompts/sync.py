"""Validate all prompts and (later) sync them to Langfuse.

Run via ``make prompts-sync``. Today it validates that every prompt file parses
(front matter + Jinja2 compiles) — a useful CI guard. Pushing versions to the
Langfuse prompt registry is wired in M1 alongside the rest of tracing; until
LANGFUSE keys are configured this step is skipped.
"""

from __future__ import annotations

from jinja2 import Environment, StrictUndefined

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.prompts.registry import _parse_front_matter, iter_prompt_files

logger = get_logger("prompts.sync")


def validate_all() -> int:
    """Parse and compile every prompt; raise on the first broken one. Returns count."""
    env = Environment(undefined=StrictUndefined, autoescape=False)
    files = iter_prompt_files()
    for path in files:
        _, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        env.parse(body)  # raises TemplateSyntaxError on a malformed template
    logger.info("prompts_validated", count=len(files))
    return len(files)


def main() -> None:
    setup_logging()
    validate_all()
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("langfuse_sync_skipped", reason="LANGFUSE keys not configured (wired in M1)")
        return
    logger.info("langfuse_sync_skipped", reason="Langfuse push implemented in M1")


if __name__ == "__main__":
    main()
