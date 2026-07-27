from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import MeetingCreateRequest, MeetingOut, MeetingUpdateRequest
from app.services import MeetingService

router = APIRouter(tags=["meetings"])


@router.get("/meetings", response_model=list[MeetingOut])
def list_meetings(
    start: datetime = Query(...),
    end: datetime = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return MeetingService(db).list_meetings(user, start, end)


@router.post("/meetings", response_model=MeetingOut)
def create_meeting(
    data: MeetingCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MeetingService(db)
    meeting = service.create_meeting(data, user)
    return service._meeting_to_out(meeting)


@router.get("/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(
    meeting_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = MeetingService(db)
    meeting = service.get_meeting(meeting_id, user)
    return service._meeting_to_out(meeting)


@router.patch("/meetings/{meeting_id}", response_model=MeetingOut)
def update_meeting(
    meeting_id: int,
    data: MeetingUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MeetingService(db)
    meeting = service.update_meeting(meeting_id, data, user)
    return service._meeting_to_out(meeting)


@router.delete("/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    MeetingService(db).delete_meeting(meeting_id, user)
    return {"message": "Meeting deleted"}
