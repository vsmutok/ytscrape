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
from .models import Channel, Playlist, Video

__all__ = ["SearchResults"]

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
