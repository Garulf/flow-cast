import pychromecast
import pychromecast.quick_play
import pytest

import casting
from media import HLS, Direct, Page, YouTube


class FakeChromecast:
    def __init__(self):
        self.disconnected = False

    def wait(self, timeout):
        pass

    def disconnect(self, timeout):
        self.disconnected = True


@pytest.fixture
def chromecast(monkeypatch):
    fake = FakeChromecast()
    fake.played = []
    monkeypatch.setattr(pychromecast, "get_chromecast_from_cast_info", lambda device, zconf: fake)
    monkeypatch.setattr(
        pychromecast.quick_play, "quick_play",
        lambda cast, app, data, timeout: fake.played.append((app, data)),
    )
    return fake


def test_youtube_goes_to_the_youtube_app(chromecast):
    casting.play("device", "zc", YouTube("FRn45upT5HA", "PL1"))
    assert chromecast.played == [("youtube", {"media_id": "FRn45upT5HA", "playlist_id": "PL1"})]
    assert chromecast.disconnected


def test_direct_goes_to_the_default_media_receiver(chromecast):
    casting.play("device", "zc", Direct("https://cdn/v.mp4", "video/mp4"))
    assert chromecast.played == [(
        "default_media_receiver",
        {"media_id": "https://cdn/v.mp4", "media_type": "video/mp4", "stream_type": "BUFFERED"},
    )]


def test_pages_are_resolved_first(chromecast, monkeypatch):
    monkeypatch.setattr(casting, "resolve", lambda page: Direct("https://cdn/live.m3u8", HLS, live=True))
    casting.play("device", "zc", Page("https://twitch.tv/x"))
    assert chromecast.played[0][1]["stream_type"] == "LIVE"


def test_resolve_failure_never_connects(monkeypatch):
    def fail(page):
        raise LookupError("No playable media found on this page.")

    monkeypatch.setattr(casting, "resolve", fail)
    monkeypatch.setattr(pychromecast, "get_chromecast_from_cast_info", pytest.fail)
    with pytest.raises(LookupError):
        casting.play("device", "zc", Page("https://x.y/z"))


def test_disconnects_when_playback_fails(chromecast, monkeypatch):
    def boom(cast, app, data, timeout):
        raise RuntimeError("app failed to launch")

    monkeypatch.setattr(pychromecast.quick_play, "quick_play", boom)
    with pytest.raises(RuntimeError):
        casting.play("device", "zc", YouTube("x"))
    assert chromecast.disconnected
