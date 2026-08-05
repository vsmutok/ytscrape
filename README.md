# ytscrape — Free YouTube Scraper for Python

[![PyPI version](https://img.shields.io/pypi/v/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![Python versions](https://img.shields.io/pypi/pyversions/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![Release](https://github.com/vsmutok/ytscrape/actions/workflows/publish.yml/badge.svg)](https://github.com/vsmutok/ytscrape/actions/workflows/publish.yml)
[![Downloads](https://img.shields.io/pypi/dm/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Free, open-source YouTube scraper library for Python.** Scrape YouTube
> search results — videos, channels, playlists and Shorts — plus detailed video
> metadata, **without an official YouTube Data API key** and **without any quota
> limits**.

`ytscrape` is a **free YouTube scraper and crawler** for Python built on top of
the internal YouTube *InnerTube* API. Use it to **search YouTube**, **extract
video, channel and playlist data**, and **fetch video metadata** — all with
**transparent pagination** and no API key required. It is a **pure-HTTP YouTube
data extractor** with a simple, Pythonic interface and a clean, extensible
architecture, so whether you want to **scrape YouTube videos**, **collect
channel data**, **mine YouTube search results**, or build a **YouTube
dataset**, you can get started in just a few lines of code.

> ⚠️ This library talks to YouTube's private endpoints. Use it responsibly and
> at your own risk; the endpoints and `params` values may change over time.

## Table of Contents

- [Why ytscrape?](#why-ytscrape)
- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [ytscrape vs. YouTube Data API](#ytscrape-vs-youtube-data-api)
- [How it works](#how-it-works)
- [Search filters](#search-filters)
- [Language & country](#language--country)
- [Pagination](#pagination)
- [Comments](#comments)
- [Use cases](#use-cases)
- [Command line](#command-line)
- [License](#license)

## Why ytscrape?

- ✅ **Free & open source** (MIT) — no paid plans, no sign-up, no rate-limit
  tiers.
- 🔑 **No YouTube Data API key** and **no quota** — nothing to register or
  manage.
- 🐍 **Pure Python** with full type hints and a tiny, dependency-light install.
- ⚡ Simple, Pythonic API — start scraping YouTube in just a few lines.

## Features

- 🔑 **No YouTube Data API key required** and **no quota** to worry about.
- 📄 **Transparent pagination** — just iterate; continuation tokens are handled
  for you.
- 🎬 Fetch detailed **video metadata** from an id or any YouTube URL.
- 💬 **Scrape all comments** (and replies) of a video from an id or URL, with
  the same transparent pagination as search.
- 🔎 Search videos, channels and playlists with a clean `SearchFilter` enum
  (no magic `EgIQAQ==` strings in your code).
- 🌍 **Language & country support** — localise results with the `Language`
  and `Country` value objects (thin wrappers around raw ISO codes, no
  hard-coded lists) bundled in a small `Locale` object; codes are validated
  with `pycountry`, so typos fail fast.
- 🐍 **Pythonic API** with an extensible OOP design (facade + factory methods
  + strategy) and full type hints — easy to build on.
- 🖥️ A tiny **CLI**: `python -m ytscrape ...`.

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

## Quick start

```python
from ytscrape import YouTube

with YouTube() as yt:
    for video in yt.search("python", max_results=5):
        print(video.title)
```

> 📂 See more runnable examples in [`examples/`](examples/) — searching
> videos/channels/playlists, fetching video details, pagination, localisation
> and error handling.

Need more control? Filter by type, search channels and fetch full video
metadata:

```python
from ytscrape import YouTube, SearchFilter

with YouTube() as yt:
    # Search videos and iterate over as many pages as needed.
    for video in yt.search("python", filter=SearchFilter.VIDEOS, max_results=20):
        print(video.title, "-", video.url)

    # Search channels.
    for channel in yt.search("python", filter=SearchFilter.CHANNELS, max_results=5):
        print(channel.title, channel.url)

    # Fetch details for a single video (id or URL both work).
    details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(details.title, details.channel, details.views)

    # Collect all comments of a video (id or URL both work).
    for comment in yt.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", max_results=20
    ):
        print(comment.author, "-", comment.text)
```

## ytscrape vs. YouTube Data API

| Feature        | ytscrape | YouTube Data API |
| -------------- | :------: | :--------------: |
| API key        |    ❌    |        ✅        |
| Quota          |    ❌    |        ✅        |
| Pagination     |    ✅    |        ✅        |
| Video metadata |    ✅    |        ✅        |
| Search         |    ✅    |        ✅        |

(`❌` = not needed / no limit, `✅` = required / applies.)

## How it works

`ytscrape` is built on top of the private YouTube *InnerTube* API — the same
endpoints the YouTube web and mobile apps use internally.

- No browser.
- No Selenium.
- No Playwright.
- Pure HTTP.

## Search filters

| Filter                   | Description          |
| ------------------------ | -------------------- |
| `SearchFilter.ALL`       | Everything (default) |
| `SearchFilter.VIDEOS`    | Videos only          |
| `SearchFilter.CHANNELS`  | Channels only        |
| `SearchFilter.PLAYLISTS` | Playlists only       |
| `SearchFilter.SHORTS`    | Shorts only          |
| `SearchFilter.MOVIES`    | Movies only          |

You can also pass the string form: `yt.search("python", filter="videos")`.

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
ISO 639-1 / ISO 3166-1 alpha-2 code — there is no hard-coded list of languages
or countries, so any valid code works. Codes are validated with
[`pycountry`](https://pypi.org/project/pycountry/): an unknown language or
country code raises a `ValueError` instead of silently producing a broken
request. The chosen locale is sent both in the request context (`hl` / `gl`)
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

## Comments

Collect the comments of a video with `YouTube.comments()`. Pass a video id or
any YouTube URL; the returned `CommentThread` is a lazy iterable that
transparently pages through every comment, just like search results:

```python
from ytscrape import YouTube

with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=50):
        marker = "  ↳" if comment.is_reply else "-"
        print(f"{marker} {comment.author}: {comment.text}")
```

By default only **top-level** comments are collected. Pass
`include_replies=True` to also collect the **replies** of every thread; each
reply has `is_reply=True` and is yielded right after the comment it replies to:

```python
with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", include_replies=True):
        marker = "  ↳" if comment.is_reply else "-"
        print(f"{marker} {comment.author}: {comment.text}")
```

Each `Comment` exposes:

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

Omit `max_results` to iterate over **all** comments; pagination is handled for
you. When `include_replies=True`, `max_results` counts replies too. A
`ParseError` is raised if the video has comments disabled.

### Collecting *every* comment (sort order)

YouTube's default **"Top comments"** view quietly **hides some comments**
(less relevant ones and "potential spam"), so collecting in that order will
appear to *skip* comments. To get **every** comment, switch the sort order to
**"Newest first"** with the `sort` parameter:

```python
from ytscrape import YouTube, CommentSort

with YouTube() as yt:
    # `CommentSort.NEWEST` (or the string "newest") returns every comment.
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", sort=CommentSort.NEWEST):
        print(comment.author, "-", comment.text)
```

`sort` accepts a `CommentSort` (`TOP` / `NEWEST`) or its string value
(`"top"` / `"newest"`); it defaults to `CommentSort.TOP` to mirror YouTube's
default view.

## Use cases

`ytscrape` is a great fit when you want to:

- **Scrape YouTube search results** for a keyword or topic.
- **Extract YouTube video data** (title, channel, views, duration, thumbnails).
- **Scrape YouTube comments** (and replies) for sentiment or audience analysis.
- **Collect YouTube channel and playlist listings** at scale.
- **Build research datasets** for analytics or machine learning.
- **Build recommendation engines** on top of real YouTube data.
- **Monitor competitors** and their channels without hitting API quotas.
- **Run trend analysis** across topics, keywords and regions.

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

## License

[MIT](LICENSE)
