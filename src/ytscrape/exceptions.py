"""Custom exceptions for the ytscrape package."""

from __future__ import annotations


class YtScraperError(Exception):
    """Base exception for all errors raised by ytscrape."""


class ContextExtractionError(YtScraperError):
    """Raised when the InnerTube context cannot be extracted from YouTube."""


class RequestError(YtScraperError):
    """Raised when an HTTP request to YouTube fails."""


class ParseError(YtScraperError):
    """Raised when a YouTube response cannot be parsed as expected."""
