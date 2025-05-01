from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db, init_db_async
from .endpoints.public import router as public_router
from contextlib import asynccontextmanager
from .endpoints.admin import router as admin_router 
from .endpoints.balance import router as balance_router 
from .endpoints.order import router as order_router 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация схемы БД через AsyncEngine при старте
    await init_db_async()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(order_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1/public")
app.include_router(admin_router, prefix="/api/v1/admin") 
app.include_router(balance_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "API работает!"}


@app.get("/ping")
async def ping(session: AsyncSession = Depends(get_db)):
    result = await session.execute("SELECT * FROM users;")
    return {"result": result.scalar()}
