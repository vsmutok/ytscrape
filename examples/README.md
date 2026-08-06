# Examples

Short, runnable examples showing how to use **ytscrape**.

Install the package first:

```bash
pip install ytscrape
```

Then run any example from the repository root:

```bash
python examples/01_search_videos.py
python examples/02_search_channels_playlists.py
python examples/03_video_details.py
python examples/04_pagination.py
python examples/05_language_region.py
python examples/06_error_handling.py
python examples/07_video_comments.py
python examples/08_channel_details.py
python examples/09_transcript.py
```

| Example                                | What it shows                                             |
| -------------------------------------- | --------------------------------------------------------- |
| `01_search_videos.py`                  | Search for videos with `SearchFilter.VIDEOS`.             |
| `02_search_channels_playlists.py`      | Search for channels and playlists.                        |
| `03_video_details.py`                  | Fetch detailed metadata for a single video (id or URL).   |
| `04_pagination.py`                     | Iterate transparently or page manually.                   |
| `05_language_region.py`                | Localise results by interface language and region.        |
| `06_error_handling.py`                 | Handle `ytscrape` exceptions gracefully.                  |
| `07_video_comments.py`                 | Collect all comments (and replies) of a video.            |
| `08_channel_details.py`                | Fetch detailed metadata for a single channel.             |
| `09_transcript.py`                     | List caption tracks and fetch a video transcript.         |

> These examples hit YouTube's private endpoints and require a network
> connection. Use the library responsibly.
