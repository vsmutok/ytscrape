"""Search YouTube for videos and print the results.

Run with:  python examples/01_search_videos.py
"""

from ytscrape import SearchFilter, YouTube


def main() -> None:
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


if __name__ == "__main__":
    main()
