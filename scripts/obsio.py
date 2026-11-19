"""Paths and file helpers shared by the build and the live switcher.

Nothing in here knows segment titles, headlines, or chyron copy. Those live
in obs-data.json and the text files the build writes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PLAYLIST_NAME = "playlist.json"
DATA_NAME = "obs-data.json"

# Folders the build owns. show-notes/ is not in this list: the spoken rundown
# and the research notes are kept by hand, and the build only adds its own
# generated files in that folder by name.
GENERATED_DIRS = (
    "chyrons",
    "headlines",
    "segment-titles",
    "ticker",
    "scenes",
    "current",
)

CURRENT_FILES = (
    "segment-title.txt",
    "chyron.txt",
    "chyron-primary.txt",
    "chyron-secondary.txt",
    "headline.txt",
    "headlines.txt",
    "segment-meta.txt",
    "scene-hint.txt",
    "state.json",
)

# Producer-monitor hint. Advanced Scene Switcher can watch this file.
SCENE_HOST = "host"
SCENE_HOST_JESS = "host-jess"


class DataError(Exception):
    """obs-data.json failed validation. The previous generated files stay put."""


def repo_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return Path(__file__).resolve().parent.parent


def data_path(root: Path, explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return root / DATA_NAME


def playlist_path(root: Path) -> Path:
    return root / PLAYLIST_NAME


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"Missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError(f"{path} must be a JSON object")
    return data


def atomic_write(path: Path, text: str) -> None:
    """Write UTF-8 text and replace the destination.

    OBS reads these files while we write them. A direct write can be caught
    halfway; write a temp file in the same directory and replace it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def one_line(text: str) -> str:
    return " ".join(text.strip().split())


def chyron_body(primary: str, secondary: str) -> str:
    primary = one_line(primary)
    secondary = one_line(secondary)
    if secondary:
        return f"{primary}\n{secondary}\n"
    return f"{primary}\n"


def split_chyron(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    primary = lines[0] if lines else ""
    secondary = " ".join(lines[1:]) if len(lines) > 1 else ""
    return primary, secondary


def safe_token(value: str, label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value).strip()).strip("-")
    if not cleaned:
        raise DataError(f"Cannot make a filename from {label} {value!r}")
    return cleaned


def prune(directory: Path, keep: set[Path]) -> None:
    """Delete files in directory that this build did not write."""
    if not directory.exists():
        return
    keep_resolved = {path.resolve() for path in keep}
    for path in sorted(directory.rglob("*"), reverse=True):
        if path.is_file() and path.resolve() not in keep_resolved:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def sorted_segments(playlist: dict) -> list[dict]:
    return sorted(playlist["segments"], key=lambda segment: segment["order"])


def segment_by_order(playlist: dict, order: int) -> dict | None:
    for segment in playlist["segments"]:
        if segment["order"] == order:
            return segment
    return None
