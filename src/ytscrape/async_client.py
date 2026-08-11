"""Async low-level HTTP client for the YouTube InnerTube API.

Uses optional :mod:`httpx`. Install with::

    pip install ytscrape[async]

:class:`AsyncInnerTubeClient` mirrors :class:`~ytscrape.client.InnerTubeClient`
and adds a concurrency semaphore plus exponential backoff on transient HTTP
errors (429 / 5xx).
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from .context import ContextExtractor, InnerTubeContext
from .exceptions import RequestError
from .locale import Country, Language, Locale

__all__ = ["AsyncInnerTubeClient"]

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

_HOME_URL = "https://www.youtube.com"
_BASE_API_URL = "https://www.youtube.com/youtubei/v1"

# HTTP statuses worth retrying with backoff.
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _require_httpx() -> Any:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise ImportError(
            "Async support requires httpx. Install it with: "
            'pip install "ytscrape[async]"'
        ) from exc
    return httpx


class AsyncInnerTubeClient:
    """Async InnerTube client backed by :class:`httpx.AsyncClient`.

    Args:
        session: Optional pre-configured ``httpx.AsyncClient``. A new one is
            created when omitted.
        user_agent: ``User-Agent`` header sent with every request.
        timeout: Per-request timeout in seconds.
        locale: Localisation for responses.
        language: ``hl`` when ``locale`` is omitted.
        region: ``gl`` when ``locale`` is omitted.
        extractor: Strategy used to parse the InnerTube context from HTML.
        max_concurrency: Maximum number of in-flight HTTP requests.
        max_retries: Extra attempts after the first failure for retryable
            status codes and transport errors.
        backoff_factor: Base delay (seconds) for exponential backoff.
            Sleep is ``backoff_factor * 2 ** attempt`` plus a small jitter.
    """

    def __init__(
        self,
        *,
        session: Any | None = None,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout: float = 30.0,
        locale: Locale | None = None,
        language: Language | str = "en",
        region: Country | str = "US",
        extractor: ContextExtractor | None = None,
        max_concurrency: int = 8,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        httpx = _require_httpx()
        self._owns_session = session is None
        self._session = session or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )
        self._user_agent = user_agent
        self._timeout = timeout
        self._locale = locale or Locale.of(language=language, country=region)
        self._extractor = extractor or ContextExtractor()
        self._context: InnerTubeContext | None = None
        self._context_lock = asyncio.Lock()
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if backoff_factor < 0:
            raise ValueError("backoff_factor must be >= 0")
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    @property
    def locale(self) -> Locale:
        """The :class:`~ytscrape.locale.Locale` used for requests."""
        return self._locale

    @property
    def max_concurrency(self) -> int:
        """Maximum number of concurrent HTTP requests."""
        return self._max_concurrency

    async def get_context(self) -> InnerTubeContext:
        """Return the InnerTube context, fetching it on first access."""
        if self._context is not None:
            return self._context
        async with self._context_lock:
            if self._context is None:
                self._context = await self._fetch_context()
            return self._context

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept-Language": self._locale.accept_language,
        }

    async def _sleep_backoff(self, attempt: int) -> None:
        delay = self._backoff_factor * (2**attempt)
        # Full jitter keeps concurrent clients from retrying in lockstep.
        delay = delay * (0.5 + random.random() * 0.5)
        if delay > 0:
            await asyncio.sleep(delay)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        expect_json: bool = False,
        error_prefix: str,
    ) -> Any:
        httpx = _require_httpx()
        last_exc: Exception | None = None
        attempts = self._max_retries + 1

        for attempt in range(attempts):
            try:
                async with self._semaphore:
                    response = await self._session.request(
                        method,
                        url,
                        headers=headers,
                        json=json,
                        timeout=self._timeout,
                    )
                if response.status_code in _RETRYABLE_STATUS:
                    if attempt + 1 < attempts:
                        await self._sleep_backoff(attempt)
                        continue
                    response.raise_for_status()
                response.raise_for_status()
                if expect_json:
                    return response.json()
                return response.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code if exc.response is not None else None
                if status in _RETRYABLE_STATUS and attempt + 1 < attempts:
                    await self._sleep_backoff(attempt)
                    continue
                raise RequestError(f"{error_prefix}: {exc}") from exc
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt + 1 < attempts:
                    await self._sleep_backoff(attempt)
                    continue
                raise RequestError(f"{error_prefix}: {exc}") from exc

        raise RequestError(f"{error_prefix}: {last_exc}")

    async def _fetch_context(self) -> InnerTubeContext:
        text = await self._request(
            "GET",
            _HOME_URL,
            headers=self._base_headers(),
            error_prefix="Failed to load YouTube home page",
        )
        return self._extractor.extract(text)

    def _client_context_for(
        self, client_name: str, *, client_version: str
    ) -> dict[str, Any]:
        name = (client_name or "WEB").upper()
        if name == "ANDROID":
            version = "20.10.38"
        else:
            name = "WEB"
            version = client_version
        return {
            "client": {
                "clientName": name,
                "clientVersion": version,
                "hl": self._locale.language.code,
                "gl": self._locale.country.code,
            }
        }

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        context = await self.get_context()
        url = f"{_BASE_API_URL}/{endpoint}?key={context.api_key}"
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "X-Goog-Visitor-Id": context.visitor_data,
        }
        data = await self._request(
            "POST",
            url,
            headers=headers,
            json=payload,
            expect_json=True,
            error_prefix=f"Request to {endpoint!r} failed",
        )
        if not isinstance(data, dict):
            raise RequestError(f"Request to {endpoint!r} returned non-object JSON")
        return data

    async def search(
        self,
        query: str | None = None,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``search`` endpoint."""
        context = await self.get_context()
        web_ctx = self._client_context_for("WEB", client_version=context.client_version)
        payload: dict[str, Any] = {"context": web_ctx}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["query"] = query or ""
            if params is not None:
                payload["params"] = params
        return await self._post("search", payload)

    async def player(
        self,
        video_id: str,
        *,
        client_name: str = "WEB",
    ) -> dict[str, Any]:
        """Call the ``player`` endpoint for a single video."""
        context = await self.get_context()
        payload = {
            "context": self._client_context_for(
                client_name, client_version=context.client_version
            ),
            "videoId": video_id,
        }
        return await self._post("player", payload)

    async def get_text(self, url: str) -> str:
        """GET an arbitrary URL and return the response body as text."""
        return await self._request(
            "GET",
            url,
            headers=self._base_headers(),
            error_prefix=f"Failed to load {url!r}",
        )

    async def browse(
        self,
        browse_id: str,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``browse`` endpoint."""
        context = await self.get_context()
        web_ctx = self._client_context_for("WEB", client_version=context.client_version)
        payload: dict[str, Any] = {"context": web_ctx}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["browseId"] = browse_id
            if params is not None:
                payload["params"] = params
        return await self._post("browse", payload)

    async def get_html(self, url: str) -> str:
        """GET an arbitrary YouTube page and return its HTML body."""
        return await self._request(
            "GET",
            url,
            headers=self._base_headers(),
            error_prefix=f"Failed to load {url!r}",
        )

    async def next(
        self,
        video_id: str | None = None,
        *,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``next`` endpoint."""
        context = await self.get_context()
        web_ctx = self._client_context_for("WEB", client_version=context.client_version)
        payload: dict[str, Any] = {"context": web_ctx}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["videoId"] = video_id or ""
        return await self._post("next", payload)

    async def aclose(self) -> None:
        """Close the underlying HTTP session if this client owns it."""
        if self._owns_session:
            await self._session.aclose()

    async def close(self) -> None:
        """Alias for :meth:`aclose` (matches the sync client name)."""
        await self.aclose()

    async def __aenter__(self) -> AsyncInnerTubeClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
