# TODO

What's left in **ytscrape**. Rough priority order within each section.
`[ ]` — not yet · 🔥 — release blocker.


## InnerTube coverage

- [ ] Channel tabs: videos, shorts, live, playlists
- [ ] Playlist items (`yt.playlist()`)
- [ ] Related videos
- [ ] Trending / home feed
- [ ] Community posts
- [ ] Search filters: upload date, duration, features, sort
- [ ] Search within a channel or playlist
- [ ] Search suggestions

## Reliability

- [ ] Built-in retries + exponential backoff on **sync** `InnerTubeClient` (429 / 5xx)
  *(async client already has retries / backoff / concurrency)*
- [ ] Rate limiting option (sync + shared policy)
- [ ] Cached InnerTube context with TTL
- [ ] Detect captcha / consent / bot checks
- [ ] Richer exception hierarchy beyond `ParseError`
  *(transcript errors already exist: `TranscriptsDisabled`, `NoTranscriptFound`)*
- [ ] Optional request logging / debug mode

## Models

- [ ] Numeric fields where search/list APIs still return strings
  *(e.g. `Video.views`, `Channel.subscribers`; `VideoDetails.views` is already `int`)*
- [ ] Parsed `published_at: datetime` where available
- [ ] Navigation helpers: `video.comments()`, `video.channel()`, `channel.videos()`
- [ ] `.to_dict()` / `.to_json()` (or shared serializers)
- [ ] Thumbnails as a list of sizes (not only largest URL)

## CLI

- [ ] `--json` / `--jsonl` / `--csv` output
- [ ] Commands for playlist, trending, channel tabs (after library APIs)
- [ ] `--output`, `--quiet`, `--limit`, stable exit codes
- [ ] Progress for long collections
- [ ] Split handlers/formatters out of `__main__.py`

## Tests & CI

- [ ] 🔥 Run `pytest` in CI (today only pre-commit)
- [ ] Python 3.10–3.14 matrix
- [ ] Coverage + Codecov badge
- [ ] `mypy` / typecheck in CI (when ready)
- [ ] Network-marked live tests (nightly / manual)
- [ ] Snapshot fixtures of real InnerTube responses
- [ ] Dependabot / scheduled `pre-commit autoupdate`

## Docs
- [ ] Examples for playlists and CSV/JSON export
- [ ] CLI demo GIF in the README
- [ ] Optional benchmarks vs `yt-dlp` / Playwright
