# ytscrape — Free YouTube Scraper for Python

**Scrape YouTube search results, video metadata and comments — no API key, no
quota, no browser.**

[![PyPI version](https://img.shields.io/pypi/v/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![Python versions](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/ytscrape/)
[![Downloads](https://img.shields.io/pepy/dt/ytscrape)](https://pepy.tech/project/ytscrape)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg)](https://peps.python.org/pep-0561/)
[![API key](https://img.shields.io/badge/API%20key-not%20required-success)](#ytscrape-vs-the-alternatives)

[![CI](https://img.shields.io/github/actions/workflow/status/vsmutok/ytscrape/pre-commit.yml?branch=main&label=ci)](https://github.com/vsmutok/ytscrape/actions/workflows/pre-commit.yml)
[![Release](https://img.shields.io/github/actions/workflow/status/vsmutok/ytscrape/publish.yml?label=release)](https://github.com/vsmutok/ytscrape/actions/workflows/publish.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Last commit](https://img.shields.io/github/last-commit/vsmutok/ytscrape)](https://github.com/vsmutok/ytscrape/commits/main)
[![Stars](https://img.shields.io/github/stars/vsmutok/ytscrape?style=flat)](https://github.com/vsmutok/ytscrape/stargazers)

`ytscrape` is a **free YouTube scraper** for Python built on top of the
internal YouTube *InnerTube* API — the same endpoints the YouTube web app uses.
Use it to **search YouTube**, **extract video, channel and playlist data**,
**fetch video metadata** and **collect every comment (and reply)** of a video —
all with **transparent pagination**, **typed models** and **no API key**.

```python
from ytscrape import YouTube

with YouTube() as yt:
    for video in yt.search("python", max_results=5):
        print(video.title, video.url)
```

> ⚠️ This library talks to YouTube's private endpoints. Use it responsibly and
> at your own risk; the endpoints and `params` values may change over time.

## Table of Contents

- [Why ytscrape?](#why-ytscrape)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Feature coverage](#feature-coverage)
- [ytscrape vs. the alternatives](#ytscrape-vs-the-alternatives)
- [How it works](#how-it-works)
- [Search](#search)
- [Video details](#video-details)
- [Comments](#comments)
- [Language & country](#language--country)
- [Pagination](#pagination)
- [Data models](#data-models)
- [Error handling](#error-handling)
- [Advanced: proxies, retries, custom sessions](#advanced-proxies-retries-custom-sessions)
- [Command line](#command-line)
- [Examples](#examples)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Why ytscrape?

- 🔑 **No YouTube Data API key**, **no quota**, no sign-up, no billing project.
- 🧊 **No browser** — no Selenium, no Playwright, no headless Chrome. Pure HTTP.
- 🧩 **Typed models** (`Video`, `Channel`, `Playlist`, `VideoDetails`,
  `Comment`) instead of raw, deeply-nested JSON.
- 📄 **Transparent pagination** — just iterate; continuation tokens are handled
  for you.
- 💬 **Full comment scraping**, including replies and the sort order that
  actually returns *every* comment.
- 🌍 **Localisation** — interface language (`hl`) and content region (`gl`),
  validated with `pycountry`.
- 🪶 **Tiny install** — only `requests` and `pycountry`.
- 🖥️ **CLI included**: `ytscrape search "python" --max 10`.
- 🧱 **Clean, extensible OOP design** (facade + factory methods + strategy) —
  easy to build on or to mock in tests.

## Installation

```bash
pip install ytscrape
```

or with [uv](https://github.com/astral-sh/uv):

```bash
uv add ytscrape
```

From source:

```bash
pip install .
```

Requires **Python 3.10+**. Runtime dependencies: `requests`, `pycountry`.

## Quick start

Everything you usually need, in one snippet:

```python
from ytscrape import YouTube, SearchFilter, CommentSort

with YouTube(language="en", region="US") as yt:
    # 1. Search videos and iterate over as many pages as needed.
    for video in yt.search("python", filter=SearchFilter.VIDEOS, max_results=20):
        print(video.title, "-", video.url)

    # 2. Search channels.
    for channel in yt.search("python", filter=SearchFilter.CHANNELS, max_results=5):
        print(channel.title, channel.url)

    # 3. Fetch details for a single video (id or URL both work).
    details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(details.title, details.channel, details.views, details.length_seconds)

    # 4. Collect comments — including replies and *every* comment.
    for comment in yt.comments(
        "https://youtu.be/dQw4w9WgXcQ",
        include_replies=True,
        sort=CommentSort.NEWEST,
        max_results=100,
    ):
        marker = "  ↳" if comment.is_reply else "-"
        print(f"{marker} {comment.author}: {comment.text}")
```

> 📂 More runnable snippets live in [`examples/`](examples/).

## Feature coverage

| Area                                       | Status | Notes                                            |
| ------------------------------------------ | :----: | ------------------------------------------------ |
| Search — videos                             |   ✅   | `SearchFilter.VIDEOS`                            |
| Search — channels                           |   ✅   | `SearchFilter.CHANNELS`                          |
| Search — playlists                          |   ✅   | `SearchFilter.PLAYLISTS`                         |
| Search — Shorts / movies                    |   ✅   | `SearchFilter.SHORTS`, `SearchFilter.MOVIES`     |
| Video metadata                              |   ✅   | `YouTube.video()` (id or any URL)                |
| Comments                                    |   ✅   | `YouTube.comments()`, full pagination            |
| Comment replies                             |   ✅   | `include_replies=True`                           |
| Comment sort (top / newest)                 |   ✅   | `sort=CommentSort.NEWEST` returns *every* comment |
| Continuation / pagination                   |   ✅   | Transparent for search and comments              |
| Localisation (`hl` / `gl`)                  |   ✅   | Validated ISO codes                              |
| Typed models + `py.typed`                   |   ✅   | PEP 561 compliant                                |
| CLI                                         |   ✅   | `python -m ytscrape` / `ytscrape`                |
| Channel videos / Shorts / live tabs         |   🚧   | Planned — see [Roadmap](#roadmap)                |
| Playlist items                              |   🚧   | Planned                                          |
| Transcripts / subtitles                     |   🚧   | Planned                                          |
| Related videos, trending, home feed         |   🚧   | Planned                                          |
| Community posts                             |   🚧   | Planned                                          |
| Async (`asyncio`) API                       |   🚧   | Planned                                          |

## ytscrape vs. the alternatives

| | **ytscrape** | YouTube Data API | `yt-dlp` | Browser automation |
| ---------------------- | :----------: | :--------------: | :------: | :----------------: |
| API key required       |      ❌      |        ✅        |    ❌    |         ❌         |
| Daily quota            |      ❌      |        ✅        |    ❌    |         ❌         |
| Browser / driver needed|      ❌      |        ❌        |    ❌    |         ✅         |
| Search                 |      ✅      |        ✅        |    ✅    |         ✅         |
| Video metadata         |      ✅      |        ✅        |    ✅    |         ✅         |
| Comments + replies     |      ✅      |    ✅ (quota)    |    ✅    |         ✅         |
| Typed Python models    |      ✅      |        ❌        |    ❌    |         ❌         |
| Downloads media        |      ❌      |        ❌        |    ✅    |         ✅         |
| Install size           |    tiny      |     medium       |  large   |       huge         |

**Rule of thumb:** use `yt-dlp` when you need to *download media*, the official
Data API when you need *guaranteed, ToS-blessed access*, and `ytscrape` when you
need **fast, key-less access to YouTube metadata and comments** from Python.

## How it works

`ytscrape` speaks the private YouTube *InnerTube* API directly:

1. It loads `youtube.com` once and extracts the InnerTube **context**
   (API key, client version, visitor data).
2. It POSTs to `youtubei/v1/search`, `youtubei/v1/player` and
   `youtubei/v1/next` with that context.
3. Responses are parsed into small, frozen dataclasses; **continuation tokens**
   are followed automatically while you iterate.

No browser. No Selenium. No Playwright. Pure HTTP.

## Search

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    for item in yt.search("lofi", filter=SearchFilter.PLAYLISTS, max_results=10):
        print(item.title, item.url)
```

| Filter                   | Description          |
| ------------------------ | -------------------- |
| `SearchFilter.ALL`       | Everything (default) |
| `SearchFilter.VIDEOS`    | Videos only          |
| `SearchFilter.CHANNELS`  | Channels only        |
| `SearchFilter.PLAYLISTS` | Playlists only       |
| `SearchFilter.SHORTS`    | Shorts only          |
| `SearchFilter.MOVIES`    | Movies only          |

You can also pass the string form: `yt.search("python", filter="videos")` — no
magic `EgIQAQ==` strings in your code.

## Video details

```python
with YouTube() as yt:
    video = yt.video("dQw4w9WgXcQ")  # id
    video = yt.video("https://youtu.be/dQw4w9WgXcQ")  # or any URL

    print(video.title, video.views, video.length_seconds, video.is_live)
    print(video.keywords)
```

`watch?v=`, `youtu.be/`, `/shorts/` and `/embed/` URLs are all accepted.

## Comments

`YouTube.comments()` returns a lazy `CommentThread` that transparently pages
through every comment:

```python
from ytscrape import YouTube

with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=50):
        print(comment.author, "-", comment.text)
```

**Replies.** By default only *top-level* comments are collected. Pass
`include_replies=True` to also collect the replies of every thread; each reply
has `is_reply=True` and is yielded right after the comment it replies to:

```python
for comment in yt.comments(video_url, include_replies=True):
    marker = "  ↳" if comment.is_reply else "-"
    print(f"{marker} {comment.author}: {comment.text}")
```

Omit `max_results` to iterate over **all** comments. When
`include_replies=True`, `max_results` counts replies too. A `ParseError` is
raised if the video has comments disabled.

### Collecting *every* comment (sort order)

YouTube's default **"Top comments"** view quietly **hides some comments** (less
relevant ones and "potential spam"), so collecting in that order will appear to
*skip* comments. To get **every** comment, switch to **"Newest first"**:

```python
from ytscrape import YouTube, CommentSort

with YouTube() as yt:
    # `CommentSort.NEWEST` (or the string "newest") returns every comment.
    for comment in yt.comments(video_url, sort=CommentSort.NEWEST):
        print(comment.author, "-", comment.text)
```

`sort` accepts a `CommentSort` (`TOP` / `NEWEST`) or its string value; it
defaults to `CommentSort.TOP` to mirror YouTube's own default view.

### Counting what you collected

`comments()` is a lazy iterator, so the total is known only after the last page:

```python
total = 0
for comment in yt.comments(video_url, sort="newest"):
    total += 1
print(f"Collected {total} comments")

# Or materialise everything at once:
comments = list(yt.comments(video_url, sort="newest"))
print(len(comments))
```

## Language & country

YouTube localises results by *interface language* (`hl`) and *content region*
(`gl`). Configure both when creating `YouTube`, passing plain ISO codes (or the
`Language` / `Country` value objects, which wrap the same codes):

```python
from ytscrape import YouTube, Language, Country, Locale

# Just pass raw ISO codes — they are validated and normalised for you.
with YouTube(language="uk", region="UA") as yt:
    for video in yt.search("музика", max_results=10):
        print(video.title, video.url)

# The Language / Country value objects are equivalent (and reusable).
yt = YouTube(language=Language("de"), region=Country("DE"))

# Invalid codes are rejected early (validated with pycountry).
YouTube(region="XX")  # ValueError: Unknown country code 'XX'. ...

# Or pass a ready-made Locale.
yt = YouTube(locale=Locale(language="fr", country="FR"))
print(yt.locale.language.code, yt.locale.country.code)  # fr FR
```

`Language` and `Country` are thin, self-validating value objects around a raw
ISO 639-1 / ISO 3166-1 alpha-2 code — there is no hard-coded list, so any valid
code works. The chosen locale is sent both in the request context (`hl` / `gl`)
and as the `Accept-Language` HTTP header.

## Pagination

Pagination is transparent — iterating over the result object automatically
loads the next page:

```python
results = yt.search("python")

for item in results:  # loads pages on demand
    print(item.title)
```

You can also page manually:

```python
results = yt.search("python")
print(len(results.fetch_next_page()))  # explicitly load one more page
print(results.has_more)  # is there another page?
```

Use `max_results` to cap how many items you consume.

## Data models

All models are frozen dataclasses with full type hints (the package ships
`py.typed`, so mypy/pyright see the types).

**`Video`** (search results) — `video_id`, `title`, `channel`, `channel_id`,
`duration`, `views`, `published`, `thumbnail`, `url`.

**`Channel`** — `channel_id`, `title`, `handle`, `subscribers`, `video_count`,
`thumbnail`, `url`.

**`Playlist`** — `playlist_id`, `title`, `channel`, `video_count`, `thumbnail`,
`url`.

**`VideoDetails`** (from `YouTube.video()`) — `video_id`, `title`,
`description`, `channel`, `channel_id`, `length_seconds` (`int`), `views`
(`int`), `keywords`, `is_live`, `thumbnail`, `url`.

**`Comment`**:

| Field                | Description                                            |
| -------------------- | ------------------------------------------------------ |
| `comment_id`         | Unique comment id.                                     |
| `text`               | The comment body.                                      |
| `author`             | Display name of the author.                            |
| `author_channel_id`  | Channel id of the author (when available).             |
| `author_thumbnail`   | URL of the author's avatar.                            |
| `published`          | Human-readable published time (e.g. `2 days ago`).     |
| `like_count`         | Like count as an `int` (`None` when abbreviated, e.g. `1.2K`). |
| `like_count_text`    | Like count as YouTube renders it, keeping abbreviations (e.g. `1.2K`, `894`). |
| `reply_count`        | Number of replies (top-level comments only).           |
| `reply_count_text`   | Reply count as a raw display string (e.g. `64`).       |
| `heart`              | `True` if the video's creator hearted the comment.     |
| `is_reply`           | `True` for replies, `False` for top-level comments.    |

## Error handling

Every error raised by the library derives from `YtScraperError`:

```python
from ytscrape import YouTube, YtScraperError, RequestError, ParseError

try:
    with YouTube() as yt:
        for comment in yt.comments("dQw4w9WgXcQ"):
            print(comment.text)
except RequestError as exc:  # network / HTTP problem
    print("network error:", exc)
except ParseError as exc:  # unexpected response (e.g. comments disabled)
    print("cannot parse:", exc)
except YtScraperError as exc:  # catch-all
    print("ytscrape failed:", exc)
```

| Exception                | Raised when                                          |
| ------------------------ | ---------------------------------------------------- |
| `YtScraperError`         | Base class for everything below.                     |
| `ContextExtractionError` | The InnerTube context can't be read from YouTube.    |
| `RequestError`           | An HTTP request to YouTube fails.                    |
| `ParseError`             | A response can't be parsed as expected.              |

## Advanced: proxies, retries, custom sessions

`YouTube` is a thin facade over `InnerTubeClient`, which accepts your own
`requests.Session` — that is the hook for proxies, retries, custom headers or
caching:

```python
import requests
from requests.adapters import HTTPAdapter, Retry
from ytscrape import YouTube, InnerTubeClient

session = requests.Session()
session.proxies = {"https": "http://user:pass@proxy:8080"}
session.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1)))

client = InnerTubeClient(session=session, timeout=15.0, language="en", region="US")

with YouTube(client=client) as yt:
    print(next(iter(yt.search("python"))).title)
```

The same injection point makes the library trivial to unit-test: pass a fake
session and no network call ever happens.

## Command line

```bash
# Search
python -m ytscrape search "python tutorial" --filter videos --max 10

# Localised search (Ukrainian interface, Ukrainian region)
python -m ytscrape --language uk --region UA search "музика" --max 10

# Video details
python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Collect comments (pass 0 to --max for no limit)
python -m ytscrape comments https://www.youtube.com/watch?v=dQw4w9WgXcQ --max 20

# Collect comments together with their replies
python -m ytscrape comments https://www.youtube.com/watch?v=dQw4w9WgXcQ --replies

# Collect EVERY comment (the default "top" order hides some)
python -m ytscrape comments https://www.youtube.com/watch?v=dQw4w9WgXcQ --sort newest
```

After installing, a `ytscrape` console script is also available:

```bash
ytscrape search "python" --filter channels --max 5
```

## Examples

| Example                                                              | What it shows                                           |
| -------------------------------------------------------------------- | ------------------------------------------------------- |
| [`01_search_videos.py`](examples/01_search_videos.py)                 | Search for videos with `SearchFilter.VIDEOS`.           |
| [`02_search_channels_playlists.py`](examples/02_search_channels_playlists.py) | Search for channels and playlists.              |
| [`03_video_details.py`](examples/03_video_details.py)                 | Fetch detailed metadata for a single video.             |
| [`04_pagination.py`](examples/04_pagination.py)                       | Iterate transparently or page manually.                 |
| [`05_language_region.py`](examples/05_language_region.py)             | Localise results by language and region.                |
| [`06_error_handling.py`](examples/06_error_handling.py)               | Handle `ytscrape` exceptions gracefully.                |
| [`07_video_comments.py`](examples/07_video_comments.py)               | Collect all comments (and replies) of a video.          |

## FAQ

<details>
<summary><b>Do I need a YouTube Data API key?</b></summary>

No. `ytscrape` uses the same internal endpoints as the YouTube web app, so
there is nothing to register and no quota to manage.
</details>

<details>
<summary><b>Why are some comments missing?</b></summary>

Because YouTube's default **"Top comments"** view hides less relevant comments
and "potential spam". Pass `sort="newest"` (or `CommentSort.NEWEST`) to collect
every comment.
</details>

<details>
<summary><b>Why is <code>like_count</code> <code>None</code>?</b></summary>

YouTube abbreviates large counts (`1.2K`), which cannot be expressed exactly as
an `int`. The raw string is always available in `like_count_text`.
</details>

<details>
<summary><b>Can I use a proxy or rotate IPs?</b></summary>

Yes — inject your own `requests.Session` into `InnerTubeClient`. See
[Advanced](#advanced-proxies-retries-custom-sessions).
</details>

<details>
<summary><b>Will I get rate limited?</b></summary>

There is no published quota, but YouTube may throttle aggressive traffic. Reuse
one `YouTube` instance (it keeps a warm session and context), request only what
you need with `max_results`, and add delays for large crawls.
</details>

<details>
<summary><b>Does it download videos?</b></summary>

No, and it is not planned — `ytscrape` is a metadata library. Use
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for media downloads.
</details>

<details>
<summary><b>Is scraping YouTube legal?</b></summary>

This library accesses private endpoints, which may conflict with YouTube's
Terms of Service. It is provided for research and educational purposes — you
are responsible for how you use it.
</details>

<details>
<summary><b>Is there an async API?</b></summary>

Not yet — it is the top item on the [Roadmap](#roadmap). Today you can run the
synchronous client in a thread pool (`asyncio.to_thread`).
</details>

## Roadmap

- ⚡ **Async API** (`asyncio` / `httpx`) alongside the synchronous one.
- 📺 **Channel tabs**: videos, Shorts, live, playlists, about.
- 🎵 **Playlist items** with transparent pagination.
- 📝 **Transcripts / subtitles**.
- 🔗 **Related videos**, **trending** and **home feed**.
- 🗒️ **Community posts**.
- 📚 A dedicated documentation site with an API reference.

Ideas and votes are welcome in
[issues](https://github.com/vsmutok/ytscrape/issues).

## Contributing

Contributions are very welcome — bug reports, ideas and pull requests alike.

```bash
git clone https://github.com/vsmutok/ytscrape
cd ytscrape
uv sync --dev
uv run pytest              # run the test suite
uv run pre-commit run --all-files   # ruff + format + bandit
```

The project uses [Ruff](https://github.com/astral-sh/ruff) for linting and
formatting, [bandit](https://github.com/PyCQA/bandit) for security checks and
`pre-commit` to run them all. See [CHANGELOG.md](CHANGELOG.md) for release
notes.

## License

[MIT](LICENSE)
