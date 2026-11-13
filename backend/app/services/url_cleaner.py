import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

URL_REGEX = re.compile(r"https?://[^\s<>\"'\)\]\u3000-\u303f\uff00-\uffef]+", re.IGNORECASE)

SHORT_LINK_HOSTS = {
    "vt.tiktok.com",
    "vm.tiktok.com",
    "v.douyin.com",
    "xhslink.com",
    "fb.watch",
    "pin.it",
    "t.co",
    "b23.tv",
    "youtu.be",
    "bit.ly",
    "tinyurl.com",
    "v.kuaishou.com",
}

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


class UnsafeURLError(ValueError):
    """Raised when a URL is malformed or points to a private/internal network."""


def extract_url(raw_input: str) -> str:
    """Extract the first HTTP/HTTPS URL from noisy share text (Douyin, XHS, TikTok, etc.)."""
    if not raw_input or not raw_input.strip():
        raise ValueError("Không tìm thấy đường dẫn hợp lệ trong dữ liệu đầu vào.")

    match = URL_REGEX.search(raw_input.strip())
    if not match:
        raise ValueError("Không tìm thấy URL (http/https) trong nội dung chia sẻ.")

    url = match.group(0).rstrip(".,!?;:\"'")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL không đúng định dạng http/https.")
    return url


def validate_public_url(url: str) -> str:
    """Block SSRF attempts targeting localhost, private networks, or link-local metadata IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Chỉ hỗ trợ giao thức http và https.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise UnsafeURLError("URL thiếu tên miền hợp lệ.")

    if hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or hostname.endswith(".local"):
        raise UnsafeURLError("Không cho phép truy cập địa chỉ nội bộ.")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeURLError("Không cho phép truy cập địa chỉ IP nội bộ.")
    except ValueError:
        # Hostname is a domain name; try resolving DNS to verify it is not internal
        try:
            infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            for info in infos:
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                ):
                    raise UnsafeURLError("Tên miền trỏ về địa chỉ IP nội bộ.")
        except socket.gaierror:
            # Allow downstream extractor to handle or fail cleanly if DNS is unreachable in offline tests
            pass

    return url


async def resolve_short_url(url: str, timeout: float = 12.0) -> str:
    """Follow redirects on known short links so platform detection and extractors get the canonical URL."""
    validate_public_url(url)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host not in SHORT_LINK_HOSTS:
        return url

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": MOBILE_UA},
    ) as client:
        try:
            resp = await client.head(url)
            final_url = str(resp.url)
            if final_url and final_url != url:
                validate_public_url(final_url)
                return final_url
        except httpx.HTTPError:
            pass

        try:
            async with client.stream("GET", url) as resp:
                final_url = str(resp.url)
                if final_url:
                    validate_public_url(final_url)
                    return final_url
        except httpx.HTTPError:
            return url

    return url


def detect_platform(url: str) -> str:
    """Identify the source social platform from URL hostname."""
    host = (urlparse(url).hostname or "").lower()
    if "tiktok.com" in host:
        return "tiktok"
    if "douyin.com" in host or "iesdouyin.com" in host:
        return "douyin"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    if "instagram.com" in host or "instagr.am" in host:
        return "instagram"
    if "threads.net" in host or "threads.com" in host:
        return "threads"
    if "facebook.com" in host or "fb.watch" in host or "fb.com" in host:
        return "facebook"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "twitter.com" in host or host == "x.com" or host.endswith(".x.com") or "t.co" == host:
        return "twitter"
    if "pinterest." in host or "pin.it" in host:
        return "pinterest"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "kuaishou.com" in host:
        return "kuaishou"
    if "soundcloud.com" in host:
        return "soundcloud"
    if "reddit.com" in host or "redd.it" in host:
        return "reddit"
    return "generic"
