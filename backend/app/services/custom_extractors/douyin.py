import json
import re
from urllib.parse import urlparse

import httpx

from app.services.custom_extractors.base import ExtractedItem, ExtractorResult
from app.services.url_cleaner import MOBILE_UA

DOUYIN_ID_RE = re.compile(r"(?:/video/|/note/|modal_id=)(\d+)")
ROUTER_DATA_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", re.DOTALL)


def extract_douyin_id(url: str) -> str | None:
    match = DOUYIN_ID_RE.search(url)
    if match:
        return match.group(1)
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    for part in reversed(path_parts):
        if part.isdigit() and len(part) >= 10:
            return part
    return None


def parse_douyin_router_data(html: str) -> ExtractorResult | None:
    """Parse window._ROUTER_DATA JSON from iesdouyin share page."""
    match = ROUTER_DATA_RE.search(html)
    if not match:
        return None

    raw_json = match.group(1).replace("undefined", "null")
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None

    loader_data = data.get("loaderData") or {}
    item_list = None
    for value in loader_data.values():
        if not isinstance(value, dict):
            continue
        video_info = value.get("videoInfoRes") or {}
        if video_info.get("item_list"):
            item_list = video_info["item_list"]
            break

    if not item_list:
        return None

    item = item_list[0]
    title = (item.get("desc") or "Douyin Video").strip()
    author = ((item.get("author") or {}).get("nickname") or "").strip() or None

    cover_urls = (((item.get("video") or {}).get("cover") or {}).get("url_list")) or []
    thumbnail = cover_urls[0] if cover_urls else None

    headers = {
        "User-Agent": MOBILE_UA,
        "Referer": "https://www.douyin.com/",
    }

    # Check if photo slideshow / note
    images = item.get("images") or []
    if images:
        extracted: list[ExtractedItem] = []
        for img in images:
            urls = img.get("url_list") or []
            if urls:
                extracted.append(
                    ExtractedItem(
                        type="image",
                        source_url=urls[0],
                        ext="jpg",
                        headers=headers,
                        width=img.get("width"),
                        height=img.get("height"),
                    )
                )
        if extracted:
            return ExtractorResult(
                platform="douyin",
                title=title,
                author=author,
                thumbnail=thumbnail,
                items=extracted,
            )

    # Extract watermark-free video URL
    video = item.get("video") or {}
    play_addr = video.get("play_addr") or {}
    url_list = play_addr.get("url_list") or []
    if not url_list:
        return None

    raw_video_url = url_list[0].replace("/playwm/", "/play/")
    if "ratio=" not in raw_video_url:
        sep = "&" if "?" in raw_video_url else "?"
        raw_video_url = f"{raw_video_url}{sep}ratio=1080p"

    duration_ms = video.get("duration") or item.get("duration")
    duration = float(duration_ms) / 1000.0 if duration_ms and duration_ms > 1000 else duration_ms

    return ExtractorResult(
        platform="douyin",
        title=title,
        author=author,
        thumbnail=thumbnail,
        items=[
            ExtractedItem(
                type="video",
                source_url=raw_video_url,
                ext="mp4",
                headers=headers,
                width=video.get("width"),
                height=video.get("height"),
                duration=float(duration) if duration else None,
            )
        ],
    )


async def extract_douyin(url: str, timeout: float = 15.0) -> ExtractorResult | None:
    """Fetch and extract watermark-free Douyin video or photo slideshow."""
    video_id = extract_douyin_id(url)
    if not video_id:
        return None

    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    ) as client:
        resp = await client.get(share_url)
        if resp.status_code != 200:
            return None
        return parse_douyin_router_data(resp.text)
