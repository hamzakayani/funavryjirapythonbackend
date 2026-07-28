from fastapi import APIRouter, Depends, File, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.chat_ws import manager
from app.core.deps import get_current_user
from app.core.security import decode_access_token
from app.database import SessionLocal, get_db
from app.models import User, UserStatus
from app.repositories import ProjectMemberRepository, ProjectRepository, UserRepository
from app.schemas import ChatAttachmentOut, ChatMessageOut, EditMessageRequest, SendMessageRequest
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.get("/projects/{project_key}/chat/messages", response_model=list[ChatMessageOut])
def list_messages(
    project_key: str,
    before_id: int | None = Query(None),
    limit: int = Query(50, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ChatService(db).list_messages(project_key, user, before_id=before_id, limit=limit)


@router.post("/projects/{project_key}/chat/messages", response_model=ChatMessageOut)
async def send_message(
    project_key: str,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    out = ChatService(db).create_message(project_key, user, data.text, data.mentions)
    await manager.broadcast(
        out.project_id, {"type": "message_created", "message": out.model_dump(mode="json")}
    )
    return out


@router.patch("/projects/{project_key}/chat/messages/{message_id}", response_model=ChatMessageOut)
async def edit_message(
    project_key: str,
    message_id: int,
    data: EditMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    out = ChatService(db).edit_message(project_key, message_id, user, data.text, data.mentions)
    await manager.broadcast(
        out.project_id, {"type": "message_updated", "message": out.model_dump(mode="json")}
    )
    return out


@router.delete("/projects/{project_key}/chat/messages/{message_id}", response_model=ChatMessageOut)
async def delete_message(
    project_key: str,
    message_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    out = ChatService(db).delete_message(project_key, message_id, user)
    await manager.broadcast(
        out.project_id, {"type": "message_deleted", "message": out.model_dump(mode="json")}
    )
    return out


@router.post(
    "/projects/{project_key}/chat/messages/{message_id}/attachments",
    response_model=ChatAttachmentOut,
)
async def add_attachment(
    project_key: str,
    message_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    attachment_out = await service.add_attachment(project_key, message_id, file, user)
    message_out = service.get_message_out(project_key, message_id)
    await manager.broadcast(
        message_out.project_id,
        {"type": "message_updated", "message": message_out.model_dump(mode="json")},
    )
    return attachment_out


@router.get("/projects/{project_key}/chat/attachments/{attachment_id}/download")
def download_chat_attachment(
    project_key: str,
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    path, filename, content_type = ChatService(db).get_attachment_file(
        project_key, attachment_id, user
    )
    return FileResponse(
        path,
        media_type=content_type,
        filename=filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.websocket("/ws/projects/{project_key}/chat")
async def chat_websocket(
    websocket: WebSocket,
    project_key: str,
    token: str = Query(...),
):
    # Use a short-lived session only for the auth/membership checks. The
    # idle-listen loop below needs no DB access, and this connection may
    # stay open for hours — holding a pooled session for that long would
    # exhaust the connection pool after a handful of concurrent clients.
    db = SessionLocal()
    try:
        try:
            user_id = decode_access_token(token)
        except (JWTError, ValueError, TypeError):
            await websocket.close(code=4401)
            return

        user = UserRepository(db).get_by_id(user_id)
        if not user or user.status != UserStatus.Active:
            await websocket.close(code=4401)
            return

        project = ProjectRepository(db).get_by_key(project_key)
        if not project:
            await websocket.close(code=4404)
            return

        if not user.is_super_admin and not ProjectMemberRepository(db).get(project.id, user.id):
            await websocket.close(code=4403)
            return

        project_id = project.id
    finally:
        db.close()

    await manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(project_id, websocket)
