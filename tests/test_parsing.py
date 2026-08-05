"""Tests for the low-level parsing helpers."""

from __future__ import annotations

from ytscrape import Channel, Playlist, Video
from ytscrape.parsing import (
    find_comments_continuation,
    find_comments_sort_continuation,
    find_continuation,
    find_next_comments_continuation,
    find_reply_continuations,
    iter_renderers,
    parse_comments_page,
    parse_item,
)


class TestFindContinuation:
    def test_modern_continuation_command(self) -> None:
        obj = {"a": {"continuationCommand": {"token": "TOKEN123"}}}
        assert find_continuation(obj) == "TOKEN123"

    def test_legacy_continuation(self) -> None:
        obj = {"x": [{"nextContinuationData": {"continuation": "LEGACY"}}]}
        assert find_continuation(obj) == "LEGACY"

    def test_deeply_nested(self) -> None:
        obj = {
            "level1": {
                "level2": [{"level3": {"continuationCommand": {"token": "DEEP"}}}]
            }
        }
        assert find_continuation(obj) == "DEEP"

    def test_returns_none_when_absent(self) -> None:
        assert find_continuation({"foo": "bar", "list": [1, 2, 3]}) is None

    def test_returns_none_for_scalar(self) -> None:
        assert find_continuation("just a string") is None


class TestIterRenderers:
    def test_yields_known_renderers(self) -> None:
        response = {
            "contents": [
                {"videoRenderer": {"videoId": "v1"}},
                {"channelRenderer": {"channelId": "c1"}},
                {"playlistRenderer": {"playlistId": "p1"}},
            ]
        }
        pairs = list(iter_renderers(response))
        keys = [key for key, _ in pairs]
        assert keys == ["videoRenderer", "channelRenderer", "playlistRenderer"]

    def test_yields_lockup(self) -> None:
        response = {"items": [{"lockupViewModel": {"contentId": "x"}}]}
        pairs = list(iter_renderers(response))
        assert pairs == [("lockupViewModel", {"contentId": "x"})]

    def test_ignores_unknown_keys(self) -> None:
        response = {"somethingRenderer": {"foo": "bar"}}
        assert list(iter_renderers(response)) == []


class TestParseItem:
    def test_parses_video_renderer(self) -> None:
        item = parse_item("videoRenderer", {"videoId": "abc"})
        assert isinstance(item, Video)
        assert item.video_id == "abc"

    def test_parses_channel_renderer(self) -> None:
        item = parse_item("channelRenderer", {"channelId": "UC1"})
        assert isinstance(item, Channel)

    def test_parses_playlist_renderer(self) -> None:
        item = parse_item("playlistRenderer", {"playlistId": "PL1"})
        assert isinstance(item, Playlist)

    def test_unknown_renderer_returns_none(self) -> None:
        assert parse_item("mysteryRenderer", {}) is None

    def test_lockup_video(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_VIDEO", "contentId": "v"},
        )
        assert isinstance(item, Video)

    def test_lockup_channel(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_CHANNEL", "contentId": "c"},
        )
        assert isinstance(item, Channel)

    def test_lockup_playlist(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_PLAYLIST", "contentId": "p"},
        )
        assert isinstance(item, Playlist)

    def test_lockup_unknown_type_returns_none(self) -> None:
        item = parse_item(
            "lockupViewModel",
            {"contentType": "LOCKUP_CONTENT_TYPE_ALIEN", "contentId": "?"},
        )
        assert item is None


def _entity_payload(comment_id: str, text: str, author: str) -> dict:
    return {
        "commentEntityPayload": {
            "properties": {
                "commentId": comment_id,
                "content": {"content": text},
                "publishedTime": "2 days ago",
            },
            "author": {
                "displayName": author,
                "channelId": "UC" + comment_id,
                "avatarThumbnailUrl": "https://img/avatar.jpg",
            },
            "toolbar": {"likeCountLiked": "5", "replyCount": "2"},
        }
    }


class TestFindCommentsContinuation:
    def test_finds_comment_section_token(self) -> None:
        response = {
            "contents": {
                "results": [
                    {
                        "itemSectionRenderer": {
                            "sectionIdentifier": "comment-item-section",
                            "contents": [
                                {"continuationItemRenderer": {}},
                            ],
                            "continuationCommand": {"token": "COMMENTS"},
                        }
                    }
                ]
            }
        }
        assert find_comments_continuation(response) == "COMMENTS"

    def test_returns_none_when_absent(self) -> None:
        response = {"contents": {"results": []}}
        assert find_comments_continuation(response) is None


