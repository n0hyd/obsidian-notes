import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import config


_NOTE_WRITE_LOCK = threading.Lock()


def _resolve_daily_note_path(timestamp: datetime) -> Path:
    daily_folder = (
        Path(config.OBSIDIAN_DAILY_BASE)
        / timestamp.strftime("%Y")
        / timestamp.strftime("%m-%B")
    )
    note_path = daily_folder / f"{timestamp.strftime('%Y-%m-%d')}.md"

    if not note_path.exists():
        uri = (
            "obsidian://advanced-uri"
            f"?vault={quote(config.OBSIDIAN_VAULT_NAME, safe='')}"
            "&daily=true"
        )
        os.startfile(uri)

        deadline = time.time() + 15
        while time.time() < deadline:
            if note_path.exists():
                break
            time.sleep(0.5)

        if not note_path.exists():
            raise RuntimeError(
                "Timed out waiting for Obsidian to create the daily note at "
                f"{note_path}. Check that the Advanced URI plugin is installed "
                "and enabled, the vault name matches exactly, and the Daily "
                "Notes plugin folder pattern matches OBSIDIAN_DAILY_BASE's "
                "year/month structure."
            )

    return note_path


def _insert_after_notes_bullets(note_path: Path, entry: str) -> None:
    heading = "### *NOTES*"
    content = note_path.read_text(encoding="utf-8")

    lines = content.splitlines()
    try:
        heading_index = next(
            index for index, line in enumerate(lines) if line.strip() == heading
        )
    except StopIteration:
        raise RuntimeError(
            f"Required heading {heading!r} was not found in {note_path}. "
            "Check that the daily note template applied correctly."
        )

    insert_index = heading_index + 1
    while insert_index < len(lines) and lines[insert_index].startswith("- "):
        insert_index += 1

    lines.insert(insert_index, entry)
    note_path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def _append_entry_to_daily_note(entry: str, timestamp: datetime) -> None:
    with _NOTE_WRITE_LOCK:
        note_path = _resolve_daily_note_path(timestamp)
        _insert_after_notes_bullets(note_path, entry)


def append_to_daily_note(summary: str, timestamp: datetime) -> None:
    entry = f"- **{timestamp.strftime('%H:%M')}** \u2014 {summary.strip()}"

    _append_entry_to_daily_note(entry, timestamp)


def append_task_to_daily_note(
    task_text: str, due_date: str, timestamp: datetime
) -> None:
    entry = f"- [ ] {task_text.strip()} \U0001f4c5 {due_date.strip()}"

    _append_entry_to_daily_note(entry, timestamp)

def _sanitize_quick_note_title(title: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]+", " ", title)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "Untitled"


def _build_quick_note_path(title: str, timestamp: datetime) -> Path:
    inbox_folder = Path(config.OBSIDIAN_INBOX_BASE)
    inbox_folder.mkdir(parents=True, exist_ok=True)

    safe_title = _sanitize_quick_note_title(title)
    note_path = inbox_folder / f"{timestamp.strftime('%Y-%m-%d')} {safe_title}.md"

    if note_path.exists():
        counter = 2
        while True:
            alternate_path = inbox_folder / (
                f"{timestamp.strftime('%Y-%m-%d')} {safe_title} {counter}.md"
            )
            if not alternate_path.exists():
                return alternate_path
            counter += 1

    return note_path


def create_quick_note(title: str, content: str, timestamp: datetime) -> None:
    note_path = _build_quick_note_path(title, timestamp)
    note_path.write_text(content.strip() + "\n", encoding="utf-8")


def create_meeting_note(title: str, content: str, timestamp: datetime) -> None:
    # Reuse the inbox filename scheme for meeting notes as well
    note_path = _build_quick_note_path(title, timestamp)
    note_path.write_text(content.strip() + "\n", encoding="utf-8")
