from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class CreateSprintRequest(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: date
    end_date: date


class SprintOut(BaseModel):
    id: int
    name: str
    goal: Optional[str]
    start_date: date
    end_date: date
    status: str
    issue_count: int = 0

    class Config:
        from_attributes = True


class IncompleteIssueDecision(BaseModel):
    issue_id: int
    destination: str
    target_sprint_id: Optional[int] = None


class CompleteSprintRequest(BaseModel):
    incomplete_issues: List[IncompleteIssueDecision] = []
