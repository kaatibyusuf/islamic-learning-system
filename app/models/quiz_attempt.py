from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))

    started_at: Mapped[datetime] = mapped_column(DateTime)

    completed_at: Mapped[datetime | None]

    score: Mapped[float | None]