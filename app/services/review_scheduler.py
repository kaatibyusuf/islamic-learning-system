from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mastery_record import MasteryRecord
from app.models.review_queue import ReviewQueueItem, ReviewReason


class ReviewScheduler:
    def __init__(self, db: Session):
        self.db = db

    def refresh_topic_review_item(self, user_id: int, topic_id: int) -> ReviewQueueItem | None:
        stmt = select(MasteryRecord).where(
            MasteryRecord.user_id == user_id,
            MasteryRecord.topic_id == topic_id,
        )
        record = self.db.scalar(stmt)

        if not record:
            return None

        self.db.execute(
            delete(ReviewQueueItem).where(
                ReviewQueueItem.user_id == user_id,
                ReviewQueueItem.topic_id == topic_id,
                ReviewQueueItem.status == "pending",
            )
        )

        priority, reason, due_at = self._decide_review(record)
        item = ReviewQueueItem(
            user_id=user_id,
            topic_id=topic_id,
            priority=priority,
            reason=reason,
            due_at=due_at,
            status="pending",
        )
        self.db.add(item)
        self.db.flush()
        return item

    def _decide_review(
        self,
        record: MasteryRecord,
    ) -> tuple[float, ReviewReason, datetime]:
        now = datetime.now(timezone.utc)

        mastery = record.mastery_score
        retention = record.retention_score
        attempts = record.attempts_count
        accuracy = (record.correct_count / attempts) if attempts else 0.0

        if attempts <= 2:
            return 9.5, ReviewReason.NEW_TOPIC, now + timedelta(hours=12)

        if mastery < 40 or accuracy < 0.45:
            return 10.0, ReviewReason.REPEATED_MISTAKES, now + timedelta(hours=6)

        if retention < 45:
            return 8.5, ReviewReason.LOW_RETENTION, now + timedelta(days=1)

        if mastery < 70:
            return 6.5, ReviewReason.WRONG_ANSWER, now + timedelta(days=2)

        if mastery < 85:
            return 4.0, ReviewReason.LOW_RETENTION, now + timedelta(days=5)

        return 2.0, ReviewReason.LOW_RETENTION, now + timedelta(days=10)