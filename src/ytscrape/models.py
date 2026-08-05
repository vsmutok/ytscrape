"""Data models representing YouTube entities.

Every model is an immutable :func:`~dataclasses.dataclass` that knows how to
build itself from the raw renderer dictionaries returned by the YouTube
InnerTube API. Keeping the "how do I parse a renderer" logic next to the model
follows the *factory method* pattern and keeps the scraper classes free of
parsing details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Video", "Channel", "Playlist", "VideoDetails", "Comment"]


def _text(node: Any) -> str | None:
    """Extract a plain string from a YouTube ``runs``/``simpleText`` node."""
    if not isinstance(node, dict):
        return None
    if "simpleText" in node:
        return node["simpleText"]
    runs = node.get("runs")
    if isinstance(runs, list):
        return "".join(run.get("text", "") for run in runs)
    return None


def _thumbnail(node: Any) -> str | None:
    """Return the URL of the largest thumbnail found under ``node``."""
    if not isinstance(node, dict):
        return None
    thumbs = node.get("thumbnails")
    if isinstance(thumbs, list) and thumbs:
        return thumbs[-1].get("url")
    return None


# --- lockupViewModel helpers -------------------------------------------------
#
# Modern YouTube search responses wrap results in a ``lockupViewModel`` instead
# of the classic ``videoRenderer`` / ``channelRenderer`` / ``playlistRenderer``.
# The helpers below extract the interesting bits from that structure so the
# models can offer a ``from_lockup`` factory alongside ``from_renderer``.


def _lockup_title(lockup: dict[str, Any]) -> str | None:
    """Return the title of a ``lockupViewModel``."""
    meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
    title = meta.get("title")
    if isinstance(title, dict):
        return title.get("content")
    return None


def _lockup_metadata_rows(lockup: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the ``metadataRows`` list of a ``lockupViewModel`` (or empty)."""
    meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
    rows = (
        meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows")
    )
    return rows if isinstance(rows, list) else []


def _lockup_row_texts(row: dict[str, Any]) -> list[str]:
    """Return the plain-text parts of a single metadata row."""
    texts: list[str] = []
    for part in row.get("metadataParts", []) or []:
        text = part.get("text")
        if isinstance(text, dict) and text.get("content"):
            texts.append(text["content"])
    return texts


def _lockup_channel(lockup: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(channel_name, channel_id)`` extracted from a lockup, if any."""
    for row in _lockup_metadata_rows(lockup):
        for part in row.get("metadataParts", []) or []:
            text = part.get("text")
            if not isinstance(text, dict):
                continue
            for run in text.get("commandRuns", []) or []:
                browse = (
                    run.get("onTap", {})
                    .get("innertubeCommand", {})
                    .get("browseEndpoint", {})
                )
                browse_id = browse.get("browseId")
                if isinstance(browse_id, str) and browse_id.startswith("UC"):
                    return text.get("content"), browse_id
    return None, None


def _lockup_thumbnail(lockup: dict[str, Any]) -> str | None:
    """Return the largest thumbnail URL found inside a ``lockupViewModel``."""
    best: str | None = None

    def _walk(node: Any) -> None:
        nonlocal best
        if isinstance(node, dict):
            sources = node.get("sources")
            if isinstance(sources, list):
                for src in sources:
                    url = src.get("url") if isinstance(src, dict) else None
                    if isinstance(url, str) and url.startswith("http"):
                        best = url
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(lockup.get("contentImage"))
    return best


@dataclass(frozen=True, slots=True)
class Video:
    """A single video result from a search or channel listing."""

    video_id: str
    title: str | None = None
    channel: str | None = None
    channel_id: str | None = None
    duration: str | None = None
    views: str | None = None
    published: str | None = None
    thumbnail: str | None = None

    @property
    def url(self) -> str:
        """Canonical watch URL for the video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @classmethod
    def from_renderer(cls, renderer: dict[str, Any]) -> Video:
        """Build a :class:`Video` from a ``videoRenderer`` dictionary."""
        owner = renderer.get("ownerText") or renderer.get("longBylineText")
        channel_id = None
        runs = (owner or {}).get("runs") if isinstance(owner, dict) else None
        if runs:
            nav = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {})
            channel_id = nav.get("browseId")
        return cls(
            video_id=renderer.get("videoId", ""),
            title=_text(renderer.get("title")),
            channel=_text(owner),
            channel_id=channel_id,
            duration=_text(renderer.get("lengthText")),
            views=_text(renderer.get("viewCountText")),
            published=_text(renderer.get("publishedTimeText")),
            thumbnail=_thumbnail(renderer.get("thumbnail")),
        )

    @classmethod
    def from_lockup(cls, lockup: dict[str, Any]) -> Video:
        """Build a :class:`Video` from a ``lockupViewModel`` dictionary.

        Used for the modern search response format where the ``contentType``
        is ``LOCKUP_CONTENT_TYPE_VIDEO``.
        """
        channel, channel_id = _lockup_channel(lockup)
        return cls(
            video_id=lockup.get("contentId", ""),
            title=_lockup_title(lockup),
            channel=channel,
            channel_id=channel_id,
            thumbnail=_lockup_thumbnail(lockup),
        )


