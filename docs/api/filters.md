# SearchFilter and CommentSort enums — ytscrape reference

> Reference for the SearchFilter and CommentSort enums that control what result types ytscrape searches for and how comments are ordered and collected.

The `filters` module provides two enumerations that let you express search and comment-ordering intent with self-documenting names instead of raw InnerTube parameter strings. Both classes inherit from `str` and `Enum`, so a plain string such as `"videos"` or `"newest"` is accepted anywhere the enum type is expected.

## `SearchFilter`

`SearchFilter` maps human-readable filter names to the opaque `params` values that the YouTube InnerTube `search` endpoint requires. `ALL` is a special case — it maps to `None`, which tells ytscrape to omit the `params` field from the request payload entirely, returning mixed results just as an unfiltered search would.

### Members

| Member                   | String value  | Description                                                                  |
| ------------------------ | ------------- | ---------------------------------------------------------------------------- |
| `SearchFilter.ALL`       | `"all"`       | No filter applied — returns videos, channels, playlists, and Shorts together |
| `SearchFilter.VIDEOS`    | `"videos"`    | Regular long-form videos only                                                |
| `SearchFilter.CHANNELS`  | `"channels"`  | Channel results only                                                         |
| `SearchFilter.PLAYLISTS` | `"playlists"` | Playlists only                                                               |
| `SearchFilter.SHORTS`    | `"shorts"`    | YouTube Shorts only                                                          |
| `SearchFilter.MOVIES`    | `"movies"`    | Movies only                                                                  |

### Properties

**`params`** (`str | None`)

:   The raw `params` string sent to the InnerTube `search` endpoint. Returns `None` for `SearchFilter.ALL`, which causes the field to be omitted from the request payload. Concrete values for the other members are Base64-encoded strings captured from the YouTube web UI (e.g. `"EgIQAQ=="` for `VIDEOS`).


### Class methods

**`from_value(value)`** (`classmethod`)

:   Coerces a plain string or an existing `SearchFilter` instance into a `SearchFilter`. The string is matched case-insensitively. Raises `ValueError` listing all valid filter names if the value is not recognised.

      **`value`** (`SearchFilter | str`) **required**

    :   The filter to coerce. Pass a `SearchFilter` member to return it unchanged, or a lowercase string such as `"videos"`.


### String coercion

Because `SearchFilter` inherits from `str`, you can pass a plain string wherever a `SearchFilter` is accepted — ytscrape calls `from_value` internally:

```python
import ytscrape

yt = ytscrape.YouTube()

# Enum member
results = yt.search("python tutorial", filter=ytscrape.SearchFilter.VIDEOS)

# Plain string — identical behaviour
results = yt.search("python tutorial", filter="videos")

# Default — no filter
results = yt.search("python tutorial", filter=ytscrape.SearchFilter.ALL)
```

!!! note

    YouTube occasionally changes the Base64 `params` values that back each filter. If a filter stops returning the expected result type, capture a fresh value from the browser DevTools: open the **Network** tab, trigger a filtered search, find the `youtubei/v1/search` request, and copy the `params` field from the POST body. Update `_FILTER_PARAMS` in `filters.py` with the new value.


***

## `CommentSort`

`CommentSort` controls the order in which `YouTube.comments()` collects comments from a video. Unlike `SearchFilter`, the continuation token for each sort order is not a fixed constant — YouTube embeds a fresh, per-video token in the sort menu of the first comments page. `CommentSort` stores the menu title and position that let ytscrape look up the correct token at runtime.

### Members

| Member               | String value | Description                                                                                                                    |
| -------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `CommentSort.TOP`    | `"top"`      | YouTube's default "Top comments" view — surfaces the most relevant comments but may hide less relevant ones and potential spam |
| `CommentSort.NEWEST` | `"newest"`   | "Newest first" view — returns every comment in reverse-chronological order                                                     |

### Properties

**`menu_title`** (`str`)

:   The `sortFilterSubMenuRenderer` item title that identifies this sort order in the YouTube comments response. `TOP` maps to `"Top comments"` and `NEWEST` maps to `"Newest first"`. This title is used at runtime to locate the per-video continuation token.


**`menu_index`** (`int`)

:   The item's zero-based position in the sort sub-menu (`0` for `TOP`, `1` for `NEWEST`). Used alongside `menu_title` for resilient token lookup.


### Class methods

**`from_value(value)`** (`classmethod`)

:   Coerces a plain string or an existing `CommentSort` instance into a `CommentSort`. The string is matched case-insensitively. Raises `ValueError` listing valid values if unrecognised.

      **`value`** (`CommentSort | str`) **required**

    :   The sort order to coerce. Pass a `CommentSort` member to return it unchanged, or a string such as `"newest"`.


!!! warning

    `CommentSort.TOP` mirrors YouTube's "Top comments" default view, which actively hides low-relevance comments and potential spam. If you need to collect **all** comments on a video — for example, for data analysis or archival purposes — use `CommentSort.NEWEST` instead.


### Usage examples

```python
import ytscrape

yt = ytscrape.YouTube()

# Collect every comment in reverse-chronological order
comments = yt.comments("dQw4w9WgXcQ", sort=ytscrape.CommentSort.NEWEST)

# Equivalent plain-string form
comments = yt.comments("dQw4w9WgXcQ", sort="newest")

# Default top-comments view (may omit some comments)
comments = yt.comments("dQw4w9WgXcQ", sort=ytscrape.CommentSort.TOP)
```
