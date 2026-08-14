# ytscrape CLI: search, video, channel, comments, transcript

> Complete reference for the ytscrape command-line interface — search, video, channel, comments, and transcript subcommands explained.

ytscrape ships a built-in command-line interface that is available in two equivalent forms: as the `ytscrape` console script registered automatically when you install the package with pip, and as the `python -m ytscrape` module invocation. Both entry points share the same parser and produce identical output, so you can use whichever fits your workflow.

<p align="center">
  <img src="../../assets/demo_cli.gif" alt="ytscrape CLI demo" width="720">
</p>

## Global options

These flags apply to every subcommand and can be placed **before or after** the subcommand name (`ytscrape --format json search "python"` and `ytscrape search "python" --format json` are equivalent).

| Flag         | Metavar | Default | Description                                                                 |
| ------------ | ------- | ------- | --------------------------------------------------------------------------- |
| `--language` | `HL`    | `en`    | Interface language sent as the `hl` parameter, e.g. `en`, `uk`, `de`.       |
| `--region`   | `GL`    | `US`    | Content region sent as the `gl` parameter, e.g. `US`, `UA`, `DE`.           |
| `--format`   | —       | `table` | `table` prints a colourful box table; `plain` keeps the old script output; `json` / `csv` export structured data. |
| `--output` / `-o` | `FILE` | stdout | Write `json` / `csv` to a file instead of stdout. |
| `--no-color` | —       | off     | Disable ANSI colours. Also honoured via the `NO_COLOR` environment variable. |
| `--no-logo`  | —       | off     | Hide the mini `▶ ytscrape` wordmark (red `yt`, white `scrape`) shown above table output. |
| `--version`  | —       | —       | Print the installed ytscrape version and exit.                              |

Table mode also draws a small spinner on stderr (`⠋ searching…`) while the request is in flight. `--format plain` and non-TTY stderr skip it so scripts stay clean.

Global flags (`--format`, `--output`, `--language`, …) work **before or after** the subcommand:

```bash
# Structured export (stdout or -o FILE)
ytscrape search "python" --max 5 --format json
ytscrape comments dQw4w9WgXcQ --max 20 --format csv -o comments.csv
```

```bash
# Print the installed version
ytscrape --version

# All subcommands accept --language and --region before the subcommand name
ytscrape --language uk --region UA search "музика" --max 5
```

***

## `search`

Search YouTube and print matching results. The default `--format table` layout is a boxed table (type, title, channel, duration, views, URL; plus published for video results) under a colourful `▶ ytscrape` wordmark. Channel rows have no publish date, so that column is omitted when the result set has no videos. The last column is the watch URL for videos or the channel URL for channels. Use `--format plain` for the old script-friendly `<title>\t<url>` lines.

```
ytscrape search <query> [--filter FILTER] [--max N]
```

| Argument / Flag | Type              | Default | Description                                                                                            |
| --------------- | ----------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `query`         | positional string | —       | The search query.                                                                                      |
| `--filter`      | choice            | `all`   | Narrow results by type. Accepted values: `all`, `videos`, `channels`, `playlists`, `shorts`, `movies`. |
| `--max`         | integer           | `10`    | Maximum number of results to print.                                                                    |

```bash
# Search for videos — return up to 10 results (default)
ytscrape search "python tutorial" --filter videos

# Search for channels and return up to 25 results
ytscrape search "python" --filter channels --max 25

# Search for playlists with no result cap
ytscrape search "lofi study" --filter playlists --max 50

# Localised search — Ukrainian interface and region
ytscrape --language uk --region UA search "музика" --max 10
```

***

## `video`

Fetch and print metadata for a single YouTube video. Accepts either a bare video ID or any recognised YouTube URL (`watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`).

```
ytscrape video <video>
```

| Argument | Type              | Description      |
| -------- | ----------------- | ---------------- |
| `video`  | positional string | Video ID or URL. |

The command prints the following fields:

| Field     | Description                                                    |
| --------- | -------------------------------------------------------------- |
| `Title`   | Video title.                                                   |
| `Channel` | Uploader channel name.                                         |
| `Views`   | Total view count.                                              |
| `Length`  | Duration in seconds (printed with an `s` suffix, e.g. `213s`). |
| `URL`     | Canonical watch URL.                                           |

```bash
# Fetch by full URL
ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Fetch by bare video ID
ytscrape video dQw4w9WgXcQ

# Short URL form also works
ytscrape video https://youtu.be/dQw4w9WgXcQ
```

