from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_id", name="uq_quiz_question_unique"),
        UniqueConstraint("quiz_id", "position", name="uq_quiz_position_unique"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(nullable=False)

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")
    question: Mapped["Question"] = relationship()