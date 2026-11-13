from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ExtractedItem:
    type: Literal["video", "image", "audio"]
    source_url: str
    ext: str = "mp4"
    headers: dict[str, str] = field(default_factory=dict)
    width: int | None = None
    height: int | None = None
    duration: float | None = None


@dataclass
class ExtractorResult:
    platform: str
    title: str
    author: str | None = None
    thumbnail: str | None = None
    items: list[ExtractedItem] = field(default_factory=list)
