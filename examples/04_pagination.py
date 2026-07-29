"""Two ways to work with paginated search results.

Run with:  python examples/04_pagination.py
"""

from ytscrape import YouTube


def main() -> None:
    with YouTube() as yt:
        # 1. Transparent pagination: just iterate. Pages are loaded on demand;
        #    `max_results` caps how many items you consume.
        print("Transparent iteration (first 15 items):")
        for item in yt.search("python", max_results=15):
            print(f"  {item.title}")

        # 2. Manual pagination: load one page at a time.
        print("\nManual pagination:")
        results = yt.search("python")
        page = results.fetch_next_page()
        print(f"  Loaded {len(page)} more items")
        print(f"  More pages available? {results.has_more}")


if __name__ == "__main__":
    main()
