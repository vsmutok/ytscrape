"""ytscrape -- YouTube scraper.

The package exposes a single high level facade, :class:`YouTube`, together with
the data models and the :class:`SearchFilter` enum::

    from ytscrape import YouTube, SearchFilter

    with YouTube() as yt:
        for video in yt.search("python", filter=SearchFilter.VIDEOS,
                               max_results=20):
            print(video.title, video.url)

        details = yt.video("dQw4w9WgXcQ")
        print(details.title, details.views)
"""

from __future__ import annotations

from .client import InnerTubeClient
from .context import ContextExtractor, InnerTubeContext
from .exceptions import (
    ContextExtractionError,
    ParseError,
    RequestError,
    YtScraperError,
)
from .filters import CommentSort, SearchFilter
from .locale import Country, Language, Locale
from .models import Channel, Comment, Playlist, Video, VideoDetails
from .results import CommentThread, SearchResults
from .youtube import YouTube

__version__ = "0.1.2"

__all__ = [
    "YouTube",
    "SearchFilter",
    "CommentSort",
    "Language",
    "Country",
    "Locale",
    "SearchResults",
    "CommentThread",
    "Video",
    "Channel",
    "Playlist",
    "VideoDetails",
    "Comment",
    "InnerTubeClient",
    "InnerTubeContext",
    "ContextExtractor",
    "YtScraperError",
    "ContextExtractionError",
    "RequestError",
    "ParseError",
    "__version__",
]
