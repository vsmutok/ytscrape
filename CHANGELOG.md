# Changelog

All notable changes to **ytscrape** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
