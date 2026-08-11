"""Fan-out pattern: scrape many videos concurrently with AsyncYouTube.

Requires:  pip install 'ytscrape[async]'

Run:  python examples/10_async_concurrency.py
"""

from __future__ import annotations

import asyncio

from ytscrape import AsyncYouTube, SearchFilter


async def main() -> None:
    # `max_concurrency` caps in-flight HTTP calls across the client.
    async with AsyncYouTube(max_concurrency=8, max_retries=3) as yt:
        print("=== search ===")
        results = await yt.search(
            "python tutorial",
            filter=SearchFilter.VIDEOS,
            max_results=5,
        )
        videos = [video async for video in results]
        for video in videos:
            print(f"  {video.title} — {video.url}")

        print("\n=== video details in parallel ===")
        details_list = await asyncio.gather(*(yt.video(v.video_id) for v in videos))
        for details in details_list:
            print(f"  {details.title} ({details.views} views)")

        print("\n=== comments (newest, capped) ===")
        thread = await yt.comments(
            "dQw4w9WgXcQ",
            max_results=5,
            sort="newest",
        )
        async for comment in thread:
            print(f"  {comment.author}: {comment.text[:80]!r}")


if __name__ == "__main__":
    asyncio.run(main())
