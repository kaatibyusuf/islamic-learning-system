from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    subject_id: int
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140)
    parent_topic_id: int | None = None


class TopicOut(BaseModel):
    id: int
    subject_id: int
    parent_topic_id: int | None = None
    name: str
    slug: str

    model_config = {"from_attributes": True}