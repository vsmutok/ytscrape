"""Tests for the optional MCP server (``ytscrape[mcp]``)."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

mcp = pytest.importorskip("mcp")

from ytscrape import (  # noqa: E402
    ChannelDetails,
    Comment,
    CommentSort,
    ParseError,
    SearchFilter,
    Transcript,
    TranscriptSnippet,
    TranscriptTrack,
    Video,
    VideoDetails,
    YouTube,
)
from ytscrape.mcp_server import (  # noqa: E402
    _MAX_CHARS,
    _MAX_OFFSET,
    _build_parser,
    _encode_cursor,
    _resolve_proxies,
    _transcript_payload,
    build_server,
)

_EXPECTED_TOOLS = {
    "search_videos",
    "get_video",
    "get_channel",
    "get_channel_videos",
    "get_comments",
    "get_transcript",
    "list_transcripts",
}


class FakeYouTube:
    """A :class:`YouTube` stand-in that records the calls tools make."""

    def __init__(self, *, fail_video: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_video = fail_video

    def search(
        self, query: str, *, filter: Any, max_results: int | None = None
    ) -> list[Video]:
        self.calls.append(
            ("search", {"query": query, "filter": filter, "max_results": max_results})
        )
        return [Video(video_id="vid1", title="First", channel="Chan", views=42)]

    def video(self, video: str) -> VideoDetails:
        self.calls.append(("video", {"video": video}))
        if self.fail_video:
            raise ParseError("video unavailable for testing")
        return VideoDetails(video_id="vid1", title="First")

    def channel(self, channel: str) -> ChannelDetails:
        self.calls.append(("channel", {"channel": channel}))
        return ChannelDetails(channel_id="UC123", title="Chan")

    def channel_videos(
        self, channel: str, *, max_results: int | None = None
    ) -> list[Video]:
        self.calls.append(
            ("channel_videos", {"channel": channel, "max_results": max_results})
        )
        return [Video(video_id="vid2", title="Upload")]

    def comments(
        self,
        video: str,
        *,
        max_results: int | None = None,
        include_replies: bool = False,
        sort: Any = CommentSort.TOP,
    ) -> list[Comment]:
        self.calls.append(
            (
                "comments",
                {
                    "video": video,
                    "max_results": max_results,
                    "include_replies": include_replies,
                    "sort": sort,
                },
            )
        )
        return [
            Comment(comment_id="c1", text="top comment", author="A"),
            Comment(comment_id="c2", text="a reply", author="B", is_reply=True),
        ]

    def transcript(
        self,
        video: str,
        *,
        languages: tuple[str, ...] = ("en",),
        preserve_formatting: bool = False,
    ) -> Transcript:
        self.calls.append(
            (
                "transcript",
                {
                    "video": video,
                    "languages": languages,
                    "preserve_formatting": preserve_formatting,
                },
            )
        )
        return Transcript(
            snippets=(
                TranscriptSnippet(text="hello", start=0.0, duration=1.5),
                TranscriptSnippet(text="world", start=1.5, duration=1.0),
            ),
            video_id="vid1",
            language="English",
            language_code="en",
            is_generated=False,
        )

    def transcripts(self, video: str) -> list[TranscriptTrack]:
        self.calls.append(("transcripts", {"video": video}))
        return [
            TranscriptTrack(
                video_id="vid1",
                language="English",
                language_code="en",
                is_generated=False,
                _url="https://example.com/timedtext",
            )
        ]


def _build(fake: FakeYouTube) -> Any:
    return build_server(client=cast(YouTube, fake))


async def _call_tool(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    async with mcp.Client(server) as client:
        return await client.call_tool(name, arguments)


async def _list_tools(server: Any) -> Any:
    async with mcp.Client(server) as client:
        return (await client.list_tools()).tools


def test_all_tools_registered() -> None:
    server = _build(FakeYouTube())
    tools = asyncio.run(_list_tools(server))
    assert {tool.name for tool in tools} == _EXPECTED_TOOLS


def test_tools_are_annotated_read_only() -> None:
    tools = asyncio.run(_list_tools(_build(FakeYouTube())))
    for tool in tools:
        annotations = tool.annotations
        assert annotations is not None, tool.name
        assert annotations.title, tool.name
        assert annotations.read_only_hint is True, tool.name
        assert annotations.destructive_hint is False, tool.name
        assert annotations.idempotent_hint is True, tool.name
        assert annotations.open_world_hint is True, tool.name


def test_search_videos_returns_serialised_results() -> None:
    fake = FakeYouTube()
    result = asyncio.run(_call_tool(_build(fake), "search_videos", {"query": "python"}))
    assert not result.is_error
    items = result.structured_content["items"]
    assert result.structured_content["has_more"] is False
    assert result.structured_content["truncated"] is False
    assert items[0]["title"] == "First"
    assert items[0]["url"] == "https://www.youtube.com/watch?v=vid1"
    assert items[0]["type"] == "video"
    assert fake.calls[0][0] == "search"
    assert fake.calls[0][1]["filter"] is SearchFilter.ALL
    assert fake.calls[0][1]["max_results"] == 11


def test_search_videos_accepts_filter_and_max() -> None:
    fake = FakeYouTube()
    asyncio.run(
        _call_tool(
            _build(fake),
            "search_videos",
            {"query": "python", "filter": "videos", "max_results": 3},
        )
    )
    assert fake.calls[0][1]["filter"] is SearchFilter.VIDEOS
    assert fake.calls[0][1]["max_results"] == 4


def test_get_video_returns_dict() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube()), "get_video", {"video": "vid1"})
    )
    assert result.structured_content["video_id"] == "vid1"
    assert result.structured_content["title"] == "First"
    assert result.structured_content["truncated"] is False
    assert "thumbnails" not in result.structured_content


def test_get_channel_returns_dict() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube()), "get_channel", {"channel": "@chan"})
    )
    assert result.structured_content["channel_id"] == "UC123"


def test_get_channel_videos_returns_list() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube()), "get_channel_videos", {"channel": "@chan"})
    )
    assert result.structured_content["items"][0]["video_id"] == "vid2"
    assert result.structured_content["has_more"] is False


def test_get_comments_passes_sort_and_replies() -> None:
    fake = FakeYouTube()
    result = asyncio.run(
        _call_tool(
            _build(fake),
            "get_comments",
            {"video": "vid1", "sort": "newest", "include_replies": True},
        )
    )
    assert fake.calls[0][1]["sort"] is CommentSort.NEWEST
    assert fake.calls[0][1]["include_replies"] is True
    items = result.structured_content["items"]
    assert [item["is_reply"] for item in items] == [False, True]
    assert result.structured_content["has_more"] is False


def test_get_transcript_text_and_timestamps() -> None:
    fake = FakeYouTube()
    result = asyncio.run(
        _call_tool(
            _build(fake),
            "get_transcript",
            {"video": "vid1", "languages": ["en"], "include_timestamps": True},
        )
    )
    content = result.structured_content
    assert content["text"] == "hello world"
    assert content["language_code"] == "en"
    assert content["snippets"][0]["start"] == 0.0
    assert fake.calls[0][1]["languages"] == ("en",)


def test_get_transcript_omits_snippets_by_default() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube()), "get_transcript", {"video": "vid1"})
    )
    assert "snippets" not in result.structured_content
    assert result.structured_content["truncated"] is False
    assert result.structured_content["has_more"] is False


def test_search_pages_with_cursor_and_caps_max_results() -> None:
    class Many(FakeYouTube):
        def search(
            self, query: str, *, filter: Any, max_results: int | None = None
        ) -> list[Video]:
            self.calls.append(
                (
                    "search",
                    {"query": query, "filter": filter, "max_results": max_results},
                )
            )
            total = 60
            return [Video(video_id=f"v{i}", title=f"T{i}") for i in range(total)]

    fake = Many()
    first = asyncio.run(
        _call_tool(
            _build(fake),
            "search_videos",
            {"query": "python", "max_results": 100},
        )
    )
    page = first.structured_content
    assert page["count"] == 50
    assert page["has_more"] is True
    assert page["truncated"] is False
    assert page["next_cursor"]
    assert "capped at 50" in page["hint"]
    # offset 0 + cap 50 + probe
    assert fake.calls[0][1]["max_results"] == 51

    second = asyncio.run(
        _call_tool(
            _build(fake),
            "search_videos",
            {"query": "python", "max_results": 50, "cursor": page["next_cursor"]},
        )
    )
    assert second.structured_content["items"][0]["video_id"] == "v50"
    assert second.structured_content["has_more"] is False


def test_invalid_cursor_is_a_tool_error() -> None:
    result = asyncio.run(
        _call_tool(
            _build(FakeYouTube()),
            "get_comments",
            {"video": "vid1", "cursor": "not-a-cursor"},
        )
    )
    assert result.is_error
    text = " ".join(block.text for block in result.content)
    assert "Invalid cursor" in text


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("search_videos", {"query": "python"}),
        ("get_channel_videos", {"channel": "@chan"}),
        ("get_comments", {"video": "vid1"}),
    ],
)
def test_cursors_beyond_the_depth_cap_are_rejected(
    tool: str, arguments: dict[str, Any]
) -> None:
    fake = FakeYouTube()
    cursor = _encode_cursor(_MAX_OFFSET + 1)
    result = asyncio.run(
        _call_tool(_build(fake), tool, {**arguments, "cursor": cursor})
    )
    assert result.is_error
    text = " ".join(block.text for block in result.content)
    assert "depth" in text
    assert fake.calls == []


def test_cursor_at_the_depth_cap_is_allowed() -> None:
    fake = FakeYouTube()
    result = asyncio.run(
        _call_tool(
            _build(fake),
            "search_videos",
            {"query": "python", "cursor": _encode_cursor(_MAX_OFFSET)},
        )
    )
    assert not result.is_error
    # offset + default page size + probe
    assert fake.calls[0][1]["max_results"] == _MAX_OFFSET + 11


def test_filter_and_sort_are_enums() -> None:
    listed = asyncio.run(_list_tools(_build(FakeYouTube())))
    tools = {tool.name: tool for tool in listed}
    search_filter = tools["search_videos"].input_schema["properties"]["filter"]
    assert set(search_filter["enum"]) == {
        "all",
        "videos",
        "channels",
        "playlists",
        "shorts",
        "movies",
    }
    sort = tools["get_comments"].input_schema["properties"]["sort"]
    assert set(sort["enum"]) == {"top", "newest"}
    detail = tools["get_video"].input_schema["properties"]["detail"]
    assert set(detail["enum"]) == {"concise", "full"}


def test_transcript_pages_when_text_exceeds_the_cap() -> None:
    snippets = tuple(
        TranscriptSnippet(text="word " * 40, start=float(i), duration=1.0)
        for i in range(400)
    )
    transcript = Transcript(
        snippets=snippets,
        video_id="vid1",
        language="English",
        language_code="en",
        is_generated=True,
    )
    first = _transcript_payload(transcript, include_timestamps=False, cursor=None)
    assert first["truncated"] is True
    assert first["has_more"] is True
    assert len(first["text"]) <= _MAX_CHARS
    assert "next_cursor" in first["hint"]
    second = _transcript_payload(
        transcript, include_timestamps=False, cursor=first["next_cursor"]
    )
    assert second["text"]
    assert second["text"][:20] == first["text"][:20]
    assert second["next_cursor"] != first["next_cursor"]


@pytest.mark.parametrize("include_timestamps", [False, True])
def test_transcript_cut_mid_snippet_reports_truncated(
    include_timestamps: bool,
) -> None:
    # Long enough to be cut and genuinely ending with an ellipsis, which the
    # old endswith-based heuristic mistook for an already-truncated snippet.
    text = "x" * (_MAX_CHARS * 2) + "…"
    transcript = Transcript(
        snippets=(TranscriptSnippet(text=text, start=0.0, duration=1.0),),
        video_id="vid1",
        language="English",
        language_code="en",
        is_generated=True,
    )
    payload = _transcript_payload(
        transcript, include_timestamps=include_timestamps, cursor=None
    )
    assert payload["truncated"] is True
    assert payload["has_more"] is False
    assert payload["next_cursor"] is None
    assert len(payload["text"]) <= _MAX_CHARS
    assert payload["text"].endswith("…")
    assert "not repeated" in payload["hint"]
    if include_timestamps:
        assert payload["snippets"][-1]["text"] == payload["text"]


def test_transcript_ellipsis_is_not_mistaken_for_a_cut() -> None:
    transcript = Transcript(
        snippets=(TranscriptSnippet(text="to be continued…", start=0.0, duration=1.0),),
        video_id="vid1",
        language="English",
        language_code="en",
        is_generated=False,
    )
    payload = _transcript_payload(transcript, include_timestamps=False, cursor=None)
    assert payload["truncated"] is False
    assert payload["has_more"] is False
    assert payload["text"] == "to be continued…"


def test_list_transcripts_returns_tracks() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube()), "list_transcripts", {"video": "vid1"})
    )
    content = result.structured_content
    assert content["count"] == 1
    assert content["has_more"] is False
    assert content["next_cursor"] is None
    assert content["truncated"] is False
    track = content["items"][0]
    assert track["language_code"] == "en"
    assert track["is_translatable"] is False


def _proxies(*argv: str) -> dict[str, str] | None:
    return _resolve_proxies(_build_parser().parse_args(list(argv)))


def test_proxy_flag_applies_to_both_schemes() -> None:
    assert _proxies("--proxy", "http://proxy:8080") == {
        "http": "http://proxy:8080",
        "https": "http://proxy:8080",
    }


def test_per_scheme_proxy_flags() -> None:
    assert _proxies(
        "--http-proxy",
        "http://http-proxy:3128",
        "--https-proxy",
        "https://https-proxy:8443",
    ) == {"http": "http://http-proxy:3128", "https": "https://https-proxy:8443"}


def test_per_scheme_flags_override_proxy() -> None:
    assert _proxies(
        "--proxy", "http://both:8080", "--http-proxy", "http://http-only:3128"
    ) == {"http": "http://http-only:3128", "https": "http://both:8080"}


def test_no_proxy_flags_yield_none() -> None:
    assert _proxies() is None


def test_environment_proxies_apply_when_no_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://env-proxy:8080")
    session = YouTube()._client._session
    merged = session.merge_environment_settings(
        "https://www.youtube.com", {}, None, None, None
    )
    assert merged["proxies"].get("https") == "http://env-proxy:8080"


def test_errors_are_readable() -> None:
    result = asyncio.run(
        _call_tool(_build(FakeYouTube(fail_video=True)), "get_video", {"video": "vid1"})
    )
    assert result.is_error
    text = " ".join(block.text for block in result.content)
    assert "video unavailable for testing" in text
