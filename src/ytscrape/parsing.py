"""Helpers that turn raw InnerTube JSON into models and continuation tokens.

These functions encapsulate the (sometimes brittle) knowledge of where inside
YouTube's deeply nested responses the interesting data lives, so the rest of
the package can stay declarative.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .models import Channel, Comment, Playlist, Video

__all__ = [
    "find_continuation",
    "iter_renderers",
    "parse_item",
    "find_comments_continuation",
    "find_comments_sort_continuation",
    "find_next_comments_continuation",
    "find_reply_continuations",
    "parse_comments_page",
]

# Maps a renderer key to the model responsible for parsing it.
_RENDERER_FACTORIES = {
    "videoRenderer": Video.from_renderer,
    "channelRenderer": Channel.from_renderer,
    "playlistRenderer": Playlist.from_renderer,
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
            for value in node.values():
                yield from _walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from _walk(item)

    yield from _walk(response)


def parse_item(renderer_key: str, renderer: dict[str, Any]):
    """Build the appropriate model for ``renderer_key``.

    Returns ``None`` for unknown types so callers can skip them.
    """
    factory = _RENDERER_FACTORIES.get(renderer_key)
    if factory is None:
        return None
    return factory(renderer)


# --- comments ----------------------------------------------------------------
#
# Comments are served by the ``next`` endpoint. The first ``next`` call (with a
# ``videoId``) returns the watch page, which carries a continuation token that
# opens the comment section. Subsequent calls (with that ``continuation``)
# return the comment threads plus a token for the next page.


def find_comments_continuation(response: Any) -> str | None:
    """Find the continuation token that opens the comments section.

    Scans a ``next`` (watch page) response for an ``itemSectionRenderer`` whose
    ``sectionIdentifier`` is ``comment-item-section`` (the comments feed) and
    returns its continuation token. Falls back to any continuation token found
    when the marker is absent.
    """

    def _walk(node: Any) -> str | None:
        if isinstance(node, dict):
            section = node.get("itemSectionRenderer")
            if (
                isinstance(section, dict)
                and section.get("sectionIdentifier") == "comment-item-section"
            ):
                token = find_continuation(section)
                if token:
                    return token
            for value in node.values():
                token = _walk(value)
                if token:
                    return token
        elif isinstance(node, list):
            for item in node:
                token = _walk(item)
                if token:
                    return token
        return None

    return _walk(response)


def _submenu_item_token(item: Any) -> str | None:
    """Return the continuation token carried by one sort-menu item."""
    if not isinstance(item, dict):
        return None
    endpoint = item.get("serviceEndpoint", item.get("navigationEndpoint", {}))
    return find_continuation(endpoint) if isinstance(endpoint, dict) else None


def find_comments_sort_continuation(
    response: Any, *, title: str | None = None, index: int | None = None
) -> str | None:
    """Find the continuation token that re-opens comments in a given sort order.

    The first comments page carries a ``sortFilterSubMenuRenderer`` with one
    item per sort order (``Top comments``, ``Newest first``). Each item embeds
    its own continuation token, so switching order is a matter of following the
    right item's token.

    The menu is localised, so the desired item is matched first by its English
    ``title`` and, failing that, by ``index`` (its position in the menu). When
    neither is provided (or the requested item is the one already selected),
    ``None`` is returned so the caller can keep using the current page.
    """

    def _find_menu(node: Any) -> dict[str, Any] | None:
        if isinstance(node, dict):
            menu = node.get("sortFilterSubMenuRenderer")
            if isinstance(menu, dict):
                return menu
            for value in node.values():
                found = _find_menu(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _find_menu(item)
                if found is not None:
                    return found
        return None

    menu = _find_menu(response)
    if menu is None:
        return None
    items = menu.get("subMenuItems")
    if not isinstance(items, list):
        return None

    # Prefer an exact title match; fall back to the item's position.
    if title is not None:
        for item in items:
            if isinstance(item, dict) and item.get("title") == title:
                if item.get("selected"):
                    return None
                return _submenu_item_token(item)
    if index is not None and 0 <= index < len(items):
        item = items[index]
        if isinstance(item, dict) and not item.get("selected"):
            return _submenu_item_token(item)
    return None


# Keys under which YouTube nests the list of comment items together with the
# trailing ``continuationItemRenderer`` that points at the *next* comments page.
_COMMENT_ITEMS_COMMANDS = (
    "reloadContinuationItemsCommand",
    "appendContinuationItemsAction",
)


def find_next_comments_continuation(response: Any) -> str | None:
    """Find the token that loads the *next page* of comments.

    A comments ``next`` response is littered with continuation tokens: a
    sort/reload menu token (which reloads the **same** page) and one reply
    token per comment (which loads a thread's replies). Using a generic
    :func:`find_continuation` here therefore grabs the wrong token and makes
    pagination loop over the same comments forever.

    The genuine "next page" token lives in the ``continuationItemRenderer``
    that YouTube appends as the last entry of the comment-items list carried by
    ``reloadContinuationItemsCommand`` / ``appendContinuationItemsAction``. This
    function locates that list and returns only that token, ignoring the sort
    and per-comment reply tokens.
    """

    def _token_from_items(items: Any) -> str | None:
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            renderer = item.get("continuationItemRenderer")
            if isinstance(renderer, dict):
                token = find_continuation(renderer)
                if token:
                    return token
        return None

    def _walk(node: Any) -> str | None:
        if isinstance(node, dict):
            for key in _COMMENT_ITEMS_COMMANDS:
                command = node.get(key)
                if isinstance(command, dict):
                    token = _token_from_items(command.get("continuationItems"))
                    if token:
                        return token
            for value in node.values():
                token = _walk(value)
                if token:
                    return token
        elif isinstance(node, list):
            for item in node:
                token = _walk(item)
                if token:
                    return token
        return None

    return _walk(response)


def _thread_comment_id(thread: dict[str, Any]) -> str | None:
    """Return the top-level comment id of a ``commentThreadRenderer``."""

    def _walk(node: Any) -> str | None:
        if isinstance(node, dict):
            # Don't descend into the replies branch: we want the *parent* id.
            if "commentRepliesRenderer" in node:
                return None
            view_model = node.get("commentViewModel")
            if isinstance(view_model, dict):
                inner = view_model.get("commentViewModel", view_model)
                if isinstance(inner, dict) and inner.get("commentId"):
                    return inner["commentId"]
            renderer = node.get("commentRenderer")
            if isinstance(renderer, dict) and renderer.get("commentId"):
                return renderer["commentId"]
            for key, value in node.items():
                if key == "replies":
                    continue
                found = _walk(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found:
                    return found
        return None

    return _walk(thread)


def find_reply_continuations(response: Any) -> list[tuple[str | None, str]]:
    """Collect the reply-continuation token of every comment thread on a page.

    Each top-level comment that has replies carries its own continuation token
    under ``commentThreadRenderer.replies.commentRepliesRenderer``. Fetching
    that token via the ``next`` endpoint returns the thread's replies (and, in
    turn, a token for the next page of replies).

    Returns ``(parent_comment_id, token)`` pairs in document order so callers
    can insert each thread's replies right after the comment they belong to;
    threads without replies contribute nothing. ``parent_comment_id`` is
    ``None`` when the parent id cannot be determined.
    """
    pairs: list[tuple[str | None, str]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            thread = node.get("commentThreadRenderer")
            if isinstance(thread, dict):
                replies = thread.get("replies")
                token = (
                    find_continuation(replies) if isinstance(replies, dict) else None
                )
                if token:
                    pairs.append((_thread_comment_id(thread), token))
                    # The token has been captured; still descend to catch any
                    # deeper nested threads, but skip this thread's own replies.
                    for key, value in thread.items():
                        if key != "replies":
                            _walk(value)
                    return
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(response)
    return pairs


def _entity_payloads(response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map ``commentId`` -> ``commentEntityPayload`` from framework mutations.

    Modern comment responses keep the actual comment data in
    ``frameworkUpdates.entityBatchUpdate.mutations`` and only reference it by
    key from the ``commentViewModel`` renderers.
    """
    payloads: dict[str, dict[str, Any]] = {}
    mutations = (
        response.get("frameworkUpdates", {})
        .get("entityBatchUpdate", {})
        .get("mutations", [])
    )
    if not isinstance(mutations, list):
        return payloads
    for mutation in mutations:
        entity = mutation.get("payload", {}) if isinstance(mutation, dict) else {}
        payload = entity.get("commentEntityPayload")
        if isinstance(payload, dict):
            comment_id = payload.get("properties", {}).get("commentId")
            if comment_id:
                payloads[comment_id] = payload
    return payloads


