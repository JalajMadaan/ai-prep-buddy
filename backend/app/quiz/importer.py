"""Import a question-bank YAML into Postgres + the Qdrant questions index.

Idempotent: rubrics upsert by (name, version), questions by ``ext_key``.
Run via ``make import-questions``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.question_index import QdrantQuestionIndex, QuestionVector
from app.core.logging import get_logger, setup_logging
from app.db.repositories.questions import QuestionRepository, RubricRepository
from app.db.session import get_sessionmaker
from app.quiz.bank import BankSpec, load_bank

logger = get_logger("quiz.importer")

# backend/app/quiz/importer.py -> parents[3] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_BANK = _REPO_ROOT / "content" / "questions" / "seed.yaml"


@dataclass
class ImportReport:
    rubrics: int = 0
    questions: int = 0


async def import_bank(
    session: AsyncSession, index: QdrantQuestionIndex, bank: BankSpec
) -> ImportReport:
    rubric_ids: dict[str, object] = {}
    rubric_repo = RubricRepository(session)
    for rubric_spec in bank.rubrics:
        rubric = await rubric_repo.upsert(
            name=rubric_spec.name,
            version=rubric_spec.version,
            dimensions=[d.model_dump() for d in rubric_spec.dimensions],
            anchors=rubric_spec.anchors,
        )
        rubric_ids[rubric_spec.name] = rubric.id

    await index.ensure_collection()
    question_repo = QuestionRepository(session)
    vectors: list[QuestionVector] = []
    for q_spec in bank.questions:
        question = await question_repo.upsert(
            ext_key=q_spec.ext_key(),
            kind=q_spec.kind,
            round=q_spec.round,
            text=q_spec.text,
            options=q_spec.options,
            answer=q_spec.answer,
            explanation=q_spec.explanation,
            rubric_id=rubric_ids.get(q_spec.rubric) if q_spec.rubric else None,
            topic_ids=q_spec.topic_ids,
            difficulty=q_spec.difficulty,
            status=q_spec.status,
            created_by="human",
        )
        vectors.append(
            QuestionVector(
                id=question.id,
                text=q_spec.text,
                payload={
                    "question_id": str(question.id),
                    "kind": q_spec.kind,
                    "round": q_spec.round,
                    "topic_ids": q_spec.topic_ids,
                    "difficulty": q_spec.difficulty,
                    "status": q_spec.status,
                },
            )
        )

    await index.upsert(vectors)
    await session.commit()
    report = ImportReport(rubrics=len(bank.rubrics), questions=len(bank.questions))
    logger.info("question_import_complete", rubrics=report.rubrics, questions=report.questions)
    return report


async def main() -> None:
    setup_logging()
    bank = load_bank(SEED_BANK)
    async with get_sessionmaker()() as session:
        await import_bank(session, QdrantQuestionIndex(), bank)


if __name__ == "__main__":
    asyncio.run(main())
