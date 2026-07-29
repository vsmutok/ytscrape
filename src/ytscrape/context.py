"""Extraction of the YouTube InnerTube context.

The InnerTube API needs three values that YouTube embeds into the HTML of its
home page: an API key, the client version and the ``visitorData`` token. This
module isolates the scraping of those values behind a small, testable object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["InnerTubeContext", "ContextExtractor"]


@dataclass(frozen=True, slots=True)
class InnerTubeContext:
    """The set of values required to talk to the InnerTube API."""

    api_key: str
    client_version: str
    visitor_data: str


class ContextExtractor:
    """Extract an :class:`InnerTubeContext` from YouTube home page HTML.

    The regular expressions live here so that the networking client only has to
    hand over raw HTML and receive a ready-to-use context back.
    """

    _PATTERNS = {
        "api_key": r'"INNERTUBE_API_KEY":"([^"]+)"',
        "client_version": r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"',
        "visitor_data": r'"(?:VISITOR_DATA|visitorData)":"([^"]+)"',
    }

    def extract(self, html: str) -> InnerTubeContext:
        """Parse ``html`` and return the extracted :class:`InnerTubeContext`.

        Raises:
            ContextExtractionError: If any required value is missing.
        """
        # Imported lazily to keep this module free of package-level cycles.
        from .exceptions import ContextExtractionError

        values: dict[str, str] = {}
        for name, pattern in self._PATTERNS.items():
            match = re.search(pattern, html)
            if not match:
                raise ContextExtractionError(
                    f"Unable to find {name!r} in YouTube response."
                )
            values[name] = match.group(1)

        return InnerTubeContext(
            api_key=values["api_key"],
            client_version=values["client_version"],
            visitor_data=values["visitor_data"],
        )
