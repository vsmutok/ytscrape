# Detail models: VideoDetails and ChannelDetails API

> Reference for VideoDetails and ChannelDetails, the rich frozen dataclass models returned by YouTube.video() and YouTube.channel() respectively.

`VideoDetails` and `ChannelDetails` are the rich metadata models returned when you fetch a specific video or channel by ID, URL, or handle. Both are immutable frozen dataclasses. They carry far more information than the lightweight `Video` and `Channel` search-result models — including descriptions, keyword tuples, and (for channels) external links and analytics metadata.

## VideoDetails

Returned by `YouTube.video()`. Contains every piece of metadata available from the InnerTube player endpoint for a single video.

**`video_id`** (`str`)

:   The unique YouTube video identifier (e.g. `"dQw4w9WgXcQ"`). Never `None`.


**`title`** (`str | None`)

:   Full video title. `None` only if the player response omitted it entirely.


**`description`** (`str | None`)

:   The video's short description as stored in the player response. May be a truncated version of the full description shown on the watch page.


**`channel`** (`str | None`)

:   Display name of the uploading channel (the `author` field in the player response).


**`channel_id`** (`str | None`)

:   Internal channel identifier beginning with `UC`. Pass this directly to `YouTube.channel()` to fetch full channel details.


**`length_seconds`** (`int | None`)

:   Video duration in seconds as an integer (e.g. `212`). `None` for live streams or if parsing fails.


**`views`** (`int | None`)

:   Exact view count as an integer (e.g. `1458723912`). Unlike the search-result `views` string, this is a true integer suitable for arithmetic. `None` if unavailable.


**`keywords`** (`tuple[str, ...]`)

:   Tuple of SEO keyword strings attached to the video. Empty tuple if the video has no keywords.


**`is_live`** (`bool`)

:   `True` when YouTube reports the video as a live stream (`isLiveContent`). Always a bool, never `None`.


**`thumbnail`** (`str | None`)

:   URL of the highest-resolution thumbnail from the player response.


**`url`** (`str`)

:   **Property.** The canonical watch URL: `https://www.youtube.com/watch?v={video_id}`.


***

## ChannelDetails

Returned by `YouTube.channel()`. Aggregates metadata from the InnerTube `browse` endpoint plus the optional About-panel continuation. Fields that require the About panel (such as `joined_date`, `country`, `view_count`, and `links`) are `None` or empty when the About data is unavailable.

**`channel_id`** (`str`)

:   Internal channel identifier. Never `None`.


**`title`** (`str | None`)

:   Channel display name.


**`description`** (`str | None`)

:   Channel description. Populated from the About panel when available; falls back to the channel metadata or microformat description.


**`handle`** (`str | None`)

:   The channel's `@handle` (e.g. `"@RickAstleyYT"`). Extracted from the page header metadata or the vanity URL.


**`subscribers`** (`str | None`)

:   Formatted subscriber count as YouTube renders it (e.g. `"1.23M subscribers"`).


**`video_count`** (`str | None`)

:   Formatted video count (e.g. `"142 videos"`).


**`view_count`** (`str | None`)

:   Formatted total view count as shown in the About panel (e.g. `"1,234,567,890 views"`). Requires the About panel data; `None` otherwise.


**`keywords`** (`tuple[str, ...]`)

:   Tuple of channel keywords parsed from the metadata. Quoted phrases (e.g. `"lo-fi music"`) are kept intact as single entries. Falls back to `tags` when empty.


**`thumbnail`** (`str | None`)

:   URL of the channel avatar. Identical to `photo` — both fields are set to the same value for convenience.


**`photo`** (`str | None`)

:   Alias for `thumbnail`. The channel avatar URL. Both fields are always set to the same value; choose whichever name reads more naturally in your code.


**`banner`** (`str | None`)

:   URL of the channel's banner image, extracted from the page header. `None` if the channel has no banner or the header format is unrecognised.


**`vanity_url`** (`str | None`)

:   The channel's vanity URL (e.g. `"https://www.youtube.com/@RickAstleyYT"`). Always normalised to `https://`.


**`rss_url`** (`str | None`)

:   The channel's public RSS feed URL (e.g. `"https://www.youtube.com/feeds/videos.xml?channel_id=UC…"`).


**`is_family_safe`** (`bool | None`)

:   YouTube's family-safe flag. `None` when the flag is absent from the response.


**`tags`** (`tuple[str, ...]`)

:   Tuple of microformat tags (broad topic labels set by the channel owner).


**`available_countries`** (`tuple[str, ...]`)

:   ISO 3166-1 alpha-2 country codes where the channel's content is available (e.g. `("US", "GB", "DE")`). Empty tuple when not specified.


**`country`** (`str | None`)

:   The country the channel is associated with, as shown in the About panel (e.g. `"United Kingdom"`). Requires the About panel data.


**`joined_date`** (`str | None`)

:   The date the channel joined YouTube, formatted as YouTube renders it in the About panel (e.g. `"Joined Jul 27, 2009"`). Requires the About panel data.


**`links`** (`dict[str, str]`)

:   A dictionary mapping platform keys to external URLs (e.g. `{"x": "https://x.com/rickastley", "instagram": "https://instagram.com/…"}`). Keys are normalised platform slugs such as `"instagram"`, `"x"`, `"tiktok"`, `"patreon"`, or a slugified domain name for unrecognised platforms. Requires the About panel data; empty dict otherwise.


**`url`** (`str`)

:   **Property.** The canonical channel URL: `https://www.youtube.com/channel/{channel_id}`.


***

## Code example

```python
from ytscrape import YouTube

yt = YouTube()

# --- VideoDetails ---
video = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

print(video.title)  # "Rick Astley - Never Gonna Give You Up (Official Music Video)"
print(video.channel)  # "Rick Astley"
print(video.channel_id)  # "UCuAXFkgsw1L7xaCfnd5JJOw"
print(video.views)  # 1458723912  (integer)
print(video.length_seconds)  # 212
print(video.is_live)  # False
print(video.keywords[:3])  # ('Rick Astley', 'Never Gonna Give You Up', 'pop')
print(video.url)  # "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Convert duration to minutes:seconds
mins, secs = divmod(video.length_seconds, 60)
print(f"{mins}:{secs:02d}")  # "3:32"

# --- ChannelDetails ---
channel = yt.channel("@RickAstleyYT")

print(channel.title)  # "Rick Astley"
print(channel.handle)  # "@RickAstleyYT"
print(channel.subscribers)  # "4.36M subscribers"
print(channel.joined_date)  # "Joined Oct 24, 2013"
print(channel.country)  # "United Kingdom"
print(channel.banner)  # "https://yt3.googleusercontent.com/…"

# Iterate external links
for platform, link_url in channel.links.items():
    print(f"{platform}: {link_url}")
# x: https://x.com/rickastley
# instagram: https://www.instagram.com/officialrickastley/
```

!!! note

    `ChannelDetails.thumbnail` and `ChannelDetails.photo` always contain the same URL. The `photo` alias exists for readability — use whichever feels more natural for the context (e.g. `channel.photo` in a UI context, `channel.thumbnail` when treating channels uniformly with videos).
