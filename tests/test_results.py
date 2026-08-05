"""Tests for the lazy, paginated :class:`SearchResults`."""

from __future__ import annotations

from typing import Any

from ytscrape import CommentThread, SearchResults, Video


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


def _comment_page(
    comment_ids: list[str],
    token: str | None,
    *,
    reply_tokens: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a fake comments ``next`` response with the given ids and token.

    ``reply_tokens`` optionally maps a comment id to the reply-continuation
    token YouTube would nest under that thread's ``commentRepliesRenderer``.
    """
    reply_tokens = reply_tokens or {}
    mutations = [
        {
            "payload": {
                "commentEntityPayload": {
                    "properties": {
                        "commentId": cid,
                        "content": {"content": f"text-{cid}"},
                    },
                    "author": {"displayName": f"author-{cid}"},
                    "toolbar": {},
                }
            }
        }
        for cid in comment_ids
    ]
    items: list[dict[str, Any]] = []
    for cid in comment_ids:
        item: dict[str, Any] = {
            "commentViewModel": {"commentViewModel": {"commentId": cid}}
        }
        if cid in reply_tokens:
            # Wrap the comment in a thread renderer carrying the reply token,
            # mirroring YouTube's ``commentThreadRenderer.replies`` structure.
            item = {
                "commentThreadRenderer": {
                    "comment": item,
                    "replies": {
                        "commentRepliesRenderer": {
                            "contents": [
                                {
                                    "continuationItemRenderer": {
                                        "continuationEndpoint": {
                                            "continuationCommand": {
                                                "token": reply_tokens[cid]
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    },
                }
            }
        items.append(item)
    # YouTube appends the "next page" token as a trailing continuationItemRenderer
    # inside the comment-items list, alongside a sort-menu / per-comment reply
    # token that must NOT be followed for pagination.
    if token is not None:
        items.append(
            {"continuationItemRenderer": {"continuationCommand": {"token": token}}}
        )
    page: dict[str, Any] = {
        "frameworkUpdates": {"entityBatchUpdate": {"mutations": mutations}},
        "onResponseReceivedEndpoints": [
            {"appendContinuationItemsAction": {"continuationItems": items}}
        ],
    }
    return page


class FakeCommentClient:
    """A stand-in for :class:`InnerTubeClient` that serves canned comment pages."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages
        self.calls: list[str | None] = []

    def next(self, *, continuation: str | None = None) -> dict[str, Any]:
        self.calls.append(continuation)
        return self._pages.pop(0)


class TestCommentThread:
    def test_first_page_comments(self) -> None:
        first = _comment_page(["a", "b"], token=None)
        thread = CommentThread(FakeCommentClient([]), first)
        assert [c.comment_id for c in thread] == ["a", "b"]

    def test_has_more_reflects_continuation(self) -> None:
        with_token = CommentThread(FakeCommentClient([]), _comment_page(["a"], "T"))
        without_token = CommentThread(FakeCommentClient([]), _comment_page(["a"], None))
        assert with_token.has_more is True
        assert without_token.has_more is False

    def test_transparent_pagination(self) -> None:
        first = _comment_page(["a"], token="T1")
        client = FakeCommentClient([_comment_page(["b", "c"], token=None)])
        thread = CommentThread(client, first)
        assert [c.comment_id for c in thread] == ["a", "b", "c"]
        assert client.calls == ["T1"]

    def test_max_results_caps_iteration(self) -> None:
        first = _comment_page(["a", "b", "c"], token=None)
        thread = CommentThread(FakeCommentClient([]), first, max_results=2)
        assert [c.comment_id for c in thread] == ["a", "b"]

    def test_fetch_next_page_returns_new_comments(self) -> None:
        first = _comment_page(["a"], token="T1")
        client = FakeCommentClient([_comment_page(["b"], token=None)])
        thread = CommentThread(client, first)
        new_items = thread.fetch_next_page()
        assert [c.comment_id for c in new_items] == ["b"]
        assert thread.has_more is False

    def test_fetch_next_page_when_exhausted_returns_empty(self) -> None:
        first = _comment_page(["a"], token=None)
        thread = CommentThread(FakeCommentClient([]), first)
        assert thread.fetch_next_page() == []

    def test_ignores_sort_and_reply_tokens(self) -> None:
        # A realistic page also carries a top-level sort/reload token and a
        # per-comment reply token. Neither must be used for paging: doing so is
        # exactly what caused the same comments to repeat.
        first = _comment_page(["a"], token="NEXT")
        first["continuationCommand"] = {"token": "SORT-RELOAD"}
        first["frameworkUpdates"]["entityBatchUpdate"]["mutations"][0]["payload"][
            "commentEntityPayload"
        ]["replies"] = {"continuationCommand": {"token": "REPLY-a"}}
        client = FakeCommentClient([_comment_page(["b"], token=None)])
        thread = CommentThread(client, first)
        assert [c.comment_id for c in thread] == ["a", "b"]
        # Only the genuine "next page" token was followed.
        assert client.calls == ["NEXT"]

    def test_deduplicates_repeated_comments_across_pages(self) -> None:
        # Even if YouTube echoes a comment on a later page, it is yielded once.
        first = _comment_page(["a", "b"], token="T1")
        client = FakeCommentClient([_comment_page(["b", "c"], token=None)])
        thread = CommentThread(client, first)
        assert [c.comment_id for c in thread] == ["a", "b", "c"]

    def test_replies_not_collected_by_default(self) -> None:
        # A thread carries a reply token, but without include_replies we neither
        # follow it nor yield any replies.
        first = _comment_page(["a"], token=None, reply_tokens={"a": "R-a"})
        client = FakeCommentClient([])
        thread = CommentThread(client, first)
        assert [c.comment_id for c in thread] == ["a"]
        assert client.calls == []

    def test_include_replies_expands_each_thread(self) -> None:
        # Comment "a" has replies; they are fetched via its reply token and
        # yielded right after "a", flagged as replies. Comment "b" has none.
        first = _comment_page(["a", "b"], token=None, reply_tokens={"a": "R-a"})
        reply_page = _comment_page(["a1", "a2"], token=None)
        client = FakeCommentClient([reply_page])
        thread = CommentThread(client, first, include_replies=True)
        collected = list(thread)
        assert [c.comment_id for c in collected] == ["a", "a1", "a2", "b"]
        assert [c.is_reply for c in collected] == [False, True, True, False]
        assert client.calls == ["R-a"]

    def test_include_replies_pages_through_reply_pages(self) -> None:
        # A thread's replies can span multiple pages; every page is followed.
        first = _comment_page(["a"], token=None, reply_tokens={"a": "R-a"})
        reply_page1 = _comment_page(["a1"], token="R-a-2")
        reply_page2 = _comment_page(["a2"], token=None)
        client = FakeCommentClient([reply_page1, reply_page2])
        thread = CommentThread(client, first, include_replies=True)
        assert [c.comment_id for c in thread] == ["a", "a1", "a2"]
        assert client.calls == ["R-a", "R-a-2"]

    def test_include_replies_respects_max_results(self) -> None:
        # max_results counts replies too, capping the flattened stream.
        first = _comment_page(["a", "b"], token=None, reply_tokens={"a": "R-a"})
        reply_page = _comment_page(["a1", "a2"], token=None)
        client = FakeCommentClient([reply_page])
        thread = CommentThread(client, first, include_replies=True, max_results=2)
        assert [c.comment_id for c in thread] == ["a", "a1"]
