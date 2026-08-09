# Language, Country, and Locale classes — ytscrape reference

> Reference for the Language, Country, and Locale value objects that configure and localise ytscrape's InnerTube requests by language and region.

The `locale` module provides three immutable value objects — `Language`, `Country`, and `Locale` — that control how YouTube localises its responses. YouTube uses two InnerTube context fields for this: `hl` (interface language) and `gl` (content region). All three classes validate input against the official ISO lists via `pycountry`, so typos raise a clear `ValueError` instead of silently producing broken requests.

## `Language`

`Language` wraps a single ISO 639-1 two-letter language code and sets the `hl` field in every InnerTube request context.

### Constructor

**`code`** (`str`)

:   A valid [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) two-letter language code (e.g. `"en"`, `"uk"`, `"de"`). The code is normalised to lowercase on creation. An unrecognised code raises `ValueError`.


### Attributes

**`code`** (`str`)

:   The validated, lowercase ISO 639-1 language code (e.g. `"en"`, `"uk"`).


### Class methods

**`of(value)`** (`classmethod`)

:   Coerces a raw ISO 639-1 string or an existing `Language` instance into a `Language`. Returns the instance unchanged if it is already a `Language`.
    
      **`value`** (`Language | str`) **required**
    
    :   The language to coerce.


### Examples

```python
from ytscrape import Language

# Standard construction — normalised to lowercase
lang = Language("EN")
print(lang.code)   # "en"

# Ukrainian
lang_uk = Language("uk")
print(lang_uk.code)  # "uk"

# Invalid code raises ValueError
Language("xx")
# ValueError: Unknown language code 'xx'. Expected a valid ISO 639-1
#             (two-letter) code such as 'en', 'uk' or 'de'.
```

***

## `Country`

`Country` wraps a single ISO 3166-1 alpha-2 two-letter country code and sets the `gl` field in every InnerTube request context.

### Constructor

**`code`** (`str`)

:   A valid [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) two-letter country code (e.g. `"US"`, `"UA"`, `"DE"`). The code is normalised to uppercase on creation. An unrecognised code raises `ValueError`.


### Attributes

**`code`** (`str`)

:   The validated, uppercase ISO 3166-1 alpha-2 country code (e.g. `"US"`, `"UA"`).


### Class methods

**`of(value)`** (`classmethod`)

:   Coerces a raw ISO 3166-1 alpha-2 string or an existing `Country` instance into a `Country`. Returns the instance unchanged if it is already a `Country`.
    
      **`value`** (`Country | str`) **required**
    
    :   The country to coerce.


### Examples

```python
from ytscrape import Country

# Normalised to uppercase
country = Country("ua")
print(country.code)  # "UA"

# US (default)
country_us = Country("US")
print(country_us.code)  # "US"

# Invalid code raises ValueError
Country("ZZ")
# ValueError: Unknown country code 'ZZ'. Expected a valid ISO 3166-1
#             alpha-2 (two-letter) code such as 'US', 'UA' or 'DE'.
```

***

## `Locale`

`Locale` bundles a `Language` and a `Country` into a single immutable value object. It is the object you pass to `YouTube` to localise all requests made through that client instance.

### Constructor

**`language`** (`Language | str`)

:   The interface language. Accepts a `Language` instance or a raw ISO 639-1 code string. Defaults to `Language("en")`.


**`country`** (`Country | str`)

:   The content region. Accepts a `Country` instance or a raw ISO 3166-1 alpha-2 code string. Defaults to `Country("US")`.


### Attributes

**`language`** (`Language`)

:   The validated `Language` instance used for the `hl` context field.


**`country`** (`Country`)

:   The validated `Country` instance used for the `gl` context field.


**`accept_language`** (`str`)

:   The value for the `Accept-Language` HTTP header derived from this locale. Combines the language and country codes into a standard language tag with a plain-language fallback and a quality factor — for example, `Language("uk")` + `Country("UA")` produces `"uk-UA,uk;q=0.9"`.


### Class methods

**`of(language, country)`** (`classmethod`)

:   Builds a `Locale` from optional language and country arguments, falling back to defaults (`"en"` / `"US"`) for any argument that is `None`. Each argument is coerced via `Language.of` or `Country.of`.
    
      **`language`** (`Language | str | None`)
    
    :   The interface language, or `None` to use the default `"en"`.
    
    
      **`country`** (`Country | str | None`)
    
    :   The content region, or `None` to use the default `"US"`.


### Usage with `YouTube`

Pass a `Locale` to the `YouTube` constructor to localise all requests made through that client:

```python
from ytscrape import YouTube, Locale

# French results from France
yt_fr = YouTube(locale=Locale("fr", "FR"))
results = yt_fr.search("tutoriel python")

# Ukrainian results from Ukraine — using Locale.of
yt_ua = YouTube(locale=Locale.of("uk", "UA"))
results = yt_ua.search("python навчання")

# Direct value objects
from ytscrape import Language, Country

yt_de = YouTube(locale=Locale(Language("de"), Country("DE")))

# Accept-Language header value
locale = Locale("uk", "UA")
print(locale.accept_language)  # "uk-UA,uk;q=0.9"
```

### Validation behaviour

Both `Language` and `Country` are validated immediately on construction using `pycountry`. Passing an unrecognised code raises `ValueError` with a message indicating what was wrong and what form is expected:

```python
from ytscrape import Locale

# Bad language code
Locale("zz", "US")
# ValueError: Unknown language code 'zz'. Expected a valid ISO 639-1
#             (two-letter) code such as 'en', 'uk' or 'de'.

# Bad country code
Locale("en", "XX")
# ValueError: Unknown country code 'XX'. Expected a valid ISO 3166-1
#             alpha-2 (two-letter) code such as 'US', 'UA' or 'DE'.
```
