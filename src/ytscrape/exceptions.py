"""Custom exceptions for the ytscrape package."""

from __future__ import annotations

# Public issue tracker — appended to bot-check / block style errors.
GITHUB_ISSUES_URL = "https://github.com/vsmutok/ytscrape/issues"

# Shared advice when YouTube rate-limits, bot-checks, or serves a consent wall.
_BLOCK_MITIGATION_HINT = (
    "Try changing your IP address or using a proxy — that resolves this in "
    f"about 99% of cases. If the problem persists, please open a GitHub issue: "
    f"{GITHUB_ISSUES_URL}"
)


def with_block_mitigation(message: str) -> str:
    """Append IP/proxy + GitHub issue guidance to a block-related error message."""
    base = message.rstrip()
    if not base.endswith((".", "!", "?")):
        base = f"{base}."
    return f"{base} {_BLOCK_MITIGATION_HINT}"


class YtScraperError(Exception):
    """Base exception for all errors raised by ytscrape."""


class ContextExtractionError(YtScraperError):
    """Raised when the InnerTube context cannot be extracted from YouTube."""


class RequestError(YtScraperError):
    """Raised when an HTTP request to YouTube fails."""


class ParseError(YtScraperError):
    """Raised when a YouTube response cannot be parsed as expected."""


class TranscriptError(YtScraperError):
    """Base class for transcript / caption related failures."""


class TranscriptsDisabled(TranscriptError):
    """Raised when a video has no captions (or captions are disabled)."""

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        super().__init__(
            f"Subtitles are disabled for video {video_id!r} "
            "(or no caption tracks were returned)."
        )


class NoTranscriptFound(TranscriptError):
    """Raised when none of the requested languages are available."""

    def __init__(
        self,
        video_id: str,
        requested: tuple[str, ...] | list[str],
        *,
        available: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.video_id = video_id
        self.requested = tuple(requested)
        self.available = tuple(available or ())
        available_txt = ", ".join(self.available) if self.available else "(none listed)"
        super().__init__(
            f"No transcript found for video {video_id!r} in languages "
            f"{list(self.requested)}. Available: {available_txt}."
        )
