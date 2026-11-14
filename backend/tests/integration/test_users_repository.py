"""Integration test: create and read a user against the app_test database.

Requires `make up`. Runs via `make test-int` (excluded from `make check`).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.repositories.users import UserRepository

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"


@pytest.mark.integration
async def test_create_and_read_user() -> None:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as session:
            repo = UserRepository(session)
            created = await repo.create(
                display_name="Jalaj",
                github_id="gh-123",
                settings={"persona": "strict"},
            )
            await session.commit()
            user_id = created.id

        # id is a UUIDv7 and timestamps were populated by the database.
        assert isinstance(user_id, uuid.UUID)
        assert created.created_at is not None

        async with session_factory() as session:
            repo = UserRepository(session)
            fetched = await repo.get(user_id)
            assert fetched is not None
            assert fetched.display_name == "Jalaj"
            assert fetched.github_id == "gh-123"
            assert fetched.settings == {"persona": "strict"}

            by_gh = await repo.get_by_github_id("gh-123")
            assert by_gh is not None and by_gh.id == user_id

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
