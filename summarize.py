import os

from dotenv import load_dotenv
from openai import OpenAI

import config


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize(transcript: str) -> str:
    response = client.responses.create(
        model=config.OPENAI_MODEL,
        instructions=(
            "You summarize short spoken work notes into a single factual, "
            "concise bullet point for a daily work log. Preserve names, dates, "
            "and specifics exactly as stated. No preamble, output only the bullet text."
        ),
        input=transcript,
    )
    return response.output_text.strip()
