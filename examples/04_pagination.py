"""Two ways to work with paginated search results.

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/04_pagination.py
Run async:  python examples/04_pagination.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        # 1. Transparent pagination: just iterate. Pages are loaded on demand;
        #    `max_results` caps how many items you consume.
        print("Transparent iteration (first 15 items):")
        for item in yt.search("python", max_results=15):
            print(f"  {item.title}")

        # 2. Manual pagination: load one page at a time.
        print("\nManual pagination:")
        results = yt.search("python")
        page = results.fetch_next_page()
        print(f"  Loaded {len(page)} more items")
        print(f"  More pages available? {results.has_more}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        print("Transparent iteration (first 15 items):")
        results = await yt.search("python", max_results=15)
        async for item in results:
            print(f"  {item.title}")

        print("\nManual pagination:")
        results = await yt.search("python")
        page = await results.fetch_next_page()
        print(f"  Loaded {len(page)} more items")
        print(f"  More pages available? {results.has_more}")


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
