from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.question import Question, QuestionType
from app.models.question_attempt import QuestionAttempt
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_question import QuizQuestion
from app.models.user import User, UserRole
from app.schemas.quiz import QuizSubmitIn, QuizSubmitOut
from app.schemas.quiz_manage import (
    QuizCreate,
    QuizDetailOut,
    QuizDetailQuestionOut,
    QuizOut,
    QuizQuestionAdd,
    QuizQuestionOut,
    QuizUpdate,
)
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


@router.post(
    "",
    response_model=QuizOut,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz(
    payload: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> QuizOut:
    quiz = Quiz(
        title=payload.title.strip(),
        description=payload.description,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return QuizOut.model_validate(quiz)


@router.patch("/{quiz_id}", response_model=QuizOut)
def update_quiz(
    quiz_id: int,
    payload: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> QuizOut:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    if payload.title is not None:
        quiz.title = payload.title.strip()

    if payload.description is not None:
        quiz.description = payload.description

    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return QuizOut.model_validate(quiz)


@router.get("", response_model=list[QuizOut])
def list_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[QuizOut]:
    quizzes = db.scalars(
        select(Quiz)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
    ).all()
    return [QuizOut.model_validate(quiz) for quiz in quizzes]


@router.get("/{quiz_id}", response_model=QuizDetailOut)
def get_quiz_detail(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizDetailOut:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    rows = db.execute(
        select(QuizQuestion, Question)
        .join(Question, Question.id == QuizQuestion.question_id)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.position.asc())
    ).all()

    questions = [
        QuizDetailQuestionOut(
            quiz_question_id=quiz_question.id,
            question_id=question.id,
            position=quiz_question.position,
            prompt=question.prompt,
            question_type=question.question_type.value,
            difficulty=question.difficulty,
            topic_id=question.topic_id,
            choices=question.choices,
        )
        for quiz_question, question in rows
    ]

    return QuizDetailOut(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        questions=questions,
    )


@router.post(
    "/{quiz_id}/questions",
    response_model=QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_question_to_quiz(
    quiz_id: int,
    payload: QuizQuestionAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> QuizQuestionOut:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    question = db.scalar(select(Question).where(Question.id == payload.question_id))
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    existing_question = db.scalar(
        select(QuizQuestion).where(
            QuizQuestion.quiz_id == quiz_id,
            QuizQuestion.question_id == payload.question_id,
        )
    )
    if existing_question:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question already exists in this quiz",
        )

    existing_position = db.scalar(
        select(QuizQuestion).where(
            QuizQuestion.quiz_id == quiz_id,
            QuizQuestion.position == payload.position,
        )
    )
    if existing_position:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another question already uses this position",
        )

    quiz_question = QuizQuestion(
        quiz_id=quiz_id,
        question_id=payload.question_id,
        position=payload.position,
    )
    db.add(quiz_question)
    db.commit()
    db.refresh(quiz_question)

    return QuizQuestionOut.model_validate(quiz_question)


@router.delete(
    "/{quiz_id}/questions/{quiz_question_id}",
    status_code=status.HTTP_200_OK,
)
def remove_question_from_quiz(
    quiz_id: int,
    quiz_question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> dict[str, str]:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    quiz_question = db.scalar(
        select(QuizQuestion).where(
            QuizQuestion.id == quiz_question_id,
            QuizQuestion.quiz_id == quiz_id,
        )
    )
    if not quiz_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz question not found",
        )

    db.delete(quiz_question)
    db.commit()

    return {"message": "Question removed from quiz successfully"}


@router.post("/{quiz_id}/submit", response_model=QuizSubmitOut)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    quiz_attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        started_at=datetime.now(timezone.utc),
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
            user_id=current_user.id,
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
        mastery_engine.recalculate_user_topic_mastery(
            user_id=current_user.id,
            topic_id=topic_id,
        )
        scheduler.refresh_topic_review_item(
            user_id=current_user.id,
            topic_id=topic_id,
        )

    db.commit()

    return QuizSubmitOut(
        quiz_attempt_id=quiz_attempt.id,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_answers,
    )