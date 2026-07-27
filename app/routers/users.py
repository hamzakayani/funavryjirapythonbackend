from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.repositories import UserRepository
from app.schemas import UserListItem

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserListItem])
def list_platform_users(
    q: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    users = UserRepository(db).list_active()
    if q:
        needle = q.strip().lower()
        users = [u for u in users if needle in u.name.lower() or needle in u.email.lower()]
    return users
