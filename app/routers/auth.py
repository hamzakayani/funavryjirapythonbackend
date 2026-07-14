from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token, hash_password, verify_password,
    get_current_user, require_super_admin,
)
from app.database import get_db
from app.models import User, UserStatus, ProjectMember, Project
from app.schemas import (
    RegisterRequest, LoginRequest, AuthResponse, MeResponse,
    UserBrief, ProjectMembershipOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        name=data.name,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        job_title=data.job_title,
        status=UserStatus.Pending,
    )
    db.add(user)
    db.commit()
    return {"message": "Registration submitted. Awaiting approval.", "status": "Pending"}


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status != UserStatus.Active:
        messages = {
            UserStatus.Pending: "Your account is awaiting approval.",
            UserStatus.Rejected: "Your registration was not approved.",
            UserStatus.Suspended: "Your account has been suspended. Contact your administrator.",
        }
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_NOT_ACTIVE", "message": messages[user.status]})
    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        user=UserBrief(id=user.id, name=user.name, email=user.email, is_super_admin=user.is_super_admin, status=user.status.value),
    )


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = []
    for pm in db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all():
        project = db.query(Project).filter(Project.id == pm.project_id).first()
        if project and not project.is_archived:
            memberships.append(ProjectMembershipOut(
                project_id=project.id,
                project_key=project.key,
                project_name=project.name,
                role=pm.project_role.value,
            ))
    return MeResponse(
        id=user.id, name=user.name, email=user.email,
        is_super_admin=user.is_super_admin, status=user.status.value,
        job_title=user.job_title, project_memberships=memberships,
    )
