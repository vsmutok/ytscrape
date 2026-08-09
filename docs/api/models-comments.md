# Comment model and CommentThread paginated iterator

> Reference for the Comment frozen dataclass and the CommentThread paginated iterator returned by YouTube.comments(), with full reply thread support.

`Comment` is the frozen dataclass produced when you iterate over a `CommentThread`. Each instance represents either a top-level comment or a reply, distinguished by the `is_reply` flag. `CommentThread` itself is a lazy, paginated iterable — it fetches new pages of comments automatically as you consume items, and can optionally expand every reply thread inline.

## Comment

**`comment_id`** (`str`)

:   The unique comment identifier assigned by YouTube. Never `None`.


**`text`** (`str | None`)

:   The plain text body of the comment. `None` only in the rare case that YouTube returns a comment with no text node.


**`author`** (`str | None`)

:   Display name of the commenter (e.g. `"Rick Astley"`).


**`author_channel_id`** (`str | None`)

:   The channel ID of the commenter. Can be passed to `YouTube.channel()` to fetch their channel details.


**`author_thumbnail`** (`str | None`)

:   URL of the commenter's avatar thumbnail.


**`published`** (`str | None`)

:   Relative publication time exactly as YouTube renders it (e.g. `"2 days ago"`, `"3 weeks ago"`).


**`like_count`** (`int | None`)

:   Number of likes on the comment as an integer. `None` when YouTube returns an abbreviated string (such as `"1.2K"`) that cannot be represented as an exact integer. Use `like_count_text` if you just need to display the value.


**`like_count_text`** (`str | None`)

:   The raw like count string exactly as YouTube renders it (e.g. `"894"`, `"1.2K"`). Always populated when like data is available, regardless of whether the value is numeric.


**`reply_count`** (`int | None`)

:   Number of replies to this top-level comment. `None` for replies (which cannot themselves be replied to) or when YouTube does not include the count.


**`reply_count_text`** (`str | None`)

:   Raw reply count string as YouTube renders it (e.g. `"42"`). `None` when unavailable.


**`heart`** (`bool`)

:   `True` when the video's creator has hearted this comment. Always a bool, never `None`.


**`is_reply`** (`bool`)

:   `True` when this comment is a reply to a top-level comment, `False` for top-level comments. Always a bool, never `None`.


***

## CommentThread

`CommentThread` is the lazy, paginated container returned by `YouTube.comments()`. It works identically to `SearchResults` — a plain `for` loop is all you need, and new pages are fetched automatically.

### Properties

**`has_more`** (`bool`)

:   `True` while YouTube has at least one more page of comments to fetch. Becomes `False` once the continuation token is exhausted.


### Methods

**`fetch_next_page()`** (`list[Comment]`)

:   Explicitly fetches the next page of comments, appends them to the internal buffer, and returns the newly added `Comment` instances as a list. When `include_replies=True` the list also contains the replies expanded for each thread on the fetched page. Returns an empty list when there are no more pages.


### Iteration

`CommentThread` is directly iterable and yields `Comment` instances. The iterator respects `max_results` if it was provided to `YouTube.comments()`.

### `max_results` cap

Pass `max_results` to `YouTube.comments()` to limit how many comments are yielded. The iterator stops once the cap is reached, even if more pages are available.

### `include_replies` behaviour

By default only top-level comments are yielded. Set `include_replies=True` to also expand every thread's replies. When enabled, replies are yielded **immediately after** the top-level comment they belong to and are marked with `is_reply=True`. This means the iteration order mirrors YouTube's collapsed-thread layout: parent, then its replies, then the next parent.

***

## Code example

```python
from ytscrape import YouTube

yt = YouTube()

# Basic iteration — top-level comments only
for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=50):
    print(f"{comment.author}: {comment.text}")

# Include replies and detect them
for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", include_replies=True, max_results=100):
    prefix = "  ↳" if comment.is_reply else "•"
    print(f"{prefix} [{comment.author}] {comment.text}")

# Find creator-hearted comments
hearted = [
    c for c in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=200)
    if c.heart
]
print(f"Found {len(hearted)} hearted comment(s)")

# Manual paging
thread = yt.comments("https://youtu.be/dQw4w9WgXcQ")
page1 = thread.fetch_next_page()
page2 = thread.fetch_next_page() if thread.has_more else []
```

!!! note

    `like_count` is `None` whenever YouTube returns an abbreviated value like `"1.2K"` because abbreviations cannot be represented as an exact integer. In those cases `like_count_text` still holds the display string. If you need to display a like count unconditionally, always prefer `like_count_text`; use `like_count` only when you need arithmetic.
