from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserStatus
from app.repositories import ProjectMemberRepository, ProjectRepository, UserRepository
from app.schemas import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    ProjectMembershipOut,
    RegisterRequest,
    UserBrief,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.members = ProjectMemberRepository(db)
        self.projects = ProjectRepository(db)

    def register(self, data: RegisterRequest) -> dict:
        if self.users.get_by_email(data.email):
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        user = User(
            name=data.name,
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            job_title=data.job_title,
            status=UserStatus.Pending,
        )
        self.users.create(user)
        self.users.save()
        return {"message": "Registration submitted. Awaiting approval.", "status": "Pending"}

    def login(self, data: LoginRequest) -> AuthResponse:
        user = self.users.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if user.status != UserStatus.Active:
            messages = {
                UserStatus.Pending: "Your account is awaiting approval.",
                UserStatus.Rejected: "Your registration was not approved.",
                UserStatus.Suspended: "Your account has been suspended. Contact your administrator.",
            }
            raise HTTPException(
                status_code=403,
                detail={"code": "ACCOUNT_NOT_ACTIVE", "message": messages[user.status]},
            )
        return AuthResponse(
            access_token=create_access_token(user.id),
            user=UserBrief(
                id=user.id,
                name=user.name,
                email=user.email,
                is_super_admin=user.is_super_admin,
                status=user.status.value,
            ),
        )

    def me(self, user: User) -> MeResponse:
        memberships = []
        for pm in self.members.list_for_user(user.id):
            project = self.projects.get_by_id(pm.project_id)
            if project and not project.is_archived:
                memberships.append(
                    ProjectMembershipOut(
                        project_id=project.id,
                        project_key=project.key,
                        project_name=project.name,
                        role=pm.project_role.value,
                    )
                )
        return MeResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_super_admin=user.is_super_admin,
            status=user.status.value,
            job_title=user.job_title,
            project_memberships=memberships,
        )
