# InnerTubeClient — ytscrape Low-Level HTTP Client Reference

> Complete reference for InnerTubeClient — the low-level HTTP layer that drives all InnerTube API calls and session management in ytscrape.

`InnerTubeClient` is the low-level HTTP layer that underpins every network call in ytscrape. It owns the `requests.Session`, lazily bootstraps the InnerTube context (API key, visitor data, client version) from the YouTube home page, and exposes thin wrappers around the `search`, `player`, `browse`, and `next` InnerTube endpoints. It knows nothing about pagination, data models, or response parsing — that logic lives in the higher-level [`YouTube`](youtube.md) facade.

Most users should work exclusively through `YouTube` and never touch `InnerTubeClient` directly. The main reason to instantiate it yourself is to inject a custom `requests.Session` — for example to add proxy routing, retry logic, or a custom `User-Agent` — and then pass it into `YouTube` via the `client` argument.

!!! note

    Unless you have a specific reason to work at the HTTP level, use the
      [`YouTube`](youtube.md) facade instead. It handles pagination, model
      parsing, and resource management for you.


***

## Custom session injection example

The example below wires up an `HTTPAdapter` with automatic retries and an HTTPS proxy, then hands the session to `YouTube` so all scraping goes through it.

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ytscrape import YouTube, InnerTubeClient

retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)

session = requests.Session()
session.mount("https://", adapter)
session.proxies = {"https": "https://user:pass@proxy.example.com:8080"}

client = InnerTubeClient(session=session, timeout=60.0)

with YouTube(client=client) as yt:
    details = yt.video("dQw4w9WgXcQ")
    print(details.title)
```

***

## Constructor

```python
InnerTubeClient(
    *,
    session: requests.Session | None = None,
    user_agent: str = "<Chrome/138 UA string>",
    timeout: float = 30.0,
    locale: Locale | None = None,
    language: Language | str = "en",
    region: Country | str = "US",
    extractor: ContextExtractor | None = None,
)
```

All arguments are keyword-only.

**`session`** (`requests.Session | None`)

:   A pre-configured [`requests.Session`](https://docs.python-requests.org/en/latest/api/#requests.Session)
      to use for all HTTP calls. When omitted a new default session is created. Injecting a custom
      session is the primary reason to instantiate `InnerTubeClient` directly — it lets you add retry
      adapters, proxy configuration, cookie jars, or certificate settings without modifying ytscrape
      internals.


**`user_agent`** (`str`)

:   The `User-Agent` header sent with every request. The default mimics a recent Chrome browser on
      Windows, which is what YouTube expects. Override it only when you have a specific need, such as
      testing or compliance requirements.


**`timeout`** (`float`)

:   Per-request timeout in seconds. Applied to every `GET` and `POST` call made by this client.


**`locale`** (`Locale | None`)

:   A [`Locale`](locale.md) object that bundles language and country together. When provided, the
      `language` and `region` arguments are ignored. Omit it to let the client build a `Locale` from
      the individual `language` and `region` values.


**`language`** (`Language | str`)

:   The `hl` (host language) value embedded in every InnerTube request context. Accepts a
      [`Language`](locale.md) enum member or a raw ISO 639-1 code such as `"fr"` or `"ja"`. Ignored
      when `locale` is provided.


**`region`** (`Country | str`)

:   The `gl` (geolocation) value embedded in every InnerTube request context. Accepts a
      [`Country`](locale.md) enum member or a raw ISO 3166-1 alpha-2 code such as `"GB"` or `"JP"`.
      Ignored when `locale` is provided.


**`extractor`** (`ContextExtractor | None`)

:   A [`ContextExtractor`](innertube-client.md) strategy object used to parse the InnerTube context (API
      key, visitor data, client version) out of the YouTube home page HTML. When omitted the default
      `ContextExtractor` is used. Override for testing or when YouTube changes its initialization
      script format.


***

## Properties

### `locale`

```python
@property
def locale(self) -> Locale
```

The [`Locale`](locale.md) (language + country pair) used for all requests. Set at construction
time from either the `locale` argument or the `language` / `region` pair.

### `context`

```python
@property
def context(self) -> InnerTubeContext
```

The [`InnerTubeContext`](innertube-client.md) holding the API key, visitor data token, and client version
string required for authenticated InnerTube calls. The context is fetched **lazily** on first
access — the client makes a `GET` request to the YouTube home page and parses the initialization
script. Subsequent accesses return the cached value.

!!! note

    The first call to any endpoint method (or to `context` directly) will trigger an HTTP request to
      `https://www.youtube.com` to bootstrap the context. This is normal behaviour.


