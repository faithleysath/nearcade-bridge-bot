from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.websocket import router as websocket_router

app = FastAPI(
    title="Nearcade Bridge Bot API",
    description="API for Nearcade bridge bot operations",
    version="1.0.0"
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


@app.get("/")
async def root():
    return {"message": "Nearcade Bridge Bot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)