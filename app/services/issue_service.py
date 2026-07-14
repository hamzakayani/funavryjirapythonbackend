from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import (
    can_assign_issue,
    can_change_issue_status,
    can_edit_issue,
    can_manage_project,
    require_project_access,
)
from app.models import Comment, Issue, IssueAttachment, IssueStatus, IssueType, Priority, User, Worklog
from app.repositories import (
    ActivityLogRepository,
    CommentRepository,
    IssueLabelRepository,
    IssueRepository,
    SprintRepository,
    WorklogRepository,
)
from app.schemas import (
    ActivityOut,
    BoardResponse,
    CommentOut,
    CommentRequest,
    CreateIssueRequest,
    IssueAttachmentOut,
    IssueDetailOut,
    IssueOut,
    ReorderBacklogRequest,
    SearchResult,
    SprintOut,
    UpdateIssueRequest,
    UserMini,
    WorklogOut,
    WorklogRequest,
)
from app.services.project_service import ProjectService

STATUSES = ["To Do", "In Progress", "In Review", "Done"]
MAX_REFERENCE_IMAGE_BYTES = 5 * 1024 * 1024
UPLOADS_BASE_PATH = "/jira/uploads"
REFERENCE_IMAGE_DIR = "issue-attachments"


class IssueService:
    def __init__(self, db: Session):
        self.db = db
        self.issues = IssueRepository(db)
        self.sprints = SprintRepository(db)
        self.labels = IssueLabelRepository(db)
        self.comments = CommentRepository(db)
        self.worklogs = WorklogRepository(db)
        self.activities = ActivityLogRepository(db)
        self.projects = ProjectService(db)

    def issue_to_out(self, issue: Issue) -> IssueOut:
        return IssueOut(
            id=issue.id,
            issue_key=issue.issue_key,
            title=issue.title,
            description=issue.description,
            issue_type=issue.issue_type.value,
            priority=issue.priority.value,
            status=issue.status.value,
            assignee=UserMini(id=issue.assignee.id, name=issue.assignee.name, avatar_url=issue.assignee.avatar_url) if issue.assignee else None,
            reporter=UserMini(id=issue.reporter.id, name=issue.reporter.name, avatar_url=issue.reporter.avatar_url),
            sprint_id=issue.sprint_id,
            parent_issue_id=issue.parent_issue_id,
            story_points=issue.story_points,
            original_estimate_minutes=issue.original_estimate_minutes,
            remaining_estimate_minutes=issue.remaining_estimate_minutes,
            time_logged_minutes=self.worklogs.sum_for_issue(issue.id),
            due_date=issue.due_date,
            labels=[l.label for l in issue.labels],
            backlog_order=issue.backlog_order,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    def attachment_to_out(self, attachment: IssueAttachment) -> IssueAttachmentOut:
        return IssueAttachmentOut(
            id=attachment.id,
            original_filename=attachment.original_filename,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
            file_url=f"{UPLOADS_BASE_PATH}/{REFERENCE_IMAGE_DIR}/{attachment.stored_filename}",
            uploaded_by=UserMini(id=attachment.uploaded_by.id, name=attachment.uploaded_by.name, avatar_url=attachment.uploaded_by.avatar_url),
            created_at=attachment.created_at,
        )

    def search(self, key: str, user: User) -> SearchResult:
        issue = self.issues.get_by_key(key.strip())
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        return SearchResult(
            id=issue.id,
            issue_key=issue.issue_key,
            title=issue.title,
            project_key=issue.project.key,
            project_name=issue.project.name,
            status=issue.status.value,
            issue_type=issue.issue_type.value,
        )

    def list_epics(self, project_key: str, user: User) -> list[IssueOut]:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        return [self.issue_to_out(e) for e in self.issues.list_epics(project.id)]

    def get_backlog(
        self,
        project_key: str,
        user: User,
        *,
        issue_type: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
    ) -> list[IssueOut]:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        active = self.sprints.get_active(project.id)
        assignee_id = None
        unassigned = False
        if assignee == "me":
            assignee_id = user.id
        elif assignee == "unassigned":
            unassigned = True
        issues = self.issues.list_backlog(
            project.id,
            active_sprint_id=active.id if active else None,
            issue_type=issue_type,
            assignee_id=assignee_id,
            unassigned=unassigned,
            status=status,
        )
        return [self.issue_to_out(i) for i in issues]

    def reorder_backlog(self, project_key: str, data: ReorderBacklogRequest, user: User) -> dict:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Cannot reorder backlog")
        for idx, issue_id in enumerate(data.issue_ids):
            issue = self.issues.get_in_project(issue_id, project.id)
            if issue:
                issue.backlog_order = idx
        self.issues.save()
        return {"message": "Backlog reordered"}

    def get_board(
        self,
        project_key: str,
        user: User,
        *,
        assignee: str | None = None,
        issue_type: str | None = None,
    ) -> BoardResponse:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        active_sprint = self.sprints.get_active(project.id)
        columns = {s: [] for s in STATUSES}
        sprint_out = None
        if active_sprint:
            sprint_out = SprintOut(
                id=active_sprint.id,
                name=active_sprint.name,
                goal=active_sprint.goal,
                start_date=active_sprint.start_date,
                end_date=active_sprint.end_date,
                status=active_sprint.status.value,
                issue_count=self.issues.count_for_sprint(active_sprint.id, include_archived=True),
            )
            assignee_id = user.id if assignee == "me" else None
            for issue in self.issues.list_board(
                active_sprint.id, assignee_id=assignee_id, issue_type=issue_type
            ):
                out = self.issue_to_out(issue)
                if issue.status.value in columns:
                    columns[issue.status.value].append(out.model_dump())
        return BoardResponse(sprint=sprint_out, columns=columns)

    def sprint_issues(self, sprint_id: int, user: User) -> list[IssueOut]:
        sprint = self.sprints.get_by_id(sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")
        require_project_access(self.db, user, sprint.project_id)
        return [self.issue_to_out(i) for i in self.issues.list_for_sprint(sprint.id)]

    def create_issue(self, project_key: str, data: CreateIssueRequest, user: User) -> IssueOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if data.issue_type == "Sub-task" and not data.parent_issue_id:
            raise HTTPException(status_code=422, detail="Sub-task requires a parent issue")
        num = self.issues.next_issue_number(project.id)
        issue = Issue(
            project_id=project.id,
            issue_number=num,
            issue_key=f"{project.key}-{num}",
            title=data.title,
            description=data.description,
            issue_type=IssueType(data.issue_type),
            priority=Priority(data.priority),
            assignee_id=data.assignee_id,
            reporter_id=user.id,
            sprint_id=data.sprint_id,
            parent_issue_id=data.parent_issue_id,
            story_points=data.story_points,
            original_estimate_minutes=data.original_estimate_minutes,
            remaining_estimate_minutes=data.original_estimate_minutes,
            due_date=data.due_date,
            backlog_order=self.issues.count_for_project(project.id),
        )
        self.issues.create(issue)
        self.activities.create(issue_id=issue.id, user_id=user.id, action="created")
        self.issues.save()
        issue = self.issues.get_by_id_with_relations(issue.id)
        return self.issue_to_out(issue)

    def get_issue(self, issue_id: int, user: User) -> IssueDetailOut:
        issue = self.issues.get_detail(issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        base = self.issue_to_out(issue)
        comments = [
            CommentOut(
                id=c.id,
                body=c.body,
                author=UserMini(id=c.author.id, name=c.author.name, avatar_url=c.author.avatar_url),
                created_at=c.created_at,
            )
            for c in sorted(issue.comments, key=lambda x: x.created_at)
        ]
        worklogs = [
            WorklogOut(
                id=w.id,
                date_worked=w.date_worked,
                time_spent_minutes=w.time_spent_minutes,
                description=w.description,
                user=UserMini(id=w.user.id, name=w.user.name, avatar_url=w.user.avatar_url),
                created_at=w.created_at,
            )
            for w in sorted(issue.worklogs, key=lambda x: x.created_at, reverse=True)
        ]
        attachments = [
            self.attachment_to_out(a)
            for a in sorted(issue.attachments, key=lambda x: x.created_at, reverse=True)
        ]
        activities = [
            ActivityOut(
                id=a.id,
                action=a.action,
                field_name=a.field_name,
                old_value=a.old_value,
                new_value=a.new_value,
                user=UserMini(id=a.user.id, name=a.user.name, avatar_url=a.user.avatar_url),
                created_at=a.created_at,
            )
            for a in sorted(issue.activities, key=lambda x: x.created_at, reverse=True)
        ]
        parent_out = None
        if issue.parent_issue_id:
            parent = self.issues.get_by_id_with_relations(
                issue.parent_issue_id, include_archived=True
            )
            if parent:
                parent_out = self.issue_to_out(parent)
        return IssueDetailOut(
            **base.model_dump(),
            comments=comments,
            worklogs=worklogs,
            attachments=attachments,
            activities=activities,
            subtasks=[self.issue_to_out(s) for s in self.issues.list_subtasks(issue.id)],
            parent=parent_out,
        )

    def update_issue(self, issue_id: int, data: UpdateIssueRequest, user: User) -> IssueOut:
        issue = self.issues.get_by_id(issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)

        if data.status is not None:
            if not can_change_issue_status(self.db, user, issue):
                raise HTTPException(status_code=403, detail="Cannot change status")
            old = issue.status.value
            issue.status = IssueStatus(data.status)
            self.activities.create(
                issue_id=issue.id,
                user_id=user.id,
                action="field_changed",
                field_name="status",
                old_value=old,
                new_value=issue.status.value,
            )
        elif not can_edit_issue(self.db, user, issue):
            raise HTTPException(status_code=403, detail="Cannot edit issue")

        if "assignee_id" in data.model_dump(exclude_unset=True):
            if not can_assign_issue(self.db, user, issue, data.assignee_id):
                raise HTTPException(status_code=403, detail="Cannot assign this issue")

        field_map = {
            "title": ("title", lambda v: v),
            "description": ("description", lambda v: v),
            "priority": ("priority", lambda v: Priority(v)),
            "assignee_id": ("assignee_id", lambda v: v),
            "sprint_id": ("sprint_id", lambda v: v),
            "parent_issue_id": ("parent_issue_id", lambda v: v),
            "story_points": ("story_points", lambda v: v),
            "original_estimate_minutes": ("original_estimate_minutes", lambda v: v),
            "remaining_estimate_minutes": ("remaining_estimate_minutes", lambda v: v),
            "due_date": ("due_date", lambda v: v),
        }
        updates = data.model_dump(exclude_unset=True, exclude={"status", "labels", "issue_type"})
        for field, (attr, conv) in field_map.items():
            if field in updates:
                old_val = getattr(issue, attr)
                new_val = conv(updates[field])
                if old_val != new_val:
                    setattr(issue, attr, new_val)
                    self.activities.create(
                        issue_id=issue.id,
                        user_id=user.id,
                        action="field_changed",
                        field_name=field,
                        old_value=str(old_val),
                        new_value=str(new_val),
                    )

        if data.labels is not None:
            self.labels.replace_for_issue(issue, data.labels)

        self.issues.save()
        issue = self.issues.get_by_id_with_relations(issue.id)
        return self.issue_to_out(issue)

    def assign_to_me(self, issue_id: int, user: User) -> dict:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        old = issue.assignee_id
        issue.assignee_id = user.id
        self.activities.create(
            issue_id=issue.id,
            user_id=user.id,
            action="field_changed",
            field_name="assignee_id",
            old_value=str(old),
            new_value=str(user.id),
        )
        self.issues.save()
        return {"message": "Assigned to you"}

    def archive_issue(self, issue_id: int, user: User) -> dict:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        if not can_manage_project(self.db, user, issue.project_id):
            raise HTTPException(status_code=403, detail="Cannot archive issue")
        issue.is_archived = True
        self.issues.save()
        return {"message": "Issue archived"}

    def add_comment(self, issue_id: int, data: CommentRequest, user: User) -> CommentOut:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        comment = Comment(issue_id=issue.id, author_id=user.id, body=data.body)
        self.comments.create(comment)
        self.activities.create(issue_id=issue.id, user_id=user.id, action="comment_added")
        self.comments.save()
        self.comments.refresh(comment)
        return CommentOut(
            id=comment.id,
            body=comment.body,
            author=UserMini(id=user.id, name=user.name, avatar_url=user.avatar_url),
            created_at=comment.created_at,
        )

    def add_worklog(self, issue_id: int, data: WorklogRequest, user: User) -> WorklogOut:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        if not can_edit_issue(self.db, user, issue) and issue.assignee_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot log time on this issue")
        if data.date_worked > date.today():
            raise HTTPException(status_code=422, detail="Cannot log time for future dates")
        wl = Worklog(
            issue_id=issue.id,
            user_id=user.id,
            date_worked=data.date_worked,
            time_spent_minutes=data.time_spent_minutes,
            description=data.description,
        )
        self.worklogs.create(wl)
        self.activities.create(
            issue_id=issue.id,
            user_id=user.id,
            action="worklog_added",
            new_value=f"{data.time_spent_minutes}m",
        )
        self.worklogs.save()
        self.worklogs.refresh(wl)
        return WorklogOut(
            id=wl.id,
            date_worked=wl.date_worked,
            time_spent_minutes=wl.time_spent_minutes,
            description=wl.description,
            user=UserMini(id=user.id, name=user.name, avatar_url=user.avatar_url),
            created_at=wl.created_at,
        )

    async def add_attachment(
        self, issue_id: int, file: UploadFile, user: User
    ) -> IssueAttachmentOut:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        if not can_edit_issue(self.db, user, issue):
            raise HTTPException(status_code=403, detail="Cannot attach images to this issue")
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="Only image files can be attached")

        original_filename = Path(file.filename or "reference-image").name
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            raise HTTPException(status_code=422, detail="Unsupported image type")

        stored_filename = f"{uuid4().hex}{suffix}"
        upload_dir = Path(settings.upload_dir) / REFERENCE_IMAGE_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_filename

        size = 0
        try:
            with destination.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_REFERENCE_IMAGE_BYTES:
                        out.close()
                        destination.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail="Reference image must be 5 MB or smaller",
                        )
                    out.write(chunk)
        finally:
            await file.close()

        attachment = IssueAttachment(
            issue_id=issue.id,
            uploaded_by_id=user.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=file.content_type,
            file_size=size,
        )
        self.db.add(attachment)
        self.activities.create(
            issue_id=issue.id,
            user_id=user.id,
            action="attachment_added",
            new_value=original_filename,
        )
        self.db.commit()
        self.db.refresh(attachment)
        attachment.uploaded_by = user
        return self.attachment_to_out(attachment)

    def delete_attachment(self, issue_id: int, attachment_id: int, user: User) -> dict:
        issue = self.issues.get_by_id(issue_id, include_archived=True)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        require_project_access(self.db, user, issue.project_id)
        if not can_edit_issue(self.db, user, issue):
            raise HTTPException(status_code=403, detail="Cannot remove images from this issue")

        attachment = (
            self.db.query(IssueAttachment)
            .filter(IssueAttachment.id == attachment_id, IssueAttachment.issue_id == issue.id)
            .first()
        )
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        original_filename = attachment.original_filename
        stored_filename = attachment.stored_filename
        self.db.delete(attachment)
        self.activities.create(
            issue_id=issue.id,
            user_id=user.id,
            action="attachment_removed",
            old_value=original_filename,
        )
        self.db.commit()

        attachment_path = Path(settings.upload_dir) / REFERENCE_IMAGE_DIR / stored_filename
        attachment_path.unlink(missing_ok=True)
        return {"message": "Attachment removed"}
