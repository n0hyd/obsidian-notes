import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import config


def append_to_daily_note(summary: str, timestamp: datetime) -> None:
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

    heading = "### *NOTES*"
    entry = f"- **{timestamp.strftime('%H:%M')}** \u2014 {summary.strip()}"
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
    while insert_index < len(lines) and lines[insert_index].startswith(("-", "*")):
        insert_index += 1

    lines.insert(insert_index, entry)
    note_path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
