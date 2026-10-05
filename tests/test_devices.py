import asyncio
from types import SimpleNamespace

import devices


def test_cast_subtitle():
    assert devices.cast_subtitle(None) == "Chromecast"
    assert devices.cast_subtitle("Chromecast Ultra") == "Chromecast Ultra"
    assert devices.cast_subtitle("Google TV Streamer") == "Chromecast · Google TV Streamer"


def test_unknown_models_are_not_hidden():
    device = SimpleNamespace(services=set(), cast_type=None)
    assert devices.supports_video(device, zc=None)


def test_speakers_are_not_video():
    device = SimpleNamespace(services=set(), cast_type="audio")
    assert not devices.supports_video(device, zc=None)


def test_cast_devices_filters_and_sorts(monkeypatch):
    tv = SimpleNamespace(friendly_name="Living Room TV", video=True)
    bedroom = SimpleNamespace(friendly_name="Bedroom TV", video=True)
    speaker = SimpleNamespace(friendly_name="Kitchen speaker", video=False)
    browser = SimpleNamespace(devices={1: tv, 2: speaker, 3: bedroom}, zc=None)
    monkeypatch.setattr(devices, "cast_browser", lambda: browser)
    monkeypatch.setattr(devices, "supports_video", lambda device, zc: device.video)
    assert asyncio.run(devices.cast_devices(video=True)) == [bedroom, tv]
    assert asyncio.run(devices.cast_devices(video=False)) == [bedroom, speaker, tv]


def test_no_browser_means_no_devices(monkeypatch):
    monkeypatch.setattr(devices, "cast_browser", lambda: None)
    assert asyncio.run(devices.cast_devices(video=True)) == []
