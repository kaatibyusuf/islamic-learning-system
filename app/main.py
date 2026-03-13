from fastapi import FastAPI

from app.api.routes.quizzes import router as quizzes_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(quizzes_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}