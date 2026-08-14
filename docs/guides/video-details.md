# Fetch Video Metadata with YouTube.video() in ytscrape

> Retrieve rich metadata for any YouTube video — title, description, view count, duration, keywords, and more — using a video id or URL.

`YouTube.video()` fetches detailed metadata for a single video and returns a `VideoDetails` dataclass. It accepts either a bare 11-character video id or any standard YouTube URL — no extra parsing needed on your side.

## Calling `yt.video()`

Pass a video id or any URL that embeds one. The method extracts the id automatically from all common URL formats.

```python
from ytscrape import YouTube

with YouTube() as yt:
    # Plain video id
    details = yt.video("dQw4w9WgXcQ")

    # Or any YouTube URL — all formats work
    details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```

## Supported URL formats

| Format      | Example                                       |
| ----------- | --------------------------------------------- |
| `watch?v=`  | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| `youtu.be/` | `https://youtu.be/dQw4w9WgXcQ`                |
| `/shorts/`  | `https://www.youtube.com/shorts/dQw4w9WgXcQ`  |
| `/embed/`   | `https://www.youtube.com/embed/dQw4w9WgXcQ`   |

## Full example

The snippet below mirrors the official [examples/03\_video\_details.py](https://github.com/vsmutok/ytscrape/blob/main/examples/03_video_details.py) example and shows every commonly used field:

```python
from ytscrape import YouTube

with YouTube() as yt:
    # A plain id or any YouTube URL both work.
    details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    print(f"Title:     {details.title}")
    print(f"Channel:   {details.channel}")
    print(f"Views:     {details.views}")
    print(f"Length:    {details.length_seconds}s")
    print(f"Published: {details.published}")
    print(f"Category:  {details.category}")
    print(f"Live:      {details.is_live}")
    print(f"Keywords:  {', '.join(details.keywords[:5])}")
    print(f"URL:       {details.url}")
```

You can also access the full description and the channel id for further lookups:

```python
with YouTube() as yt:
    details = yt.video("dQw4w9WgXcQ")

    print(details.description)
    print(details.channel_id)  # UC…
    print(details.thumbnail)  # URL of the highest-resolution thumbnail
```

## Field reference

`VideoDetails` is a frozen dataclass. All fields are listed below.

| Field            | Type              | Description                                                           |
| ---------------- | ----------------- | --------------------------------------------------------------------- |
| `video_id`       | `str`             | Unique 11-character YouTube video id                                  |
| `title`          | `str \| None`     | Video title                                                           |
| `description`    | `str \| None`     | Full video description                                                |
| `channel`        | `str \| None`     | Display name of the uploading channel                                 |
| `channel_id`     | `str \| None`     | `UC…` id of the uploading channel                                     |
| `length_seconds` | `int \| None`     | Duration of the video in seconds                                      |
| `views`          | `int \| None`     | Total view count as an integer                                        |
| `keywords`       | `tuple[str, ...]` | Tags / keywords associated with the video                             |
| `is_live`              | `bool`              | `True` if the video is a live stream or live content                  |
| `thumbnail`            | `str \| None`       | URL of the highest-resolution available thumbnail                     |
| `published`            | `str \| None`       | ISO publish date from player microformat (e.g. `2009-10-25`)          |
| `upload_date`          | `str \| None`       | ISO upload date                                                       |
| `category`             | `str \| None`       | YouTube category (e.g. `Music`)                                       |
| `owner_profile_url`    | `str \| None`       | Channel profile / vanity URL                                          |
| `embed_url`            | `str \| None`       | Embed iframe URL                                                      |
| `is_private`           | `bool`              | `True` if the player reports the video as private                     |
| `is_upcoming`          | `bool`              | `True` for scheduled premieres                                        |
| `allow_ratings`        | `bool \| None`      | Whether likes/ratings are enabled                                     |
| `is_family_safe`       | `bool \| None`      | Family-safe flag from microformat                                     |
| `available_countries`  | `tuple[str, ...]`   | ISO country codes where the video is available                        |
| `url`                  | `str`               | Canonical `https://www.youtube.com/watch?v=…` URL (computed property) |

!!! note

    `length_seconds` is an `int` (e.g. `212`), not a formatted string like `"3:32"`. To display a human-readable duration, convert it yourself: `f"{details.length_seconds // 60}:{details.length_seconds % 60:02d}"`.
