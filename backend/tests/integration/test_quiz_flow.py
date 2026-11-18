"""Integration test: build a drill, answer an MCQ, check side-effects, finish."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.review_card import ReviewCard
from app.db.models.skill import SkillState
from app.db.repositories.questions import QuestionRepository
from app.db.repositories.users import UserRepository
from app.llm.gateway import Gateway
from app.services.quiz import QuizService

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"
TOPIC = "llm.attention"


@pytest.mark.integration
async def test_today_answer_finish() -> None:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid.uuid4()

        async with sm() as s:
            await UserRepository(s).ensure(user_id, display_name="Tester")
            question = await QuestionRepository(s).upsert(
                ext_key="quiz-mcq",
                kind="mcq",
                text="Which stabilises softmax?",
                options=["dropout", "sqrt(d_k) scaling"],
                answer={"correct_index": 1},
                explanation="scaling keeps softmax stable",
                topic_ids=[TOPIC],
                difficulty=2,
                status="approved",
            )
            await s.commit()
            qid = question.id

        async with sm() as s:
            quiz, questions = await QuizService(s, Gateway()).build_today(user_id, size=5, seed=1)
            await s.commit()
            assert qid in [q.id for q in questions]
            session_id = quiz.id

        async with sm() as s:
            result = await QuizService(s, Gateway()).answer(
                user_id, quiz_session_id=session_id, question_id=qid, answer="1"
            )
            await s.commit()
        assert result["correct"] is True
        assert result["score"] == 1.0
        assert result["next_due_at"]

        # Side-effects: mastery updated and a review card scheduled.
        async with sm() as s:
            state = await s.get(SkillState, (user_id, TOPIC))
            assert state is not None and state.attempts == 1 and state.mastery > 0.5
            card = await s.get(ReviewCard, (user_id, qid))
            assert card is not None

        async with sm() as s:
            summary = await QuizService(s, Gateway()).finish(session_id)
        assert summary == {"total": 1, "correct": 1}
    finally:
        await engine.dispose()
