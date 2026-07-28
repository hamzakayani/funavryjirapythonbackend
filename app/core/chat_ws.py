from collections import defaultdict
from typing import Any


class ChatConnectionManager:
    """In-process WebSocket broadcaster, one connection set per project.

    Only broadcasts to clients connected to THIS process. This means the
    backend MUST run as a single process (`-w 1` in `ecosystem.config.js`)
    for chat broadcasts to reach all connected clients — this is an ENFORCED
    deployment requirement, not just an incidental fact. If this is ever
    changed to multiple workers, a Redis pub/sub layer must be added first,
    otherwise a message posted through one worker will only reach the
    fraction of clients connected to that same worker.
    """

    def __init__(self) -> None:
        self._connections: dict[int, set] = defaultdict(set)

    async def connect(self, project_id: int, websocket) -> None:
        await websocket.accept()
        self._connections[project_id].add(websocket)

    def disconnect(self, project_id: int, websocket) -> None:
        self._connections[project_id].discard(websocket)
        if not self._connections[project_id]:
            del self._connections[project_id]

    async def broadcast(self, project_id: int, event: dict[str, Any]) -> None:
        dead = []
        for websocket in self._connections.get(project_id, set()):
            try:
                await websocket.send_json(event)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(project_id, websocket)


manager = ChatConnectionManager()
