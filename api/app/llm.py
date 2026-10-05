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
        self.reasoning_effort = config.llm.reasoning_effort

    async def chat(self, system: str, user: str, max_tokens: int = 500) -> str:
        headers = {"Authorization": f"Bearer {self.api_key or 'dummy'}"}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        choice = resp.json()["choices"][0]
        text = choice["message"].get("content") or ""
        if not text.strip() and choice.get("finish_reason") == "length":
            raise RuntimeError(
                "model exhausted max_tokens before emitting content "
                "(reasoning budget too large; set llm.reasoning_effort or raise max_tokens)"
            )
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
