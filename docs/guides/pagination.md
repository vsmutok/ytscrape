# Paginate YouTube Search Results and Comments in ytscrape

> Iterate over search results and comments across multiple pages automatically, or drive page-by-page loading manually with fetch_next_page().

ytscrape hides YouTube's continuation tokens behind plain Python iterators. The two paginated result types — `SearchResults` (from `yt.search()`) and `CommentThread` (from `yt.comments()`) — share the same interface: iterate over them and pages load on demand; call `fetch_next_page()` when you want explicit control.

## Automatic iteration

The simplest way to consume results is a `for` loop. The first page is fetched when you call `search()` or `comments()`, and subsequent pages are fetched automatically as your loop consumes items beyond the current buffer.

```python
from ytscrape import YouTube

with YouTube() as yt:
    # Pages are loaded on demand — no manual paging needed.
    for item in yt.search("python", max_results=15):
        print(f"  {item.title}")
```

The same pattern works for comments:

```python
with YouTube() as yt:
    for comment in yt.comments("https://youtu.be/dQw4w9WgXcQ", max_results=50):
        print(comment.author, "-", comment.text)
```

## Capping results with `max_results`

Pass `max_results` to stop after a fixed number of items. The iterator returns cleanly once the cap is reached, even when more pages are available on YouTube's side. Omit it entirely to exhaust every page.

```python
with YouTube() as yt:
    # Stop after 25 results, regardless of page boundaries.
    for video in yt.search("python tutorial", filter="videos", max_results=25):
        print(video.title)
```

For `CommentThread`, `max_results` counts replies too when `include_replies=True`.

## Manual paging with `fetch_next_page()` and `has_more`

Both `SearchResults` and `CommentThread` expose two members for explicit page control:

* **`fetch_next_page()`** — loads the next page from YouTube, buffers the new items, and returns them as a list. Returns an empty list when no more pages are available.
* **`has_more`** — `True` as long as a continuation token is available.

```python
from ytscrape import YouTube

with YouTube() as yt:
    results = yt.search("python")

    # Explicitly load one page at a time.
    page = results.fetch_next_page()
    print(f"Loaded {len(page)} more items")
    print(f"More pages available? {results.has_more}")
```

You can mix manual paging with iteration — the iterator picks up exactly where the internal buffer left off, so items are never duplicated or skipped.

### Manual paging for comments

`CommentThread.fetch_next_page()` works identically and returns the comments (and any expanded replies) from the next page:

```python
with YouTube() as yt:
    thread = yt.comments("https://youtu.be/dQw4w9WgXcQ")

    first_batch = thread.fetch_next_page()
    print(f"First page: {len(first_batch)} comments")
    print(f"Has more: {thread.has_more}")

    second_batch = thread.fetch_next_page()
    print(f"Second page: {len(second_batch)} comments")
```

## Collecting everything at once

Materialise the entire result set into a list by wrapping the iterable with `list()`. All pages are fetched synchronously before `list()` returns.

```python
with YouTube() as yt:
    all_results = list(yt.search("python tutorial", filter="videos", max_results=50))
    print(f"Total: {len(all_results)} videos")
```

!!! tip

    Create one `YouTube` instance and reuse it across multiple paginated calls. The instance maintains a warm HTTP session and a cached InnerTube context, avoiding the extra round-trip needed to extract those details on every new `YouTube()` construction.

