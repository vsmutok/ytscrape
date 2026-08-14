"""Pretty CLI rendering: logo, colours, and tables (no extra deps)."""

from __future__ import annotations

import os
import shutil
import sys
import threading
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Any, TextIO

from .models import Channel, ChannelDetails, Comment, Playlist, Video, VideoDetails
from .transcripts import Transcript, TranscriptList

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[38;5;196m"
ORANGE = "\033[38;5;208m"
YELLOW = "\033[38;5;220m"
WHITE = "\033[38;5;255m"
GRAY = "\033[38;5;245m"
CYAN = "\033[38;5;51m"


def colour_enabled(stream: Any | None = None, *, force: bool | None = None) -> bool:
    """Return whether ANSI colours should be used."""
    if force is False:
        return False
    if force is True:
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    target = stream if stream is not None else sys.stdout
    return bool(getattr(target, "isatty", lambda: False)())


_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


class Spinner:
    """TTY-only braille spinner written to stderr (does not pollute stdout)."""

    def __init__(
        self,
        message: str = "loading",
        *,
        enabled: bool | None = None,
        stream: TextIO | None = None,
        interval: float = 0.08,
    ) -> None:
        self.message = message
        self.stream = stream if stream is not None else sys.stderr
        if enabled is None:
            enabled = bool(getattr(self.stream, "isatty", lambda: False)())
        self.enabled = enabled
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Spinner:
        if not self.enabled:
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._thread = None
        if self.enabled:
            self.stream.write("\r\033[K")
            self.stream.flush()

    def _run(self) -> None:
        i = 0
        while not self._stop.is_set():
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            line = f"  {frame}  {self.message}"
            self.stream.write(f"\r{line}")
            self.stream.flush()
            i += 1
            self._stop.wait(self.interval)


def paint(text: str, *codes: str, enabled: bool) -> str:
    if not enabled or not codes:
        return text
    return f"{''.join(codes)}{text}{RESET}"


def logo(*, enabled: bool, version: str) -> str:
    """Compact colourful wordmark printed above command output."""
    play = paint("▶", RED, BOLD, enabled=enabled)
    name = paint("yt", RED, BOLD, enabled=enabled) + paint(
        "scrape", WHITE, BOLD, enabled=enabled
    )
    tag = paint(f"v{version}", DIM, GRAY, enabled=enabled)
    rule = paint("─" * 28, DIM, GRAY, enabled=enabled)
    return f"  {play} {name}  {tag}\n  {rule}"


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "—"
    text = str(value)
    for br in ("\r\n", "\r", "\n", "\u2028", "\u2029", "\x85", "\t"):
        text = text.replace(br, " ")
    return " ".join(text.split()) or "—"


def _char_display_width(ch: str, *, emoji_presentation: bool = False) -> int:
    """Terminal columns taken by one code point (emoji / CJK = 2)."""
    code = ord(ch)
    if code == 0:
        return 0
    category = unicodedata.category(ch)
    if category in {"Mn", "Me", "Cf"}:
        return 0
    if 0xFE00 <= code <= 0xFE0F or code == 0x200D:
        return 0
    east = unicodedata.east_asian_width(ch)
    if east in {"W", "F"}:
        return 2
    # Colour emoji in the SMP (and flags) are double-wide. Older symbols
    # such as ♥ / ★ stay single-wide unless followed by U+FE0F.
    if 0x1F1E6 <= code <= 0x1F1FF or 0x1F300 <= code <= 0x1FAFF:
        return 2
    if emoji_presentation:
        return 2
    return 1


def display_width(text: str) -> int:
    total = 0
    chars = list(text)
    i = 0
    n = len(chars)
    while i < n:
        nxt = chars[i + 1] if i + 1 < n else ""
        emoji = nxt == "\ufe0f"
        total += _char_display_width(chars[i], emoji_presentation=emoji)
        i += 1
    return total


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    if width <= 1:
        return "…"
    out: list[str] = []
    used = 0
    limit = width - 1
    chars = list(text)
    for i, ch in enumerate(chars):
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        w = _char_display_width(ch, emoji_presentation=nxt == "\ufe0f")
        if used + w > limit:
            break
        out.append(ch)
        used += w
    return "".join(out) + "…"


def _pad(text: str, width: int) -> str:
    return text + " " * max(width - display_width(text), 0)


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    enabled: bool,
    max_width: int | None = None,
) -> str:
    """Render an aligned box table. Long cells are truncated to the terminal."""
    if not rows:
        return paint("(no results)", DIM, enabled=enabled)

    str_rows = [[_cell(c) for c in row] for row in rows]
    cols = len(headers)
    widths = [display_width(h) for h in headers]
    for row in str_rows:
        for i in range(cols):
            widths[i] = max(widths[i], display_width(row[i] if i < len(row) else ""))

    term = max_width
    if term is None:
        term = shutil.get_terminal_size((100, 24)).columns
    # borders + padding: 3 per column + 1
    overhead = 1 + 3 * cols
    budget = max(term - overhead, cols)
    while sum(widths) > budget:
        i = max(range(cols), key=lambda j: widths[j])
        if widths[i] <= 4:
            break
        widths[i] -= 1

    def hline(left: str, mid: str, right: str) -> str:
        parts = [left]
        for i, w in enumerate(widths):
            parts.append("─" * (w + 2))
            parts.append(right if i == cols - 1 else mid)
        return paint("".join(parts), DIM, GRAY, enabled=enabled)

    def row_line(cells: Sequence[str], *, header: bool = False) -> str:
        bits = [paint("│", DIM, GRAY, enabled=enabled)]
        for i in range(cols):
            raw = cells[i] if i < len(cells) else ""
            text = _pad(_truncate(raw, widths[i]), widths[i])
            if header:
                text = paint(text, BOLD, WHITE, enabled=enabled)
            elif i == 0:
                text = paint(text, CYAN, enabled=enabled)
            bits.append(f" {text} ")
            bits.append(paint("│", DIM, GRAY, enabled=enabled))
        return "".join(bits)

    lines = [
        hline("┌", "┬", "┐"),
        row_line(list(headers), header=True),
        hline("├", "┼", "┤"),
    ]
    lines.extend(row_line(r) for r in str_rows)
    lines.append(hline("└", "┴", "┘"))
    return "\n".join(lines)


