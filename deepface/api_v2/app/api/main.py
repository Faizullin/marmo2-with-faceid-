from fastapi import APIRouter

from app.api.routes import (
    user_face_id_auth,
    user_face_id_register
)

api_router = APIRouter()
api_router.include_router(user_face_id_auth.router, tags=["user_face_id/auth"])
api_router.include_router(user_face_id_register.router, tags=["user_face_id/register"])
