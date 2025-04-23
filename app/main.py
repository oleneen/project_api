from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API работает!"}

@app.get("/ping")
async def ping(session: AsyncSession = Depends(get_db)):
    result = await session.execute("SELECT * FROM users;")
    return {"result": result.scalar()}
