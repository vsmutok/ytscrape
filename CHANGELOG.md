# Changelog

All notable changes to **ytscrape** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] — 2026-10-08

### Added

- `VideoDetails.scheduled_at`: planned start time of scheduled premieres /
  upcoming live streams; shown as `Scheduled` in `ytscrape video` (#16).
- First-class proxy support: new `proxies` argument on `YouTube`,
  `AsyncYouTube`, `InnerTubeClient` and `AsyncInnerTubeClient` accepting a
  `requests`-style mapping (e.g. `{"https": "http://user:pass@host:8080"}`).
  The sync clients expose a settable `proxies` property for rotating proxies at
  runtime (e.g. after a `BotDetected` error) (#17).

### Changed

- `VideoDetails.published` / `published_at` (the publication date) are now
  `None` for scheduled videos that are not published yet, instead of the
  planned start time (#16). Docs and README highlight the publication date.

## [2.0.0] — 2026-10-02

### Added

- Reliability: `RetryPolicy` (exponential backoff, jitter, `Retry-After`),
  `RateLimiter` / `min_interval`, `ContextCache` with TTL and a global
  `DEFAULT_CONTEXT_CACHE` keyed by `(language, region)`. New client kwargs
  `retry`, `rate_limiter`, `min_interval`, `context_cache`.
- Exceptions: `YtScrapeError` base (alias `YtScraperError`), `RateLimited`,
  `BotDetected` (alias `CaptchaRequired`), `ConsentRequired`,
  `VideoUnavailable`, `AgeRestricted`; `RequestError.status_code` / `.url`.
- Debug logging on the `ytscrape` logger (requests, retries, timings).
- `YouTube.channel_videos()` / `AsyncYouTube.channel_videos()` returning lazy
  `ChannelVideos` / `AsyncChannelVideos`.
- Navigation helpers: `Video.details()/comments()/channel_details()`,
  `VideoDetails.comments()/channel_details()`, `Channel.details()/videos()`,
  `ChannelDetails.videos()`; `UnboundModelError` for unbound models.
- `Thumbnail(url, width, height)` and `thumbnails` tuples on all models.
- `VideoDetails.published_at` / `uploaded_at` datetimes; `Video.published_at`.
- Parse helpers `parse_count`, `parse_relative_time`, `parse_date`.
- CI: pytest matrix 3.10–3.14 with coverage (Codecov) and mypy, nightly
  live tests, Dependabot; publishing requires passing tests.
- Docs: reliability, models & navigation, channel videos, recipes, FAQ,
  migration guide.

### Changed (breaking)

- `Video.views` is `int | None` (raw text in `views_text`).
- `Video.published` removed → `published_text` + `published_at`.
- `Channel.subscribers` / `video_count`, `Playlist.video_count`,
  `ChannelDetails.subscribers` / `video_count` / `view_count` are
  `int | None` with `*_text` counterparts.
- `video()` raises `VideoUnavailable` / `AgeRestricted` / `BotDetected`.
- Exports serialise datetimes as ISO 8601 and thumbnails as lists of dicts.

### Fixed

- Examples updated for numeric counts.

## [1.0.1] - 2026-08-19

### Added

- Paginator export: `SearchResults` and `CommentThread` expose `to_json()` /
  `to_csv()` / `dump_json` / `dump_csv`. Async counterparts use
  `await results.to_json()` (and the same dump helpers). Streams honour
  `max_results` and write a JSON array or CSV table of items.

## [1.0.0] - 2026-08-14

### Changed

- CLI wordmark matches the brand logo: red `yt`, white `scrape`.
- CLI `--format` / `--output` / `--language` / `--region` work after the
  subcommand as well (`ytscrape search "JS" --format csv`).
- Search parsing uses only classic InnerTube renderers
  (`videoRenderer` / `channelRenderer` / `playlistRenderer`).
  `lockupViewModel` helpers and `from_lockup` factories are gone.

### Added

- Brand assets under `docs/assets/`: light/dark `ytscrape` wordmarks in the
  README header and on the docs home page, matching light/dark icons as the
  docs-site logo / favicon, and an animated CLI demo GIF in the README
  (CLI cheatsheet) and the CLI overview page.
- JSON / CSV export: models have `to_dict()` / `to_json()` / `to_csv()`
  (and `dump_json` / `dump_csv`). Collections use `dumps_json` /
  `dumps_csv`. CLI: `--format json|csv` and `--output FILE`.
- Colourful CLI: mini `▶ ytscrape` wordmark, boxed tables for search /
  video / channel / comments / transcripts. `--format plain` keeps the
  old TSV / key-value output; `--no-color` / `NO_COLOR` disable ANSI.
  Search tables omit the unused `Published` column when results are
  channels (or other non-video items). Table columns stay aligned when
  titles contain emoji or other wide characters (♥ stays single-width;
  emoji presentation such as ❤️ is double-width). Newlines in comments
  are flattened so they cannot break a table row. Search tables include a
  `URL` column for video watch links and channel pages. Table mode shows
  a braille spinner on stderr while a request is in flight.
- Richer video metadata: search `Video` fills `duration` / `views` /
  `published` / `description` from classic `videoRenderer` fields
  (`lengthText`, `viewCountText`, `publishedTimeText`, `descriptionSnippet`).
- `VideoDetails` now also reads player microformat: `published`,
  `upload_date`, `category`, `owner_profile_url`, `embed_url`, `is_private`,
  `is_upcoming`, `allow_ratings`, `is_family_safe`, `available_countries`.

## [0.1.5] - 2026-08-11

### Added

- ⚡ Async API: `AsyncYouTube` / `AsyncInnerTubeClient` with the same public
  surface as the sync facade (`search`, `video`, `channel`, `comments`,
  `transcript` / `transcripts`). Optional extra:
  `pip install "ytscrape[async]"` (`httpx`).
- Shared parsing path for sync and async (`ytscrape.parsing` + models).
- Async concurrency limit (`max_concurrency`) and exponential backoff with
  jitter on 429 / 5xx / transport errors (`max_retries`, `backoff_factor`).
- Async paginators: `AsyncSearchResults`, `AsyncCommentThread` (`async for`).
- Feature examples `01`–`09` now include both sync and async paths
  (`run_sync` / `run_async`, CLI flag `--async`).
- Concurrency-focused example `examples/10_async_concurrency.py`.
- Docs site updates: async guide (`docs/guides/async.md`),
  `docs/examples.md`, plus installation, quickstart, advanced, pagination,
  comments, transcripts, API pages, and a leaner README that points at docs
  instead of duplicating long guides.

## [0.1.4] - 2026-08-6

### Added

- 📝 Transcripts / captions via `YouTube.transcript()` and
  `YouTube.transcripts()`, modeled after youtube-transcript-api:
  ANDROID InnerTube `player` for caption tracks, timedtext XML download,
  language priority, manual-vs-ASR preference, optional server-side
  `translate()`, and CLI `ytscrape transcript`.
- New types: `Transcript`, `TranscriptSnippet`, `TranscriptTrack`,
  `TranscriptList`; errors `TranscriptsDisabled`, `NoTranscriptFound`.
- Example `examples/09_transcript.py`.
- 🖼️ Richer `ChannelDetails`: `photo` (avatar), `banner`, `country`,
  `joined_date`, `view_count`, and `links` as a platform→URL dictionary
  (e.g. `{"x": "…", "instagram": "…", "discord": "…"}`). About-panel fields
  are loaded via the channel engagement-panel continuation.
- 📺 Channel metadata with `YouTube.channel(channel)`. Pass a channel id
  (`UC…`), a `@handle`, or any channel URL (`/channel/…`, `/@handle`, `/c/…`,
  `/user/…`) and get a typed `ChannelDetails` model (title, description,
  handle, subscribers, video count, keywords/tags, avatar, vanity + RSS URLs,
  family-safe flag, available countries, external links).
- 🔌 New low-level `InnerTubeClient.browse()` / `get_html()` helpers used by
  channel resolution.
- 🖥️ New CLI command: `python -m ytscrape channel <id|@handle|url>`.
- 📚 New example `examples/08_channel_details.py`.

## [0.1.3] - 2026-08-5

### Added

- 💬 Collect the comments of a video with `YouTube.comments(video)`. Pass a
  video id or any YouTube URL and iterate over the returned `CommentThread`;
  it transparently pages through every comment (and reply), just like search
  results. Comments are exposed as a new `Comment` model (author, text, like &
  reply counts, published time, `is_reply`).
- ↳ Optional reply collection: `YouTube.comments(video, include_replies=True)`
  now also expands the replies of every comment thread. Each reply has
  `is_reply=True` and is yielded right after the comment it replies to; the CLI
  gained a matching `--replies` flag.
- 🖥️ New CLI command:
  `python -m ytscrape comments <video> [--max N] [--replies] [--sort top|newest]`.
- 🔀 New `sort` option for comment collection:
  `YouTube.comments(video, sort=CommentSort.NEWEST)` (or `sort="newest"`). The
  new `CommentSort` enum (`TOP` / `NEWEST`) is exported from the package top
  level, and the CLI gained a matching `--sort` flag.
- 📚 New example `examples/07_video_comments.py` showing how to collect
  comments (and their replies).
- ❤️ Richer `Comment` model: new `heart` flag (whether the video's creator
  hearted the comment) plus `like_count_text` / `reply_count_text` fields that
  keep YouTube's raw counts, including abbreviations such as `1.2K` that the
  integer `like_count` / `reply_count` cannot represent exactly.

## [0.1.2] - 2026-07-29

### Added

- 📚 New [`examples/`](examples/) folder with short, runnable, self-contained
  scripts: searching videos (`01_search_videos.py`), channels & playlists
  (`02_search_channels_playlists.py`), fetching video details
  (`03_video_details.py`), pagination (`04_pagination.py`), language & region
  localisation (`05_language_region.py`) and error handling
  (`06_error_handling.py`), plus an `examples/README.md` index.
- 🏷️ PyPI version badge in the README linking to the project page on PyPI.

### Changed

- 📝 Expanded the README with a link to the new `examples/` folder right after
  the Quick start section.

## [0.1.1] - 2026-07-29

### Added

- 🔎 Search YouTube videos, channels and playlists via a clean `SearchFilter`
  enum (no magic `params` strings in your code).
- 📄 Transparent pagination — iterate over results and continuation tokens are
  handled for you; `max_results` caps how many items you consume.
- 🎬 Fetch detailed video metadata from a video id or any YouTube URL.
- 🌍 Language & country support (`hl` / `gl`) through the `Language`, `Country`
  and `Locale` value objects, validated with `pycountry`.
- 🖥️ A tiny CLI: `python -m ytscrape ...` and a `ytscrape` console script.
- 📦 Automated PyPI publishing on version tags via the
  `.github/workflows/publish.yml` GitHub Action (Trusted Publishing / OIDC).