class TestFindNextCommentsContinuation:
    def test_returns_token_from_trailing_continuation_item(self) -> None:
        response = {
            "onResponseReceivedEndpoints": [
                {
                    "appendContinuationItemsAction": {
                        "continuationItems": [
                            {"commentViewModel": {}},
                            {
                                "continuationItemRenderer": {
                                    "continuationCommand": {"token": "NEXT"}
                                }
                            },
                        ]
                    }
                }
            ],
        }
        assert find_next_comments_continuation(response) == "NEXT"

    def test_ignores_sort_and_reply_tokens(self) -> None:
        # Only the token that lives inside the comment-items command is the real
        # "next page"; a top-level sort/reload token and per-comment reply
        # tokens must be ignored (following them repeats the same comments).
        response = {
            "continuationCommand": {"token": "SORT-RELOAD"},
            "onResponseReceivedEndpoints": [
                {
                    "reloadContinuationItemsCommand": {
                        "continuationItems": [
                            {
                                "commentViewModel": {
                                    "replies": {
                                        "continuationCommand": {"token": "REPLY"}
                                    }
                                }
                            },
                            {
                                "continuationItemRenderer": {
                                    "continuationCommand": {"token": "NEXT"}
                                }
                            },
                        ]
                    }
                }
            ],
        }
        assert find_next_comments_continuation(response) == "NEXT"

    def test_returns_none_on_last_page(self) -> None:
        response = {
            "onResponseReceivedEndpoints": [
                {
                    "appendContinuationItemsAction": {
                        "continuationItems": [{"commentViewModel": {}}]
                    }
                }
            ],
        }
        assert find_next_comments_continuation(response) is None


def _sort_menu(*, top_selected: bool = True) -> dict:
    """Build a ``sortFilterSubMenuRenderer`` with Top + Newest items."""
    return {
        "sortFilterSubMenuRenderer": {
            "subMenuItems": [
                {
                    "title": "Top comments",
                    "selected": top_selected,
                    "serviceEndpoint": {"continuationCommand": {"token": "TOP"}},
                },
                {
                    "title": "Newest first",
                    "selected": not top_selected,
                    "serviceEndpoint": {"continuationCommand": {"token": "NEWEST"}},
                },
            ]
        }
    }


class TestFindCommentsSortContinuation:
    def test_finds_token_by_title(self) -> None:
        response = {"a": {"b": _sort_menu()}}
        assert (
            find_comments_sort_continuation(response, title="Newest first") == "NEWEST"
        )

    def test_falls_back_to_index_when_title_missing(self) -> None:
        # A localised menu (non-English titles) still resolves by position.
        menu = _sort_menu()
        for item in menu["sortFilterSubMenuRenderer"]["subMenuItems"]:
            item["title"] = "\u041d\u0435\u0432\u0456\u0434\u043e\u043c\u043e"
        assert (
            find_comments_sort_continuation(menu, title="Newest first", index=1)
            == "NEWEST"
        )

    def test_returns_none_when_requested_order_already_selected(self) -> None:
        # "Top" is selected by default, so switching to it is a no-op.
        response = _sort_menu(top_selected=True)
        assert (
            find_comments_sort_continuation(response, title="Top comments", index=0)
            is None
        )

    def test_returns_none_without_menu(self) -> None:
        assert find_comments_sort_continuation({"contents": []}, title="x") is None


def _thread_with_replies(comment_id: str, reply_token: str) -> dict:
    """Build a ``commentThreadRenderer`` carrying a reply-continuation token."""
    return {
        "commentThreadRenderer": {
            "comment": {
                "commentViewModel": {"commentViewModel": {"commentId": comment_id}}
            },
            "replies": {
                "commentRepliesRenderer": {
                    "contents": [
                        {
                            "continuationItemRenderer": {
                                "continuationEndpoint": {
                                    "continuationCommand": {"token": reply_token}
                                }
                            }
                        }
                    ]
                }
            },
        }
    }


class TestFindReplyContinuations:
    def test_collects_parent_id_and_token_per_thread(self) -> None:
        response = {
            "contents": [
                _thread_with_replies("c1", "R1"),
                _thread_with_replies("c2", "R2"),
            ]
        }
        assert find_reply_continuations(response) == [("c1", "R1"), ("c2", "R2")]

    def test_returns_empty_when_no_replies(self) -> None:
        response = {"contents": [{"commentThreadRenderer": {"comment": {}}}]}
        assert find_reply_continuations(response) == []


