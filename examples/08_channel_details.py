"""Fetch detailed metadata for a single channel (by id, @handle or URL).

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/08_channel_details.py
Run async:  python examples/08_channel_details.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, ChannelDetails, YouTube


def _print_channel(details: ChannelDetails) -> None:
    print(f"Title:        {details.title}")
    print(f"Handle:       {details.handle}")
    print(f"Subscribers:  {details.subscribers}")
    print(f"Videos:       {details.video_count}")
    print(f"Views:        {details.view_count}")
    print(f"Country:      {details.country}")
    print(f"Joined:       {details.joined_date}")
    print(f"Family safe:  {details.is_family_safe}")
    print(f"Photo:        {details.photo}")
    print(f"Banner:       {details.banner}")
    print(f"Keywords:     {', '.join(details.keywords[:5])}")
    print(f"URL:          {details.url}")
    print(f"Vanity URL:   {details.vanity_url}")
    print(f"RSS:          {details.rss_url}")
    if details.links:
        print(f"Links:        {details.links}")
    if details.description:
        print(f"Description:  {details.description[:120]}...")


def run_sync() -> None:
    with YouTube() as yt:
        # A channel id, @handle or any channel URL all work.
        details = yt.channel("https://www.youtube.com/@CodeBrux")
        _print_channel(details)


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        details = await yt.channel("https://www.youtube.com/@CodeBrux")
        _print_channel(details)


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
