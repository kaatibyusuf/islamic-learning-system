from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import User, UserRole
from app.schemas.topic import TopicCreate, TopicOut


router = APIRouter(prefix="/topics", tags=["topics"])


@router.post(
    "",
    response_model=TopicOut,
    status_code=status.HTTP_201_CREATED,
)
def create_topic(
    payload: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> TopicOut:
    subject = db.scalar(select(Subject).where(Subject.id == payload.subject_id))
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    existing_slug = db.scalar(select(Topic).where(Topic.slug == payload.slug))
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic slug already exists",
        )

    if payload.parent_topic_id is not None:
        parent = db.scalar(select(Topic).where(Topic.id == payload.parent_topic_id))
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent topic not found",
            )

    topic = Topic(
        subject_id=payload.subject_id,
        parent_topic_id=payload.parent_topic_id,
        name=payload.name.strip(),
        slug=payload.slug.strip().lower(),
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return TopicOut.model_validate(topic)


@router.get("", response_model=list[TopicOut])
def list_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicOut]:
    topics = db.scalars(select(Topic).order_by(Topic.name.asc())).all()
    return [TopicOut.model_validate(topic) for topic in topics]


@router.get("/subject/{subject_id}", response_model=list[TopicOut])
def list_topics_by_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicOut]:
    topics = db.scalars(
        select(Topic)
        .where(Topic.subject_id == subject_id)
        .order_by(Topic.name.asc())
    ).all()
    return [TopicOut.model_validate(topic) for topic in topics]