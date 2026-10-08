"""Low level HTTP client for the YouTube InnerTube API.

:class:`InnerTubeClient` owns the :class:`requests.Session`, lazily fetches the
:class:`~ytscrape.context.InnerTubeContext` and exposes thin wrappers around
the ``search`` and ``player`` endpoints. It knows nothing about models or
pagination; that logic lives in the higher level :class:`ytscrape.YouTube`
facade.
"""

from __future__ import annotations

import email.utils
import logging
import secrets
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests

from .context import (
    DEFAULT_CONTEXT_CACHE,
    ContextCache,
    ContextExtractor,
    InnerTubeContext,
)
from .exceptions import (
    AgeRestricted,
    BotDetected,
    ConsentRequired,
    RateLimited,
    RequestError,
    VideoUnavailable,
    with_block_mitigation,
)
from .locale import Country, Language, Locale

__all__ = [
    "InnerTubeClient",
    "RateLimiter",
    "RetryPolicy",
    "check_playability",
    "detect_block",
    "parse_retry_after",
]

logger = logging.getLogger("ytscrape")

#: HTTP statuses retried by default.
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Retry / exponential backoff settings shared by sync and async clients.

    The delay before retry ``n`` (0-based) is
    ``min(max_backoff, backoff_factor * 2 ** n)``, scaled by a random factor
    in ``[0.5, 1.0]`` when ``jitter`` is on. A ``Retry-After`` header (if
    ``respect_retry_after``) overrides it, capped at ``max_backoff``.

    Args:
        max_retries: Extra attempts after the first one (``0`` disables).
        backoff_factor: Base delay in seconds.
        max_backoff: Upper bound for a single sleep, in seconds.
        jitter: Randomise delays so concurrent clients do not retry in sync.
        retry_statuses: HTTP statuses that trigger a retry.
        retry_on_connection_errors: Also retry connection errors / timeouts.
        respect_retry_after: Honour the ``Retry-After`` response header.
    """

    max_retries: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 30.0
    jitter: bool = True
    retry_statuses: frozenset[int] = RETRYABLE_STATUS
    retry_on_connection_errors: bool = True
    respect_retry_after: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be >= 0")
        if self.max_backoff < 0:
            raise ValueError("max_backoff must be >= 0")

    @classmethod
    def disabled(cls) -> RetryPolicy:
        """A policy that never retries."""
        return cls(max_retries=0)

    def compute_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Seconds to sleep before retry number ``attempt`` (0-based)."""
        if retry_after is not None and self.respect_retry_after:
            return max(0.0, min(retry_after, self.max_backoff))
        delay = min(self.max_backoff, self.backoff_factor * (2**attempt))
        if self.jitter:
            # secrets avoids bandit B311 on stdlib random; not used for crypto.
            delay *= 0.5 + secrets.randbelow(10_001) / 10_000 * 0.5
        return delay


class RateLimiter:
    """Enforce a minimum interval between consecutive requests.

    Thread-safe; one instance may be shared by several clients (sync or
    async) to throttle them together.

    Args:
        min_interval: Minimum seconds between request starts (``0`` = off).
    """

    def __init__(self, min_interval: float = 0.0) -> None:
        if min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        self.min_interval = min_interval
        self._next_at = 0.0
        self._lock = threading.Lock()

    def reserve(self) -> float:
        """Book the next request slot and return how long to sleep first."""
        if self.min_interval <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_at)
            self._next_at = start + self.min_interval
            return start - now

    def wait(self) -> None:
        """Block the current thread until a request may be sent."""
        delay = self.reserve()
        if delay > 0:
            logger.debug("Rate limiter sleeping %.3fs", delay)
            time.sleep(delay)

    async def async_wait(self) -> None:
        """Async counterpart of :meth:`wait`."""
        import asyncio

        delay = self.reserve()
        if delay > 0:
            logger.debug("Rate limiter sleeping %.3fs", delay)
            await asyncio.sleep(delay)


def parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header (delta seconds or HTTP date)."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed is None:  # pragma: no cover - older Pythons
        return None
    return max(0.0, parsed.timestamp() - time.time())


_BOT_MARKERS = (
    "confirm you're not a bot",
    "confirm you\u2019re not a bot",
    'id="captcha-form"',
    "/sorry/index",
)
_CONSENT_HOSTS = ("consent.youtube.com", "consent.google.com")


def detect_block(
    url: str | None,
    text: str | None = None,
    status_code: int | None = None,
) -> None:
    """Raise if a response looks like a consent wall, captcha or bot check.

    Args:
        url: Final URL of the response (after redirects).
        text: Response body (HTML / text), optional.
        status_code: HTTP status, optional.

    Raises:
        ConsentRequired: Redirected to ``consent.youtube.com`` / ``consent.google.com``.
        BotDetected: ``google.com/sorry`` redirect, captcha or
            "Sign in to confirm you're not a bot" page.
    """
    final_url = (url or "").lower()
    if any(host in final_url for host in _CONSENT_HOSTS):
        raise ConsentRequired(
            with_block_mitigation("YouTube redirected to the cookie consent page"),
            status_code=status_code,
            url=url,
        )
    if "google.com/sorry" in final_url:
        raise BotDetected(
            with_block_mitigation("YouTube served a captcha (google.com/sorry)"),
            status_code=status_code,
            url=url,
        )
    if text:
        lowered = text[:200_000].lower()
        if any(marker in lowered for marker in _BOT_MARKERS):
            raise BotDetected(
                with_block_mitigation(
                    "YouTube asked to confirm you're not a bot (captcha / bot check)"
                ),
                status_code=status_code,
                url=url,
            )


def check_playability(data: dict[str, Any], video_id: str) -> None:
    """Raise for a ``player`` response whose ``playabilityStatus`` is not OK.

    Raises:
        BotDetected: ``LOGIN_REQUIRED`` with a "not a bot" reason.
        AgeRestricted: Age-gated video.
        VideoUnavailable: ``ERROR`` / ``UNPLAYABLE`` / other login walls.
    """
    status_block = data.get("playabilityStatus") or {}
    status = status_block.get("status")
    if status in (None, "OK", "LIVE_STREAM_OFFLINE"):
        return
    reason = str(status_block.get("reason") or "")
    lowered = reason.lower()
    check_bot_playability(data, video_id)
    if (
        "age" in lowered
        or status == "AGE_CHECK_REQUIRED"
        or ("desktopLegacyAgeGateReason" in status_block)
    ):
        raise AgeRestricted(video_id, reason or None)
    # Anonymous web clients often get ``UNPLAYABLE`` (no streams, e.g. missing
    # PoToken) while metadata is still present — that is fine for scraping.
    if status == "UNPLAYABLE" and data.get("videoDetails"):
        return
    raise VideoUnavailable(video_id, reason or status)


