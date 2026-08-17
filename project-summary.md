# Project Summary

## Purpose

This project turns Just Press Record audio files from iCloud Drive into structured Obsidian notes on a Windows laptop. It watches for new recordings, transcribes them, determines the note intent from a spoken trigger phrase, uses OpenAI for summarization or task extraction when needed, and writes the result into either the daily note or the Obsidian inbox.

## End-to-End Flow

1. Just Press Record saves audio files into the configured iCloud Drive folder.
2. `watcher.py` monitors that folder recursively and waits for each new file to finish syncing.
3. `main.py` sends the file through transcription and timestamp extraction.
4. `intent.py` checks the transcript for a leading trigger phrase.
5. Based on the detected intent:
   - task items are extracted into task text plus due date
   - quick notes get a generated title and summary
   - meeting notes get a generated title and summary
   - regular notes get summarized into a daily-note bullet
6. `obsidian_writer.py` writes the final output into the correct Obsidian location.
7. The processed file path is saved into `processed_files.json` so it is not handled twice.

## Main Modules

- `config.py`
  Central location for paths, model names, vault name, trigger phrases, filler words, and the processed-file log path.

- `watcher.py`
  Watches the Just Press Record root folder, filters for supported audio extensions, waits for files to stabilize, handles new-file events in background threads, and persists the processed-file set.

- `main.py`
  Orchestrates the pipeline for each file. It also performs a startup backlog scan so older unprocessed recordings are picked up when the script starts.

- `transcribe.py`
  Handles speech-to-text and recording timestamp extraction. It tries `whisperx` first when available, then falls back to `faster-whisper` using the configured local model.

- `intent.py`
  Removes optional filler words at the start of the transcript, detects the note type, strips the spoken trigger phrase, and extracts structured task data with the OpenAI API when the note is a task.

- `summarize.py`
  Makes OpenAI calls for note summarization and title generation.

- `obsidian_writer.py`
  Appends daily-note entries, creates inbox notes, sanitizes filenames, and uses Obsidian Advanced URI to create the daily note automatically if it does not exist yet.

## Note Types and Trigger Phrases

The transcript is checked after removing leading filler words such as `um`, `uh`, `so`, `okay`, `actually`, and `basically`.

- `create a task`
  Launches the task workflow. The script extracts `task_text` and `due_date`, then appends a checkbox item to the current daily note.

- `quick note`
  Launches the quick-note workflow. The script removes the trigger phrase, generates a short title plus summary, and creates a dated markdown note in the Obsidian inbox.

- `meeting note`
  Launches the meeting-note workflow. The script removes the trigger phrase, generates a short title plus summary, and creates a dated markdown note in the Obsidian inbox using the same filename scheme as quick notes.

- no trigger phrase
  Falls back to the default note workflow. The transcript is summarized into a single bullet and appended to the daily note with the recording time.

## Transcription and Timestamp Details

- The configured primary local transcription model is `faster-whisper` with `config.WHISPER_MODEL`.
- If `whisperx` is installed and works, the script uses it first.
- If `whisperx` is unavailable or fails, the script logs a warning and falls back to `faster-whisper`.
- Recording timestamps are read from `ffprobe` metadata first.
- If `ffprobe` does not provide a timestamp, the script tries `mutagen`.
- If neither source works, it falls back to the file creation time from Windows.

## Obsidian Output Behavior

- Daily-note entries are written under the configured daily note folder structure by year and month.
- If the daily note does not exist yet, the script opens an Obsidian Advanced URI to create it and waits up to 15 seconds for the file to appear.
- Task entries are written as checklist items with a due date.
- Default note entries are written as timestamped bullets.
- Quick notes and meeting notes are created as standalone markdown files in the inbox with filenames like `YYYY-MM-DD Title.md`.
- If an inbox note filename already exists, the writer appends `2`, `3`, and so on to avoid collisions.

## State and Error Handling

- Processed files are tracked in `processed_files.json` as resolved absolute paths.
- The watcher avoids duplicate work by tracking both processed files and files currently pending.
- `main.py` treats transcription, timestamp extraction, and intent processing failures as non-fatal for the long-running watcher; errors are logged and the watcher continues.
- `watcher.py` also catches unexpected worker-thread errors so one bad file does not stop monitoring.

## Runtime Requirements

- Windows environment with Python 3.11+
- Just Press Record files syncing into the configured iCloud Drive path
- Obsidian installed with the correct vault name configured
- Obsidian Advanced URI plugin enabled for daily-note auto-creation
- `ffprobe` and `ffmpeg` available on `PATH`
- Python dependencies from `requirements.txt`
- `OPENAI_API_KEY` provided through `.env`

## Operational Notes

- Supported watched audio extensions are `.m4a`, `.wav`, and `.aif`.
- The watcher expects audio files inside date-named folders such as `YYYY-MM-DD`.
- The startup backlog scan processes older unlogged files in timestamp order.
- All path and model changes should be made in `config.py`, not scattered across the codebase.
