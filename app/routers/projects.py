from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    get_current_user, require_project_access, can_manage_project,
    can_edit_issue, can_change_issue_status, can_assign_issue, get_project_membership,
)
from app.database import get_db
from app.models import (
    User, Project, ProjectMember, Sprint, SprintStatus, Issue, IssueType,
    IssueStatus, Priority, Comment, Worklog, ActivityLog,
)
from app.schemas import (
    ProjectOut, ProjectMemberOut, SprintOut, CreateSprintRequest,
    CompleteSprintRequest, CreateIssueRequest, UpdateIssueRequest,
    ReorderBacklogRequest, CommentRequest, WorklogRequest,
    IssueOut, IssueDetailOut, BoardResponse, CommentOut, WorklogOut,
    ActivityOut, UserMini, SearchResult,
)
from app.services.issues import (
    log_activity, get_next_issue_number, get_time_logged,
    issue_to_out, sync_labels,
)
from app.routers.admin import _project_out

router = APIRouter(tags=["projects"])

STATUSES = ["To Do", "In Progress", "In Review", "Done"]


def _get_project_by_key(db: Session, key: str) -> Project:
    project = db.query(Project).filter(Project.key == key.upper(), Project.is_archived == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_super_admin:
        projects = db.query(Project).filter(Project.is_archived == False).all()
    else:
        ids = [pm.project_id for pm in db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()]
        projects = db.query(Project).filter(Project.id.in_(ids), Project.is_archived == False).all()
    return [_project_out(p, db) for p in projects]


@router.get("/projects/{project_key}", response_model=ProjectOut)
def get_project(project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    return _project_out(project, db)


@router.get("/projects/{project_key}/members", response_model=list[ProjectMemberOut])
def project_members(project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        result.append(ProjectMemberOut(
            id=m.id, user_id=m.user_id, name=u.name, email=u.email,
            project_role=m.project_role.value, assigned_at=m.assigned_at,
        ))
    return result


@router.get("/search", response_model=SearchResult)
def search_issue(
    key: str = Query(..., min_length=3),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue_key = key.strip().upper()
    issue = db.query(Issue).options(
        joinedload(Issue.project),
    ).filter(Issue.issue_key == issue_key, Issue.is_archived == False).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    return SearchResult(
        id=issue.id,
        issue_key=issue.issue_key,
        title=issue.title,
        project_key=issue.project.key,
        project_name=issue.project.name,
        status=issue.status.value,
        issue_type=issue.issue_type.value,
    )


@router.get("/projects/{project_key}/epics", response_model=list[IssueOut])
def list_epics(
    project_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    epics = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels),
    ).filter(
        Issue.project_id == project.id,
        Issue.issue_type == IssueType.Epic,
        Issue.is_archived == False,
    ).order_by(Issue.backlog_order).all()
    return [issue_to_out(e, db) for e in epics]


# Backlog
@router.get("/projects/{project_key}/backlog", response_model=list[IssueOut])
def get_backlog(
    project_key: str,
    issue_type: str | None = None,
    assignee: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    active_sprint = db.query(Sprint).filter(Sprint.project_id == project.id, Sprint.status == SprintStatus.Active).first()
    q = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels)
    ).filter(
        Issue.project_id == project.id, Issue.is_archived == False,
    )
    if active_sprint:
        q = q.filter((Issue.sprint_id == None) | (Issue.sprint_id != active_sprint.id))
    else:
        q = q.filter(Issue.sprint_id == None)
    q = q.filter(Issue.status != IssueStatus.Done)
    if issue_type:
        q = q.filter(Issue.issue_type == IssueType(issue_type))
    if assignee == "me":
        q = q.filter(Issue.assignee_id == user.id)
    elif assignee == "unassigned":
        q = q.filter(Issue.assignee_id == None)
    if status:
        q = q.filter(Issue.status == IssueStatus(status))
    issues = q.order_by(Issue.backlog_order.asc(), Issue.created_at.asc()).all()
    return [issue_to_out(i, db) for i in issues]


@router.patch("/projects/{project_key}/backlog/reorder")
def reorder_backlog(
    project_key: str, data: ReorderBacklogRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    if not can_manage_project(db, user, project.id):
        raise HTTPException(status_code=403, detail="Cannot reorder backlog")
    for idx, issue_id in enumerate(data.issue_ids):
        issue = db.query(Issue).filter(Issue.id == issue_id, Issue.project_id == project.id).first()
        if issue:
            issue.backlog_order = idx
    db.commit()
    return {"message": "Backlog reordered"}


# Sprints
@router.get("/projects/{project_key}/sprints", response_model=list[SprintOut])
def list_sprints(project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    sprints = db.query(Sprint).filter(Sprint.project_id == project.id).order_by(Sprint.created_at.desc()).all()
    result = []
    for s in sprints:
        count = db.query(Issue).filter(Issue.sprint_id == s.id, Issue.is_archived == False).count()
        result.append(SprintOut(
            id=s.id, name=s.name, goal=s.goal, start_date=s.start_date,
            end_date=s.end_date, status=s.status.value, issue_count=count,
        ))
    return result


@router.post("/projects/{project_key}/sprints", response_model=SprintOut)
def create_sprint(
    project_key: str, data: CreateSprintRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    if not can_manage_project(db, user, project.id):
        raise HTTPException(status_code=403, detail="Cannot create sprint")
    if data.end_date < data.start_date:
        raise HTTPException(status_code=422, detail="End date must be after start date")
    sprint = Sprint(
        project_id=project.id, name=data.name, goal=data.goal,
        start_date=data.start_date, end_date=data.end_date,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return SprintOut(
        id=sprint.id, name=sprint.name, goal=sprint.goal,
        start_date=sprint.start_date, end_date=sprint.end_date,
        status=sprint.status.value, issue_count=0,
    )


@router.post("/sprints/{sprint_id}/start")
def start_sprint(sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    require_project_access(db, user, sprint.project_id)
    if not can_manage_project(db, user, sprint.project_id):
        raise HTTPException(status_code=403, detail="Cannot start sprint")
    active = db.query(Sprint).filter(
        Sprint.project_id == sprint.project_id, Sprint.status == SprintStatus.Active
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="Project already has an active sprint")
    issue_count = db.query(Issue).filter(Issue.sprint_id == sprint.id, Issue.is_archived == False).count()
    if issue_count == 0:
        raise HTTPException(status_code=422, detail="Sprint must contain at least one issue")
    sprint.status = SprintStatus.Active
    db.commit()
    return {"message": "Sprint started"}


@router.post("/sprints/{sprint_id}/complete")
def complete_sprint(
    sprint_id: int, data: CompleteSprintRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    require_project_access(db, user, sprint.project_id)
    if not can_manage_project(db, user, sprint.project_id):
        raise HTTPException(status_code=403, detail="Cannot complete sprint")
    for decision in data.incomplete_issues:
        issue = db.query(Issue).filter(Issue.id == decision.issue_id, Issue.sprint_id == sprint.id).first()
        if not issue:
            continue
        if decision.destination == "backlog":
            issue.sprint_id = None
        elif decision.destination == "sprint" and decision.target_sprint_id:
            issue.sprint_id = decision.target_sprint_id
    sprint.status = SprintStatus.Completed
    db.commit()
    return {"message": "Sprint completed"}


@router.get("/sprints/{sprint_id}/issues", response_model=list[IssueOut])
def sprint_issues(sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    require_project_access(db, user, sprint.project_id)
    issues = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels)
    ).filter(Issue.sprint_id == sprint.id, Issue.is_archived == False).all()
    return [issue_to_out(i, db) for i in issues]


@router.get("/sprints/{sprint_id}/worklogs/summary")
def sprint_worklog_summary(sprint_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    require_project_access(db, user, sprint.project_id)
    issue_ids = [i.id for i in db.query(Issue).filter(Issue.sprint_id == sprint.id).all()]
    total = db.query(func.coalesce(func.sum(Worklog.time_spent_minutes), 0)).filter(
        Worklog.issue_id.in_(issue_ids)
    ).scalar() if issue_ids else 0
    by_user = db.query(
        Worklog.user_id, func.sum(Worklog.time_spent_minutes)
    ).filter(Worklog.issue_id.in_(issue_ids)).group_by(Worklog.user_id).all() if issue_ids else []
    users_breakdown = []
    for uid, mins in by_user:
        u = db.query(User).filter(User.id == uid).first()
        users_breakdown.append({"user_id": uid, "name": u.name if u else "Unknown", "total_minutes": int(mins)})
    return {"total_minutes": int(total or 0), "by_user": users_breakdown}


# Board
@router.get("/projects/{project_key}/board", response_model=BoardResponse)
def get_board(
    project_key: str,
    assignee: str | None = None,
    issue_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    active_sprint = db.query(Sprint).filter(
        Sprint.project_id == project.id, Sprint.status == SprintStatus.Active
    ).first()
    columns = {s: [] for s in STATUSES}
    sprint_out = None
    if active_sprint:
        sprint_out = SprintOut(
            id=active_sprint.id, name=active_sprint.name, goal=active_sprint.goal,
            start_date=active_sprint.start_date, end_date=active_sprint.end_date,
            status=active_sprint.status.value,
            issue_count=db.query(Issue).filter(Issue.sprint_id == active_sprint.id).count(),
        )
        q = db.query(Issue).options(
            joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels)
        ).filter(
            Issue.sprint_id == active_sprint.id, Issue.is_archived == False,
            Issue.issue_type != IssueType.Epic,
        )
        if assignee == "me":
            q = q.filter(Issue.assignee_id == user.id)
        if issue_type:
            q = q.filter(Issue.issue_type == IssueType(issue_type))
        for issue in q.all():
            out = issue_to_out(issue, db)
            status = issue.status.value
            if status in columns:
                columns[status].append(out.model_dump())
    return BoardResponse(sprint=sprint_out, columns=columns)


# Issues
@router.post("/projects/{project_key}/issues", response_model=IssueOut)
def create_issue(
    project_key: str, data: CreateIssueRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    project = _get_project_by_key(db, project_key)
    require_project_access(db, user, project.id)
    if data.issue_type == "Sub-task" and not data.parent_issue_id:
        raise HTTPException(status_code=422, detail="Sub-task requires a parent issue")
    num = get_next_issue_number(db, project.id)
    max_order = db.query(Issue).filter(Issue.project_id == project.id).count()
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
        backlog_order=max_order,
    )
    db.add(issue)
    db.flush()
    log_activity(db, issue.id, user.id, "created")
    db.commit()
    db.refresh(issue)
    issue = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels)
    ).filter(Issue.id == issue.id).first()
    return issue_to_out(issue, db)


@router.get("/issues/{issue_id}", response_model=IssueDetailOut)
def get_issue(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    issue = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels),
        joinedload(Issue.comments).joinedload(Comment.author),
        joinedload(Issue.worklogs).joinedload(Worklog.user),
        joinedload(Issue.activities).joinedload(ActivityLog.user),
    ).filter(Issue.id == issue_id, Issue.is_archived == False).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    base = issue_to_out(issue, db)
    comments = [CommentOut(
        id=c.id, body=c.body,
        author=UserMini(id=c.author.id, name=c.author.name),
        created_at=c.created_at,
    ) for c in sorted(issue.comments, key=lambda x: x.created_at)]
    worklogs = [WorklogOut(
        id=w.id, date_worked=w.date_worked, time_spent_minutes=w.time_spent_minutes,
        description=w.description, user=UserMini(id=w.user.id, name=w.user.name),
        created_at=w.created_at,
    ) for w in sorted(issue.worklogs, key=lambda x: x.created_at, reverse=True)]
    activities = [ActivityOut(
        id=a.id, action=a.action, field_name=a.field_name,
        old_value=a.old_value, new_value=a.new_value,
        user=UserMini(id=a.user.id, name=a.user.name), created_at=a.created_at,
    ) for a in sorted(issue.activities, key=lambda x: x.created_at, reverse=True)]
    subtasks = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels),
    ).filter(Issue.parent_issue_id == issue.id, Issue.is_archived == False).all()
    parent_out = None
    if issue.parent_issue_id:
        parent = db.query(Issue).options(
            joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels),
        ).filter(Issue.id == issue.parent_issue_id).first()
        if parent:
            parent_out = issue_to_out(parent, db)
    return IssueDetailOut(
        **base.model_dump(),
        comments=comments,
        worklogs=worklogs,
        activities=activities,
        subtasks=[issue_to_out(s, db) for s in subtasks],
        parent=parent_out,
    )


@router.patch("/issues/{issue_id}", response_model=IssueOut)
def update_issue(
    issue_id: int, data: UpdateIssueRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.is_archived == False).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)

    if data.status is not None:
        if not can_change_issue_status(db, user, issue):
            raise HTTPException(status_code=403, detail="Cannot change status")
        old = issue.status.value
        issue.status = IssueStatus(data.status)
        log_activity(db, issue.id, user.id, "field_changed", "status", old, data.status)
    elif not can_edit_issue(db, user, issue):
        raise HTTPException(status_code=403, detail="Cannot edit issue")

    if "assignee_id" in data.model_dump(exclude_unset=True):
        new_assignee = data.assignee_id
        if not can_assign_issue(db, user, issue, new_assignee):
            raise HTTPException(status_code=403, detail="Cannot assign this issue")

    field_map = {
        "title": ("title", lambda v: v),
        "description": ("description", lambda v: v),
        "priority": ("priority", lambda v: Priority(v)),
        "assignee_id": ("assignee_id", lambda v: v),
        "sprint_id": ("sprint_id", lambda v: v),
        "parent_issue_id": ("parent_issue_id", lambda v: v),
        "story_points": ("story_points", lambda v: v),
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
                log_activity(db, issue.id, user.id, "field_changed", field, str(old_val), str(new_val))

    if data.labels is not None:
        sync_labels(db, issue, data.labels)

    db.commit()
    issue = db.query(Issue).options(
        joinedload(Issue.assignee), joinedload(Issue.reporter), joinedload(Issue.labels)
    ).filter(Issue.id == issue.id).first()
    return issue_to_out(issue, db)


@router.post("/issues/{issue_id}/assign-to-me")
def assign_to_me(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    old = issue.assignee_id
    issue.assignee_id = user.id
    log_activity(db, issue.id, user.id, "field_changed", "assignee_id", str(old), str(user.id))
    db.commit()
    return {"message": "Assigned to you"}


@router.delete("/issues/{issue_id}")
def archive_issue(issue_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    if not can_manage_project(db, user, issue.project_id):
        raise HTTPException(status_code=403, detail="Cannot archive issue")
    issue.is_archived = True
    db.commit()
    return {"message": "Issue archived"}


@router.post("/issues/{issue_id}/comments", response_model=CommentOut)
def add_comment(
    issue_id: int, data: CommentRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    comment = Comment(issue_id=issue.id, author_id=user.id, body=data.body)
    db.add(comment)
    log_activity(db, issue.id, user.id, "comment_added")
    db.commit()
    db.refresh(comment)
    return CommentOut(
        id=comment.id, body=comment.body,
        author=UserMini(id=user.id, name=user.name), created_at=comment.created_at,
    )


@router.post("/issues/{issue_id}/worklogs", response_model=WorklogOut)
def add_worklog(
    issue_id: int, data: WorklogRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user, issue.project_id)
    if not can_edit_issue(db, user, issue) and issue.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot log time on this issue")
    if data.date_worked > date.today():
        raise HTTPException(status_code=422, detail="Cannot log time for future dates")
    wl = Worklog(
        issue_id=issue.id, user_id=user.id,
        date_worked=data.date_worked, time_spent_minutes=data.time_spent_minutes,
        description=data.description,
    )
    db.add(wl)
    log_activity(db, issue.id, user.id, "worklog_added", None, None, f"{data.time_spent_minutes}m")
    db.commit()
    db.refresh(wl)
    return WorklogOut(
        id=wl.id, date_worked=wl.date_worked, time_spent_minutes=wl.time_spent_minutes,
        description=wl.description, user=UserMini(id=user.id, name=user.name),
        created_at=wl.created_at,
    )
