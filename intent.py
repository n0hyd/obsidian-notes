import os
import string
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

import config


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class TaskExtraction(BaseModel):
    task_text: str
    due_date: str


def _strip_leading_fillers(transcript: str) -> str:
    filler_words = {
        str(word).strip().lower()
        for word in config.FILLER_WORDS
    }
    remaining = transcript.lstrip()

    while remaining:
        parts = remaining.split(None, 1)
        first_word = parts[0]
        normalized = first_word.strip(string.punctuation).lower()

        if not normalized or normalized not in filler_words:
            break

        remaining = parts[1] if len(parts) > 1 else ""
        remaining = remaining.lstrip()

    return remaining


def detect_intent(transcript: str) -> str:
    remaining = _strip_leading_fillers(transcript)
    task_trigger_phrase = config.TASK_TRIGGER_PHRASE.lower()
    quick_note_trigger_phrase = config.QUICK_NOTE_TRIGGER_PHRASE.lower()
    meeting_note_trigger_phrase = getattr(config, "MEETING_NOTE_TRIGGER_PHRASE", "meeting note").lower()

    if remaining.lower().startswith(task_trigger_phrase):
        return "task"

    if remaining.lower().startswith(quick_note_trigger_phrase):
        return "quick_note"

    if remaining.lower().startswith(meeting_note_trigger_phrase):
        return "meeting_note"

    return "note"


def strip_intent_trigger(transcript: str) -> str:
    remaining = _strip_leading_fillers(transcript)
    task_trigger_phrase = config.TASK_TRIGGER_PHRASE.lower()
    quick_note_trigger_phrase = config.QUICK_NOTE_TRIGGER_PHRASE.lower()
    meeting_note_trigger_phrase = getattr(config, "MEETING_NOTE_TRIGGER_PHRASE", "meeting note").lower()
    lower_remaining = remaining.lower()

    if lower_remaining.startswith(task_trigger_phrase):
        return remaining[len(config.TASK_TRIGGER_PHRASE):].lstrip()

    if lower_remaining.startswith(quick_note_trigger_phrase):
        return remaining[len(config.QUICK_NOTE_TRIGGER_PHRASE):].lstrip()

    if lower_remaining.startswith(meeting_note_trigger_phrase):
        return remaining[len(config.MEETING_NOTE_TRIGGER_PHRASE):].lstrip()

    return remaining


def extract_task(transcript: str, reference_date: datetime) -> TaskExtraction:
    response = client.beta.chat.completions.parse(
        model=config.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract a task from this spoken note. task_text is the task "
                    "itself, concise, factual, stripped of the 'create a task' trigger "
                    "phrase and any filler words - do not include the due date in "
                    "task_text. due_date must be resolved to YYYY-MM-DD format; if the "
                    "speaker says a relative date like 'tomorrow' or 'next Thursday', "
                    "resolve it using the reference date provided. If no due date is "
                    "stated at all, use the reference date itself as due_date."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Transcript:\n{transcript}\n\n"
                    "Reference date:\n"
                    f"{reference_date.strftime('%A, %Y-%m-%d')}"
                ),
            },
        ],
        response_format=TaskExtraction,
    )
    return response.choices[0].message.parsed
