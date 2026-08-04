"""Tests for the :class:`SearchFilter` enum."""

from __future__ import annotations

import pytest

from ytscrape import SearchFilter


class TestSearchFilterParams:
    def test_all_maps_to_none(self) -> None:
        assert SearchFilter.ALL.params is None

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (SearchFilter.VIDEOS, "EgIQAQ=="),
            (SearchFilter.CHANNELS, "EgIQAg=="),
            (SearchFilter.PLAYLISTS, "EgIQAw=="),
            (SearchFilter.SHORTS, "EgIQCQ=="),
            (SearchFilter.MOVIES, "EgIQBA=="),
        ],
    )
    def test_params_values(self, member: SearchFilter, expected: str) -> None:
        assert member.params == expected

    def test_every_member_has_params_entry(self) -> None:
        # ``params`` must not raise for any member.
        for member in SearchFilter:
            _ = member.params


class TestSearchFilterFromValue:
    def test_passes_through_enum_member(self) -> None:
        assert SearchFilter.from_value(SearchFilter.VIDEOS) is SearchFilter.VIDEOS

    def test_coerces_lower_case_string(self) -> None:
        assert SearchFilter.from_value("videos") is SearchFilter.VIDEOS

    def test_coerces_mixed_case_string(self) -> None:
        assert SearchFilter.from_value("Channels") is SearchFilter.CHANNELS

    def test_unknown_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown search filter"):
            SearchFilter.from_value("bananas")

    def test_is_str_enum(self) -> None:
        # SearchFilter subclasses str, so members compare equal to their value.
        assert SearchFilter.VIDEOS == "videos"
