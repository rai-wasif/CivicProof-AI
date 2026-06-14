from __future__ import annotations

import json
import base64
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str | None
    model: str | None
    base_url: str | None = None


class OptionalLLMClient:
    """Small direct API client used only when the user configures a provider."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "OptionalLLMClient":
        provider = (os.getenv("CIVICPROOF_LLM_PROVIDER") or "local").strip().lower()
        if provider == "groq":
            config = LLMConfig(provider, os.getenv("GROQ_API_KEY"), os.getenv("GROQ_MODEL"), "https://api.groq.com/openai/v1")
        elif provider == "openai":
            config = LLMConfig(
                provider,
                os.getenv("OPENAI_API_KEY"),
                os.getenv("OPENAI_MODEL"),
                os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            )
        elif provider == "gemini":
            config = LLMConfig(provider, os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL") or "gemini-1.5-flash")
        else:
            config = LLMConfig("local", None, None)
        return cls(config)

    @property
    def configured(self) -> bool:
        return self.config.provider in {"groq", "openai", "gemini"} and bool(self.config.api_key)

    def generate_json(self, prompt: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        response = self.generate_text(prompt + "\nReturn only valid JSON.")
        if not response:
            return None
        return _extract_json(response)

    def generate_text(self, prompt: str) -> str | None:
        if not self.configured:
            return None
        if self.config.provider in {"groq", "openai"}:
            return self._chat_openai_compatible(prompt)
        if self.config.provider == "gemini":
            return self._chat_gemini(prompt)
        return None

    def _chat_openai_compatible(self, prompt: str) -> str | None:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise civic complaint analysis assistant. Prefer structured, factual outputs.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        try:
            result = requests.post(url, headers=headers, json=payload, timeout=30)
            result.raise_for_status()
            data = result.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _chat_gemini(self, prompt: str) -> str | None:
        model = self.config.model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
        try:
            result = requests.post(url, params={"key": self.config.api_key}, json=payload, timeout=30)
            result.raise_for_status()
            data = result.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None


class GeminiVisionClient:
    """Optional Gemini image-understanding client using the REST generateContent API."""

    def __init__(self, api_key: str | None, model: str | None = None):
        self.api_key = api_key
        self.model = model or "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> "GeminiVisionClient":
        return cls(os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_VISION_MODEL") or os.getenv("GEMINI_MODEL"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def analyze_civic_image(self, image_path: str | Path, complaint_text: str | None = None) -> dict[str, Any] | None:
        if not self.configured:
            return None

        path = Path(image_path)
        if not path.exists() or path.stat().st_size > 20 * 1024 * 1024:
            return None

        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        image_data = base64.b64encode(path.read_bytes()).decode("ascii")
        prompt = (
            "Analyze this civic complaint image for a municipal complaint assistant. "
            "Return only valid JSON with these keys: "
            "summary, issue_category, urgency_level, visible_evidence, missing_details, confidence. "
            "issue_category must be one of: Garbage, Sewage, Road damage, Streetlight, Water leakage, Unknown. "
            "urgency_level must be Low, Medium, or High. "
            "visible_evidence and missing_details must be arrays of short strings. "
            "confidence must be a number from 0 to 1. "
            "Do not invent exact location. "
            f"User complaint text, if any: {complaint_text or 'None'}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": image_data}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            result = requests.post(url, params={"key": self.api_key}, json=payload, timeout=45)
            result.raise_for_status()
            data = result.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return _extract_json(text)
        except Exception:
            return None


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
