"""Tests for the data models and their factory methods."""

from __future__ import annotations

from ytscrape import Channel, ChannelDetails, Comment, Playlist, Video, VideoDetails


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


class TestChannelDetails:
    def test_url(self) -> None:
        assert (
            ChannelDetails(channel_id="UCabcdefghijklmnopqrstuv").url
            == "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv"
        )

    def test_from_browse_response(self) -> None:
        data = {
            "metadata": {
                "channelMetadataRenderer": {
                    "title": "Rick Astley",
                    "description": "Bio here",
                    "externalId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                    "keywords": 'Official "rick astley" meme',
                    "avatar": {"thumbnails": [{"url": "http://avatar.jpg"}]},
                    "vanityChannelUrl": "http://www.youtube.com/@RickAstleyYT",
                    "ownerUrls": ["http://www.youtube.com/@RickAstleyYT"],
                    "rssUrl": "https://www.youtube.com/feeds/videos.xml?channel_id=UCuAXFkgsw1L7xaCfnd5JJOw",
                    "isFamilySafe": True,
                    "availableCountryCodes": ["US", "UA"],
                }
            },
            "microformat": {
                "microformatDataRenderer": {
                    "title": "Rick Astley",
                    "tags": ["Official", "Rick Astley"],
                    "familySafe": True,
                }
            },
            "header": {
                "pageHeaderRenderer": {
                    "content": {
                        "pageHeaderViewModel": {
                            "metadata": {
                                "contentMetadataViewModel": {
                                    "metadataRows": [
                                        {
                                            "metadataParts": [
                                                {"text": {"content": "@RickAstleyYT"}}
                                            ]
                                        },
                                        {
                                            "metadataParts": [
                                                {
                                                    "text": {
                                                        "content": "4.53M subscribers"
                                                    }
                                                },
                                                {"text": {"content": "434 videos"}},
                                            ]
                                        },
                                    ]
                                }
                            },
                            "banner": {
                                "imageBannerViewModel": {
                                    "image": {
                                        "sources": [
                                            {"url": "http://banner-small.jpg"},
                                            {"url": "http://banner.jpg"},
                                        ]
                                    }
                                }
                            },
                            "attribution": {
                                "attributionViewModel": {
                                    "text": {"content": " rickastley.lnk.to/x "}
                                }
                            },
                        }
                    }
                }
            },
        }
        details = ChannelDetails.from_browse_response(data)
        assert details.channel_id == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert details.title == "Rick Astley"
        assert details.description == "Bio here"
        assert details.handle == "@RickAstleyYT"
        assert details.subscribers == "4.53M subscribers"
        assert details.video_count == "434 videos"
        assert details.keywords == ("Official", "rick astley", "meme")
        assert details.thumbnail == "http://avatar.jpg"
        assert details.photo == "http://avatar.jpg"
        assert details.banner == "http://banner.jpg"
        assert details.vanity_url == "https://www.youtube.com/@RickAstleyYT"
        assert details.rss_url.endswith("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert details.is_family_safe is True
        assert details.tags == ("Official", "Rick Astley")
        assert details.available_countries == ("US", "UA")
        assert details.links == {"x": "https://rickastley.lnk.to/x"}
        assert details.country is None
        assert details.joined_date is None
        assert details.url == (
            "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw"
        )

    def test_from_browse_response_with_about(self) -> None:
        data = {
            "metadata": {
                "channelMetadataRenderer": {
                    "title": "CodeBrux",
                    "externalId": "UCxuAWlvSGhAM6aUY7-T5rJQ",
                    "avatar": {"thumbnails": [{"url": "http://photo.jpg"}]},
                }
            },
            "header": {
                "pageHeaderRenderer": {
                    "content": {
                        "pageHeaderViewModel": {
                            "banner": {
                                "imageBannerViewModel": {
                                    "image": {"sources": [{"url": "http://banner.jpg"}]}
                                }
                            }
                        }
                    }
                }
            },
        }
        about = {
            "aboutChannelViewModel": {
                "description": "Channel bio",
                "country": "Netherlands",
                "joinedDateText": {"content": "Joined Sep 11, 2015"},
                "viewCountText": "291,498,626 views",
                "subscriberCountText": "1.2M subscribers",
                "videoCountText": "400 videos",
                "links": [
                    {
                        "channelExternalLinkViewModel": {
                            "title": {"content": "Twitter"},
                            "link": {
                                "content": "twitter.com/CodeBrux",
                                "commandRuns": [
                                    {
                                        "onTap": {
                                            "innertubeCommand": {
                                                "urlEndpoint": {
                                                    "url": (
                                                        "https://www.youtube.com/redirect?"
                                                        "q=https%3A%2F%2Ftwitter.com%2FCodeBrux"
                                                    )
                                                }
                                            }
                                        }
                                    }
                                ],
                            },
                        }
                    },
                    {
                        "channelExternalLinkViewModel": {
                            "title": {"content": "Instagram"},
                            "link": {
                                "content": "instagram.com/codebrux",
                                "commandRuns": [
                                    {
                                        "onTap": {
                                            "innertubeCommand": {
                                                "urlEndpoint": {
                                                    "url": "https://instagram.com/codebrux"
                                                }
                                            }
                                        }
                                    }
                                ],
                            },
                        }
                    },
                    {
                        "channelExternalLinkViewModel": {
                            "title": {"content": "Discord"},
                            "link": {"content": "discord.gg/brux"},
                        }
                    },
                ],
            }
        }
        details = ChannelDetails.from_browse_response(data, about=about)
        assert details.photo == "http://photo.jpg"
        assert details.banner == "http://banner.jpg"
        assert details.country == "Netherlands"
        assert details.joined_date == "Joined Sep 11, 2015"
        assert details.view_count == "291,498,626 views"
        assert details.subscribers == "1.2M subscribers"
        assert details.video_count == "400 videos"
        assert details.description == "Channel bio"
        assert details.links == {
            "x": "https://twitter.com/CodeBrux",
            "instagram": "https://instagram.com/codebrux",
            "discord": "https://discord.gg/brux",
        }

    def test_from_browse_response_empty(self) -> None:
        details = ChannelDetails.from_browse_response({})
        assert details.channel_id == ""
        assert details.keywords == ()
        assert details.tags == ()
        assert details.links == {}
        assert details.is_family_safe is None


class TestComment:
    def test_from_entity_payload(self) -> None:
        payload = {
            "properties": {
                "commentId": "c1",
                "content": {"content": "Great video!"},
                "publishedTime": "2 days ago",
            },
            "author": {
                "displayName": "Alice",
                "channelId": "UCalice",
                "avatarThumbnailUrl": "https://avatar.jpg",
            },
            "toolbar": {"likeCountLiked": "12", "replyCount": "3"},
        }
        comment = Comment.from_entity_payload(payload)
        assert comment.comment_id == "c1"
        assert comment.text == "Great video!"
        assert comment.author == "Alice"
        assert comment.author_channel_id == "UCalice"
        assert comment.author_thumbnail == "https://avatar.jpg"
        assert comment.published == "2 days ago"
        assert comment.like_count == 12
        assert comment.like_count_text == "12"
        assert comment.reply_count == 3
        assert comment.reply_count_text == "3"
        assert comment.heart is False
        assert comment.is_reply is False

    def test_from_entity_payload_heart(self) -> None:
        payload = {"properties": {"commentId": "h1"}, "author": {}, "toolbar": {}}
        comment = Comment.from_entity_payload(payload, heart=True)
        assert comment.heart is True

    def test_from_entity_payload_reply_flag(self) -> None:
        payload = {"properties": {"commentId": "r1"}, "author": {}, "toolbar": {}}
        comment = Comment.from_entity_payload(payload, is_reply=True)
        assert comment.comment_id == "r1"
        assert comment.is_reply is True

    def test_from_entity_payload_abbreviated_like_count(self) -> None:
        payload = {
            "properties": {"commentId": "c2"},
            "author": {},
            "toolbar": {"likeCountLiked": "1.2K"},
        }
        comment = Comment.from_entity_payload(payload)
        # Non-numeric abbreviations cannot be represented exactly as an int,
        # but the raw display string is preserved.
        assert comment.like_count is None
        assert comment.like_count_text == "1.2K"

    def test_from_renderer(self) -> None:
        renderer = {
            "commentId": "x1",
            "contentText": {"runs": [{"text": "Hello "}, {"text": "there"}]},
            "authorText": {"simpleText": "Bob"},
            "authorEndpoint": {"browseEndpoint": {"browseId": "UCbob"}},
            "authorThumbnail": {"thumbnails": [{"url": "http://a.jpg"}]},
            "publishedTimeText": {"simpleText": "1 week ago"},
            "replyCount": 4,
        }
        comment = Comment.from_renderer(renderer, is_reply=True)
        assert comment.comment_id == "x1"
        assert comment.text == "Hello there"
        assert comment.author == "Bob"
        assert comment.author_channel_id == "UCbob"
        assert comment.author_thumbnail == "http://a.jpg"
        assert comment.published == "1 week ago"
        assert comment.reply_count == 4
        assert comment.reply_count_text == "4"
        assert comment.heart is False
        assert comment.is_reply is True

    def test_from_renderer_heart(self) -> None:
        renderer = {"commentId": "x2", "isHearted": True}
        assert Comment.from_renderer(renderer).heart is True
        assert Comment.from_renderer({"commentId": "x3"}, heart=True).heart is True
