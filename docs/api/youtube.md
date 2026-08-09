# YouTube Class — ytscrape High-Level Scraping API Reference

> Complete reference for the YouTube facade class — the primary entry point for searching, fetching videos, channels, comments, and transcripts.

The `YouTube` class is the main entry point for every scraping task in ytscrape. It is a thin facade over `InnerTubeClient`, the paginated result types, and the data models. You construct one instance, call methods on it, and let ytscrape handle authentication headers, pagination, and response parsing.

In most cases a zero-argument `YouTube()` call is all you need. Pass keyword arguments only when you want to target a specific locale, adjust the request timeout, or inject a pre-built `InnerTubeClient` (for example when running tests or routing traffic through a proxy).

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    for video in yt.search("python", filter=SearchFilter.VIDEOS, max_results=20):
        print(video.title, video.url)

    details = yt.video("dQw4w9WgXcQ")
    print(details.title, details.views)

    transcript = yt.transcript("dQw4w9WgXcQ", languages=["en"])
    print(transcript.text[:200])
```

***

## Constructor

```python
YouTube(
    *,
    client: InnerTubeClient | None = None,
    locale: Locale | None = None,
    language: Language | str = "en",
    region: Country | str = "US",
    timeout: float = 30.0,
)
```

All arguments are keyword-only.

**`client`** (`InnerTubeClient | None`)

:   A pre-built [`InnerTubeClient`](innertube-client.md) to use instead of creating a new one. When
      provided, the `locale`, `language`, `region`, and `timeout` arguments are ignored. Useful when you
      want to share a session across multiple `YouTube` instances or inject a custom client for testing.


**`locale`** (`Locale | None`)

:   A [`Locale`](locale.md) object that bundles language and country together. When provided, the
      `language` and `region` arguments are ignored. Omit it to let the client build a `Locale` from
      the individual `language` and `region` values.


**`language`** (`Language | str`)

:   The `hl` (host language) value sent in every InnerTube request. Accepts a
      [`Language`](locale.md) enum member or a raw ISO 639-1 code such as `"fr"` or `"de"`. Ignored
      when `locale` is provided.


**`region`** (`Country | str`)

:   The `gl` (geolocation) value sent in every InnerTube request. Accepts a
      [`Country`](locale.md) enum member or a raw ISO 3166-1 alpha-2 code such as `"GB"` or `"DE"`.
      Ignored when `locale` is provided.


**`timeout`** (`float`)

:   Per-request timeout in seconds applied to every HTTP call made by the default client. Ignored when
      `client` is provided.


***

## Properties

### `client`

```python
@property
def client(self) -> InnerTubeClient
```

The underlying [`InnerTubeClient`](innertube-client.md) instance. Useful when you need to call
low-level endpoints directly or inspect the session state without bypassing the facade.

### `locale`

```python
@property
def locale(self) -> Locale
```

The [`Locale`](locale.md) (language + country pair) that is being used for all requests. This is
a shortcut for `yt.client.locale`.

***

## Methods

### `search`

Search YouTube and return a lazily-paginated [`SearchResults`](models-search.md) object.

```python
def search(
    self,
    query: str,
    *,
    filter: SearchFilter | str = SearchFilter.ALL,
    max_results: int | None = None,
) -> SearchResults
```

**`query`** (`str`) **required**

:   The search query string.


**`filter`** (`SearchFilter | str`)

:   Narrows results to a specific content type. Accepts a [`SearchFilter`](filters.md) enum member
      (`ALL`, `VIDEOS`, `CHANNELS`, `PLAYLISTS`) or its lowercase string value (`"all"`, `"videos"`,
      `"channels"`, `"playlists"`).


**`max_results`** (`int | None`)

:   Optional cap on the total number of items yielded when iterating over the returned
      `SearchResults`. `None` means iterate until YouTube runs out of pages.


**Returns:** [`SearchResults`](models-search.md) — a lazy iterable that transparently fetches
continuation pages on demand.

```python
from ytscrape import YouTube, SearchFilter

yt = YouTube()

# Iterate over the first 50 video results
for video in yt.search("python tutorial", filter=SearchFilter.VIDEOS, max_results=50):
    print(video.title, video.url)
```

***

### `video`

Fetch detailed metadata for a single video.

```python
def video(self, video: str) -> VideoDetails
```

**`video`** (`str`) **required**

:   A video id or any YouTube URL that contains one. Supported URL formats include
      `watch?v=`, `youtu.be/`, `/shorts/`, and `/embed/`.


**Returns:** [`VideoDetails`](models-details.md) — rich metadata including title, description,
view count, like count, upload date, and channel info.

```python
from ytscrape import YouTube

yt = YouTube()

# Pass a full URL or just the 11-character video id
details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(details.title)
print(details.views)
print(details.channel.title)
```

***

### `channel`

Fetch detailed metadata for a single channel.

```python
def channel(self, channel: str) -> ChannelDetails
```

**`channel`** (`str`) **required**

:   A channel id starting with `UC`, a `@handle`, or any YouTube channel URL. Supported formats
      include `/channel/UC…`, `/@handle`, `/c/name`, and `/user/name`.


**Returns:** [`ChannelDetails`](models-details.md) — includes title, description,
subscriber count, video count, and channel id.

```python
from ytscrape import YouTube

