import re
import shutil
import time
import uuid
from pathlib import Path

from app.config import settings

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, default_ext: str = "mp4") -> str:
    base = Path(name).name.strip()
    cleaned = SAFE_FILENAME_RE.sub("_", base).strip("._")
    if not cleaned:
        cleaned = f"clipsave_{uuid.uuid4().hex[:8]}.{default_ext}"
    if "." not in cleaned:
        cleaned = f"{cleaned}.{default_ext}"
    return cleaned[:120]


class StorageManager:
    """Manages temporary downloaded files with TTL auto-cleanup."""

    def __init__(self, base_dir: Path | None = None, ttl_seconds: int | None = None) -> None:
        self.base_dir = Path(base_dir or settings.temp_dir)
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.file_ttl_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_job_dir(self) -> tuple[str, Path]:
        job_id = uuid.uuid4().hex
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_id, job_dir

    def get_file_path(self, job_id: str, filename: str) -> Path | None:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            return None
        safe_name = Path(filename).name
        if safe_name != filename or safe_name in {"", ".", ".."}:
            return None
        candidate = (self.base_dir / job_id / safe_name).resolve()
        expected_parent = (self.base_dir / job_id).resolve()
        if candidate.parent != expected_parent or not candidate.is_file():
            return None
        return candidate

    def cleanup_expired(self) -> int:
        if not self.base_dir.exists():
            return 0
        now = time.time()
        removed = 0
        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                age = now - entry.stat().st_mtime
                if age > self.ttl_seconds:
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
            except OSError:
                continue
        return removed

    def clear_all(self) -> None:
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
            self.base_dir.mkdir(parents=True, exist_ok=True)


storage = StorageManager()
