---
name: gemini-structured-output
description: Calling Google Gemini API using google-genai SDK for Pydantic-validated JSON responses
---

# Gemini Structured Output Skill

This skill documents how to reliably call Gemini using the modern `google-genai` SDK and enforce Pydantic validation.

## 1. Setup & Initialization
```python
import os
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None
```

## 2. Structured JSON Generation Pattern
Always request `response_mime_type="application/json"` and supply `response_schema` when possible, or parse with Pydantic:

```python
async def generate_structured(prompt: str, schema_cls):
    if not client:
        raise ValueError("GEMINI_API_KEY is not configured.")

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        )
    )
    raw_text = response.text.strip()
    try:
        return schema_cls.model_validate_json(raw_text)
    except Exception as exc:
        # Retry once with error correction hint
        retry_prompt = f"{prompt}\n\nPrevious response failed validation:\n{raw_text}\nError: {exc}. Output ONLY valid JSON matching schema."
        retry_response = await client.aio.models.generate_content(
            model=model_name,
            contents=retry_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        return schema_cls.model_validate_json(retry_response.text.strip())
```

## 3. Handling Scanned PDFs
If text extraction from PyMuPDF yields under 50 characters, upload the file bytes to Gemini Multimodal directly to read and transcribe questions.
