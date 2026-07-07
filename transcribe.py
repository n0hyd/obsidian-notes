import json
import logging
import os
import subprocess
from datetime import datetime, timezone

from faster_whisper import WhisperModel
from mutagen import File as MutagenFile

import config


os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", config.HF_HUB_DISABLE_SYMLINKS_WARNING)
MODEL = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(audio_path: str) -> str:
    try:
        segments, _ = MODEL.transcribe(audio_path)
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to transcribe audio file: {audio_path}") from exc

    if not transcript:
        raise RuntimeError(f"Transcription returned no text for audio file: {audio_path}")

    return transcript


def _parse_iso_datetime(value):
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed

    return parsed.astimezone().replace(tzinfo=None)


def _parse_ffprobe_creation_time(audio_path):
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_entries",
        "format_tags=creation_time",
        audio_path,
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError:
        return None

    try:
        payload = json.loads(result.stdout)
        creation_time = payload["format"]["tags"]["creation_time"]
        parsed = _parse_iso_datetime(creation_time)
    except Exception:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)

    logging.debug("Recording timestamp source: ffprobe")
    return parsed


def _parse_mutagen_tag_datetime(value):
    candidates = value if isinstance(value, list) else [value]

    for candidate in candidates:
        if candidate is None:
            continue

        text = str(candidate).strip()
        if not text:
            continue

        try:
            parsed = _parse_iso_datetime(text)
            logging.debug("Recording timestamp source: mutagen")
            return parsed
        except ValueError:
            for format_string in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y:%m:%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(text, format_string)
                    logging.debug("Recording timestamp source: mutagen")
                    return parsed
                except ValueError:
                    continue

    return None


def _parse_mutagen_creation_time(audio_path):
    try:
        metadata = MutagenFile(audio_path)
    except Exception:
        return None

    if metadata is None or not getattr(metadata, "tags", None):
        return None

    for tag_name in ("©day", "date"):
        try:
            value = metadata.tags.get(tag_name)
        except Exception:
            value = None

        parsed = _parse_mutagen_tag_datetime(value)
        if parsed is not None:
            return parsed

    return None


def get_recording_timestamp(audio_path: str) -> datetime:
    timestamp = _parse_ffprobe_creation_time(audio_path)
    if timestamp is not None:
        return timestamp

    timestamp = _parse_mutagen_creation_time(audio_path)
    if timestamp is not None:
        return timestamp

    local_timestamp = datetime.fromtimestamp(os.path.getctime(audio_path))
    logging.debug("Recording timestamp source: filesystem")
    return local_timestamp
