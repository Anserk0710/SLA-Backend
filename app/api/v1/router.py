from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.public_tickets import router as public_ticket_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(public_ticket_router)