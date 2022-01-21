from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse

from app import templates


route = APIRouter(
    prefix="/ui",
    tags=["ui"]
)


@route.get("/index", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
