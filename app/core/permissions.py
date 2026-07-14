from typing import Optional

from sqlalchemy.orm import Session

from app.models import ProjectMember, User
from app.repositories import ProjectMemberRepository


def get_project_membership(db: Session, user: User, project_id: int) -> Optional[ProjectMember]:
    if user.is_super_admin:
        return None
    return ProjectMemberRepository(db).get(project_id, user.id)


def can_manage_project(db: Session, user: User, project_id: int) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, project_id)
    return membership is not None and membership.project_role.value == "Lead"


def can_edit_issue(db: Session, user: User, issue) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return issue.reporter_id == user.id or issue.assignee_id == user.id


def can_change_issue_status(db: Session, user: User, issue) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return issue.assignee_id == user.id


def can_assign_issue(db: Session, user: User, issue, assignee_id: int | None) -> bool:
    if user.is_super_admin:
        return True
    membership = get_project_membership(db, user, issue.project_id)
    if membership and membership.project_role.value == "Lead":
        return True
    return assignee_id == user.id or (assignee_id is None and issue.assignee_id == user.id)
