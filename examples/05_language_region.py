"""Localise results by interface language (hl) and content region (gl).

Run with:  python examples/05_language_region.py
"""

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
