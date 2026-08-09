# Localise YouTube results by language and region in ytscrape

> Configure ytscrape's interface language and content region with ISO codes to receive localised titles, descriptions, and metadata from YouTube.

YouTube serves localised content based on two parameters: the **interface language** (`hl`) and the **content region** (`gl`). Setting them tells YouTube which language to use for UI text and which country's content catalogue to surface. ytscrape lets you control both when creating a `YouTube` instance.

## Passing raw ISO codes

The simplest way is to pass plain ISO codes directly to `YouTube()`. They are validated and normalised for you:

```python
from ytscrape import YouTube

with YouTube(language="uk", region="UA") as yt:
    for video in yt.search("музика", max_results=5):
        print(video.title, video.url)
```

`language` accepts an ISO 639-1 two-letter code (e.g. `"en"`, `"uk"`, `"de"`).\
`region` accepts an ISO 3166-1 alpha-2 two-letter code (e.g. `"US"`, `"UA"`, `"DE"`).

## The `Language` and `Country` value objects

`Language` and `Country` are thin, self-validating value objects. They wrap the raw ISO code and normalise its casing on construction — lower-case for language, upper-case for country. You can use them interchangeably with plain strings anywhere ytscrape accepts a language or region:

```python
from ytscrape import YouTube, Language, Country

yt = YouTube(language=Language("de"), region=Country("DE"))
print(yt.locale.language.code)  # "de"
print(yt.locale.country.code)   # "DE"
```

## The `Locale` object

A `Locale` bundles a `Language` and a `Country` together. Build one when you want to construct the locale separately and reuse it across multiple `YouTube` instances:

```python
from ytscrape import YouTube, Locale, Language, Country

locale = Locale(language=Language("de"), country=Country("DE"))

with YouTube(locale=locale) as yt:
    print(f"Locale: {yt.locale.language.code}-{yt.locale.country.code}")
    for video in yt.search("musik", max_results=5):
        print(video.title)
```

`Locale` also accepts raw strings for both fields — it coerces them to `Language` and `Country` automatically:

```python
locale = Locale(language="fr", country="FR")
```

The `Locale.of()` classmethod is a convenience alternative that accepts `None` for either argument and falls back to the defaults (`"en"` / `"US"`):

```python
locale = Locale.of(language="fr", country="FR")
```

## Validation

Invalid codes are rejected early with a clear error message rather than silently producing a broken request:

```python
from ytscrape import YouTube

YouTube(region="XX")
# ValueError: Unknown country code 'XX'. Expected a valid ISO 3166-1
# alpha-2 (two-letter) code such as 'US', 'UA' or 'DE'.

YouTube(language="zz")
# ValueError: Unknown language code 'zz'. Expected a valid ISO 639-1
# (two-letter) code such as 'en', 'uk' or 'de'.
```

## How locale is sent

The chosen locale affects every request in two ways:

1. **InnerTube context** — `hl` (language code) and `gl` (country code) are embedded in the JSON payload of every API call.
2. **`Accept-Language` header** — set to a value like `uk-UA,uk;q=0.9`, which also influences the HTML YouTube returns for context extraction.

## Full example

```python
from ytscrape import Country, Language, Locale, YouTube


def main() -> None:
    # Pass raw ISO codes — they are validated and normalised for you.
    with YouTube(language="uk", region="UA") as yt:
        print("Ukrainian interface / region:")
        for video in yt.search("музика", max_results=5):
            print(f"  {video.title}")

    # The Language / Country / Locale value objects are equivalent.
    locale = Locale(language=Language("de"), country=Country("DE"))
    with YouTube(locale=locale) as yt:
        print(f"\nLocale: {yt.locale.language.code}-{yt.locale.country.code}")
        for video in yt.search("musik", max_results=5):
            print(f"  {video.title}")


if __name__ == "__main__":
    main()
```

## Supported code formats

| Parameter  | Format                                       | Example                        |
| ---------- | -------------------------------------------- | ------------------------------ |
| `language` | ISO 639-1 (two-letter, lower-cased)          | `"en"`, `"uk"`, `"de"`, `"fr"` |
| `region`   | ISO 3166-1 alpha-2 (two-letter, upper-cased) | `"US"`, `"UA"`, `"DE"`, `"FR"` |

!!! note

    ytscrape validates codes against the official ISO lists using the `pycountry` library — there is no hard-coded whitelist. Any code that `pycountry` recognises will work, so newly added or uncommon codes are supported automatically.

