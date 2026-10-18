"""MCP server exposing ytscrape as Model Context Protocol tools.

Requires the optional ``mcp`` extra::

    pip install "ytscrape[mcp]"

Run over stdio (the transport used by Claude Code, Claude Desktop, Cursor,
VS Code, …)::

    ytscrape-mcp

or as a module::

    python -m ytscrape.mcp_server

For hosted setups the server also speaks Streamable HTTP and SSE::

    ytscrape-mcp --transport streamable-http --host 0.0.0.0 --port 8000

The tools are read-only and map directly to the :class:`~ytscrape.YouTube`
facade: ``search_videos``, ``get_video``, ``get_channel``,
``get_channel_videos``, ``get_comments``, ``get_transcript`` and
``list_transcripts``.
"""

from __future__ import annotations

import argparse
import base64
import json
from collections.abc import Callable, Iterable, Mapping
from functools import wraps
from typing import Any, Literal, TypeVar, cast

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__
from .exceptions import YtScraperError
from .export import to_dict
from .filters import CommentSort, SearchFilter
from .transcripts import Transcript
from .youtube import YouTube

__all__ = ["build_server", "main"]

_F = TypeVar("_F", bound=Callable[..., Any])

# Hard ceiling so one tool call cannot fill an agent's context window.
# max_results above this is clamped; the response says so via ``hint``.
_MAX_RESULTS = 50
_MAX_CHARS = 16_000
_DESCRIPTION_PREVIEW = 400

SearchFilterName = Literal["all", "videos", "channels", "playlists", "shorts", "movies"]
CommentSortName = Literal["top", "newest"]
DetailLevel = Literal["concise", "full"]

_VIDEO_CONCISE = (
    "video_id",
    "url",
    "title",
    "channel",
    "channel_id",
    "length_seconds",
    "views",
    "is_live",
    "is_upcoming",
    "published",
    "published_at",
    "scheduled_at",
    "category",
)
_CHANNEL_CONCISE = (
    "channel_id",
    "url",
    "title",
    "handle",
    "subscribers",
    "video_count",
    "view_count",
    "country",
)
_BULKY_KEYS = (
    "thumbnails",
    "available_countries",
    "keywords",
    "tags",
    "links",
    "description",
)


def _read_only(title: str) -> ToolAnnotations:
    """Annotations for a read-only tool that queries the open web."""
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )


