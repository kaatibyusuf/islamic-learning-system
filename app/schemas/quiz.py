from pydantic import BaseModel, Field


class QuizAnswerIn(BaseModel):
    question_id: int
    response: str = Field(min_length=1)
    response_time: int | None = None


class QuizSubmitIn(BaseModel):
    answers: list[QuizAnswerIn]


class QuizSubmitOut(BaseModel):
    quiz_attempt_id: int
    score: float
    total_questions: int
    correct_answers: int