"""Localise results by interface language (hl) and content region (gl).

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/05_language_region.py
Run async:  python examples/05_language_region.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, Country, Language, Locale, YouTube


def run_sync() -> None:
    # Pass raw ISO codes — they are validated and normalised for you.
    with YouTube(language="uk", region="UA") as yt:
        print("Ukrainian interface / region:")
        for video in yt.search("музика", max_results=5):
            print(f"  {video.title}")

    # The Language / Country / Locale value objects are equivalent.
    locale = Locale(language=Language("de"), country=Country("DE"))
    with YouTube(locale=locale) as yt:
        print(f"\nLocale: {yt.locale.language.code}-{yt.locale.country.code}")
        for video in yt.search("musik", max_results=5):
            print(f"  {video.title}")


async def run_async() -> None:
    async with AsyncYouTube(language="uk", region="UA") as yt:
        print("Ukrainian interface / region:")
        results = await yt.search("музика", max_results=5)
        async for video in results:
            print(f"  {video.title}")

    locale = Locale(language=Language("de"), country=Country("DE"))
    async with AsyncYouTube(locale=locale) as yt:
        print(f"\nLocale: {yt.locale.language.code}-{yt.locale.country.code}")
        results = await yt.search("musik", max_results=5)
        async for video in results:
            print(f"  {video.title}")


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
