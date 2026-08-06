"""Tests for the :class:`InnerTubeClient` using a fake HTTP session."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from ytscrape import InnerTubeClient, RequestError

_HOME_HTML = """
    "INNERTUBE_API_KEY":"KEY",
    "INNERTUBE_CLIENT_VERSION":"1.2.3",
    "VISITOR_DATA":"VD"
"""


class FakeResponse:
    def __init__(
        self,
        *,
        text: str = "",
        json_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.text = text
        self._json = json_data or {}
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self) -> dict[str, Any]:
        return self._json


class FakeSession:
    """Records requests and serves canned responses."""

    def __init__(
        self,
        *,
        get_response: FakeResponse | None = None,
        post_response: FakeResponse | None = None,
    ) -> None:
        self._get_response = get_response or FakeResponse(text=_HOME_HTML)
        self._post_response = post_response or FakeResponse(json_data={"ok": True})
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []
        self.closed = False

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        return self._get_response

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.post_calls.append({"url": url, **kwargs})
        return self._post_response

    def close(self) -> None:
        self.closed = True


class TestContext:
    def test_context_is_fetched_and_cached(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        context = client.context
        assert context.api_key == "KEY"
        assert context.client_version == "1.2.3"
        assert context.visitor_data == "VD"
        # A second access must not trigger another GET.
        _ = client.context
        assert len(session.get_calls) == 1

    def test_context_fetch_failure_raises_request_error(self) -> None:
        session = FakeSession(
            get_response=FakeResponse(raise_exc=requests.RequestException("boom"))
        )
        client = InnerTubeClient(session=session)
        with pytest.raises(RequestError, match="Failed to load YouTube home page"):
            _ = client.context


class TestLocale:
    def test_default_locale(self) -> None:
        client = InnerTubeClient(session=FakeSession())
        assert client.locale.language.code == "en"
        assert client.locale.country.code == "US"

    def test_custom_language_and_region(self) -> None:
        client = InnerTubeClient(session=FakeSession(), language="uk", region="UA")
        assert client.locale.language.code == "uk"
        assert client.locale.country.code == "UA"

    def test_accept_language_header_sent(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session, language="uk", region="UA")
        _ = client.context
        assert session.get_calls[0]["headers"]["Accept-Language"] == "uk-UA,uk;q=0.9"


class TestSearch:
    def test_search_query_payload(self) -> None:
        session = FakeSession(post_response=FakeResponse(json_data={"r": 1}))
        client = InnerTubeClient(session=session)
        result = client.search("python", params="EgIQAQ==")
        assert result == {"r": 1}
        payload = session.post_calls[0]["json"]
        assert payload["query"] == "python"
        assert payload["params"] == "EgIQAQ=="
        assert "continuation" not in payload

    def test_search_continuation_payload(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.search(continuation="TOKEN")
        payload = session.post_calls[0]["json"]
        assert payload["continuation"] == "TOKEN"
        assert "query" not in payload

    def test_search_omits_params_when_none(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.search("python", params=None)
        payload = session.post_calls[0]["json"]
        assert "params" not in payload

    def test_client_context_contains_locale(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session, language="de", region="DE")
        client.search("query")
        client_ctx = session.post_calls[0]["json"]["context"]["client"]
        assert client_ctx["hl"] == "de"
        assert client_ctx["gl"] == "DE"
        assert client_ctx["clientVersion"] == "1.2.3"

    def test_post_failure_raises_request_error(self) -> None:
        session = FakeSession(
            post_response=FakeResponse(raise_exc=requests.RequestException("nope"))
        )
        client = InnerTubeClient(session=session)
        with pytest.raises(RequestError, match="Request to 'search' failed"):
            client.search("python")


class TestPlayer:
    def test_player_payload(self) -> None:
        session = FakeSession(post_response=FakeResponse(json_data={"p": 1}))
        client = InnerTubeClient(session=session)
        result = client.player("vid123")
        assert result == {"p": 1}
        payload = session.post_calls[0]["json"]
        assert payload["videoId"] == "vid123"
        assert "context" in payload


class TestBrowse:
    def test_browse_payload(self) -> None:
        session = FakeSession(post_response=FakeResponse(json_data={"b": 1}))
        client = InnerTubeClient(session=session)
        result = client.browse("UCxxxxxxxxxxxxxxxxxxxxxx")
        assert result == {"b": 1}
        payload = session.post_calls[0]["json"]
        assert payload["browseId"] == "UCxxxxxxxxxxxxxxxxxxxxxx"
        assert "continuation" not in payload
        assert session.post_calls[0]["url"].endswith("browse?key=KEY")

    def test_browse_with_params(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.browse("UCxxxxxxxxxxxxxxxxxxxxxx", params="PARAMS")
        payload = session.post_calls[0]["json"]
        assert payload["params"] == "PARAMS"

    def test_browse_continuation_payload(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.browse("ignored", continuation="TOKEN")
        payload = session.post_calls[0]["json"]
        assert payload["continuation"] == "TOKEN"
        assert "browseId" not in payload


class TestGetHtml:
    def test_get_html_returns_text(self) -> None:
        session = FakeSession(get_response=FakeResponse(text="<html>channel</html>"))
        client = InnerTubeClient(session=session)
        assert client.get_html("https://www.youtube.com/@x") == "<html>channel</html>"
        assert session.get_calls[-1]["url"] == "https://www.youtube.com/@x"

    def test_get_html_failure_raises_request_error(self) -> None:
        session = FakeSession(
            get_response=FakeResponse(raise_exc=requests.RequestException("boom"))
        )
        client = InnerTubeClient(session=session)
        with pytest.raises(RequestError, match="Failed to load"):
            client.get_html("https://www.youtube.com/@x")


class TestNext:
    def test_next_video_id_payload(self) -> None:
        session = FakeSession(post_response=FakeResponse(json_data={"n": 1}))
        client = InnerTubeClient(session=session)
        result = client.next("vid123")
        assert result == {"n": 1}
        payload = session.post_calls[0]["json"]
        assert payload["videoId"] == "vid123"
        assert "continuation" not in payload
        assert session.post_calls[0]["url"].endswith("next?key=KEY")

    def test_next_continuation_payload(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.next(continuation="TOKEN")
        payload = session.post_calls[0]["json"]
        assert payload["continuation"] == "TOKEN"
        assert "videoId" not in payload


class TestLifecycle:
    def test_close_closes_session(self) -> None:
        session = FakeSession()
        client = InnerTubeClient(session=session)
        client.close()
        assert session.closed is True

    def test_context_manager(self) -> None:
        session = FakeSession()
        with InnerTubeClient(session=session) as client:
            assert client is not None
        assert session.closed is True
