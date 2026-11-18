"""Integration test: SchedulerService persists and advances a review card."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.review_card import ReviewCard
from app.db.repositories.questions import QuestionRepository
from app.db.repositories.users import UserRepository
from app.services.scheduler import SchedulerService

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"


@pytest.mark.integration
async def test_review_persists_and_advances() -> None:
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
                ext_key="sched-q",
                kind="mcq",
                text="Q?",
                options=["a", "b"],
                answer={"correct_index": 0},
                topic_ids=["llm.attention"],
                difficulty=2,
                status="approved",
            )
            await s.commit()
            question_id = question.id

        async with sm() as s:
            card = await SchedulerService(s).review(
                user_id=user_id, question_id=question_id, rating="good"
            )
            await s.commit()
            first_due = card.due_at

        async with sm() as s:
            stored = await s.get(ReviewCard, (user_id, question_id))
            assert stored is not None
            assert stored.due_at is not None
            assert stored.fsrs_state  # FSRS state persisted

        async with sm() as s:
            card2 = await SchedulerService(s).review(
                user_id=user_id, question_id=question_id, rating="good"
            )
            await s.commit()
            assert card2.due_at >= first_due  # a second good review pushes it out
    finally:
        await engine.dispose()
