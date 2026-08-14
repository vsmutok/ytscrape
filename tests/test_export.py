"""JSON / CSV export for models and collections."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from ytscrape import Comment, Video, dump_csv, dump_json, dumps_csv, dumps_json, to_dict
from ytscrape.transcripts import Transcript, TranscriptSnippet


def test_video_to_dict_includes_url_and_type() -> None:
    video = Video(video_id="abc", title="Hello", channel="Ch")
    data = video.to_dict()
    assert data["video_id"] == "abc"
    assert data["title"] == "Hello"
    assert data["url"] == video.url
    assert data["type"] == "video"


def test_dumps_json_roundtrip() -> None:
    video = Video(video_id="abc", title="Hello")
    parsed = json.loads(video.to_json())
    assert parsed["video_id"] == "abc"
    assert parsed["url"].endswith("abc")


def test_dumps_csv_has_header_and_row() -> None:
    video = Video(video_id="abc", title="Hello")
    text = video.to_csv()
    rows = list(csv.DictReader(StringIO(text)))
    assert len(rows) == 1
    assert rows[0]["video_id"] == "abc"
    assert rows[0]["title"] == "Hello"
    assert rows[0]["url"] == video.url


def test_collection_json_and_csv() -> None:
    items = [
        Video(video_id="a", title="A"),
        Comment(comment_id="c1", text="hi", author="@x"),
    ]
    parsed = json.loads(dumps_json(items))
    assert parsed[0]["type"] == "video"
    assert parsed[1]["comment_id"] == "c1"

    csv_text = dumps_csv(items)
    rows = list(csv.DictReader(StringIO(csv_text)))
    assert rows[0]["video_id"] == "a"
    assert rows[1]["comment_id"] == "c1"


def test_transcript_csv_one_row_per_snippet() -> None:
    transcript = Transcript(
        snippets=(
            TranscriptSnippet(text="one", start=0.0, duration=1.0),
            TranscriptSnippet(text="two", start=1.0, duration=1.5),
        ),
        video_id="vid",
        language="English",
        language_code="en",
        is_generated=True,
    )
    data = transcript.to_dict()
    assert data["text"] == "one two"
    assert len(data["snippets"]) == 2

    rows = list(csv.DictReader(StringIO(transcript.to_csv())))
    assert len(rows) == 2
    assert rows[0]["text"] == "one"
    assert rows[1]["text"] == "two"
    assert rows[0]["video_id"] == "vid"


def test_dump_to_path(tmp_path: Path) -> None:
    video = Video(video_id="abc", title="T")
    json_path = tmp_path / "v.json"
    csv_path = tmp_path / "v.csv"
    video.dump_json(json_path)
    video.dump_csv(csv_path)
    assert json.loads(json_path.read_text())["video_id"] == "abc"
    assert "video_id" in csv_path.read_text()

    buf = StringIO()
    dump_json([video], buf, indent=None)
    assert '"abc"' in buf.getvalue()
    buf2 = StringIO()
    dump_csv([video], buf2)
    assert "abc" in buf2.getvalue()


def test_to_dict_passthrough_primitives() -> None:
    assert to_dict(None) is None
    assert to_dict(3) == 3
    assert to_dict({"a": Video(video_id="x")})["a"]["video_id"] == "x"
