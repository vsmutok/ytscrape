# Search YouTube for Videos, Channels, and Playlists

> Search YouTube for videos, channels, playlists, Shorts, and movies using SearchFilter — no API key, no quota, fully typed results.

The `YouTube.search()` method is the primary way to query YouTube. It accepts a text query and an optional filter and returns a `SearchResults` object — a lazy, paginated iterable that streams results across as many pages as you need.

## Basic search

With no filter applied, YouTube returns a mixed feed of videos, channels, and playlists. Iterate directly over the results to consume them one at a time; pages are loaded on demand.

```python
from ytscrape import YouTube

with YouTube() as yt:
    for item in yt.search("python tutorial"):
        print(item.title, item.url)
```

Pass `max_results` to stop after a fixed number of items:

```python
with YouTube() as yt:
    for item in yt.search("python tutorial", max_results=10):
        print(item.title)
```

## Filtering by result type

Import `SearchFilter` and pass it as the `filter` keyword argument to restrict results to a single content type.

| Filter                   | String value  | Description                                            |
| ------------------------ | ------------- | ------------------------------------------------------ |
| `SearchFilter.ALL`       | `"all"`       | Mixed feed — videos, channels, and playlists (default) |
| `SearchFilter.VIDEOS`    | `"videos"`    | Videos only                                            |
| `SearchFilter.CHANNELS`  | `"channels"`  | Channels only                                          |
| `SearchFilter.PLAYLISTS` | `"playlists"` | Playlists only                                         |
| `SearchFilter.SHORTS`    | `"shorts"`    | YouTube Shorts only                                    |
| `SearchFilter.MOVIES`    | `"movies"`    | Movies only                                            |

### Videos

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    results = yt.search(
        "python tutorial",
        filter=SearchFilter.VIDEOS,
        max_results=10,
    )
    for video in results:
        print(f"{video.title}  ({video.duration})")
        print(f"  by {video.channel} — {video.views}")
        print(f"  {video.url}")
```

### Channels

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    for channel in yt.search("python", filter=SearchFilter.CHANNELS, max_results=5):
        print(f"{channel.title} — {channel.subscribers}")
        print(f"  {channel.url}")
```

### Playlists

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    for playlist in yt.search("python", filter=SearchFilter.PLAYLISTS, max_results=5):
        print(f"{playlist.title} ({playlist.video_count} videos)")
        print(f"  {playlist.url}")
```

## Using string values instead of the enum

Every `SearchFilter` member has an equivalent lowercase string value. You can pass it directly without importing the enum:

```python
with YouTube() as yt:
    for video in yt.search("lofi", filter="videos", max_results=5):
        print(video.title)
```

Valid string values are `"all"`, `"videos"`, `"channels"`, `"playlists"`, `"shorts"`, and `"movies"`. An unrecognised value raises `ValueError` immediately.

## The `max_results` parameter

`max_results` caps the total number of items yielded during iteration. Once that count is reached the iterator stops cleanly, even if YouTube has more pages.

```python
with YouTube() as yt:
    # Fetch at most 25 results across however many pages that requires.
    for video in yt.search("machine learning", filter="videos", max_results=25):
        print(video.title)
```

Omit `max_results` entirely to consume every result YouTube returns for the query.

## Return type: `SearchResults`

`yt.search()` returns a `SearchResults` object. It is a **lazy iterable** — the first page of results is fetched when `search()` is called, and additional pages are fetched automatically as you consume items past the end of each page.

You can also drive pagination manually — see the [Pagination guide](pagination.md) for details.

## Result field reference

Each yielded item is a frozen, fully typed dataclass. The concrete type depends on the active filter.

### `Video` — returned by `ALL` and `VIDEOS`

| Field        | Type          | Description                                                           |
| ------------ | ------------- | --------------------------------------------------------------------- |
| `video_id`   | `str`         | Unique 11-character YouTube video id                                  |
| `title`      | `str \| None` | Video title                                                           |
| `channel`    | `str \| None` | Display name of the uploading channel                                 |
| `channel_id` | `str \| None` | `UC…` channel id                                                      |
| `duration`   | `str \| None` | Formatted duration string (e.g. `"10:32"`)                            |
| `views`      | `str \| None` | View count as rendered by YouTube (e.g. `"1.2M views"`)               |
| `published`  | `str \| None` | Relative publish time (e.g. `"3 days ago"`)                           |
| `thumbnail`  | `str \| None` | URL of the largest available thumbnail                                |
| `url`        | `str`         | Canonical `https://www.youtube.com/watch?v=…` URL (computed property) |

### `Channel` — returned by `ALL` and `CHANNELS`

| Field         | Type          | Description                                                             |
| ------------- | ------------- | ----------------------------------------------------------------------- |
| `channel_id`  | `str`         | `UC…` channel id                                                        |
| `title`       | `str \| None` | Channel display name                                                    |
| `handle`      | `str \| None` | `@handle` when available                                                |
| `subscribers` | `str \| None` | Subscriber count as rendered by YouTube (e.g. `"1.23M subscribers"`)    |
| `video_count` | `str \| None` | Public video count                                                      |
| `thumbnail`   | `str \| None` | URL of the channel avatar                                               |
| `url`         | `str`         | Canonical `https://www.youtube.com/channel/UC…` URL (computed property) |

### `Playlist` — returned by `ALL` and `PLAYLISTS`

| Field         | Type          | Description                                                                 |
| ------------- | ------------- | --------------------------------------------------------------------------- |
| `playlist_id` | `str`         | Unique playlist id                                                          |
| `title`       | `str \| None` | Playlist title                                                              |
| `channel`     | `str \| None` | Name of the channel that owns the playlist                                  |
| `video_count` | `str \| None` | Number of videos in the playlist                                            |
| `thumbnail`   | `str \| None` | URL of the playlist thumbnail                                               |
| `url`         | `str`         | Canonical `https://www.youtube.com/playlist?list=…` URL (computed property) |

## Async search

With `AsyncYouTube` (optional `ytscrape[async]` extra):

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


asyncio.run(main())
```

See the [Async API guide](async.md).

!!! tip

    Create one `YouTube` or `AsyncYouTube` instance and reuse it across multiple searches. The instance holds a warm HTTP session and a cached InnerTube context, so subsequent calls skip the initial context-extraction request and run noticeably faster.
