"""Handle the exceptions ytscrape can raise.

All ytscrape errors derive from `YtScraperError`, so catching that one is
enough for a broad guard; catch the specific subclasses when you need to react
differently.

Run with:  python examples/06_error_handling.py
"""

from ytscrape import ParseError, RequestError, YouTube, YtScraperError


def main() -> None:
    with YouTube() as yt:
        # An invalid id/URL cannot be parsed into a video id.
        try:
            yt.video("not-a-real-video-id")
        except ParseError as exc:
            print(f"Could not parse video id: {exc}")

        # Network / HTTP failures surface as RequestError.
        try:
            details = yt.video("dQw4w9WgXcQ")
            print(f"Got: {details.title}")
        except RequestError as exc:
            print(f"Request to YouTube failed: {exc}")
        except YtScraperError as exc:
            # Catch-all for any other ytscrape error.
            print(f"Something went wrong: {exc}")


if __name__ == "__main__":
    main()
