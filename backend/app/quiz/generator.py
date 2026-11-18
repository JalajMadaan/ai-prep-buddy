"""LLM question generator with a validator pipeline.

Generates MCQs from knowledge-base chunks, then gates each candidate: valid JSON
(schema), structural checks (4 options, one correct, distinct), answerable from
the cited source (LLM check), and not a near-duplicate (cosine >= threshold vs the
questions index). Survivors are saved as ``draft`` for admin approval.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.adapters.question_index import QdrantQuestionIndex, QuestionVector
from app.core.logging import get_logger
from app.db.repositories.questions import QuestionRepository
from app.llm.gateway import Gateway
from app.prompts.registry import render_prompt
from app.rag.retriever import HybridRetriever

logger = get_logger("quiz.generator")
GENERATOR_VERSION = "question_gen/v1"
DEFAULT_DUP_THRESHOLD = 0.92


class GeneratedQuestion(BaseModel):
    text: str
    options: list[str]
    correct_index: int
    explanation: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)


class AnswerableVerdict(BaseModel):
    answerable: bool
    reason: str = ""


def validate_structure(q: GeneratedQuestion) -> list[str]:
    """Return a list of structural problems ([] means the question is well-formed)."""
    errors: list[str] = []
    options = [o.strip() for o in q.options]
    if not q.text.strip():
        errors.append("empty_text")
    if len(options) < 3:
        errors.append("too_few_options")
    if any(not o for o in options):
        errors.append("empty_option")
    if len({o.lower() for o in options}) != len(options):
        errors.append("duplicate_options")
    if not 0 <= q.correct_index < len(options):
        errors.append("correct_index_out_of_range")
    return errors


@dataclass
class GenerateReport:
    accepted: int = 0
    rejected: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.rejected[reason] = self.rejected.get(reason, 0) + 1


class QuestionGenerator:
    def __init__(
        self,
        retriever: HybridRetriever,
        gateway: Gateway,
        question_repo: QuestionRepository,
        index: QdrantQuestionIndex,
        *,
        dup_threshold: float = DEFAULT_DUP_THRESHOLD,
    ) -> None:
        self._retriever = retriever
        self._gateway = gateway
        self._repo = question_repo
        self._index = index
        self._dup = dup_threshold

    async def generate_for_topic(self, topic_id: str, *, count: int) -> GenerateReport:
        report = GenerateReport()
        chunks = await self._retriever.retrieve(
            topic_id.replace(".", " "), top_k=6, topic_ids=[topic_id]
        )
        if not chunks:
            report.reject("no_source_chunks")
            return report

        sources = "\n\n".join(f"[{i}] {c.title}: {c.text}" for i, c in enumerate(chunks, 1))
        source_ids = [c.chunk_id for c in chunks]
        for _ in range(count):
            await self._generate_one(topic_id, sources, source_ids, report)
        logger.info(
            "question_generation",
            topic=topic_id,
            accepted=report.accepted,
            rejected=report.rejected,
        )
        return report

    async def _generate_one(
        self, topic_id: str, sources: str, source_ids: list[uuid.UUID], report: GenerateReport
    ) -> None:
        prompt = render_prompt("question_gen", 1, topic=topic_id, sources=sources)
        try:
            gq = await self._gateway.structured(
                [{"role": "user", "content": prompt}], GeneratedQuestion, alias="generator"
            )
        except Exception:
            report.reject("invalid_json")
            return

        errors = validate_structure(gq)
        if errors:
            report.reject(errors[0])
            return

        check = render_prompt(
            "question_check",
            1,
            sources=sources,
            question=gq.text,
            options=gq.options,
            correct_index=gq.correct_index,
        )
        verdict = await self._gateway.structured(
            [{"role": "user", "content": check}], AnswerableVerdict, alias="fast"
        )
        if not verdict.answerable:
            report.reject("not_answerable")
            return

        similar = await self._index.search_similar(gq.text, limit=1)
        if similar and similar[0].score >= self._dup:
            report.reject("duplicate")
            return

        ext_key = "gen_" + hashlib.sha256(gq.text.encode("utf-8")).hexdigest()[:26]
        question = await self._repo.upsert(
            ext_key=ext_key,
            kind="mcq",
            text=gq.text,
            options=gq.options,
            answer={"correct_index": gq.correct_index},
            explanation=gq.explanation,
            topic_ids=[topic_id],
            difficulty=gq.difficulty,
            source_chunk_ids=source_ids,
            status="draft",
            created_by="generator",
            generator_version=GENERATOR_VERSION,
        )
        await self._index.upsert(
            [
                QuestionVector(
                    id=question.id,
                    text=gq.text,
                    payload={
                        "question_id": str(question.id),
                        "kind": "mcq",
                        "topic_ids": [topic_id],
                        "difficulty": gq.difficulty,
                        "status": "draft",
                    },
                )
            ]
        )
        report.accepted += 1
