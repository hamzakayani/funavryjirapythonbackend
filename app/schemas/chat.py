from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.issue import UserMini
from app.schemas.types import UTCDateTime


class MentionIn(BaseModel):
    type: Literal["user", "issue"]
    id: int


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    mentions: list[MentionIn] = []


class EditMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    mentions: list[MentionIn] = []


class ChatMentionOut(BaseModel):
    type: Literal["user", "issue"]
    id: int
    label: str


class ChatAttachmentOut(BaseModel):
    id: int
    original_filename: str
    content_type: str
    file_size: int
    file_url: str
    created_at: UTCDateTime

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    project_id: int
    author: UserMini
    body: str
    is_edited: bool
    is_deleted: bool
    mentions: list[ChatMentionOut] = []
    attachments: list[ChatAttachmentOut] = []
    created_at: UTCDateTime
    updated_at: UTCDateTime

    class Config:
        from_attributes = True


class ChatProjectSummaryOut(BaseModel):
    id: int
    key: str
    name: str
    last_message_at: Optional[UTCDateTime] = None
