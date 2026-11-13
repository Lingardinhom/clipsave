from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthResponse, ShortcutVersionResponse
from app.services.media_processor import is_ffmpeg_available
from app.services.ytdlp_service import get_ytdlp_version

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        ffmpeg_available=is_ffmpeg_available(),
        ytdlp_version=get_ytdlp_version(),
    )


@router.get("/api/v1/shortcut/version", response_model=ShortcutVersionResponse)
async def shortcut_version() -> ShortcutVersionResponse:
    return ShortcutVersionResponse(
        version=settings.shortcut_version,
        notes="ClipSave v1.0.0 — Hỗ trợ tải video đa nền tảng không watermark chuẩn iPhone Photos.",
        icloud_url=settings.shortcut_icloud_url or None,
    )
