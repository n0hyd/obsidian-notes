import os

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

import config


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize(transcript: str) -> str:
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize short spoken work notes into a single factual, "
                        "concise bullet point for a daily work log. Preserve names, dates, "
                        "and specifics exactly as stated. No preamble, output only the bullet text."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
        )
    except OpenAIError as exc:
        raise RuntimeError("OpenAI summarization request failed") from exc

    summary = response.choices[0].message.content.strip()
    if not summary:
        raise RuntimeError("OpenAI summarization returned no text")

    return summary


def generate_note_title(transcript: str) -> str:
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a short, descriptive markdown title for a note. "
                        "Keep it to 4-6 words, no quotes, and no punctuation at the end."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
        )
    except OpenAIError as exc:
        raise RuntimeError("OpenAI title generation request failed") from exc

    title = response.choices[0].message.content.strip()
    if not title:
        raise RuntimeError("OpenAI title generation returned no text")

    return title
