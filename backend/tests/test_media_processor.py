import asyncio
from pathlib import Path

import pytest

from app.services.media_processor import (
    convert_to_audio,
    ensure_ios_compatible_video,
    is_ffmpeg_available,
    is_ios_photos_compatible,
    probe_media,
)


@pytest.mark.skipif(not is_ffmpeg_available(), reason="ffmpeg not installed")
async def test_ffmpeg_converts_incompatible_video_and_audio(tmp_path: Path):
    # Create a 1-second MPEG-4 Part 2 + Vorbis MKV/AVI or WebM-like video (not iOS Photos compatible)
    src_mkv = tmp_path / "sample.mkv"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-c:v",
        "mpeg4",
        "-c:a",
        "libvorbis",
        str(src_mkv),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode == 0
    assert src_mkv.exists()

    before_info = await probe_media(src_mkv)
    assert not is_ios_photos_compatible(src_mkv, before_info)

    mp4_path, after_info = await ensure_ios_compatible_video(src_mkv)
    assert mp4_path.exists()
    assert mp4_path.suffix == ".mp4"
    assert after_info.video_codec == "h264"
    assert after_info.audio_codec == "aac"
    assert is_ios_photos_compatible(mp4_path, after_info)

    # Also test audio extraction to m4a
    m4a_path, audio_info = await convert_to_audio(mp4_path, "m4a")
    assert m4a_path.exists()
    assert m4a_path.suffix == ".m4a"
    assert audio_info.audio_codec == "aac"
