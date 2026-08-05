"""Collect the comments of a single video (by id or URL).

Run with:  python examples/07_video_comments.py
"""

from ytscrape import CommentSort, YouTube


def main() -> None:
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
            "https://www.youtube.com/watch?v=75IuMfHdTfc",
            max_results=1000,
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


if __name__ == "__main__":
    main()
