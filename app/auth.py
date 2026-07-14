from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserStatus, ProjectMember, Project

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status != UserStatus.Active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account status: {user.status.value}")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")
    return user


def get_project_membership(db: Session, user: User, project_id: int) -> Optional[ProjectMember]:
    if user.is_super_admin:
        return None
    return db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
    ).first()


def require_project_access(db: Session, user: User, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.is_archived == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not user.is_super_admin:
        membership = get_project_membership(db, user, project_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Not a project member")
    return project


def can_manage_project(db: Session, user: User, project_id: int) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, project_id)
    return membership is not None and membership.project_role.value == "Lead"


def can_edit_issue(db: Session, user: User, issue) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return issue.reporter_id == user.id or issue.assignee_id == user.id


def can_change_issue_status(db: Session, user: User, issue) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return issue.assignee_id == user.id


def can_assign_issue(db: Session, user: User, issue, assignee_id: int | None) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return assignee_id == user.id or (assignee_id is None and issue.assignee_id == user.id)
