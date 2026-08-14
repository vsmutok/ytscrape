"""Command line interface: ``python -m ytscrape``.

Examples:
    python -m ytscrape search "python tutorial" --filter videos --max 10
    python -m ytscrape video https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python -m ytscrape transcript dQw4w9WgXcQ --lang en --lang uk
"""

from __future__ import annotations

import argparse
import sys

from . import YouTube, __version__
from . import _cli as cli
from .exceptions import YtScraperError
from .export import dump_csv, dump_json, dumps_csv, dumps_json
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
        choices=("table", "plain", "json", "csv"),
        default="table" if default is None else default,
        dest="output_format",
        help=(
            "Output style. 'table' (default) is pretty; 'plain' is "
            "script-friendly; 'json' / 'csv' export structured data."
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


def _use_table(args: argparse.Namespace) -> bool:
    return args.output_format == "table"


def _colour(args: argparse.Namespace) -> bool:
    force = False if args.no_color else None
    return cli.colour_enabled(force=force)


def _spinner_on(args: argparse.Namespace) -> bool:
    if args.output_format == "plain":
        return False
    return bool(getattr(sys.stderr, "isatty", lambda: False)())


def _emit_export(args: argparse.Namespace, payload: object) -> None:
    dest = args.output
    if args.output_format == "json":
        if dest:
            dump_json(payload, dest)
        else:
            sys.stdout.write(dumps_json(payload))
        return
    if dest:
        dump_csv(payload, dest)
    else:
        sys.stdout.write(dumps_csv(payload))


def _print_banner(args: argparse.Namespace) -> None:
    if args.no_logo or not _use_table(args):
        return
    print(cli.logo(enabled=_colour(args), version=__version__))


def main(argv: list[str] | None = None) -> int:
    """Entry point for the console script and ``python -m ytscrape``."""
    args = _build_parser().parse_args(argv)
    pretty = _use_table(args)
    color = _colour(args)

    try:
        with YouTube(language=args.language, region=args.region) as yt:
            _print_banner(args)
            if args.command == "search":
                with cli.Spinner("searching…", enabled=_spinner_on(args)):
                    results = list(
                        yt.search(
                            args.query,
                            filter=args.filter,
                            max_results=args.max_results,
                        )
                    )
                if args.output_format in {"json", "csv"}:
                    _emit_export(args, results)
                elif pretty:
                    headers, rows = cli.search_rows(results)
                    print(cli.render_table(headers, rows, enabled=color))
                else:
                    for item in results:
                        print(cli.plain_search_line(item))
            elif args.command == "video":
                with cli.Spinner("fetching video…", enabled=_spinner_on(args)):
                    details = yt.video(args.video)
                if args.output_format in {"json", "csv"}:
                    _emit_export(args, details)
                elif pretty:
                    print(cli.render_kv(cli.video_pairs(details), enabled=color))
                else:
                    print(f"Title:     {details.title}")
                    print(f"Channel:   {details.channel}")
                    print(f"Views:     {details.views}")
                    print(f"Length:    {details.length_seconds}s")
                    print(f"Published: {details.published}")
                    print(f"Category:  {details.category}")
                    print(f"Live:      {details.is_live}")
                    print(f"URL:       {details.url}")
            elif args.command == "channel":
                with cli.Spinner("fetching channel…", enabled=_spinner_on(args)):
                    details = yt.channel(args.channel)
                if args.output_format in {"json", "csv"}:
                    _emit_export(args, details)
                elif pretty:
                    print(cli.render_kv(cli.channel_pairs(details), enabled=color))
                else:
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
                with cli.Spinner("loading comments…", enabled=_spinner_on(args)):
                    comments = list(
                        yt.comments(
                            args.video,
                            max_results=max_results,
                            include_replies=args.include_replies,
                            sort=args.sort,
                        )
                    )
                if args.output_format in {"json", "csv"}:
                    _emit_export(args, comments)
                elif pretty:
                    print(cli.comment_table(comments, enabled=color))
                else:
                    for comment in comments:
                        prefix = "  \u21b3 " if comment.is_reply else ""
                        print(f"{prefix}{comment.author}: {comment.text}")
            elif args.command == "transcript":
                if args.list_only:
                    spin = cli.Spinner(
                        "listing transcripts…",
                        enabled=_spinner_on(args),
                    )
                    with spin:
                        tracks = yt.transcripts(args.video)
                    if args.output_format in {"json", "csv"}:
                        _emit_export(args, list(tracks))
                    elif pretty:
                        print(cli.transcript_list_table(tracks, enabled=color))
                    else:
                        print(tracks)
                else:
                    languages = tuple(args.languages) if args.languages else ("en",)
                    spin = cli.Spinner(
                        "fetching transcript…",
                        enabled=_spinner_on(args),
                    )
                    with spin:
                        result = yt.transcript(
                            args.video,
                            languages=languages,
                            preserve_formatting=args.preserve_formatting,
                        )
                    if args.output_format in {"json", "csv"}:
                        _emit_export(args, result)
                    elif pretty:
                        print(cli.transcript_table(result, enabled=color))
                    else:
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
