"""Search YouTube for videos and print the results.

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/01_search_videos.py
Run async:  python examples/01_search_videos.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, SearchFilter, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        results = yt.search(
            "python tutorial",
            filter=SearchFilter.VIDEOS,
            max_results=10,
        )
        for video in results:
            print(f"{video.title}  ({video.duration})")
            print(f"  by {video.channel} — {video.views}")
            print(f"  {video.url}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        results = await yt.search(
            "python tutorial",
            filter=SearchFilter.VIDEOS,
            max_results=10,
        )
        async for video in results:
            print(f"{video.title}  ({video.duration})")
            print(f"  by {video.channel} — {video.views}")
            print(f"  {video.url}")


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
