import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

from app.config import settings
from app.models.schemas import AudioFormatOption, ModeOption, QualityOption


def get_ytdlp_version() -> str:
    return getattr(yt_dlp.version, "__version__", "unknown")


def build_format_selector(platform: str, mode: ModeOption, quality: QualityOption) -> str:
    if mode == "audio":
        return "bestaudio/best"

    height_filter = ""
    if quality == "1080p":
        height_filter = "[height<=1080]"
    elif quality == "720p":
        height_filter = "[height<=720]"
    elif quality == "480p":
        height_filter = "[height<=480]"

    if platform == "tiktok":
        # Prefer watermark-free H.264 stream over TikTok's watermarked download_addr
        return (
            f"bv*{height_filter}[format_note!*=watermark][vcodec^=h264]+ba/"
            f"b{height_filter}[format_note!*=watermark][vcodec^=h264]/"
            f"bv*{height_filter}[format_note!*=watermark]+ba/"
            f"b{height_filter}[format_note!*=watermark]/"
            f"bv*{height_filter}+ba/b{height_filter}/best"
        )

    return (
        f"bv*{height_filter}[vcodec^=avc1]+ba[acodec^=mp4a]/"
        f"b{height_filter}[ext=mp4][vcodec!*=vp9][vcodec!*=av01]/"
        f"bv*{height_filter}+ba/b{height_filter}/best"
    )


def _sync_download_with_ytdlp(
    url: str,
    job_dir: Path,
    platform: str,
    mode: ModeOption,
    quality: QualityOption,
) -> dict[str, Any]:
    outtmpl = str(job_dir / "%(autonumber)02d_%(id)s.%(ext)s")
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    ydl_opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "format": build_format_selector(platform, mode, quality),
        "merge_output_format": "mp4" if mode != "audio" else None,
        "noplaylist": True,
        "playlistend": 20,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "max_filesize": max_bytes,
        "socket_timeout": 25,
        "retries": 2,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )
        },
    }

    if settings.ytdlp_cookies_file and Path(settings.ytdlp_cookies_file).is_file():
        ydl_opts["cookiefile"] = settings.ytdlp_cookies_file

    # Remove None values
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return info or {}


async def download_with_ytdlp(
    url: str,
    job_dir: Path,
    platform: str,
    mode: ModeOption,
    quality: QualityOption,
    audio_format: AudioFormatOption = "m4a",
) -> dict[str, Any]:
    """Run yt-dlp download asynchronously in a worker thread."""
    return await asyncio.to_thread(
        _sync_download_with_ytdlp,
        url,
        job_dir,
        platform,
        mode,
        quality,
    )
