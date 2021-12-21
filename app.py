from fastapi import FastAPI

from dao.base import *
from webapp.routers import position


app = FastAPI(title='Vyapari', description='APIs for Vyapari', version='0.1')
app.include_router(position.router_position)


@app.get("/")
async def root():
    return {"message": "Running Vyapari! ..."}


@app.on_event("startup")
async def startup():
    print("Connecting DB ...")
    if conn.is_closed():
        conn.connect()


@app.on_event("shutdown")
async def shutdown():
    print("Closing DB connection...")
    if not conn.is_closed():
        conn.close()
