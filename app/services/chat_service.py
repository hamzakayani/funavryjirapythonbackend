from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import can_manage_project, require_project_access
from app.models import ChatAttachment, ChatMessage, ChatMessageMention
from app.repositories import (
    ChatReadRepository,
    ChatRepository,
    IssueRepository,
    ProjectMemberRepository,
    ProjectRepository,
)
from app.schemas import (
    ChatAttachmentOut,
    ChatMentionOut,
    ChatMessageOut,
    ChatProjectSummaryOut,
    ChatUnreadOut,
    MentionIn,
    UserMini,
)
from app.services.notification_service import NotificationService

DELETED_PLACEHOLDER = "[message deleted]"
MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024
CHAT_ATTACHMENT_DIR = "chat-attachments"


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.chats = ChatRepository(db)
        self.reads = ChatReadRepository(db)
        self.projects = ProjectRepository(db)
        self.members = ProjectMemberRepository(db)
        self.issues = IssueRepository(db)
        self.notifications = NotificationService(db)

    def _get_project_by_key_or_404(self, project_key: str):
        project = self.projects.get_by_key(project_key)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def _resolve_valid_mentions(self, project_id: int, mentions: list[MentionIn]) -> list[ChatMessageMention]:
        resolved: list[ChatMessageMention] = []
        for mention in mentions:
            if mention.type == "user":
                if self.members.get(project_id, mention.id) is not None:
                    resolved.append(ChatMessageMention(mentioned_user_id=mention.id))
            elif mention.type == "issue":
                issue = self.issues.get_by_id(mention.id, include_archived=True)
                if issue and issue.project_id == project_id:
                    resolved.append(ChatMessageMention(mentioned_issue_id=mention.id))
        return resolved

    def _mention_to_out(self, mention: ChatMessageMention) -> ChatMentionOut:
        if mention.mentioned_user_id is not None:
            return ChatMentionOut(
                type="user", id=mention.mentioned_user_id, label=mention.mentioned_user.name
            )
        return ChatMentionOut(
            type="issue", id=mention.mentioned_issue_id, label=mention.mentioned_issue.issue_key
        )

    def _attachment_to_out(self, attachment, project_key: str) -> ChatAttachmentOut:
        return ChatAttachmentOut(
            id=attachment.id,
            original_filename=attachment.original_filename,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
            file_url=f"/api/v1/projects/{project_key}/chat/attachments/{attachment.id}/download",
            created_at=attachment.created_at,
        )

    def _message_to_out(
        self, message: ChatMessage, *, mask_deleted: bool, project_key: str
    ) -> ChatMessageOut:
        masked = mask_deleted and message.is_deleted
        return ChatMessageOut(
            id=message.id,
            project_id=message.project_id,
            author=UserMini(
                id=message.author.id, name=message.author.name, avatar_url=message.author.avatar_url
            ),
            body=DELETED_PLACEHOLDER if masked else message.body,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
            mentions=[] if masked else [self._mention_to_out(m) for m in message.mentions],
            attachments=(
                []
                if masked
                else [self._attachment_to_out(a, project_key) for a in message.attachments]
            ),
            created_at=message.created_at,
            updated_at=message.updated_at,
            deleted_at=message.deleted_at,
        )

    def list_messages(
        self, project_key: str, user, *, before_id: int | None, limit: int
    ) -> list[ChatMessageOut]:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        messages = self.chats.list_for_project(project.id, before_id=before_id, limit=limit)
        return [self._message_to_out(m, mask_deleted=True, project_key=project.key) for m in messages]

    def create_message(
        self, project_key: str, user, text: str, mentions: list[MentionIn]
    ) -> ChatMessageOut:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)

        message = ChatMessage(project_id=project.id, author_id=user.id, body=text)
        message.mentions = self._resolve_valid_mentions(project.id, mentions)
        self.chats.create(message)

        for mention in message.mentions:
            if mention.mentioned_user_id:
                self.notifications.notify_chat_mention(project, user, mention.mentioned_user_id)

        self.chats.save()
        self.chats.refresh(message)
        return self._message_to_out(message, mask_deleted=False, project_key=project.key)

    def edit_message(
        self, project_key: str, message_id: int, user, text: str, mentions: list[MentionIn]
    ) -> ChatMessageOut:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        message = self.chats.get_by_id(message_id, project.id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.author_id != user.id:
            raise HTTPException(status_code=403, detail="Only the author can edit this message")

        previously_mentioned_user_ids = {
            m.mentioned_user_id for m in message.mentions if m.mentioned_user_id
        }
        message.body = text
        message.is_edited = True
        message.mentions = self._resolve_valid_mentions(project.id, mentions)

        for mention in message.mentions:
            if mention.mentioned_user_id and mention.mentioned_user_id not in previously_mentioned_user_ids:
                self.notifications.notify_chat_mention(project, user, mention.mentioned_user_id)

        self.chats.save()
        self.chats.refresh(message)
        return self._message_to_out(message, mask_deleted=False, project_key=project.key)

    def delete_message(self, project_key: str, message_id: int, user) -> ChatMessageOut:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        message = self.chats.get_by_id(message_id, project.id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Message not found")

        is_own = message.author_id == user.id
        if not (is_own or can_manage_project(self.db, user, project.id)):
            raise HTTPException(status_code=403, detail="Cannot delete this message")

        message.is_deleted = True
        message.deleted_at = datetime.utcnow()
        self.chats.save()
        self.chats.refresh(message)
        return self._message_to_out(message, mask_deleted=True, project_key=project.key)

    def mark_read(self, project_key: str, user) -> None:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        latest_id = self.chats.latest_message_id(project.id)
        self.reads.upsert(project.id, user.id, latest_id)
        self.reads.save()

    def get_unread_status(self, project_key: str, user) -> ChatUnreadOut:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        latest_id = self.chats.latest_message_id(project.id)
        if latest_id is None:
            return ChatUnreadOut(has_unread=False)
        read_state = self.reads.get(project.id, user.id)
        last_read_id = read_state.last_read_message_id if read_state else None
        has_unread = last_read_id is None or last_read_id < latest_id
        return ChatUnreadOut(has_unread=has_unread)

    def get_message_out(self, project_key: str, message_id: int) -> ChatMessageOut:
        project = self._get_project_by_key_or_404(project_key)
        message = self.chats.get_by_id(message_id, project.id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return self._message_to_out(message, mask_deleted=False, project_key=project.key)

    async def add_attachment(
        self, project_key: str, message_id: int, file: UploadFile, user
    ) -> ChatAttachmentOut:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)
        message = self.chats.get_by_id(message_id, project.id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.author_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the author can attach files to this message"
            )

        original_filename = Path(file.filename or "file").name
        suffix = Path(original_filename).suffix
        stored_filename = f"{uuid4().hex}{suffix}"
        upload_dir = Path(settings.upload_dir) / CHAT_ATTACHMENT_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_filename

        size = 0
        try:
            with destination.open("wb") as out_file:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_CHAT_ATTACHMENT_BYTES:
                        out_file.close()
                        destination.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413, detail="Attachment must be 10 MB or smaller"
                        )
                    out_file.write(chunk)
        finally:
            await file.close()

        attachment = ChatAttachment(
            message_id=message.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=file.content_type or "application/octet-stream",
            file_size=size,
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return self._attachment_to_out(attachment, project.key)

    def get_attachment_file(
        self, project_key: str, attachment_id: int, user
    ) -> tuple[Path, str, str]:
        project = self._get_project_by_key_or_404(project_key)
        require_project_access(self.db, user, project.id)

        attachment = (
            self.db.query(ChatAttachment)
            .join(ChatMessage, ChatAttachment.message_id == ChatMessage.id)
            .filter(ChatAttachment.id == attachment_id, ChatMessage.project_id == project.id)
            .first()
        )
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        path = Path(settings.upload_dir) / CHAT_ATTACHMENT_DIR / attachment.stored_filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Attachment not found")

        return path, attachment.original_filename, attachment.content_type

    def list_projects_for_admin(self) -> list[ChatProjectSummaryOut]:
        return [
            ChatProjectSummaryOut(
                id=project.id,
                key=project.key,
                name=project.name,
                last_message_at=self.chats.last_message_at(project.id),
            )
            for project in self.projects.list_all()
        ]

    def list_messages_for_admin(
        self, project_id: int, *, before_id: int | None, limit: int
    ) -> list[ChatMessageOut]:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        messages = self.chats.list_for_project(project.id, before_id=before_id, limit=limit)
        return [self._message_to_out(m, mask_deleted=False, project_key=project.key) for m in messages]
