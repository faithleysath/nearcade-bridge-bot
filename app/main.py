from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.websocket import router as websocket_router
from app.api.v1.bots import router as bots_router
from app.api.v1.messages import router as messages_router
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时可以添加清理逻辑

app = FastAPI(
    title="Nearcade Bridge Bot API",
    description="API for Nearcade bridge bot operations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(prefix="/ws", router=websocket_router, tags=["websocket"])
app.include_router(prefix="/api/v1", router=bots_router, tags=["bots"])
app.include_router(prefix="/api/v1", router=messages_router, tags=["messages"])


@app.get("/")
async def root():
    return {"message": "Nearcade Bridge Bot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)