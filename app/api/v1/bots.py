from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.bot import Bot

router = APIRouter()


@router.post("/bots/", response_model=dict)
async def create_bot(
    bot_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的Bot
    """
    # 创建新的Bot实例
    new_bot = Bot(
        name=bot_data["name"],
        token=bot_data["token"],
        description=bot_data.get("description", "")
    )

    # 添加到数据库会话
    db.add(new_bot)

    # 提交到数据库
    await db.commit()

    # 刷新以获取生成的ID
    await db.refresh(new_bot)

    return {"id": new_bot.id, "name": new_bot.name, "message": "Bot创建成功"}


@router.get("/bots/{bot_id}", response_model=dict)
async def get_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    根据ID获取Bot信息
    """
    # 使用select查询
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if bot is None:
        raise HTTPException(status_code=404, detail="Bot未找到")

    return {
        "id": bot.id,
        "name": bot.name,
        "description": bot.description,
        "is_active": bot.is_active,
        "created_at": bot.created_at
    }


@router.get("/bots/", response_model=list)
async def list_bots(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    获取Bot列表
    """
    # 分页查询
    result = await db.execute(
        select(Bot).offset(skip).limit(limit)
    )
    bots = result.scalars().all()

    return [
        {
            "id": bot.id,
            "name": bot.name,
            "is_active": bot.is_active,
            "created_at": bot.created_at
        }
        for bot in bots
    ]


@router.put("/bots/{bot_id}", response_model=dict)
async def update_bot(
    bot_id: int,
    bot_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    更新Bot信息
    """
    # 查找现有Bot
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if bot is None:
        raise HTTPException(status_code=404, detail="Bot未找到")

    # 更新字段
    if "name" in bot_data:
        bot.name = bot_data["name"]
    if "description" in bot_data:
        bot.description = bot_data["description"]
    if "is_active" in bot_data:
        bot.is_active = bot_data["is_active"]

    # 提交更改
    await db.commit()
    await db.refresh(bot)

    return {"id": bot.id, "name": bot.name, "message": "Bot更新成功"}


@router.delete("/bots/{bot_id}", response_model=dict)
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除Bot
    """
    # 查找要删除的Bot
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if bot is None:
        raise HTTPException(status_code=404, detail="Bot未找到")

    # 删除Bot
    await db.delete(bot)
    await db.commit()

    return {"message": "Bot删除成功"}