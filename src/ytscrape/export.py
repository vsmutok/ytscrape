"""Serialize ytscrape models (and collections of them) to JSON / CSV.

Models expose the same helpers as methods (``obj.to_json()``, ``obj.to_csv()``).
Collections and mixed search results go through the module-level functions::

    from ytscrape import Video, dumps_json, dumps_csv

    print(video.to_json())
    print(dumps_csv(results))
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, TextIO

__all__ = [
    "Exportable",
    "to_dict",
    "dumps_json",
    "dumps_csv",
    "dump_json",
    "dump_csv",
]

_COMPUTED = ("url", "text", "is_translatable")


def to_dict(obj: Any) -> Any:
    """Convert a model, mapping, or collection into JSON-friendly data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Mapping):
        return {str(k): to_dict(v) for k, v in obj.items()}
    if is_dataclass(obj) and not isinstance(obj, type):
        data: dict[str, Any] = {}
        for item in fields(obj):
            if item.name.startswith("_"):
                continue
            data[item.name] = to_dict(getattr(obj, item.name))
        for name in _COMPUTED:
            if name in data:
                continue
            try:
                value = getattr(obj, name)
            except Exception:
                continue
            if callable(value):
                continue
            data[name] = to_dict(value)
        type_name = type(obj).__name__
        if type_name in {"Video", "Channel", "Playlist"}:
            data.setdefault("type", type_name.lower())
        return data
    if isinstance(obj, (list, tuple)):
        return [to_dict(item) for item in obj]
    if isinstance(obj, Iterable) and not isinstance(obj, (bytes, bytearray)):
        try:
            return [to_dict(item) for item in obj]
        except TypeError:
            return str(obj)
    return str(obj)


def dumps_json(obj: Any, *, indent: int | None = 2) -> str:
    """Return a JSON string for ``obj`` (model or collection)."""
    payload = to_dict(obj)
    return json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"


def dump_json(
    obj: Any,
    path: str | Path | TextIO,
    *,
    indent: int | None = 2,
) -> None:
    """Write JSON to a path or file object."""
    text = dumps_json(obj, indent=indent)
    _write_text(path, text)


def dumps_csv(obj: Any) -> str:
    """Return CSV text for a model or a collection of models."""
    rows = _csv_rows(obj)
    if not rows:
        return ""
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in keys})
    return buf.getvalue()


def dump_csv(obj: Any, path: str | Path | TextIO) -> None:
    """Write CSV to a path or file object."""
    _write_text(path, dumps_csv(obj))


def _write_text(path: str | Path | TextIO, text: str) -> None:
    if hasattr(path, "write"):
        path.write(text)  # type: ignore[union-attr]
        return
    Path(path).write_text(text, encoding="utf-8")


def _flatten(prefix: str, value: Any, dest: dict[str, str]) -> None:
    if value is None:
        dest[prefix] = ""
        return
    if isinstance(value, bool):
        dest[prefix] = "true" if value else "false"
        return
    if isinstance(value, (str, int, float)):
        dest[prefix] = str(value)
        return
    if isinstance(value, Mapping):
        if not value:
            dest[prefix] = ""
            return
        dest[prefix] = json.dumps(value, ensure_ascii=False)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        dest[prefix] = json.dumps(value, ensure_ascii=False)
        return
    dest[prefix] = str(value)


def _csv_rows(obj: Any) -> list[dict[str, str]]:
    data = to_dict(obj)
    if data is None:
        return []
    if isinstance(data, list):
        rows: list[dict[str, str]] = []
        for item in data:
            if isinstance(item, Mapping):
                row: dict[str, str] = {}
                for key, value in item.items():
                    _flatten(str(key), value, row)
                rows.append(row)
            else:
                rows.append({"value": "" if item is None else str(item)})
        return rows
    if isinstance(data, Mapping):
        # Transcript: prefer one row per snippet when present.
        snippets = data.get("snippets")
        if isinstance(snippets, list) and snippets:
            meta = {
                k: v
                for k, v in data.items()
                if k != "snippets" and not isinstance(v, (list, dict))
            }
            rows = []
            for snippet in snippets:
                row: dict[str, str] = {}
                for key, value in meta.items():
                    _flatten(str(key), value, row)
                if isinstance(snippet, Mapping):
                    for key, value in snippet.items():
                        _flatten(str(key), value, row)
                rows.append(row)
            return rows
        row = {}
        for key, value in data.items():
            _flatten(str(key), value, row)
        return [row]
    return [{"value": str(data)}]


class Exportable:
    """Mixin: ``to_dict`` / ``to_json`` / ``to_csv`` (+ dump helpers)."""

    def to_dict(self) -> Any:
        return to_dict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        return dumps_json(self, indent=indent)

    def to_csv(self) -> str:
        return dumps_csv(self)

    def dump_json(self, path: str | Path | TextIO, *, indent: int | None = 2) -> None:
        dump_json(self, path, indent=indent)

    def dump_csv(self, path: str | Path | TextIO) -> None:
        dump_csv(self, path)
