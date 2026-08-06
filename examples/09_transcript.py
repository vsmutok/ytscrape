"""Fetch a video transcript (captions).

Run with:  python examples/09_transcript.py
"""

from ytscrape import YouTube


def main() -> None:
    with YouTube() as yt:
        video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # List every available caption track first.
        print("Available tracks:")
        print(yt.transcripts(video))
        print()

        # Prefer Ukrainian, fall back to English (manual captions beat ASR).
        transcript = yt.transcript(video, languages=["uk", "en"])
        print(
            f"Fetched: {transcript.language} ({transcript.language_code}), "
            f"generated={transcript.is_generated}, lines={len(transcript)}"
        )
        print()
        for snippet in transcript[:8]:
            print(f"[{snippet.start:6.1f}s] {snippet.text}")
        print("...")
        print(transcript.text[:240], "…")


if __name__ == "__main__":
    main()
