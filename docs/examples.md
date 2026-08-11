# Runnable examples (sync and async)

> Copy-paste friendly scripts under [`examples/`](https://github.com/vsmutok/ytscrape/tree/main/examples) — each feature ships both `YouTube` and `AsyncYouTube` variants.

The repository includes short scripts you can run against a live YouTube
connection. Feature examples expose **both** APIs in one file:

- **Sync** — `run_sync()` with `YouTube` (default)
- **Async** — `run_async()` with `AsyncYouTube` (`--async` flag)

## Install

=== "pip"

    ```bash
    pip install ytscrape
    pip install "ytscrape[async]"   # for --async and the concurrency example
    ```

=== "uv"

    ```bash
    uv add ytscrape
    uv add "ytscrape[async]"
    ```

Clone the repo (or open it after install) and run from the project root:

```bash
python examples/01_search_videos.py
python examples/01_search_videos.py --async
python examples/10_async_concurrency.py
```

## Catalogue

| Script | Topic |
| ------ | ----- |
| [`01_search_videos.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/01_search_videos.py) | Search with `SearchFilter.VIDEOS` |
| [`02_search_channels_playlists.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/02_search_channels_playlists.py) | Channels and playlists |
| [`03_video_details.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/03_video_details.py) | `video()` metadata |
| [`04_pagination.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/04_pagination.py) | Transparent vs manual pages |
| [`05_language_region.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/05_language_region.py) | `language` / `region` / `Locale` |
| [`06_error_handling.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/06_error_handling.py) | `ParseError`, `RequestError`, `YtScraperError` |
| [`07_video_comments.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/07_video_comments.py) | Comments, replies, `CommentSort.NEWEST` |
| [`08_channel_details.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/08_channel_details.py) | `channel()` metadata |
| [`09_transcript.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/09_transcript.py) | Caption tracks and transcripts |
| [`10_async_concurrency.py`](https://github.com/vsmutok/ytscrape/blob/main/examples/10_async_concurrency.py) | `asyncio.gather` + `max_concurrency` (async only) |

## Sync ↔ async mapping

| Sync | Async |
| ---- | ----- |
| `with YouTube() as yt:` | `async with AsyncYouTube() as yt:` |
| `for item in yt.search(...)` | `async for item in await yt.search(...)` |
| `yt.video(...)` / `yt.channel(...)` | `await yt.video(...)` / `await yt.channel(...)` |
| `for c in yt.comments(...)` | `async for c in await yt.comments(...)` |
| `yt.transcript(...)` | `await yt.transcript(...)` |

Models (`Video`, `Comment`, `VideoDetails`, `Transcript`, …) are identical —
only I/O and iteration differ. See the [Async API guide](guides/async.md) for
concurrency limits, retries, and fan-out patterns.

!!! warning

    Examples call live YouTube endpoints. Prefer small `max_results`, reuse one
    client, and avoid aggressive parallel crawls.

## Next steps

* [Quickstart](quickstart.md) — first search, details, and comments
* [Async API](guides/async.md) — `AsyncYouTube` in depth
* [API reference](api/youtube.md) — full method signatures
