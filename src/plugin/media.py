import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import ParseResult, parse_qs, urlparse

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
YOUTUBE_VIDEO_PATHS = {"shorts", "live", "embed"}
HLS = "application/x-mpegURL"
CONTENT_TYPES = {
    "mp4": "video/mp4",
    "m4v": "video/mp4",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "mov": "video/quicktime",
    "m3u8": HLS,
    "mpd": "application/dash+xml",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "opus": "audio/ogg",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


@dataclass(frozen=True)
class YouTube:
    video_id: str
    playlist_id: str | None = None


@dataclass(frozen=True)
class Direct:
    url: str
    content_type: str
    live: bool = False

    @property
    def is_audio(self) -> bool:
        return self.content_type.startswith("audio/")


@dataclass(frozen=True)
class Page:
    url: str


Media = YouTube | Direct | Page


def classify(text: str) -> Media | None:
    text = text.strip()
    if not text or any(char.isspace() for char in text):
        return None
    url = urlparse(text)
    if url.scheme not in ("http", "https") or not url.hostname:
        return None
    return youtube(url) or direct(url, text) or Page(text)


def youtube(url: ParseResult) -> YouTube | None:
    params = parse_qs(url.query)
    parts = url.path.strip("/").split("/")
    if url.hostname == "youtu.be":
        video_id = parts[0]
    elif url.hostname not in YOUTUBE_HOSTS:
        return None
    elif parts[0] == "watch":
        video_id = first(params, "v")
    elif parts[0] in YOUTUBE_VIDEO_PATHS and len(parts) > 1:
        video_id = parts[1]
    else:
        return None
    return YouTube(video_id, first(params, "list")) if video_id else None


def direct(url: ParseResult, text: str) -> Direct | None:
    extension = PurePosixPath(url.path).suffix.lstrip(".").lower()
    content_type = CONTENT_TYPES.get(extension)
    return Direct(text, content_type) if content_type else None


def first(params: dict[str, list[str]], name: str) -> str | None:
    values = params.get(name)
    return values[0] if values else None


FORMAT = "best[vcodec!=?none][acodec!=?none][ext=mp4]/best[vcodec!=?none][acodec!=?none]/best"
YT_DLP_LOGGER = logging.getLogger("flow-cast.yt-dlp")


def resolve(page: Page) -> Direct | YouTube:
    import yt_dlp

    options = {
        "format": FORMAT,
        "noplaylist": True,
        "extract_flat": "in_playlist",
        "playlist_items": "1",
        "lazy_playlist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": YT_DLP_LOGGER,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(page.url, download=False)
    if info and info.get("_type") in ("playlist", "multi_video"):
        return first_youtube_video(info)
    if not info or not info.get("url"):
        raise LookupError("No playable media found on this page.")
    return Direct(info["url"], content_type_of(info), live=bool(info.get("is_live")))


def first_youtube_video(playlist: dict) -> YouTube:
    entry = next(iter(playlist.get("entries") or []), None)
    if entry and entry.get("_type") == "playlist":
        return first_youtube_video(entry)
    if not entry or entry.get("ie_key") != "Youtube" or not entry.get("id"):
        raise LookupError("No playable media found on this page.")
    url = urlparse(playlist.get("webpage_url") or "")
    return YouTube(entry["id"], first(parse_qs(url.query), "list"))


def content_type_of(info: dict) -> str:
    if str(info.get("protocol", "")).startswith("m3u8"):
        return HLS
    return CONTENT_TYPES.get(info.get("ext", ""), "video/mp4")
