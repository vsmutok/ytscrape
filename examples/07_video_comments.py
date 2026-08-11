"""Collect the comments of a single video (by id or URL).

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/07_video_comments.py
Run async:  python examples/07_video_comments.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, CommentSort, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        # A plain id or any YouTube URL both work. Iterating pages through
        # every comment transparently; `max_results` caps how many you consume.
        # Pass `include_replies=True` to also collect each comment's replies
        # (they arrive right after their parent, with `is_reply=True`).
        #
        # `sort` controls completeness: the default "top" order mirrors YouTube
        # and quietly hides some comments, while `CommentSort.NEWEST`
        # ("newest") returns *every* comment -- use it to collect them all.
        total = 0
        for comment in yt.comments(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            max_results=100,
            include_replies=True,
            sort=CommentSort.NEWEST,
        ):
            total += 1
            prefix = "  \u21b3 " if comment.is_reply else ""
            # `like_count_text` keeps YouTube's raw count (e.g. "1.2K") even
            # when the integer `like_count` is None because it was abbreviated.
            count = comment.like_count_text
            likes = f" ({count} likes)" if count else ""
            heart = " \u2764\ufe0f" if comment.heart else ""
            print(f"{prefix}{comment.author}{likes}{heart}: {comment.text}")

        # `yt.comments(...)` is a lazy iterator, so the simplest way to know how
        # many comments were collected is to count them as you go.
        print(f"\nComments collected: {total}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        total = 0
        thread = await yt.comments(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            max_results=100,
            include_replies=True,
            sort=CommentSort.NEWEST,
        )
        async for comment in thread:
            total += 1
            prefix = "  \u21b3 " if comment.is_reply else ""
            count = comment.like_count_text
            likes = f" ({count} likes)" if count else ""
            heart = " \u2764\ufe0f" if comment.heart else ""
            print(f"{prefix}{comment.author}{likes}{heart}: {comment.text}")

        print(f"\nComments collected: {total}")


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
