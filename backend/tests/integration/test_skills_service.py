"""Integration test: SkillsService persists state + an audit event per answer."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.skill import SkillEvent, SkillState
from app.db.repositories.users import UserRepository
from app.services.skills import SkillsService

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"
TOPIC = "llm.attention"


@pytest.mark.integration
async def test_record_outcome_persists_state_and_events() -> None:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid.uuid4()

        async with sm() as s:
            await UserRepository(s).ensure(user_id, display_name="Tester")
            await SkillsService(s).record_outcome(
                user_id=user_id, topic_ids=[TOPIC], source="quiz", outcome=1.0, difficulty=4
            )
            await s.commit()

        async with sm() as s:
            state = await s.get(SkillState, (user_id, TOPIC))
            assert state is not None
            assert state.attempts == 1
            assert state.mastery > 0.5  # a correct answer raised mastery
            events = (
                (await s.execute(select(SkillEvent).where(SkillEvent.user_id == user_id)))
                .scalars()
                .all()
            )
            assert len(events) == 1
            assert events[0].delta > 0

        # A second, wrong answer updates the same row and appends another event.
        async with sm() as s:
            await SkillsService(s).record_outcome(
                user_id=user_id, topic_ids=[TOPIC], source="quiz", outcome=0.0, difficulty=2
            )
            await s.commit()

        async with sm() as s:
            state = await s.get(SkillState, (user_id, TOPIC))
            assert state is not None
            assert state.attempts == 2
            count = len(
                (await s.execute(select(SkillEvent).where(SkillEvent.user_id == user_id)))
                .scalars()
                .all()
            )
            assert count == 2
    finally:
        await engine.dispose()
