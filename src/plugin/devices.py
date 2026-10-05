import asyncio
import logging
import threading

DISCOVERY_WAIT = 3
# "ca" capability bit a cast device advertises over mDNS when it has a screen
CAST_VIDEO_OUT = 1

logger = logging.getLogger("flow-cast.devices")
_browser = None
_browser_lock = threading.Lock()


def cast_browser():
    """Browse for Chromecasts in the background; found devices accumulate in browser.devices."""
    global _browser
    with _browser_lock:
        if _browser is None:
            try:
                from pychromecast.discovery import CastBrowser, SimpleCastListener
                from zeroconf import Zeroconf

                browser = CastBrowser(SimpleCastListener(), Zeroconf())
                browser.start_discovery()
                _browser = browser
            except Exception:  # e.g. the mDNS port may be unavailable
                logger.exception("Chromecast discovery failed")
        return _browser


def supports_video(device, zc) -> bool:
    from pychromecast.const import CAST_TYPE_CHROMECAST
    from pychromecast.models import MDNSServiceInfo
    from zeroconf import ServiceInfo

    for service in device.services:
        if isinstance(service, MDNSServiceInfo):
            info = ServiceInfo("_googlecast._tcp.local.", service.name)
            capabilities = info.properties.get(b"ca") if info.load_from_cache(zc) else None
            if capabilities and capabilities.isdigit():
                return bool(int(capabilities) & CAST_VIDEO_OUT)
    # pychromecast only knows the type of models in its table; don't hide devices it doesn't
    return device.cast_type in (CAST_TYPE_CHROMECAST, None)


def cast_subtitle(model: str | None) -> str:
    if not model:
        return "Chromecast"
    # avoid "Chromecast · Chromecast Ultra"
    return model if "chromecast" in model.lower() else f"Chromecast · {model}"


async def cast_devices(video: bool) -> list:
    browser = await asyncio.to_thread(cast_browser)
    if browser is None:
        return []
    # discovery starts on the first query, so give it a moment if nothing has answered yet
    for _ in range(DISCOVERY_WAIT * 10):
        if browser.devices:
            break
        await asyncio.sleep(0.1)
    found = list(browser.devices.values())
    if video:
        found = [device for device in found if supports_video(device, browser.zc)]
    return sorted(found, key=lambda device: device.friendly_name or "")
