import asyncio
from pathlib import Path
from uuid import UUID

from pyflowlauncher import Plugin, Result

import casting
import clipboard
import devices
from launcher import KEEP_OPEN, CastLauncher
from media import Direct, classify

plugin = Plugin(launcher=CastLauncher())

ICON = str(Path(__file__).resolve().parent.parent / "icon.png")
CAST_ICON = str(Path(__file__).resolve().parent.parent / "cast.png")


def full_query(text: str) -> str:
    keyword = plugin.launcher.action_keyword
    return f"{keyword} {text}" if keyword else text


def hint() -> Result:
    return Result(
        title="Paste a URL to cast",
        subtitle="YouTube links, media files, or any page yt-dlp supports",
        icon=ICON,
    )


def clipboard_result() -> Result:
    text = clipboard.read_text()
    if not text or classify(text) is None:
        return hint()
    url = text.strip()
    return Result(
        title=f"Cast {url}",
        subtitle="URL from clipboard",
        icon=ICON,
    ).add_action(change_query, [full_query(url)])


@plugin.on_method
async def query(query: str):
    asyncio.get_running_loop().run_in_executor(None, devices.cast_browser)
    text = query.strip()
    if not text:
        yield clipboard_result()
        return
    media = classify(text)
    if media is None:
        yield hint()
        return
    audio = isinstance(media, Direct) and media.is_audio
    found = await devices.cast_devices(video=not audio)
    if not found:
        yield Result(
            title="No Chromecasts found",
            subtitle="Make sure this PC and the Chromecast are on the same network",
            icon=ICON,
        )
        return
    for index, device in enumerate(found):
        yield Result(
            title=device.friendly_name,
            subtitle=devices.cast_subtitle(device.model_name),
            icon=CAST_ICON,
            score=len(found) - index,
        ).add_action(cast, [str(device.uuid), text])


@plugin.on_method
async def change_query(query: str):
    await plugin.launcher.api.invoke(plugin.launcher.api.change_query(query))
    return KEEP_OPEN


_background_tasks = set()


def in_background(coro) -> None:
    """Answer the action straight away so Flow isn't left waiting on the cast."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def send_to(device, browser, url: str) -> None:
    name = device.friendly_name if device else "Chromecast"
    try:
        if device is None:
            raise LookupError("The Chromecast is no longer on the network.")
        await asyncio.to_thread(casting.play, device, browser.zc, classify(url))
    except Exception as error:
        plugin.logger.exception("Casting to %s failed", name)
        message = (f"Couldn't cast to {name}", str(error) or type(error).__name__)
    else:
        message = (f"Casting to {name}", url)
    await plugin.launcher.api.invoke(plugin.launcher.api.show_msg(*message, ICON))


@plugin.on_method
async def cast(uuid: str, url: str):
    browser = devices.cast_browser()
    device = browser.devices.get(UUID(uuid)) if browser else None
    in_background(send_to(device, browser, url))
