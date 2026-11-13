import json
import logging
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Initialize Google GenAI client if key is present
_genai_client = None
if settings.has_gemini:
    try:
        from google import genai
        _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Google GenAI client successfully initialized with model %s", settings.GEMINI_MODEL)
    except Exception as e:
        logger.warning("Failed to initialize Google GenAI client: %s", e)
        _genai_client = None
else:
    logger.info("GEMINI_API_KEY not configured. Running in offline/graceful mode.")


class GeminiNotConfiguredError(RuntimeError):
    """Raised when an AI operation is requested but GEMINI_API_KEY is not set."""
    pass


def get_genai_client():
    global _genai_client
    if _genai_client is None and settings.has_gemini:
        try:
            from google import genai
            _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error("Error creating Google GenAI client: %s", e)
    return _genai_client


async def generate_structured(prompt: str, schema_cls: Type[T], max_retries: int = 1) -> T:
    """
    Call Gemini using google-genai SDK requesting structured JSON matching the Pydantic schema.
    If validation fails, retries once with error correction hint.
    """
    client = get_genai_client()
    if not client:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not configured on the server.")

    from google.genai import types

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        raw_text = (response.text or "").strip()
        # Clean markdown codeblocks if model inadvertently added them
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        return schema_cls.model_validate_json(raw_text)

    except Exception as exc:
        logger.warning("Primary structured generation failed (%s). Retrying with correction hint...", exc)
        if max_retries <= 0:
            raise

        retry_prompt = (
            f"{prompt}\n\n"
            f"PREVIOUS RESPONSE FAILED VALIDATION:\n"
            f"Error: {exc}\n"
            f"Schema fields: {list(schema_cls.model_fields.keys())}\n"
            f"Output ONLY valid raw JSON matching the schema."
        )

        retry_response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=retry_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        retry_text = (retry_response.text or "").strip()
        if retry_text.startswith("```json"):
            retry_text = retry_text[7:]
        if retry_text.startswith("```"):
            retry_text = retry_text[3:]
        if retry_text.endswith("```"):
            retry_text = retry_text[:-3]
        retry_text = retry_text.strip()

        return schema_cls.model_validate_json(retry_text)


async def transcribe_multimodal(file_bytes: bytes, mime_type: str = "application/pdf", prompt: Optional[str] = None) -> str:
    """
    Pass binary file bytes (PDF or scanned image) to Gemini multimodal model
    to extract text when PyMuPDF extracted under 50 characters.
    """
    client = get_genai_client()
    if not client:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not configured on the server.")

    from google.genai import types

    if not prompt:
        prompt = (
            "Transcribe all text from this scanned VTU question paper or study note accurately. "
            "Preserve module numbers, question numbers, sub-questions, and marks verbatim."
        )

    file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[file_part, prompt],
        config=types.GenerateContentConfig(
            temperature=0.1,
        ),
    )
    return (response.text or "").strip()
