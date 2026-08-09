# Fetch Channel Metadata with YouTube.channel() in ytscrape

> Retrieve rich metadata for any YouTube channel — subscribers, external links, banner, join date, and more — by id, handle, or URL.

`YouTube.channel()` fetches detailed metadata for a single YouTube channel and returns a `ChannelDetails` dataclass. It accepts a raw `UC…` channel id, an `@handle`, or any standard channel URL — all formats are resolved automatically.

## Calling `yt.channel()`

```python
from ytscrape import YouTube

with YouTube() as yt:
    # Channel id
    details = yt.channel("UCuAXFkgsw1L7xaCfnd5JJOw")

    # @handle
    details = yt.channel("@RickAstleyYT")

    # Full channel URL
    details = yt.channel("https://www.youtube.com/@RickAstleyYT")
```

## Supported input formats

| Format             | Example                                                    |
| ------------------ | ---------------------------------------------------------- |
| `UC…` channel id   | `UCuAXFkgsw1L7xaCfnd5JJOw`                                 |
| `@handle`          | `@RickAstleyYT`                                            |
| `/channel/UC…` URL | `https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw` |
| `/@handle` URL     | `https://www.youtube.com/@RickAstleyYT`                    |
| `/c/name` URL      | `https://www.youtube.com/c/RickAstleyYT`                   |
| `/user/name` URL   | `https://www.youtube.com/user/RickAstleyVEVO`              |

## Full example

The snippet below mirrors the official [examples/08\_channel\_details.py](https://github.com/vsmutok/ytscrape/blob/main/examples/08_channel_details.py) example and shows every commonly used field:

```python
from ytscrape import YouTube

with YouTube() as yt:
    # A channel id, @handle or any channel URL all work.
    details = yt.channel("https://www.youtube.com/@CodeBrux")

    print(f"Title:        {details.title}")
    print(f"Handle:       {details.handle}")
    print(f"Subscribers:  {details.subscribers}")
    print(f"Videos:       {details.video_count}")
    print(f"Views:        {details.view_count}")
    print(f"Country:      {details.country}")
    print(f"Joined:       {details.joined_date}")
    print(f"Family safe:  {details.is_family_safe}")
    print(f"Photo:        {details.photo}")
    print(f"Banner:       {details.banner}")
    print(f"Keywords:     {', '.join(details.keywords[:5])}")
    print(f"URL:          {details.url}")
    print(f"Vanity URL:   {details.vanity_url}")
    print(f"RSS:          {details.rss_url}")

    if details.links:
        print(f"Links:        {details.links}")
    if details.description:
        print(f"Description:  {details.description[:120]}...")
```

## The `links` field

`links` is a `dict[str, str]` mapping a platform name to its URL. The keys are derived from the link titles and URLs that the channel owner has added to their profile. Well-known platforms — `x`, `instagram`, `tiktok`, `facebook`, `spotify`, `discord`, `patreon`, `github`, and others — get a predictable lowercase key. Custom links fall back to a slugified version of their title.

```python
with YouTube() as yt:
    details = yt.channel("@RickAstleyYT")
    print(details.links)
    # e.g. {"x": "https://twitter.com/rickastley", "instagram": "https://instagram.com/..."}

    # Access a specific platform safely
    twitter = details.links.get("x")
```

If a channel has no external links, `links` is an empty dictionary.

## Field reference

`ChannelDetails` is a frozen dataclass. All fields are listed below.

| Field                 | Type              | Description                                                             |
| --------------------- | ----------------- | ----------------------------------------------------------------------- |
| `channel_id`          | `str`             | `UC…` channel id                                                        |
| `title`               | `str \| None`     | Channel display name                                                    |
| `description`         | `str \| None`     | Channel description                                                     |
| `handle`              | `str \| None`     | `@handle` when available                                                |
| `subscribers`         | `str \| None`     | Subscriber count as rendered by YouTube (e.g. `"1.23M subscribers"`)    |
| `video_count`         | `str \| None`     | Number of public videos                                                 |
| `view_count`          | `str \| None`     | Total channel view count                                                |
| `keywords`            | `tuple[str, ...]` | Channel keywords / tags                                                 |
| `tags`                | `tuple[str, ...]` | Microformat tags (may overlap with `keywords`)                          |
| `thumbnail`           | `str \| None`     | Channel avatar URL (alias for `photo`)                                  |
| `photo`               | `str \| None`     | Channel avatar URL                                                      |
| `banner`              | `str \| None`     | Channel banner image URL                                                |
| `vanity_url`          | `str \| None`     | Custom vanity URL (e.g. `https://www.youtube.com/@RickAstleyYT`)        |
| `rss_url`             | `str \| None`     | RSS feed URL for the channel's public videos                            |
| `is_family_safe`      | `bool \| None`    | Whether YouTube marks the channel as family-safe                        |
| `available_countries` | `tuple[str, ...]` | ISO 3166-1 alpha-2 country codes where the channel is available         |
| `country`             | `str \| None`     | Country the channel is registered in                                    |
| `joined_date`         | `str \| None`     | Join date as rendered by YouTube (e.g. `"Joined Oct 24, 2010"`)         |
| `links`               | `dict[str, str]`  | External social / website links — `{"x": "…", "instagram": "…"}`        |
| `url`                 | `str`             | Canonical `https://www.youtube.com/channel/UC…` URL (computed property) |

!!! note

    Inputs that use a handle or a `/c/`/`/user/` vanity path require an extra HTTP request to resolve the `UC…` channel id before the metadata request can be made. Passing the raw `UC…` id directly skips this lookup and is marginally faster.
