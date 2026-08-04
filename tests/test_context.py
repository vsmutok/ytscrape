"""Tests for the InnerTube context extraction."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ytscrape import ContextExtractionError, ContextExtractor, InnerTubeContext

_VALID_HTML = (
    "<html><head><script>ytcfg.set({"
    '"INNERTUBE_API_KEY":"AIzaTESTKEY",'
    '"INNERTUBE_CLIENT_VERSION":"2.20240101.00.00",'
    '"VISITOR_DATA":"CgtWaXNpdG9yRGF0YQ%3D%3D"'
    "});</script></head></html>"
)


class TestContextExtractor:
    def test_extracts_all_values(self) -> None:
        context = ContextExtractor().extract(_VALID_HTML)
        assert isinstance(context, InnerTubeContext)
        assert context.api_key == "AIzaTESTKEY"
        assert context.client_version == "2.20240101.00.00"
        assert context.visitor_data == "CgtWaXNpdG9yRGF0YQ%3D%3D"

    def test_accepts_lowercase_visitor_data_key(self) -> None:
        html = _VALID_HTML.replace("VISITOR_DATA", "visitorData")
        context = ContextExtractor().extract(html)
        assert context.visitor_data == "CgtWaXNpdG9yRGF0YQ%3D%3D"

    def test_missing_api_key_raises(self) -> None:
        html = _VALID_HTML.replace("INNERTUBE_API_KEY", "SOMETHING_ELSE")
        with pytest.raises(ContextExtractionError, match="api_key"):
            ContextExtractor().extract(html)

    def test_missing_client_version_raises(self) -> None:
        html = _VALID_HTML.replace("INNERTUBE_CLIENT_VERSION", "SOMETHING_ELSE")
        with pytest.raises(ContextExtractionError, match="client_version"):
            ContextExtractor().extract(html)

    def test_missing_visitor_data_raises(self) -> None:
        html = _VALID_HTML.replace("VISITOR_DATA", "SOMETHING_ELSE")
        with pytest.raises(ContextExtractionError, match="visitor_data"):
            ContextExtractor().extract(html)

    def test_empty_html_raises(self) -> None:
        with pytest.raises(ContextExtractionError):
            ContextExtractor().extract("")


class TestInnerTubeContext:
    def test_is_frozen(self) -> None:
        context = InnerTubeContext(api_key="k", client_version="v", visitor_data="d")
        with pytest.raises(FrozenInstanceError):
            context.api_key = "other"  # type: ignore[misc]
