"""User repository: all user SQL lives here, keeping it out of services."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    """Data access for :class:`User`. Flushes but does not commit; the caller
    (service or request session) owns the transaction boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        display_name: str,
        github_id: str | None = None,
        email_hash: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> User:
        """Insert a new user and return it (with its generated id populated)."""
        user = User(
            display_name=display_name,
            github_id=github_id,
            email_hash=email_hash,
            settings=settings or {},
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get(self, user_id: UUID) -> User | None:
        """Fetch a user by primary key, or None."""
        return await self._session.get(User, user_id)

    async def get_by_github_id(self, github_id: str) -> User | None:
        """Fetch a user by their GitHub id, or None."""
        result = await self._session.execute(select(User).where(User.github_id == github_id))
        return result.scalars().one_or_none()
