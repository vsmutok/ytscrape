"""Minimal command line interface: ``python -m ytscrape``.

Examples:
    python -m ytscrape search "python tutorial" --filter videos --max 10
    python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ
"""

from __future__ import annotations

import argparse
import sys

from . import YouTube, __version__
from .exceptions import YtScraperError
from .filters import CommentSort, SearchFilter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytscrape",
        description="Scrape YouTube search results and video metadata.",
    )
    parser.add_argument(
        "--version", action="version", version=f"ytscrape {__version__}"
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
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search YouTube.")
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
    video.add_argument("video", help="Video id or URL.")

    comments = sub.add_parser(
        "comments", help="Collect the comments of a single video."
    )
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

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the console script and ``python -m ytscrape``."""
    args = _build_parser().parse_args(argv)

    try:
        with YouTube(language=args.language, region=args.region) as yt:
            if args.command == "search":
                results = yt.search(
                    args.query,
                    filter=args.filter,
                    max_results=args.max_results,
                )
                for item in results:
                    title = getattr(item, "title", None)
                    print(f"{title}\t{item.url}")
            elif args.command == "video":
                details = yt.video(args.video)
                print(f"Title:   {details.title}")
                print(f"Channel: {details.channel}")
                print(f"Views:   {details.views}")
                print(f"Length:  {details.length_seconds}s")
                print(f"URL:     {details.url}")
            elif args.command == "comments":
                max_results = args.max_results or None
                for comment in yt.comments(
                    args.video,
                    max_results=max_results,
                    include_replies=args.include_replies,
                    sort=args.sort,
                ):
                    prefix = "  \u21b3 " if comment.is_reply else ""
                    print(f"{prefix}{comment.author}: {comment.text}")
    except YtScraperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
