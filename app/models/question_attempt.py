from datetime import datetime
from sqlalchemy import ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
        index=True,
    )

    quiz_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_attempts.id")
    )

    response: Mapped[str] = mapped_column(Text)

    is_correct: Mapped[bool] = mapped_column(Boolean)

    response_time: Mapped[int | None]

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )