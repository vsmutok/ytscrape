"""YouTube transcript / caption fetching.

The flow mirrors `youtube-transcript-api`:

1. Call InnerTube ``player`` (ANDROID client) for caption track metadata.
2. Pick a track by language preference (manual captions first, then ASR).
3. Download the timedtext XML from the track ``baseUrl`` and parse snippets.

Public surface is intentionally small and typed so it fits the rest of
:mod:`ytscrape` (models + :class:`~ytscrape.YouTube` facade).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from html import unescape
from itertools import chain
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree

from .exceptions import (
    NoTranscriptFound,
    ParseError,
    TranscriptsDisabled,
    YtScraperError,
)

if TYPE_CHECKING:
    from .client import InnerTubeClient

__all__ = [
    "TranscriptSnippet",
    "Transcript",
    "TranscriptTrack",
    "TranscriptList",
    "fetch_transcript",
    "list_transcripts",
]

_FORMATTING_TAGS = (
    "strong",
    "em",
    "b",
    "i",
    "mark",
    "small",
    "del",
    "ins",
    "sub",
    "sup",
)


@dataclass(frozen=True, slots=True)
class TranscriptSnippet:
    """One timed caption line."""

    text: str
    start: float
    """Wall-clock start time in seconds."""
    duration: float
    """How long the line stays on screen (may overlap the next snippet)."""


@dataclass(frozen=True, slots=True)
class Transcript:
    """A fully fetched transcript for a video."""

    snippets: tuple[TranscriptSnippet, ...]
    video_id: str
    language: str
    language_code: str
    is_generated: bool

    def __iter__(self) -> Iterator[TranscriptSnippet]:
        return iter(self.snippets)

    def __len__(self) -> int:
        return len(self.snippets)

    def __getitem__(
        self, index: int | slice
    ) -> TranscriptSnippet | tuple[TranscriptSnippet, ...]:
        return self.snippets[index]

    @property
    def text(self) -> str:
        """All snippet texts joined with spaces."""
        return " ".join(snippet.text for snippet in self.snippets if snippet.text)

    def to_raw_data(self) -> list[dict[str, Any]]:
        """List of ``{text, start, duration}`` dicts (API-compat helper)."""
        return [asdict(snippet) for snippet in self.snippets]


@dataclass(frozen=True, slots=True)
class _TranslationLanguage:
    language: str
    language_code: str


@dataclass(slots=True)
class TranscriptTrack:
    """Metadata for one available caption track (not yet downloaded)."""

    video_id: str
    language: str
    language_code: str
    is_generated: bool
    _url: str
    _translation_languages: tuple[_TranslationLanguage, ...] = ()
    _client: InnerTubeClient | None = None

    @property
    def is_translatable(self) -> bool:
        return bool(self._translation_languages)

    @property
    def translation_languages(self) -> tuple[dict[str, str], ...]:
        """``({"language": …, "language_code": …}, …)`` for UI / debugging."""
        return tuple(
            {
                "language": item.language,
                "language_code": item.language_code,
            }
            for item in self._translation_languages
        )

    def fetch(self, *, preserve_formatting: bool = False) -> Transcript:
        """Download and parse this track's timedtext XML."""
        if self._client is None:
            raise YtScraperError("TranscriptTrack has no HTTP client bound.")
        if "&exp=xpe" in self._url:
            raise ParseError(
                f"Transcript for {self.video_id!r} requires a PO token "
                "(YouTube bot-check / exp=xpe)."
            )
        raw = self._client.get_text(self._url)
        snippets = _parse_timedtext(raw, preserve_formatting=preserve_formatting)
        return Transcript(
            snippets=tuple(snippets),
            video_id=self.video_id,
            language=self.language,
            language_code=self.language_code,
            is_generated=self.is_generated,
        )

    def translate(self, language_code: str) -> TranscriptTrack:
        """Return a translated track (YouTube server-side translation)."""
        if not self.is_translatable:
            raise ParseError(
                f"Transcript track {self.language_code!r} for "
                f"{self.video_id!r} is not translatable."
            )
        mapping = {
            item.language_code: item.language for item in self._translation_languages
        }
        if language_code not in mapping:
            raise NoTranscriptFound(
                self.video_id,
                (language_code,),
                available=tuple(mapping),
            )
        sep = "&" if "?" in self._url else "?"
        return TranscriptTrack(
            video_id=self.video_id,
            language=mapping[language_code],
            language_code=language_code,
            is_generated=True,
            _url=f"{self._url}{sep}tlang={language_code}",
            _translation_languages=(),
            _client=self._client,
        )

    def __str__(self) -> str:
        tag = " [generated]" if self.is_generated else ""
        tr = " [translatable]" if self.is_translatable else ""
        return f'{self.language_code} ("{self.language}"){tag}{tr}'


