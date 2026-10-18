---
description: "Export to JSON and CSV — ytscrape, the Python YouTube scraper without an API key."
---

# Export to JSON and CSV

Every model (`Video`, `Comment`, `VideoDetails`, `Transcript`, …) can serialize
itself. Search and comment paginators expose the same helpers — no `list()`
needed. Module-level `dumps_json` / `dumps_csv` still work on any iterable.

```python
from ytscrape import YouTube

with YouTube() as yt:
    results = yt.search("python", max_results=10)
    results.dump_csv("search.csv")
    print(results.to_json())

    details = yt.video("dQw4w9WgXcQ")
    details.dump_json("video.json")

    thread = yt.comments("dQw4w9WgXcQ", max_results=50)
    thread.dump_csv("comments.csv")
    print(thread.to_json())
```

Async paginators use the same names, awaited:

```python
async with AsyncYouTube() as yt:
    results = await yt.search("python", max_results=10)
    await results.dump_csv("search.csv")
    print(await results.to_json())
```

CLI:

```bash
ytscrape search "python" --max 5 --format json
ytscrape comments dQw4w9WgXcQ --max 20 --format csv -o comments.csv
ytscrape video dQw4w9WgXcQ --format json -o video.json
```

JSON includes computed fields such as `url`. Search items also get a `type`
key (`video` / `channel` / `playlist`). Transcript CSV writes one row per
caption snippet.

## Subtitle files

Fetched transcripts also expose `to_srt()` / `to_vtt()` and
`dump_srt(path)` / `dump_vtt(path)` for SubRip and WebVTT subtitles:

```python
with YouTube() as yt:
    transcript = yt.transcript("dQw4w9WgXcQ", languages=["en"])
    transcript.dump_srt("captions.srt")
    transcript.dump_vtt("captions.vtt")
```

These helpers accept file paths or text streams. See the
[transcript guide](transcripts.md#exporting-subtitles) for timing and empty-caption
handling.
