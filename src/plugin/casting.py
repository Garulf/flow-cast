from media import Direct, Media, Page, YouTube, resolve

CAST_TIMEOUT = 10


def play(device, zconf, media: Media) -> None:
    import pychromecast
    from pychromecast import quick_play

    if isinstance(media, Page):
        media = resolve(media)
    app, data = quick_play_args(media)
    chromecast = pychromecast.get_chromecast_from_cast_info(device, zconf)
    try:
        chromecast.wait(timeout=CAST_TIMEOUT)
        quick_play.quick_play(chromecast, app, data, timeout=CAST_TIMEOUT)
    finally:
        # also stops the connection thread, which otherwise retries forever
        chromecast.disconnect(timeout=CAST_TIMEOUT)


def quick_play_args(media: YouTube | Direct) -> tuple[str, dict]:
    if isinstance(media, YouTube):
        return "youtube", {"media_id": media.video_id, "playlist_id": media.playlist_id}
    return "default_media_receiver", {
        "media_id": media.url,
        "media_type": media.content_type,
        "stream_type": "LIVE" if media.live else "BUFFERED",
    }
