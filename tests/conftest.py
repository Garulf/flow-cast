import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

import devices
import flowcast

TV = SimpleNamespace(uuid=UUID(int=1), friendly_name="Living Room TV", model_name="Google TV Streamer")
BEDROOM = SimpleNamespace(uuid=UUID(int=2), friendly_name="Bedroom TV", model_name="Chromecast Ultra")


@pytest.fixture
def launcher():
    launcher = flowcast.plugin.launcher
    launcher.action_keyword = "fc"
    yield launcher
    launcher.action_keyword = ""


@pytest.fixture
def found(monkeypatch):
    """Devices cast_devices returns; records the video flag it was called with."""
    state = SimpleNamespace(devices=[BEDROOM, TV], video=None)

    async def cast_devices(video):
        state.video = video
        return state.devices

    browser = SimpleNamespace(devices={TV.uuid: TV, BEDROOM.uuid: BEDROOM}, zc="zc")
    monkeypatch.setattr(devices, "cast_browser", lambda: browser)
    monkeypatch.setattr(devices, "cast_devices", cast_devices)
    return state


@pytest.fixture
def clipboard_text(monkeypatch):
    state = SimpleNamespace(text=None)
    monkeypatch.setattr(flowcast.clipboard, "read_text", lambda: state.text)
    return state


@pytest.fixture
def messages(launcher, monkeypatch):
    sent = []

    async def invoke(command):
        sent.append(command)

    monkeypatch.setattr(launcher.api, "invoke", invoke)
    return sent


def run_query(text):
    async def collect():
        return [result async for result in flowcast.query(text)]

    return asyncio.run(collect())


def run_cast(uuid, url):
    async def go():
        await flowcast.cast(uuid, url)
        await asyncio.gather(*flowcast._background_tasks)

    asyncio.run(go())
