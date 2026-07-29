# ytscrape — Free YouTube Scraper for Python

[![PyPI version](https://img.shields.io/pypi/v/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![Python versions](https://img.shields.io/pypi/pyversions/ytscrape.svg)](https://pypi.org/project/ytscrape/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Free, open-source YouTube scraper library for Python.** Scrape YouTube
> search results — videos, channels, playlists and Shorts — plus detailed video
> metadata, **without an official YouTube Data API key** and **without any quota
> limits**.

`ytscrape` is a **free YouTube scraper and crawler** for Python built on top of
the internal YouTube *InnerTube* API. Use it to **search YouTube**, **extract
video, channel and playlist data**, and **fetch video metadata** — all with
**transparent pagination** and no API key required.

Whether you need to **scrape YouTube videos**, **collect channel data**, **mine
YouTube search results**, or build a **YouTube data extractor** or **dataset**,
`ytscrape` gives you a simple, Pythonic interface and a clean, extensible
architecture that is easy to grow with new endpoints and data sources.

**Keywords:** free youtube scraper, youtube scraper python, youtube data
extractor, youtube api without key, scrape youtube videos, youtube channel
scraper, youtube search scraper, youtube crawler, youtube metadata, python
youtube scraping library, open source youtube scraper.

> ⚠️ This library talks to YouTube's private endpoints. Use it responsibly and
> at your own risk; the endpoints and `params` values may change over time.

## Why ytscrape?

- ✅ **Free & open source** (MIT) — no paid plans, no sign-up, no rate-limit
  tiers.
- 🔑 **No YouTube Data API key required** and **no quota** to worry about.
- 🐍 **Pure Python** with full type hints and a tiny, dependency-light install.
- ⚡ Simple, Pythonic API — start scraping YouTube in just a few lines.

## Features

- 🔎 Search videos, channels and playlists with a clean `SearchFilter` enum
  (no magic `EgIQAQ==` strings in your code).
- 📄 **Transparent pagination** — just iterate; continuation tokens are handled
  for you.
- 🎬 Fetch detailed video metadata from an id or any YouTube URL.
- 🌍 **Language & country support** — localise results with the `Language`
  and `Country` value objects (thin wrappers around raw ISO codes, no
  hard-coded lists) bundled in a small `Locale` object; codes are validated
  with `pycountry`, so typos fail fast.
- 🧱 Extensible OOP design (facade + factory methods + strategy) and full type
  hints — easy to build on.
- 🖥️ A tiny CLI: `python -m ytscrape ...`.

## Installation

```bash
pip install ytscrape
```

From source:

```bash
pip install .
```

## Quick start

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
```

### Search filters

| Filter                     | Description         |
| -------------------------- | ------------------- |
| `SearchFilter.ALL`         | Everything (default)|
| `SearchFilter.VIDEOS`      | Videos only         |
| `SearchFilter.CHANNELS`    | Channels only       |
| `SearchFilter.PLAYLISTS`   | Playlists only      |
| `SearchFilter.SHORTS`      | Shorts only         |
| `SearchFilter.MOVIES`      | Movies only         |

You can also pass the string form: `yt.search("python", filter="videos")`.

### Language & country

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

### Pagination

Pagination is transparent — iterating over the result object automatically
loads the next page:

```python
results = yt.search("python")

for item in results:      # loads pages on demand
    print(item.title)
```

You can also page manually:

```python
results = yt.search("python")
print(len(results.fetch_next_page()))  # explicitly load one more page
print(results.has_more)                # is there another page?
```

Use `max_results` to cap how many items you consume.

## Use cases

`ytscrape` is a great fit when you want to:

- **Scrape YouTube search results** for a keyword or topic.
- **Extract YouTube video data** (title, channel, views, duration, thumbnails).
- **Collect YouTube channel and playlist listings** at scale.
- **Build a YouTube dataset** for research, analytics or machine learning.
- **Monitor YouTube** content for a niche without hitting API quotas.

## Command line

```bash
# Search
python -m ytscrape search "python tutorial" --filter videos --max 10

# Localised search (Ukrainian interface, Ukrainian region)
python -m ytscrape --language uk --region UA search "музика" --max 10

# Video details
python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

After installing, a `ytscrape` console script is also available:

```bash
ytscrape search "python" --filter channels --max 5
```

## License

[MIT](LICENSE)

    "build>=1.5.0",
    "twine>=7.0.0",
