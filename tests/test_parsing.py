"""Tests for the low-level parsing helpers."""

from __future__ import annotations

from ytscrape import Channel, Playlist, Video
from ytscrape.parsing import find_continuation, iter_renderers, parse_item


class TestFindContinuation:
    def test_modern_continuation_command(self) -> None:
        obj = {"a": {"continuationCommand": {"token": "TOKEN123"}}}
        assert find_continuation(obj) == "TOKEN123"

    def test_legacy_continuation(self) -> None:
        obj = {"x": [{"nextContinuationData": {"continuation": "LEGACY"}}]}
        assert find_continuation(obj) == "LEGACY"

    def test_deeply_nested(self) -> None:
        obj = {
            "level1": {
                "level2": [{"level3": {"continuationCommand": {"token": "DEEP"}}}]
            }
        }
        assert find_continuation(obj) == "DEEP"

    def test_returns_none_when_absent(self) -> None:
        assert find_continuation({"foo": "bar", "list": [1, 2, 3]}) is None

    def test_returns_none_for_scalar(self) -> None:
        assert find_continuation("just a string") is None


class TestIterRenderers:
    def test_yields_known_renderers(self) -> None:
        response = {
            "contents": [
                {"videoRenderer": {"videoId": "v1"}},
                {"channelRenderer": {"channelId": "c1"}},
                {"playlistRenderer": {"playlistId": "p1"}},
            ]
        }
        pairs = list(iter_renderers(response))
        keys = [key for key, _ in pairs]
        assert keys == ["videoRenderer", "channelRenderer", "playlistRenderer"]

    def test_yields_lockup(self) -> None:
        response = {"items": [{"lockupViewModel": {"contentId": "x"}}]}
        pairs = list(iter_renderers(response))
        assert pairs == [("lockupViewModel", {"contentId": "x"})]

    def test_ignores_unknown_keys(self) -> None:
        response = {"somethingRenderer": {"foo": "bar"}}
        assert list(iter_renderers(response)) == []


class TestParseItem:
    def test_parses_video_renderer(self) -> None:
        item = parse_item("videoRenderer", {"videoId": "abc"})
        assert isinstance(item, Video)
        assert item.video_id == "abc"

    def test_parses_channel_renderer(self) -> None:
        item = parse_item("channelRenderer", {"channelId": "UC1"})
        assert isinstance(item, Channel)

    def test_parses_playlist_renderer(self) -> None:
        item = parse_item("playlistRenderer", {"playlistId": "PL1"})
        assert isinstance(item, Playlist)

    def test_unknown_renderer_returns_none(self) -> None:
        assert parse_item("mysteryRenderer", {}) is None

    def test_lockup_video(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_VIDEO", "contentId": "v"},
        )
        assert isinstance(item, Video)

    def test_lockup_channel(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_CHANNEL", "contentId": "c"},
        )
        assert isinstance(item, Channel)

    def test_lockup_playlist(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_PLAYLIST", "contentId": "p"},
        )
        assert isinstance(item, Playlist)

    def test_lockup_unknown_type_returns_none(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_ALIEN", "contentId": "?"},
        )
        assert item is None
