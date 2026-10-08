"""Tests for the async API (fake clients; no live network)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock

import pytest

from ytscrape import (
    AsyncCommentThread,
    AsyncSearchResults,
    AsyncYouTube,
    CommentSort,
    ParseError,
    SearchFilter,
    VideoDetails,
)
from ytscrape.async_client import AsyncInnerTubeClient


class FakeAsyncClient:
    """Minimal async stand-in for :class:`AsyncInnerTubeClient`."""

    def __init__(
        self,
        *,
        comments_token: str | None = "CT",
        html: str = "",
        browse_response: dict[str, Any] | None = None,
    ) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.player_calls: list[str] = []
        self.browse_calls: list[dict[str, Any]] = []
        self.get_html_calls: list[str] = []
        self.next_calls: list[dict[str, Any]] = []
        self._comments_token = comments_token
        self._html = html
        self._browse_response = browse_response
        self.closed = False

    async def search(
        self,
        query: str | None = None,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        self.search_calls.append(
            {"query": query, "params": params, "continuation": continuation}
        )
        return {"contents": [{"videoRenderer": {"videoId": "vid1"}}]}

    async def player(
        self, video_id: str, *, client_name: str = "WEB"
    ) -> dict[str, Any]:
        self.player_calls.append(video_id)
        return {"videoDetails": {"videoId": video_id, "title": "T"}}

    async def browse(
        self,
        browse_id: str,
        *,
        params: str | None = None,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        self.browse_calls.append(
            {
                "browse_id": browse_id,
                "params": params,
                "continuation": continuation,
            }
        )
        if self._browse_response is not None:
            return self._browse_response
        return {
            "metadata": {
                "channelMetadataRenderer": {
                    "title": "Channel",
                    "externalId": browse_id,
                }
            }
        }

    async def get_html(self, url: str) -> str:
        self.get_html_calls.append(url)
        return self._html

    async def next(
        self,
        video_id: str | None = None,
        *,
        continuation: str | None = None,
    ) -> dict[str, Any]:
        self.next_calls.append({"video_id": video_id, "continuation": continuation})
        if continuation is None:
            section: dict[str, Any] = {
                "itemSectionRenderer": {
                    "sectionIdentifier": "comment-item-section",
                }
            }
            if self._comments_token is not None:
                section["itemSectionRenderer"]["continuationCommand"] = {
                    "token": self._comments_token
                }
            return {"contents": [section]}
        comment_id = "n1" if continuation == "NEWEST" else "c1"
        return {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {
                            "payload": {
                                "commentEntityPayload": {
                                    "properties": {
                                        "commentId": comment_id,
                                        "content": {"content": "hi"},
                                    },
                                    "author": {"displayName": "A"},
                                    "toolbar": {},
                                }
                            }
                        }
                    ]
                }
            },
            "sortFilterSubMenuRenderer": {
                "subMenuItems": [
                    {"title": "Top comments", "selected": True},
                    {
                        "title": "Newest first",
                        "selected": False,
                        "serviceEndpoint": {"continuationCommand": {"token": "NEWEST"}},
                    },
                ]
            },
            "contents": [
                {"commentViewModel": {"commentViewModel": {"commentId": comment_id}}}
            ],
        }

    async def close(self) -> None:
        self.closed = True


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class TestAsyncYouTubeSearch:
    def test_search_returns_async_results(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            results = await yt.search("python")
            assert isinstance(results, AsyncSearchResults)
            items = [item async for item in results]
            assert len(items) == 1
            assert client.search_calls[0]["query"] == "python"

        _run(body())

    def test_search_passes_filter_params(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            await yt.search("python", filter=SearchFilter.VIDEOS)
            assert client.search_calls[0]["params"] == "EgIQAQ=="

        _run(body())


class TestAsyncYouTubeVideo:
    def test_video_returns_details(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            details = await yt.video("dQw4w9WgXcQ")
            assert isinstance(details, VideoDetails)
            assert details.video_id == "dQw4w9WgXcQ"

        _run(body())


class TestAsyncYouTubeChannel:
    def test_channel_handle(self) -> None:
        async def body() -> None:
            channel_id = "UCuAXFkgsw1L7xaCfnd5JJOw"
            client = FakeAsyncClient(html=f'{{"externalId":"{channel_id}"}}')
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            details = await yt.channel("@RickAstleyYT")
            assert details.channel_id == channel_id

        _run(body())


class TestAsyncYouTubeComments:
    def test_comments_iteration(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            thread = await yt.comments("dQw4w9WgXcQ")
            assert isinstance(thread, AsyncCommentThread)
            comments = [c async for c in thread]
            assert [c.comment_id for c in comments] == ["c1"]

        _run(body())

    def test_comments_newest(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            thread = await yt.comments("dQw4w9WgXcQ", sort=CommentSort.NEWEST)
            comments = [c async for c in thread]
            assert [c.comment_id for c in comments] == ["n1"]

        _run(body())

    def test_comments_without_section_raises(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient(comments_token=None)
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            with pytest.raises(ParseError, match="comments section"):
                await yt.comments("dQw4w9WgXcQ")

        _run(body())


class TestAsyncLifecycle:
    def test_context_manager(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            async with AsyncYouTube(client=client) as yt:  # type: ignore[arg-type]
                assert yt.client is client
            assert client.closed is True

        _run(body())


class TestAsyncClientBackoff:
    def test_retries_on_429(self) -> None:
        httpx = pytest.importorskip("httpx")

        async def body() -> None:
            home = (
                '"INNERTUBE_API_KEY":"KEY",'
                '"INNERTUBE_CLIENT_VERSION":"1.2.3",'
                '"VISITOR_DATA":"VD"'
            )
            call_count = {"n": 0}

            class FakeResponse:
                def __init__(self, status_code: int, text: str = "", data: Any = None):
                    self.status_code = status_code
                    self.text = text
                    self._data = data or {}
                    self.request = httpx.Request("GET", "https://www.youtube.com")

                def raise_for_status(self) -> None:
                    if self.status_code >= 400:
                        raise httpx.HTTPStatusError(
                            "err",
                            request=self.request,
                            response=httpx.Response(
                                self.status_code, request=self.request
                            ),
                        )

                def json(self) -> Any:
                    return self._data

            class FakeSession:
                async def request(self, method: str, url: str, **kwargs: Any) -> Any:
                    call_count["n"] += 1
                    if "youtubei" in url:
                        if call_count["n"] < 3:
                            return FakeResponse(429)
                        return FakeResponse(200, data={"ok": True})
                    return FakeResponse(200, text=home)

                async def aclose(self) -> None:
                    return None

            client = AsyncInnerTubeClient(
                session=FakeSession(),
                max_retries=3,
                backoff_factor=0.0,
            )
            result = await client.search("q")
            assert result == {"ok": True}
            assert call_count["n"] >= 3
            await client.close()

        _run(body())

    def test_invalid_concurrency(self) -> None:
        pytest.importorskip("httpx")
        with pytest.raises(ValueError, match="max_concurrency"):
            AsyncInnerTubeClient(session=MagicMock(), max_concurrency=0)


class TestAsyncProxies:
    def test_proxies_to_mounts_helper(self) -> None:
        httpx = pytest.importorskip("httpx")
        from ytscrape.async_client import _proxies_to_mounts

        mounts = _proxies_to_mounts(
            httpx, {"https": "http://proxy:8080", "http": "http://proxy:3128"}
        )
        assert set(mounts) == {"https://", "http://"}
        assert all(
            isinstance(t, httpx.AsyncHTTPTransport) for t in mounts.values()
        )

    def test_proxies_build_client_with_mounts(self) -> None:
        pytest.importorskip("httpx")
        proxies = {"https": "http://user:pass@proxy:8080"}
        client = AsyncInnerTubeClient(proxies=proxies)
        assert client.proxies == proxies
        # The proxy is wired into the underlying httpx client's mounts.
        assert len(client._session._mounts) >= 1

    def test_proxies_default_empty(self) -> None:
        pytest.importorskip("httpx")
        client = AsyncInnerTubeClient()
        assert client.proxies == {}

    def test_proxies_forwarded_by_facade(self) -> None:
        pytest.importorskip("httpx")
        proxies = {"https": "http://proxy:8080"}
        yt = AsyncYouTube(proxies=proxies)
        assert yt.proxies == proxies


class TestAsyncSearchPaging:
    def test_fetch_next_page(self) -> None:
        async def body() -> None:
            class PagingClient:
                async def search(self, **kwargs: Any) -> dict[str, Any]:
                    if kwargs.get("continuation") == "T1":
                        return {
                            "contents": [
                                {"videoRenderer": {"videoId": "v2", "title": {}}}
                            ]
                        }
                    return {}

            first = {
                "contents": [
                    {"videoRenderer": {"videoId": "v1"}},
                    {
                        "continuationItemRenderer": {
                            "continuationEndpoint": {
                                "continuationCommand": {"token": "T1"}
                            }
                        }
                    },
                ]
            }
            results = AsyncSearchResults(PagingClient(), first, max_results=2)
            items = [item async for item in results]
            assert [i.video_id for i in items if hasattr(i, "video_id")] == [
                "v1",
                "v2",
            ]

        _run(body())

    def test_to_json_export(self) -> None:
        async def body() -> None:
            first = {"contents": [{"videoRenderer": {"videoId": "v1"}}]}
            results = AsyncSearchResults(FakeAsyncClient(), first, max_results=1)
            parsed = json.loads(await results.to_json())
            assert parsed[0]["video_id"] == "v1"
            csv_text = await results.to_csv()
            assert "video_id" in csv_text

        _run(body())


class TestAsyncNavigation:
    def test_bound_helpers_are_awaitable(self) -> None:
        async def body() -> None:
            client = FakeAsyncClient()
            yt = AsyncYouTube(client=client)  # type: ignore[arg-type]
            results = await yt.search("python")
            video = await anext(aiter(results))
            video = replace(video, video_id="dQw4w9WgXcQ")
            details = await video.details()
            assert isinstance(details, VideoDetails)
            channel = await yt.channel("UCuAXFkgsw1L7xaCfnd5JJOw")
            videos = await channel.videos(max_results=5)
            assert [v async for v in videos] == []
            assert client.browse_calls[-1]["params"] is not None

        _run(body())
