"""ytscrape -- YouTube scraper.

The package exposes a high level facade, :class:`YouTube`, together with
the data models and the :class:`SearchFilter` enum::

    from ytscrape import YouTube, SearchFilter

    with YouTube() as yt:
        for video in yt.search("python", filter=SearchFilter.VIDEOS,
                               max_results=20):
            print(video.title, video.url)

        details = yt.video("dQw4w9WgXcQ")
        print(details.title, details.views)

        transcript = yt.transcript("dQw4w9WgXcQ", languages=["en"])
        print(transcript.text)

Async usage (optional ``httpx`` extra)::

    from ytscrape import AsyncYouTube

    async with AsyncYouTube() as yt:
        async for video in await yt.search("python", max_results=10):
            print(video.title)
"""

from __future__ import annotations

from .async_client import AsyncInnerTubeClient
from .async_results import AsyncCommentThread, AsyncSearchResults
from .async_youtube import AsyncYouTube
from .client import InnerTubeClient
from .context import ContextExtractor, InnerTubeContext
from .exceptions import (
    ContextExtractionError,
    NoTranscriptFound,
    ParseError,
    RequestError,
    TranscriptError,
    TranscriptsDisabled,
    YtScraperError,
)
from .filters import CommentSort, SearchFilter
from .locale import Country, Language, Locale
from .models import Channel, ChannelDetails, Comment, Playlist, Video, VideoDetails
from .results import CommentThread, SearchResults
from .transcripts import Transcript, TranscriptList, TranscriptSnippet, TranscriptTrack
from .youtube import YouTube

__version__ = "0.1.5"

__all__ = [
    "YouTube",
    "AsyncYouTube",
    "SearchFilter",
    "CommentSort",
    "Language",
    "Country",
    "Locale",
    "SearchResults",
    "AsyncSearchResults",
    "CommentThread",
    "AsyncCommentThread",
    "Video",
    "Channel",
    "Playlist",
    "VideoDetails",
    "ChannelDetails",
    "Comment",
    "Transcript",
    "TranscriptSnippet",
    "TranscriptTrack",
    "TranscriptList",
    "InnerTubeClient",
    "AsyncInnerTubeClient",
    "InnerTubeContext",
    "ContextExtractor",
    "YtScraperError",
    "ContextExtractionError",
    "RequestError",
    "ParseError",
    "TranscriptError",
    "TranscriptsDisabled",
    "NoTranscriptFound",
    "__version__",
]
