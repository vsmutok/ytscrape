"""Low level HTTP client for the YouTube InnerTube API.

:class:`InnerTubeClient` owns the :class:`requests.Session`, lazily fetches the
:class:`~ytscrape.context.InnerTubeContext` and exposes thin wrappers around
the ``search`` and ``player`` endpoints. It knows nothing about models or
pagination; that logic lives in the higher level :class:`ytscrape.YouTube`
facade.
"""

from __future__ import annotations

from typing import Any

import requests

from .context import ContextExtractor, InnerTubeContext
from .exceptions import RequestError
from .locale import Country, Language, Locale

__all__ = ["InnerTubeClient"]

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

_HOME_URL = "https://www.youtube.com"
_BASE_API_URL = "https://www.youtube.com/youtubei/v1"


class InnerTubeClient:
    """Perform authenticated requests against the InnerTube API.

    Args:
        session: Optional pre-configured :class:`requests.Session`. A new one is
            created when omitted, which makes the client easy to unit test by
            injecting a fake session.
        user_agent: ``User-Agent`` header sent with every request.
        timeout: Per-request timeout in seconds.
        locale: The :class:`~ytscrape.locale.Locale` (language + country)
            used to localise responses. When omitted it is built from
            ``language`` and ``region``.
        language: ``hl`` value sent in the request context. A
            :class:`~ytscrape.locale.Language` or a raw ISO 639-1 code.
            Ignored when ``locale`` is provided.
        region: ``gl`` value sent in the request context. A
            :class:`~ytscrape.locale.Country` or a raw ISO 3166-1 alpha-2
            code. Ignored when ``locale`` is provided.
        extractor: Strategy object used to parse the InnerTube context out of
            the YouTube home page.
    """

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout: float = 30.0,
        locale: Locale | None = None,
        language: Language | str = "en",
        region: Country | str = "US",
        extractor: ContextExtractor | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._user_agent = user_agent
        self._timeout = timeout
        self._locale = locale or Locale.of(language=language, country=region)
        self._extractor = extractor or ContextExtractor()
        self._context: InnerTubeContext | None = None

    @property
    def locale(self) -> Locale:
        """The :class:`~ytscrape.locale.Locale` used for requests."""
        return self._locale

    @property
    def context(self) -> InnerTubeContext:
        """Return the InnerTube context, fetching it on first access."""
        if self._context is None:
            self._context = self._fetch_context()
        return self._context

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept-Language": self._locale.accept_language,
        }

    def _fetch_context(self) -> InnerTubeContext:
        try:
            response = self._session.get(
                _HOME_URL,
                headers=self._base_headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RequestError(f"Failed to load YouTube home page: {exc}") from exc
        return self._extractor.extract(response.text)

    def _client_context(self) -> dict[str, Any]:
        return {
            "client": {
                "clientName": "WEB",
                "clientVersion": self.context.client_version,
                "hl": self._locale.language.code,
                "gl": self._locale.country.code,
            }
        }

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{_BASE_API_URL}/{endpoint}?key={self.context.api_key}"
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "X-Goog-Visitor-Id": self.context.visitor_data,
        }
        try:
            response = self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise RequestError(f"Request to {endpoint!r} failed: {exc}") from exc

    def search(
        self,
        query: str | None = None,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``search`` endpoint.

        Either ``query`` (first page) or ``continuation`` (subsequent pages)
        must be provided.
        """
        payload: dict[str, Any] = {"context": self._client_context()}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["query"] = query or ""
            if params is not None:
                payload["params"] = params
        return self._post("search", payload)

    def player(self, video_id: str) -> dict[str, Any]:
        """Call the ``player`` endpoint for a single video."""
        payload = {"context": self._client_context(), "videoId": video_id}
        return self._post("player", payload)

    def next(
        self,
        video_id: str | None = None,
        *,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``next`` endpoint.

        Either ``video_id`` (to load the watch page, which contains the token
        that opens the comments section) or ``continuation`` (to load comment
        threads and their replies) must be provided.
        """
        payload: dict[str, Any] = {"context": self._client_context()}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["videoId"] = video_id or ""
        return self._post("next", payload)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> InnerTubeClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
