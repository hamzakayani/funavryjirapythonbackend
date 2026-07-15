"""Seed demo users, project, and sample issues for local development."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    DEFAULT_STATUSES,
    Issue,
    IssueStatusDef,
    IssueType,
    Priority,
    Project,
    ProjectRole,
    Sprint,
    SprintStatus,
    User,
    UserStatus,
)
from app.repositories import (
    ActivityLogRepository,
    IssueRepository,
    IssueStatusRepository,
    ProjectMemberRepository,
    ProjectRepository,
    SprintRepository,
    UserRepository,
)

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


def seed_demo_data(db: Session):
    users_repo = UserRepository(db)
    projects_repo = ProjectRepository(db)
    members_repo = ProjectMemberRepository(db)
    sprints_repo = SprintRepository(db)
    issues_repo = IssueRepository(db)
    activities_repo = ActivityLogRepository(db)
    statuses_repo = IssueStatusRepository(db)

    def get_or_create_user(data: dict) -> User:
        user = users_repo.get_by_email(data["email"])
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
        return users_repo.create(user)

    def create_issue(
        project: Project,
        reporter_id: int,
        *,
        title: str,
        issue_type: IssueType,
        issue_number: int,
        assignee_id: int | None = None,
        sprint_id: int | None = None,
        parent_issue_id: int | None = None,
        status: str = "To Do",
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
        issues_repo.create(issue)
        activities_repo.create(issue_id=issue.id, user_id=reporter_id, action="created")
        return issue

    users = {u["email"]: get_or_create_user(u) for u in DEMO_USERS}
    admin = users["admin@example.com"]
    lead = users["jordan.lead@example.com"]
    member = users["sam.member@example.com"]
    dev = users["alex.dev@example.com"]

    project = projects_repo.get_by_key("ENG", include_archived=True)
    if not project:
        project = projects_repo.create(
            Project(
                key="ENG",
                name="Engineering Platform",
                description="Core platform development — backlog, sprints, and board demo project.",
                created_by=admin.id,
            )
        )
    else:
        project.name = "Engineering Platform"
        project.description = (
            "Core platform development — backlog, sprints, and board demo project."
        )

    members_repo.upsert(project.id, lead.id, ProjectRole.Lead)
    members_repo.upsert(project.id, member.id, ProjectRole.Member)
    members_repo.upsert(project.id, dev.id, ProjectRole.Member)

    if not statuses_repo.list_for_project(project.id):
        for idx, name in enumerate(DEFAULT_STATUSES):
            statuses_repo.create(
                IssueStatusDef(project_id=project.id, name=name, order=idx, is_default=True)
            )

    if issues_repo.count_for_project(project.id) >= 5:
        db.commit()
        return

    today = date.today()
    active_sprint = sprints_repo.get_active(project.id)
    if not active_sprint:
        active_sprint = sprints_repo.create(
            Sprint(
                project_id=project.id,
                name="Sprint 1 — Foundation",
                goal="Deliver authentication and project workspace MVP",
                start_date=today - timedelta(days=7),
                end_date=today + timedelta(days=7),
                status=SprintStatus.Active,
            )
        )
    planned_sprint = sprints_repo.get_by_status(project.id, SprintStatus.Planned)
    if not planned_sprint:
        planned_sprint = sprints_repo.create(
            Sprint(
                project_id=project.id,
                name="Sprint 2 — Board & Backlog",
                goal="Complete drag-and-drop board and backlog grooming",
                start_date=today + timedelta(days=8),
                end_date=today + timedelta(days=22),
                status=SprintStatus.Planned,
            )
        )
    db.flush()

    start_num = issues_repo.next_issue_number(project.id)

    epic = create_issue(
        project,
        lead.id,
        title="User Management & Onboarding",
        issue_type=IssueType.Epic,
        issue_number=start_num,
        description="Epic covering registration, approval workflow, and role-based access.",
        story_points=13,
        backlog_order=0,
    )

    story1 = create_issue(
        project,
        lead.id,
        title="Implement Super Admin user approval queue",
        issue_type=IssueType.Story,
        issue_number=start_num + 1,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        parent_issue_id=epic.id,
        status="In Progress",
        priority=Priority.High,
        story_points=5,
        backlog_order=1,
    )

    create_issue(
        project,
        lead.id,
        title="Add project member assignment UI",
        issue_type=IssueType.Story,
        issue_number=start_num + 2,
        assignee_id=dev.id,
        sprint_id=active_sprint.id,
        parent_issue_id=epic.id,
        status="To Do",
        story_points=3,
        backlog_order=2,
    )

    create_issue(
        project,
        member.id,
        title="Write unit tests for auth endpoints",
        issue_type=IssueType.SubTask,
        issue_number=start_num + 3,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        parent_issue_id=story1.id,
        status="In Review",
        story_points=2,
        backlog_order=3,
    )

    create_issue(
        project,
        lead.id,
        title="Fix login error message for suspended users",
        issue_type=IssueType.Bug,
        issue_number=start_num + 4,
        assignee_id=dev.id,
        sprint_id=active_sprint.id,
        status="To Do",
        priority=Priority.Highest,
        story_points=1,
        backlog_order=4,
    )

    create_issue(
        project,
        lead.id,
        title="Set up CI pipeline",
        issue_type=IssueType.Task,
        issue_number=start_num + 5,
        assignee_id=member.id,
        sprint_id=active_sprint.id,
        status="Done",
        story_points=2,
        backlog_order=5,
    )

    create_issue(
        project,
        lead.id,
        title="Design sprint completion flow",
        issue_type=IssueType.Story,
        issue_number=start_num + 6,
        sprint_id=planned_sprint.id,
        status="To Do",
        story_points=5,
        backlog_order=6,
    )

    create_issue(
        project,
        lead.id,
        title="Add global issue key search",
        issue_type=IssueType.Task,
        issue_number=start_num + 7,
        status="To Do",
        story_points=2,
        backlog_order=7,
    )

    db.commit()
