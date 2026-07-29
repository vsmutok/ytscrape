"""Fetch detailed metadata for a single video (by id or URL).

Run with:  python examples/03_video_details.py
"""

from ytscrape import YouTube


def main() -> None:
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


if __name__ == "__main__":
    main()
