from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_title: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserBrief(BaseModel):
    id: int
    name: str
    email: str
    is_super_admin: bool
    status: str

    class Config:
        from_attributes = True


class ProjectMembershipOut(BaseModel):
    project_id: int
    project_key: str
    project_name: str
    role: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    is_super_admin: bool
    status: str
    job_title: Optional[str] = None
    project_memberships: List[ProjectMembershipOut] = []

    class Config:
        from_attributes = True