***

## Methods

### `search`

Call the raw InnerTube `search` endpoint.

```python
def search(
    self,
    query: str | None = None,
    *,
    params: str | None = None,
    continuation: str | None = None,
) -> dict[str, Any]
```

**`query`** (`str | None`)

:   The search query string. Used for the first page of results. Either `query` or `continuation`
      must be provided.


**`params`** (`str | None`)

:   Base64-encoded filter parameters. Constructed by [`SearchFilter`](filters.md) and passed
      through as-is to the InnerTube payload. Omit for unfiltered results.


**`continuation`** (`str | None`)

:   Opaque continuation token for fetching subsequent pages. When provided, `query` and `params` are
      ignored.


**Returns:** `dict[str, Any]` — raw InnerTube JSON response. Pass to `SearchResults` or parse
manually.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

# First page — raw response dict
first_page = client.search("python tutorial")
print(type(first_page))  # <class 'dict'>

client.close()
```

***

### `player`

Call the raw InnerTube `player` endpoint for a single video.

```python
def player(
    self,
    video_id: str,
    *,
    client_name: str = "WEB",
) -> dict[str, Any]
```

**`video_id`** (`str`) **required**

:   The 11-character YouTube video id.


**`client_name`** (`str`)

:   The InnerTube client identity to send. `"WEB"` is used for standard metadata. `"ANDROID"` is
      preferred for caption track lists, as it exposes them more reliably (the same approach used by
      youtube-transcript-api).


**Returns:** `dict[str, Any]` — raw InnerTube player response containing video metadata, streaming
URLs, and caption track manifests.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

response = client.player("dQw4w9WgXcQ")
print(response["videoDetails"]["title"])

# Use ANDROID client for captions
caption_response = client.player("dQw4w9WgXcQ", client_name="ANDROID")
tracks = caption_response.get("captions", {})

client.close()
```

***

### `browse`

Call the raw InnerTube `browse` endpoint, used for channels, tabs, and shelves.

```python
def browse(
    self,
    browse_id: str,
    *,
    params: str | None = None,
    continuation: str | None = None,
) -> dict[str, Any]
```

**`browse_id`** (`str`) **required**

:   The channel or tab id to browse (typically a `UC…` channel id). Either `browse_id` or
      `continuation` must drive the call — when `continuation` is provided, `browse_id` and `params`
      are ignored.


**`params`** (`str | None`)

:   Base64-encoded parameters for selecting a specific tab or continuation within a channel page.


**`continuation`** (`str | None`)

:   Opaque continuation token for fetching subsequent pages of a browse result.


**Returns:** `dict[str, Any]` — raw InnerTube browse response.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

# Fetch a channel's home tab
response = client.browse("UCVHFbw7woebKtFFkLgYnoBg")
print(response.keys())

client.close()
```

***

### `next`

Call the raw InnerTube `next` endpoint, used for the watch page and comment threads.

```python
def next(
    self,
    video_id: str | None = None,
    *,
    continuation: str | None = None,
) -> dict[str, Any]
```

**`video_id`** (`str | None`)

:   The 11-character video id. Used to load the watch-page data, which contains the initial
      continuation token that opens the comments section. Either `video_id` or `continuation` must be
      provided.


**`continuation`** (`str | None`)

:   Opaque continuation token for fetching comment threads, individual reply threads, or additional
      pages of comments. When provided, `video_id` is ignored.


**Returns:** `dict[str, Any]` — raw InnerTube next response.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

# Load watch page to obtain the comments continuation token
watch_response = client.next("dQw4w9WgXcQ")
print(watch_response.keys())

client.close()
```