@dataclass(frozen=True, slots=True)
class Channel:
    """A single channel result from a search."""

    channel_id: str
    title: str | None = None
    handle: str | None = None
    subscribers: str | None = None
    video_count: str | None = None
    thumbnail: str | None = None

    @property
    def url(self) -> str:
        """Canonical channel URL."""
        return f"https://www.youtube.com/channel/{self.channel_id}"

    @classmethod
    def from_renderer(cls, renderer: dict[str, Any]) -> Channel:
        """Build a :class:`Channel` from a ``channelRenderer`` dictionary."""
        return cls(
            channel_id=renderer.get("channelId", ""),
            title=_text(renderer.get("title")),
            handle=_text(renderer.get("subscriberCountText"))
            if "@" in (_text(renderer.get("subscriberCountText")) or "")
            else _text(renderer.get("navigationEndpoint")),
            subscribers=_text(renderer.get("videoCountText")),
            video_count=_text(renderer.get("videoCountText")),
            thumbnail=_thumbnail(renderer.get("thumbnail")),
        )

    @classmethod
    def from_lockup(cls, lockup: dict[str, Any]) -> Channel:
        """Build a :class:`Channel` from a ``lockupViewModel`` dictionary.

        Used for the modern search response format where the ``contentType``
        is ``LOCKUP_CONTENT_TYPE_CHANNEL``.
        """
        rows = _lockup_metadata_rows(lockup)
        # The first metadata row typically holds the subscriber / video count.
        subscribers = None
        if rows:
            texts = _lockup_row_texts(rows[0])
            subscribers = texts[0] if texts else None
        return cls(
            channel_id=lockup.get("contentId", ""),
            title=_lockup_title(lockup),
            subscribers=subscribers,
            thumbnail=_lockup_thumbnail(lockup),
        )


@dataclass(frozen=True, slots=True)
class Playlist:
    """A single playlist result from a search."""

    playlist_id: str
    title: str | None = None
    channel: str | None = None
    video_count: str | None = None
    thumbnail: str | None = None

    @property
    def url(self) -> str:
        """Canonical playlist URL."""
        return f"https://www.youtube.com/playlist?list={self.playlist_id}"

    @classmethod
    def from_renderer(cls, renderer: dict[str, Any]) -> Playlist:
        """Build a :class:`Playlist` from a ``playlistRenderer`` dictionary."""
        return cls(
            playlist_id=renderer.get("playlistId", ""),
            title=_text(renderer.get("title")),
            channel=_text(renderer.get("longBylineText")),
            video_count=renderer.get("videoCount"),
            thumbnail=_thumbnail(renderer.get("thumbnail")),
        )

    @classmethod
    def from_lockup(cls, lockup: dict[str, Any]) -> Playlist:
        """Build a :class:`Playlist` from a ``lockupViewModel`` dictionary.

        Used for the modern search response format where the ``contentType``
        is ``LOCKUP_CONTENT_TYPE_PLAYLIST``.
        """
        channel, _ = _lockup_channel(lockup)
        return cls(
            playlist_id=lockup.get("contentId", ""),
            title=_lockup_title(lockup),
            channel=channel,
            thumbnail=_lockup_thumbnail(lockup),
        )


