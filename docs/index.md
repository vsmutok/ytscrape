# ytscrape — Free Open-Source Python YouTube Scraper

> Learn what ytscrape is, how it uses YouTube's InnerTube API over plain HTTP, and how it compares to the YouTube Data API, yt-dlp, and browser automation.

ytscrape is a free, open-source Python library that lets you search YouTube, extract video and channel metadata, collect comments and replies, and fetch transcripts — all without an API key, a quota, or a headless browser. It communicates directly with YouTube's internal *InnerTube* API (the same private endpoints the YouTube web app itself uses) through plain HTTP requests, parses the responses into fully-typed, frozen dataclasses, and handles pagination for you automatically.

## Features

!!! abstract "No API Key Required"

    ytscrape uses YouTube's internal InnerTube endpoints — no Google Cloud project, no credential management, and no quota to exhaust.


!!! abstract "No Browser Needed"

    Pure HTTP only. No Selenium, no Playwright, no headless Chrome. Install it and start scraping immediately.


!!! abstract "Search YouTube"

    Search for videos, channels, playlists, Shorts, and movies using `SearchFilter`. Pass a `max_results` cap or iterate indefinitely.


!!! abstract "Video & Channel Metadata"

    Fetch rich details via `yt.video()` and `yt.channel()`. Typed models surface every field — views, duration, subscribers, join date, links, and more.


!!! abstract "Comments & Replies"

    Collect every comment with `yt.comments()`. Include threaded replies with `include_replies=True`, and use `CommentSort.NEWEST` to ensure no comment is skipped.


!!! abstract "Transcripts & Subtitles"

    List available caption tracks with `yt.transcripts()` and download a preferred one with `yt.transcript()`. Manual captions are automatically preferred over auto-generated ones.

## How ytscrape Compares

|                         | **ytscrape** | YouTube Data API | `yt-dlp` | Browser automation |
| ----------------------- | :----------: | :--------------: | :------: | :----------------: |
| API key required        |       ❌      |         ✅        |     ❌    |          ❌         |
| Daily quota             |       ❌      |         ✅        |     ❌    |          ❌         |
| Browser / driver needed |       ❌      |         ❌        |     ❌    |          ✅         |
| Search                  |       ✅      |         ✅        |     ✅    |          ✅         |
| Video metadata          |       ✅      |         ✅        |     ✅    |          ✅         |
| Comments + replies      |       ✅      |     ✅ (quota)    |     ✅    |          ✅         |
| Typed Python models     |       ✅      |         ❌        |     ❌    |          ❌         |
| Downloads media         |       ❌      |         ❌        |     ✅    |          ✅         |
| Install size            |     tiny     |      medium      |   large  |        huge        |

**Rule of thumb:** use `yt-dlp` when you need to download media, the official Data API when you need guaranteed, ToS-blessed access, and ytscrape when you need **fast, key-less access to YouTube metadata and comments** from Python.

## How It Works

ytscrape speaks YouTube's private *InnerTube* API directly, with no browser in the loop:

1. **Context extraction.** On first use, ytscrape fetches `youtube.com` once and extracts the InnerTube context — the API key, client version, and visitor data — embedded in the page's initial JavaScript.

2. **POST requests.** Every subsequent call POSTs to one of YouTube's internal JSON endpoints — `youtubei/v1/search`, `youtubei/v1/player`, `youtubei/v1/browse`, or `youtubei/v1/next` — with that context attached as the request body.

3. **Typed parsing.** Responses are parsed from deeply-nested JSON into small, frozen dataclasses (`Video`, `Channel`, `VideoDetails`, `Comment`, etc.) with full type hints. The package ships `py.typed`, so mypy and pyright see every field.

4. **Transparent pagination.** Continuation tokens returned by YouTube are stored internally. Iterating the result object automatically fires the next page request whenever you exhaust the current batch — you never handle tokens manually.

!!! note

    ytscrape accesses YouTube's private, undocumented endpoints. The API contracts and internal `params` values may change without notice. Use this library responsibly, respect YouTube's Terms of Service, and avoid aggressive request rates. It is provided for research and educational purposes — you are responsible for your usage.


## Next Steps

Ready to make your first request? Head to the [Quickstart](quickstart.md) to install ytscrape and run your first search in under five minutes.
