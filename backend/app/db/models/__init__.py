"""SQLAlchemy models.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see them. Import new models here.
"""

from app.db.base import Base
from app.db.models.chunk import Chunk
from app.db.models.conversation import Conversation, Message
from app.db.models.document import Document
from app.db.models.question import Question, Rubric
from app.db.models.user import User

__all__ = ["Base", "Chunk", "Conversation", "Document", "Message", "Question", "Rubric", "User"]
