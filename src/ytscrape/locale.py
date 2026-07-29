"""Language and country (region) support for InnerTube requests.

YouTube localises its responses through two request-context fields:

* ``hl`` -- the *interface language* (e.g. ``en``, ``uk``, ``de``);
* ``gl`` -- the *content region / country* (e.g. ``US``, ``UA``, ``DE``).

Instead of hard-coding a fixed list of languages and countries, this module
models each one as a small, self-validating value object -- :class:`Language`
and :class:`Country` -- that simply wraps a raw ISO code supplied by the
caller. The code is validated (and normalised) against the official ISO lists
via `pycountry`, so any valid language / country works while typos raise a
clear error instead of silently producing a broken request. A :class:`Locale`
value object bundles the two together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pycountry

__all__ = ["Language", "Country", "Locale"]

_DEFAULT_LANGUAGE = "en"
_DEFAULT_COUNTRY = "US"


def _validate_language(code: str) -> str:
    """Return the normalised ISO 639-1 language ``code`` or raise ``ValueError``.

    The code is normalised to lower case and validated against the ISO 639-1
    (two-letter) language list via ``pycountry``.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"Invalid language: {code!r}.")
    normalised = code.strip().lower()
    if len(normalised) != 2 or pycountry.languages.get(
        alpha_2=normalised
    ) is None:
        raise ValueError(
            f"Unknown language code {code!r}. Expected a valid ISO 639-1 "
            "(two-letter) code such as 'en', 'uk' or 'de'."
        )
    return normalised


def _validate_country(code: str) -> str:
    """Return the normalised ISO 3166-1 alpha-2 country ``code`` or raise ``ValueError``.

    The code is normalised to upper case and validated against the ISO 3166-1
    alpha-2 (two-letter) country list via ``pycountry``.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"Invalid country: {code!r}.")
    normalised = code.strip().upper()
    if len(normalised) != 2 or pycountry.countries.get(
        alpha_2=normalised
    ) is None:
        raise ValueError(
            f"Unknown country code {code!r}. Expected a valid ISO 3166-1 "
            "alpha-2 (two-letter) code such as 'US', 'UA' or 'DE'."
        )
    return normalised


@dataclass(frozen=True, slots=True)
class Language:
    """Interface language (``hl``) sent in the InnerTube request context.

    A thin value object around a raw
    `ISO 639-1 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_
    (two-letter) code. The code is validated and normalised (lower-cased) on
    creation via ``pycountry``; an unknown code raises :class:`ValueError`.

    Example:
        >>> Language("EN").code
        'en'
    """

    code: str = _DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        # Normalise / validate, keeping the dataclass frozen.
        object.__setattr__(self, "code", _validate_language(self.code))

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code

    @classmethod
    def of(cls, value: "Language | str") -> "Language":
        """Coerce ``value`` into a :class:`Language`.

        Accepts an existing :class:`Language` (returned as-is) or a raw ISO
        639-1 code, which is validated via ``pycountry``.
        """
        if isinstance(value, cls):
            return value
        return cls(value)


@dataclass(frozen=True, slots=True)
class Country:
    """Content region / country (``gl``) sent in the request context.

    A thin value object around a raw
    `ISO 3166-1 alpha-2 <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`_
    (two-letter) code. The code is validated and normalised (upper-cased) on
    creation via ``pycountry``; an unknown code raises :class:`ValueError`.

    Example:
        >>> Country("ua").code
        'UA'
    """

    code: str = _DEFAULT_COUNTRY

    def __post_init__(self) -> None:
        # Normalise / validate, keeping the dataclass frozen.
        object.__setattr__(self, "code", _validate_country(self.code))

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code

    @classmethod
    def of(cls, value: "Country | str") -> "Country":
        """Coerce ``value`` into a :class:`Country`.

        Accepts an existing :class:`Country` (returned as-is) or a raw ISO
        3166-1 alpha-2 code, which is validated via ``pycountry``.
        """
        if isinstance(value, cls):
            return value
        return cls(value)


@dataclass(frozen=True, slots=True)
class Locale:
    """A language + country pair used to localise InnerTube responses.

    Args:
        language: Interface language (``hl``). A :class:`Language` or a raw
            ISO 639-1 code.
        country: Content region (``gl``). A :class:`Country` or a raw ISO
            3166-1 alpha-2 code.
    """

    language: Language = field(default_factory=Language)
    country: Country = field(default_factory=Country)

    def __post_init__(self) -> None:
        # Accept both value objects and raw strings, keeping the dataclass
        # frozen.
        object.__setattr__(self, "language", Language.of(self.language))
        object.__setattr__(self, "country", Country.of(self.country))

    @classmethod
    def of(
        cls,
        language: "Language | str | None" = None,
        country: "Country | str | None" = None,
    ) -> "Locale":
        """Build a :class:`Locale`, falling back to defaults for missing parts."""
        kwargs: dict[str, Language | Country] = {}
        if language is not None:
            kwargs["language"] = Language.of(language)
        if country is not None:
            kwargs["country"] = Country.of(country)
        return cls(**kwargs)

    @property
    def accept_language(self) -> str:
        """Value for the ``Accept-Language`` HTTP header.

        Combines the language and region into a standard tag such as
        ``uk-UA`` and adds a plain-language fallback (``uk-UA,uk;q=0.9``).
        """
        lang = self.language.code
        return f"{lang}-{self.country.code},{lang};q=0.9"
