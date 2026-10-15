"""Command line interface: ``python -m ytscrape``.

Examples:
    python -m ytscrape search "python tutorial" --filter videos --max 10
    python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python -m ytscrape transcript dQw4w9WgXcQ --lang en --lang uk
    ytscrape search "python" --format jsonl --max 10
"""

from __future__ import annotations

import argparse
import sys

from . import YouTube, __version__
from . import _cli as cli
from .exceptions import YtScraperError
from .filters import CommentSort, SearchFilter


def _add_shared_flags(
    parser: argparse.ArgumentParser, *, suppress_defaults: bool = False
) -> None:
    """Flags accepted both before and after the subcommand.

    Subparsers use ``SUPPRESS`` so their defaults do not overwrite a value
    already set on the parent (``ytscrape --format json search …``).
    """
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument(
        "--language",
        default="en" if default is None else default,
        metavar="HL",
        help="Interface language (hl), e.g. en, uk, de.",
    )
    parser.add_argument(
        "--region",
        default="US" if default is None else default,
        metavar="GL",
        help="Content region / country (gl), e.g. US, UA, DE.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "plain", "json", "jsonl", "csv"),
        default="table" if default is None else default,
        dest="output_format",
        help=(
            "Output style. 'table' (default) is pretty; 'plain' is "
            "script-friendly; 'json' exports one document; 'jsonl' writes "
            "one JSON object per line; 'csv' exports structured data."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None if default is None else default,
        metavar="FILE",
        help="Write json/csv output to FILE instead of stdout.",
    )
    no_color_kw: dict[str, object] = {"action": "store_true"}
    no_logo_kw: dict[str, object] = {"action": "store_true"}
    if suppress_defaults:
        no_color_kw["default"] = argparse.SUPPRESS
        no_logo_kw["default"] = argparse.SUPPRESS
    parser.add_argument(
        "--no-color",
        help="Disable ANSI colours (also honours NO_COLOR).",
        **no_color_kw,  # type: ignore[arg-type]
    )
    parser.add_argument(
        "--no-logo",
        help="Skip the ytscrape wordmark.",
        **no_logo_kw,  # type: ignore[arg-type]
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytscrape",
        description="Scrape YouTube search results and video metadata.",
    )
    parser.add_argument(
        "--version", action="version", version=f"ytscrape {__version__}"
    )
    _add_shared_flags(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search YouTube.")
    _add_shared_flags(search, suppress_defaults=True)
    search.add_argument("query", help="Search query.")
    search.add_argument(
        "--filter",
        choices=[f.value for f in SearchFilter],
        default=SearchFilter.ALL.value,
        help="Type of results to return.",
    )
    search.add_argument(
        "--max",
        type=int,
        default=10,
        dest="max_results",
        help="Maximum number of results to print.",
    )

    video = sub.add_parser("video", help="Fetch details for a single video.")
    _add_shared_flags(video, suppress_defaults=True)
    video.add_argument("video", help="Video id or URL.")

    channel = sub.add_parser("channel", help="Fetch details for a single channel.")
    _add_shared_flags(channel, suppress_defaults=True)
    channel.add_argument("channel", help="Channel id, @handle or URL.")

    comments = sub.add_parser(
        "comments",
        help="Collect the comments of a single video.",
    )
    _add_shared_flags(comments, suppress_defaults=True)
    comments.add_argument("video", help="Video id or URL.")
    comments.add_argument(
        "--max",
        type=int,
        default=20,
        dest="max_results",
        help="Maximum number of comments to print (0 = no limit).",
    )
    comments.add_argument(
        "--replies",
        action="store_true",
        dest="include_replies",
        help="Also collect the replies of every comment.",
    )
    comments.add_argument(
        "--sort",
        choices=[s.value for s in CommentSort],
        default=CommentSort.TOP.value,
        help=(
            "Sort order. 'top' (default) mirrors YouTube and hides some "
            "comments; 'newest' collects every comment."
        ),
    )

    transcript = sub.add_parser(
        "transcript",
        help="Fetch captions / transcript for a video.",
    )
    _add_shared_flags(transcript, suppress_defaults=True)
    transcript.add_argument("video", help="Video id or URL.")
    transcript.add_argument(
        "--lang",
        action="append",
        dest="languages",
        metavar="CODE",
        help=("Preferred language code (repeatable, tried in order). Default: en."),
    )
    transcript.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="Only list available caption tracks, do not download.",
    )
    transcript.add_argument(
        "--preserve-formatting",
        action="store_true",
        help="Keep basic HTML formatting tags in snippet text.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the console script and ``python -m ytscrape``."""
    args = _build_parser().parse_args(argv)
    try:
        with YouTube(language=args.language, region=args.region) as yt:
            cli.print_banner(args, version=__version__)
            cli.COMMANDS[args.command](yt, args)
    except YtScraperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
