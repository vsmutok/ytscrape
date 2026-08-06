"""Minimal command line interface: ``python -m ytscrape``.

Examples:
    python -m ytscrape search "python tutorial" --filter videos --max 10
    python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python -m ytscrape transcript dQw4w9WgXcQ --lang en --lang uk
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

    channel = sub.add_parser("channel", help="Fetch details for a single channel.")
    channel.add_argument("channel", help="Channel id, @handle or URL.")

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

    transcript = sub.add_parser(
        "transcript", help="Fetch captions / transcript for a video."
    )
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
            elif args.command == "channel":
                details = yt.channel(args.channel)
                print(f"Title:        {details.title}")
                print(f"Handle:       {details.handle}")
                print(f"Subscribers:  {details.subscribers}")
                print(f"Videos:       {details.video_count}")
                print(f"Views:        {details.view_count}")
                print(f"Country:      {details.country}")
                print(f"Joined:       {details.joined_date}")
                print(f"Photo:        {details.photo}")
                print(f"Banner:       {details.banner}")
                print(f"Channel id:   {details.channel_id}")
                print(f"URL:          {details.url}")
                if details.vanity_url:
                    print(f"Vanity URL:   {details.vanity_url}")
                if details.links:
                    print(f"Links:        {details.links}")
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
            elif args.command == "transcript":
                if args.list_only:
                    print(yt.transcripts(args.video))
                else:
                    languages = tuple(args.languages) if args.languages else ("en",)
                    result = yt.transcript(
                        args.video,
                        languages=languages,
                        preserve_formatting=args.preserve_formatting,
                    )
                    print(
                        f"# {result.video_id} | {result.language_code} "
                        f"| generated={result.is_generated} "
                        f"| snippets={len(result)}"
                    )
                    for snippet in result:
                        print(
                            f"[{snippet.start:8.2f} +{snippet.duration:5.2f}] "
                            f"{snippet.text}"
                        )
    except YtScraperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
