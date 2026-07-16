import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.issue import IssueDetailOut

# Letters (incl. common accented ranges), spaces, hyphens, apostrophes, periods.
NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ' .-]{1,79}$")


class SpectatorViewRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not NAME_PATTERN.match(value):
            raise ValueError("Enter your full name using letters only.")
        return value


class SpectatorViewOut(BaseModel):
    issue: IssueDetailOut
    views_used: int
    views_remaining: int
    view_limit: int
