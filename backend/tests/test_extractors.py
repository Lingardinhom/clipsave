import json

from app.services.custom_extractors.douyin import extract_douyin_id, parse_douyin_router_data
from app.services.custom_extractors.tiktok_fallback import parse_tikwm_payload
from app.services.custom_extractors.xiaohongshu import parse_xiaohongshu_html


def test_douyin_id_extraction():
    assert extract_douyin_id("https://www.douyin.com/video/7345678901234567890") == "7345678901234567890"
    assert extract_douyin_id("https://www.douyin.com/discover?modal_id=7345678901234567890") == "7345678901234567890"


def test_parse_douyin_video_strips_watermark():
    payload = {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "desc": "Clip hay",
                            "author": {"nickname": "Tester"},
                            "video": {
                                "width": 1080,
                                "height": 1920,
                                "duration": 15000,
                                "cover": {"url_list": ["https://img.example.com/c.jpg"]},
                                "play_addr": {
                                    "url_list": ["https://aweme.snssdk.com/aweme/v1/playwm/?video_id=abc"]
                                },
                            },
                        }
                    ]
                }
            }
        }
    }
    html = f"<html><script>window._ROUTER_DATA = {json.dumps(payload)}</script></html>"
    res = parse_douyin_router_data(html)
    assert res is not None
    assert res.platform == "douyin"
    assert res.author == "Tester"
    assert len(res.items) == 1
    assert "/playwm/" not in res.items[0].source_url
    assert "/play/" in res.items[0].source_url
    assert res.items[0].duration == 15.0


def test_parse_xiaohongshu_carousel():
    state = {
        "note": {
            "firstNoteId": "n1",
            "noteDetailMap": {
                "n1": {
                    "note": {
                        "title": "XHS Album",
                        "user": {"nickname": "Alice"},
                        "imageList": [
                            {"urlDefault": "https://ci.xiaohongshu.com/1.jpg", "width": 1080, "height": 1440},
                            {"urlDefault": "//ci.xiaohongshu.com/2.jpg", "width": 1080, "height": 1440},
                        ],
                    }
                }
            },
        }
    }
    html = f"<html><script>window.__INITIAL_STATE__ = {json.dumps(state)}</script></html>"
    res = parse_xiaohongshu_html(html)
    assert res is not None
    assert res.platform == "xiaohongshu"
    assert len(res.items) == 2
    assert res.items[1].source_url.startswith("https://")


def test_parse_tikwm_photo_mode():
    payload = {
        "code": 0,
        "data": {
            "title": "Photo post",
            "author": {"nickname": "TikToker"},
            "images": [
                "https://p16.tiktokcdn.com/img1.jpeg",
                "https://p16.tiktokcdn.com/img2.jpeg",
            ],
        },
    }
    res = parse_tikwm_payload(payload)
    assert res is not None
    assert res.platform == "tiktok"
    assert len(res.items) == 2
    assert all(i.type == "image" for i in res.items)
