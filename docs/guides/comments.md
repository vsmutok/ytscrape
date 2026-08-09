# Collect YouTube video comments and replies with ytscrape

> Iterate every comment and reply on a YouTube video using ytscrape's lazy CommentThread, control sort order, and handle disabled comments.

YouTube comment sections can run into the thousands. `yt.comments()` returns a lazy `CommentThread` iterator that pages through all of them automatically — you never need to handle a continuation token yourself.

## Basic iteration

Pass a video id or any YouTube URL. Use `max_results` to cap how many comments you consume:

```python
from ytscrape import YouTube

with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=50):
        print(comment.author, "-", comment.text)
```

`yt.comments()` accepts the same video input formats as `yt.video()`: a bare 11-character id, a `watch?v=` URL, a `youtu.be/` short link, a `/shorts/` URL, or an `/embed/` URL.

## Collecting replies

By default only top-level comments are collected. Pass `include_replies=True` to also expand each thread's replies. Replies are yielded immediately after the comment they belong to, and they carry `is_reply=True`:

```python
with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", include_replies=True):
        marker = "  ↳" if comment.is_reply else "-"
        print(f"{marker} {comment.author}: {comment.text}")
```

When `include_replies=True`, `max_results` counts replies alongside top-level comments.

## Sort order

The sort order matters for completeness.

| Sort         | Constant                      | What it returns                                                                                    |
| ------------ | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| Top comments | `CommentSort.TOP` *(default)* | Mirrors YouTube's ranked view — **hides** some comments flagged as low-relevance or potential spam |
| Newest first | `CommentSort.NEWEST`          | Reverse-chronological — returns **every** comment                                                  |

Use `CommentSort.NEWEST` whenever you need to collect all comments, not just the highlighted ones:

```python
from ytscrape import YouTube, CommentSort

with YouTube() as yt:
    for comment in yt.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        sort=CommentSort.NEWEST,
    ):
        print(comment.author, "-", comment.text)
```

`sort` also accepts the string shorthand: `sort="newest"` and `sort="top"` are both valid.

## Counting comments

`yt.comments()` is a lazy iterator, so the total is only known once every page has been consumed. Count as you go, or materialise all comments into a list first:

```python
# Count while iterating
total = 0
for comment in yt.comments(video_url, sort="newest"):
    total += 1
print(f"Collected {total} comments")

# Or materialise everything at once
comments = list(yt.comments(video_url, sort="newest"))
print(len(comments))
```

## Full example

The following snippet is drawn from the bundled `examples/07_video_comments.py`:

```python
from ytscrape import CommentSort, YouTube


def main() -> None:
    with YouTube() as yt:
        total = 0
        for comment in yt.comments(
            "https://www.youtube.com/watch?v=75IuMfHdTfc",
            max_results=1000,
            include_replies=True,
            sort=CommentSort.NEWEST,
        ):
            total += 1
            prefix = "  ↳ " if comment.is_reply else ""
            # `like_count_text` keeps YouTube's raw count (e.g. "1.2K") even
            # when the integer `like_count` is None because it was abbreviated.
            count = comment.like_count_text
            likes = f" ({count} likes)" if count else ""
            heart = " ❤️" if comment.heart else ""
            print(f"{prefix}{comment.author}{likes}{heart}: {comment.text}")

        print(f"\nComments collected: {total}")


if __name__ == "__main__":
    main()
```

## Comment fields

Every comment is a frozen dataclass with the following fields:

| Field               | Type          | Description                                                                          |
| ------------------- | ------------- | ------------------------------------------------------------------------------------ |
| `comment_id`        | `str`         | Unique comment id.                                                                   |
| `text`              | `str \| None` | The comment body.                                                                    |
| `author`            | `str \| None` | Display name of the author.                                                          |
| `author_channel_id` | `str \| None` | Channel id of the author (when available).                                           |
| `author_thumbnail`  | `str \| None` | URL of the author's avatar image.                                                    |
| `published`         | `str \| None` | Human-readable published time (e.g. `"2 days ago"`).                                 |
| `like_count`        | `int \| None` | Like count as an integer, or `None` when abbreviated.                                |
| `like_count_text`   | `str \| None` | Like count as YouTube renders it, preserving abbreviations (e.g. `"1.2K"`, `"894"`). |
| `reply_count`       | `int \| None` | Number of replies (top-level comments only).                                         |
| `reply_count_text`  | `str \| None` | Reply count as a raw display string.                                                 |
| `heart`             | `bool`        | `True` if the video creator hearted the comment.                                     |
| `is_reply`          | `bool`        | `True` for replies, `False` for top-level comments.                                  |

!!! note

    `like_count` is `None` when YouTube returns an abbreviated string like `"1.2K"` instead of an exact integer. Use `like_count_text` whenever you need to display the count exactly as YouTube shows it.


## Disabled comments

If a video has comments turned off, `yt.comments()` raises `ParseError` as soon as the call is made — before you start iterating:

```python
from ytscrape import YouTube, ParseError

with YouTube() as yt:
    try:
        for comment in yt.comments("https://youtu.be/VIDEO_WITH_NO_COMMENTS"):
            print(comment.text)
    except ParseError as exc:
        print(f"Comments are unavailable: {exc}")
```
