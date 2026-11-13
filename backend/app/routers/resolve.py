import mimetypes
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.config import settings
from app.models.schemas import ResolveRequest, ResolveResponse
from app.services.resolver import resolve_media
from app.services.storage import storage
from app.services.url_cleaner import UnsafeURLError

router = APIRouter(prefix="/api/v1", tags=["media"])

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = settings.api_key.strip()
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key không hợp lệ hoặc bị thiếu (header X-API-Key).",
        )


def enforce_rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _RATE_BUCKETS[client_ip]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quá nhiều yêu cầu trong 1 phút. Vui lòng thử lại sau giây lát.",
        )
    bucket.append(now)


@router.post(
    "/resolve",
    response_model=ResolveResponse,
    dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)],
)
async def resolve_endpoint(payload: ResolveRequest, request: Request) -> ResolveResponse:
    base_url = settings.public_base_url.strip() or str(request.base_url).rstrip("/")
    try:
        return await resolve_media(payload, base_url=base_url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/download/{job_id}/{filename}")
async def download_media_file(job_id: str, filename: str) -> FileResponse:
    file_path = storage.get_file_path(job_id, filename)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp không tồn tại hoặc đã hết hạn (TTL).",
        )

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if file_path.suffix.lower() == ".mp4":
        mime_type = "video/mp4"
    elif file_path.suffix.lower() == ".m4a":
        mime_type = "audio/mp4"

    return FileResponse(
        path=file_path,
        media_type=mime_type or "application/octet-stream",
        filename=file_path.name,
    )