class TranscriptList:
    """Available caption tracks for one video."""

    def __init__(
        self,
        video_id: str,
        manually_created: dict[str, TranscriptTrack],
        generated: dict[str, TranscriptTrack],
        translation_languages: tuple[_TranslationLanguage, ...],
    ) -> None:
        self.video_id = video_id
        self._manual = manually_created
        self._generated = generated
        self._translation_languages = translation_languages

    def __iter__(self) -> Iterator[TranscriptTrack]:
        return chain(self._manual.values(), self._generated.values())

    def __len__(self) -> int:
        return len(self._manual) + len(self._generated)

    def __str__(self) -> str:
        def _lines(tracks: Iterable[TranscriptTrack]) -> str:
            items = [f" - {track}" for track in tracks]
            return "\n".join(items) if items else "None"

        translations = [
            f' - {item.language_code} ("{item.language}")'
            for item in self._translation_languages
        ]
        return (
            f"For this video ({self.video_id}) transcripts are available in "
            f"the following languages:\n\n"
            f"(MANUALLY CREATED)\n{_lines(self._manual.values())}\n\n"
            f"(GENERATED)\n{_lines(self._generated.values())}\n\n"
            f"(TRANSLATION LANGUAGES)\n"
            f"{chr(10).join(translations) if translations else 'None'}"
        )

    def find_transcript(self, language_codes: Iterable[str]) -> TranscriptTrack:
        """Prefer manual tracks, then generated, in the given language order."""
        return self._find(language_codes, [self._manual, self._generated])

    def find_generated_transcript(
        self, language_codes: Iterable[str]
    ) -> TranscriptTrack:
        return self._find(language_codes, [self._generated])

    def find_manually_created_transcript(
        self, language_codes: Iterable[str]
    ) -> TranscriptTrack:
        return self._find(language_codes, [self._manual])

    def _find(
        self,
        language_codes: Iterable[str],
        sources: list[dict[str, TranscriptTrack]],
    ) -> TranscriptTrack:
        codes = tuple(language_codes)
        for code in codes:
            for source in sources:
                track = source.get(code)
                if track is not None:
                    return track
        available = tuple(
            track.language_code
            for track in chain(self._manual.values(), self._generated.values())
        )
        raise NoTranscriptFound(self.video_id, codes, available=available)


def list_transcripts(client: InnerTubeClient, video_id: str) -> TranscriptList:
    """Build a :class:`TranscriptList` from the InnerTube player response."""
    data = client.player(video_id, client_name="ANDROID")
    captions = _extract_captions_json(data, video_id)
    return _build_transcript_list(client, video_id, captions)


def fetch_transcript(
    client: InnerTubeClient,
    video_id: str,
    *,
    languages: Iterable[str] = ("en",),
    preserve_formatting: bool = False,
) -> Transcript:
    """Shortcut: list tracks → pick by language priority → fetch XML."""
    return (
        list_transcripts(client, video_id)
        .find_transcript(languages)
        .fetch(preserve_formatting=preserve_formatting)
    )


def _extract_captions_json(data: dict[str, Any], video_id: str) -> dict[str, Any]:
    _assert_playability(data.get("playabilityStatus"), video_id)
    captions = data.get("captions")
    if not isinstance(captions, dict):
        raise TranscriptsDisabled(video_id)
    renderer = captions.get("playerCaptionsTracklistRenderer")
    if not isinstance(renderer, dict) or "captionTracks" not in renderer:
        raise TranscriptsDisabled(video_id)
    return renderer


