# Fetch YouTube video transcripts and captions with ytscrape

> Download timed caption snippets for any YouTube video, list available language tracks, and translate them server-side with ytscrape.

ytscrape can download the full timed transcript for any video that has captions enabled — manually created or auto-generated. No API key is required; the library talks directly to the same timedtext endpoint the YouTube web player uses.

## Fetching a transcript

Pass a video id or URL together with a language preference list. `yt.transcript()` returns a `Transcript` object containing every timed caption snippet:

```python
from ytscrape import YouTube

with YouTube() as yt:
    transcript = yt.transcript("dQw4w9WgXcQ", languages=["en"])
    print(f"{transcript.language} ({transcript.language_code})")
    print(f"Auto-generated: {transcript.is_generated}")
    print(f"Snippets: {len(transcript)}")
    print(transcript.text[:200])
```

## Language preference list

`languages` is tried in order. Within each language code, a **manually created** caption track is preferred over an **auto-generated (ASR)** one — the same behaviour as `youtube-transcript-api`. If none of the requested languages are available, `NoTranscriptFound` is raised.

```python
# Prefer Ukrainian; fall back to English if no Ukrainian track exists.
transcript = yt.transcript(video_id, languages=["uk", "en"])
```

## The `Transcript` object

| Attribute / method | Type                            | Description                                                          |
| ------------------ | ------------------------------- | -------------------------------------------------------------------- |
| `snippets`         | `tuple[TranscriptSnippet, ...]` | All timed caption lines.                                             |
| `video_id`         | `str`                           | The video this transcript belongs to.                                |
| `language`         | `str`                           | Human-readable language name (e.g. `"English"`).                     |
| `language_code`    | `str`                           | ISO 639-1 code (e.g. `"en"`).                                        |
| `is_generated`     | `bool`                          | `True` for auto-generated (ASR) tracks.                              |
| `text`             | `str` *(property)*              | All snippets joined with spaces — useful for full-text search.       |
| `to_raw_data()`    | `list[dict]`                    | Returns snippets as a list of `{"text", "start", "duration"}` dicts. |

`Transcript` also supports `len()`, iteration, indexing, and slicing directly over its snippets.

## `TranscriptSnippet` fields

Each element of `transcript.snippets` is a frozen dataclass:

| Field      | Type    | Description                                                |
| ---------- | ------- | ---------------------------------------------------------- |
| `text`     | `str`   | The caption line text.                                     |
| `start`    | `float` | Wall-clock start time in seconds.                          |
| `duration` | `float` | How long the line is shown (may overlap the next snippet). |

## Iterating snippets

The snippet below is taken from `examples/09_transcript.py`:

```python
from ytscrape import YouTube


def main() -> None:
    with YouTube() as yt:
        video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # List every available caption track first.
        print("Available tracks:")
        print(yt.transcripts(video))
        print()

        # Prefer Ukrainian, fall back to English (manual captions beat ASR).
        transcript = yt.transcript(video, languages=["uk", "en"])
        print(
            f"Fetched: {transcript.language} ({transcript.language_code}), "
            f"generated={transcript.is_generated}, lines={len(transcript)}"
        )
        print()
        for snippet in transcript[:8]:
            print(f"[{snippet.start:6.1f}s] {snippet.text}")
        print("...")
        print(transcript.text[:240], "…")


if __name__ == "__main__":
    main()
```

## Listing available tracks

Use `yt.transcripts()` to inspect what caption tracks exist for a video without downloading any of them. It returns a `TranscriptList`:

```python
with YouTube() as yt:
    tracks = yt.transcripts("dQw4w9WgXcQ")
    for track in tracks:
        print(track.language_code, track.language, track.is_generated)
```

### `TranscriptList` methods

| Method                                             | Description                                                                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `find_transcript(language_codes)`                  | Returns the best matching `TranscriptTrack` — manual tracks preferred over generated, in the given language order. |
| `find_generated_transcript(language_codes)`        | Returns only auto-generated (ASR) tracks.                                                                          |
| `find_manually_created_transcript(language_codes)` | Returns only manually created tracks.                                                                              |

All three raise `NoTranscriptFound` when no match exists.

### `TranscriptTrack` attributes and properties

| Attribute / property    | Type                            | Description                                                             |
| ----------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| `video_id`              | `str`                           | The video this track belongs to.                                        |
| `language`              | `str`                           | Human-readable language name.                                           |
| `language_code`         | `str`                           | ISO 639-1 code.                                                         |
| `is_generated`          | `bool`                          | `True` for auto-generated (ASR) tracks.                                 |
| `is_translatable`       | `bool` *(property)*             | `True` if YouTube can translate this track server-side.                 |
| `translation_languages` | `tuple[dict, ...]` *(property)* | Available translation targets as `{"language", "language_code"}` dicts. |

Call `.fetch()` on a `TranscriptTrack` to download its snippets and get back a `Transcript`.

## Server-side translation

When `is_translatable` is `True`, YouTube can translate the track into another language on the fly. Use `TranscriptTrack.translate(language_code)` to get a translated `TranscriptTrack`, then call `.fetch()` on the result:

```python
with YouTube() as yt:
    tracks = yt.transcripts("dQw4w9WgXcQ")
    track = tracks.find_transcript(["en"])
    if track.is_translatable:
        translated = track.translate("fr")
        french_transcript = translated.fetch()
        print(french_transcript.text[:200])
```

`translate()` raises `NoTranscriptFound` if the requested target language is not in the track's translation list.

## Preserving HTML formatting

Auto-generated transcripts sometimes include inline HTML tags (`<i>`, `<b>`, etc.). By default they are stripped. Pass `preserve_formatting=True` to keep them:

```python
transcript = yt.transcript(video_id, languages=["en"], preserve_formatting=True)
```

## Exceptions

| Exception             | Raised when                                                                                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TranscriptsDisabled` | The video has no caption tracks at all, or captions are disabled. Carries a `.video_id` attribute.                                                                      |
| `NoTranscriptFound`   | None of the requested language codes match any available track. Carries `.requested` (tuple of requested codes) and `.available` (tuple of available codes) attributes. |

```python
from ytscrape import YouTube, TranscriptsDisabled, NoTranscriptFound

with YouTube() as yt:
    try:
        transcript = yt.transcript("dQw4w9WgXcQ", languages=["zh"])
    except TranscriptsDisabled as exc:
        print(f"No captions for video: {exc.video_id}")
    except NoTranscriptFound as exc:
        print(f"Requested: {exc.requested}")
        print(f"Available: {exc.available}")
```
