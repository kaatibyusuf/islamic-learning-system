from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class SubjectOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}