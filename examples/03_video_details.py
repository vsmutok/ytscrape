"""Fetch detailed metadata for a single video (by id or URL).

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/03_video_details.py
Run async:  python examples/03_video_details.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        # A plain id or any YouTube URL both work.
        details = yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        print(f"Title:    {details.title}")
        print(f"Channel:  {details.channel}")
        print(f"Views:    {details.views}")
        print(f"Length:   {details.length_seconds}s")
        print(f"Live:     {details.is_live}")
        print(f"Keywords: {', '.join(details.keywords[:5])}")
        print(f"URL:      {details.url}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        details = await yt.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        print(f"Title:    {details.title}")
        print(f"Channel:  {details.channel}")
        print(f"Views:    {details.views}")
        print(f"Length:   {details.length_seconds}s")
        print(f"Live:     {details.is_live}")
        print(f"Keywords: {', '.join(details.keywords[:5])}")
        print(f"URL:      {details.url}")


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
