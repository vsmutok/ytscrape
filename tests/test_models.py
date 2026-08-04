"""Tests for the data models and their factory methods."""

from __future__ import annotations

from ytscrape import Channel, Playlist, Video, VideoDetails


class TestVideoUrl:
    def test_url(self) -> None:
        assert (
            Video(video_id="dQw4w9WgXcQ").url
            == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )


class TestVideoFromRenderer:
    def test_full_renderer(self) -> None:
        renderer = {
            "videoId": "abc12345678",
            "title": {"runs": [{"text": "Hello "}, {"text": "World"}]},
            "ownerText": {
                "runs": [
                    {
                        "text": "Cool Channel",
                        "navigationEndpoint": {
                            "browseEndpoint": {"browseId": "UC12345"}
                        },
                    }
                ]
            },
            "lengthText": {"simpleText": "3:14"},
            "viewCountText": {"simpleText": "1,234 views"},
            "publishedTimeText": {"simpleText": "2 days ago"},
            "thumbnail": {
                "thumbnails": [
                    {"url": "http://small.jpg"},
                    {"url": "http://large.jpg"},
                ]
            },
        }
        video = Video.from_renderer(renderer)
        assert video.video_id == "abc12345678"
        assert video.title == "Hello World"
        assert video.channel == "Cool Channel"
        assert video.channel_id == "UC12345"
        assert video.duration == "3:14"
        assert video.views == "1,234 views"
        assert video.published == "2 days ago"
        assert video.thumbnail == "http://large.jpg"

    def test_empty_renderer_uses_defaults(self) -> None:
        video = Video.from_renderer({})
        assert video.video_id == ""
        assert video.title is None
        assert video.channel is None
        assert video.channel_id is None
        assert video.thumbnail is None

    def test_uses_long_byline_when_owner_missing(self) -> None:
        renderer = {
            "videoId": "id",
            "longBylineText": {"runs": [{"text": "By Line"}]},
        }
        video = Video.from_renderer(renderer)
        assert video.channel == "By Line"


class TestVideoFromLockup:
    def test_video_lockup(self) -> None:
        lockup = {
            "contentId": "vid123",
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": "Lockup Title"},
                    "metadata": {
                        "contentMetadataViewModel": {
                            "metadataRows": [
                                {
                                    "metadataParts": [
                                        {
                                            "text": {
                                                "content": "Channel Name",
                                                "commandRuns": [
                                                    {
                                                        "onTap": {
                                                            "innertubeCommand": {
                                                                "browseEndpoint": {
                                                                    "browseId": (
                                                                        "UCxyz"
                                                                    )
                                                                }
                                                            }
                                                        }
                                                    }
                                                ],
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                }
            },
            "contentImage": {
                "thumbnailViewModel": {
                    "image": {"sources": [{"url": "https://thumb.jpg"}]}
                }
            },
        }
        video = Video.from_lockup(lockup)
        assert video.video_id == "vid123"
        assert video.title == "Lockup Title"
        assert video.channel == "Channel Name"
        assert video.channel_id == "UCxyz"
        assert video.thumbnail == "https://thumb.jpg"


class TestChannel:
    def test_url(self) -> None:
        assert (
            Channel(channel_id="UC123").url == "https://www.youtube.com/channel/UC123"
        )

    def test_from_renderer(self) -> None:
        renderer = {
            "channelId": "UC999",
            "title": {"simpleText": "My Channel"},
            "videoCountText": {"simpleText": "100 videos"},
            "thumbnail": {"thumbnails": [{"url": "http://ch.jpg"}]},
        }
        channel = Channel.from_renderer(renderer)
        assert channel.channel_id == "UC999"
        assert channel.title == "My Channel"
        assert channel.subscribers == "100 videos"
        assert channel.video_count == "100 videos"
        assert channel.thumbnail == "http://ch.jpg"

    def test_from_lockup(self) -> None:
        lockup = {
            "contentId": "UCabc",
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": "Lockup Channel"},
                    "metadata": {
                        "contentMetadataViewModel": {
                            "metadataRows": [
                                {
                                    "metadataParts": [
                                        {"text": {"content": "1M subscribers"}}
                                    ]
                                }
                            ]
                        }
                    },
                }
            },
        }
        channel = Channel.from_lockup(lockup)
        assert channel.channel_id == "UCabc"
        assert channel.title == "Lockup Channel"
        assert channel.subscribers == "1M subscribers"


class TestPlaylist:
    def test_url(self) -> None:
        assert (
            Playlist(playlist_id="PL123").url
            == "https://www.youtube.com/playlist?list=PL123"
        )

    def test_from_renderer(self) -> None:
        renderer = {
            "playlistId": "PL999",
            "title": {"simpleText": "Best Songs"},
            "longBylineText": {"runs": [{"text": "Owner"}]},
            "videoCount": "42",
            "thumbnail": {"thumbnails": [{"url": "http://pl.jpg"}]},
        }
        playlist = Playlist.from_renderer(renderer)
        assert playlist.playlist_id == "PL999"
        assert playlist.title == "Best Songs"
        assert playlist.channel == "Owner"
        assert playlist.video_count == "42"
        assert playlist.thumbnail == "http://pl.jpg"


class TestVideoDetails:
    def test_url(self) -> None:
        assert VideoDetails(video_id="xyz").url == "https://www.youtube.com/watch?v=xyz"

    def test_from_player_response(self) -> None:
        data = {
            "videoDetails": {
                "videoId": "vid",
                "title": "A Title",
                "shortDescription": "desc",
                "author": "Author",
                "channelId": "UC1",
                "lengthSeconds": "215",
                "viewCount": "9999",
                "keywords": ["a", "b"],
                "isLiveContent": True,
                "thumbnail": {"thumbnails": [{"url": "http://t.jpg"}]},
            }
        }
        details = VideoDetails.from_player_response(data)
        assert details.video_id == "vid"
        assert details.title == "A Title"
        assert details.description == "desc"
        assert details.channel == "Author"
        assert details.channel_id == "UC1"
        assert details.length_seconds == 215
        assert details.views == 9999
        assert details.keywords == ("a", "b")
        assert details.is_live is True
        assert details.thumbnail == "http://t.jpg"

    def test_from_player_response_invalid_numbers(self) -> None:
        data = {
            "videoDetails": {
                "videoId": "vid",
                "lengthSeconds": "not-a-number",
                "viewCount": None,
            }
        }
        details = VideoDetails.from_player_response(data)
        assert details.length_seconds is None
        assert details.views is None

    def test_from_player_response_empty(self) -> None:
        details = VideoDetails.from_player_response({})
        assert details.video_id == ""
        assert details.keywords == ()
        assert details.is_live is False
