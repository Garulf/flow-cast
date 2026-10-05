import logging

import pytest
import yt_dlp

from media import FORMAT, HLS, Direct, Page, YouTube, resolve


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


def youtube_entry(video_id):
    return {"_type": "url", "ie_key": "Youtube", "id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}


def test_options_stop_after_the_first_playlist_entry(ydl):
    ydl.info = {"url": "https://cdn/v.mp4", "ext": "mp4"}
    resolve(Page("https://x.y/z"))
    options = ydl.options
    assert options["extract_flat"] == "in_playlist"
    assert options["playlist_items"] == "1"
    assert options["lazy_playlist"] is True


def test_youtube_playlist_plays_in_the_youtube_app(ydl):
    ydl.info = {
        "_type": "playlist",
        "id": "PL1",
        "extractor_key": "YoutubeTab",
        "webpage_url": "https://www.youtube.com/playlist?list=PL1",
        "entries": iter([youtube_entry("vid1")]),
    }
    assert resolve(Page("https://www.youtube.com/playlist?list=PL1")) == YouTube("vid1", "PL1")


def test_youtube_channel_plays_its_latest_video(ydl):
    videos_tab = {
        "_type": "playlist",
        "id": "UCabc",
        "webpage_url": "https://www.youtube.com/@somechannel/videos",
        "entries": iter([youtube_entry("vid9")]),
    }
    ydl.info = {
        "_type": "playlist",
        "id": "@somechannel",
        "extractor_key": "YoutubeTab",
        "webpage_url": "https://www.youtube.com/@somechannel",
        "entries": iter([videos_tab]),
    }
    assert resolve(Page("https://www.youtube.com/@somechannel")) == YouTube("vid9")


def test_other_playlists_are_not_playable(ydl):
    ydl.info = {"_type": "playlist", "extractor_key": "Generic", "entries": [{"_type": "url", "url": "https://x.y/1"}]}
    with pytest.raises(LookupError, match="No playable media found on this page."):
        resolve(Page("https://x.y/list"))


def select(formats):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        selector = ydl.build_format_selector(FORMAT)
        context = {"formats": formats, "has_merged_format": False, "incomplete_formats": False}
        return [chosen["format_id"] for chosen in selector(context)]


def test_format_prefers_mp4_when_codecs_are_unknown():
    formats = [
        {"format_id": "ogv", "ext": "ogv", "url": "https://a/0.ogv", "protocol": "https"},
        {"format_id": "mp4", "ext": "mp4", "url": "https://a/1.mp4", "protocol": "https"},
        {"format_id": "avi", "ext": "avi", "url": "https://a/2.avi", "protocol": "https"},
    ]
    assert select(formats) == ["mp4"]


def test_format_skips_video_only_streams():
    formats = [
        {"format_id": "webm", "ext": "webm", "vcodec": "vp9", "acodec": "opus", "url": "https://a/0.webm", "protocol": "https"},
        {"format_id": "mp4-video", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "url": "https://a/1.mp4", "protocol": "https"},
    ]
    assert select(formats) == ["webm"]
