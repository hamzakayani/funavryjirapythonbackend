from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ActivityLog,
    Comment,
    Issue,
    IssueAttachment,
    IssueType,
    Priority,
    ProjectMember,
    Worklog,
)


class IssueRepository:
    def __init__(self, db: Session):
        self.db = db

    def _with_relations(self):
        return self.db.query(Issue).options(
            joinedload(Issue.assignee),
            joinedload(Issue.reporter),
            joinedload(Issue.labels),
        )

    def get_by_id(self, issue_id: int, *, include_archived: bool = False) -> Optional[Issue]:
        q = self.db.query(Issue).filter(Issue.id == issue_id)
        if not include_archived:
            q = q.filter(Issue.is_archived == False)  # noqa: E712
        return q.first()

    def get_by_id_with_relations(
        self, issue_id: int, *, include_archived: bool = False
    ) -> Optional[Issue]:
        q = self._with_relations().filter(Issue.id == issue_id)
        if not include_archived:
            q = q.filter(Issue.is_archived == False)  # noqa: E712
        return q.first()

    def get_detail(self, issue_id: int) -> Optional[Issue]:
        return (
            self.db.query(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
                joinedload(Issue.labels),
                joinedload(Issue.comments).joinedload(Comment.author),
                joinedload(Issue.worklogs).joinedload(Worklog.user),
                joinedload(Issue.attachments).joinedload(IssueAttachment.uploaded_by),
                joinedload(Issue.activities).joinedload(ActivityLog.user),
            )
            .filter(Issue.id == issue_id, Issue.is_archived == False)  # noqa: E712
            .first()
        )

    def get_by_key(self, issue_key: str) -> Optional[Issue]:
        return (
            self.db.query(Issue)
            .options(joinedload(Issue.project))
            .filter(Issue.issue_key == issue_key.upper(), Issue.is_archived == False)  # noqa: E712
            .first()
        )

    def search(self, query: str, user_id: int | None = None, *, limit: int = 10) -> list[Issue]:
        pattern = f"%{query.strip()}%"
        q = (
            self.db.query(Issue)
            .options(joinedload(Issue.project))
            .filter(
                Issue.is_archived == False,  # noqa: E712
                or_(
                    Issue.issue_key.ilike(pattern),
                    Issue.title.ilike(pattern),
                    Issue.description.ilike(pattern),
                ),
            )
        )
        if user_id is not None:
            q = q.join(ProjectMember, ProjectMember.project_id == Issue.project_id).filter(ProjectMember.user_id == user_id)
        return q.order_by(Issue.updated_at.desc()).limit(limit).all()

    def get_in_project(self, issue_id: int, project_id: int) -> Optional[Issue]:
        return (
            self.db.query(Issue)
            .filter(Issue.id == issue_id, Issue.project_id == project_id)
            .first()
        )

    def count_for_project(self, project_id: int) -> int:
        return self.db.query(Issue).filter(Issue.project_id == project_id).count()

    def count_for_sprint(self, sprint_id: int, *, include_archived: bool = False) -> int:
        q = self.db.query(Issue).filter(Issue.sprint_id == sprint_id)
        if not include_archived:
            q = q.filter(Issue.is_archived == False)  # noqa: E712
        return q.count()

    def list_ids_for_sprint(self, sprint_id: int) -> list[int]:
        return [i.id for i in self.db.query(Issue).filter(Issue.sprint_id == sprint_id).all()]

    def next_issue_number(self, project_id: int) -> int:
        last = (
            self.db.query(Issue)
            .filter(Issue.project_id == project_id)
            .order_by(Issue.issue_number.desc())
            .first()
        )
        return (last.issue_number + 1) if last else 1

    def list_epics(self, project_id: int) -> list[Issue]:
        return (
            self._with_relations()
            .filter(
                Issue.project_id == project_id,
                Issue.issue_type == IssueType.Epic,
                Issue.is_archived == False,  # noqa: E712
            )
            .order_by(Issue.backlog_order)
            .all()
        )

    def list_backlog(
        self,
        project_id: int,
        *,
        active_sprint_id: int | None,
        issue_type: str | None = None,
        assignee_id: int | None = None,
        unassigned: bool = False,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[Issue]:
        q = self._with_relations().filter(
            Issue.project_id == project_id,
            Issue.is_archived == False,  # noqa: E712
        )
        if active_sprint_id:
            q = q.filter((Issue.sprint_id == None) | (Issue.sprint_id != active_sprint_id))  # noqa: E711
        else:
            q = q.filter(Issue.sprint_id == None)  # noqa: E711
        q = q.filter(Issue.status != "Done")
        if issue_type:
            q = q.filter(Issue.issue_type == IssueType(issue_type))
        if unassigned:
            q = q.filter(Issue.assignee_id == None)  # noqa: E711
        elif assignee_id is not None:
            q = q.filter(Issue.assignee_id == assignee_id)
        if status:
            q = q.filter(Issue.status == status)
        if priority:
            q = q.filter(Issue.priority == Priority(priority))
        return q.order_by(Issue.backlog_order.asc(), Issue.created_at.asc()).all()

    def list_all_for_project(
        self,
        project_id: int,
        *,
        issue_type: str | None = None,
        assignee_id: int | None = None,
        unassigned: bool = False,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[Issue]:
        q = self._with_relations().filter(
            Issue.project_id == project_id,
            Issue.is_archived == False,  # noqa: E712
        )
        if issue_type:
            q = q.filter(Issue.issue_type == IssueType(issue_type))
        if unassigned:
            q = q.filter(Issue.assignee_id == None)  # noqa: E711
        elif assignee_id is not None:
            q = q.filter(Issue.assignee_id == assignee_id)
        if status:
            q = q.filter(Issue.status == status)
        if priority:
            q = q.filter(Issue.priority == Priority(priority))
        return q.order_by(Issue.backlog_order.asc(), Issue.created_at.asc()).all()

    def list_for_sprint(self, sprint_id: int) -> list[Issue]:
        return (
            self._with_relations()
            .filter(Issue.sprint_id == sprint_id, Issue.is_archived == False)  # noqa: E712
            .all()
        )

    def list_board(
        self,
        sprint_id: int,
        *,
        assignee_id: int | None = None,
        unassigned: bool = False,
        issue_type: str | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[Issue]:
        q = self._with_relations().filter(
            Issue.sprint_id == sprint_id,
            Issue.is_archived == False,  # noqa: E712
            Issue.issue_type != IssueType.Epic,
        )
        if unassigned:
            q = q.filter(Issue.assignee_id == None)  # noqa: E711
        elif assignee_id is not None:
            q = q.filter(Issue.assignee_id == assignee_id)
        if issue_type:
            q = q.filter(Issue.issue_type == IssueType(issue_type))
        if status:
            q = q.filter(Issue.status == status)
        if priority:
            q = q.filter(Issue.priority == Priority(priority))
        return q.all()

    def list_subtasks(self, parent_issue_id: int) -> list[Issue]:
        return (
            self._with_relations()
            .filter(Issue.parent_issue_id == parent_issue_id, Issue.is_archived == False)  # noqa: E712
            .all()
        )

    def get_in_sprint(self, issue_id: int, sprint_id: int) -> Optional[Issue]:
        return (
            self.db.query(Issue)
            .filter(Issue.id == issue_id, Issue.sprint_id == sprint_id)
            .first()
        )

    def create(self, issue: Issue) -> Issue:
        self.db.add(issue)
        self.db.flush()
        return issue

    def save(self) -> None:
        self.db.commit()

    def refresh(self, issue: Issue) -> Issue:
        self.db.refresh(issue)
        return issue
