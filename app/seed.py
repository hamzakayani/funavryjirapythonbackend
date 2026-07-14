"""Seed demo users, project, and sample issues for local development."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import (
    User, UserStatus, Project, ProjectMember, ProjectRole,
    Sprint, SprintStatus, Issue, IssueType, IssueStatus, Priority,
)
from app.services.issues import log_activity, get_next_issue_number


DEMO_USERS = [
    {
        "name": "Super Admin",
        "email": "admin@example.com",
        "password": "admin123",
        "job_title": "System Administrator",
        "status": UserStatus.Active,
        "is_super_admin": True,
    },
    {
        "name": "Jordan Lead",
        "email": "jordan.lead@example.com",
        "password": "demo123",
        "job_title": "Scrum Master",
        "status": UserStatus.Active,
        "is_super_admin": False,
    },
    {
        "name": "Sam Member",
        "email": "sam.member@example.com",
        "password": "demo123",
        "job_title": "Software Engineer",
        "status": UserStatus.Active,
        "is_super_admin": False,
    },
    {
        "name": "Alex Developer",
        "email": "alex.dev@example.com",
        "password": "demo123",
        "job_title": "Frontend Developer",
        "status": UserStatus.Active,
        "is_super_admin": False,
    },
    {
        "name": "Taylor Pending",
        "email": "taylor.pending@example.com",
        "password": "demo123",
        "job_title": "QA Engineer",
        "status": UserStatus.Pending,
        "is_super_admin": False,
    },
    {
        "name": "Riley Rejected",
        "email": "riley.rejected@example.com",
        "password": "demo123",
        "job_title": "Contractor",
        "status": UserStatus.Rejected,
        "is_super_admin": False,
        "rejection_reason": "Not part of the organization.",
    },
    {
        "name": "Casey Suspended",
        "email": "casey.suspended@example.com",
        "password": "demo123",
        "job_title": "Designer",
        "status": UserStatus.Suspended,
        "is_super_admin": False,
    },
]


def _get_or_create_user(db: Session, data: dict) -> User:
    user = db.query(User).filter(User.email == data["email"]).first()
    if user:
        return user
    user = User(
        name=data["name"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        job_title=data.get("job_title"),
        status=data["status"],
        is_super_admin=data.get("is_super_admin", False),
        rejection_reason=data.get("rejection_reason"),
    )
    db.add(user)
    db.flush()
    return user


def _add_member(db: Session, project_id: int, user_id: int, role: ProjectRole):
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not existing:
        db.add(ProjectMember(project_id=project_id, user_id=user_id, project_role=role))


def _create_issue(
    db: Session,
    project: Project,
    reporter_id: int,
    *,
    title: str,
    issue_type: IssueType,
    issue_number: int,
    assignee_id: int | None = None,
    sprint_id: int | None = None,
    parent_issue_id: int | None = None,
    status: IssueStatus = IssueStatus.ToDo,
    priority: Priority = Priority.Medium,
    story_points: int | None = None,
    backlog_order: int = 0,
    description: str | None = None,
) -> Issue:
    issue = Issue(
        project_id=project.id,
        issue_number=issue_number,
        issue_key=f"{project.key}-{issue_number}",
        title=title,
        description=description,
        issue_type=issue_type,
        priority=priority,
        status=status,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        sprint_id=sprint_id,
        parent_issue_id=parent_issue_id,
        story_points=story_points,
        backlog_order=backlog_order,
    )
    db.add(issue)
    db.flush()
    log_activity(db, issue.id, reporter_id, "created")
    return issue


def seed_demo_data(db: Session):
    users = {u["email"]: _get_or_create_user(db, u) for u in DEMO_USERS}
    admin = users["admin@example.com"]
    lead = users["jordan.lead@example.com"]
    member = users["sam.member@example.com"]
    dev = users["alex.dev@example.com"]

    project = db.query(Project).filter(Project.key == "ENG").first()
    if not project:
        project = Project(
            key="ENG",
            name="Engineering Platform",
            description="Core platform development — backlog, sprints, and board demo project.",
            created_by=admin.id,
        )
        db.add(project)
        db.flush()
    else:
        project.name = "Engineering Platform"
        project.description = "Core platform development — backlog, sprints, and board demo project."

    _add_member(db, project.id, lead.id, ProjectRole.Lead)
    _add_member(db, project.id, member.id, ProjectRole.Member)
    _add_member(db, project.id, dev.id, ProjectRole.Member)

    issue_count = db.query(Issue).filter(Issue.project_id == project.id).count()
    if issue_count >= 5:
        db.commit()
        return

    today = date.today()
    active_sprint = db.query(Sprint).filter(
        Sprint.project_id == project.id, Sprint.status == SprintStatus.Active
    ).first()
    if not active_sprint:
        active_sprint = Sprint(
            project_id=project.id,
            name="Sprint 1 — Foundation",
            goal="Deliver authentication and project workspace MVP",
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7),
            status=SprintStatus.Active,
        )
        db.add(active_sprint)
    planned_sprint = db.query(Sprint).filter(
        Sprint.project_id == project.id, Sprint.status == SprintStatus.Planned
    ).first()
    if not planned_sprint:
        planned_sprint = Sprint(
            project_id=project.id,
            name="Sprint 2 — Board & Backlog",
            goal="Complete drag-and-drop board and backlog grooming",
            start_date=today + timedelta(days=8),
            end_date=today + timedelta(days=22),
            status=SprintStatus.Planned,
        )
        db.add(planned_sprint)
    db.flush()

    start_num = get_next_issue_number(db, project.id)

    epic = _create_issue(
        db, project, lead.id,
        title="User Management & Onboarding",
        issue_type=IssueType.Epic,
        issue_number=start_num,
        description="Epic covering registration, approval workflow, and role-based access.",
        story_points=13,
        backlog_order=0,
    )

    story1 = _create_issue(
        db, project, lead.id,
        title="Implement Super Admin user approval queue",
        issue_type=IssueType.Story,
        issue_number=start_num + 1,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        parent_issue_id=epic.id,
        status=IssueStatus.InProgress,
        priority=Priority.High,
        story_points=5,
        backlog_order=1,
    )

    _create_issue(
        db, project, lead.id,
        title="Add project member assignment UI",
        issue_type=IssueType.Story,
        issue_number=start_num + 2,
        assignee_id=dev.id,
        sprint_id=active_sprint.id,
        parent_issue_id=epic.id,
        status=IssueStatus.ToDo,
        story_points=3,
        backlog_order=2,
    )

    _create_issue(
        db, project, member.id,
        title="Write unit tests for auth endpoints",
        issue_type=IssueType.SubTask,
        issue_number=start_num + 3,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        parent_issue_id=story1.id,
        status=IssueStatus.InReview,
        story_points=2,
        backlog_order=3,
    )

    _create_issue(
        db, project, lead.id,
        title="Fix login error message for suspended users",
        issue_type=IssueType.Bug,
        issue_number=start_num + 4,
        assignee_id=dev.id,
        sprint_id=active_sprint.id,
        status=IssueStatus.ToDo,
        priority=Priority.Highest,
        story_points=1,
        backlog_order=4,
    )

    _create_issue(
        db, project, lead.id,
        title="Set up CI pipeline",
        issue_type=IssueType.Task,
        issue_number=start_num + 5,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        status=IssueStatus.Done,
        story_points=2,
        backlog_order=5,
    )

    _create_issue(
        db, project, lead.id,
        title="Design sprint completion flow",
        issue_type=IssueType.Story,
        issue_number=start_num + 6,
        sprint_id=planned_sprint.id,
        status=IssueStatus.ToDo,
        story_points=5,
        backlog_order=6,
    )

    _create_issue(
        db, project, lead.id,
        title="Add global issue key search",
        issue_type=IssueType.Task,
        issue_number=start_num + 7,
        status=IssueStatus.ToDo,
        story_points=2,
        backlog_order=7,
    )

    db.commit()