yt = YouTube()

# Using a handle
channel = yt.channel("@RickAstleyYT")
print(channel.title)
print(channel.subscribers)
print(channel.description)
```

***

### `comments`

Collect comments for a video and return a lazily-paginated [`CommentThread`](models-comments.md).

```python
def comments(
    self,
    video: str,
    *,
    max_results: int | None = None,
    include_replies: bool = False,
    sort: CommentSort | str = CommentSort.TOP,
) -> CommentThread
```

**`video`** (`str`) **required**

:   A video id or any YouTube URL that contains one (`watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`
      are all supported).


**`max_results`** (`int | None`)

:   Optional cap on the total number of comments yielded when iterating. When `include_replies` is
      `True`, replies count toward this limit too.


**`include_replies`** (`bool`)

:   When `True`, replies to each top-level comment are also collected. Each reply is yielded
      immediately after the comment it belongs to and has its `is_reply` attribute set to `True`.


**`sort`** (`CommentSort | str`)

:   The order in which comments are fetched. `CommentSort.TOP` mirrors YouTube's "Top comments" view
      but intentionally omits less relevant comments and potential spam. `CommentSort.NEWEST` (or
      `"newest"`) returns every comment. Use `"newest"` when completeness matters.


**Returns:** [`CommentThread`](models-comments.md) — a lazy iterable that pages through comments on
demand.

**Raises:** `ParseError` — if the comments section cannot be found (e.g. comments are disabled).

!!! warning

    `CommentSort.TOP` (the default) **omits some comments** — YouTube intentionally hides low-relevance
      results and potential spam from this view. Use `sort="newest"` when you need a complete collection.


```python
from ytscrape import YouTube, CommentSort

with YouTube() as yt:
    # Collect all comments, including replies, newest first
    for comment in yt.comments(
        "https://youtu.be/dQw4w9WgXcQ",
        sort=CommentSort.NEWEST,
        include_replies=True,
        max_results=200,
    ):
        prefix = "  ↳" if comment.is_reply else ""
        print(f"{prefix} {comment.author}: {comment.text[:80]}")
```

***

### `transcript`

Fetch a transcript (captions track) for a video.

```python
def transcript(
    self,
    video: str,
    *,
    languages: list[str] | tuple[str, ...] = ("en",),
    preserve_formatting: bool = False,
) -> Transcript
```

**`video`** (`str`) **required**

:   A video id or any YouTube watch URL.


**`languages`** (`list[str] | tuple[str, ...]`)

:   Preferred language codes tried in order, e.g. `["uk", "en"]`. Manually created captions are
      preferred over auto-generated ones within each language, following the same behaviour as
      youtube-transcript-api.


**`preserve_formatting`** (`bool`)

:   When `True`, a small set of HTML formatting tags (`<i>`, `<b>`, etc.) are preserved inside
      snippet text. By default all tags are stripped.


**Returns:** [`Transcript`](models-transcripts.md) — the full transcript with
`.text` (plain string) and `.snippets` (list of timed `TranscriptSnippet` objects).

```python
from ytscrape import YouTube

yt = YouTube()

# Try Ukrainian first, fall back to English
transcript = yt.transcript("dQw4w9WgXcQ", languages=["uk", "en"])
print(transcript.language)
print(transcript.text[:300])

# Access individual timed snippets
for snippet in transcript.snippets:
    print(f"[{snippet.start:.1f}s] {snippet.text}")
```

***

### `transcripts`

List all available caption tracks for a video without downloading any of them.

```python
def transcripts(self, video: str) -> TranscriptList
```

**`video`** (`str`) **required**

:   A video id or any YouTube watch URL.


**Returns:** [`TranscriptList`](models-transcripts.md) — an iterable of
`TranscriptTrack` objects. Use `.find_transcript()` to locate a specific track, and `.fetch()` or
`.translate()` on a track to download it.

```python
from ytscrape import YouTube

yt = YouTube()

track_list = yt.transcripts("dQw4w9WgXcQ")
for track in track_list:
    print(track.language, track.language_code, "auto" if track.is_generated else "manual")

# Find a specific track and fetch it
track = track_list.find_transcript(["en"])
transcript = track.fetch()
print(transcript.text[:200])
```

***

### `close`

Close the underlying HTTP session and release all associated resources.

```python
def close(self) -> None
```

**Returns:** `None`

!!! tip

    Prefer the context manager form (`with YouTube() as yt: …`) over calling `close()` manually — it
      guarantees cleanup even when an exception is raised inside the block.


```python
from ytscrape import YouTube

yt = YouTube()
try:
    details = yt.video("dQw4w9WgXcQ")
    print(details.title)
finally:
    yt.close()
```

***

### Context manager support

`YouTube` implements the context manager protocol (`__enter__` / `__exit__`), so you can use it
in a `with` statement. `__exit__` calls `close()` automatically, even when an exception is raised
inside the block.

```python
def __enter__(self) -> YouTube
def __exit__(self, *exc_info: object) -> None
```

```python
from ytscrape import YouTube, SearchFilter

with YouTube(language="de", region="DE") as yt:
    for video in yt.search("python kurs", filter=SearchFilter.VIDEOS, max_results=10):
        print(video.title, video.url)
# HTTP session is closed automatically here
```
