---
description: "Run the optional ytscrape MCP server (`ytscrape[mcp]`, `ytscrape-mcp`) so Claude, Cursor, VS Code and other MCP clients can search YouTube, read comments and fetch transcripts."
---

# Serve ytscrape over MCP (Model Context Protocol)

> Run the optional `ytscrape[mcp]` server so Claude, Cursor, VS Code and other MCP clients can search YouTube, read comments and fetch transcripts.

ytscrape ships an optional [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the [`YouTube`](../api/youtube.md) facade as **read-only tools** for AI clients. It is built on the official Python MCP SDK and needs no API key or quota.

## Install the optional extra

MCP support depends on the [`mcp`](https://pypi.org/project/mcp/) SDK. It is **not** installed with the base package:

=== "pip"

    ```bash
    pip install "ytscrape[mcp]"
    ```

=== "uv"

    ```bash
    uv add "ytscrape[mcp]"
    ```

## Tools

| Tool | Maps to | Notes |
| ---- | ------- | ----- |
| `search_videos` | `YouTube.search` | `filter` selects videos / channels / playlists / Shorts / movies |
| `get_video` | `YouTube.video` | accepts a video id or any watch URL |
| `get_channel` | `YouTube.channel` | accepts an id, `@handle` or channel URL |
| `get_channel_videos` | `YouTube.channel_videos` | a channel's uploads (Videos tab) |
| `get_comments` | `YouTube.comments` | `sort="newest"` collects *every* comment; `include_replies` adds replies |
| `get_transcript` | `YouTube.transcript` | plain text, plus timed snippets with `include_timestamps` |
| `list_transcripts` | `YouTube.transcripts` | available caption tracks |

All tools return JSON-friendly dictionaries and are annotated as read-only
(`readOnlyHint`, `openWorldHint`, `idempotentHint`), so clients can auto-approve
them safely. ytscrape errors (bot detection, rate limits, unavailable videos,
disabled comments, …) surface to the client as readable tool errors instead of
opaque failures.

`filter` and `sort` are enums (`all` / `videos` / `channels` / `playlists` /
`shorts` / `movies`, and `top` / `newest`). `detail` is `concise` or `full`.

## Limits

The server is sized for an agent's context window, not for bulk export. These
ceilings are hard — they are not configuration flags.

| Limit | Value | What happens if you exceed it |
| ----- | ----- | ----------------------------- |
| `max_results` | **50** per call | Clamped to 50. `hint` says so. The extra items are **not** fetched. |
| Response size | **16 000** characters of JSON | `truncated: true` and a `hint`. The call still succeeds. |
| Description preview | **400** characters | `get_video` / `get_channel` with `detail="concise"` shorten `description`. |
| Cursor | opaque string | Must be the previous `next_cursor`, unchanged. Anything else is a tool error. |
| Cursor depth | **1 000** items | Cursors past that offset are a tool error: pagination re-reads the listing from the start, so it is intentionally shallow. |

`max_results` must be at least 1. It is a **page size**, not "how many items
exist". Asking for 1 000 comments does not return 1 000 comments.

### Pagination

List tools (`search_videos`, `get_channel_videos`, `get_comments`,
`list_transcripts`) and `get_transcript` return the same envelope:

```json
{
  "items": [],
  "count": 0,
  "has_more": true,
  "next_cursor": "bzoxMA",
  "truncated": false
}
```

`count` is how many items are **in this page**, not the total on YouTube.
When `has_more` is true, call the same tool again with `cursor` set to
`next_cursor`. Do not raise `max_results` to "get the rest" — the cap will
clamp it, and a bigger page is more likely to be cut for size.

Pagination is offset-based: every page re-reads the listing from the start and
skips to the cursor. Deeper pages therefore cost more YouTube requests, and
cursors past 1 000 items are rejected — start a new listing instead.
`list_transcripts` returns the same envelope, but track lists are short:
`has_more` is always `false` and `next_cursor` is `null`.

`get_transcript` pages by caption snippets, not by a character budget you
choose. `has_more` / `next_cursor` work the same way. Omit
`include_timestamps` (or set it to `false`) and pass a narrower `languages`
list when you only need the text.

### When a response is truncated

`truncated: true` means this page was cut so it would fit 16 000 characters.
`hint` names the next step. Typical hints:

- pass `next_cursor` instead of raising `max_results`
- `include_timestamps=false`, or a narrower `languages`, for a long transcript
- `detail="concise"` (the default) instead of `detail="full"`

A single caption snippet longer than the page is cut mid-text; its `hint` says
the rest of that snippet is not repeated, and `next_cursor` continues with the
following snippet.

`detail="full"` on `get_video` / `get_channel` still sits under the same
16 000-character ceiling: bulky fields are dropped and the longest string is
shortened rather than failing the call. List rows never include thumbnails,
keywords, descriptions, tags or country lists — those fields belong on
`get_video` / `get_channel`.

## Configure an MCP client

The server speaks **stdio** by default. Point any MCP client at the console
script:

=== "Claude Code / Claude Desktop"

    ```json
    {
      "mcpServers": {
        "ytscrape": {
          "command": "ytscrape-mcp"
        }
      }
    }
    ```

=== "Cursor / VS Code"

    ```json
    {
      "mcpServers": {
        "ytscrape": {
          "command": "ytscrape-mcp",
          "args": ["--language", "en", "--region", "US"]
        }
      }
    }
    ```

Prefer a pinned install? Use `uvx` or `pipx` style commands:

```json
{
  "mcpServers": {
    "ytscrape": {
      "command": "uvx",
      "args": ["--from", "ytscrape[mcp]", "ytscrape-mcp"]
    }
  }
}
```

Running from a source checkout works too:

```bash
python -m ytscrape.mcp_server
```

## Options

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--language` | `en` | Interface language (`hl`), e.g. `uk`, `de` |
| `--region` | `US` | Content region (`gl`), e.g. `UA`, `DE` |
| `--timeout` | `30` | Per-request timeout in seconds |
| `--proxy` | – | Route requests through one proxy URL (HTTP *and* HTTPS) |
| `--http-proxy` | – | Proxy for HTTP requests only (overrides `--proxy`) |
| `--https-proxy` | – | Proxy for HTTPS requests only (overrides `--proxy`) |
| `--transport` | `stdio` | `stdio`, `streamable-http` or `sse` |
| `--host` / `--port` | `127.0.0.1` / `8000` | Bind address for HTTP transports |

## Behind a proxy (IP blocks)

YouTube sometimes rate-limits or bot-checks individual IPs (cloud hosts,
VPNs, heavy usage). Standard HTTP/HTTPS proxies fix this in most cases:

=== "Environment variables (recommended)"

    The underlying `requests` session honours the usual variables, so no flags
    are needed — `NO_PROXY` keeps working too:

    ```json
    {
      "mcpServers": {
        "ytscrape": {
          "command": "ytscrape-mcp",
          "env": {
            "HTTPS_PROXY": "http://username:password@proxy.example.com:8080"
          }
        }
      }
    }
    ```

=== "CLI flags"

    ```json
    {
      "mcpServers": {
        "ytscrape": {
          "command": "ytscrape-mcp",
          "args": [
            "--https-proxy",
            "http://username:password@proxy.example.com:8080"
          ]
        }
      }
    }
    ```

    Use `--proxy` to send both HTTP and HTTPS through one endpoint; explicit
    flags take precedence over environment variables. Without any proxy
    configuration the server connects directly.

## Hosted / HTTP mode

For containerised or remote deployments, serve Streamable HTTP:

```bash
ytscrape-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

MCP clients then connect to `http://<host>:8000/mcp`. SSE is available with
`--transport sse` for older clients that require it.

> ⚠️ **Do not expose this server to the internet without authentication.**
> HTTP transports have no auth of their own. Binding `--host 0.0.0.0` (or any
> public address) hands anyone who can reach the port an open YouTube scraper.
> Keep the default `127.0.0.1` for local use, or put the process behind your
> own authenticated reverse proxy. stdio does not have this problem.

## Example prompts

Once connected, plain-language requests are enough:

- “Search YouTube for *python asyncio tutorial* and summarise the top three videos.”
- “Read the newest comments (replies included) on `dQw4w9WgXcQ` and cluster them by sentiment.”
- “Fetch the transcript of this video and write a blog outline: https://youtu.be/…”

> ⚠️ The MCP server uses the same private endpoints as the library. Use it
> responsibly — see the note in the [README](https://github.com/vsmutok/ytscrape#readme).
