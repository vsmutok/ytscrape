# Get Started with ytscrape: Search, Metadata and Comments

> Install ytscrape and write your first Python script to search videos, fetch video details, and collect comments — all without a YouTube API key.

This guide walks you through installing ytscrape and using its three most common features: searching YouTube for videos, fetching detailed metadata for a single video, and collecting comments. By the end you will have working Python snippets you can run immediately and adapt for your own projects.

### 1. Install ytscrape

ytscrape is published on PyPI and requires Python 3.10 or newer. Install it with your preferred package manager:

=== "pip"

    ```bash
    pip install ytscrape
    ```

=== "uv"

    ```bash
    uv add ytscrape
    ```

Verify the installation by importing the package and checking its version:

```python
import ytscrape
print(ytscrape.__version__)  # e.g. 0.1.4
```

### 2. Search for videos

Use `YouTube.search()` with `SearchFilter.VIDEOS` to find videos matching a query. The result is a lazy, paginated object — iterating it loads more pages on demand. The `max_results` argument caps how many items are consumed.

```python
from ytscrape import SearchFilter, YouTube

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

Each `video` in the loop is a typed `Video` dataclass. Its most useful fields are `video_id`, `title`, `channel`, `channel_id`, `duration`, `views`, `published`, `thumbnail`, and `url`.

### 3. Fetch video details

Call `YouTube.video()` with a video id or any YouTube URL to retrieve a `VideoDetails` object packed with rich metadata. The `watch?v=`, `youtu.be/`, `/shorts/`, and `/embed/` URL formats are all accepted.

```python
from ytscrape import YouTube

with YouTube() as yt:
    details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    print(details.title)
    print(details.channel, details.channel_id)
    print(details.views, details.length_seconds)
    print(details.is_live)
    print(details.keywords)
    print(details.description[:200])
```

`VideoDetails` fields include `video_id`, `title`, `description`, `channel`, `channel_id`, `length_seconds` (int), `views` (int), `keywords`, `is_live`, `thumbnail`, and `url`.

### 4. Collect comments

`YouTube.comments()` returns a lazy `CommentThread` iterable. Use `include_replies=True` to collect threaded replies alongside top-level comments — each reply arrives right after its parent and has `is_reply=True`.

Pass `sort=CommentSort.NEWEST` to ensure **every** comment is returned. YouTube's default `"top"` order silently omits less-relevant comments and potential spam, so `NEWEST` is the right choice whenever completeness matters.

```python
from ytscrape import CommentSort, YouTube

with YouTube() as yt:
    total = 0
    for comment in yt.comments(
        "https://www.youtube.com/watch?v=75IuMfHdTfc",
        max_results=1000,
        include_replies=True,
        sort=CommentSort.NEWEST,
    ):
        total += 1
        prefix = "  ↳ " if comment.is_reply else ""
        # `like_count_text` preserves YouTube's raw string (e.g. "1.2K")
        # even when `like_count` is None because the value was abbreviated.
        count = comment.like_count_text
        likes = f" ({count} likes)" if count else ""
        heart = " ❤️" if comment.heart else ""
        print(f"{prefix}{comment.author}{likes}{heart}: {comment.text}")

    # `yt.comments(...)` is a lazy iterator, so count as you go.
    print(f"\nComments collected: {total}")
```


!!! tip

    Always use `YouTube` as a context manager (`with YouTube() as yt:`). This keeps a single HTTP session open for the duration of your script, reuses the extracted InnerTube context across all requests, and ensures the session is closed cleanly on exit. If you need to manage the lifetime manually, call `yt.close()` when you are done.


## Next Steps

* **[Installation](installation.md)** — Python version requirements, all runtime dependencies, and how to install from source.
* **Guides** — Deep dives into search filters, language and region localisation, transparent pagination, channel metadata, transcripts, error handling, and advanced configuration (proxies, retries, custom sessions).
