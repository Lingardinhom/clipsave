from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.config import settings
from app.models.schemas import HealthResponse, ShortcutVersionResponse
from app.services.media_processor import is_ffmpeg_available
from app.services.ytdlp_service import get_ytdlp_version

router = APIRouter(tags=["system"])

SHORTCUT_DIST_DIR = Path(__file__).resolve().parents[3] / "shortcut" / "dist"
ALLOWED_SHORTCUT_FILES = {
    "ClipSave.unsigned.shortcut",
    "ClipSave-1Tap.unsigned.shortcut",
    "ClipSave.shortcut",
    "ClipSave-1Tap.shortcut",
    "ClipSave-iOS-Bundle.zip",
}


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


@router.get("/api/v1/shortcut/files/{filename}")
async def download_shortcut_bundle(filename: str) -> FileResponse:
    if filename not in ALLOWED_SHORTCUT_FILES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp.")
    target = (SHORTCUT_DIST_DIR / filename).resolve()
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp chưa được đóng gói trên server.",
        )
    media_type = "application/zip" if filename.endswith(".zip") else "application/octet-stream"
    return FileResponse(path=target, media_type=media_type, filename=filename)
