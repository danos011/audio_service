from fastapi import APIRouter

from .audio import audio_router

router = APIRouter(prefix="/api")
router.include_router(audio_router)
