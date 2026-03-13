from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.question import Question, QuestionType
from app.models.question_attempt import QuestionAttempt
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_question import QuizQuestion
from app.schemas.quiz import QuizSubmitIn, QuizSubmitOut
from app.services.mastery_engine import MasteryEngine
from app.services.review_scheduler import ReviewScheduler

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _normalize_response(value: str) -> str:
    return value.strip().lower()


def _is_answer_correct(question: Question, response: str) -> bool:
    normalized_response = _normalize_response(response)
    normalized_key = _normalize_response(question.answer_key)

    if question.question_type in {
        QuestionType.MCQ,
        QuestionType.TRUE_FALSE,
        QuestionType.FILL_BLANK,
        QuestionType.SHORT_ANSWER,
    }:
        return normalized_response == normalized_key

    return False


@router.post("/{quiz_id}/submit", response_model=QuizSubmitOut)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitIn,
    db: Session = Depends(get_db),
) -> QuizSubmitOut:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    quiz_question_rows = db.execute(
        select(QuizQuestion, Question)
        .join(Question, Question.id == QuizQuestion.question_id)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.position.asc())
    ).all()

    if not quiz_question_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz has no questions",
        )

    questions_by_id = {question.id: question for _, question in quiz_question_rows}
    valid_question_ids = set(questions_by_id.keys())

    submitted_question_ids = {answer.question_id for answer in payload.answers}
    unknown_ids = submitted_question_ids - valid_question_ids
    if unknown_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid question IDs submitted: {sorted(unknown_ids)}",
        )

    user_id = 1

    started_at = datetime.now(timezone.utc)
    quiz_attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        started_at=started_at,
        completed_at=None,
        score=None,
    )
    db.add(quiz_attempt)
    db.flush()

    correct_answers = 0
    touched_topics: set[int] = set()

    for answer in payload.answers:
        question = questions_by_id[answer.question_id]
        is_correct = _is_answer_correct(question, answer.response)

        if is_correct:
            correct_answers += 1

        touched_topics.add(question.topic_id)

        attempt = QuestionAttempt(
            user_id=user_id,
            question_id=question.id,
            quiz_attempt_id=quiz_attempt.id,
            response=answer.response,
            is_correct=is_correct,
            response_time=answer.response_time,
            attempted_at=datetime.now(timezone.utc),
        )
        db.add(attempt)

    total_questions = len(valid_question_ids)
    score = round((correct_answers / total_questions) * 100, 2)

    quiz_attempt.completed_at = datetime.now(timezone.utc)
    quiz_attempt.score = score
    db.add(quiz_attempt)
    db.flush()

    mastery_engine = MasteryEngine(db)
    scheduler = ReviewScheduler(db)

    for topic_id in touched_topics:
        mastery_engine.recalculate_user_topic_mastery(user_id=user_id, topic_id=topic_id)
        scheduler.refresh_topic_review_item(user_id=user_id, topic_id=topic_id)

    db.commit()

    return QuizSubmitOut(
        quiz_attempt_id=quiz_attempt.id,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_answers,
    )