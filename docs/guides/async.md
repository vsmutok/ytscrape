# Use the async API with AsyncYouTube and httpx

> Install the optional `ytscrape[async]` extra, scrape with `AsyncYouTube`, and control concurrency, retries, and backoff for parallel YouTube requests.

ytscrape ships a full **async** surface that mirrors the synchronous [`YouTube`](../api/youtube.md) API. Parsing and models are shared; only the HTTP layer differs (`httpx.AsyncClient` instead of `requests`). Use async when you fan out work across many videos, channels, or searches and want overlapping I/O.

## Install the optional extra

Async support depends on [`httpx`](https://www.python-httpx.org/). It is **not** installed with the base package:

=== "pip"

    ```bash
    pip install "ytscrape[async]"
    ```

=== "uv"

    ```bash
    uv add "ytscrape[async]"
    ```

If you import `AsyncYouTube` without httpx, you get a clear `ImportError` that points at this install command.

## Quick start

```python
import asyncio
from ytscrape import AsyncYouTube, SearchFilter


async def main() -> None:
    async with AsyncYouTube() as yt:
        results = await yt.search(
            "python tutorial",
            filter=SearchFilter.VIDEOS,
            max_results=10,
        )
        async for video in results:
            print(video.title, video.url)

        details = await yt.video("dQw4w9WgXcQ")
        print(details.title, details.views)


asyncio.run(main())
```

Always prefer `async with AsyncYouTube() as yt:` so the underlying `httpx` client is closed cleanly. For manual lifetime management, call `await yt.aclose()` (or `await yt.close()`).

## Same public API as `YouTube`

| Sync (`YouTube`)              | Async (`AsyncYouTube`)                         | Returns                                      |
| ----------------------------- | ---------------------------------------------- | -------------------------------------------- |
| `yt.search(...)`              | `await yt.search(...)`                         | [`AsyncSearchResults`](../api/youtube.md)    |
| `yt.video(...)`               | `await yt.video(...)`                          | same `VideoDetails`                          |
| `yt.channel(...)`             | `await yt.channel(...)`                        | same `ChannelDetails`                        |
| `yt.comments(...)`            | `await yt.comments(...)`                       | [`AsyncCommentThread`](../api/youtube.md)    |
| `yt.transcript(...)`          | `await yt.transcript(...)`                     | same `Transcript`                            |
| `yt.transcripts(...)`         | `await yt.transcripts(...)`                    | same `TranscriptList`                        |

Arguments match the sync facade: `filter`, `max_results`, `include_replies`, `sort`, `languages`, `preserve_formatting`, locale (`language` / `region` / `locale`), and `timeout`.

Models (`Video`, `Comment`, `VideoDetails`, `Transcript`, …) are identical — only iteration and I/O are async.

## Async iteration and pagination

`search` and `comments` return lazy async iterables. The first page is loaded when you `await` the method; further pages load as you iterate.

```python
async with AsyncYouTube() as yt:
    thread = await yt.comments(
        "dQw4w9WgXcQ",
        max_results=500,
        include_replies=True,
        sort="newest",
    )
    async for comment in thread:
        prefix = "  ↳ " if comment.is_reply else ""
        print(f"{prefix}{comment.author}: {comment.text}")
```

Manual paging mirrors the sync API with async methods:

```python
results = await yt.search("python", filter="videos")
page = await results.fetch_next_page()
print(len(page), results.has_more)
```

To materialise everything into a list:

```python
results = await yt.search("python", max_results=50)
items = [item async for item in results]
```

## Concurrency limit, retries, and backoff

The default [`AsyncInnerTubeClient`](../api/innertube-client.md) caps in-flight HTTP calls and retries transient failures (408, 425, 429, 5xx) with exponential backoff and jitter.

```python
async with AsyncYouTube(
    max_concurrency=8,  # max parallel HTTP requests (default 8)
    max_retries=3,  # attempts after the first failure (default 3)
    backoff_factor=0.5,  # base delay in seconds (default 0.5)
    timeout=30.0,
) as yt:
    ...
```

| Parameter           | Default | Role                                                                 |
| ------------------- | ------: | -------------------------------------------------------------------- |
| `max_concurrency`   |       8 | `asyncio.Semaphore` around every HTTP call                           |
| `max_retries`       |       3 | Extra attempts for retryable status codes                           |
| `backoff_factor`    |     0.5 | Base for `factor * 2**attempt` (+ jitter) between retries            |
| `timeout`           |    30.0 | Per-request timeout (seconds)                                        |

These knobs apply when `AsyncYouTube` builds its own client. If you pass `client=AsyncInnerTubeClient(...)`, configure concurrency and retries on that client instead.

## Parallel work across many videos

Pagination for a **single** search or comment thread is still sequential (each page needs the previous continuation token). The real speedup comes from running **independent** operations concurrently — for example several videos at once:

```python
import asyncio
from ytscrape import AsyncYouTube, CommentSort

VIDEO_IDS = ["dQw4w9WgXcQ", "jNQXAC9IVRw", "9bZkp7q19f0"]


async def collect_comments(yt: AsyncYouTube, video_id: str, limit: int = 200) -> int:
    n = 0
    thread = await yt.comments(
        video_id,
        max_results=limit,
        sort=CommentSort.NEWEST,
    )
    async for _ in thread:
        n += 1
    return n


async def main() -> None:
    async with AsyncYouTube(max_concurrency=8) as yt:
        counts = await asyncio.gather(*(collect_comments(yt, vid) for vid in VIDEO_IDS))
        for vid, n in zip(VIDEO_IDS, counts, strict=True):
            print(vid, n)


asyncio.run(main())
```

Runnable examples live in the repo (see also [Examples](../examples.md)):

* `examples/01_search_videos.py --async` (and the other `0x_*.py` scripts) — same feature, sync or async via `--async`
* `examples/10_async_concurrency.py` — search, parallel `video()` fan-out, comments with `max_concurrency`

## Transcripts

```python
async with AsyncYouTube() as yt:
    transcript = await yt.transcript("dQw4w9WgXcQ", languages=["en", "uk"])
    print(transcript.text[:200])

    tracks = await yt.transcripts("dQw4w9WgXcQ")
    track = tracks.find_transcript(["en"])
    # Prefer the async fetch on the track when you already hold a bound client:
    data = await track.afetch()
```

`TranscriptTrack.fetch()` remains synchronous (uses a bound sync-style client path when present). Prefer `await track.afetch()` under `AsyncYouTube`, or use `await yt.transcript(...)` for the one-shot helper.

## Proxies and custom httpx clients

Inject a preconfigured `httpx.AsyncClient` via `AsyncInnerTubeClient`:

```python
import httpx
from ytscrape import AsyncYouTube, AsyncInnerTubeClient


async def main() -> None:
    transport = httpx.AsyncHTTPTransport(retries=0)
    session = httpx.AsyncClient(
        proxy="http://user:pass@proxy:8080",
        transport=transport,
        timeout=30.0,
    )
    client = AsyncInnerTubeClient(
        session=session,
        max_concurrency=4,
        max_retries=3,
        backoff_factor=0.5,
    )
    async with AsyncYouTube(client=client) as yt:
        details = await yt.video("dQw4w9WgXcQ")
        print(details.title)


asyncio.run(main())
```

See also [Advanced](advanced.md) for the synchronous `requests.Session` equivalent.

## When to use sync vs async

| Prefer **sync** `YouTube`                         | Prefer **async** `AsyncYouTube`                                      |
| ------------------------------------------------- | -------------------------------------------------------------------- |
| Simple scripts, notebooks, CLI                    | Many independent videos / queries in one process                     |
| One search or comment thread                      | High I/O concurrency with a shared client                            |
| No event loop in the app                          | FastAPI / aiohttp / other asyncio stacks                             |

For a single long comment thread, wall-clock time is often similar: pages must load in order. Async shines when you `asyncio.gather` many independent jobs under one `max_concurrency` budget.

## Error handling

Exceptions are the same as sync (`RequestError`, `ParseError`, `TranscriptsDisabled`, …). Use normal `try` / `except` around `await` calls. Bot-check and block-style errors include guidance to change IP or use a proxy, and to open a GitHub issue if that fails — see [Error handling](error-handling.md).

## Next steps

* [Examples](../examples.md) — sync + async scripts for every feature
* [API — YouTube / AsyncYouTube](../api/youtube.md)
* [API — InnerTube / AsyncInnerTubeClient](../api/innertube-client.md)
* [Pagination](pagination.md)
* [Comments](comments.md)
* [Advanced (proxies, sessions)](advanced.md)
