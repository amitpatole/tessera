"""Pluggable model client for the understanding step — optional, off by default.

The agent answers correctly with **no** model (the deterministic resolver). A model only makes the
understanding step robust to unusual phrasing. The contract is one method, ``complete``; the
air-gapped adapter talks to a local Ollama over stdlib ``urllib`` so the base install stays
dependency-free and the offline deployment story holds. Cloud adapters (Bedrock/Anthropic) land with
the cloud deploy phase and lazy-import their SDKs.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Anything that can turn a prompt into text. The agent never depends on a concrete provider."""

    def complete(self, prompt: str) -> str: ...


class OllamaClient:
    """A self-hosted, air-gapped model via a local Ollama server (no third-party SDK, no API key)."""

    def __init__(self, model: str = "llama3.1", host: str = "http://127.0.0.1:11434",
                 timeout: float = 30.0) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def complete(self, prompt: str) -> str:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed localhost
            data = json.loads(resp.read().decode())
        return str(data.get("response", ""))


class OpenAIClient:
    """A cloud model via the OpenAI chat-completions API (key from env, no third-party SDK)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None,
                 base_url: str = "https://api.openai.com/v1", timeout: float = 30.0) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed host
            data = json.loads(resp.read().decode())
        return str(data["choices"][0]["message"]["content"])
