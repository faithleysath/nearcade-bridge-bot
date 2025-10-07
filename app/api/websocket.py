from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Header, WebSocketException, Depends
import json
import uuid
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket连接管理（单bot模式）
class BotConnectionManager:
    def __init__(self):
        # 存储唯一的bot连接
        self.bot_connection: WebSocket | None = None
        self.bot_id: int | None = None
        # 存储等待响应的Future对象, key是echo (request_id), value是Future
        self.pending_requests: dict[str, asyncio.Future] = {}
        # 添加并发保护
        self._connection_lock = asyncio.Lock()
        self._requests_lock = asyncio.Lock()
        # 连接状态
        self._is_connected = False


    async def add_bot(self, bot_id: int, websocket: WebSocket) -> bool:
        """添加唯一的bot连接"""
        async with self._connection_lock:
            if self._is_connected and self.bot_connection is not None:
                logger.warning(f"Bot {self.bot_id} already connected, disconnecting...")
                await self.remove_bot()

            self.bot_connection = websocket
            self.bot_id = bot_id
            self._is_connected = True
            logger.info(f"Bot {bot_id} connected successfully")
            return True

    async def remove_bot(self) -> None:
        """移除bot连接，并取消所有待处理的请求"""
        async with self._connection_lock:
            bot_id = self.bot_id
            self.bot_connection = None
            self.bot_id = None
            self._is_connected = False

        # 清理所有待处理请求，防止内存泄漏
        async with self._requests_lock:
            for request_id in list(self.pending_requests.keys()):
                future = self.pending_requests.pop(request_id)
                if not future.done():
                    future.set_exception(WebSocketException(code=1001, reason="Bot disconnected"))

        if bot_id:
            logger.info(f"Bot {bot_id} disconnected")

    async def listen_bot(self) -> str | None:
        """监听bot消息"""
        if not self._is_connected or self.bot_connection is None:
            return None

        try:
            data = await self.bot_connection.receive_text()
            try:
                message = json.loads(data)
                echo = message.get('echo')
                if echo and echo in self.pending_requests:
                    async with self._requests_lock:
                        future = self.pending_requests.pop(echo, None)
                        if future and not future.done():
                            future.set_result(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Received invalid JSON: {e}")
            return data
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected, cleaning up connection")
            await self.remove_bot()
        except Exception as e:
            logger.error(f"Error listening to bot: {e}")
            await self.remove_bot()
        return None

    async def _send_text_to_bot(self, message: str) -> bool:
        """发送文本数据给bot"""
        if not self._is_connected or self.bot_connection is None:
            return False

        try:
            await self.bot_connection.send_text(message)
            return True
        except WebSocketDisconnect:
            logger.info("Bot disconnected during send, cleaning up")
            await self.remove_bot()
        except Exception as e:
            logger.error(f"Error sending message to bot: {e}")
            await self.remove_bot()
        return False
    
    async def send_request_to_bot(self, payload: dict) -> asyncio.Future:
        """发送请求给bot并等待响应"""
        if not self._is_connected or self.bot_connection is None:
            raise ConnectionError("No bot connected")

        request_id = str(uuid.uuid4())
        payload['echo'] = request_id

        # 获取当前事件循环并创建一个Future
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        # 存储Future，等待响应
        async with self._requests_lock:
            self.pending_requests[request_id] = future

        # 发送请求
        success = await self._send_text_to_bot(json.dumps(payload))

        if not success:
            # 如果发送失败，立即将异常设置给Future
            async with self._requests_lock:
                self.pending_requests.pop(request_id, None)
            if not future.done():
                future.set_exception(ConnectionError("Failed to send request to bot."))

        return future


bot_connections_manager = BotConnectionManager()

def _validate_token_format(token: str) -> bool:
    """验证token格式"""
    # 至少8位字符，包含字母和数字
    if len(token) < 8:
        return False
    has_letter = any(c.isalpha() for c in token)
    has_digit = any(c.isdigit() for c in token)
    return has_letter and has_digit

async def verify_bot_connection(
        websocket: WebSocket,
        path: str,
        authorization: str | None = Header(None),
):
    """验证bot连接并返回bot_id"""
    # 验证Authorization header
    if authorization is None or not authorization.startswith("Bearer "):
        raise WebSocketException(code=1008, reason="Missing or invalid Authorization header")

    token_parts = authorization.split(" ", 1)
    if len(token_parts) != 2:
        raise WebSocketException(code=1008, reason="Invalid Authorization header format")

    token = token_parts[1]

    # 验证token格式
    if not _validate_token_format(token):
        raise WebSocketException(code=1008, reason="Invalid token format")

    # 从环境变量获取配置
    expected_path = os.getenv("WS_PATH")
    expected_token = os.getenv("WS_TOKEN")
    expected_bot_id_str = os.getenv("BOT_ID")

    # 验证环境变量已配置
    if not all([expected_path, expected_token, expected_bot_id_str]):
        logger.error("Missing required environment variables: WS_PATH, WS_TOKEN, BOT_ID")
        raise WebSocketException(code=1008, reason="Server configuration error")

    try:
        expected_bot_id = int(expected_bot_id_str)  # type: ignore
    except ValueError:
        logger.error("Invalid BOT_ID in environment variables")
        raise WebSocketException(code=1008, reason="Server configuration error")

    # 验证路径和token
    if path != expected_path or token != expected_token:
        logger.warning(f"Connection attempt with invalid path/token: path={path}, bot_id expected={expected_bot_id}")
        raise WebSocketException(code=1008, reason="Invalid token, path, or bot_id")

    await websocket.accept()

    try:
        first_message = await websocket.receive_json()
        bot_id = first_message.get("self_id")

        if bot_id is None:
            raise WebSocketException(code=1008, reason="Missing self_id in first message")

        if not isinstance(bot_id, int):
            try:
                bot_id = int(bot_id)
            except (ValueError, TypeError):
                raise WebSocketException(code=1008, reason="Invalid self_id format")

        if bot_id == expected_bot_id:
            logger.info(f"Bot {bot_id} authentication successful")
            return bot_id
        else:
            logger.warning(f"Bot ID mismatch: expected={expected_bot_id}, received={bot_id}")
            raise WebSocketException(code=1008, reason="Bot ID mismatch")

    except json.JSONDecodeError:
        raise WebSocketException(code=1008, reason="Invalid JSON in first message")
    except asyncio.TimeoutError:
        raise WebSocketException(code=1008, reason="Timeout waiting for first message")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during authentication")
        raise

@router.websocket("/{path}")
async def websocket_endpoint(websocket: WebSocket, bot_id=Depends(verify_bot_connection)):
    logger.info(f"WebSocket connection established for bot_id: {bot_id}")
    await bot_connections_manager.add_bot(bot_id, websocket)
    try:
        while True:
            data = await bot_connections_manager.listen_bot()
            if data:
                logger.debug(f"Received message: {data}")
    except WebSocketDisconnect:
        logger.info(f"Bot {bot_id} disconnected.")
        await bot_connections_manager.remove_bot()
    except Exception as e:
        logger.error(f"Unexpected error in websocket endpoint: {e}")
        await bot_connections_manager.remove_bot()