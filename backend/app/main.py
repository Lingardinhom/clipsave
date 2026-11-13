import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import health, resolve
from app.services.storage import storage


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(60)
        storage.cleanup_expired()


@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.base_dir.mkdir(parents=True, exist_ok=True)
    cleanup_task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API cho phím tắt iPhone ClipSave — Tải video đa nền tảng không watermark.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(resolve.router)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if settings.enable_web_ui and WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
