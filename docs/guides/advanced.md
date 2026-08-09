# Configure proxies, retries, and sessions in ytscrape

> Inject a custom requests.Session into InnerTubeClient to configure proxies, automatic retries, timeouts, and testable fake HTTP backends.

`YouTube` is a thin facade over `InnerTubeClient`, which owns the `requests.Session` that performs every HTTP call. Injecting your own session is the single hook for proxies, retries, custom headers, caching, or unit-test mocks — none of the rest of the library needs to change.

## Injecting a custom session

Build your `requests.Session`, configure it, then wrap it in an `InnerTubeClient` and pass that to `YouTube`:

```python
import requests
from ytscrape import YouTube, InnerTubeClient

session = requests.Session()
# ... configure session here ...

client = InnerTubeClient(session=session, language="en", region="US")

with YouTube(client=client) as yt:
    print(next(iter(yt.search("python"))).title)
```

Any option you set on the session — headers, auth, cookies, adapters — is automatically used for every request ytscrape makes.

## Proxies

Set `session.proxies` to route traffic through an HTTP or SOCKS proxy:

```python
import requests
from ytscrape import YouTube, InnerTubeClient

session = requests.Session()
session.proxies = {"https": "http://user:pass@proxy:8080"}

client = InnerTubeClient(session=session, language="en", region="US")

with YouTube(client=client) as yt:
    print(next(iter(yt.search("python"))).title)
```

## Retries with `HTTPAdapter`

Mount an `HTTPAdapter` with a `Retry` policy to automatically retry transient failures:

```python
import requests
from requests.adapters import HTTPAdapter, Retry
from ytscrape import YouTube, InnerTubeClient

session = requests.Session()
session.proxies = {"https": "http://user:pass@proxy:8080"}
session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1)),
)

client = InnerTubeClient(session=session, timeout=15.0, language="en", region="US")

with YouTube(client=client) as yt:
    print(next(iter(yt.search("python"))).title)
```

`backoff_factor=1` means the client waits 1 s, 2 s, 4 s, … between retries. See the [`urllib3` `Retry` documentation](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry) for the full set of options.

## Custom timeout

Pass `timeout` (in seconds) to `InnerTubeClient` to override the default of 30 seconds. This timeout applies to every individual request:

```python
client = InnerTubeClient(timeout=10.0, language="en", region="US")

with YouTube(client=client) as yt:
    details = yt.video("dQw4w9WgXcQ")
```

You can also set `timeout` directly on the default client by passing it to `YouTube`:

```python
with YouTube(timeout=10.0) as yt:
    details = yt.video("dQw4w9WgXcQ")
```

## Using `InnerTubeClient` directly

`InnerTubeClient` exposes the raw InnerTube endpoint wrappers (`search`, `player`, `browse`, `next`) when you need lower-level access. All of them return the parsed JSON dictionary from YouTube's API:

```python
from ytscrape import InnerTubeClient

with InnerTubeClient(language="en", region="US") as client:
    data = client.player("dQw4w9WgXcQ")
    print(data["videoDetails"]["title"])
```

Pass a fully configured `InnerTubeClient` to `YouTube` when you want to share the same session and context across all high-level calls:

```python
client = InnerTubeClient(session=my_session, timeout=15.0)
yt = YouTube(client=client)
```

## Testing with a fake session

Because `InnerTubeClient` accepts any `requests.Session`, you can inject a mock in tests so that no real network call ever happens:

```python
from unittest.mock import MagicMock
import requests
from ytscrape import YouTube, InnerTubeClient

fake_session = MagicMock(spec=requests.Session)
# Configure fake_session.get / .post to return canned responses...

client = InnerTubeClient(session=fake_session)
yt = YouTube(client=client)
# All calls on `yt` now go through your mock.
```

!!! tip

    Reuse a single `YouTube` instance across multiple operations. On the first call, the client fetches the YouTube home page to extract the InnerTube context (API key, client version, visitor data). Reusing the same instance keeps that context warm and avoids an extra round-trip on every subsequent call.


!!! warning

    `requests.Session` is **not thread-safe**. If you run ytscrape from multiple threads, create a separate `YouTube` (and therefore a separate session) per thread rather than sharing one instance.
