from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.date_ranges import resolve_range
from app.core.deps import can_edit_standup_entry, can_manage_project, require_project_access
from app.models import (
    AttendanceStatus,
    Standup,
    StandupAssignedTask,
    StandupEntry,
    StandupLeave,
    StandupStatus,
    User,
)
from app.repositories import (
    IssueRepository,
    ProjectMemberRepository,
    ProjectRepository,
    StandupAssignedTaskRepository,
    StandupEntryRepository,
    StandupLeaveRepository,
    StandupRepository,
    UserRepository,
)
from app.schemas import (
    AssignTaskRequest,
    AttendanceReportOut,
    AttendanceReportRow,
    DeclareLeaveRequest,
    MarkAttendanceRequest,
    ProjectLeaveOut,
    StandupAssignedTaskOut,
    StandupEntryOut,
    StandupLeaveOut,
    StandupOut,
    UpdateEntryRequest,
    UpdateIssueRequest,
    UserMini,
)
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService

ATTENDANCE_BUCKETS = ["Present", "Late", "Absent", "On Leave"]


class StandupService:
    def __init__(self, db: Session):
        self.db = db
        self.standups = StandupRepository(db)
        self.entries = StandupEntryRepository(db)
        self.assigned_tasks = StandupAssignedTaskRepository(db)
        self.leaves = StandupLeaveRepository(db)
        self.members = ProjectMemberRepository(db)
        self.users = UserRepository(db)
        self.project_repo = ProjectRepository(db)
        self.issue_repo = IssueRepository(db)
        self.projects = ProjectService(db)
        self.issues = IssueService(db)

    # -- conversion helpers --------------------------------------------------

    def _user_mini(self, user_id: int, job_role_map: dict) -> Optional[UserMini]:
        u = self.users.get_by_id(user_id)
        if not u:
            return None
        return UserMini(id=u.id, name=u.name, avatar_url=u.avatar_url, job_role=job_role_map.get(u.id))

    def _entry_to_out(self, entry: StandupEntry, job_role_map: dict) -> StandupEntryOut:
        tasks = [
            StandupAssignedTaskOut(id=t.id, issue=self.issues.issue_to_out(t.issue))
            for t in self.assigned_tasks.list_for_entry(entry.id)
        ]
        return StandupEntryOut(
            id=entry.id,
            user=self._user_mini(entry.user_id, job_role_map),
            attendance_status=entry.attendance_status.value,
            yesterday_summary=entry.yesterday_summary,
            blockers=entry.blockers,
            is_blocked=entry.is_blocked,
            marked_by=self._user_mini(entry.marked_by, job_role_map) if entry.marked_by else None,
            marked_at=entry.marked_at,
            assigned_tasks=tasks,
        )

    def _standup_to_out(self, standup: Standup, project_key: str) -> StandupOut:
        job_role_map = {
            m.user_id: m.job_role for m in self.members.list_for_project(standup.project_id)
        }
        entries = self.entries.list_for_standup(standup.id)
        return StandupOut(
            id=standup.id,
            project_key=project_key,
            date=standup.date,
            status=standup.status.value,
            created_by=self._user_mini(standup.created_by, job_role_map),
            started_at=standup.started_at,
            completed_at=standup.completed_at,
            entries=[self._entry_to_out(e, job_role_map) for e in entries],
        )

    def _get_standup(self, standup_id: int) -> Standup:
        standup = self.standups.get_by_id(standup_id)
        if not standup:
            raise HTTPException(status_code=404, detail="Standup not found")
        return standup

    def _get_entry_or_404(self, standup_id: int, target_user_id: int) -> StandupEntry:
        entry = self.entries.get(standup_id, target_user_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Standup entry not found")
        return entry

    # -- core lifecycle -------------------------------------------------------

    def get_today(self, project_key: str, user: User) -> Optional[StandupOut]:
        """Read-only lookup — does NOT create a standup. A day with no
        standup yet is a real, visible state (nobody has started roll-call),
        not something to paper over by auto-creating on the first page view."""
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        standup = self.standups.get_by_project_and_date(project.id, date.today())
        if not standup:
            return None
        return self._standup_to_out(standup, project.key)

    def start_today(self, project_key: str, user: User) -> StandupOut:
        """Lead/Super Admin only. Idempotent — calling it again after the
        standup already exists for today just returns the existing one."""
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Only the project lead can start standup")
        today = date.today()
        standup = self.standups.get_by_project_and_date(project.id, today)
        if not standup:
            standup = Standup(project_id=project.id, date=today, created_by=user.id)
            self.standups.create(standup)
            for member in self.members.list_for_project(project.id):
                leave = self.leaves.get_active_for_user_on_date(member.user_id, today)
                self.entries.create(
                    StandupEntry(
                        standup_id=standup.id,
                        user_id=member.user_id,
                        attendance_status=(
                            AttendanceStatus.OnLeave if leave else AttendanceStatus.Present
                        ),
                    )
                )
            self.standups.save()
            self.standups.refresh(standup)
        return self._standup_to_out(standup, project.key)

    def get_standup(self, standup_id: int, user: User) -> StandupOut:
        standup = self._get_standup(standup_id)
        require_project_access(self.db, user, standup.project_id)
        project = self.project_repo.get_by_id(standup.project_id)
        return self._standup_to_out(standup, project.key)

    def get_history(self, project_key: str, user: User, start: date, end: date) -> list[StandupOut]:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        standups = self.standups.list_for_project(project.id, start, end)
        return [self._standup_to_out(s, project.key) for s in standups]

    def mark_attendance(
        self, standup_id: int, target_user_id: int, data: MarkAttendanceRequest, user: User
    ) -> StandupEntryOut:
        standup = self._get_standup(standup_id)
        require_project_access(self.db, user, standup.project_id)
        if not can_manage_project(self.db, user, standup.project_id):
            raise HTTPException(status_code=403, detail="Only the project lead can mark attendance")
        entry = self._get_entry_or_404(standup_id, target_user_id)
        entry.attendance_status = data.status
        entry.marked_by = user.id
        entry.marked_at = datetime.utcnow()
        self.entries.save()
        job_role_map = {m.user_id: m.job_role for m in self.members.list_for_project(standup.project_id)}
        return self._entry_to_out(entry, job_role_map)

    def update_entry(
        self, standup_id: int, target_user_id: int, data: UpdateEntryRequest, user: User
    ) -> StandupEntryOut:
        standup = self._get_standup(standup_id)
        require_project_access(self.db, user, standup.project_id)
        if not can_edit_standup_entry(self.db, user, standup.project_id, target_user_id):
            raise HTTPException(status_code=403, detail="Cannot edit this standup entry")
        entry = self._get_entry_or_404(standup_id, target_user_id)
        updates = data.model_dump(exclude_unset=True)
        if "yesterday_summary" in updates:
            entry.yesterday_summary = data.yesterday_summary
        if "blockers" in updates:
            entry.blockers = data.blockers
        if "is_blocked" in updates:
            entry.is_blocked = data.is_blocked
        self.entries.save()
        job_role_map = {m.user_id: m.job_role for m in self.members.list_for_project(standup.project_id)}
        return self._entry_to_out(entry, job_role_map)

    def assign_task(
        self, standup_id: int, target_user_id: int, data: AssignTaskRequest, user: User
    ) -> StandupEntryOut:
        standup = self._get_standup(standup_id)
        require_project_access(self.db, user, standup.project_id)
        if not can_manage_project(self.db, user, standup.project_id):
            raise HTTPException(status_code=403, detail="Cannot assign tasks in this standup")
        entry = self._get_entry_or_404(standup_id, target_user_id)

        if bool(data.issue_id) == bool(data.new_issue):
            raise HTTPException(
                status_code=422, detail="Provide exactly one of issue_id or new_issue"
            )

        project = self.project_repo.get_by_id(standup.project_id)

        if data.new_issue:
            payload = data.new_issue.model_copy(update={"assignee_id": target_user_id})
            issue_out = self.issues.create_issue(project.key, payload, user)
            issue_id = issue_out.id
        else:
            issue = self.issue_repo.get_by_id(data.issue_id)
            if not issue or issue.project_id != standup.project_id:
                raise HTTPException(status_code=404, detail="Issue not found in this project")
            self.issues.update_issue(
                data.issue_id, UpdateIssueRequest(assignee_id=target_user_id), user
            )
            issue_id = data.issue_id

        if not self.assigned_tasks.exists(entry.id, issue_id):
            self.assigned_tasks.create(
                StandupAssignedTask(standup_entry_id=entry.id, issue_id=issue_id)
            )
            self.assigned_tasks.save()

        job_role_map = {m.user_id: m.job_role for m in self.members.list_for_project(standup.project_id)}
        return self._entry_to_out(entry, job_role_map)

    def complete_standup(self, standup_id: int, user: User) -> dict:
        standup = self._get_standup(standup_id)
        require_project_access(self.db, user, standup.project_id)
        if not can_manage_project(self.db, user, standup.project_id):
            raise HTTPException(status_code=403, detail="Cannot complete standup")
        if standup.status == StandupStatus.Completed:
            raise HTTPException(status_code=409, detail="Standup already completed")
        entries = self.entries.list_for_standup(standup.id)
        unmarked_user_ids = [
            e.user_id
            for e in entries
            if e.marked_by is None and not e.yesterday_summary and not e.blockers
        ]
        standup.status = StandupStatus.Completed
        standup.completed_at = datetime.utcnow()
        self.standups.save()
        return {"message": "Standup completed", "unmarked_user_ids": unmarked_user_ids}

    # -- leave ----------------------------------------------------------------

    def declare_leave(
        self, project_key: str, user: User, data: DeclareLeaveRequest
    ) -> StandupLeaveOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if data.end_date < data.start_date:
            raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
        leave = StandupLeave(
            user_id=user.id,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
        )
        self.leaves.create(leave)
        self.leaves.save()
        return StandupLeaveOut(
            id=leave.id, start_date=leave.start_date, end_date=leave.end_date, reason=leave.reason
        )

    def list_project_leave(self, project_key: str, user: User) -> list[ProjectLeaveOut]:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        today = date.today()
        job_role_map = {m.user_id: m.job_role for m in self.members.list_for_project(project.id)}
        result = []
        for member in self.members.list_for_project(project.id):
            for leave in self.leaves.list_for_user(member.user_id):
                if leave.end_date < today:
                    continue
                mini = self._user_mini(member.user_id, job_role_map)
                if not mini:
                    continue
                result.append(
                    ProjectLeaveOut(
                        id=leave.id,
                        user=mini,
                        start_date=leave.start_date,
                        end_date=leave.end_date,
                        reason=leave.reason,
                    )
                )
        return result

    # -- reporting --------------------------------------------------------------

    def get_attendance_report(
        self,
        project_key: str,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> AttendanceReportOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        range_start, range_end = resolve_range(range_, start_date, end_date)

        standups = self.standups.list_for_project(project.id, range_start, range_end)
        counts: dict[int, dict[str, int]] = {}
        for standup in standups:
            for entry in self.entries.list_for_standup(standup.id):
                bucket = counts.setdefault(entry.user_id, {k: 0 for k in ATTENDANCE_BUCKETS})
                bucket[entry.attendance_status.value] += 1

        job_role_map = {m.user_id: m.job_role for m in self.members.list_for_project(project.id)}
        rows = []
        for user_id, bucket in counts.items():
            mini = self._user_mini(user_id, job_role_map)
            if not mini:
                continue
            rows.append(
                AttendanceReportRow(
                    user=mini,
                    present_count=bucket["Present"],
                    late_count=bucket["Late"],
                    absent_count=bucket["Absent"],
                    leave_count=bucket["On Leave"],
                    total_standups=sum(bucket.values()),
                )
            )
        return AttendanceReportOut(
            project_key=project.key, range_start=range_start, range_end=range_end, rows=rows
        )