def _hearted_toolbar_keys(response: dict[str, Any]) -> set[str]:
    """Return the set of toolbar-state keys whose comment was hearted.

    Whether the creator hearted a comment is not stored on the comment entity
    itself but in a sibling ``engagementToolbarStateEntityPayload`` mutation
    (``heartState``). Each comment references its toolbar state through the
    shared ``toolbarStateKey``, so callers can look a comment up by that key.
    """
    hearted: set[str] = set()
    mutations = (
        response.get("frameworkUpdates", {})
        .get("entityBatchUpdate", {})
        .get("mutations", [])
    )
    if not isinstance(mutations, list):
        return hearted
    for mutation in mutations:
        entity = mutation.get("payload", {}) if isinstance(mutation, dict) else {}
        state = entity.get("engagementToolbarStateEntityPayload")
        if not isinstance(state, dict):
            continue
        if state.get("heartState") == "TOOLBAR_HEART_STATE_HEARTED":
            key = state.get("key")
            if isinstance(key, str):
                hearted.add(key)
    return hearted


def parse_comments_page(
    response: dict[str, Any], *, force_reply: bool = False
) -> list[Comment]:
    """Extract every comment (and reply) contained in a comments ``next`` page.

    Handles both the modern ``commentViewModel`` + ``commentEntityPayload``
    shape and the classic ``commentRenderer`` shape, so the caller gets a flat
    list of :class:`~ytscrape.models.Comment` objects regardless of format.

    When ``force_reply`` is ``True`` every comment on the page is marked as a
    reply. This is needed for reply pages fetched via a thread's reply token:
    those responses list the replies directly (not nested under a ``replies``
    key), so the ``is_reply`` flag cannot be inferred from the structure alone.
    """
    payloads = _entity_payloads(response)
    hearted_keys = _hearted_toolbar_keys(response)
    comments: list[Comment] = []
    seen: set[str] = set()

    def _is_hearted(payload: dict[str, Any]) -> bool:
        key = payload.get("properties", {}).get("toolbarStateKey")
        return isinstance(key, str) and key in hearted_keys

    def _walk(node: Any, *, in_replies: bool) -> None:
        if isinstance(node, dict):
            view_model = node.get("commentViewModel")
            if isinstance(view_model, dict):
                # Newer responses nest an inner ``commentViewModel``.
                inner = view_model.get("commentViewModel", view_model)
                comment_id = inner.get("commentId") if isinstance(inner, dict) else None
                payload = payloads.get(comment_id) if comment_id else None
                if payload is not None and comment_id not in seen:
                    seen.add(comment_id)
                    comments.append(
                        Comment.from_entity_payload(
                            payload,
                            is_reply=in_replies,
                            heart=_is_hearted(payload),
                        )
                    )

            renderer = node.get("commentRenderer")
            if isinstance(renderer, dict):
                comment_id = renderer.get("commentId")
                if comment_id and comment_id not in seen:
                    seen.add(comment_id)
                    comments.append(
                        Comment.from_renderer(renderer, is_reply=in_replies)
                    )

            for key, value in node.items():
                child_in_replies = in_replies or key in _REPLY_KEYS
                _walk(value, in_replies=child_in_replies)
        elif isinstance(node, list):
            for item in node:
                _walk(item, in_replies=in_replies)

    _walk(response, in_replies=force_reply)
    return comments


_REPLY_KEYS = {"commentRepliesRenderer", "replies"}
