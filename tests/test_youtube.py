"""Tests for the :class:`YouTube` facade."""

from __future__ import annotations

from typing import Any

import pytest

from ytscrape import ParseError, SearchFilter, VideoDetails, YouTube
from ytscrape.results import SearchResults


class FakeClient:
    """A minimal :class:`InnerTubeClient` stand-in for facade tests."""

    def __init__(self) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.player_calls: list[str] = []
        self.closed = False

    def search(
        self,
        query: str | None = None,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        self.search_calls.append(
            {"query": query, "params": params, "continuation": continuation}
        )
        return {"contents": [{"videoRenderer": {"videoId": "vid1"}}]}

    def player(self, video_id: str) -> dict[str, Any]:
        self.player_calls.append(video_id)
        return {"videoDetails": {"videoId": video_id, "title": "T"}}

    def close(self) -> None:
        self.closed = True


class TestNormalizeVideoId:
    @pytest.mark.parametrize(
        "value",
        [
            "dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "  dQw4w9WgXcQ  ",
        ],
    )
    def test_extracts_id(self, value: str) -> None:
        assert YouTube._normalize_video_id(value) == "dQw4w9WgXcQ"

    def test_watch_url_with_extra_params(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL1"
        assert YouTube._normalize_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_raises_parse_error(self) -> None:
        with pytest.raises(ParseError, match="Could not extract a video id"):
            YouTube._normalize_video_id("https://example.com/")

    def test_too_short_raises(self) -> None:
        with pytest.raises(ParseError):
            YouTube._normalize_video_id("short")


class TestYouTubeSearch:
    def test_search_returns_search_results(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        results = yt.search("python")
        assert isinstance(results, SearchResults)

    def test_search_passes_filter_params(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        yt.search("python", filter=SearchFilter.VIDEOS)
        assert client.search_calls[0]["query"] == "python"
        assert client.search_calls[0]["params"] == "EgIQAQ=="

    def test_search_accepts_string_filter(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        yt.search("python", filter="channels")
        assert client.search_calls[0]["params"] == "EgIQAg=="

    def test_search_all_sends_no_params(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        yt.search("python")
        assert client.search_calls[0]["params"] is None


class TestYouTubeVideo:
    def test_video_returns_details(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        details = yt.video("dQw4w9WgXcQ")
        assert isinstance(details, VideoDetails)
        assert details.video_id == "dQw4w9WgXcQ"
        assert client.player_calls == ["dQw4w9WgXcQ"]

    def test_video_accepts_url(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        yt.video("https://youtu.be/dQw4w9WgXcQ")
        assert client.player_calls == ["dQw4w9WgXcQ"]


class TestYouTubeLifecycle:
    def test_close_closes_client(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        yt.close()
        assert client.closed is True

    def test_context_manager_closes(self) -> None:
        client = FakeClient()
        with YouTube(client=client) as yt:
            assert yt.client is client
        assert client.closed is True
