"""Tests for the language / country / locale value objects."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ytscrape import Country, Language, Locale


class TestLanguage:
    def test_default_is_english(self) -> None:
        assert Language().code == "en"

    def test_normalises_to_lower_case(self) -> None:
        assert Language("EN").code == "en"
        assert Language("  Uk  ").code == "uk"

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown language code"):
            Language("zz")

    @pytest.mark.parametrize("code", ["", "   ", "eng", "e"])
    def test_invalid_length_or_empty_raises(self, code: str) -> None:
        with pytest.raises(ValueError):
            Language(code)

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError):
            Language(123)  # type: ignore[arg-type]

    def test_of_passes_through_existing_instance(self) -> None:
        lang = Language("de")
        assert Language.of(lang) is lang

    def test_of_coerces_string(self) -> None:
        assert Language.of("fr") == Language("fr")

    def test_str_returns_code(self) -> None:
        assert str(Language("de")) == "de"

    def test_is_frozen(self) -> None:
        lang = Language("en")
        with pytest.raises(FrozenInstanceError):
            lang.code = "de"  # type: ignore[misc]


class TestCountry:
    def test_default_is_us(self) -> None:
        assert Country().code == "US"

    def test_normalises_to_upper_case(self) -> None:
        assert Country("ua").code == "UA"
        assert Country(" de ").code == "DE"

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown country code"):
            Country("XX")

    @pytest.mark.parametrize("code", ["", "   ", "USA", "U"])
    def test_invalid_length_or_empty_raises(self, code: str) -> None:
        with pytest.raises(ValueError):
            Country(code)

    def test_of_passes_through_existing_instance(self) -> None:
        country = Country("DE")
        assert Country.of(country) is country

    def test_of_coerces_string(self) -> None:
        assert Country.of("fr") == Country("FR")

    def test_str_returns_code(self) -> None:
        assert str(Country("UA")) == "UA"


class TestLocale:
    def test_defaults(self) -> None:
        locale = Locale()
        assert locale.language.code == "en"
        assert locale.country.code == "US"

    def test_accepts_raw_strings(self) -> None:
        locale = Locale(language="uk", country="UA")
        assert locale.language.code == "uk"
        assert locale.country.code == "UA"

    def test_accepts_value_objects(self) -> None:
        locale = Locale(language=Language("de"), country=Country("DE"))
        assert locale.language == Language("de")
        assert locale.country == Country("DE")

    def test_of_falls_back_to_defaults(self) -> None:
        locale = Locale.of(language="fr")
        assert locale.language.code == "fr"
        assert locale.country.code == "US"

    def test_of_with_no_args_uses_defaults(self) -> None:
        locale = Locale.of()
        assert locale.language.code == "en"
        assert locale.country.code == "US"

    def test_accept_language_header(self) -> None:
        locale = Locale(language="uk", country="UA")
        assert locale.accept_language == "uk-UA,uk;q=0.9"

    def test_invalid_code_propagates(self) -> None:
        with pytest.raises(ValueError):
            Locale(language="zz", country="US")