def check_bot_playability(data: dict[str, Any], video_id: str) -> None:
    """Raise :class:`BotDetected` if a ``player`` response is a bot check."""
    status_block = data.get("playabilityStatus") or {}
    reason = str(status_block.get("reason") or "")
    if "not a bot" in reason.lower():
        raise BotDetected(with_block_mitigation(f"{video_id}: {reason}"))


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
        proxies: Optional ``requests``-style proxy mapping, e.g.
            ``{"https": "http://user:pass@host:8080"}`` or
            ``{"http": "http://host:port", "https": "http://host:port"}``.
            Applied to the underlying session. You can also rotate proxies at
            runtime by assigning to the :attr:`proxies` property (handy after a
            :class:`~ytscrape.exceptions.BotDetected` error).
        retry: :class:`RetryPolicy` for 429 / 5xx / connection errors.
            Defaults to ``RetryPolicy()``; pass ``RetryPolicy.disabled()``
            to turn retries off.
        rate_limiter: Optional :class:`RateLimiter` (may be shared).
        min_interval: Shortcut creating a private ``RateLimiter`` when
            ``rate_limiter`` is omitted. ``0`` disables throttling.
        context_cache: ``None`` (default) uses the process-wide
            :data:`~ytscrape.context.DEFAULT_CONTEXT_CACHE` only when the
            client creates its own session; ``True`` always uses it;
            ``False`` disables caching; or pass a
            :class:`~ytscrape.context.ContextCache`.
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
        proxies: Mapping[str, str] | None = None,
        retry: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        min_interval: float = 0.0,
        context_cache: ContextCache | bool | None = None,
    ) -> None:
        self._session = session or requests.Session()
        if proxies is not None:
            self._session.proxies.update(proxies)
        self._user_agent = user_agent
        self._timeout = timeout
        self._locale = locale or Locale.of(language=language, country=region)
        self._extractor = extractor or ContextExtractor()
        self._context: InnerTubeContext | None = None
        self._retry = retry or RetryPolicy()
        self._rate_limiter = rate_limiter or RateLimiter(min_interval)
        self._context_cache = resolve_context_cache(
            context_cache, owns_session=session is None
        )

    @property
    def proxies(self) -> dict[str, str]:
        """The proxy mapping applied to the underlying session.

        Assign a new mapping to rotate proxies at runtime (e.g. after a
        :class:`~ytscrape.exceptions.BotDetected` error); pass ``None`` or an
        empty mapping to clear the proxy configuration.
        """
        return dict(self._session.proxies)

    @proxies.setter
    def proxies(self, value: Mapping[str, str] | None) -> None:
        self._session.proxies.clear()
        if value:
            self._session.proxies.update(value)

    @property
    def retry_policy(self) -> RetryPolicy:
        """The :class:`RetryPolicy` in use."""
        return self._retry

    @property
    def rate_limiter(self) -> RateLimiter:
        """The :class:`RateLimiter` in use."""
        return self._rate_limiter

    @property
    def locale(self) -> Locale:
        """The :class:`~ytscrape.locale.Locale` used for requests."""
        return self._locale

    @property
    def context(self) -> InnerTubeContext:
        """Return the InnerTube context, fetching it on first access."""
        if self._context is None:
            key = self._cache_key()
            cache = self._context_cache
            cached = cache.get(key) if cache is not None else None
            if cached is not None:
                logger.debug("Using cached InnerTube context for %s", key)
                self._context = cached
            else:
                self._context = self._fetch_context()
                if self._context_cache is not None:
                    self._context_cache.set(key, self._context)
        return self._context

    def _cache_key(self) -> tuple[str, str]:
        return (self._locale.language.code, self._locale.country.code)

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
        expect_json: bool = False,
        error_prefix: str,
    ) -> Any:
        policy = self._retry
        attempts = policy.max_retries + 1
        for attempt in range(attempts):
            self._rate_limiter.wait()
            started = time.monotonic()
            logger.debug("%s %s (attempt %d/%d)", method, url, attempt + 1, attempts)
            try:
                if method == "POST":
                    response = self._session.post(
                        url, json=json, headers=headers, timeout=self._timeout
                    )
                else:
                    response = self._session.get(
                        url, headers=headers, timeout=self._timeout
                    )
            except (requests.ConnectionError, requests.Timeout) as exc:
                if policy.retry_on_connection_errors and attempt + 1 < attempts:
                    delay = policy.compute_delay(attempt)
                    logger.debug("%s; retrying in %.2fs", exc, delay)
                    time.sleep(delay)
                    continue
                raise RequestError(f"{error_prefix}: {exc}", url=url) from exc
            except requests.RequestException as exc:
                raise RequestError(f"{error_prefix}: {exc}", url=url) from exc

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
                final_url if isinstance(final_url, str) else None,
                None if expect_json else getattr(response, "text", None),
                status,
            )
            if isinstance(status, int) and status in policy.retry_statuses:
                resp_headers = getattr(response, "headers", None) or {}
                retry_after = parse_retry_after(resp_headers.get("Retry-After"))
                if attempt + 1 < attempts:
                    delay = policy.compute_delay(attempt, retry_after)
                    logger.debug("HTTP %s; retrying in %.2fs", status, delay)
                    time.sleep(delay)
                    continue
                if status == 429:
                    raise RateLimited(
                        with_block_mitigation(
                            f"{error_prefix}: HTTP 429 Too Many Requests"
                        ),
                        url=url,
                        retry_after=retry_after,
                    )
            try:
                response.raise_for_status()
                if expect_json:
                    return response.json()
                return response.text
            except requests.RequestException as exc:
                raise RequestError(
                    f"{error_prefix}: {exc}", status_code=status, url=url
                ) from exc
            except ValueError as exc:
                raise RequestError(
                    f"{error_prefix}: invalid JSON: {exc}", status_code=status, url=url
                ) from exc
        raise RequestError(
            f"{error_prefix}: retries exhausted", url=url
        )  # pragma: no cover

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept-Language": self._locale.accept_language,
        }

    def _fetch_context(self) -> InnerTubeContext:
        text = self._request(
            "GET",
            _HOME_URL,
            headers=self._base_headers(),
            error_prefix="Failed to load YouTube home page",
        )
        return self._extractor.extract(text)

    def _client_context(self) -> dict[str, Any]:
        return self._client_context_for("WEB")

    def _client_context_for(self, client_name: str) -> dict[str, Any]:
        """Build an InnerTube ``context`` block for the given client identity."""
        name = (client_name or "WEB").upper()
        if name == "ANDROID":
            # Stable public Android client used by youtube-transcript-api.
            # Caption tracks are more reliably exposed here than on WEB.
            version = "20.10.38"
        else:
            name = "WEB"
            version = self.context.client_version
        return {
            "client": {
                "clientName": name,
                "clientVersion": version,
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
        return self._request(
            "POST",
            url,
            headers=headers,
            json=payload,
            expect_json=True,
            error_prefix=f"Request to {endpoint!r} failed",
        )

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

    def player(
        self,
        video_id: str,
        *,
        client_name: str = "WEB",
    ) -> dict[str, Any]:
        """Call the ``player`` endpoint for a single video.

        Args:
            video_id: 11-char YouTube video id.
            client_name: InnerTube client identity. ``WEB`` is used for normal
                metadata; ``ANDROID`` is preferred for caption track lists
                (same approach as youtube-transcript-api).
        """
        payload = {
            "context": self._client_context_for(client_name),
            "videoId": video_id,
        }
        data = self._post("player", payload)
        check_bot_playability(data, video_id)
        return data

    def get_text(self, url: str) -> str:
        """GET an arbitrary URL and return the response body as text.

        Used for timedtext / caption XML downloads.
        """
        return self._request(
            "GET",
            url,
            headers=self._base_headers(),
            error_prefix=f"Failed to load {url!r}",
        )

    def browse(
        self,
        browse_id: str,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        """Call the ``browse`` endpoint (channels, tabs, shelves, …).

        Either ``browse_id`` (first page of a channel / tab) or
        ``continuation`` (subsequent pages) must be provided.
        """
        payload: dict[str, Any] = {"context": self._client_context()}
        if continuation is not None:
            payload["continuation"] = continuation
        else:
            payload["browseId"] = browse_id
            if params is not None:
                payload["params"] = params
        return self._post("browse", payload)

    def get_html(self, url: str) -> str:
        """GET an arbitrary YouTube page and return its HTML body."""
        return self._request(
            "GET",
            url,
            headers=self._base_headers(),
            error_prefix=f"Failed to load {url!r}",
        )

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


def resolve_context_cache(
    value: ContextCache | bool | None, *, owns_session: bool
) -> ContextCache | None:
    """Normalise the ``context_cache`` constructor argument."""
    if isinstance(value, ContextCache):
        return value
    if value is True or (value is None and owns_session):
        return DEFAULT_CONTEXT_CACHE
    return None
