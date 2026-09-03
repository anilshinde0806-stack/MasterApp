"""Provider-neutral interface for vehicle damage detection.

The review UI stores and reviews :class:`JobCardDamageAISuggestion` records.
An image model can be connected later by implementing ``analyze`` and
persisting its normalized 0-100 bounding boxes through the existing model.
"""

import base64
import json
import mimetypes
import os

import requests


class DamageAIConfigurationError(RuntimeError):
    pass


class DamageAIProvider:
    name = "pending_provider"

    def analyze(self, image_file):
        """Return normalized suggestions, or an empty list until a provider is configured."""
        return []


class OpenAIDamageAIProvider(DamageAIProvider):
    name = "openai"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_DAMAGE_MODEL", "gpt-4.1-mini").strip()
        self.endpoint = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses").strip()
        if not self.api_key:
            raise DamageAIConfigurationError("OPENAI_API_KEY is not configured.")

    def analyze(self, image_file):
        image_file.seek(0)
        encoded = base64.b64encode(image_file.read()).decode("ascii")
        mime = mimetypes.guess_type(getattr(image_file, "name", "photo.jpg"))[0] or "image/jpeg"
        prompt = (
            "Inspect this vehicle photo for visible repair damage. Return ONLY valid JSON with an array named "
            "suggestions. Each item must contain category (dent, scratch, broken, paint, missing, glass, other), "
            "confidence (0-100), x, y, width, height (all percentages from the top-left), and note. "
            "Do not guess hidden damage; return an empty array when no visible damage is present."
        )
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "input": [{"role": "user", "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}", "detail": "high"},
                ]}],
                "max_output_tokens": 900,
            },
            timeout=90,
        )
        if not response.ok:
            detail = response.text[:1000].strip()
            raise requests.HTTPError(
                f"OpenAI API returned HTTP {response.status_code}: {detail}",
                response=response,
            )
        payload = response.json()
        text = payload.get("output_text", "")
        if not text:
            for item in payload.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        text += content.get("text", "")
        parsed = json.loads(text.strip().strip("`").replace("json\n", "", 1))
        return parsed.get("suggestions", []) if isinstance(parsed, dict) else []


class GeminiDamageAIProvider(DamageAIProvider):
    name = "gemini"

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_DAMAGE_MODEL", "gemini-3.6-flash").strip()
        self.endpoint = os.getenv(
            "GEMINI_GENERATE_CONTENT_URL",
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        ).strip()
        if not self.api_key:
            raise DamageAIConfigurationError("GEMINI_API_KEY is not configured.")

    def analyze(self, image_file):
        image_file.seek(0)
        encoded = base64.b64encode(image_file.read()).decode("ascii")
        mime = mimetypes.guess_type(getattr(image_file, "name", "photo.jpg"))[0] or "image/jpeg"
        prompt = (
            "Inspect this vehicle photo for visible repair damage. Return ONLY valid JSON with an array named "
            "suggestions. Each item must contain category (dent, scratch, broken, paint, missing, glass, other), "
            "confidence (0-100), x, y, width, height (all percentages from the top-left), and note. "
            "Do not guess hidden damage; return an empty array when no visible damage is present."
        )
        response = requests.post(
            self.endpoint.format(model=self.model),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": encoded}},
                ]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
            },
            timeout=90,
        )
        if not response.ok:
            detail = response.text[:1000].strip()
            raise requests.HTTPError(
                f"Gemini API returned HTTP {response.status_code}: {detail}", response=response
            )
        payload = response.json()
        text = "".join(
            part.get("text", "")
            for candidate in payload.get("candidates", [])
            for part in candidate.get("content", {}).get("parts", [])
        )
        parsed = json.loads(text.strip().strip("`").replace("json\n", "", 1))
        return parsed.get("suggestions", []) if isinstance(parsed, dict) else []


def get_damage_ai_provider():
    """Return the configured provider without making the UI depend on a vendor."""
    provider = os.getenv("DAMAGE_AI_PROVIDER", "openai").strip().lower()
    if provider in {"", "none", "pending_provider"}:
        return DamageAIProvider()
    if provider == "openai":
        return OpenAIDamageAIProvider()
    if provider == "gemini":
        return GeminiDamageAIProvider()
    raise DamageAIConfigurationError(f"Unsupported damage AI provider: {provider}")
