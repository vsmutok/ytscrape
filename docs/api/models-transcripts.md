# Transcript models: TranscriptSnippet and TranscriptTrack

> Reference for TranscriptSnippet, Transcript, TranscriptTrack, and TranscriptList — the four models powering ytscrape's caption and subtitle support.

ytscrape's transcript system mirrors the familiar three-step flow: list available tracks for a video, find the one you want, then fetch and parse it. Four models are involved: `TranscriptSnippet` (a single timed caption line), `Transcript` (a fully fetched and parsed transcript), `TranscriptTrack` (metadata for one available but not-yet-downloaded caption track), and `TranscriptList` (the collection of all tracks for a video).

***

## TranscriptSnippet

A single timed caption line within a fetched transcript. All fields are required and are never `None`.

**`text`** (`str`)

:   The caption text for this line, with HTML formatting tags stripped (unless `preserve_formatting=True` was passed to `TranscriptTrack.fetch()`).


**`start`** (`float`)

:   Wall-clock start time in seconds (e.g. `42.56`). Parsed from the `start` attribute of the timedtext XML element.


**`duration`** (`float`)

:   How long the line stays on screen in seconds (e.g. `3.12`). Note that adjacent snippets may overlap: `start + duration` of one snippet can exceed the `start` of the next.


***

## Transcript

A fully fetched and parsed transcript for a single video. Returned by `TranscriptTrack.fetch()`.

**`snippets`** (`tuple[TranscriptSnippet, ...]`)

:   Ordered tuple of all caption snippets, from first to last.


**`video_id`** (`str`)

:   The YouTube video ID this transcript belongs to.


**`language`** (`str`)

:   Full language name (e.g. `"English"`, `"Français"`).


**`language_code`** (`str`)

:   ISO 639-1 language code (e.g. `"en"`, `"fr"`).


**`is_generated`** (`bool`)

:   `True` when this is an auto-generated (ASR) caption track, `False` for manually created captions.


### Properties

**`text`** (`str`)

:   **Property.** All snippet texts joined with a single space. Useful when you want the full transcript as a plain string for search, summarisation, or storage.


### Sequence interface

`Transcript` is fully iterable, indexable, and supports `len()`:

* **Iterate** — `for snippet in transcript:` yields each `TranscriptSnippet` in order.
* **Index** — `transcript[0]` returns the first `TranscriptSnippet`; `transcript[-1]` the last; `transcript[2:5]` returns a tuple of snippets.
* **Length** — `len(transcript)` returns the total number of snippets.

### Methods

**`to_raw_data()`** (`list[dict[str, Any]]`)

:   Returns a list of plain `{"text": ..., "start": ..., "duration": ...}` dictionaries, one per snippet. Useful for serialisation or passing data to code that does not import ytscrape types.

      ```python
      import json
      print(json.dumps(transcript.to_raw_data()[:3], indent=2))
      ```


***

## TranscriptTrack

Metadata for one available caption track. Instances are collected inside a `TranscriptList` and are not downloaded until you call `fetch()`.

**`video_id`** (`str`)

:   The YouTube video ID this track belongs to.


**`language`** (`str`)

:   Full language name (e.g. `"English (auto-generated)"`).


**`language_code`** (`str`)

:   ISO 639-1 language code (e.g. `"en"`).


**`is_generated`** (`bool`)

:   `True` for auto-generated (ASR) tracks, `False` for manually created tracks.


### Properties

**`is_translatable`** (`bool`)

:   **Property.** `True` when YouTube can translate this track into other languages server-side. Use `translate()` to obtain a translated `TranscriptTrack`.


**`translation_languages`** (`tuple[dict[str, str], ...]`)

:   **Property.** A tuple of `{"language": …, "language_code": …}` dicts listing every language this track can be translated into. Empty tuple when `is_translatable` is `False`.


### Methods

**`fetch(*, preserve_formatting=False)`** (`Transcript`)

:   Downloads the timedtext XML for this track, parses it into `TranscriptSnippet` instances, and returns a `Transcript` object.

      * `preserve_formatting` — when `True`, semantic HTML tags (`<b>`, `<i>`, `<em>`, `<strong>`, etc.) are preserved in snippet text instead of being stripped. All other tags are still removed.

      Raises `ParseError` if the transcript XML cannot be parsed or if YouTube requires a PO token for this track.


