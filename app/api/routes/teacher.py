from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models.user import User, UserRole


router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/dashboard")
def teacher_dashboard(
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> dict:
    return {
        "message": f"Welcome, {current_user.full_name}",
        "role": current_user.role,
    }