"""Helpers that turn raw InnerTube JSON into models and continuation tokens.

These functions encapsulate the (sometimes brittle) knowledge of where inside
YouTube's deeply nested responses the interesting data lives, so the rest of
the package can stay declarative.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .models import Channel, Playlist, Video

__all__ = ["find_continuation", "iter_renderers", "parse_item"]

# Maps a (classic) renderer key to the model responsible for parsing it.
_RENDERER_FACTORIES = {
    "videoRenderer": Video.from_renderer,
    "channelRenderer": Channel.from_renderer,
    "playlistRenderer": Playlist.from_renderer,
}

# Key used by the modern search response format.
_LOCKUP_KEY = "lockupViewModel"

# Maps a ``lockupViewModel.contentType`` to the model that parses it.
_LOCKUP_FACTORIES = {
    "LOCKUP_CONTENT_TYPE_VIDEO": Video.from_lockup,
    "LOCKUP_CONTENT_TYPE_CHANNEL": Channel.from_lockup,
    "LOCKUP_CONTENT_TYPE_PLAYLIST": Playlist.from_lockup,
}


def find_continuation(obj: Any) -> str | None:
    """Recursively search ``obj`` for a continuation token.

    Handles both the modern ``continuationCommand.token`` shape and the older
    ``nextContinuationData.continuation`` shape.
    """
    if isinstance(obj, dict):
        command = obj.get("continuationCommand")
        if isinstance(command, dict) and "token" in command:
            return command["token"]

        legacy = obj.get("nextContinuationData")
        if isinstance(legacy, dict) and "continuation" in legacy:
            return legacy["continuation"]

        for value in obj.values():
            token = find_continuation(value)
            if token:
                return token
    elif isinstance(obj, list):
        for item in obj:
            token = find_continuation(item)
            if token:
                return token
    return None


def iter_renderers(
    response: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(renderer_key, renderer)`` pairs contained in ``response``.

    This walks the response tree looking for the known renderer keys, which
    makes it resilient to whether the data came from the first page
    (``twoColumnSearchResultsRenderer``) or a continuation
    (``appendContinuationItemsAction``).
    """

    def _walk(node: Any) -> Iterator[tuple[str, dict[str, Any]]]:
        if isinstance(node, dict):
            for key in _RENDERER_FACTORIES:
                if key in node and isinstance(node[key], dict):
                    yield key, node[key]
            if _LOCKUP_KEY in node and isinstance(node[_LOCKUP_KEY], dict):
                yield _LOCKUP_KEY, node[_LOCKUP_KEY]
            for value in node.values():
                yield from _walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from _walk(item)

    yield from _walk(response)


def parse_item(renderer_key: str, renderer: dict[str, Any]):
    """Build the appropriate model for ``renderer_key``.

    Handles both the classic ``*Renderer`` keys and the modern
    ``lockupViewModel`` (dispatched by its ``contentType``). Returns ``None``
    for unknown types so callers can skip them.
    """
    if renderer_key == _LOCKUP_KEY:
        factory = _LOCKUP_FACTORIES.get(renderer.get("contentType", ""))
        return factory(renderer) if factory is not None else None

    factory = _RENDERER_FACTORIES.get(renderer_key)
    if factory is None:
        return None
    return factory(renderer)
