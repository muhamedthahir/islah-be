from anthropic import Anthropic

from app.config import settings

_client = Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are an editor who turns raw YouTube video transcripts into a "
    "publish-ready written article. Rewrite the linguistic, spoken-style "
    "transcript into clear, well-structured prose with headings and "
    "paragraphs. Remove filler words, false starts, and timestamps. Preserve "
    "the original meaning, examples, and factual content — do not invent "
    "new information. Output only the article text, in Markdown."
)


def generate_article(title: str, transcript_text: str) -> str:
    message = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Video title: {title}\n\n"
                    f"Transcript:\n{transcript_text}"
                ),
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")
