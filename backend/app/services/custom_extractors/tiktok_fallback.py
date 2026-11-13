import httpx

from app.services.custom_extractors.base import ExtractedItem, ExtractorResult
from app.services.url_cleaner import MOBILE_UA


def parse_tikwm_payload(payload: dict) -> ExtractorResult | None:
    """Parse TikWM JSON response into watermark-free video or photo carousel items."""
    if payload.get("code") != 0:
        return None
    data = payload.get("data") or {}
    if not data:
        return None

    title = (data.get("title") or "TikTok Video").strip()
    author = ((data.get("author") or {}).get("nickname") or "").strip() or None
    thumbnail = data.get("cover") or data.get("origin_cover")
    headers = {"User-Agent": MOBILE_UA}

    # Photo Mode carousel
    images = data.get("images") or []
    if images:
        items = [
            ExtractedItem(type="image", source_url=img_url, ext="jpg", headers=headers)
            for img_url in images
            if isinstance(img_url, str) and img_url.startswith("http")
        ]
        if items:
            return ExtractorResult(
                platform="tiktok",
                title=title,
                author=author,
                thumbnail=thumbnail,
                items=items,
            )

    video_url = data.get("hdplay") or data.get("play")
    if not video_url:
        return None

    return ExtractorResult(
        platform="tiktok",
        title=title,
        author=author,
        thumbnail=thumbnail,
        items=[
            ExtractedItem(
                type="video",
                source_url=video_url,
                ext="mp4",
                headers=headers,
                duration=float(data["duration"]) if data.get("duration") else None,
            )
        ],
    )


async def extract_tiktok_fallback(url: str, timeout: float = 15.0) -> ExtractorResult | None:
    """Fallback watermark-free TikTok & Photo Mode extractor via TikWM public API."""
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": MOBILE_UA},
    ) as client:
        resp = await client.get(
            "https://www.tikwm.com/api/",
            params={"url": url, "hd": 1},
        )
        if resp.status_code != 200:
            return None
        try:
            payload = resp.json()
        except ValueError:
            return None
        return parse_tikwm_payload(payload)
