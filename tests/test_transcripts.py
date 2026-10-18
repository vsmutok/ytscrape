"""Tests for transcript listing, selection and timedtext parsing."""

from __future__ import annotations

from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from ytscrape import (
    NoTranscriptFound,
    Transcript,
    TranscriptsDisabled,
    YouTube,
)
from ytscrape.transcripts import (
    TranscriptList,
    TranscriptSnippet,
    _parse_timedtext,
    fetch_transcript,
    list_transcripts,
)

_CAPTIONS = {
    "playerCaptionsTracklistRenderer": {
        "captionTracks": [
            {
                "baseUrl": "https://www.youtube.com/api/timedtext?v=vid&lang=de&fmt=srv3",
                "name": {"runs": [{"text": "German"}]},
                "languageCode": "de",
                "isTranslatable": True,
            },
            {
                "baseUrl": "https://www.youtube.com/api/timedtext?v=vid&lang=en",
                "name": {"runs": [{"text": "English (auto-generated)"}]},
                "languageCode": "en",
                "kind": "asr",
                "isTranslatable": True,
            },
        ],
        "translationLanguages": [
            {
                "languageCode": "uk",
                "languageName": {"runs": [{"text": "Ukrainian"}]},
            },
            {
                "languageCode": "fr",
                "languageName": {"runs": [{"text": "French"}]},
            },
        ],
    }
}

# YouTube timedtext embeds HTML entities inside text nodes.
_TIMEDTEXT_XML = (
    '<?xml version="1.0" encoding="utf-8" ?>\n'
    "<transcript>\n"
    '  <text start="0.5" dur="1.5">Hello &amp; welcome</text>\n'
    '  <text start="2.0" dur="2.0">to &lt;b&gt;YouTube&lt;/b&gt;</text>\n'
    '  <text start="4.0" dur="1.0"></text>\n'
    "</transcript>\n"
)


class FakeTranscriptClient:
    def __init__(
        self,
        *,
        player_response: dict[str, Any] | None = None,
        text_by_url: dict[str, str] | None = None,
    ) -> None:
        self.player_calls: list[dict[str, Any]] = []
        self.get_text_calls: list[str] = []
        self._player_response = player_response or {
            "playabilityStatus": {"status": "OK"},
            "captions": _CAPTIONS,
        }
        self._text_by_url = text_by_url or {}

    def player(self, video_id: str, *, client_name: str = "WEB") -> dict[str, Any]:
        self.player_calls.append({"video_id": video_id, "client_name": client_name})
        return self._player_response

    def get_text(self, url: str) -> str:
        self.get_text_calls.append(url)
        if url in self._text_by_url:
            return self._text_by_url[url]
        return _TIMEDTEXT_XML


class TestParseTimedtext:
    def test_basic_snippets_strip_html(self) -> None:
        snippets = _parse_timedtext(_TIMEDTEXT_XML)
        assert len(snippets) == 2
        assert snippets[0] == TranscriptSnippet(
            text="Hello & welcome", start=0.5, duration=1.5
        )
        assert snippets[1].text == "to YouTube"
        assert snippets[1].start == 2.0

    def test_preserve_formatting(self) -> None:
        snippets = _parse_timedtext(_TIMEDTEXT_XML, preserve_formatting=True)
        assert snippets[1].text == "to <b>YouTube</b>"

    def test_invalid_xml_raises(self) -> None:
        from ytscrape import ParseError

        with pytest.raises(ParseError):
            _parse_timedtext("<not-closed")


