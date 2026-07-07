# AGENTS.md

## Project
Voice note pipeline: Just Press Record (iPhone) → iCloud Drive → watcher script →
faster-whisper transcription → OpenAI summarization → append to Obsidian daily note
(created via Templater/Advanced URI if missing). Runs on a Windows laptop via
Task Scheduler. Single user, single machine, not a distributed or multi-user system.

## Stack
- Python 3.11+, Windows paths (use `pathlib`, raw strings, or forward slashes — never
  hardcode backslash escapes)
- `watchdog` for filesystem monitoring
- `faster-whisper` (CPU, int8) for transcription
- `ffprobe` (via subprocess) for audio metadata timestamps, `mutagen` as fallback
- `openai` SDK for summarization — model name always read from `config.py`, never
  hardcoded in a function body
- No web framework, no database. State is a flat JSON file (`processed_files.json`)
  and markdown files in the Obsidian vault.

## File map
- `config.py` — all constants (paths, model names, vault name). Edit this for any
  path/model change. Nothing else should contain a literal path or model string.
- `watcher.py` — filesystem watching + iCloud placeholder-file polling only
- `transcribe.py` — `transcribe()` and `get_recording_timestamp()` only
- `summarize.py` — `summarize()` only, one OpenAI call
- `obsidian_writer.py` — `append_to_daily_note()` only, including the
  Advanced URI/`os.startfile` daily-note-creation logic
- `main.py` — orchestration (`process_file()`) and the watcher entry point only

## Rules for changes
1. **Stay inside the file(s) named in the prompt.** Don't touch other files unless
   a change is strictly required to fix a bug you were asked to fix — and say which
   file and why in one line, don't rewrite it silently.
2. **Don't re-explain the whole file back.** After an edit, report only what changed,
   in 1-3 bullet points. No restating unchanged code, no walkthroughs of logic that
   didn't move.
3. **No unsolicited refactors.** If you notice an unrelated issue, name it in one line
   at the end ("Note: X could also be improved") — don't fix it unless asked.
4. **Match existing style exactly** rather than reformatting: naming conventions,
   docstring style, error-handling pattern (try/except + log + continue, not raise-
   and-crash) already established in the file you're editing.
5. **Ask before adding a new dependency.** `requirements.txt` is intentionally short —
   flag if a task seems to need a new package instead of silently adding it.
6. **Errors get logged and swallowed at the `process_file()` boundary**, not raised
   up into the watcher loop. One bad file must never kill the running process.
7. **All paths are Windows paths.** Don't introduce POSIX-only path handling
   (`os.path` mixed separators, `/tmp`, etc.).

## Output format for responses
- Code changes only, no preamble ("Here's the updated function...") unless something
  needs a flag (see rules 3 and 5 above).
- Skip summarizing what the code does — the prompt already specified the behavior.
- If a prompt's spec is ambiguous, make the smallest reasonable assumption and note
  it in one line rather than asking a clarifying question, unless the ambiguity
  would change which file gets touched.
- Dont tell me what you are doing, just do it.
- When validating or running code, use `venv\Scripts\python.exe`    (the project's virtual environment), not the system Python. All dependencies from requirements.txt are installed there.