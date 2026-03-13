from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.subject import SubjectCreate, SubjectOut


router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.post(
    "",
    response_model=SubjectOut,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> SubjectOut:
    existing = db.scalar(select(Subject).where(Subject.name == payload.name))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subject already exists",
        )

    subject = Subject(
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectOut.model_validate(subject)


@router.get("", response_model=list[SubjectOut])
def list_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SubjectOut]:
    subjects = db.scalars(select(Subject).order_by(Subject.name.asc())).all()
    return [SubjectOut.model_validate(subject) for subject in subjects]