class TestTranscriptList:
    def test_list_and_find_prefers_manual(self) -> None:
        client = FakeTranscriptClient()
        listing = list_transcripts(client, "vid12345678")  # type: ignore[arg-type]
        assert isinstance(listing, TranscriptList)
        assert len(listing) == 2
        assert client.player_calls[0]["client_name"] == "ANDROID"

        track = listing.find_transcript(["en", "de"])
        assert track.language_code == "en"
        assert track.is_generated is True

        manual = listing.find_manually_created_transcript(["de", "en"])
        assert manual.language_code == "de"
        assert manual.is_generated is False

        generated = listing.find_generated_transcript(["en"])
        assert generated.is_generated is True

    def test_find_missing_raises(self) -> None:
        client = FakeTranscriptClient()
        listing = list_transcripts(client, "vid12345678")  # type: ignore[arg-type]
        with pytest.raises(NoTranscriptFound) as exc:
            listing.find_transcript(["ja", "ko"])
        assert "ja" in str(exc.value)
        assert exc.value.video_id == "vid12345678"

    def test_disabled_captions(self) -> None:
        client = FakeTranscriptClient(
            player_response={"playabilityStatus": {"status": "OK"}}
        )
        with pytest.raises(TranscriptsDisabled):
            list_transcripts(client, "vid12345678")  # type: ignore[arg-type]

    def test_translate_appends_tlang(self) -> None:
        client = FakeTranscriptClient()
        listing = list_transcripts(client, "vid12345678")  # type: ignore[arg-type]
        track = listing.find_manually_created_transcript(["de"])
        translated = track.translate("uk")
        assert translated.language_code == "uk"
        assert "tlang=uk" in translated._url
        assert translated.is_generated is True

    def test_fetch_transcript_shortcut(self) -> None:
        client = FakeTranscriptClient()
        result = fetch_transcript(
            client,  # type: ignore[arg-type]
            "vid12345678",
            languages=["de"],
        )
        assert isinstance(result, Transcript)
        assert result.language_code == "de"
        assert result.video_id == "vid12345678"
        assert len(result) == 2
        assert "Hello" in result.text
        assert result.to_raw_data()[0]["start"] == 0.5
        assert client.get_text_calls
        assert "fmt=srv3" not in client.get_text_calls[0]


