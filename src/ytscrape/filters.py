"""Search filters for the YouTube InnerTube search endpoint.

Instead of scattering "magic" ``params`` strings such as ``EgIQAQ==`` across
the code base, they are collected in a single, self-documenting enum.
"""

from __future__ import annotations

from enum import Enum


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
    def from_value(cls, value: "SearchFilter | str") -> "SearchFilter":
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
