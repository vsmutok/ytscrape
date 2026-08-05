"""Search filters for the YouTube InnerTube search endpoint.

Instead of scattering "magic" ``params`` strings such as ``EgIQAQ==`` across
the code base, they are collected in a single, self-documenting enum.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["SearchFilter", "CommentSort"]


class SearchFilter(str, Enum):
    """Type of results returned by :meth:`ytscrape.YouTube.search`.

    Each member maps to the ``params`` value that the YouTube InnerTube
    ``search`` endpoint expects. ``ALL`` intentionally maps to ``None`` so that
    the ``params`` field is omitted from the request payload.

    YouTube changes these values from time to time; if a filter stops working,
    capture a fresh value from the browser DevTools (Network tab) and update it
    here.
    """

    ALL = "all"
    VIDEOS = "videos"
    CHANNELS = "channels"
    PLAYLISTS = "playlists"
    SHORTS = "shorts"
    MOVIES = "movies"

    @property
    def params(self) -> str | None:
        """Return the ``params`` value sent to the InnerTube endpoint."""
        return _FILTER_PARAMS[self]

    @classmethod
    def from_value(cls, value: SearchFilter | str) -> SearchFilter:
        """Coerce a string or :class:`SearchFilter` into a :class:`SearchFilter`."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value.lower())
        except ValueError as exc:  # pragma: no cover - defensive branch
            valid = ", ".join(member.value for member in cls)
            raise ValueError(
                f"Unknown search filter {value!r}. Valid filters: {valid}."
            ) from exc


# ``params`` values captured from the YouTube web UI (Filters -> Type).
# YouTube tweaks these from time to time; if a filter stops working, grab a
# fresh value from DevTools (Network tab, ``youtubei/v1/search`` payload).
_FILTER_PARAMS: dict[SearchFilter, str | None] = {
    SearchFilter.ALL: None,
    SearchFilter.VIDEOS: "EgIQAQ==",
    SearchFilter.CHANNELS: "EgIQAg==",
    SearchFilter.PLAYLISTS: "EgIQAw==",
    SearchFilter.SHORTS: "EgIQCQ==",
    SearchFilter.MOVIES: "EgIQBA==",
}


class CommentSort(str, Enum):
    """Order in which :meth:`ytscrape.YouTube.comments` collects comments.

    ``TOP`` mirrors YouTube's default "Top comments" view, which surfaces the
    most relevant comments but **hides some of them** (less relevant ones and
    "potential spam"). ``NEWEST`` maps to the "Newest first" view, which lists
    *every* comment in reverse-chronological order and therefore is the option
    to use when you want to collect them all.

    Unlike :class:`SearchFilter`, the continuation token for each sort order is
    not a fixed constant: YouTube embeds a fresh, per-video token in the sort
    menu of the first comments page. This enum stores the menu title that
    identifies each option so the token can be looked up at runtime.
    """

    TOP = "top"
    NEWEST = "newest"

    @property
    def menu_title(self) -> str:
        """The ``sortFilterSubMenuRenderer`` item title identifying this order."""
        return _SORT_MENU_TITLES[self]

    @property
    def menu_index(self) -> int:
        """The item's position in the sort menu (``0`` = Top, ``1`` = Newest)."""
        return _SORT_MENU_INDEX[self]

    @classmethod
    def from_value(cls, value: CommentSort | str) -> CommentSort:
        """Coerce a string or :class:`CommentSort` into a :class:`CommentSort`."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value.lower())
        except ValueError as exc:
            valid = ", ".join(member.value for member in cls)
            raise ValueError(
                f"Unknown comment sort {value!r}. Valid values: {valid}."
            ) from exc


# The sort menu (``sortFilterSubMenuRenderer.subMenuItems``) is localised, so we
# match on both the (English) title and its position for resilience.
_SORT_MENU_TITLES: dict[CommentSort, str] = {
    CommentSort.TOP: "Top comments",
    CommentSort.NEWEST: "Newest first",
}

_SORT_MENU_INDEX: dict[CommentSort, int] = {
    CommentSort.TOP: 0,
    CommentSort.NEWEST: 1,
}
