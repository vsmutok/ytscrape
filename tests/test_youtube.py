"""Tests for the :class:`YouTube` facade."""

from __future__ import annotations

from typing import Any

import pytest

from ytscrape import (
    CommentSort,
    ParseError,
    SearchFilter,
    VideoDetails,
    YouTube,
)
from ytscrape.results import CommentThread, SearchResults


class FakeClient:
    """A minimal :class:`InnerTubeClient` stand-in for facade tests."""

    def __init__(self, *, comments_token: str | None = "CT") -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.player_calls: list[str] = []
        self.next_calls: list[dict[str, Any]] = []
        self._comments_token = comments_token
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

    def next(
        self,
        video_id: str | None = None,
        *,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        self.next_calls.append({"video_id": video_id, "continuation": continuation})
        if continuation is None:
            # Watch page carrying the comments-section token.
            section: dict[str, Any] = {
                "itemSectionRenderer": {
                    "sectionIdentifier": "comment-item-section",
                }
            }
            if self._comments_token is not None:
                section["itemSectionRenderer"]["continuationCommand"] = {
                    "token": self._comments_token
                }
            return {"contents": [section]}
        # A distinct comment id per sort order lets tests tell them apart.
        comment_id = "n1" if continuation == "NEWEST" else "c1"
        return {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {
                            "payload": {
                                "commentEntityPayload": {
                                    "properties": {
                                        "commentId": comment_id,
                                        "content": {"content": "hi"},
                                    },
                                    "author": {"displayName": "A"},
                                    "toolbar": {},
                                }
                            }
                        }
                    ]
                }
            },
            # The first comments page also carries the sort menu; each item
            # embeds its own continuation token (Top is selected by default).
            "sortFilterSubMenuRenderer": {
                "subMenuItems": [
                    {"title": "Top comments", "selected": True},
                    {
                        "title": "Newest first",
                        "selected": False,
                        "serviceEndpoint": {"continuationCommand": {"token": "NEWEST"}},
                    },
                ]
            },
            "contents": [
                {"commentViewModel": {"commentViewModel": {"commentId": comment_id}}}
            ],
        }

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


class TestYouTubeComments:
    def test_comments_returns_comment_thread(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        thread = yt.comments("dQw4w9WgXcQ")
        assert isinstance(thread, CommentThread)

    def test_comments_normalizes_url_and_uses_token(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        comments = list(yt.comments("https://youtu.be/dQw4w9WgXcQ"))
        # First next call loads the watch page by id, the second uses the token.
        assert client.next_calls[0] == {
            "video_id": "dQw4w9WgXcQ",
            "continuation": None,
        }
        assert client.next_calls[1] == {"video_id": None, "continuation": "CT"}
        assert [c.comment_id for c in comments] == ["c1"]

    def test_comments_respects_max_results(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        thread = yt.comments("dQw4w9WgXcQ", max_results=0)
        assert list(thread) == []

    def test_comments_defaults_to_no_replies(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        thread = yt.comments("dQw4w9WgXcQ")
        assert thread._include_replies is False

    def test_comments_forwards_include_replies(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        thread = yt.comments("dQw4w9WgXcQ", include_replies=True)
        assert thread._include_replies is True

    def test_comments_without_section_raises(self) -> None:
        client = FakeClient(comments_token=None)
        yt = YouTube(client=client)
        with pytest.raises(ParseError, match="comments section"):
            yt.comments("dQw4w9WgXcQ")

    def test_comments_default_sort_stays_on_top(self) -> None:
        # The default order is "top", which is already selected, so no extra
        # ``next`` call is made to switch order and the top comment surfaces.
        client = FakeClient()
        yt = YouTube(client=client)
        comments = list(yt.comments("dQw4w9WgXcQ"))
        assert [c.comment_id for c in comments] == ["c1"]
        assert [call["continuation"] for call in client.next_calls] == [None, "CT"]

    def test_comments_newest_follows_sort_token(self) -> None:
        # Asking for "newest" follows the sort menu's own continuation token,
        # re-opening the feed in that order (an extra ``next`` call).
        client = FakeClient()
        yt = YouTube(client=client)
        comments = list(yt.comments("dQw4w9WgXcQ", sort=CommentSort.NEWEST))
        assert [c.comment_id for c in comments] == ["n1"]
        assert client.next_calls[-1] == {"video_id": None, "continuation": "NEWEST"}

    def test_comments_accepts_string_sort(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        comments = list(yt.comments("dQw4w9WgXcQ", sort="newest"))
        assert [c.comment_id for c in comments] == ["n1"]

    def test_comments_invalid_sort_raises(self) -> None:
        client = FakeClient()
        yt = YouTube(client=client)
        with pytest.raises(ValueError, match="Unknown comment sort"):
            yt.comments("dQw4w9WgXcQ", sort="oldest")


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
