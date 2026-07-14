from sqlalchemy.orm import Session

from app.models import Issue, IssueLabel


class IssueLabelRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_for_issue(self, issue: Issue, labels: list[str]) -> None:
        self.db.query(IssueLabel).filter(IssueLabel.issue_id == issue.id).delete()
        for label in labels:
            self.db.add(IssueLabel(issue_id=issue.id, label=label[:50]))
