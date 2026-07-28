import asyncio

from app.core.chat_ws import ChatConnectionManager


class FakeWebSocket:
    def __init__(self, fail_on_send: bool = False):
        self.sent: list[dict] = []
        self.fail_on_send = fail_on_send

    async def accept(self):
        pass

    async def send_json(self, data: dict):
        if self.fail_on_send:
            raise RuntimeError("connection closed")
        self.sent.append(data)


def test_broadcast_reaches_only_connections_for_that_project():
    manager = ChatConnectionManager()
    ws_project_1 = FakeWebSocket()
    ws_project_2 = FakeWebSocket()

    async def run():
        await manager.connect(1, ws_project_1)
        await manager.connect(2, ws_project_2)
        await manager.broadcast(1, {"type": "message_created"})

    asyncio.run(run())

    assert ws_project_1.sent == [{"type": "message_created"}]
    assert ws_project_2.sent == []


def test_broadcast_drops_dead_connections_without_raising():
    manager = ChatConnectionManager()
    dead_ws = FakeWebSocket(fail_on_send=True)
    alive_ws = FakeWebSocket()

    async def run():
        await manager.connect(1, dead_ws)
        await manager.connect(1, alive_ws)
        await manager.broadcast(1, {"type": "message_created"})

    asyncio.run(run())  # must not raise even though dead_ws.send_json raises

    assert alive_ws.sent == [{"type": "message_created"}]


def test_disconnect_removes_connection():
    manager = ChatConnectionManager()
    ws = FakeWebSocket()

    async def run():
        await manager.connect(1, ws)

    asyncio.run(run())
    manager.disconnect(1, ws)

    assert 1 not in manager._connections