***

## `channel`

Fetch and print metadata for a single YouTube channel. Accepts a bare channel ID (`UC…`), an `@handle`, or any recognised channel URL (`/@handle`, `/channel/UC…`, `/c/…`, `/user/…`).

```
ytscrape channel <channel>
```

| Argument  | Type              | Description                    |
| --------- | ----------------- | ------------------------------ |
| `channel` | positional string | Channel ID, `@handle`, or URL. |

The command prints the following fields (conditional fields are omitted when empty):

| Field         | Description                           |
| ------------- | ------------------------------------- |
| `Title`       | Channel display name.                 |
| `Handle`      | `@handle` of the channel.             |
| `Subscribers` | Subscriber count.                     |
| `Videos`      | Total number of uploaded videos.      |
| `Views`       | Total channel view count.             |
| `Country`     | Country set on the channel.           |
| `Joined`      | Channel creation date.                |
| `Photo`       | URL of the channel avatar.            |
| `Banner`      | URL of the channel banner image.      |
| `Channel id`  | Internal `UC…` channel identifier.    |
| `URL`         | Canonical channel URL.                |
| `Vanity URL`  | Custom `/c/…` URL, if set.            |
| `Links`       | External links listed on the channel. |

```bash
# Fetch by @handle
ytscrape channel @RickAstleyYT

# Fetch by channel ID
ytscrape channel UCuAXFkgsw1L7xaCfnd5JJOw

# Fetch by full URL
ytscrape channel https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw
```

***

## `comments`

Collect and print comments for a YouTube video. Each line is printed in the format `<author>: <text>`; replies are indented with a ` ↳` prefix.

```
ytscrape comments <video> [--max N] [--replies] [--sort top|newest]
```

| Argument / Flag | Type              | Default | Description                                                 |
| --------------- | ----------------- | ------- | ----------------------------------------------------------- |
| `video`         | positional string | —       | Video ID or URL.                                            |
| `--max`         | integer           | `20`    | Maximum number of comments to print. Pass `0` for no limit. |
| `--replies`     | flag              | off     | Also collect replies to every top-level comment.            |
| `--sort`        | choice            | `top`   | Sort order. Accepted values: `top`, `newest`.               |

```bash
# Fetch the top 20 comments (default)
ytscrape comments https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Fetch up to 100 comments, including replies
ytscrape comments dQw4w9WgXcQ --max 100 --replies

# Fetch comments in newest-first order (no limit)
ytscrape comments dQw4w9WgXcQ --max 0 --sort newest
```

!!! note

    YouTube's default **"Top comments"** view silently hides low-relevance comments and suspected spam, so a `--sort top` run will appear to skip some comments. Use `--sort newest` to collect **every** comment in reverse-chronological order — this is the only sort order that guarantees complete coverage.


***

## `transcript`

Fetch and print the caption transcript for a YouTube video. Before the transcript lines, a summary header is printed in the form `# <video_id> | <language_code> | generated=<bool> | snippets=<count>`. Each subsequent line is printed with its timestamp offset and duration: `[   12.40 +  4.20] Hello world`.

```
ytscrape transcript <video> [--lang CODE ...] [--list] [--preserve-formatting]
```

| Argument / Flag         | Type              | Default | Description                                                                            |
| ----------------------- | ----------------- | ------- | -------------------------------------------------------------------------------------- |
| `video`                 | positional string | —       | Video ID or URL.                                                                       |
| `--lang CODE`           | repeatable string | `en`    | Preferred language code. Repeat the flag to specify fallback languages tried in order. |
| `--list`                | flag              | off     | List available caption tracks without downloading any transcript.                      |
| `--preserve-formatting` | flag              | off     | Keep basic HTML formatting tags (e.g. `<b>`, `<i>`) in snippet text.                   |

```bash
# Fetch the English transcript (default)
ytscrape transcript dQw4w9WgXcQ

# Prefer Ukrainian, fall back to English if unavailable
ytscrape transcript dQw4w9WgXcQ --lang uk --lang en

# List all available caption tracks without downloading
ytscrape transcript dQw4w9WgXcQ --list

# Fetch English transcript, preserving HTML formatting tags
ytscrape transcript dQw4w9WgXcQ --lang en --preserve-formatting
```

!!! tip

    Run `--list` first to discover which language codes are available for a video before fetching. Auto-generated tracks are clearly identified in the listing so you can choose between a human-edited caption and a machine-generated one.
