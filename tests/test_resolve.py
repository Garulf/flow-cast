import logging

import pytest
import yt_dlp

from media import FORMAT, HLS, Direct, Page, resolve


class FakeYoutubeDL:
    info = None
    options = None

    def __init__(self, options):
        FakeYoutubeDL.options = options

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        assert download is False
        return self.info


@pytest.fixture
def ydl(monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL


def test_progressive_mp4(ydl):
    ydl.info = {"url": "https://cdn/v.mp4", "ext": "mp4", "protocol": "https"}
    assert resolve(Page("https://vimeo.com/1")) == Direct("https://cdn/v.mp4", "video/mp4")


def test_hls_by_protocol(ydl):
    ydl.info = {"url": "https://cdn/master.m3u8", "ext": "mp4", "protocol": "m3u8_native", "is_live": True}
    assert resolve(Page("https://twitch.tv/x")) == Direct("https://cdn/master.m3u8", HLS, live=True)


def test_unknown_extension_defaults_to_mp4(ydl):
    ydl.info = {"url": "https://cdn/v", "ext": "unknown_video", "protocol": "https"}
    assert resolve(Page("https://x.y/z")).content_type == "video/mp4"


def test_playlist_page_is_not_playable(ydl):
    ydl.info = {"_type": "playlist", "entries": []}
    with pytest.raises(LookupError, match="No playable media found on this page."):
        resolve(Page("https://www.youtube.com/playlist?list=PL1"))


def test_options_keep_stdout_clean(ydl):
    ydl.info = {"url": "https://cdn/v.mp4", "ext": "mp4"}
    resolve(Page("https://x.y/z"))
    options = ydl.options
    assert options["format"] == FORMAT
    assert options["quiet"] and options["no_warnings"] and options["noplaylist"]
    assert isinstance(options["logger"], logging.Logger)