***

### `get_html`

Fetch an arbitrary YouTube page and return its full HTML body.

```python
def get_html(self, url: str) -> str
```

**`url`** (`str`) **required**

:   The full URL of a YouTube page (e.g. a channel or user page) to fetch.


**Returns:** `str` — the raw HTML response body. Raises `RequestError` on any HTTP or network
error.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

html = client.get_html("https://www.youtube.com/@RickAstleyYT")
print(html[:500])

client.close()
```

***

### `get_text`

Fetch an arbitrary URL and return the response body as plain text.

```python
def get_text(self, url: str) -> str
```

**`url`** (`str`) **required**

:   The full URL to fetch. Primarily used internally to download timedtext XML caption files, but
      available for any text resource.


**Returns:** `str` — the response body decoded as text. Raises `RequestError` on any HTTP or
network error.

```python
from ytscrape import InnerTubeClient

client = InnerTubeClient()

# Download a timedtext / caption XML file directly
xml = client.get_text("https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=en")
print(xml[:300])

client.close()
```

***

### `close`

Close the underlying `requests.Session` and release all associated resources.

```python
def close(self) -> None
```

**Returns:** `None`

!!! tip

    `InnerTubeClient` also implements the context manager protocol (`__enter__` / `__exit__`), so
      you can use `with InnerTubeClient() as client: …` and have the session closed automatically.
      When you pass a client to `YouTube`, let `YouTube` manage the lifecycle instead.


```python
from ytscrape import InnerTubeClient

with InnerTubeClient(timeout=60.0) as client:
    response = client.player("dQw4w9WgXcQ")
    print(response["videoDetails"]["title"])
# Session is closed automatically here
```

***

## AsyncInnerTubeClient

Async low-level HTTP layer backed by `httpx.AsyncClient`. Mirrors `InnerTubeClient` endpoint wrappers (`search`, `player`, `browse`, `next`, `get_html`, `get_text`) as coroutines, and adds:

* **`max_concurrency`** — `asyncio.Semaphore` limiting in-flight requests
* **`max_retries` / `backoff_factor`** — exponential backoff with jitter on retryable statuses (408, 425, 429, 500, 502, 503, 504)

Install: `pip install "ytscrape[async]"`.

```python
import asyncio
from ytscrape import AsyncInnerTubeClient, AsyncYouTube


async def main() -> None:
    async with AsyncInnerTubeClient(
        max_concurrency=8,
        max_retries=3,
        backoff_factor=0.5,
        timeout=30.0,
        language="en",
        region="US",
    ) as client:
        data = await client.player("dQw4w9WgXcQ")
        print(data["videoDetails"]["title"])

        # Or hand the client to the high-level facade:
        async with AsyncYouTube(client=client) as yt:
            details = await yt.video("dQw4w9WgXcQ")
            print(details.title)


asyncio.run(main())
```

### Constructor (async-specific)

```python
AsyncInnerTubeClient(
    *,
    session: httpx.AsyncClient | None = None,
    user_agent: str = "<Chrome UA>",
    timeout: float = 30.0,
    locale: Locale | None = None,
    language: Language | str = "en",
    region: Country | str = "US",
    extractor: ContextExtractor | None = None,
    max_concurrency: int = 8,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
)
```

Inject a custom `httpx.AsyncClient` (proxies, custom transports, timeouts) via `session=`. Prefer letting `AsyncYouTube` own the client lifecycle when using the facade.

Most application code should use [`AsyncYouTube`](youtube.md) rather than calling InnerTube endpoints directly. Guide: [Async API](../guides/async.md).
