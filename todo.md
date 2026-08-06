# TODO

What's left to do in **ytscrape**. Items in each section are roughly ordered by
priority. `[x]` — done, `[ ]` — not yet, 🔥 — blocks the release.

## Done

- [x] Search: videos, channels, playlists, shorts, movies
- [x] Video details (`yt.video()`)
- [x] Channel metadata (`yt.channel()`)
- [x] Comments with transparent pagination
- [x] Replies (`include_replies=True`)
- [x] Comment sorting (`sort="top" | "newest"`)
- [x] Comment fields: hearts, raw like/reply counts
- [x] CLI (`python -m ytscrape`)
- [x] Examples + README

## Quick wins

- [ ] Remove or repurpose the root `main.py`
- [ ] Add `CONTRIBUTING.md` and link it from the README
- [ ] Add issue/PR templates in `.github/`

## InnerTube coverage

- [x] Channel metadata (`yt.channel()`)
- [ ] Channel tabs: videos, shorts, live, playlists
- [ ] Playlist items (`yt.playlist()`)
- [x] Transcripts / subtitles (`yt.transcript()` / `yt.transcripts()`)
- [ ] Related videos
- [ ] Trending / home feed
- [ ] Community posts
- [ ] Search filters: upload date, duration, features
- [ ] Search within a channel or playlist
- [ ] Search suggestions

## Async API

- [ ] `AsyncYouTube` with the same public API (optional `httpx` extra)
- [ ] Shared parsing for sync and async
- [ ] Concurrency limit and backoff

## Reliability

- [ ] Built-in retries with exponential backoff (429 / 5xx)
- [ ] Rate limiting option
- [ ] Cached InnerTube context with TTL
- [ ] Detect captcha / consent / bot checks
- [ ] Specific exceptions instead of one `ParseError`
- [ ] Optional request logging

## Models

- [ ] Numeric fields where YouTube returns strings (views, subscribers)
- [ ] Parsed `published_at: datetime`
- [ ] Navigation: `video.comments()`, `video.channel()`, `channel.videos()`
- [ ] `.to_dict()` / `.to_json()`
- [ ] Thumbnails as a list of sizes

## CLI

- [ ] `--json` / `--jsonl` / `--csv` output
- [x] Commands for channel + transcript (playlist/trending still open)
- [ ] Commands for playlist, trending
- [ ] `--output`, `--quiet`, `--limit`, stable exit codes
- [ ] Progress bar for long collections
- [ ] Proper argument parser with subcommand help

## Tests & CI

- [ ] 🔥 Run `pytest` in CI (only pre-commit runs today)
- [ ] Python 3.10–3.14 matrix
- [ ] Coverage + Codecov badge
- [ ] `mypy --strict` in CI
- [ ] Network-marked live tests on a nightly schedule
- [ ] Snapshot fixtures of real InnerTube responses
- [ ] Dependabot / scheduled `pre-commit autoupdate`

## Docs

- [ ] Docs site (MkDocs) on GitHub Pages
- [ ] API reference from docstrings
- [ ] Legal / ToS section
- [x] Examples for channels + transcripts
- [ ] Examples for playlists, async, CSV export
- [ ] CLI demo GIF in the README
- [ ] Reproducible benchmarks vs `yt-dlp` / Playwright
