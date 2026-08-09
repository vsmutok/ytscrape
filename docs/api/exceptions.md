# Exception classes and error hierarchy — ytscrape reference

> Reference for every exception class raised by ytscrape, covering the full class hierarchy, extra attributes, and when each exception is raised.

All errors raised by ytscrape are subclasses of a single base exception, `YtScraperError`. This makes it easy to write a broad catch-all while still being able to distinguish specific failure modes when you need to react differently. The hierarchy splits into four concrete error categories and one abstract transcript sub-hierarchy.

## Exception hierarchy

```
YtScraperError
├── ContextExtractionError
├── RequestError
├── ParseError
└── TranscriptError
    ├── TranscriptsDisabled
    └── NoTranscriptFound
```

## Import path

```python
from ytscrape import (
    YtScraperError,
    ContextExtractionError,
    RequestError,
    ParseError,
    TranscriptError,
    TranscriptsDisabled,
    NoTranscriptFound,
)
```

***

## `YtScraperError`

The base class for every exception in ytscrape. Catching `YtScraperError` guarantees you will not miss any library-raised error, regardless of which operation triggered it.

**Inherits from:** `Exception`

!!! tip

    Use `YtScraperError` as a broad catch-all in production code where you want to handle any ytscrape failure in a uniform way — for example, logging the error and returning a graceful empty result — without caring about the specific failure mode.


***

## `ContextExtractionError`

**Inherits from:** `YtScraperError`

Raised when ytscrape cannot extract the InnerTube context from the YouTube page. The InnerTube context (API key, client version, and related fields) is bootstrapped from the initial page HTML; if that HTML is missing the expected data — because of a YouTube layout change, a bot-detection response, or a network error at page-load time — this exception is raised before any API call is attempted.

**Extra attributes:** none beyond the message string.

***

## `RequestError`

**Inherits from:** `YtScraperError`

Raised when an HTTP request to a YouTube InnerTube endpoint fails. This covers network-level failures such as timeouts, connection errors, and non-2xx responses from the API.

**Extra attributes:** none beyond the message string.

***

## `ParseError`

**Inherits from:** `YtScraperError`

Raised when a YouTube API response cannot be parsed into the expected structure. This can happen if YouTube changes its response schema, returns an unexpected payload, or when comments are disabled for a video and the expected comment continuation data is absent.

**Extra attributes:** none beyond the message string.

***

## `TranscriptError`

**Inherits from:** `YtScraperError`

Abstract base class for all transcript and caption-related failures. Catch this type to handle any transcript problem without distinguishing between captions being absent entirely versus the requested language not being available.

**Extra attributes:** none beyond the message string.

***

## `TranscriptsDisabled`

**Inherits from:** `TranscriptError`

Raised when a video has no caption tracks at all — either because the owner has disabled subtitles or because YouTube returned no caption data for the video.

### Constructor

**`video_id`** (`str`) **required**

:   The YouTube video ID for which captions were requested.


### Attributes

**`video_id`** (`str`)

:   The ID of the video that has no available caption tracks.


***

## `NoTranscriptFound`

**Inherits from:** `TranscriptError`

Raised when the video has caption tracks but none of them match any of the requested languages. The exception carries the full list of requested languages and the languages that were actually available, making it straightforward to surface a helpful error message or fall back to an available language.

### Constructor

**`video_id`** (`str`) **required**

:   The YouTube video ID for which the transcript was requested.


**`requested`** (`tuple[str, ...] | list[str]`) **required**

:   The ordered list of language codes that were requested but not found.


**`available`** (`tuple[str, ...] | list[str] | None`)

:   The language codes of caption tracks that are actually available for the video. Defaults to an empty tuple when not provided. Displayed as `"(none listed)"` in the exception message if empty.


### Attributes

**`video_id`** (`str`)

:   The ID of the video whose transcript could not be found.


**`requested`** (`tuple[str, ...]`)

:   The language codes that were requested, stored as a tuple.


**`available`** (`tuple[str, ...]`)

:   The language codes of caption tracks that are available for this video, stored as a tuple. Empty if YouTube returned no language list.


***

## Complete try/except example

The following example covers all exception types, from the most specific to the broadest catch-all:

```python
import ytscrape
from ytscrape import (
    YtScraperError,
    ContextExtractionError,
    RequestError,
    ParseError,
    TranscriptsDisabled,
    NoTranscriptFound,
    TranscriptError,
)

yt = ytscrape.YouTube()
video_id = "dQw4w9WgXcQ"

try:
    transcript = yt.transcript(video_id, languages=["en", "de"])

except TranscriptsDisabled as exc:
    # The video has no caption tracks at all
    print(f"Captions are disabled for video '{exc.video_id}'.")

except NoTranscriptFound as exc:
    # Captions exist, but not in any of the requested languages
    print(
        f"No transcript in {list(exc.requested)} for '{exc.video_id}'. "
        f"Available languages: {list(exc.available) or 'none listed'}."
    )

except TranscriptError as exc:
    # Catch-all for any other transcript/caption failure
    print(f"Transcript error: {exc}")

except ContextExtractionError as exc:
    # ytscrape couldn't bootstrap the InnerTube context from the page
    print(f"Could not extract InnerTube context: {exc}")

except RequestError as exc:
    # Network or HTTP-level failure
    print(f"HTTP request failed: {exc}")

except ParseError as exc:
    # Unexpected response structure from the API
    print(f"Could not parse YouTube response: {exc}")

except YtScraperError as exc:
    # Broad catch-all for any other ytscrape error
    print(f"ytscrape error: {exc}")
```
