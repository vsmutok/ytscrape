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
from urllib.parse import parse_qs, unquote, urlparse

__all__ = ["Video", "Channel", "Playlist", "VideoDetails", "ChannelDetails", "Comment"]


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
    sources = node.get("sources")
    if isinstance(sources, list) and sources:
        last = sources[-1]
        if isinstance(last, dict):
            url = last.get("url")
            return url if isinstance(url, str) else None
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


def _split_keyword_string(raw: str | None) -> tuple[str, ...]:
    """Split a channel ``keywords`` string that may contain quoted phrases."""
    if not raw:
        return ()
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    for ch in raw:
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if ch.isspace() and not in_quotes:
            if current:
                parts.append("".join(current))
                current = []
            continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return tuple(part for part in parts if part)


def _header_metadata_texts(data: dict[str, Any]) -> list[str]:
    """Collect plain-text metadata parts from the channel page header."""
    texts: list[str] = []
    try:
        rows = (
            data.get("header", {})
            .get("pageHeaderRenderer", {})
            .get("content", {})
            .get("pageHeaderViewModel", {})
            .get("metadata", {})
            .get("contentMetadataViewModel", {})
            .get("metadataRows", [])
        )
    except AttributeError:
        return texts
    if not isinstance(rows, list):
        return texts
    for row in rows:
        if not isinstance(row, dict):
            continue
        for part in row.get("metadataParts", []) or []:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, dict) and isinstance(text.get("content"), str):
                texts.append(text["content"])
    return texts


def _handle_from_urls(*candidates: Any) -> str | None:
    """Extract an ``@handle`` from vanity / owner URLs when present."""
    for candidate in candidates:
        values: list[Any]
        if isinstance(candidate, list):
            values = candidate
        else:
            values = [candidate]
        for value in values:
            if not isinstance(value, str):
                continue
            marker = value.rstrip("/").rsplit("/", 1)[-1]
            if marker.startswith("@") and len(marker) > 1:
                return marker
    return None


def _page_header_view_model(data: dict[str, Any]) -> dict[str, Any]:
    """Return the channel page header view-model when present."""
    try:
        header = (
            data.get("header", {})
            .get("pageHeaderRenderer", {})
            .get("content", {})
            .get("pageHeaderViewModel", {})
        )
    except AttributeError:
        return {}
    return header if isinstance(header, dict) else {}


def _banner_from_header(data: dict[str, Any]) -> str | None:
    """Largest channel banner URL from the page header, if any."""
    header = _page_header_view_model(data)
    banner = header.get("banner", {})
    if not isinstance(banner, dict):
        return None
    image = banner.get("imageBannerViewModel", {})
    if isinstance(image, dict):
        return _thumbnail(image.get("image"))
    return _thumbnail(banner)


