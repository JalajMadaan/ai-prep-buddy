"""Conversation + message repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: uuid.UUID, title: str | None = None) -> Conversation:
        conv = Conversation(user_id=user_id, title=title)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def get_message(self, message_id: uuid.UUID) -> Message | None:
        return await self._session.get(Message, message_id)

    async def recent_messages(self, conversation_id: uuid.UUID, *, limit: int = 6) -> list[Message]:
        """Return the last ``limit`` messages in chronological order."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())  # UUIDv7 is time-ordered
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(reversed(rows))

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        role: str,
        text: str,
        style: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        model: str | None = None,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        abstained: bool = False,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            text_masked=text,
            style=style,
            citations=citations or [],
            model=model,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            abstained=abstained,
        )
        self._session.add(message)
        await self._session.flush()
        return message
