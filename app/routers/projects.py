from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import IssueType, Priority, User
from app.schemas import (
    BoardResponse,
    CommentOut,
    CommentRequest,
    CompleteSprintRequest,
    CreateIssueRequest,
    CreateSprintRequest,
    CreateStatusRequest,
    IssueDetailOut,
    IssueAttachmentOut,
    IssueOut,
    IssueStatusOut,
    ProjectMemberOut,
    ProjectOut,
    ReorderBacklogRequest,
    ReorderStatusRequest,
    SearchResult,
    SprintOut,
    UpdateIssueRequest,
    UpdateMemberRoleRequest,
    UpdateStatusRequest,
    WorklogOut,
    WorklogRequest,
)
from app.services import IssueService, ProjectService, SprintService

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProjectService(db).list_for_user(user)


@router.get("/projects/{project_key}", response_model=ProjectOut)
def get_project(project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProjectService(db).get_for_user(project_key, user)


@router.get("/projects/{project_key}/members", response_model=list[ProjectMemberOut])
def project_members(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ProjectService(db).list_members(project_key, user)


@router.patch("/projects/{project_key}/members/{user_id}/role", response_model=ProjectMemberOut)
def update_member_role(
    project_key: str,
    user_id: int,
    data: UpdateMemberRoleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectService(db).update_member_role(project_key, user_id, data, user)


@router.get("/projects/{project_key}/statuses", response_model=list[IssueStatusOut])
def list_statuses(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ProjectService(db).list_statuses(project_key, user)


@router.post("/projects/{project_key}/statuses", response_model=IssueStatusOut)
def create_status(
    project_key: str,
    data: CreateStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectService(db).create_status(project_key, data, user)


@router.patch("/projects/{project_key}/statuses/reorder", response_model=list[IssueStatusOut])
def reorder_statuses(
    project_key: str,
    data: ReorderStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectService(db).reorder_statuses(project_key, data, user)


@router.patch("/projects/{project_key}/statuses/{status_id}", response_model=IssueStatusOut)
def rename_status(
    project_key: str,
    status_id: int,
    data: UpdateStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectService(db).rename_status(project_key, status_id, data, user)


@router.delete("/projects/{project_key}/statuses/{status_id}")
def delete_status(
    project_key: str,
    status_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectService(db).delete_status(project_key, status_id, user)


@router.get("/search", response_model=SearchResult)
def search_issue(
    key: str = Query(..., min_length=3),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).search(key, user)


@router.get("/search/issues", response_model=list[SearchResult])
def search_issues(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).search_issues(q, user)


@router.get("/projects/{project_key}/epics", response_model=list[IssueOut])
def list_epics(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return IssueService(db).list_epics(project_key, user)


@router.get("/projects/{project_key}/backlog", response_model=list[IssueOut])
def get_backlog(
    project_key: str,
    issue_type: IssueType | None = None,
    assignee: str | None = None,
    status: str | None = None,
    priority: Priority | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).get_backlog(
        project_key,
        user,
        issue_type=issue_type.value if issue_type else None,
        assignee=assignee,
        status=status,
        priority=priority.value if priority else None,
    )


@router.get("/projects/{project_key}/issues", response_model=list[IssueOut])
def list_all_issues(
    project_key: str,
    issue_type: IssueType | None = None,
    assignee: str | None = None,
    status: str | None = None,
    priority: Priority | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).list_all(
        project_key,
        user,
        issue_type=issue_type.value if issue_type else None,
        assignee=assignee,
        status=status,
        priority=priority.value if priority else None,
    )


@router.patch("/projects/{project_key}/backlog/reorder")
def reorder_backlog(
    project_key: str,
    data: ReorderBacklogRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).reorder_backlog(project_key, data, user)


@router.get("/projects/{project_key}/sprints", response_model=list[SprintOut])
def list_sprints(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return SprintService(db).list_sprints(project_key, user)


@router.post("/projects/{project_key}/sprints", response_model=SprintOut)
def create_sprint(
    project_key: str,
    data: CreateSprintRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SprintService(db).create_sprint(project_key, data, user)


@router.post("/sprints/{sprint_id}/start")
def start_sprint(sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SprintService(db).start_sprint(sprint_id, user)


@router.post("/sprints/{sprint_id}/complete")
def complete_sprint(
    sprint_id: int,
    data: CompleteSprintRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SprintService(db).complete_sprint(sprint_id, data, user)


@router.get("/sprints/{sprint_id}/issues", response_model=list[IssueOut])
def sprint_issues(
    sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return IssueService(db).sprint_issues(sprint_id, user)


@router.get("/sprints/{sprint_id}/worklogs/summary")
def sprint_worklog_summary(
    sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return SprintService(db).worklog_summary(sprint_id, user)


@router.get("/projects/{project_key}/board", response_model=BoardResponse)
def get_board(
    project_key: str,
    assignee: str | None = None,
    issue_type: IssueType | None = None,
    status: str | None = None,
    priority: Priority | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).get_board(
        project_key,
        user,
        assignee=assignee,
        issue_type=issue_type.value if issue_type else None,
        status=status,
        priority=priority.value if priority else None,
    )


@router.post("/projects/{project_key}/issues", response_model=IssueOut)
def create_issue(
    project_key: str,
    data: CreateIssueRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).create_issue(project_key, data, user)


@router.get("/issues/{issue_id}", response_model=IssueDetailOut)
def get_issue(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return IssueService(db).get_issue(issue_id, user)


@router.patch("/issues/{issue_id}", response_model=IssueOut)
def update_issue(
    issue_id: int,
    data: UpdateIssueRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).update_issue(issue_id, data, user)


@router.post("/issues/{issue_id}/assign-to-me")
def assign_to_me(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return IssueService(db).assign_to_me(issue_id, user)


@router.delete("/issues/{issue_id}")
def archive_issue(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return IssueService(db).archive_issue(issue_id, user)


@router.post("/issues/{issue_id}/comments", response_model=CommentOut)
def add_comment(
    issue_id: int,
    data: CommentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).add_comment(issue_id, data, user)


@router.post("/issues/{issue_id}/worklogs", response_model=WorklogOut)
def add_worklog(
    issue_id: int,
    data: WorklogRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).add_worklog(issue_id, data, user)


@router.post("/issues/{issue_id}/attachments", response_model=IssueAttachmentOut)
async def add_issue_attachment(
    issue_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await IssueService(db).add_attachment(issue_id, file, user)


@router.delete("/issues/{issue_id}/attachments/{attachment_id}")
def delete_issue_attachment(
    issue_id: int,
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).delete_attachment(issue_id, attachment_id, user)
