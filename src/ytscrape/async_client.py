"""Async low-level HTTP client for the YouTube InnerTube API.

Uses optional :mod:`httpx`. Install with::

    pip install ytscrape[async]

:class:`AsyncInnerTubeClient` mirrors :class:`~ytscrape.client.InnerTubeClient`
and adds a concurrency semaphore plus exponential backoff on transient HTTP
errors (429 / 5xx).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

from .client import (
    RETRYABLE_STATUS,
    RateLimiter,
    RetryPolicy,
    check_bot_playability,
    detect_block,
    logger,
    parse_retry_after,
    resolve_context_cache,
)
from .context import ContextCache, ContextExtractor, InnerTubeContext
from .exceptions import RateLimited, RequestError, with_block_mitigation
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
_RETRYABLE_STATUS = RETRYABLE_STATUS


def _require_httpx() -> Any:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise ImportError(
            "Async support requires httpx. Install it with: "
            'pip install "ytscrape[async]"'
        ) from exc
    return httpx


def _proxies_to_mounts(httpx: Any, proxies: Mapping[str, str]) -> dict[str, Any]:
    """Convert a ``requests``-style proxy mapping to ``httpx`` mounts.

    ``httpx`` 0.28 dropped the ``proxies=`` argument in favour of ``mounts``.
    Keys such as ``"http"`` / ``"https"`` / ``"all"`` are normalised to the
    ``"<scheme>://"`` form expected by :class:`httpx.AsyncClient`.
    """
    mounts: dict[str, Any] = {}
    for scheme, url in proxies.items():
        if not url:
            continue
        key = scheme if scheme.endswith("://") else f"{scheme}://"
        mounts[key] = httpx.AsyncHTTPTransport(proxy=url)
    return mounts


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
        proxies: Optional ``requests``-style proxy mapping, e.g.
            ``{"https": "http://user:pass@host:8080"}``. Applied only when this
            client creates its own session (ignored when ``session`` is given).
        max_concurrency: Maximum number of in-flight HTTP requests.
        max_retries: Extra attempts after the first failure for retryable
            status codes and transport errors.
        backoff_factor: Base delay (seconds) for exponential backoff.
            Sleep is ``backoff_factor * 2 ** attempt`` plus a small jitter.
        retry: Full :class:`~ytscrape.client.RetryPolicy`; when given it
            overrides ``max_retries`` / ``backoff_factor``.
        rate_limiter: Optional shared :class:`~ytscrape.client.RateLimiter`.
        min_interval: Minimum seconds between requests when ``rate_limiter``
            is omitted (``0`` = off).
        context_cache: Same semantics as on
            :class:`~ytscrape.client.InnerTubeClient`.
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
        proxies: Mapping[str, str] | None = None,
        max_concurrency: int = 8,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        retry: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        min_interval: float = 0.0,
        context_cache: ContextCache | bool | None = None,
    ) -> None:
        httpx = _require_httpx()
        self._owns_session = session is None
        self._proxies = dict(proxies) if proxies else {}
        self._session = session or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            mounts=_proxies_to_mounts(httpx, self._proxies),
        )
        self._user_agent = user_agent
        self._timeout = timeout
        self._locale = locale or Locale.of(language=language, country=region)
        self._extractor = extractor or ContextExtractor()
        self._context: InnerTubeContext | None = None
        self._context_lock = asyncio.Lock()
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if retry is None:
            retry = RetryPolicy(max_retries=max_retries, backoff_factor=backoff_factor)
        self._retry = retry
        self._rate_limiter = rate_limiter or RateLimiter(min_interval)
        self._context_cache = resolve_context_cache(
            context_cache, owns_session=self._owns_session
        )
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @property
    def proxies(self) -> dict[str, str]:
        """The proxy mapping applied when this client created its own session.

        Read-only: ``httpx`` bakes proxies into the transport at construction
        time, so rotating them requires building a new client/session.
        """
        return dict(self._proxies)

    @property
    def retry_policy(self) -> RetryPolicy:
        """The :class:`~ytscrape.client.RetryPolicy` in use."""
        return self._retry

    @property
    def rate_limiter(self) -> RateLimiter:
        """The :class:`~ytscrape.client.RateLimiter` in use."""
        return self._rate_limiter

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
                key = (self._locale.language.code, self._locale.country.code)
                cache = self._context_cache
                cached = cache.get(key) if cache is not None else None
                if cached is not None:
                    logger.debug("Using cached InnerTube context for %s", key)
                    self._context = cached
                else:
                    self._context = await self._fetch_context()
                    if cache is not None:
                        cache.set(key, self._context)
            return self._context

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept-Language": self._locale.accept_language,
        }

    async def _sleep_backoff(
        self, attempt: int, retry_after: float | None = None
    ) -> None:
        delay = self._retry.compute_delay(attempt, retry_after)
        logger.debug("Retrying in %.2fs", delay)
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
        policy = self._retry
        attempts = policy.max_retries + 1

        for attempt in range(attempts):
            try:
                await self._rate_limiter.async_wait()
                started = time.monotonic()
                logger.debug(
                    "%s %s (attempt %d/%d)", method, url, attempt + 1, attempts
                )
                async with self._semaphore:
                    response = await self._session.request(
                        method,
                        url,
                        headers=headers,
                        json=json,
                        timeout=self._timeout,
                    )
                status = getattr(response, "status_code", None)
                logger.debug(
                    "%s %s -> %s in %.3fs",
                    method,
                    url,
                    status,
                    time.monotonic() - started,
                )
                final_url = getattr(response, "url", None)
                detect_block(
                    str(final_url) if final_url is not None else None,
                    None if expect_json else getattr(response, "text", None),
                    status,
                )
                if status in policy.retry_statuses:
                    resp_headers = getattr(response, "headers", None) or {}
                    retry_after = parse_retry_after(resp_headers.get("Retry-After"))
                    if attempt + 1 < attempts:
                        await self._sleep_backoff(attempt, retry_after)
                        continue
                    if status == 429:
                        raise RateLimited(
                            with_block_mitigation(
                                f"{error_prefix}: HTTP 429 Too Many Requests"
                            ),
                            url=url,
                            retry_after=retry_after,
                        )
                response.raise_for_status()
                if expect_json:
                    return response.json()
                return response.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code if exc.response is not None else None
                if status in policy.retry_statuses and attempt + 1 < attempts:
                    await self._sleep_backoff(attempt)
                    continue
                raise RequestError(
                    f"{error_prefix}: {exc}", status_code=status, url=url
                ) from exc
            except httpx.RequestError as exc:
                last_exc = exc
                if policy.retry_on_connection_errors and attempt + 1 < attempts:
                    await self._sleep_backoff(attempt)
                    continue
                raise RequestError(f"{error_prefix}: {exc}", url=url) from exc

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
        data = await self._post("player", payload)
        check_bot_playability(data, video_id)
        return data

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
