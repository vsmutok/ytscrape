"""Fetch a video transcript (captions).

Requires for async:  pip install 'ytscrape[async]'

Run sync:   python examples/09_transcript.py
Run async:  python examples/09_transcript.py --async
"""

from __future__ import annotations

import argparse
import asyncio

from ytscrape import AsyncYouTube, YouTube


def run_sync() -> None:
    with YouTube() as yt:
        video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # List every available caption track first.
        print("Available tracks:")
        print(yt.transcripts(video))
        print()

        # Prefer Ukrainian, fall back to English (manual captions beat ASR).
        transcript = yt.transcript(video, languages=["uk", "en"])
        print(
            f"Fetched: {transcript.language} ({transcript.language_code}), "
            f"generated={transcript.is_generated}, lines={len(transcript)}"
        )
        print()
        for snippet in transcript[:8]:
            print(f"[{snippet.start:6.1f}s] {snippet.text}")
        print("...")
        print(transcript.text[:240], "…")


async def run_async() -> None:
    async with AsyncYouTube() as yt:
        video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        print("Available tracks:")
        print(await yt.transcripts(video))
        print()

        transcript = await yt.transcript(video, languages=["uk", "en"])
        print(
            f"Fetched: {transcript.language} ({transcript.language_code}), "
            f"generated={transcript.is_generated}, lines={len(transcript)}"
        )
        print()
        for snippet in transcript[:8]:
            print(f"[{snippet.start:6.1f}s] {snippet.text}")
        print("...")
        print(transcript.text[:240], "…")


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