**`translate(language_code)`** (`TranscriptTrack`)

:   Returns a new `TranscriptTrack` that, when fetched, will request a server-side translation into the given language. The returned track has `is_generated=True`.

      Raises `ParseError` if this track is not translatable, or `NoTranscriptFound` if `language_code` is not in `translation_languages`.

      ```python
      spanish_track = track.translate("es")
      spanish_transcript = spanish_track.fetch()
      ```


### String representation

`str(track)` returns a compact human-readable summary, for example:

```
en ("English") [generated] [translatable]
fr ("Français")
```

***

## TranscriptList

The collection of all available caption tracks for a video. Returned by `YouTube.transcripts()` (which internally calls `list_transcripts`).

### Attributes

**`video_id`** (`str`)

:   The YouTube video ID whose tracks this list represents. Set when the list is constructed and never changes.


### Methods

**`find_transcript(language_codes)`** (`TranscriptTrack`)

:   Finds the best available track for the given language priority list. Manually created tracks are preferred over generated (ASR) tracks. The first matching language code wins.

      ```python
      track = transcript_list.find_transcript(["en", "fr", "de"])
      ```

      Raises `NoTranscriptFound` if none of the requested languages are available.


**`find_generated_transcript(language_codes)`** (`TranscriptTrack`)

:   Like `find_transcript()`, but considers only auto-generated (ASR) tracks. Raises `NoTranscriptFound` if no generated track matches.


**`find_manually_created_transcript(language_codes)`** (`TranscriptTrack`)

:   Like `find_transcript()`, but considers only manually created tracks. Raises `NoTranscriptFound` if no manual track matches.


### Iteration and length

`TranscriptList` is iterable and supports `len()`. Iterating over it yields every `TranscriptTrack` — manually created tracks first, then generated tracks. `len(transcript_list)` returns the total number of tracks across both groups.

```python
for track in transcript_list:
    print(track)

print(len(transcript_list))  # total number of available tracks
```

### String representation

`str(transcript_list)` prints a human-readable summary of all available tracks grouped by type:

```
For this video (dQw4w9WgXcQ) transcripts are available in the following languages:

(MANUALLY CREATED)
 - en ("English") [translatable]

(GENERATED)
 - en ("English (auto-generated)") [generated] [translatable]

(TRANSLATION LANGUAGES)
 - fr ("French")
 - de ("German")
 ...
```

***

## Full flow example

```python
from ytscrape import YouTube

yt = YouTube()

# Step 1 — list all available tracks for a video
transcript_list = yt.transcripts("dQw4w9WgXcQ")
print(transcript_list)  # human-readable summary of all tracks

# Step 2 — find the best English track (manual preferred over generated)
track = transcript_list.find_transcript(["en"])
print(track)           # en ("English") [translatable]

# Step 3 — fetch the transcript
transcript = track.fetch()

print(f"Language : {transcript.language} ({transcript.language_code})")
print(f"Generated: {transcript.is_generated}")
print(f"Snippets : {len(transcript)}")
print(f"Duration : {transcript[-1].start + transcript[-1].duration:.1f}s")

# Full text (useful for summarisation or search)
print(transcript.text[:200])

# Iterate individual snippets
for snippet in transcript:
    mins, secs = divmod(snippet.start, 60)
    print(f"[{int(mins):02d}:{secs:05.2f}] {snippet.text}")

# Serialise to plain dicts
import json
print(json.dumps(transcript.to_raw_data()[:2], indent=2))

# Translate to Spanish (if translatable)
if track.is_translatable:
    es_transcript = track.translate("es").fetch()
    print(es_transcript.text[:200])
```

!!! tip

    `find_transcript()` is the recommended entry point for most use cases. It prefers manually created captions (which tend to be more accurate) but falls back to auto-generated ones automatically, so you rarely need to call `find_manually_created_transcript()` or `find_generated_transcript()` directly.


!!! warning

    Some tracks require a PO token (indicated by `&exp=xpe` in their internal URL). Calling `fetch()` on such a track raises a `ParseError` with an explanatory message. This is a YouTube bot-check restriction and cannot be circumvented without a valid token.
