# Handle ytscrape errors: exceptions and error hierarchy

> Understand the ytscrape exception hierarchy and learn which exception to catch for network errors, parse failures, and missing transcripts.

Every error raised by ytscrape derives from a single base class, `YtScraperError`, so you always have a clean catch-all. For finer-grained control, catch the specific subclasses described below.

## Exception hierarchy

| Exception                | Raised when                                                                                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `YtScraperError`         | Base class for every error in the table below.                                                                                             |
| `ContextExtractionError` | The InnerTube context (API key, client version, visitor data) could not be extracted from the YouTube home page.                           |
| `RequestError`           | An HTTP request to YouTube failed — network error, timeout, or a non-2xx response.                                                         |
| `ParseError`             | A YouTube response could not be parsed as expected (e.g. an unrecognised page structure, an invalid video id, or comments being disabled). |
| `TranscriptError`        | Base class for the two transcript-specific failures below.                                                                                 |
| `TranscriptsDisabled`    | The video has no caption tracks, or captions have been disabled by the uploader.                                                           |
| `NoTranscriptFound`      | Caption tracks exist, but none match any of the requested language codes.                                                                  |

## Code example

```python
from ytscrape import (
    YouTube,
    YtScraperError,
    RequestError,
    ParseError,
)


def main() -> None:
    with YouTube() as yt:
        # An invalid id/URL cannot be parsed into a video id.
        try:
            yt.video("not-a-real-video-id")
        except ParseError as exc:
            print(f"Could not parse video id: {exc}")

        # Network / HTTP failures surface as RequestError.
        try:
            details = yt.video("dQw4w9WgXcQ")
            print(f"Got: {details.title}")
        except RequestError as exc:
            print(f"Request to YouTube failed: {exc}")
        except YtScraperError as exc:
            # Catch-all for any other ytscrape error.
            print(f"Something went wrong: {exc}")


if __name__ == "__main__":
    main()
```

## Transcript exceptions in detail

The two transcript-specific exceptions carry extra context that helps you react appropriately.

### `NoTranscriptFound`

Raised when `yt.transcript()` or `TranscriptList.find_transcript()` cannot match any of the requested language codes to an available track.

| Attribute   | Type              | Description                                     |
| ----------- | ----------------- | ----------------------------------------------- |
| `video_id`  | `str`             | The video that was queried.                     |
| `requested` | `tuple[str, ...]` | The language codes that were requested.         |
| `available` | `tuple[str, ...]` | The language codes that are actually available. |

```python
from ytscrape import YouTube, NoTranscriptFound

with YouTube() as yt:
    try:
        transcript = yt.transcript("dQw4w9WgXcQ", languages=["zh", "ar"])
    except NoTranscriptFound as exc:
        print(f"Requested: {list(exc.requested)}")
        print(f"Available: {list(exc.available)}")
```

### `TranscriptsDisabled`

Raised when a video has no caption tracks at all.

| Attribute  | Type  | Description                            |
| ---------- | ----- | -------------------------------------- |
| `video_id` | `str` | The video whose captions are disabled. |

```python
from ytscrape import YouTube, TranscriptsDisabled

with YouTube() as yt:
    try:
        transcript = yt.transcript("VIDEO_WITHOUT_CAPTIONS")
    except TranscriptsDisabled as exc:
        print(f"Captions are disabled for: {exc.video_id}")
```

## When to catch each exception

| Goal                                                | Exception to catch       |
| --------------------------------------------------- | ------------------------ |
| Any network or HTTP problem                         | `RequestError`           |
| Bad input, disabled comments, unrecognised response | `ParseError`             |
| YouTube home page unreachable at startup            | `ContextExtractionError` |
| No captions at all on the video                     | `TranscriptsDisabled`    |
| Captions exist but not in the requested language    | `NoTranscriptFound`      |
| Any caption-related failure                         | `TranscriptError`        |
| Any ytscrape failure                                | `YtScraperError`         |

!!! tip

    Catching `YtScraperError` at the outermost level is the simplest guard when you don't need to distinguish the failure mode — for example in a CLI tool or a background worker that just logs the error and moves on.
