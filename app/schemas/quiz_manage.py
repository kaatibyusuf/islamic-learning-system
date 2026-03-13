from pydantic import BaseModel, Field


class QuizCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None


class QuizUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None


class QuizQuestionAdd(BaseModel):
    question_id: int
    position: int = Field(ge=1)


class QuizQuestionOut(BaseModel):
    id: int
    question_id: int
    position: int

    model_config = {"from_attributes": True}


class QuizOut(BaseModel):
    id: int
    title: str
    description: str | None = None

    model_config = {"from_attributes": True}


class QuizDetailQuestionOut(BaseModel):
    quiz_question_id: int
    question_id: int
    position: int
    prompt: str
    question_type: str
    difficulty: int
    topic_id: int
    choices: dict[str, str] | None = None


class QuizDetailOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    questions: list[QuizDetailQuestionOut]