import pytest

from media import HLS, Direct, Page, YouTube, classify


@pytest.mark.parametrize("url, expected", [
    ("https://www.youtube.com/watch?v=FRn45upT5HA", YouTube("FRn45upT5HA")),
    ("https://youtube.com/watch?v=FRn45upT5HA&t=42s", YouTube("FRn45upT5HA")),
    ("https://m.youtube.com/watch?v=FRn45upT5HA", YouTube("FRn45upT5HA")),
    ("https://music.youtube.com/watch?v=FRn45upT5HA&list=PL123", YouTube("FRn45upT5HA", "PL123")),
    ("https://youtu.be/FRn45upT5HA?si=abc", YouTube("FRn45upT5HA")),
    ("https://www.youtube.com/shorts/abc123", YouTube("abc123")),
    ("https://www.youtube.com/live/abc123?feature=share", YouTube("abc123")),
    ("https://www.youtube.com/embed/abc123", YouTube("abc123")),
    ("  https://www.youtube.com/watch?v=FRn45upT5HA  ", YouTube("FRn45upT5HA")),
])
def test_youtube_links(url, expected):
    assert classify(url) == expected


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/playlist?list=PL123",
    "https://www.youtube.com/@somechannel",
    "https://www.youtube.com/watch",
    "https://youtu.be/",
])
def test_youtube_links_without_a_video_are_pages(url):
    assert classify(url) == Page(url)


@pytest.mark.parametrize("url, content_type", [
    ("https://example.com/video.mp4", "video/mp4"),
    ("https://example.com/a/CLIP.MP4?sig=abc", "video/mp4"),
    ("http://example.com/stream/index.m3u8", HLS),
    ("https://example.com/manifest.mpd", "application/dash+xml"),
    ("https://example.com/song.mp3", "audio/mpeg"),
    ("https://example.com/photo.jpg", "image/jpeg"),
])
def test_direct_media(url, content_type):
    assert classify(url) == Direct(url, content_type)


def test_direct_keeps_query_string():
    assert classify("https://cdn.example.com/a/CLIP.MP4?sig=abc").url == "https://cdn.example.com/a/CLIP.MP4?sig=abc"


def test_audio_detection():
    assert classify("https://example.com/song.flac").is_audio
    assert not classify("https://example.com/video.webm").is_audio


def test_other_pages():
    assert classify("https://vimeo.com/76979871") == Page("https://vimeo.com/76979871")


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "hello world",
    "youtube.com/watch?v=FRn45upT5HA",
    "ftp://example.com/video.mp4",
    "file:///C:/video.mp4",
    "https://",
    "check this out https://youtu.be/FRn45upT5HA",
    "https://youtu.be/FRn45upT5HA\nsecond line",
])
def test_not_a_castable_url(text):
    assert classify(text) is None
