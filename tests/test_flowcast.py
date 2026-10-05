import asyncio
from uuid import UUID

import casting
import flowcast
from conftest import BEDROOM, TV, run_cast, run_query
from launcher import KEEP_OPEN
from media import YouTube

URL = "https://www.youtube.com/watch?v=FRn45upT5HA"


def test_url_lists_devices_in_order(found):
    results = run_query(URL)
    assert [r.title for r in results] == ["Bedroom TV", "Living Room TV"]
    assert [r.subtitle for r in results] == ["Chromecast Ultra", "Chromecast · Google TV Streamer"]
    assert results[0].score > results[1].score
    assert results[0].json_rpc_action["Method"] == "cast"
    assert results[0].json_rpc_action["Parameters"] == [str(BEDROOM.uuid), URL]
    assert found.video is True


def test_audio_urls_include_speakers(found):
    run_query("https://example.com/song.mp3")
    assert found.video is False


def test_no_devices(found):
    found.devices = []
    (result,) = run_query(URL)
    assert result.title == "No Chromecasts found"
    assert result.subtitle == "Make sure this PC and the Chromecast are on the same network"


def test_not_a_url_shows_hint(found):
    (result,) = run_query("hello")
    assert result.title == "Paste a URL to cast"
    assert result.json_rpc_action is None


def test_empty_query_offers_clipboard_url(found, clipboard_text, launcher):
    clipboard_text.text = f"  {URL}\r\n"
    (result,) = run_query("")
    assert result.title == f"Cast {URL}"
    assert result.subtitle == "URL from clipboard"
    assert result.json_rpc_action["Method"] == "change_query"
    assert result.json_rpc_action["Parameters"] == [f"fc {URL}"]


def test_empty_query_without_keyword(found, clipboard_text, launcher):
    launcher.action_keyword = ""
    clipboard_text.text = URL
    (result,) = run_query("")
    assert result.json_rpc_action["Parameters"] == [URL]


def test_empty_query_with_prose_on_clipboard_shows_hint(found, clipboard_text):
    clipboard_text.text = f"watch this {URL}"
    (result,) = run_query("")
    assert result.title == "Paste a URL to cast"


def test_empty_query_with_empty_clipboard_shows_hint(found, clipboard_text):
    (result,) = run_query("")
    assert result.title == "Paste a URL to cast"


def test_change_query_keeps_window_open(messages):
    assert asyncio.run(flowcast.change_query(f"fc {URL}")) == KEEP_OPEN
    assert messages == [{"Method": "Flow.Launcher.ChangeQuery", "Parameters": [f"fc {URL}", False]}]


def test_cast_success(found, messages, monkeypatch):
    played = []
    monkeypatch.setattr(casting, "play", lambda device, zc, media: played.append((device, zc, media)))
    run_cast(str(TV.uuid), URL)
    assert played == [(TV, "zc", YouTube("FRn45upT5HA"))]
    assert messages[0]["Parameters"][:2] == ["Casting to Living Room TV", URL]


def test_cast_failure_reports_reason(found, messages, monkeypatch):
    def fail(device, zc, media):
        raise LookupError("No playable media found on this page.")

    monkeypatch.setattr(casting, "play", fail)
    run_cast(str(TV.uuid), "https://x.y/z")
    assert messages[0]["Parameters"][:2] == ["Couldn't cast to Living Room TV", "No playable media found on this page."]


def test_cast_to_vanished_device(found, messages, monkeypatch):
    monkeypatch.setattr(casting, "play", lambda *args: None)
    run_cast(str(UUID(int=99)), URL)
    assert messages[0]["Parameters"][:2] == ["Couldn't cast to Chromecast", "The Chromecast is no longer on the network."]
