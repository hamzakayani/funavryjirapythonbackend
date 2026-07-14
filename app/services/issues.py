from sqlalchemy.orm import Session

from app.models import ActivityLog, Issue, IssueLabel


def log_activity(
    db: Session,
    issue_id: int,
    user_id: int,
    action: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
):
    entry = ActivityLog(
        issue_id=issue_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)


def get_next_issue_number(db: Session, project_id: int) -> int:
    last = db.query(Issue).filter(Issue.project_id == project_id).order_by(Issue.issue_number.desc()).first()
    return (last.issue_number + 1) if last else 1


def get_time_logged(db: Session, issue_id: int) -> int:
    from app.models import Worklog
    from sqlalchemy import func
    result = db.query(func.coalesce(func.sum(Worklog.time_spent_minutes), 0)).filter(
        Worklog.issue_id == issue_id
    ).scalar()
    return int(result or 0)


def issue_to_out(issue: Issue, db: Session) -> dict:
    from app.schemas import IssueOut, UserMini
    labels = [l.label for l in issue.labels]
    return IssueOut(
        id=issue.id,
        issue_key=issue.issue_key,
        title=issue.title,
        description=issue.description,
        issue_type=issue.issue_type.value,
        priority=issue.priority.value,
        status=issue.status.value,
        assignee=UserMini(id=issue.assignee.id, name=issue.assignee.name) if issue.assignee else None,
        reporter=UserMini(id=issue.reporter.id, name=issue.reporter.name),
        sprint_id=issue.sprint_id,
        parent_issue_id=issue.parent_issue_id,
        story_points=issue.story_points,
        original_estimate_minutes=issue.original_estimate_minutes,
        remaining_estimate_minutes=issue.remaining_estimate_minutes,
        time_logged_minutes=get_time_logged(db, issue.id),
        due_date=issue.due_date,
        labels=labels,
        backlog_order=issue.backlog_order,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


def sync_labels(db: Session, issue: Issue, labels: list[str]):
    db.query(IssueLabel).filter(IssueLabel.issue_id == issue.id).delete()
    for label in labels:
        db.add(IssueLabel(issue_id=issue.id, label=label[:50]))