def _find_first(data: Any, key: str) -> Any:
    """Depth-first search for the first value stored under ``key``."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = _find_first(value, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_first(item, key)
            if found is not None:
                return found
    return None


def _about_continuation_token(data: dict[str, Any]) -> str | None:
    """Continuation token used to load the channel About engagement panel."""
    header = _page_header_view_model(data)
    description = header.get("description")
    if not isinstance(description, dict):
        return None

    def _token(node: Any) -> str | None:
        if isinstance(node, dict):
            command = node.get("continuationCommand")
            if isinstance(command, dict):
                token = command.get("token")
                if isinstance(token, str) and token:
                    return token
            for value in node.values():
                found = _token(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _token(item)
                if found is not None:
                    return found
        return None

    return _token(description)


def _content_text(value: Any) -> str | None:
    """Extract plain text from a simple string or ``{content: ...}`` node."""
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        content = value.get("content")
        if isinstance(content, str):
            text = content.strip()
            return text or None
        simple = value.get("simpleText")
        if isinstance(simple, str):
            text = simple.strip()
            return text or None
    return None


def _unwrap_youtube_redirect(url: str) -> str:
    """Resolve ``youtube.com/redirect?q=…`` wrappers to the target URL."""
    if "youtube.com/redirect" not in url and "/redirect?" not in url:
        return url
    try:
        query = parse_qs(urlparse(url).query)
        targets = query.get("q") or []
        if targets:
            return unquote(targets[0])
    except Exception:  # pragma: no cover - extremely defensive
        return url
    return url


_LINK_PLATFORM_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("instagram", ("instagram.com", "instagram")),
    ("x", ("twitter.com", "x.com", "twitter", "/x", " x")),
    ("tiktok", ("tiktok.com", "tiktok")),
    ("facebook", ("facebook.com", "fb.com", "facebook")),
    ("youtube", ("youtube.com", "youtu.be", "youtube")),
    ("spotify", ("spotify.com", "spotify")),
    ("apple_music", ("music.apple.com", "apple music", "apple_music")),
    ("discord", ("discord.gg", "discord.com", "discord")),
    ("twitch", ("twitch.tv", "twitch")),
    ("reddit", ("reddit.com", "reddit")),
    ("linkedin", ("linkedin.com", "linkedin")),
    ("telegram", ("t.me", "telegram.me", "telegram")),
    ("onlyfans", ("onlyfans.com", "onlyfans")),
    ("patreon", ("patreon.com", "patreon")),
    ("github", ("github.com", "github")),
    ("website", ("website", "official", "home")),
)


def _slugify_link_key(value: str) -> str:
    """Turn free-form link titles into stable dictionary keys."""
    cleaned = []
    prev_underscore = False
    for ch in value.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
            prev_underscore = False
        elif not prev_underscore:
            cleaned.append("_")
            prev_underscore = True
    slug = "".join(cleaned).strip("_")
    return slug or "link"


def _link_dict_key(title: str | None, url: str) -> str:
    """Pick a stable platform-oriented key for an external channel link."""
    title_l = (title or "").strip().lower()
    if title_l in {"x", "twitter", "x.com"}:
        return "x"
    haystack = f"{title_l} {url}".lower()
    for key, hints in _LINK_PLATFORM_HINTS:
        if any(hint in haystack for hint in hints):
            return key
    if title:
        return _slugify_link_key(title)
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc
        host = host.removeprefix("www.")
        if host:
            return _slugify_link_key(host.split(".")[0])
    except Exception:  # pragma: no cover
        pass
    return "link"


def _unique_link_key(base: str, used: set[str]) -> str:
    """Ensure dictionary keys stay unique when several links share a platform."""
    if base not in used:
        used.add(base)
        return base
    index = 2
    while f"{base}_{index}" in used:
        index += 1
    key = f"{base}_{index}"
    used.add(key)
    return key


def _external_link_url(view_model: dict[str, Any]) -> str | None:
    """Extract the destination URL from a channel external-link view model."""
    link = view_model.get("link")
    if not isinstance(link, dict):
        return None
    for run in link.get("commandRuns") or []:
        if not isinstance(run, dict):
            continue
        endpoint = (
            (run.get("onTap") or {}).get("innertubeCommand", {}).get("urlEndpoint", {})
        )
        if isinstance(endpoint, dict) and isinstance(endpoint.get("url"), str):
            return _unwrap_youtube_redirect(endpoint["url"])
    content = link.get("content")
    if isinstance(content, str) and content.strip():
        text = content.strip()
        if text.startswith("http://") or text.startswith("https://"):
            return text
        return f"https://{text}"
    return None


def _links_from_about(about: dict[str, Any]) -> dict[str, str]:
    """Build ``{platform: url}`` from an ``aboutChannelViewModel``."""
    raw_links = about.get("links")
    if not isinstance(raw_links, list):
        return {}
    result: dict[str, str] = {}
    used: set[str] = set()
    for item in raw_links:
        if not isinstance(item, dict):
            continue
        view = item.get("channelExternalLinkViewModel")
        if not isinstance(view, dict):
            continue
        title = _content_text(view.get("title"))
        url = _external_link_url(view)
        if not url:
            continue
        key = _unique_link_key(_link_dict_key(title, url), used)
        result[key] = url
    return result


def _links_from_attribution(data: dict[str, Any]) -> dict[str, str]:
    """Fallback single link taken from the header attribution row."""
    header = _page_header_view_model(data)
    try:
        attribution = (
            header.get("attribution", {})
            .get("attributionViewModel", {})
            .get("text", {})
        )
    except AttributeError:
        return {}
    text = _content_text(attribution)
    if not text:
        return {}
    url = text if text.startswith("http") else f"https://{text}"
    return {_link_dict_key(None, url): url}


@dataclass(frozen=True, slots=True)
class ChannelDetails:
    """Detailed metadata about a single channel fetched by id/URL/handle."""

    channel_id: str
    title: str | None = None
    description: str | None = None
    handle: str | None = None
    subscribers: str | None = None
    video_count: str | None = None
    view_count: str | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    thumbnail: str | None = None
    photo: str | None = None
    banner: str | None = None
    vanity_url: str | None = None
    rss_url: str | None = None
    is_family_safe: bool | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    available_countries: tuple[str, ...] = field(default_factory=tuple)
    country: str | None = None
    joined_date: str | None = None
    links: dict[str, str] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """Canonical channel URL."""
        return f"https://www.youtube.com/channel/{self.channel_id}"

    @classmethod
    def from_browse_response(
        cls,
        data: dict[str, Any],
        *,
        about: dict[str, Any] | None = None,
    ) -> ChannelDetails:
        """Build :class:`ChannelDetails` from a ``browse`` endpoint response.

        Pass the optional About-panel payload (or a full continuation response
        that embeds ``aboutChannelViewModel``) as ``about`` to fill country,
        joined date, view count and the labelled external links dictionary.
        """
        meta = data.get("metadata", {}).get("channelMetadataRenderer", {})
        if not isinstance(meta, dict):
            meta = {}
        micro = data.get("microformat", {}).get("microformatDataRenderer", {})
        if not isinstance(micro, dict):
            micro = {}

        about_vm: dict[str, Any] = {}
        if isinstance(about, dict):
            if "aboutChannelViewModel" in about and isinstance(
                about.get("aboutChannelViewModel"), dict
            ):
                about_vm = about["aboutChannelViewModel"]
            else:
                found = _find_first(about, "aboutChannelViewModel")
                if isinstance(found, dict):
                    about_vm = found

        header_texts = _header_metadata_texts(data)
        handle = None
        subscribers = None
        video_count = None
        for text in header_texts:
            if text.startswith("@") and handle is None:
                handle = text
            elif "subscriber" in text.lower() and subscribers is None:
                subscribers = text
            elif "video" in text.lower() and video_count is None:
                video_count = text

        if handle is None:
            handle = _handle_from_urls(
                meta.get("vanityChannelUrl"),
                meta.get("ownerUrls"),
            )

        vanity = meta.get("vanityChannelUrl") or meta.get("channelUrl")
        if isinstance(vanity, str) and vanity.startswith("http://"):
            vanity = "https://" + vanity[len("http://") :]

        keywords = _split_keyword_string(meta.get("keywords"))
        tags = tuple(micro.get("tags") or ())
        if not keywords and tags:
            keywords = tags

        countries = meta.get("availableCountryCodes") or micro.get("availableCountries")
        if not isinstance(countries, list):
            countries = []

        links = _links_from_about(about_vm) if about_vm else {}
        if not links:
            links = _links_from_attribution(data)

        if about_vm:
            subscribers = subscribers or _content_text(
                about_vm.get("subscriberCountText")
            )
            video_count = video_count or _content_text(about_vm.get("videoCountText"))
            description = (
                _content_text(about_vm.get("description"))
                or meta.get("description")
                or micro.get("description")
            )
            country = _content_text(about_vm.get("country"))
            joined_date = _content_text(about_vm.get("joinedDateText"))
            view_count = _content_text(about_vm.get("viewCountText"))
        else:
            description = meta.get("description") or micro.get("description")
            country = None
            joined_date = None
            view_count = None

        channel_id = meta.get("externalId") or about_vm.get("channelId") or ""
        family_safe = meta.get("isFamilySafe")
        if family_safe is None:
            family_safe = micro.get("familySafe")

        photo = _thumbnail(meta.get("avatar")) or _thumbnail(micro.get("thumbnail"))

        return cls(
            channel_id=channel_id if isinstance(channel_id, str) else "",
            title=meta.get("title") or micro.get("title"),
            description=description,
            handle=handle,
            subscribers=subscribers,
            video_count=video_count,
            view_count=view_count,
            keywords=keywords,
            thumbnail=photo,
            photo=photo,
            banner=_banner_from_header(data),
            vanity_url=vanity if isinstance(vanity, str) else None,
            rss_url=meta.get("rssUrl") if isinstance(meta.get("rssUrl"), str) else None,
            is_family_safe=bool(family_safe) if family_safe is not None else None,
            tags=tags,
            available_countries=tuple(
                code for code in countries if isinstance(code, str)
            ),
            country=country,
            joined_date=joined_date,
            links=links,
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
