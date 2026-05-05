"""
LLM provider abstraction.

Two providers supported:
- openai_compatible: works for Ollama, OpenAI, LocalAI, vLLM, LM Studio, etc.
- anthropic: Anthropic Messages API.

Both expose: `await chat(system, user, max_tokens) -> str`.
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

import httpx

from app.config import config


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, system: str, user: str, max_tokens: int = 500) -> str: ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self) -> None:
        self.base_url = config.llm.base_url.rstrip("/")
        self.model = config.llm.model
        self.api_key = os.environ.get(config.llm.api_key_env, "")
        self.timeout = config.llm.request_timeout

    async def chat(self, system: str, user: str, max_tokens: int = 500) -> str:
        headers = {"Authorization": f"Bearer {self.api_key or 'dummy'}"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return _strip_think(text)


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        self.base_url = (config.llm.base_url or "https://api.anthropic.com").rstrip("/")
        self.model = config.llm.model
        self.api_key = os.environ.get(config.llm.api_key_env, "")
        self.timeout = config.llm.request_timeout

    async def chat(self, system: str, user: str, max_tokens: int = 500) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        body = resp.json()
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        return _strip_think(text)


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks from reasoning models, then trim."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai_compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
}


def get_llm() -> LLMProvider:
    cls = _PROVIDERS.get(config.llm.provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {config.llm.provider}")
    return cls()


llm = get_llm()
