import json
import re

import httpx

from app.services.custom_extractors.base import ExtractedItem, ExtractorResult
from app.services.url_cleaner import MOBILE_UA

INITIAL_STATE_RE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.DOTALL)


def parse_xiaohongshu_html(html: str) -> ExtractorResult | None:
    """Parse window.__INITIAL_STATE__ from Xiaohongshu note page."""
    match = INITIAL_STATE_RE.search(html)
    if not match:
        return None

    raw_json = match.group(1).replace(":undefined", ":null")
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None

    note_data = data.get("note") or {}
    note_detail_map = note_data.get("noteDetailMap") or {}
    note = None

    first_note_id = note_data.get("firstNoteId")
    if first_note_id and first_note_id in note_detail_map:
        note = (note_detail_map[first_note_id] or {}).get("note")

    if not note:
        for entry in note_detail_map.values():
            if isinstance(entry, dict) and entry.get("note"):
                note = entry["note"]
                break

    if not note:
        return None

    title = (note.get("title") or note.get("desc") or "Xiaohongshu Note").strip()
    author = ((note.get("user") or {}).get("nickname") or "").strip() or None
    headers = {
        "User-Agent": MOBILE_UA,
        "Referer": "https://www.xiaohongshu.com/",
    }

    # Check video first
    video = note.get("video") or {}
    media = video.get("media") or {}
    stream = media.get("stream") or {}
    h264_list = stream.get("h264") or stream.get("h265") or []
    if h264_list and isinstance(h264_list, list):
        best_stream = h264_list[0]
        video_url = best_stream.get("masterUrl")
        if not video_url and best_stream.get("backupUrls"):
            video_url = best_stream["backupUrls"][0]
        if video_url:
            return ExtractorResult(
                platform="xiaohongshu",
                title=title,
                author=author,
                items=[
                    ExtractedItem(
                        type="video",
                        source_url=video_url,
                        ext="mp4",
                        headers=headers,
                        width=best_stream.get("width"),
                        height=best_stream.get("height"),
                        duration=best_stream.get("duration"),
                    )
                ],
            )

    consumer = video.get("consumer") or {}
    origin_key = consumer.get("originVideoKey")
    if origin_key:
        return ExtractorResult(
            platform="xiaohongshu",
            title=title,
            author=author,
            items=[
                ExtractedItem(
                    type="video",
                    source_url=f"https://sns-video-bd.xhscdn.com/{origin_key.lstrip('/')}",
                    ext="mp4",
                    headers=headers,
                )
            ],
        )

    # Image carousel
    image_list = note.get("imageList") or []
    items: list[ExtractedItem] = []
    for img in image_list:
        img_url = img.get("urlDefault") or img.get("urlPre") or ""
        if not img_url and img.get("infoList"):
            img_url = img["infoList"][0].get("url", "")
        if img_url:
            if img_url.startswith("//"):
                img_url = f"https:{img_url}"
            items.append(
                ExtractedItem(
                    type="image",
                    source_url=img_url,
                    ext="jpg",
                    headers=headers,
                    width=img.get("width"),
                    height=img.get("height"),
                )
            )

    if items:
        return ExtractorResult(
            platform="xiaohongshu",
            title=title,
            author=author,
            thumbnail=items[0].source_url,
            items=items,
        )
    return None


async def extract_xiaohongshu(url: str, timeout: float = 15.0) -> ExtractorResult | None:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    ) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        return parse_xiaohongshu_html(resp.text)
