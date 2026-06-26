"""Pluggable model client for the understanding step — optional, off by default.

The agent answers correctly with **no** model (the deterministic resolver). A model only makes the
understanding step robust to unusual phrasing. The contract is one method, ``complete``; the
air-gapped adapter talks to a local Ollama over stdlib ``urllib`` so the base install stays
dependency-free and the offline deployment story holds. Cloud adapters (Bedrock/Anthropic) land with
the cloud deploy phase and lazy-import their SDKs.
"""

from __future__ import annotations

import json
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
