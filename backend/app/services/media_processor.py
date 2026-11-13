import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaInfo:
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    pix_fmt: str | None = None
    format_name: str | None = None


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


async def probe_media(file_path: Path) -> MediaInfo:
    """Inspect media streams using ffprobe."""
    if not shutil.which("ffprobe"):
        return MediaInfo()

    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0 or not stdout:
        return MediaInfo()

    try:
        data = json.loads(stdout.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return MediaInfo()

    info = MediaInfo()
    fmt = data.get("format") or {}
    info.format_name = fmt.get("format_name")
    if fmt.get("duration"):
        try:
            info.duration = float(fmt["duration"])
        except (TypeError, ValueError):
            pass

    for stream in data.get("streams") or []:
        codec_type = stream.get("codec_type")
        if codec_type == "video" and info.video_codec is None:
            info.video_codec = (stream.get("codec_name") or "").lower()
            info.pix_fmt = (stream.get("pix_fmt") or "").lower()
            info.width = stream.get("width")
            info.height = stream.get("height")
        elif codec_type == "audio" and info.audio_codec is None:
            info.audio_codec = (stream.get("codec_name") or "").lower()

    return info


def is_ios_photos_compatible(file_path: Path, info: MediaInfo) -> bool:
    """Check if video container & codecs can be saved natively to iPhone Photos app."""
    ext = file_path.suffix.lower()
    if ext not in {".mp4", ".mov", ".m4v"}:
        return False
    if info.video_codec not in {"h264", "hevc", "h265"}:
        return False
    if info.video_codec == "h264" and info.pix_fmt and info.pix_fmt not in {"yuv420p", "yuvj420p"}:
        return False
    return not (info.audio_codec and info.audio_codec not in {"aac", "mp3", "alac"})


async def _run_ffmpeg(args: list[str]) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode == 0, stderr.decode("utf-8", errors="ignore")


async def ensure_ios_compatible_video(input_path: Path) -> tuple[Path, MediaInfo]:
    """Remux or transcode video into iPhone Photos-compatible MP4 (H.264 + AAC, faststart)."""
    info = await probe_media(input_path)
    if not is_ffmpeg_available():
        return input_path, info

    if is_ios_photos_compatible(input_path, info):
        return input_path, info

    output_path = input_path.with_name(f"{input_path.stem}_ios.mp4")

    # Fast path: video codec is already H.264/HEVC and audio is AAC/absent -> remux only
    can_copy_video = info.video_codec in {"h264", "hevc", "h265"} and (
        not info.pix_fmt or info.pix_fmt in {"yuv420p", "yuvj420p"}
    )
    can_copy_audio = not info.audio_codec or info.audio_codec in {"aac", "mp3"}

    if can_copy_video and can_copy_audio:
        ok, _ = await _run_ffmpeg(
            ["-i", str(input_path), "-c", "copy", "-movflags", "+faststart", str(output_path)]
        )
        if ok and output_path.exists():
            input_path.unlink(missing_ok=True)
            return output_path, await probe_media(output_path)

    # Video compatible, audio incompatible (e.g. opus/vorbis) -> copy video, encode audio AAC
    if can_copy_video:
        ok, _ = await _run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
        if ok and output_path.exists():
            input_path.unlink(missing_ok=True)
            return output_path, await probe_media(output_path)

    # Full transcode to H.264 yuv420p + AAC (handles VP9, AV1, WebM, 10-bit H.264, etc.)
    ok, err = await _run_ffmpeg(
        [
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    if ok and output_path.exists():
        input_path.unlink(missing_ok=True)
        return output_path, await probe_media(output_path)

    raise RuntimeError(f"Không thể chuyển đổi video sang chuẩn iPhone MP4: {err}")


async def convert_to_audio(input_path: Path, target_format: str = "m4a") -> tuple[Path, MediaInfo]:
    """Extract or convert media file to M4A or MP3."""
    if not is_ffmpeg_available():
        return input_path, await probe_media(input_path)

    target_format = target_format.lower()
    if target_format not in {"m4a", "mp3"}:
        target_format = "m4a"

    if input_path.suffix.lower() == f".{target_format}":
        return input_path, await probe_media(input_path)

    output_path = input_path.with_name(f"{input_path.stem}.{target_format}")
    if target_format == "m4a":
        args = ["-i", str(input_path), "-vn", "-c:a", "aac", "-b:a", "192k", str(output_path)]
    else:
        args = ["-i", str(input_path), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(output_path)]

    ok, err = await _run_ffmpeg(args)
    if ok and output_path.exists():
        input_path.unlink(missing_ok=True)
        return output_path, await probe_media(output_path)

    raise RuntimeError(f"Không thể trích xuất âm thanh {target_format.upper()}: {err}")
