from pydantic import BaseModel, Field

from app.models.question import QuestionType


class QuestionCreate(BaseModel):
    topic_id: int
    question_type: QuestionType
    prompt: str = Field(min_length=3)
    choices: dict[str, str] | None = None
    answer_key: str = Field(min_length=1)
    explanation: str | None = None
    difficulty: int = Field(ge=1, le=5, default=1)


class QuestionOut(BaseModel):
    id: int
    topic_id: int
    question_type: QuestionType
    prompt: str
    choices: dict[str, str] | None = None
    answer_key: str
    explanation: str | None = None
    difficulty: int

    model_config = {"from_attributes": True}