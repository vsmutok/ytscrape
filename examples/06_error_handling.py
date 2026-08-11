"""Handle the exceptions ytscrape can raise.

All ytscrape errors derive from `YtScraperError`, so catching that one is
enough for a broad guard; catch the specific subclasses when you need to react
differently.

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/06_error_handling.py
Run async:  python examples/06_error_handling.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, ParseError, RequestError, YouTube, YtScraperError


def run_sync() -> None:
    with YouTube() as yt:
        # An invalid id/URL cannot be parsed into a video id.
        try:
            yt.video("not-a-real-video-id")
        except ParseError as exc:
            print(f"Could not parse video id: {exc}")

        # Network / HTTP failures surface as RequestError.
        try:
            details = yt.video("dQw4w9WgXcQ")
            print(f"Got: {details.title}")
        except RequestError as exc:
            print(f"Request to YouTube failed: {exc}")
        except YtScraperError as exc:
            # Catch-all for any other ytscrape error.
            print(f"Something went wrong: {exc}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        try:
            await yt.video("not-a-real-video-id")
        except ParseError as exc:
            print(f"Could not parse video id: {exc}")

        try:
            details = await yt.video("dQw4w9WgXcQ")
            print(f"Got: {details.title}")
        except RequestError as exc:
            print(f"Request to YouTube failed: {exc}")
        except YtScraperError as exc:
            print(f"Something went wrong: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="use AsyncYouTube (requires ytscrape[async])",
    )
    args = parser.parse_args()
    if args.use_async:
        asyncio.run(run_async())
    else:
        run_sync()


if __name__ == "__main__":
    main()
