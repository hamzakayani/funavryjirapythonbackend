from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.permissions import (
    can_assign_issue,
    can_change_issue_status,
    can_edit_issue,
    can_edit_standup_entry,
    can_manage_project,
    get_project_membership,
)
from app.core.security import decode_access_token
from app.database import get_db
from app.models import Project, User, UserStatus
from app.repositories import ProjectRepository, UserRepository

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        user_id = decode_access_token(credentials.credentials)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status != UserStatus.Active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account status: {user.status.value}",
        )
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required",
        )
    return user


def require_project_access(db: Session, user: User, project_id: int) -> Project:
    project = ProjectRepository(db).get_active_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not user.is_super_admin:
        membership = get_project_membership(db, user, project_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Not a project member")
    return project


__all__ = [
    "get_current_user",
    "require_super_admin",
    "require_project_access",
    "get_project_membership",
    "can_manage_project",
    "can_edit_issue",
    "can_change_issue_status",
    "can_assign_issue",
    "can_edit_standup_entry",
]
