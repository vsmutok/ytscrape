"""The public facade of the package: the :class:`YouTube` class."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from .client import InnerTubeClient
from .exceptions import ParseError
from .filters import SearchFilter
from .locale import Country, Language, Locale
from .models import VideoDetails
from .results import SearchResults

__all__ = ["YouTube"]

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTube:
    """High level entry point for scraping YouTube.

    This class is a thin *facade* over :class:`InnerTubeClient`,
    :class:`SearchResults` and the data models. Typical usage::

        from ytscrape import YouTube, SearchFilter

        yt = YouTube()
        for video in yt.search("python", filter=SearchFilter.VIDEOS):
            print(video.title, video.url)

        details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print(details.title, details.views)

    Args:
        client: A pre-built :class:`InnerTubeClient`. When omitted, one is
            created from the keyword arguments below, which allows injecting a
            custom client (e.g. for testing) while keeping the common case
            simple.
        locale: The :class:`~ytscrape.locale.Locale` (language + country) used
            to localise responses when building a default client. When omitted
            it is built from ``language`` and ``region``.
        language: ``hl`` value used for requests when building a default
            client. Accepts a :class:`~ytscrape.locale.Language` or a raw
            ISO 639-1 code. Ignored when ``locale`` is provided.
        region: ``gl`` value used for requests when building a default client.
            Accepts a :class:`~ytscrape.locale.Country` or a raw ISO 3166-1
            alpha-2 code. Ignored when ``locale`` is provided.
        timeout: Per-request timeout (seconds) when building a default client.
    """

    def __init__(
        self,
        *,
        client: InnerTubeClient | None = None,
        locale: Locale | None = None,
        language: Language | str = "en",
        region: Country | str = "US",
        timeout: float = 30.0,
    ) -> None:
        self._client = client or InnerTubeClient(
            locale=locale,
            language=language,
            region=region,
            timeout=timeout,
        )

    @property
    def client(self) -> InnerTubeClient:
        """The underlying :class:`InnerTubeClient`."""
        return self._client

    @property
    def locale(self) -> Locale:
        """The :class:`~ytscrape.locale.Locale` used for requests."""
        return self._client.locale

    def search(
        self,
        query: str,
        *,
        filter: SearchFilter | str = SearchFilter.ALL,
        max_results: int | None = None,
    ) -> SearchResults:
        """Search YouTube and return a paginated :class:`SearchResults`.

        Args:
            query: The search query.
            filter: Which kind of results to return (``all``, ``videos``,
                ``channels`` or ``playlists``). Accepts a :class:`SearchFilter`
                or its string value.
            max_results: Optional cap on the total number of items yielded when
                iterating. ``None`` means iterate until YouTube runs out of
                pages.
        """
        search_filter = SearchFilter.from_value(filter)
        first_page = self._client.search(query, params=search_filter.params)
        return SearchResults(
            self._client, first_page, max_results=max_results
        )

    def video(self, video: str) -> VideoDetails:
        """Fetch detailed metadata for a single video.

        Args:
            video: A video id or any YouTube URL that contains one
                (``watch?v=``, ``youtu.be/``, ``/shorts/`` and ``/embed/`` are
                all supported).
        """
        video_id = self._normalize_video_id(video)
        response = self._client.player(video_id)
        return VideoDetails.from_player_response(response)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._client.close()

    def __enter__(self) -> "YouTube":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @staticmethod
    def _normalize_video_id(value: str) -> str:
        """Extract an 11-character video id from an id or URL."""
        value = value.strip()
        if _VIDEO_ID_RE.match(value):
            return value

        parsed = urlparse(value)
        if parsed.query:
            query_id = parse_qs(parsed.query).get("v", [None])[0]
            if query_id and _VIDEO_ID_RE.match(query_id):
                return query_id

        # youtu.be/<id>, /shorts/<id>, /embed/<id>, /v/<id>
        segments = [seg for seg in parsed.path.split("/") if seg]
        for segment in reversed(segments):
            if _VIDEO_ID_RE.match(segment):
                return segment

        raise ParseError(f"Could not extract a video id from {value!r}.")
