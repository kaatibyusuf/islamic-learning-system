from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.questions import router as questions_router
from app.api.routes.quizzes import router as quizzes_router
from app.api.routes.subjects import router as subjects_router
from app.api.routes.teacher import router as teacher_router
from app.api.routes.topics import router as topics_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)

app.include_router(auth_router)
app.include_router(subjects_router)
app.include_router(topics_router)
app.include_router(questions_router)
app.include_router(quizzes_router)
app.include_router(teacher_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}