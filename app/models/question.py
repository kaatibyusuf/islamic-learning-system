import enum
from sqlalchemy import String, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id"),
        nullable=False,
        index=True,
    )

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"),
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    choices: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    answer_key: Mapped[str] = mapped_column(String, nullable=False)

    explanation: Mapped[str | None] = mapped_column(Text)

    difficulty: Mapped[int] = mapped_column(default=1)

    topic: Mapped["Topic"] = relationship()