def _translate_errors(fn: _F) -> _F:
    """Surface ytscrape errors to MCP clients as readable tool errors."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except YtScraperError as exc:
            raise ToolError(str(exc)) from exc

    return cast(_F, wrapper)


_SERVER_INSTRUCTIONS = (
    "Scrape public YouTube data without an API key. Use search_videos to find "
    "videos, get_video / get_channel / get_channel_videos for metadata, "
    "get_comments for comments (sort='newest' collects every comment, "
    "include_replies adds replies) and get_transcript / list_transcripts for "
    "captions. List tools return items plus has_more and next_cursor — pass "
    "next_cursor to continue instead of raising max_results (capped at 50). "
    "Responses are truncated to fit a context window (truncated=true plus a "
    "hint). get_video / get_channel default to detail='concise'; pass "
    "detail='full' only when you need the rest. All tools are read-only."
)


def _encode_cursor(offset: int) -> str:
    raw = f"o:{offset}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    """Decode an opaque ``next_cursor`` into a non-negative offset."""
    if not cursor:
        return 0
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        text = base64.urlsafe_b64decode(padded).decode()
        kind, value = text.split(":", 1)
        if kind != "o":
            raise ValueError
        offset = int(value)
    except (ValueError, UnicodeError) as exc:
        raise ToolError(
            "Invalid cursor. Pass next_cursor from the previous response unchanged."
        ) from exc
    if offset < 0:
        raise ToolError("Invalid cursor.")
    return offset


def _clamp_max_results(max_results: int) -> tuple[int, str | None]:
    if max_results < 1:
        raise ToolError("max_results must be at least 1.")
    if max_results > _MAX_RESULTS:
        return _MAX_RESULTS, (
            f"max_results was capped at {_MAX_RESULTS}. "
            "Pass next_cursor to fetch the next page instead of raising the limit."
        )
    return max_results, None


def _json_len(payload: Any) -> int:
    return len(json.dumps(payload, ensure_ascii=False, default=str))


def _join_hints(*hints: str | None) -> str | None:
    parts = [hint for hint in hints if hint]
    return " ".join(parts) or None


def _page(
    items: Iterable[Any],
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[Any], bool, str | None]:
    """Take one page and report whether another page exists.

    The iterable must already be capped at ``offset + limit + 1`` so the extra
    item is the ``has_more`` probe and YouTube is not walked to the end.
    """
    offset = _decode_cursor(cursor)
    page: list[Any] = []
    has_more = False
    for index, item in enumerate(items):
        if index < offset:
            continue
        if len(page) < limit:
            page.append(item)
            continue
        has_more = True
        break
    next_cursor = _encode_cursor(offset + len(page)) if has_more else None
    return page, has_more, next_cursor


def _list_item(item: Any) -> dict[str, Any]:
    """Serialise a list row without bulky fields that blow the page budget."""
    data = to_dict(item)
    for key in ("thumbnails", "keywords", "description", "available_countries", "tags"):
        data.pop(key, None)
    return data


def _fit_items(
    items: list[dict[str, Any]], *, budget: int
) -> tuple[list[dict[str, Any]], bool]:
    """Drop trailing items until the JSON payload fits ``budget``."""
    kept: list[dict[str, Any]] = []
    truncated = False
    for item in items:
        trial = [*kept, item]
        if _json_len(trial) <= budget:
            kept = trial
            continue
        truncated = True
        if not kept:
            kept = [_shrink_mapping(item, budget)]
        break
    return kept, truncated


def _shrink_mapping(data: dict[str, Any], budget: int) -> dict[str, Any]:
    """Drop bulky fields, then shorten the longest string, until it fits."""
    shrunk = dict(data)
    for key in _BULKY_KEYS:
        if _json_len(shrunk) <= budget:
            return shrunk
        shrunk.pop(key, None)
    if _json_len(shrunk) <= budget:
        return shrunk
    longest = max(
        (key for key, value in shrunk.items() if isinstance(value, str)),
        key=lambda key: len(shrunk[key]),
        default=None,
    )
    if longest is not None:
        overflow = _json_len(shrunk) - budget
        keep = max(0, len(shrunk[longest]) - overflow - 1)
        shrunk[longest] = shrunk[longest][:keep] + "…"
    return shrunk


def _project(
    data: dict[str, Any],
    *,
    detail: DetailLevel,
    keep: tuple[str, ...],
) -> tuple[dict[str, Any], bool, str | None]:
    """Return a concise or full mapping that fits the character budget."""
    truncated = False
    hint: str | None = None
    if detail == "concise":
        projected = {key: data[key] for key in keep if key in data}
        description = data.get("description")
        if isinstance(description, str) and description:
            if len(description) > _DESCRIPTION_PREVIEW:
                projected["description"] = description[:_DESCRIPTION_PREVIEW] + "…"
                truncated = True
                hint = (
                    "Description was shortened. Pass detail='full' for the rest "
                    "(still subject to the response size cap)."
                )
            else:
                projected["description"] = description
    else:
        projected = {
            key: value
            for key, value in data.items()
            if key not in {"truncated", "hint"}
        }
        before = _json_len(projected)
        if before > _MAX_CHARS:
            projected = _shrink_mapping(projected, _MAX_CHARS)
            truncated = True
            hint = (
                "Response exceeded the size cap and bulky fields were omitted. "
                "Ask for a specific field instead of the full object."
            )
    if _json_len(projected) > _MAX_CHARS:
        projected = _shrink_mapping(projected, _MAX_CHARS)
        truncated = True
        hint = _join_hints(
            hint,
            "Response was cut to fit the context window.",
        )
    projected["truncated"] = truncated
    if hint:
        projected["hint"] = hint
    return projected, truncated, hint


def _list_payload(
    raw_items: Iterable[Any],
    *,
    cursor: str | None,
    limit: int,
    cap_hint: str | None,
    extra_hint: str | None = None,
) -> dict[str, Any]:
    page, has_more, next_cursor = _page(raw_items, cursor=cursor, limit=limit)
    dicts = [_list_item(item) for item in page]
    fitted, char_truncated = _fit_items(dicts, budget=_MAX_CHARS)
    if char_truncated and fitted:
        # Items dropped for size are still available on the next page.
        has_more = True
        next_cursor = _encode_cursor(_decode_cursor(cursor) + len(fitted))
    hint = _join_hints(
        cap_hint,
        extra_hint,
        (
            "Response was cut to fit the context window. "
            "Lower max_results or omit replies."
            if char_truncated
            else None
        ),
        (
            "More results exist. Pass next_cursor to continue; "
            f"do not raise max_results above {_MAX_RESULTS}."
            if has_more
            else None
        ),
    )
    payload: dict[str, Any] = {
        "items": fitted,
        "count": len(fitted),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "truncated": char_truncated,
    }
    if hint:
        payload["hint"] = hint
    return payload


def _transcript_payload(
    transcript: Transcript,
    *,
    include_timestamps: bool,
    cursor: str | None,
) -> dict[str, Any]:
    """Return one page of caption snippets that fits the character budget."""
    offset = _decode_cursor(cursor)
    snippets = transcript.snippets
    if offset > len(snippets):
        offset = len(snippets)
    kept: list[Any] = []
    parts: list[str] = []
    for snippet in snippets[offset:]:
        piece = snippet.text or ""
        trial = " ".join([*parts, piece] if piece else parts)
        overhead = 800 if include_timestamps else 400
        if parts and len(trial) + overhead > _MAX_CHARS:
            break
        if not parts and len(piece) + overhead > _MAX_CHARS:
            piece = piece[: _MAX_CHARS - overhead] + "…"
            kept.append(snippet)
            parts.append(piece)
            break
        kept.append(snippet)
        if piece:
            parts.append(piece)
        if len(" ".join(parts)) + overhead >= _MAX_CHARS:
            break
    consumed = len(kept)
    cut_snippet = bool(
        kept
        and parts
        and parts[-1].endswith("…")
        and not (kept[-1].text or "").endswith("…")
    )
    truncated = cut_snippet or offset + consumed < len(snippets)
    next_cursor = _encode_cursor(offset + consumed) if truncated and consumed else None
    hint = None
    if truncated:
        hint = (
            "Transcript was cut to fit the context window. Pass next_cursor for "
            "the next snippets, keep include_timestamps=false, or narrow languages."
        )
    payload: dict[str, Any] = {
        "video_id": transcript.video_id,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "is_generated": transcript.is_generated,
        "text": " ".join(parts),
        "truncated": truncated,
        "has_more": truncated,
        "next_cursor": next_cursor,
    }
    if include_timestamps:
        payload["snippets"] = [to_dict(snippet) for snippet in kept]
        if truncated and kept and parts and parts[-1].endswith("…"):
            payload["snippets"][-1] = {**payload["snippets"][-1], "text": parts[-1]}
    if hint:
        payload["hint"] = hint
    return payload


def build_server(
    *,
    client: YouTube | None = None,
    language: str = "en",
    region: str = "US",
    timeout: float = 30.0,
    proxies: Mapping[str, str] | None = None,
) -> MCPServer:
    """Build the MCP server with every ytscrape tool registered.

    Args:
        client: A pre-built :class:`~ytscrape.YouTube` facade. When omitted,
            one is created from the keyword arguments below (mainly useful for
            tests and embedding).
        language: Interface language (``hl``) used for requests.
        region: Content region (``gl``) used for requests.
        timeout: Per-request timeout in seconds.
        proxies: Optional ``requests``-style proxy mapping, e.g.
            ``{"https": "http://user:pass@host:8080"}``. When omitted, the
            standard ``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``NO_PROXY`` environment
            variables are honoured by the underlying ``requests`` session.
    """
    yt = client or YouTube(
        language=language, region=region, timeout=timeout, proxies=proxies
    )
    server = MCPServer(
        "ytscrape",
        version=__version__,
        instructions=_SERVER_INSTRUCTIONS,
    )

    @server.tool(annotations=_read_only("Search YouTube"))
    @_translate_errors
    def search_videos(
        query: str,
        filter: SearchFilterName = "all",
        max_results: int = 10,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Search YouTube and return one page of videos, channels or playlists.

        The response is ``{items, count, has_more, next_cursor, truncated}``.
        When ``has_more`` is true, pass ``next_cursor`` back to continue.
        ``max_results`` is capped at 50.

        Args:
            query: The search query.
            filter: Result type: 'all', 'videos', 'channels', 'playlists',
                'shorts' or 'movies'.
            max_results: Page size (1-50).
            cursor: Opaque ``next_cursor`` from the previous page.
        """
        limit, cap_hint = _clamp_max_results(max_results)
        offset = _decode_cursor(cursor)
        results = yt.search(
            query,
            filter=SearchFilter.from_value(filter),
            max_results=offset + limit + 1,
        )
        return _list_payload(results, cursor=cursor, limit=limit, cap_hint=cap_hint)

    @server.tool(annotations=_read_only("Get Video Details"))
    @_translate_errors
    def get_video(
        video: str,
        detail: DetailLevel = "concise",
    ) -> dict[str, Any]:
        """Fetch metadata for a single video.

        Defaults to a concise projection (no thumbnails, keyword lists or
        country lists). Pass detail='full' for the complete object; either
        way the payload is capped and may set truncated=true with a hint.

        Args:
            video: A video id or any YouTube URL that contains one
                ('watch?v=', 'youtu.be/', '/shorts/' and '/embed/').
            detail: 'concise' (default) or 'full'.
        """
        payload, _, _ = _project(
            to_dict(yt.video(video)), detail=detail, keep=_VIDEO_CONCISE
        )
        return payload

    @server.tool(annotations=_read_only("Get Channel Details"))
    @_translate_errors
    def get_channel(
        channel: str,
        detail: DetailLevel = "concise",
    ) -> dict[str, Any]:
        """Fetch metadata for a single channel.

        Defaults to a concise projection. Pass detail='full' for the complete
        object; either way the payload is capped and may set truncated=true
        with a hint.

        Args:
            channel: A channel id ('UC…'), a '@handle', or any YouTube
                channel URL ('/channel/UC…', '/@handle', '/c/…', '/user/…').
            detail: 'concise' (default) or 'full'.
        """
        payload, _, _ = _project(
            to_dict(yt.channel(channel)), detail=detail, keep=_CHANNEL_CONCISE
        )
        return payload

    @server.tool(annotations=_read_only("List Channel Videos"))
    @_translate_errors
    def get_channel_videos(
        channel: str,
        max_results: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """List one page of a channel's uploads (the Videos tab).

        Returns ``{items, count, has_more, next_cursor, truncated}``.
        ``max_results`` is capped at 50; pass ``next_cursor`` to continue.

        Args:
            channel: A channel id, '@handle' or channel URL.
            max_results: Page size (1-50).
            cursor: Opaque ``next_cursor`` from the previous page.
        """
        limit, cap_hint = _clamp_max_results(max_results)
        offset = _decode_cursor(cursor)
        videos = yt.channel_videos(channel, max_results=offset + limit + 1)
        return _list_payload(videos, cursor=cursor, limit=limit, cap_hint=cap_hint)

    @server.tool(annotations=_read_only("Get Video Comments"))
    @_translate_errors
    def get_comments(
        video: str,
        max_results: int = 20,
        sort: CommentSortName = "top",
        include_replies: bool = False,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Collect one page of comments, replies included on request.

        Returns ``{items, count, has_more, next_cursor, truncated}``. When
        ``has_more`` is true the thread was cut — pass ``next_cursor`` instead
        of raising ``max_results`` (capped at 50, replies included in the
        count). YouTube's default 'top' view omits some comments; pass
        sort='newest' to walk every comment. Replies follow their parent and
        carry 'is_reply' set to true.

        Args:
            video: A video id or any YouTube URL that contains one.
            max_results: Page size (1-50). Counts replies when include_replies
                is enabled.
            sort: Comment order: 'top' (default) or 'newest'.
            include_replies: Also collect the replies of every comment.
            cursor: Opaque ``next_cursor`` from the previous page.
        """
        limit, cap_hint = _clamp_max_results(max_results)
        offset = _decode_cursor(cursor)
        thread = yt.comments(
            video,
            max_results=offset + limit + 1,
            include_replies=include_replies,
            sort=CommentSort.from_value(sort),
        )
        return _list_payload(
            thread,
            cursor=cursor,
            limit=limit,
            cap_hint=cap_hint,
            extra_hint=(
                "sort='top' hides some comments; pass sort='newest' to collect "
                "every comment."
                if sort == "top"
                else None
            ),
        )

    @server.tool(annotations=_read_only("Get Transcript"))
    @_translate_errors
    def get_transcript(
        video: str,
        languages: list[str] | None = None,
        include_timestamps: bool = False,
        preserve_formatting: bool = False,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one page of a video transcript (captions) as plain text.

        Languages are tried in order; manually created captions are preferred
        over auto-generated ones. The text is capped; when ``truncated`` is
        true, pass ``next_cursor`` for the next snippets, or set
        include_timestamps to false and narrow ``languages``.

        Args:
            video: A video id or any YouTube URL that contains one.
            languages: Preferred language codes, tried in order.
                Defaults to ['en'].
            include_timestamps: Also return timed snippets of this page
                ('start' and 'duration' in seconds).
            preserve_formatting: Keep basic HTML formatting tags ('<i>',
                '<b>', …) inside snippet text.
            cursor: Opaque ``next_cursor`` from the previous page of snippets.
        """
        transcript = yt.transcript(
            video,
            languages=tuple(languages or ("en",)),
            preserve_formatting=preserve_formatting,
        )
        return _transcript_payload(
            transcript,
            include_timestamps=include_timestamps,
            cursor=cursor,
        )

    @server.tool(annotations=_read_only("List Transcripts"))
    @_translate_errors
    def list_transcripts(video: str) -> list[dict[str, Any]]:
        """List the caption tracks available for a video.

        Use the returned language codes with get_transcript.

        Args:
            video: A video id or any YouTube URL that contains one.
        """
        return [to_dict(track) for track in yt.transcripts(video)]

    return server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytscrape-mcp",
        description="Run the ytscrape MCP server (stdio by default).",
    )
    parser.add_argument(
        "--language",
        default="en",
        metavar="HL",
        help="Interface language (hl), e.g. en, uk, de.",
    )
    parser.add_argument(
        "--region",
        default="US",
        metavar="GL",
        help="Content region / country (gl), e.g. US, UA, DE.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        metavar="URL",
        help=(
            "Route requests through one proxy for both HTTP and HTTPS, e.g. "
            "http://user:pass@host:8080."
        ),
    )
    parser.add_argument(
        "--http-proxy",
        default=None,
        metavar="URL",
        help=(
            "Proxy for HTTP requests (overrides --proxy). When no proxy flags "
            "are given, the HTTP_PROXY environment variable is honoured."
        ),
    )
    parser.add_argument(
        "--https-proxy",
        default=None,
        metavar="URL",
        help=(
            "Proxy for HTTPS requests (overrides --proxy). When no proxy flags "
            "are given, the HTTPS_PROXY environment variable is honoured."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default="stdio",
        help="MCP transport to serve (default: stdio).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transports (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transports (default: 8000).",
    )
    return parser


def _resolve_proxies(args: argparse.Namespace) -> dict[str, str] | None:
    """Build the proxies mapping from CLI arguments.

    Per-scheme flags win over the combined ``--proxy``. When no proxy flag is
    given the mapping is ``None``, letting the underlying ``requests`` session
    fall back to the standard environment variables (``HTTP_PROXY`` /
    ``HTTPS_PROXY`` / ``NO_PROXY``).
    """
    http = args.http_proxy or args.proxy
    https = args.https_proxy or args.proxy
    proxies = {
        scheme: url
        for scheme, url in (("http", http), ("https", https))
        if url is not None
    }
    return proxies or None


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``ytscrape-mcp`` console script."""
    args = _build_parser().parse_args(argv)
    server = build_server(
        language=args.language,
        region=args.region,
        timeout=args.timeout,
        proxies=_resolve_proxies(args),
    )
    match args.transport:
        case "streamable-http":
            server.run("streamable-http", host=args.host, port=args.port)
        case "sse":  # pragma: no cover - exercised in live/hosted setups
            server.run("sse", host=args.host, port=args.port)
        case _:
            server.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
