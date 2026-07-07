import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from obsidian_writer import append_to_daily_note
from summarize import summarize
from transcribe import get_recording_timestamp, transcribe


def process_file(audio_path: str) -> None:
    filename = Path(audio_path).name

    try:
        transcript = transcribe(audio_path)
    except Exception:
        logging.exception("Failed during transcription for %s", filename)
        return

    try:
        timestamp = get_recording_timestamp(audio_path)
    except Exception:
        logging.exception("Failed to get recording timestamp for %s", filename)
        return

    try:
        summary = summarize(transcript)
    except Exception:
        logging.exception("Failed during summarization for %s", filename)
        return

    try:
        append_to_daily_note(summary, timestamp)
    except Exception:
        logging.exception("Failed to append daily note for %s", filename)
        return

    logging.info("Successfully processed %s: %s", filename, summary)


def _scan_startup_backlog(watcher_module) -> None:
    root_path = Path(config.JPR_ROOT).resolve()
    log_path = Path(config.PROCESSED_LOG).resolve()
    processed_files = watcher_module.load_processed_files(log_path)
    backlog_candidates = []

    if not root_path.exists():
        logging.error("Watch root does not exist: %s", root_path)
        return

    for path in root_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in watcher_module.AUDIO_EXTENSIONS:
            continue

        path_string = str(path.resolve())
        if path_string in processed_files:
            continue

        backlog_candidates.append(path.resolve())

    backlog_found = len(backlog_candidates)
    ready_backlog = []

    for path in backlog_candidates:
        if not watcher_module.wait_for_ready_file(path):
            continue

        try:
            timestamp = get_recording_timestamp(str(path))
        except Exception:
            logging.exception("Failed to get backlog timestamp for %s", path.name)
            timestamp = datetime.max

        ready_backlog.append((timestamp, path))

    backlog_processed = 0

    for _, path in sorted(ready_backlog, key=lambda item: item[0]):
        path_string = str(path)
        logging.info("Processing backlog file: %s", path)
        process_file(path_string)
        processed_files.add(path_string)
        watcher_module.save_processed_files(log_path, processed_files)
        backlog_processed += 1
        logging.info("Processed backlog file: %s", path)

    logging.info(
        "Startup backlog scan complete: found %s file(s), processed %s file(s)",
        backlog_found,
        backlog_processed,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    import watcher

    _scan_startup_backlog(watcher)
    watcher.watch()


if __name__ == "__main__":
    main()
