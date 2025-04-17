from fastapi import FastAPI
from .database import engine
from .models import Base
from apscheduler.schedulers.background import BackgroundScheduler
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API работает!"}

@app.on_event("startup")
def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(match_orders, 'interval', seconds=5, args=[SessionLocal()])
    scheduler.start()