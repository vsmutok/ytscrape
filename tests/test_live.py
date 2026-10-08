"""Live smoke tests against the real YouTube.

Skipped by default. Run with::

    uv run pytest --run-network -m network

They check the *shape* of the data (types, non-empty fields), not exact
values, so changing view counts do not break them.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest

from ytscrape import Thumbnail, VideoUnavailable, YouTube

pytestmark = pytest.mark.network

VIDEO_ID = "dQw4w9WgXcQ"
CHANNEL = "@RickAstleyYT"
CHANNEL_ID = "UCuAXFkgsw1L7xaCfnd5JJOw"


def _assert_thumbnails(thumbnails: tuple[Thumbnail, ...]) -> None:
    assert thumbnails
    for thumb in thumbnails:
        assert isinstance(thumb, Thumbnail)
        assert thumb.url.startswith("https://")
        assert thumb.width is None or thumb.width > 0
        assert thumb.height is None or thumb.height > 0


def _assert_country_codes(codes: tuple[str, ...]) -> None:
    assert codes
    assert all(isinstance(c, str) and len(c) == 2 and c.isupper() for c in codes)


@pytest.fixture(scope="module")
def yt() -> Iterator[YouTube]:
    with YouTube(language="en", region="US") as client:
        yield client


def test_search(yt: YouTube) -> None:
    videos = list(yt.search("python tutorial", max_results=5))
    assert videos
    assert all(v.title for v in videos)
    assert any(isinstance(getattr(v, "views", None), int) for v in videos)


def test_video_details(yt: YouTube) -> None:
    details = yt.video(VIDEO_ID)

    # Identity
    assert details.video_id == VIDEO_ID
    assert details.url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert details.title
    assert "Never Gonna Give You Up" in details.title
    assert details.description

    # Channel
    assert details.channel == "Rick Astley"
    assert details.channel_id == CHANNEL_ID
    assert details.owner_profile_url
    assert "youtube.com/" in details.owner_profile_url

    # Counters
    assert isinstance(details.length_seconds, int)
    assert 200 < details.length_seconds < 230
    assert isinstance(details.views, int)
    assert details.views > 1_000_000_000

    # Publication date: "Never Gonna Give You Up" was published on
    # 2009-10-25 UTC (2009-10-24 in UTC-7, as YouTube reports it).
    assert isinstance(details.published, str)
    assert isinstance(details.published_at, datetime)
    assert details.published_at.tzinfo is not None
    assert details.published_at.year == 2009
    assert details.published_at.month == 10
    assert details.published_at.day in (24, 25)
    assert isinstance(details.upload_date, str)
    assert isinstance(details.uploaded_at, datetime)
    assert details.uploaded_at.tzinfo is not None
    assert details.uploaded_at.year == 2009

    # Media
    assert details.thumbnail
    assert details.thumbnail.startswith("https://")
    _assert_thumbnails(details.thumbnails)
    assert details.embed_url == f"https://www.youtube.com/embed/{VIDEO_ID}"

    # Metadata
    assert details.keywords
    assert all(isinstance(k, str) and k for k in details.keywords)
    assert details.category == "Music"
    _assert_country_codes(details.available_countries)
    assert "US" in details.available_countries

    # Flags
    assert details.is_live is False
    assert details.is_private is False
    assert details.is_upcoming is False
    assert details.scheduled_at is None
    assert details.allow_ratings is True
    assert details.is_family_safe is True


def test_channel(yt: YouTube) -> None:
    channel = yt.channel(CHANNEL)

    # Identity
    assert channel.channel_id == CHANNEL_ID
    assert channel.title == "Rick Astley"
    assert channel.handle == CHANNEL
    assert channel.description
    assert channel.vanity_url == f"https://www.youtube.com/{CHANNEL}"
    assert channel.rss_url == (
        f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    )

    # Counters (integers plus YouTube's raw wording)
    assert isinstance(channel.subscribers, int)
    assert channel.subscribers > 1_000_000
    assert channel.subscribers_text
    assert "subscriber" in channel.subscribers_text
    assert isinstance(channel.video_count, int)
    assert channel.video_count > 100
    assert channel.video_count_text
    assert "video" in channel.video_count_text
    assert isinstance(channel.view_count, int)
    assert channel.view_count > 1_000_000_000
    assert channel.view_count_text
    assert "view" in channel.view_count_text

    # Images
    assert channel.photo
    assert channel.photo.startswith("https://")
    assert channel.thumbnail == channel.photo
    _assert_thumbnails(channel.thumbnails)
    assert channel.banner
    assert channel.banner.startswith("https://")

    # Metadata
    assert channel.keywords
    assert all(isinstance(k, str) and k for k in channel.keywords)
    assert channel.tags
    assert all(isinstance(t, str) and t for t in channel.tags)
    assert channel.is_family_safe is True
    _assert_country_codes(channel.available_countries)

    # About panel
    assert channel.country == "United Kingdom"
    assert channel.joined_date
    assert "2015" in channel.joined_date
    assert channel.links
    for name, link in channel.links.items():
        assert isinstance(name, str)
        assert name
        assert isinstance(link, str)
        assert link.startswith("http")


def test_channel_videos(yt: YouTube) -> None:
    videos = list(yt.channel_videos(CHANNEL, max_results=5))
    assert videos
    assert all(v.video_id for v in videos)


def test_comments(yt: YouTube) -> None:
    comments = list(yt.comments(VIDEO_ID, max_results=5))
    assert comments
    assert all(c.text for c in comments)


def test_transcript(yt: YouTube) -> None:
    transcript = yt.transcript(VIDEO_ID)
    assert list(transcript)


def test_unavailable_video(yt: YouTube) -> None:
    with pytest.raises(VideoUnavailable):
        yt.video("aaaaaaaaaaa")
