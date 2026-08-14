from __future__ import annotations

from io import StringIO
from time import sleep

from ytscrape import Channel, Video, VideoDetails, __version__
from ytscrape.__main__ import _build_parser
from ytscrape._cli import (
    BOLD,
    RED,
    WHITE,
    Spinner,
    colour_enabled,
    display_width,
    logo,
    paint,
    render_table,
    search_rows,
    video_pairs,
)


def test_global_flags_work_after_subcommand() -> None:
    parser = _build_parser()
    after = parser.parse_args(
        ["search", "JS", "--filter", "videos", "--max", "50", "--format", "csv"]
    )
    assert after.output_format == "csv"
    assert after.max_results == 50
    assert after.filter == "videos"

    before = parser.parse_args(["--format", "json", "search", "JS", "-o", "out.json"])
    assert before.output_format == "json"
    assert before.output == "out.json"


def test_spinner_writes_and_clears() -> None:
    buf = StringIO()
    with Spinner("loading…", enabled=True, stream=buf, interval=0.01):
        sleep(0.03)
    text = buf.getvalue()
    assert "loading…" in text
    assert "\r\033[K" in text


def test_spinner_silent_when_disabled() -> None:
    buf = StringIO()
    with Spinner("loading…", enabled=False, stream=buf):
        pass
    assert buf.getvalue() == ""


def test_logo_includes_name_and_version() -> None:
    text = logo(enabled=False, version=__version__)
    assert "ytscrape" in text
    assert f"v{__version__}" in text
    assert "▶" in text


def test_logo_uses_ansi_when_enabled() -> None:
    coloured = logo(enabled=True, version="0.0.0")
    assert "\033[" in coloured
    assert colour_enabled(force=True) is True
    assert paint("yt", RED, BOLD, enabled=True) in coloured
    assert paint("scrape", WHITE, BOLD, enabled=True) in coloured
    assert colour_enabled(force=False) is False


def test_paint_noop_when_disabled() -> None:
    assert paint("hi", "\033[1m", enabled=False) == "hi"


def test_render_table_empty() -> None:
    assert "no results" in render_table(("A",), [], enabled=False)


def test_render_table_boxes_and_truncates() -> None:
    table = render_table(
        ("#", "Title"),
        [(1, "hello world")],
        enabled=False,
        max_width=14,
    )
    assert "┌" in table and "┐" in table
    assert "Title" in table
    assert "…" in table


def test_render_table_aligns_emoji() -> None:
    table = render_table(
        ("#", "Title"),
        [(1, "Python 🐍"), (2, "No emoji")],
        enabled=False,
        max_width=80,
    )
    lines = [line for line in table.splitlines() if line.startswith("│")]
    widths = {display_width(line) for line in lines}
    assert len(widths) == 1
    assert display_width("🐍") == 2
    assert display_width("♥") == 1
    assert display_width("❤") == 1
    assert display_width("❤️") == 2
    assert display_width("😭") == 2

    hearts = render_table(
        ("#", "♥", "Comment"),
        [(1, "♥", "ok"), (2, None, "They 😭"), (3, None, "love ❤️")],
        enabled=False,
        max_width=80,
    )
    heart_lines = [line for line in hearts.splitlines() if line.startswith("│")]
    assert len({display_width(line) for line in heart_lines}) == 1


def test_search_rows_from_video() -> None:
    video = Video(
        video_id="abc",
        title="A title",
        channel="Chan",
        duration="3:14",
        views="1K views",
        published="1 day ago",
    )
    headers, rows = search_rows([video])
    assert headers[0] == "#"
    assert rows[0][1] == "video"
    assert rows[0][2] == "A title"
    assert rows[0][4] == "3:14"
    assert headers[-2] == "Published"
    assert headers[-1] == "URL"
    assert rows[0][-2] == "1 day ago"
    assert rows[0][-1] == video.url


def test_search_rows_omit_published_for_channels() -> None:
    channel = Channel(
        channel_id="UC123",
        title="A channel",
        handle="@a",
        subscribers="1M subscribers",
    )
    headers, rows = search_rows([channel])
    assert "Published" not in headers
    assert rows[0][1] == "channel"
    assert rows[0][3] == "@a"
    assert rows[0][5] == "1M subscribers"
    assert headers[-1] == "URL"
    assert rows[0][-1] == channel.url


def test_video_pairs_include_new_fields() -> None:
    details = VideoDetails(
        video_id="vid",
        title="T",
        channel="C",
        views=10,
        length_seconds=12,
        published="2009-10-25",
        category="Music",
    )
    pairs = dict(video_pairs(details))
    assert pairs["Title"] == "T"
    assert pairs["Length"] == "12s"
    assert pairs["Published"] == "2009-10-25"
    assert pairs["Category"] == "Music"
