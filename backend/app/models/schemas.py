from typing import Literal

from pydantic import BaseModel, Field

QualityOption = Literal["best", "1080p", "720p", "480p"]
ModeOption = Literal["auto", "video", "audio"]
AudioFormatOption = Literal["m4a", "mp3"]


class ResolveRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=4096, description="Raw URL or share text from any platform")
    mode: ModeOption = Field(default="auto", description="auto (video or carousel), video, or audio")
    quality: QualityOption = Field(default="best", description="Target max resolution")
    audio_format: AudioFormatOption = Field(default="m4a", description="Audio format when mode=audio")
    ios_compatible: bool = Field(
        default=True,
        description="Ensure MP4 H.264+AAC output compatible with iPhone Photos app",
    )


class MediaItem(BaseModel):
    type: Literal["video", "image", "audio"]
    download_url: str
    filename: str
    mime_type: str
    ext: str
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    size_bytes: int | None = None


class ResolveResponse(BaseModel):
    status: Literal["ok", "error"]
    platform: str
    resolved_url: str
    title: str
    author: str | None = None
    thumbnail: str | None = None
    is_carousel: bool = False
    items: list[MediaItem] = Field(default_factory=list)
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    ffmpeg_available: bool
    ytdlp_version: str


class ShortcutVersionResponse(BaseModel):
    version: str
    notes: str
    icloud_url: str | None = None