def render_kv(pairs: Sequence[tuple[str, Any]], *, enabled: bool) -> str:
    rows = [(k, _cell(v)) for k, v in pairs]
    return render_table(("Field", "Value"), rows, enabled=enabled)


def item_type(item: Any) -> str:
    if isinstance(item, Video):
        return "video"
    if isinstance(item, Channel):
        return "channel"
    if isinstance(item, Playlist):
        return "playlist"
    return type(item).__name__.lower()


def search_rows(items: Iterable[Any]) -> tuple[tuple[str, ...], list[list[Any]]]:
    materialised = list(items)
    show_published = any(isinstance(item, Video) for item in materialised)
    headers: tuple[str, ...] = ("#", "Type", "Title", "Channel", "Duration", "Views")
    if show_published:
        headers = (*headers, "Published")
    headers = (*headers, "URL")
    rows: list[list[Any]] = []
    for i, item in enumerate(materialised, start=1):
        row: list[Any] = [
            i,
            item_type(item),
            getattr(item, "title", None),
            getattr(item, "channel", None)
            or getattr(item, "handle", None)
            or getattr(item, "channel_id", None),
            getattr(item, "duration", None) or getattr(item, "video_count", None),
            getattr(item, "views", None) or getattr(item, "subscribers", None),
        ]
        if show_published:
            # Channels have no publish date in search results.
            row.append(
                getattr(item, "published", None) if isinstance(item, Video) else None
            )
        row.append(getattr(item, "url", None))
        rows.append(row)
    return headers, rows


def video_pairs(d: VideoDetails) -> list[tuple[str, Any]]:
    return [
        ("Title", d.title),
        ("Channel", d.channel),
        ("Channel id", d.channel_id),
        ("Views", d.views),
        ("Length", f"{d.length_seconds}s" if d.length_seconds is not None else None),
        ("Published", d.published),
        ("Uploaded", d.upload_date),
        ("Category", d.category),
        ("Live", d.is_live),
        ("Private", d.is_private),
        ("Upcoming", d.is_upcoming),
        ("Family safe", d.is_family_safe),
        ("Ratings", d.allow_ratings),
        ("Keywords", ", ".join(d.keywords[:8]) if d.keywords else None),
        ("Countries", len(d.available_countries) or None),
        ("Embed", d.embed_url),
        ("URL", d.url),
    ]


def channel_pairs(d: ChannelDetails) -> list[tuple[str, Any]]:
    links = None
    if d.links:
        links = ", ".join(f"{k}={v}" for k, v in d.links.items())
    return [
        ("Title", d.title),
        ("Handle", d.handle),
        ("Subscribers", d.subscribers),
        ("Videos", d.video_count),
        ("Views", d.view_count),
        ("Country", d.country),
        ("Joined", d.joined_date),
        ("Channel id", d.channel_id),
        ("URL", d.url),
        ("Vanity", d.vanity_url),
        ("Photo", d.photo),
        ("Links", links),
    ]


def comment_table(comments: Sequence[Comment], *, enabled: bool) -> str:
    rows = []
    for i, c in enumerate(comments, start=1):
        author = f"↳ {c.author}" if c.is_reply else c.author
        rows.append(
            [
                i,
                author,
                c.like_count_text or c.like_count,
                "♥" if c.heart else "",
                c.published,
                c.text,
            ]
        )
    return render_table(
        ("#", "Author", "Likes", "♥", "When", "Comment"),
        rows,
        enabled=enabled,
    )


def transcript_list_table(tracks: TranscriptList, *, enabled: bool) -> str:
    rows = [
        [
            t.language_code,
            t.language,
            t.is_generated,
            t.is_translatable,
        ]
        for t in tracks
    ]
    return render_table(
        ("Code", "Language", "Generated", "Translatable"),
        rows,
        enabled=enabled,
    )


def transcript_table(result: Transcript, *, enabled: bool) -> str:
    header = render_kv(
        [
            ("Video", result.video_id),
            ("Language", result.language_code),
            ("Generated", result.is_generated),
            ("Snippets", len(result)),
        ],
        enabled=enabled,
    )
    rows = [[f"{s.start:.2f}", f"{s.duration:.2f}", s.text] for s in result]
    body = render_table(("Start", "Dur", "Text"), rows, enabled=enabled)
    return f"{header}\n{body}"


def plain_search_line(item: Any) -> str:
    title = getattr(item, "title", None)
    return f"{title}\t{item.url}"
