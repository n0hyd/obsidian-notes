import json
import logging
import re
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config
from main import process_file


AUDIO_EXTENSIONS = {".m4a", ".wav", ".aif"}
DATE_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
POLL_INTERVAL_SECONDS = 2
MAX_WAIT_SECONDS = 60
RESCAN_INTERVAL_SECONDS = 30


def load_processed_files(log_path):
    if not log_path.exists():
        return set()

    try:
        with log_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        logging.exception("Failed to load processed files log: %s", log_path)
        return set()

    if not isinstance(data, list):
        logging.warning("Processed files log is not a JSON list: %s", log_path)
        return set()

    return {str(Path(item).resolve()) for item in data if isinstance(item, str)}


def save_processed_files(log_path, processed_files):
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            json.dump(sorted(processed_files), handle, indent=2)
    except Exception:
        logging.exception("Failed to save processed files log: %s", log_path)


def is_dated_audio_file(path, root_path):
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        return False

    try:
        relative_parts = path.relative_to(root_path).parts
    except ValueError:
        return False

    if len(relative_parts) < 2:
        return False

    return any(DATE_FOLDER_PATTERN.match(part) for part in relative_parts[:-1])


def wait_for_ready_file(path):
    last_size = None
    deadline = time.time() + MAX_WAIT_SECONDS

    while time.time() < deadline:
        if not path.exists():
            logging.warning("File disappeared before it was ready: %s", path)
            return False

        try:
            current_size = path.stat().st_size
        except OSError:
            logging.exception("Failed to read file size: %s", path)
            return False

        if current_size > 0 and current_size == last_size:
            return True

        last_size = current_size
        time.sleep(POLL_INTERVAL_SECONDS)

    logging.warning("File did not finish syncing within %ss: %s", MAX_WAIT_SECONDS, path)
    return False


class JprEventHandler(FileSystemEventHandler):
    def __init__(self, watcher):
        self.watcher = watcher

    def _handle_file_event(self, event_path, is_directory):
        if is_directory:
            return

        self.watcher.handle_new_path(event_path)

    def on_created(self, event):
        self._handle_file_event(event.src_path, event.is_directory)

    def on_moved(self, event):
        self._handle_file_event(event.dest_path, event.is_directory)

    def on_modified(self, event):
        self._handle_file_event(event.src_path, event.is_directory)


class JprWatcher:
    def __init__(self):
        self.root_path = Path(config.JPR_ROOT).resolve()
        self.log_path = Path(config.PROCESSED_LOG).resolve()
        self.processed_files = load_processed_files(self.log_path)
        self.pending_files = set()
        self.lock = threading.Lock()

    def handle_new_path(self, raw_path):
        path = Path(raw_path).resolve()

        if not is_dated_audio_file(path, self.root_path):
            return

        path_string = str(path)

        with self.lock:
            if path_string in self.processed_files or path_string in self.pending_files:
                return

            self.pending_files.add(path_string)

        worker = threading.Thread(target=self._process_when_ready, args=(path,), daemon=True)
        worker.start()

    def _process_when_ready(self, path):
        path_string = str(path)

        try:
            if not wait_for_ready_file(path):
                return

            logging.info("Processing file: %s", path)
            if not process_file(path_string):
                logging.warning("File was not processed successfully: %s", path)
                return

            with self.lock:
                self.processed_files.add(path_string)
                save_processed_files(self.log_path, self.processed_files)

            logging.info("Processed file: %s", path)
        except Exception:
            logging.exception("Unexpected watcher error while processing: %s", path)
        finally:
            with self.lock:
                self.pending_files.discard(path_string)

    def scan_for_unprocessed_files(self):
        if not self.root_path.exists():
            return

        for path in self.root_path.rglob("*"):
            if not path.is_file():
                continue

            self.handle_new_path(path)

    def run(self):
        if not self.root_path.exists():
            logging.error("Watch root does not exist: %s", self.root_path)
            return

        observer = Observer()
        observer.schedule(JprEventHandler(self), str(self.root_path), recursive=True)
        observer.start()

        logging.info("Watching for JPR audio files in %s", self.root_path)
        next_rescan_at = time.time() + RESCAN_INTERVAL_SECONDS

        try:
            while True:
                time.sleep(1)

                if time.time() >= next_rescan_at:
                    self.scan_for_unprocessed_files()
                    next_rescan_at = time.time() + RESCAN_INTERVAL_SECONDS
        except KeyboardInterrupt:
            logging.info("Stopping watcher")
            observer.stop()

        observer.join()


def watch():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    JprWatcher().run()


if __name__ == "__main__":
    watch()
