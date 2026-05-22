from fastapi import APIRouter
from app.api.v1.endpoints import tickets

router = APIRouter(prefix="/v1")
router.include_router(tickets.router, tags=["tickets"])
