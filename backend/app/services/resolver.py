import mimetypes
from pathlib import Path
from urllib.parse import quote

import httpx

from app.models.schemas import MediaItem, ResolveRequest, ResolveResponse
from app.services.custom_extractors.base import ExtractorResult
from app.services.custom_extractors.douyin import extract_douyin
from app.services.custom_extractors.tiktok_fallback import extract_tiktok_fallback
from app.services.custom_extractors.xiaohongshu import extract_xiaohongshu
from app.services.media_processor import (
    convert_to_audio,
    ensure_ios_compatible_video,
    probe_media,
)
from app.services.storage import sanitize_filename, storage
from app.services.url_cleaner import (
    MOBILE_UA,
    UnsafeURLError,
    detect_platform,
    extract_url,
    resolve_short_url,
)
from app.services.ytdlp_service import download_with_ytdlp

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
AUDIO_EXTS = {".m4a", ".mp3", ".aac", ".opus", ".ogg", ".wav"}


def _build_download_url(base_url: str, job_id: str, filename: str) -> str:
    clean_base = base_url.rstrip("/")
    return f"{clean_base}/api/v1/download/{job_id}/{quote(filename)}"


def _guess_mime(path: Path, media_type: str) -> str:
    ext = path.suffix.lower()
    if ext == ".mp4":
        return "video/mp4"
    if ext == ".mov":
        return "video/quicktime"
    if ext == ".m4a":
        return "audio/mp4"
    if ext == ".mp3":
        return "audio/mpeg"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    return f"{media_type}/octet-stream"


async def _finalize_local_file(
    file_path: Path,
    job_id: str,
    base_url: str,
    req: ResolveRequest,
    fallback_width: int | None = None,
    fallback_height: int | None = None,
    fallback_duration: float | None = None,
) -> MediaItem:
    ext = file_path.suffix.lower()

    if ext in IMAGE_EXTS:
        media_type = "image"
        final_path = file_path
        width, height, duration = fallback_width, fallback_height, None
    elif req.mode == "audio" or ext in AUDIO_EXTS:
        media_type = "audio"
        final_path, info = await convert_to_audio(file_path, req.audio_format)
        width, height, duration = None, None, info.duration or fallback_duration
    else:
        media_type = "video"
        if req.ios_compatible:
            final_path, info = await ensure_ios_compatible_video(file_path)
        else:
            info = await probe_media(file_path)
        width = info.width or fallback_width
        height = info.height or fallback_height
        duration = info.duration or fallback_duration

    return MediaItem(
        type=media_type,
        download_url=_build_download_url(base_url, job_id, final_path.name),
        filename=final_path.name,
        mime_type=_guess_mime(final_path, media_type),
        ext=final_path.suffix.lstrip(".").lower(),
        width=width,
        height=height,
        duration=duration,
        size_bytes=final_path.stat().st_size if final_path.exists() else None,
    )


async def _materialize_extractor_result(
    result: ExtractorResult,
    resolved_url: str,
    base_url: str,
    req: ResolveRequest,
) -> ResolveResponse:
    job_id, job_dir = storage.create_job_dir()
    media_items: list[MediaItem] = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=45.0) as client:
        for idx, item in enumerate(result.items, start=1):
            headers = dict(item.headers or {})
            headers.setdefault("User-Agent", MOBILE_UA)

            if req.mode == "audio" and item.type == "image":
                continue

            filename = sanitize_filename(f"clipsave_{idx:02d}.{item.ext}", default_ext=item.ext)
            dest_path = job_dir / filename

            async with client.stream("GET", item.source_url, headers=headers) as resp:
                resp.raise_for_status()
                with dest_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

            final_item = await _finalize_local_file(
                dest_path,
                job_id,
                base_url,
                req,
                fallback_width=item.width,
                fallback_height=item.height,
                fallback_duration=item.duration,
            )
            media_items.append(final_item)

    if not media_items:
        raise RuntimeError("Không tải được tệp media nào từ liên kết này.")

    return ResolveResponse(
        status="ok",
        platform=result.platform,
        resolved_url=resolved_url,
        title=result.title,
        author=result.author,
        thumbnail=result.thumbnail,
        is_carousel=len(media_items) > 1,
        items=media_items,
    )


async def resolve_media(req: ResolveRequest, base_url: str) -> ResolveResponse:
    """Main orchestration pipeline: clean URL -> detect platform -> extract -> iOS-compatible output."""
    cleaned_url = extract_url(req.url)
    canonical_url = await resolve_short_url(cleaned_url)
    platform = detect_platform(canonical_url)

    # 1. Try specialized watermark-free extractors for Asian / Photo-mode platforms first
    if platform == "douyin":
        extracted = await extract_douyin(canonical_url)
        if extracted and extracted.items:
            return await _materialize_extractor_result(extracted, canonical_url, base_url, req)

    if platform == "xiaohongshu":
        extracted = await extract_xiaohongshu(canonical_url)
        if extracted and extracted.items:
            return await _materialize_extractor_result(extracted, canonical_url, base_url, req)

    if platform == "tiktok" and "/photo/" in canonical_url:
        # TikTok Photo Mode (/photo/) is only handled cleanly via TikTok fallback
        extracted = await extract_tiktok_fallback(canonical_url)
        if extracted and extracted.items:
            return await _materialize_extractor_result(extracted, canonical_url, base_url, req)

    # 2. Primary universal engine: yt-dlp
    job_id, job_dir = storage.create_job_dir()
    ytdlp_error: Exception | None = None
    try:
        info = await download_with_ytdlp(
            canonical_url,
            job_dir,
            platform=platform,
            mode=req.mode,
            quality=req.quality,
            audio_format=req.audio_format,
        )
        downloaded_files = sorted(
            [
                p
                for p in job_dir.iterdir()
                if p.is_file() and not p.name.endswith((".part", ".ytdl", ".temp"))
            ]
        )
        if downloaded_files:
            items: list[MediaItem] = []
            for file_path in downloaded_files:
                items.append(await _finalize_local_file(file_path, job_id, base_url, req))

            title = (info.get("title") or "ClipSave Media").strip()
            author = (info.get("uploader") or info.get("channel") or "").strip() or None
            thumbnail = info.get("thumbnail")
            return ResolveResponse(
                status="ok",
                platform=platform,
                resolved_url=canonical_url,
                title=title,
                author=author,
                thumbnail=thumbnail,
                is_carousel=len(items) > 1,
                items=items,
            )
    except Exception as exc:  # noqa: BLE001
        ytdlp_error = exc

    # 3. TikTok fallback if yt-dlp failed or returned nothing
    if platform == "tiktok":
        extracted = await extract_tiktok_fallback(canonical_url)
        if extracted and extracted.items:
            return await _materialize_extractor_result(extracted, canonical_url, base_url, req)

    if isinstance(ytdlp_error, UnsafeURLError):
        raise ytdlp_error
    if ytdlp_error:
        raise RuntimeError(f"Không thể tải video từ {platform}: {ytdlp_error}") from ytdlp_error
    raise RuntimeError(f"Không tìm thấy luồng video/ảnh hợp lệ từ {platform}.")
