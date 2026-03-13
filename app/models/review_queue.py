from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ReviewReason(str, enum.Enum):
    NEW_TOPIC = "new_topic"
    WRONG_ANSWER = "wrong_answer"
    LOW_RETENTION = "low_retention"
    REPEATED_MISTAKES = "repeated_mistakes"
    UPCOMING_EXAM = "upcoming_exam"


class ReviewQueueItem(Base, TimestampMixin):
    __tablename__ = "review_queue_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id"),
        nullable=False,
        index=True,
    )

    priority: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    reason: Mapped[ReviewReason] = mapped_column(
        Enum(ReviewReason, name="review_reason"),
        nullable=False,
    )

    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)