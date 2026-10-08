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

import logging as _logging

from .async_client import AsyncInnerTubeClient
from .async_results import AsyncChannelVideos, AsyncCommentThread, AsyncSearchResults
from .async_youtube import AsyncYouTube
from .client import InnerTubeClient, RateLimiter, RetryPolicy
from .context import ContextCache, ContextExtractor, InnerTubeContext
from .exceptions import (
    AgeRestricted,
    BotDetected,
    CaptchaRequired,
    ConsentRequired,
    ContextExtractionError,
    NoTranscriptFound,
    ParseError,
    RateLimited,
    RequestError,
    TranscriptError,
    TranscriptsDisabled,
    VideoUnavailable,
    YtScrapeError,
    YtScraperError,
)
from .export import dump_csv, dump_json, dumps_csv, dumps_json, to_dict
from .filters import CommentSort, SearchFilter
from .locale import Country, Language, Locale
from .models import (
    Channel,
    ChannelDetails,
    Comment,
    Playlist,
    Thumbnail,
    UnboundModelError,
    Video,
    VideoDetails,
)
from .results import ChannelVideos, CommentThread, SearchResults
from .transcripts import Transcript, TranscriptList, TranscriptSnippet, TranscriptTrack
from .youtube import YouTube

_logging.getLogger("ytscrape").addHandler(_logging.NullHandler())

__version__ = "2.1.0"

__all__ = [
    "AgeRestricted",
    "AsyncChannelVideos",
    "AsyncCommentThread",
    "AsyncInnerTubeClient",
    "AsyncSearchResults",
    "AsyncYouTube",
    "BotDetected",
    "CaptchaRequired",
    "Channel",
    "ChannelDetails",
    "ChannelVideos",
    "Comment",
    "CommentSort",
    "CommentThread",
    "ConsentRequired",
    "ContextCache",
    "ContextExtractionError",
    "ContextExtractor",
    "Country",
    "InnerTubeClient",
    "InnerTubeContext",
    "Language",
    "Locale",
    "NoTranscriptFound",
    "ParseError",
    "Playlist",
    "RateLimited",
    "RateLimiter",
    "RequestError",
    "RetryPolicy",
    "SearchFilter",
    "SearchResults",
    "Thumbnail",
    "Transcript",
    "TranscriptError",
    "TranscriptList",
    "TranscriptSnippet",
    "TranscriptTrack",
    "TranscriptsDisabled",
    "UnboundModelError",
    "Video",
    "VideoDetails",
    "VideoUnavailable",
    "YouTube",
    "YtScrapeError",
    "YtScraperError",
    "__version__",
    "dump_csv",
    "dump_json",
    "dumps_csv",
    "dumps_json",
    "to_dict",
]
