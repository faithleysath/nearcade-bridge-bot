from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Header, WebSocketException, Depends
from typing import TYPE_CHECKING
import json
import uuid
import asyncio

if TYPE_CHECKING:
    from typing import List

router = APIRouter()

# WebSocket连接管理
class BotConnectionManager:
    def __init__(self):
        # 存储bot的WebSocket连接
        self.bot_connections: dict[int, WebSocket] = {}
        # 存储等待响应的Future对象, key是echo (request_id), value是Future
        self.pending_requests: dict[str, asyncio.Future] = {}
        # 存储每个bot的请求队列
        self.bot_request_queues: dict[int, set[str]] = {}


    async def add_bot(self, bot_id: int, websocket: WebSocket):
        self.bot_connections[bot_id] = websocket
        self.bot_request_queues[bot_id] = set()

    async def remove_bot(self, bot_id: int):
        """移除一个bot连接，并取消其所有待处理的请求"""
        if bot_id in self.bot_connections:
            del self.bot_connections[bot_id]
        
        # 清理与该bot相关的所有待处理请求，防止内存泄漏
        # 注意：这只是一个简单的实现，更复杂的场景可能需要更精细的处理
        for request_id in list(self.bot_request_queues.get(bot_id, [])):
            if request_id in self.pending_requests:
                future = self.pending_requests.pop(request_id)
                if not future.done():
                    future.set_exception(WebSocketException(code=1001, reason="Bot disconnected"))

    async def listen_bot(self, bot_id: int):
        if bot_id in self.bot_connections:
            try:
                data = await self.bot_connections[bot_id].receive_text()
                try:
                    message = json.loads(data)
                    echo = message.get('echo')
                    if echo and echo in self.pending_requests:
                        future = self.pending_requests.pop(echo)
                        if not future.done():
                            future.set_result(data)
                        self.bot_request_queues[bot_id].discard(echo)
                except json.JSONDecodeError:
                    pass
                return data
            except WebSocketDisconnect:
                await self.remove_bot(bot_id)
        return None

    async def send_text_to_bot(self, bot_id: int, message: str):
        if bot_id in self.bot_connections:
            try:
                await self.bot_connections[bot_id].send_text(message)
                return True
            except WebSocketDisconnect:
                await self.remove_bot(bot_id)
        return False
    
    async def send_request_to_bot(self, bot_id: int, payload: dict):
        request_id = str(uuid.uuid4())
        payload['echo'] = request_id

        # 获取当前事件循环并创建一个Future
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        # 存储Future，等待响应
        self.pending_requests[request_id] = future
        self.bot_request_queues[bot_id].add(request_id)
        
        # 发送请求
        success = await self.send_text_to_bot(bot_id, json.dumps(payload))

        if not success:
            # 如果发送失败，立即将异常设置给Future
            self.pending_requests.pop(request_id, None)
            future.set_exception(ConnectionError(f"Failed to send request to bot {bot_id}."))

        return future


bot_connections_manager = BotConnectionManager()

async def verify_token_and_path_and_bot(
        websocket: WebSocket,
        path: str,
        authorization: str | None = Header(None),
):
    if authorization is None or not authorization.startswith("Bearer "):
        raise WebSocketException(code=1008, reason="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    if path == "123" and token == "123321":
        await websocket.accept()
        try:
            first_message = await websocket.receive_json()
            bot_id = first_message.get("self_id")
            if bot_id == 3892215616:
                return path, token, bot_id
        except:
            pass
    raise WebSocketException(code=1008, reason="Invalid token, path, or bot_id")

@router.websocket("/{path}")
async def websocket_endpoint(websocket: WebSocket, path_token_bot=Depends(verify_token_and_path_and_bot)):
    path, token, bot_id = path_token_bot
    print(f"WebSocket connection established for bot_id: {bot_id}")
    await bot_connections_manager.add_bot(bot_id, websocket)
    try:
        while True:
            data = await bot_connections_manager.listen_bot(bot_id)
            print(f"Received message: {data}")
    except WebSocketDisconnect:
        print(f"Bot {bot_id} disconnected.")
        await bot_connections_manager.remove_bot(bot_id)