def _assert_playability(status: Any, video_id: str) -> None:
    if not isinstance(status, dict):
        return
    code = status.get("status")
    if code in (None, "OK"):
        return
    reason = status.get("reason")
    if code == "LOGIN_REQUIRED":
        if reason == "This video may be inappropriate for some users.":
            raise ParseError(f"Video {video_id!r} is age-restricted.")
        if reason and "bot" in str(reason).lower():
            raise ParseError(
                f"YouTube blocked the transcript request for {video_id!r} (bot check)."
            )
    if code == "ERROR" and reason == "This video is unavailable":
        raise ParseError(f"Video {video_id!r} is unavailable.")
    detail = reason or code
    raise ParseError(f"Video {video_id!r} is unplayable: {detail}")


def _build_transcript_list(
    client: InnerTubeClient,
    video_id: str,
    captions: dict[str, Any],
) -> TranscriptList:
    translation_languages = tuple(
        _TranslationLanguage(
            language=_runs_text(item.get("languageName"))
            or item.get("languageCode", ""),
            language_code=str(item.get("languageCode") or ""),
        )
        for item in captions.get("translationLanguages") or []
        if isinstance(item, dict) and item.get("languageCode")
    )

    manual: dict[str, TranscriptTrack] = {}
    generated: dict[str, TranscriptTrack] = {}

    tracks = captions.get("captionTracks") or []
    if not isinstance(tracks, list) or not tracks:
        raise TranscriptsDisabled(video_id)

    for caption in tracks:
        if not isinstance(caption, dict):
            continue
        base_url = caption.get("baseUrl")
        language_code = caption.get("languageCode")
        if not isinstance(base_url, str) or not isinstance(language_code, str):
            continue
        is_generated = caption.get("kind", "") == "asr"
        name = _runs_text(caption.get("name")) or language_code
        url = base_url.replace("&fmt=srv3", "")
        track = TranscriptTrack(
            video_id=video_id,
            language=name,
            language_code=language_code,
            is_generated=is_generated,
            _url=url,
            _translation_languages=(
                translation_languages if caption.get("isTranslatable") else ()
            ),
            _client=client,
        )
        target = generated if is_generated else manual
        target[language_code] = track

    if not manual and not generated:
        raise TranscriptsDisabled(video_id)

    return TranscriptList(video_id, manual, generated, translation_languages)


def _runs_text(node: Any) -> str | None:
    if not isinstance(node, dict):
        return None
    runs = node.get("runs")
    if isinstance(runs, list):
        parts = [
            run.get("text", "")
            for run in runs
            if isinstance(run, dict) and isinstance(run.get("text"), str)
        ]
        text = "".join(parts).strip()
        return text or None
    simple = node.get("simpleText")
    if isinstance(simple, str) and simple.strip():
        return simple.strip()
    return None


def _parse_timedtext(
    raw_data: str,
    *,
    preserve_formatting: bool = False,
) -> list[TranscriptSnippet]:
    html_re = _html_strip_regex(preserve_formatting)
    try:
        root = ElementTree.fromstring(raw_data)
    except ElementTree.ParseError as exc:
        raise ParseError(f"Could not parse transcript XML: {exc}") from exc

    snippets: list[TranscriptSnippet] = []
    for element in root:
        if element.text is None:
            continue
        text = re.sub(html_re, "", unescape(element.text)).strip()
        if not text:
            continue
        try:
            start = float(element.attrib.get("start", "0.0"))
            duration = float(element.attrib.get("dur", "0.0"))
        except (TypeError, ValueError):
            start = 0.0
            duration = 0.0
        snippets.append(TranscriptSnippet(text=text, start=start, duration=duration))
    return snippets


def _html_strip_regex(preserve_formatting: bool) -> re.Pattern[str]:
    if preserve_formatting:
        formats = "|".join(_FORMATTING_TAGS)
        pattern = rf"<\/?(?!\/?({formats})\b).*?\b>"
        return re.compile(pattern, re.IGNORECASE)
    return re.compile(r"<[^>]*>", re.IGNORECASE)
