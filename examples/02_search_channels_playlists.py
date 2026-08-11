"""Search YouTube for channels and playlists.

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/02_search_channels_playlists.py
Run async:  python examples/02_search_channels_playlists.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, SearchFilter, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        print("Channels:")
        for channel in yt.search("python", filter=SearchFilter.CHANNELS, max_results=5):
            print(f"  {channel.title} — {channel.subscribers}")
            print(f"    {channel.url}")

        print("\nPlaylists:")
        for playlist in yt.search(
            "python", filter=SearchFilter.PLAYLISTS, max_results=5
        ):
            print(f"  {playlist.title} ({playlist.video_count})")
            print(f"    {playlist.url}")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        print("Channels:")
        channels = await yt.search(
            "python", filter=SearchFilter.CHANNELS, max_results=5
        )
        async for channel in channels:
            print(f"  {channel.title} — {channel.subscribers}")
            print(f"    {channel.url}")

        print("\nPlaylists:")
        playlists = await yt.search(
            "python", filter=SearchFilter.PLAYLISTS, max_results=5
        )
        async for playlist in playlists:
            print(f"  {playlist.title} ({playlist.video_count})")
            print(f"    {playlist.url}")


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
