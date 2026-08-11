"""Async public facade: :class:`AsyncYouTube`."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from . import parsing
from .async_client import AsyncInnerTubeClient
from .async_results import AsyncCommentThread, AsyncSearchResults
from .exceptions import ParseError
from .filters import CommentSort, SearchFilter
from .locale import Country, Language, Locale
from .models import ChannelDetails, VideoDetails, _about_continuation_token
from .transcripts import (
    Transcript,
    TranscriptList,
    async_fetch_transcript,
    async_list_transcripts,
)
from .youtube import (
    _CHANNEL_ID_IN_HTML_RE,
    _CHANNEL_ID_RE,
    _HANDLE_RE,
    YouTube,
)

__all__ = ["AsyncYouTube"]


class AsyncYouTube:
    """Async high-level entry point with the same surface as :class:`YouTube`.

    Typical usage::

        import asyncio
        from ytscrape import AsyncYouTube, SearchFilter

        async def main() -> None:
            async with AsyncYouTube() as yt:
                async for video in await yt.search(
                    "python", filter=SearchFilter.VIDEOS, max_results=10
                ):
                    print(video.title, video.url)

                details = await yt.video("dQw4w9WgXcQ")
                print(details.title)

        asyncio.run(main())

    Requires the optional ``httpx`` extra: ``pip install ytscrape[async]``.

    Args:
        client: A pre-built :class:`AsyncInnerTubeClient`.
        locale: Locale when building a default client.
        language: ``hl`` when ``locale`` is omitted.
        region: ``gl`` when ``locale`` is omitted.
        timeout: Per-request timeout for the default client.
        max_concurrency: Cap on concurrent HTTP requests (default client only).
        max_retries: Retry budget for transient failures (default client only).
        backoff_factor: Base delay for exponential backoff (default client only).
    """

    def __init__(
        self,
        *,
        client: AsyncInnerTubeClient | None = None,
        locale: Locale | None = None,
        language: Language | str = "en",
        region: Country | str = "US",
        timeout: float = 30.0,
        max_concurrency: int = 8,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self._client = client or AsyncInnerTubeClient(
            locale=locale,
            language=language,
            region=region,
            timeout=timeout,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )

    @property
    def client(self) -> AsyncInnerTubeClient:
        """The underlying :class:`AsyncInnerTubeClient`."""
        return self._client

    @property
    def locale(self) -> Locale:
        """The :class:`~ytscrape.locale.Locale` used for requests."""
        return self._client.locale

    async def search(
        self,
        query: str,
        *,
        filter: SearchFilter | str = SearchFilter.ALL,
        max_results: int | None = None,
    ) -> AsyncSearchResults:
        """Search YouTube and return paginated :class:`AsyncSearchResults`."""
        search_filter = SearchFilter.from_value(filter)
        first_page = await self._client.search(query, params=search_filter.params)
        return AsyncSearchResults(self._client, first_page, max_results=max_results)

    async def transcript(
        self,
        video: str,
        *,
        languages: list[str] | tuple[str, ...] = ("en",),
        preserve_formatting: bool = False,
    ) -> Transcript:
        """Fetch a transcript/captions track for a video."""
        video_id = YouTube._normalize_video_id(video)
        return await async_fetch_transcript(
            self._client,
            video_id,
            languages=languages,
            preserve_formatting=preserve_formatting,
        )

    async def transcripts(self, video: str) -> TranscriptList:
        """List available caption tracks for a video."""
        video_id = YouTube._normalize_video_id(video)
        return await async_list_transcripts(self._client, video_id)

    async def video(self, video: str) -> VideoDetails:
        """Fetch detailed metadata for a single video."""
        video_id = YouTube._normalize_video_id(video)
        response = await self._client.player(video_id)
        return VideoDetails.from_player_response(response)

    async def channel(self, channel: str) -> ChannelDetails:
        """Fetch detailed metadata for a single channel."""
        channel_id = await self._normalize_channel_id(channel)
        response = await self._client.browse(channel_id)
        about_response = None
        about_token = _about_continuation_token(response)
        if about_token is not None:
            about_response = await self._client.browse(
                channel_id, continuation=about_token
            )
        details = ChannelDetails.from_browse_response(response, about=about_response)
        if not details.channel_id:
            raise ParseError(f"Could not parse channel metadata for {channel_id!r}.")
        return details

    async def comments(
        self,
        video: str,
        *,
        max_results: int | None = None,
        include_replies: bool = False,
        sort: CommentSort | str = CommentSort.TOP,
    ) -> AsyncCommentThread:
        """Collect comments of a video as a paginated async thread."""
        sort_order = CommentSort.from_value(sort)
        video_id = YouTube._normalize_video_id(video)
        watch_page = await self._client.next(video_id)
        token = parsing.find_comments_continuation(watch_page)
        if token is None:
            raise ParseError(
                f"Could not find a comments section for video {video_id!r} "
                "(comments may be disabled)."
            )
        first_page = await self._client.next(continuation=token)

        if sort_order is not CommentSort.TOP:
            sort_token = parsing.find_comments_sort_continuation(
                first_page,
                title=sort_order.menu_title,
                index=sort_order.menu_index,
            )
            if sort_token is not None:
                first_page = await self._client.next(continuation=sort_token)

        return AsyncCommentThread(
            self._client,
            first_page,
            max_results=max_results,
            include_replies=include_replies,
        )

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._client.close()

    async def __aenter__(self) -> AsyncYouTube:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def _normalize_channel_id(self, value: str) -> str:
        value = value.strip()
        if _CHANNEL_ID_RE.match(value):
            return value

        if _HANDLE_RE.match(value):
            return await self._resolve_channel_id_from_url(
                f"https://www.youtube.com/{value}"
            )

        parsed = urlparse(value)
        segments = [seg for seg in parsed.path.split("/") if seg]
        if not segments and not parsed.netloc:
            if re.match(r"^[\w.-]{3,}$", value):
                return await self._resolve_channel_id_from_url(
                    f"https://www.youtube.com/@{value}"
                )
            raise ParseError(f"Could not extract a channel id from {value!r}.")

        if not segments:
            raise ParseError(f"Could not extract a channel id from {value!r}.")

        if segments[0] == "channel" and len(segments) >= 2:
            candidate = segments[1]
            if _CHANNEL_ID_RE.match(candidate):
                return candidate
            raise ParseError(f"Could not extract a channel id from {value!r}.")

        if segments[0].startswith("@") or segments[0] in {"c", "user"}:
            path = "/" + "/".join(
                segments[:2] if segments[0] in {"c", "user"} else segments[:1]
            )
            return await self._resolve_channel_id_from_url(
                f"https://www.youtube.com{path}"
            )

        if _CHANNEL_ID_RE.match(segments[-1]):
            return segments[-1]

        raise ParseError(f"Could not extract a channel id from {value!r}.")

    async def _resolve_channel_id_from_url(self, url: str) -> str:
        html = await self._client.get_html(url)
        match = _CHANNEL_ID_IN_HTML_RE.search(html)
        if match:
            return match.group(1)
        raise ParseError(f"Could not resolve a channel id from {url!r}.")
