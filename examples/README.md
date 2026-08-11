# Examples

Short, runnable scripts for **ytscrape**. Every feature example includes both a
**sync** (`YouTube`) and an **async** (`AsyncYouTube`) implementation.

## Install

```bash
pip install ytscrape
pip install "ytscrape[async]"   # only if you want --async / 10_async_concurrency
```

## Run

From the repository root:

```bash
# Sync (default)
python examples/01_search_videos.py

# Async counterpart of the same script
python examples/01_search_videos.py --async

# Concurrency / fan-out pattern (async only)
python examples/10_async_concurrency.py
```

| Example | What it shows |
| ------- | ------------- |
| [`01_search_videos.py`](01_search_videos.py) | Search videos with `SearchFilter.VIDEOS` (sync + async). |
| [`02_search_channels_playlists.py`](02_search_channels_playlists.py) | Search channels and playlists (sync + async). |
| [`03_video_details.py`](03_video_details.py) | Fetch `VideoDetails` by id or URL (sync + async). |
| [`04_pagination.py`](04_pagination.py) | Transparent iteration and manual pages (sync + async). |
| [`05_language_region.py`](05_language_region.py) | Localise with `language` / `region` / `Locale` (sync + async). |
| [`06_error_handling.py`](06_error_handling.py) | Catch `ParseError`, `RequestError`, `YtScraperError` (sync + async). |
| [`07_video_comments.py`](07_video_comments.py) | Comments, replies, `CommentSort.NEWEST` (sync + async). |
| [`08_channel_details.py`](08_channel_details.py) | Fetch `ChannelDetails` by id, handle or URL (sync + async). |
| [`09_transcript.py`](09_transcript.py) | List caption tracks and fetch a transcript (sync + async). |
| [`10_async_concurrency.py`](10_async_concurrency.py) | Parallel `asyncio.gather` with `max_concurrency` (async only). |

## Pattern used in each file

```python
def run_sync() -> None:
    with YouTube() as yt:
        ...


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        ...


# CLI: default = sync, pass --async for AsyncYouTube
```

Async iteration differs only in the I/O surface:

| Sync | Async |
| ---- | ----- |
| `for item in yt.search(...)` | `async for item in await yt.search(...)` |
| `yt.video(...)` | `await yt.video(...)` |
| `for c in yt.comments(...)` | `async for c in await yt.comments(...)` |

Full guides and API reference: [docs site](https://vsmutok.github.io/ytscrape/).

> These examples hit YouTube's private endpoints and need a network connection.
> Use the library responsibly.
