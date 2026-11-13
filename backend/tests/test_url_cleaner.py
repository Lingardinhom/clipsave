import pytest

from app.services.url_cleaner import (
    UnsafeURLError,
    detect_platform,
    extract_url,
    validate_public_url,
)


def test_extract_url_from_noisy_douyin_share_text():
    raw = "8.74 复制打开抖音，看看【测试账号的作品】太好看了！ https://v.douyin.com/iRNB5abc/ 01/15"
    assert extract_url(raw) == "https://v.douyin.com/iRNB5abc/"


def test_extract_url_from_xiaohongshu_text():
    raw = "小红书好物分享 http://xhslink.com/a/xyz123，复制本条信息"
    assert extract_url(raw) == "http://xhslink.com/a/xyz123"


def test_extract_url_invalid_raises():
    with pytest.raises(ValueError):
        extract_url("chỉ có văn bản không có link")


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1:8000/admin",
        "http://localhost/secret",
        "http://192.168.1.1/login",
        "http://169.254.169.254/latest/meta-data/",
        "http://mybox.local/api",
        "ftp://example.com/file.mp4",
    ],
)
def test_validate_public_url_blocks_ssrf(bad_url: str):
    with pytest.raises(UnsafeURLError):
        validate_public_url(bad_url)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.tiktok.com/@user/video/12345", "tiktok"),
        ("https://vt.tiktok.com/ZSYabc/", "tiktok"),
        ("https://www.douyin.com/video/7345678901234567890", "douyin"),
        ("https://www.xiaohongshu.com/explore/65abc", "xiaohongshu"),
        ("https://www.instagram.com/reel/C8xyz/", "instagram"),
        ("https://www.threads.net/@user/post/123", "threads"),
        ("https://www.facebook.com/reel/999", "facebook"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "youtube"),
        ("https://x.com/user/status/123456", "twitter"),
        ("https://www.pinterest.com/pin/123/", "pinterest"),
        ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili"),
    ],
)
def test_detect_platform(url: str, expected: str):
    assert detect_platform(url) == expected
