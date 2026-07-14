from sqlalchemy.orm import Session

from app.models import Comment


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        self.db.flush()
        return comment

    def save(self) -> None:
        self.db.commit()

    def refresh(self, comment: Comment) -> Comment:
        self.db.refresh(comment)
        return comment
