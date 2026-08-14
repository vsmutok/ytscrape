# Export to JSON and CSV

Every model (`Video`, `Comment`, `VideoDetails`, `Transcript`, …) can serialize
itself. Collections of mixed search results use the module-level helpers.

```python
from pathlib import Path

from ytscrape import YouTube, dumps_csv, dumps_json

with YouTube() as yt:
    results = list(yt.search("python", max_results=10))
    print(results[0].to_json())
    Path("search.csv").write_text(dumps_csv(results), encoding="utf-8")

    details = yt.video("dQw4w9WgXcQ")
    details.dump_json("video.json")

    comments = list(yt.comments("dQw4w9WgXcQ", max_results=50))
    dumps_json(comments)  # string
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
