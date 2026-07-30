"""Example usage of the ytscrape package.

Run with:  python main.py
"""

from __future__ import annotations

from ytscrape import SearchFilter, YouTube


def main() -> None:
    with YouTube() as yt:
        print("=== Videos for 'python' ===")
        for video in yt.search("python", filter=SearchFilter.VIDEOS, max_results=5):
            print(f"- {video.title} ({video.url})")

        print("\n=== Channels for 'python' ===")
        for channel in yt.search("python", filter=SearchFilter.CHANNELS, max_results=5):
            print(f"- {channel.title} ({channel.url})")


if __name__ == "__main__":
    main()
