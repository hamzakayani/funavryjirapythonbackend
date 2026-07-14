from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserStatus
from app.repositories import ProjectMemberRepository, ProjectRepository, UserRepository
from app.schemas import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    ProjectMembershipOut,
    RegisterRequest,
    UpdateProfileRequest,
    UserBrief,
)

MAX_AVATAR_BYTES = 3 * 1024 * 1024
UPLOADS_BASE_PATH = "/jira/uploads"
AVATAR_IMAGE_DIR = "user-avatars"


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
                avatar_url=user.avatar_url,
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
            avatar_url=user.avatar_url,
            project_memberships=memberships,
        )

    def update_profile(self, user: User, data: UpdateProfileRequest) -> MeResponse:
        user.name = data.name.strip()
        user.job_title = data.job_title.strip() if data.job_title else None
        self.users.save()
        self.db.refresh(user)
        return self.me(user)

    async def update_avatar(self, user: User, file: UploadFile) -> MeResponse:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="Only image files can be used as profile photos")

        original_filename = Path(file.filename or "profile-image").name
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            raise HTTPException(status_code=422, detail="Unsupported image type")

        stored_filename = f"{uuid4().hex}{suffix}"
        upload_dir = Path(settings.upload_dir) / AVATAR_IMAGE_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_filename

        size = 0
        try:
            with destination.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_AVATAR_BYTES:
                        out.close()
                        destination.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail="Profile image must be 3 MB or smaller",
                        )
                    out.write(chunk)
        finally:
            await file.close()

        user.avatar_url = f"{UPLOADS_BASE_PATH}/{AVATAR_IMAGE_DIR}/{stored_filename}"
        self.users.save()
        self.db.refresh(user)
        return self.me(user)
