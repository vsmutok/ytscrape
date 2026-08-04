"""Tests for the lazy, paginated :class:`SearchResults`."""

from __future__ import annotations

from typing import Any

from ytscrape import SearchResults, Video


def _video_page(video_ids: list[str], token: str | None) -> dict[str, Any]:
    """Build a fake search response containing videos and a continuation token."""
    page: dict[str, Any] = {
        "contents": [{"videoRenderer": {"videoId": vid}} for vid in video_ids]
    }
    if token is not None:
        page["continuationCommand"] = {"token": token}
    return page


class FakeClient:
    """A stand-in for :class:`InnerTubeClient` that serves canned pages."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages
        self.calls: list[str | None] = []

    def search(self, *, continuation: str | None = None) -> dict[str, Any]:
        self.calls.append(continuation)
        # Serve pages in order; the first page is handled by SearchResults
        # directly, so continuations start from index 1.
        return self._pages.pop(0)


class TestSearchResults:
    def test_first_page_items(self) -> None:
        first = _video_page(["a", "b"], token=None)
        results = SearchResults(FakeClient([]), first)
        items = list(results)
        assert [v.video_id for v in items] == ["a", "b"]
        assert all(isinstance(v, Video) for v in items)

    def test_has_more_reflects_continuation(self) -> None:
        with_token = SearchResults(FakeClient([]), _video_page(["a"], "T"))
        without_token = SearchResults(FakeClient([]), _video_page(["a"], None))
        assert with_token.has_more is True
        assert without_token.has_more is False

    def test_transparent_pagination(self) -> None:
        first = _video_page(["a"], token="T1")
        client = FakeClient([_video_page(["b", "c"], token=None)])
        results = SearchResults(client, first)
        assert [v.video_id for v in results] == ["a", "b", "c"]
        assert client.calls == ["T1"]

    def test_max_results_caps_iteration(self) -> None:
        first = _video_page(["a", "b", "c"], token=None)
        results = SearchResults(FakeClient([]), first, max_results=2)
        assert [v.video_id for v in results] == ["a", "b"]

    def test_fetch_next_page_returns_new_items(self) -> None:
        first = _video_page(["a"], token="T1")
        client = FakeClient([_video_page(["b"], token=None)])
        results = SearchResults(client, first)
        new_items = results.fetch_next_page()
        assert [v.video_id for v in new_items] == ["b"]
        assert results.has_more is False

    def test_fetch_next_page_when_exhausted_returns_empty(self) -> None:
        first = _video_page(["a"], token=None)
        results = SearchResults(FakeClient([]), first)
        assert results.fetch_next_page() == []

    def test_skips_empty_pages_with_continuation(self) -> None:
        # First page empty but has a token; second page has data.
        first = _video_page([], token="T1")
        client = FakeClient(
            [
                _video_page([], token="T2"),
                _video_page(["x"], token=None),
            ]
        )
        results = SearchResults(client, first)
        assert [v.video_id for v in results] == ["x"]