class TestParseCommentsPage:
    def test_parses_entity_payload_comments(self) -> None:
        response = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {"payload": _entity_payload("c1", "Hello", "Alice")},
                        {"payload": _entity_payload("c2", "World", "Bob")},
                    ]
                }
            },
            "onResponseReceivedEndpoints": [
                {
                    "reloadContinuationItemsCommand": {
                        "continuationItems": [
                            {
                                "commentThreadRenderer": {
                                    "commentViewModel": {
                                        "commentViewModel": {"commentId": "c1"}
                                    }
                                }
                            },
                            {
                                "commentThreadRenderer": {
                                    "commentViewModel": {
                                        "commentViewModel": {"commentId": "c2"}
                                    }
                                }
                            },
                        ]
                    }
                }
            ],
        }
        comments = parse_comments_page(response)
        assert [c.comment_id for c in comments] == ["c1", "c2"]
        assert comments[0].author == "Alice"
        assert comments[0].text == "Hello"
        assert comments[0].like_count == 5
        assert comments[0].reply_count == 2
        assert comments[0].is_reply is False

    def test_parses_classic_comment_renderer(self) -> None:
        response = {
            "contents": [
                {
                    "commentThreadRenderer": {
                        "comment": {
                            "commentRenderer": {
                                "commentId": "x1",
                                "contentText": {"simpleText": "Nice!"},
                                "authorText": {"simpleText": "Carol"},
                            }
                        }
                    }
                }
            ]
        }
        comments = parse_comments_page(response)
        assert len(comments) == 1
        assert comments[0].comment_id == "x1"
        assert comments[0].text == "Nice!"
        assert comments[0].author == "Carol"

    def test_marks_replies(self) -> None:
        response = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {"payload": _entity_payload("r1", "A reply", "Dan")},
                    ]
                }
            },
            "commentRepliesRenderer": {
                "contents": [
                    {"commentViewModel": {"commentViewModel": {"commentId": "r1"}}},
                ]
            },
        }
        comments = parse_comments_page(response)
        assert len(comments) == 1
        assert comments[0].is_reply is True

    def test_deduplicates_by_id(self) -> None:
        response = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {"payload": _entity_payload("c1", "Hi", "Alice")},
                    ]
                }
            },
            "a": {"commentViewModel": {"commentViewModel": {"commentId": "c1"}}},
            "b": {"commentViewModel": {"commentViewModel": {"commentId": "c1"}}},
        }
        comments = parse_comments_page(response)
        assert len(comments) == 1

    def test_resolves_creator_heart(self) -> None:
        # The hearted flag lives in a sibling ``engagementToolbarStateEntityPayload``
        # mutation; comments reference it through a shared ``toolbarStateKey``.
        payload_hearted = _entity_payload("c1", "Hi", "Alice")
        payload_hearted["commentEntityPayload"]["properties"]["toolbarStateKey"] = "K1"
        payload_plain = _entity_payload("c2", "Bye", "Bob")
        payload_plain["commentEntityPayload"]["properties"]["toolbarStateKey"] = "K2"
        response = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {"payload": payload_hearted},
                        {"payload": payload_plain},
                        {
                            "payload": {
                                "engagementToolbarStateEntityPayload": {
                                    "key": "K1",
                                    "heartState": "TOOLBAR_HEART_STATE_HEARTED",
                                }
                            }
                        },
                        {
                            "payload": {
                                "engagementToolbarStateEntityPayload": {
                                    "key": "K2",
                                    "heartState": "TOOLBAR_HEART_STATE_UNHEARTED",
                                }
                            }
                        },
                    ]
                }
            },
            "a": {"commentViewModel": {"commentViewModel": {"commentId": "c1"}}},
            "b": {"commentViewModel": {"commentViewModel": {"commentId": "c2"}}},
        }
        comments = parse_comments_page(response)
        by_id = {c.comment_id: c for c in comments}
        assert by_id["c1"].heart is True
        assert by_id["c2"].heart is False

    def test_force_reply_marks_flat_replies(self) -> None:
        # A reply page lists its comments directly (no ``replies`` nesting), so
        # is_reply can only be forced by the caller.
        response = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {"payload": _entity_payload("r1", "A reply", "Dan")},
                    ]
                }
            },
            "onResponseReceivedEndpoints": [
                {
                    "appendContinuationItemsAction": {
                        "continuationItems": [
                            {
                                "commentViewModel": {
                                    "commentViewModel": {"commentId": "r1"}
                                }
                            }
                        ]
                    }
                }
            ],
        }
        comments = parse_comments_page(response, force_reply=True)
        assert len(comments) == 1
        assert comments[0].is_reply is True

    def test_empty_response_returns_empty_list(self) -> None:
        assert parse_comments_page({}) == []
