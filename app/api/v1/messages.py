from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.db.bot import Bot
from app.db.message import Message

router = APIRouter()


@router.post("/bots/{bot_id}/messages/", response_model=dict)
async def create_message(
    bot_id: int,
    message_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    为指定Bot创建消息
    """
    # 首先检查Bot是否存在
    bot_result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = bot_result.scalar_one_or_none()

    if bot is None:
        raise HTTPException(status_code=404, detail="Bot未找到")

    # 创建新消息
    new_message = Message(
        content=message_data["content"],
        sender=message_data["sender"],
        platform=message_data["platform"],
        bot_id=bot_id
    )

    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    return {
        "id": new_message.id,
        "content": new_message.content,
        "bot_id": new_message.bot_id,
        "message": "消息创建成功"
    }


@router.get("/bots/{bot_id}/messages/", response_model=list)
async def get_bot_messages(
    bot_id: int,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定Bot的所有消息（演示一对多关系）
    """
    # 使用selectinload预加载相关数据
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.messages))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()

    if bot is None:
        raise HTTPException(status_code=404, detail="Bot未找到")

    # 返回消息列表
    messages = list(bot.messages)[skip:skip+limit]

    return [
        {
            "id": msg.id,
            "content": msg.content,
            "sender": msg.sender,
            "platform": msg.platform,
            "created_at": msg.created_at
        }
        for msg in messages
    ]


@router.get("/messages/{message_id}", response_model=dict)
async def get_message_with_bot(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取消息及其关联的Bot信息（演示多对一关系）
    """
    # 查询消息并预加载关联的Bot
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.bot))
        .where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(status_code=404, detail="消息未找到")

    return {
        "id": message.id,
        "content": message.content,
        "sender": message.sender,
        "platform": message.platform,
        "created_at": message.created_at,
        "bot": {
            "id": message.bot.id,
            "name": message.bot.name,
            "is_active": message.bot.is_active
        }
    }