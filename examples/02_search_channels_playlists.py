"""Search YouTube for channels and playlists.

Run with:  python examples/02_search_channels_playlists.py
"""

from ytscrape import SearchFilter, YouTube


def main() -> None:
    with YouTube() as yt:
        print("Channels:")
        for channel in yt.search(
            "python", filter=SearchFilter.CHANNELS, max_results=5
        ):
            print(f"  {channel.title} — {channel.subscribers}")
            print(f"    {channel.url}")

        print("\nPlaylists:")
        for playlist in yt.search(
            "python", filter=SearchFilter.PLAYLISTS, max_results=5
        ):
            print(f"  {playlist.title} ({playlist.video_count})")
            print(f"    {playlist.url}")


if __name__ == "__main__":
    main()
