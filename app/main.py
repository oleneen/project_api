from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db, init_db_async
from .endpoints.public import router as public_router
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация схемы БД через AsyncEngine при старте
    await init_db_async()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(public_router, prefix="/api/v1/public")


@app.get("/")
def read_root():
    return {"message": "API работает!"}


@app.get("/ping")
async def ping(session: AsyncSession = Depends(get_db)):
    result = await session.execute("SELECT * FROM users;")
    return {"result": result.scalar()}
