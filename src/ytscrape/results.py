"""Lazy, paginated search results.

:class:`SearchResults` is the object returned by
:meth:`ytscrape.YouTube.search`. It hides YouTube's continuation tokens behind
a plain iterator: iterating over it transparently fetches new pages until the
results (or an optional ``max_results`` limit) are exhausted.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from . import parsing
from .models import Channel, Comment, Playlist, Video

__all__ = ["SearchResults", "CommentThread"]

SearchItem = Video | Channel | Playlist


class SearchResults:
    """Iterable view over the results of a search, with transparent paging.

    The object is a lazy iterable: nothing is fetched beyond the first page
    until you actually consume items past it. Use it directly in a ``for`` loop::

        for item in youtube.search("python"):
            print(item.title)

    or page manually with :meth:`fetch_next_page`.
    """

    def __init__(
        self,
        client: Any,
        first_page: dict[str, Any],
        *,
        max_results: int | None = None,
    ) -> None:
        self._client = client
        self._continuation: str | None = parsing.find_continuation(first_page)
        self._max_results = max_results
        self._buffer: list[SearchItem] = self._extract_items(first_page)

    @staticmethod
    def _extract_items(page: dict[str, Any]) -> list[SearchItem]:
        items: list[SearchItem] = []
        for key, renderer in parsing.iter_renderers(page):
            item = parsing.parse_item(key, renderer)
            if item is not None:
                items.append(item)
        return items

    @property
    def has_more(self) -> bool:
        """Whether another page can be fetched from YouTube."""
        return self._continuation is not None

    def fetch_next_page(self) -> list[SearchItem]:
        """Fetch and buffer the next page, returning the newly added items.

        Returns an empty list when there are no more pages.
        """
        if self._continuation is None:
            return []
        page = self._client.search(continuation=self._continuation)
        self._continuation = parsing.find_continuation(page)
        new_items = self._extract_items(page)
        self._buffer.extend(new_items)
        return new_items

    def __iter__(self) -> Iterator[SearchItem]:
        index = 0
        while True:
            if self._max_results is not None and index >= self._max_results:
                return
            if index < len(self._buffer):
                yield self._buffer[index]
                index += 1
                continue
            # The buffer is exhausted: keep fetching pages until one adds new
            # items or YouTube runs out of pages. A page can legitimately be
            # empty yet still carry a continuation token (e.g. the first page
            # of a filtered search), so we must not stop on the first empty
            # page while more pages remain.
            while not self._buffer[index:] and self.has_more:
                self.fetch_next_page()
            if index >= len(self._buffer):
                return


class CommentThread:
    """Iterable view over the comments of a video, with transparent paging.

    Returned by :meth:`ytscrape.YouTube.comments`. Like :class:`SearchResults`
    it is a lazy iterable: iterating over it transparently fetches comment
    pages from YouTube's ``next`` endpoint until the comments (or an optional
    ``max_results`` limit) are exhausted::

        for comment in youtube.comments("https://youtu.be/dQw4w9WgXcQ"):
            print(comment.author, comment.text)

    By default only top-level comments are collected. Pass
    ``include_replies=True`` to also expand every thread's replies (marked with
    :attr:`~ytscrape.models.Comment.is_reply`), which are yielded right after
    the top-level comment they belong to.
    """

    def __init__(
        self,
        client: Any,
        first_page: dict[str, Any],
        *,
        max_results: int | None = None,
        include_replies: bool = False,
    ) -> None:
        self._client = client
        self._max_results = max_results
        self._include_replies = include_replies
        # Track comment ids we have already yielded so a repeated page (or a
        # comment echoed across pages) can never surface as a duplicate.
        self._seen_ids: set[str] = set()
        self._continuation: str | None = parsing.find_next_comments_continuation(
            first_page
        )
        self._buffer: list[Comment] = self._collect(first_page)

    def _dedupe(self, comments: list[Comment]) -> list[Comment]:
        """Drop comments whose id was already seen on an earlier page."""
        unique: list[Comment] = []
        for comment in comments:
            if comment.comment_id and comment.comment_id in self._seen_ids:
                continue
            if comment.comment_id:
                self._seen_ids.add(comment.comment_id)
            unique.append(comment)
        return unique

    def _collect(self, page: dict[str, Any]) -> list[Comment]:
        """Parse a top-level page and, if requested, expand every thread's replies.

        Each thread's replies are inserted right after the comment they belong
        to, so iterating the thread yields every comment immediately followed by
        its replies while preserving YouTube's ordering.
        """
        top_level = self._dedupe(parsing.parse_comments_page(page))
        if not self._include_replies:
            return top_level

        # Map each parent comment id to the replies fetched for its thread.
        replies_by_parent: dict[str, list[Comment]] = {}
        orphan_replies: list[Comment] = []
        for parent_id, token in parsing.find_reply_continuations(page):
            replies = self._fetch_replies(token)
            if parent_id:
                replies_by_parent.setdefault(parent_id, []).extend(replies)
            else:
                orphan_replies.extend(replies)

        collected: list[Comment] = []
        for comment in top_level:
            collected.append(comment)
            collected.extend(replies_by_parent.pop(comment.comment_id, []))
        # Any replies whose parent was not on this page still get surfaced.
        for leftover in replies_by_parent.values():
            collected.extend(leftover)
        collected.extend(orphan_replies)
        return collected

    def _fetch_replies(self, token: str | None) -> list[Comment]:
        """Page through every reply of a single thread starting at ``token``."""
        replies: list[Comment] = []
        while token is not None:
            page = self._client.next(continuation=token)
            replies.extend(
                self._dedupe(parsing.parse_comments_page(page, force_reply=True))
            )
            token = parsing.find_next_comments_continuation(page)
        return replies

    @property
    def has_more(self) -> bool:
        """Whether another page of comments can be fetched from YouTube."""
        return self._continuation is not None

    def fetch_next_page(self) -> list[Comment]:
        """Fetch and buffer the next page, returning the newly added comments.

        Returns an empty list when there are no more pages. When replies are
        included, the returned list also contains the replies expanded for the
        threads on the fetched page.
        """
        if self._continuation is None:
            return []
        page = self._client.next(continuation=self._continuation)
        self._continuation = parsing.find_next_comments_continuation(page)
        new_items = self._collect(page)
        self._buffer.extend(new_items)
        return new_items

    def __iter__(self) -> Iterator[Comment]:
        index = 0
        while True:
            if self._max_results is not None and index >= self._max_results:
                return
            if index < len(self._buffer):
                yield self._buffer[index]
                index += 1
                continue
            # The buffer is exhausted: keep fetching pages until one adds new
            # comments or YouTube runs out of pages. A page can legitimately be
            # empty yet still carry a continuation token, so we must not stop
            # on the first empty page while more pages remain.
            while not self._buffer[index:] and self.has_more:
                self.fetch_next_page()
            if index >= len(self._buffer):
                return
