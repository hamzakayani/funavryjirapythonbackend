from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.deps import can_manage_project, require_project_access
from app.models import Sprint, User
from app.repositories import IssueRepository, SprintRepository, WorklogRepository
from app.schemas import CompleteSprintRequest, CreateSprintRequest, SprintOut
from app.services.project_service import ProjectService


class SprintService:
    def __init__(self, db: Session):
        self.db = db
        self.sprints = SprintRepository(db)
        self.issues = IssueRepository(db)
        self.worklogs = WorklogRepository(db)
        self.projects = ProjectService(db)

    def list_sprints(self, project_key: str, user: User) -> list[SprintOut]:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        result = []
        for s in self.sprints.list_for_project(project.id):
            result.append(
                SprintOut(
                    id=s.id,
                    name=s.name,
                    goal=s.goal,
                    start_date=s.start_date,
                    end_date=s.end_date,
                    status=s.status.value,
                    issue_count=self.issues.count_for_sprint(s.id),
                )
            )
        return result

    def create_sprint(self, project_key: str, data: CreateSprintRequest, user: User) -> SprintOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Cannot create sprint")
        if data.end_date < data.start_date:
            raise HTTPException(status_code=422, detail="End date must be after start date")
        sprint = Sprint(
            project_id=project.id,
            name=data.name,
            goal=data.goal,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        self.sprints.create(sprint)
        self.sprints.save()
        self.sprints.refresh(sprint)
        return SprintOut(
            id=sprint.id,
            name=sprint.name,
            goal=sprint.goal,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            status=sprint.status.value,
            issue_count=0,
        )

    def start_sprint(self, sprint_id: int, user: User) -> dict:
        sprint = self._get_sprint(sprint_id)
        require_project_access(self.db, user, sprint.project_id)
        if not can_manage_project(self.db, user, sprint.project_id):
            raise HTTPException(status_code=403, detail="Cannot start sprint")
        if self.sprints.get_active(sprint.project_id):
            raise HTTPException(status_code=409, detail="Project already has an active sprint")
        if self.issues.count_for_sprint(sprint.id) == 0:
            raise HTTPException(status_code=422, detail="Sprint must contain at least one issue")
        from app.models import SprintStatus

        sprint.status = SprintStatus.Active
        self.sprints.save()
        return {"message": "Sprint started"}

    def complete_sprint(self, sprint_id: int, data: CompleteSprintRequest, user: User) -> dict:
        from app.models import SprintStatus

        sprint = self._get_sprint(sprint_id)
        require_project_access(self.db, user, sprint.project_id)
        if not can_manage_project(self.db, user, sprint.project_id):
            raise HTTPException(status_code=403, detail="Cannot complete sprint")
        for decision in data.incomplete_issues:
            issue = self.issues.get_in_sprint(decision.issue_id, sprint.id)
            if not issue:
                continue
            if decision.destination == "backlog":
                issue.sprint_id = None
            elif decision.destination == "sprint" and decision.target_sprint_id:
                issue.sprint_id = decision.target_sprint_id
        sprint.status = SprintStatus.Completed
        self.sprints.save()
        return {"message": "Sprint completed"}

    def worklog_summary(self, sprint_id: int, user: User) -> dict:
        sprint = self._get_sprint(sprint_id)
        require_project_access(self.db, user, sprint.project_id)
        issue_ids = self.issues.list_ids_for_sprint(sprint.id)
        total, by_user = self.worklogs.sprint_summary(issue_ids)
        return {"total_minutes": total, "by_user": by_user}

    def _get_sprint(self, sprint_id: int) -> Sprint:
        sprint = self.sprints.get_by_id(sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")
        return sprint
