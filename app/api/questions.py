from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.question import Question, QuestionType
from app.models.topic import Topic
from app.models.user import User, UserRole
from app.schemas.question import QuestionCreate, QuestionOut


router = APIRouter(prefix="/questions", tags=["questions"])


def _validate_question_payload(payload: QuestionCreate) -> None:
    if payload.question_type == QuestionType.MCQ:
        if not payload.choices or len(payload.choices) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCQ questions must include at least two choices",
            )
        if payload.answer_key not in payload.choices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For MCQ, answer_key must match one of the choice keys",
            )

    if payload.question_type == QuestionType.TRUE_FALSE:
        valid = {"true", "false"}
        if payload.answer_key.strip().lower() not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TRUE_FALSE answer_key must be 'true' or 'false'",
            )


@router.post(
    "",
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> QuestionOut:
    topic = db.scalar(select(Topic).where(Topic.id == payload.topic_id))
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found",
        )

    _validate_question_payload(payload)

    question = Question(
        topic_id=payload.topic_id,
        question_type=payload.question_type,
        prompt=payload.prompt.strip(),
        choices=payload.choices,
        answer_key=payload.answer_key.strip(),
        explanation=payload.explanation,
        difficulty=payload.difficulty,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionOut.model_validate(question)


@router.get("", response_model=list[QuestionOut])
def list_questions(
    topic_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QuestionOut]:
    stmt = select(Question).order_by(Question.id.desc())

    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)

    questions = db.scalars(stmt).all()
    return [QuestionOut.model_validate(question) for question in questions]