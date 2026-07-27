from typing import Optional

from pydantic import BaseModel


class UserListItem(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None

    class Config:
        from_attributes = True
