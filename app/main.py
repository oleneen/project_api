from fastapi import FastAPI
from .database import engine
from .models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API работает!"}