class TestYouTubeTranscriptFacade:
    def test_transcript_and_list(self) -> None:
        class FacadeClient(FakeTranscriptClient):
            def __init__(self) -> None:
                super().__init__()
                self.closed = False

            def close(self) -> None:
                self.closed = True

            def search(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
                raise AssertionError("search should not be called")

        client = FacadeClient()
        yt = YouTube(client=client)  # type: ignore[arg-type]
        listing = yt.transcripts("https://youtu.be/dQw4w9WgXcQ")
        assert any(t.language_code == "de" for t in listing)

        result = yt.transcript("dQw4w9WgXcQ", languages=["de", "en"])
        assert result.language_code == "de"
        assert result[0].text.startswith("Hello")


@pytest.fixture
def subtitle_transcript() -> Transcript:
    return Transcript(
        snippets=(
            TranscriptSnippet(text="first line", start=0.0, duration=2.34),
            TranscriptSnippet(text="second line", start=2.34, duration=2.44),
        ),
        video_id="vid12345678",
        language="English",
        language_code="en",
        is_generated=False,
    )


class TestSubtitleExport:
    def test_srt(self, subtitle_transcript: Transcript) -> None:
        assert subtitle_transcript.to_srt() == (
            "1\n00:00:00,000 --> 00:00:02,340\nfirst line\n\n"
            "2\n00:00:02,340 --> 00:00:04,780\nsecond line\n\n"
        )

    def test_vtt(self, subtitle_transcript: Transcript) -> None:
        assert subtitle_transcript.to_vtt() == (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:02.340\nfirst line\n\n"
            "00:00:02.340 --> 00:00:04.780\nsecond line\n\n"
        )

    @pytest.mark.parametrize(
        ("snippets", "expected_srt", "expected_vtt"),
        [
            ((), "", "WEBVTT\n\n"),
            (
                (TranscriptSnippet("", 0, 1), TranscriptSnippet(" \t\n", 1, 1)),
                "",
                "WEBVTT\n\n",
            ),
        ],
    )
    def test_empty_captions(
        self, subtitle_transcript, snippets, expected_srt, expected_vtt
    ):
        transcript = replace(subtitle_transcript, snippets=snippets)
        assert transcript.to_srt() == expected_srt
        assert transcript.to_vtt() == expected_vtt

    @pytest.mark.parametrize(
        ("start", "duration", "expected"),
        [
            (0.0006, 1.0002, "00:00:00,001 --> 00:00:01,001"),
            (59.9996, 0.5004, "00:01:00,000 --> 00:01:00,500"),
            (3599.9996, 1.2344, "01:00:00,000 --> 01:00:01,234"),
            (3599.5, 1, "00:59:59,500 --> 01:00:00,500"),
            (360000, 2, "100:00:00,000 --> 100:00:02,000"),
        ],
    )
    def test_timestamp_rounding(self, subtitle_transcript, start, duration, expected):
        transcript = replace(
            subtitle_transcript, snippets=(TranscriptSnippet("text", start, duration),)
        )
        assert transcript.to_srt() == f"1\n{expected}\ntext\n\n"
        assert (
            transcript.to_vtt() == f"WEBVTT\n\n{expected.replace(',', '.')}\ntext\n\n"
        )

    def test_empty_lines_do_not_split_cues(self, subtitle_transcript):
        transcript = replace(
            subtitle_transcript,
            snippets=(
                TranscriptSnippet("", 0, 1),
                TranscriptSnippet("first\r\n\r\nsecond\rthird", 1, 2),
                TranscriptSnippet(" ", 3, 1),
                TranscriptSnippet("last", 4, 1),
            ),
        )
        assert transcript.to_srt() == (
            "1\n00:00:01,000 --> 00:00:03,000\nfirst\nsecond\nthird\n\n"
            "2\n00:00:04,000 --> 00:00:05,000\nlast\n\n"
        )
        assert transcript.to_vtt() == (
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nfirst\nsecond\nthird\n\n"
            "00:00:04.000 --> 00:00:05.000\nlast\n\n"
        )

    def test_order_and_overlaps_are_preserved(self, subtitle_transcript):
        transcript = replace(
            subtitle_transcript,
            snippets=(
                TranscriptSnippet("first", 1, 4),
                TranscriptSnippet("second", 2, 1),
            ),
        )
        assert transcript.to_srt() == (
            "1\n00:00:01,000 --> 00:00:05,000\nfirst\n\n"
            "2\n00:00:02,000 --> 00:00:03,000\nsecond\n\n"
        )
        assert transcript.snippets[0].duration == 4

    def test_vtt_escapes_plain_text(self, subtitle_transcript):
        transcript = replace(
            subtitle_transcript, snippets=(TranscriptSnippet("A < B & C --> D", 0, 1),)
        )
        assert transcript.to_vtt() == (
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nA &lt; B &amp; C --&gt; D\n\n"
        )

    @pytest.mark.parametrize("method", ["to_srt", "to_vtt"])
    @pytest.mark.parametrize(
        ("start", "duration"),
        [
            (-1, 2),
            (1, -0.5),
            (float("nan"), 1),
            (float("inf"), 1),
            (0, float("nan")),
            (0, float("inf")),
            (0, 0),
            (0, 0.0001),
        ],
    )
    def test_invalid_timings(self, subtitle_transcript, method, start, duration):
        transcript = replace(
            subtitle_transcript, snippets=(TranscriptSnippet("text", start, duration),)
        )
        with pytest.raises(ValueError, match="Subtitle"):
            getattr(transcript, method)()

    @pytest.mark.parametrize("extension", ["srt", "vtt"])
    @pytest.mark.parametrize("as_string", [False, True])
    def test_dump_utf8_path(
        self, subtitle_transcript, tmp_path: Path, extension, as_string
    ):
        transcript = replace(
            subtitle_transcript, snippets=(TranscriptSnippet("Café 日本語", 0, 1),)
        )
        path = tmp_path / f"captions.{extension}"
        result = getattr(transcript, f"dump_{extension}")(
            str(path) if as_string else path
        )
        assert result is None
        assert (
            path.read_text(encoding="utf-8") == getattr(transcript, f"to_{extension}")()
        )
        assert "Café 日本語".encode() in path.read_bytes()

    @pytest.mark.parametrize("extension", ["srt", "vtt"])
    def test_dump_text_stream(self, subtitle_transcript, extension):
        stream = StringIO()
        result = getattr(subtitle_transcript, f"dump_{extension}")(stream)
        assert result is None
        assert stream.getvalue() == getattr(subtitle_transcript, f"to_{extension}")()
        assert not stream.closed
