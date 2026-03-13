from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import exp

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mastery_record import MasteryRecord
from app.models.question import Question
from app.models.question_attempt import QuestionAttempt


class MasteryEngine:
    def __init__(self, db: Session):
        self.db = db

    def recalculate_user_topic_mastery(self, user_id: int, topic_id: int) -> MasteryRecord:
        stmt = (
            select(QuestionAttempt, Question)
            .join(Question, Question.id == QuestionAttempt.question_id)
            .where(
                QuestionAttempt.user_id == user_id,
                Question.topic_id == topic_id,
            )
            .order_by(QuestionAttempt.attempted_at.asc())
        )
        rows = self.db.execute(stmt).all()

        if not rows:
            record = self._get_or_create_record(user_id=user_id, topic_id=topic_id)
            record.mastery_score = 0.0
            record.retention_score = 0.0
            record.confidence_score = 0.0
            record.attempts_count = 0
            record.correct_count = 0
            self.db.add(record)
            self.db.flush()
            return record

        total_weight = 0.0
        weighted_correct = 0.0
        response_speed_total = 0.0
        response_speed_count = 0
        correct_count = 0
        attempts_count = len(rows)

        now = datetime.now(timezone.utc)

        for attempt, question in rows:
            difficulty = max(1, int(question.difficulty or 1))
            difficulty_weight = 1.0 + (difficulty - 1) * 0.15

            attempted_at = attempt.attempted_at
            if attempted_at.tzinfo is None:
                attempted_at = attempted_at.replace(tzinfo=timezone.utc)

            age_days = max(0.0, (now - attempted_at).total_seconds() / 86400)
            recency_weight = exp(-age_days / 30.0)

            weight = difficulty_weight * (0.6 + 0.4 * recency_weight)
            total_weight += weight

            if attempt.is_correct:
                weighted_correct += weight
                correct_count += 1

            if attempt.response_time is not None and attempt.response_time > 0:
                response_speed_total += attempt.response_time
                response_speed_count += 1

        raw_mastery = (weighted_correct / total_weight) * 100 if total_weight else 0.0

        repeated_mistake_penalty = self._repeated_mistake_penalty(user_id=user_id, topic_id=topic_id)
        mastery_score = max(0.0, min(100.0, raw_mastery - repeated_mistake_penalty))

        retention_score = self._calculate_retention(rows)
        confidence_score = self._calculate_confidence(
            attempts_count=attempts_count,
            correct_count=correct_count,
            avg_response_time=(response_speed_total / response_speed_count) if response_speed_count else None,
        )

        record = self._get_or_create_record(user_id=user_id, topic_id=topic_id)
        record.mastery_score = round(mastery_score, 2)
        record.retention_score = round(retention_score, 2)
        record.confidence_score = round(confidence_score, 2)
        record.attempts_count = attempts_count
        record.correct_count = correct_count

        self.db.add(record)
        self.db.flush()
        return record

    def _get_or_create_record(self, user_id: int, topic_id: int) -> MasteryRecord:
        stmt = select(MasteryRecord).where(
            MasteryRecord.user_id == user_id,
            MasteryRecord.topic_id == topic_id,
        )
        record = self.db.scalar(stmt)
        if record:
            return record
        return MasteryRecord(user_id=user_id, topic_id=topic_id)

    def _repeated_mistake_penalty(self, user_id: int, topic_id: int) -> float:
        stmt = (
            select(QuestionAttempt, Question)
            .join(Question, Question.id == QuestionAttempt.question_id)
            .where(
                QuestionAttempt.user_id == user_id,
                Question.topic_id == topic_id,
            )
            .order_by(QuestionAttempt.attempted_at.asc())
        )
        rows = self.db.execute(stmt).all()

        wrong_streaks_by_question: dict[int, int] = defaultdict(int)
        max_penalty = 0.0

        for attempt, question in rows:
            if attempt.is_correct:
                wrong_streaks_by_question[question.id] = 0
            else:
                wrong_streaks_by_question[question.id] += 1
                streak = wrong_streaks_by_question[question.id]
                if streak >= 2:
                    max_penalty += min(2.5, streak * 0.8)

        return min(15.0, max_penalty)

    def _calculate_retention(self, rows: list[tuple[QuestionAttempt, Question]]) -> float:
        latest_by_question: dict[int, tuple[QuestionAttempt, Question]] = {}
        for attempt, question in rows:
            latest_by_question[question.id] = (attempt, question)

        now = datetime.now(timezone.utc)
        total = 0.0
        score = 0.0

        for attempt, question in latest_by_question.values():
            attempted_at = attempt.attempted_at
            if attempted_at.tzinfo is None:
                attempted_at = attempted_at.replace(tzinfo=timezone.utc)

            age_days = max(0.0, (now - attempted_at).total_seconds() / 86400)
            decay = exp(-age_days / 21.0)

            total += 1.0
            if attempt.is_correct:
                score += 100.0 * decay
            else:
                score += 35.0 * decay

        return score / total if total else 0.0

    def _calculate_confidence(
        self,
        attempts_count: int,
        correct_count: int,
        avg_response_time: float | None,
    ) -> float:
        if attempts_count == 0:
            return 0.0

        accuracy_component = (correct_count / attempts_count) * 70.0
        sample_component = min(20.0, attempts_count * 1.5)

        speed_component = 0.0
        if avg_response_time is not None:
            if avg_response_time <= 15:
                speed_component = 10.0
            elif avg_response_time <= 30:
                speed_component = 7.0
            elif avg_response_time <= 60:
                speed_component = 4.0
            else:
                speed_component = 2.0

        return min(100.0, accuracy_component + sample_component + speed_component)