@dataclass(frozen=True, slots=True)
class VideoDetails:
    """Detailed metadata about a single video fetched by id/URL."""

    video_id: str
    title: str | None = None
    description: str | None = None
    channel: str | None = None
    channel_id: str | None = None
    length_seconds: int | None = None
    views: int | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    is_live: bool = False
    thumbnail: str | None = None

    @property
    def url(self) -> str:
        """Canonical watch URL for the video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @classmethod
    def from_player_response(cls, data: dict[str, Any]) -> VideoDetails:
        """Build :class:`VideoDetails` from a ``player`` endpoint response."""
        details = data.get("videoDetails", {})

        def _int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        return cls(
            video_id=details.get("videoId", ""),
            title=details.get("title"),
            description=details.get("shortDescription"),
            channel=details.get("author"),
            channel_id=details.get("channelId"),
            length_seconds=_int(details.get("lengthSeconds")),
            views=_int(details.get("viewCount")),
            keywords=tuple(details.get("keywords", []) or ()),
            is_live=bool(details.get("isLiveContent", False)),
            thumbnail=_thumbnail(details.get("thumbnail")),
        )


def _int_or_none(value: Any) -> int | None:
    """Best-effort parse of an int from a value that may be ``None``/text."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class Comment:
    """A single comment (top-level or reply) on a video."""

    comment_id: str
    text: str | None = None
    author: str | None = None
    author_channel_id: str | None = None
    author_thumbnail: str | None = None
    published: str | None = None
    like_count: int | None = None
    like_count_text: str | None = None
    reply_count: int | None = None
    reply_count_text: str | None = None
    heart: bool = False
    is_reply: bool = False

    @classmethod
    def from_entity_payload(
        cls,
        payload: dict[str, Any],
        *,
        is_reply: bool = False,
        heart: bool = False,
    ) -> Comment:
        """Build a :class:`Comment` from a modern ``commentEntityPayload``.

        This is the shape used by the current ``next`` endpoint responses,
        where comments live in ``frameworkUpdates`` mutations and are
        referenced from ``commentViewModel`` renderers. ``heart`` reflects
        whether the video's creator hearted the comment; it lives in a separate
        toolbar-state mutation, so the caller resolves it and passes it in.
        """
        props = payload.get("properties", {}) or {}
        author = payload.get("author", {}) or {}
        toolbar = payload.get("toolbar", {}) or {}

        content = props.get("content", {})
        text = content.get("content") if isinstance(content, dict) else None

        avatar = author.get("avatarThumbnailUrl")

        like_text = _count_text(
            toolbar.get("likeCountNotliked") or toolbar.get("likeCountLiked")
        )
        reply_text = _count_text(toolbar.get("replyCount"))

        return cls(
            comment_id=props.get("commentId", ""),
            text=text,
            author=author.get("displayName"),
            author_channel_id=author.get("channelId"),
            author_thumbnail=avatar if isinstance(avatar, str) else None,
            published=props.get("publishedTime"),
            like_count=_int_or_none(toolbar.get("likeCountNotliked") or None)
            or _parse_count(toolbar.get("likeCountLiked")),
            like_count_text=like_text,
            reply_count=_parse_count(toolbar.get("replyCount")),
            reply_count_text=reply_text,
            heart=heart,
            is_reply=is_reply,
        )

    @classmethod
    def from_renderer(
        cls,
        renderer: dict[str, Any],
        *,
        is_reply: bool = False,
        heart: bool = False,
    ) -> Comment:
        """Build a :class:`Comment` from a classic ``commentRenderer``."""
        author_endpoint = renderer.get("authorEndpoint", {}).get("browseEndpoint", {})
        vote_count = renderer.get("voteCount")
        like_text = (
            _count_text(_text(vote_count))
            if isinstance(vote_count, dict)
            else _count_text(renderer.get("likeCount"))
        )
        return cls(
            comment_id=renderer.get("commentId", ""),
            text=_text(renderer.get("contentText")),
            author=_text(renderer.get("authorText")),
            author_channel_id=author_endpoint.get("browseId"),
            author_thumbnail=_thumbnail(renderer.get("authorThumbnail")),
            published=_text(renderer.get("publishedTimeText")),
            like_count=_parse_count(vote_count)
            if isinstance(vote_count, dict)
            else _int_or_none(renderer.get("likeCount")),
            like_count_text=like_text,
            reply_count=_int_or_none(renderer.get("replyCount")),
            reply_count_text=_count_text(renderer.get("replyCount")),
            heart=heart or bool(renderer.get("isHearted", False)),
            is_reply=is_reply,
        )


def _parse_count(value: Any) -> int | None:
    """Parse a like/reply count that may be a plain number or a text node.

    YouTube exposes these counts either as an integer-ish string
    (``"1.2K"``, ``"42"``) or as a ``runs``/``simpleText`` node. Non-numeric
    abbreviations such as ``"1.2K"`` are left as ``None`` because they cannot
    be represented exactly as an ``int``.
    """
    if isinstance(value, dict):
        value = _text(value)
    return _int_or_none(value)


def _count_text(value: Any) -> str | None:
    """Return a like/reply count as its raw display string.

    Unlike :func:`_parse_count`, this keeps YouTube's exact rendering,
    including abbreviations such as ``"1.2K"`` or ``"894"``. A ``runs`` /
    ``simpleText`` node is flattened to plain text first; empty strings and
    missing values collapse to ``None``.
    """
    if isinstance(value, dict):
        value = _text(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None
