import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from intent import detect_intent, extract_task, strip_intent_trigger
from obsidian_writer import (
    append_task_to_daily_note,
    append_to_daily_note,
    create_quick_note,
    create_meeting_note,
)
from summarize import generate_note_title, summarize
from transcribe import get_recording_timestamp, transcribe


def process_file(audio_path: str) -> bool:
    filename = Path(audio_path).name

    try:
        transcript = transcribe(audio_path)
    except Exception:
        logging.exception("Failed during transcription for %s", filename)
        return False

    try:
        timestamp = get_recording_timestamp(audio_path)
    except Exception:
        logging.exception("Failed to get recording timestamp for %s", filename)
        return False

    intent = detect_intent(transcript)

    try:
        if intent == "task":
            extraction = extract_task(transcript, timestamp)
            append_task_to_daily_note(
                extraction.task_text, extraction.due_date, timestamp
            )
            logging.info("Successfully processed task for %s", filename)
        elif intent == "quick_note":
            note_text = strip_intent_trigger(transcript)
            title = generate_note_title(note_text)
            summary = summarize(note_text)
            create_quick_note(title, summary, timestamp)
            logging.info("Successfully processed quick note for %s", filename)
        elif intent == "meeting_note":
            note_text = strip_intent_trigger(transcript)
            title = generate_note_title(note_text)
            summary = summarize(note_text)
            create_meeting_note(title, summary, timestamp)
            logging.info("Successfully processed meeting note for %s", filename)
        else:
            summary = summarize(transcript)
            append_to_daily_note(summary, timestamp)
            logging.info("Successfully processed note for %s", filename)
    except Exception:
        logging.exception("Failed during intent processing for %s", filename)
        return False

    return True


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
        if not process_file(path_string):
            logging.warning("Backlog file was not processed successfully: %s", path)
            continue

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
