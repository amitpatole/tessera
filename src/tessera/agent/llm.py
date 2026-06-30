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
from typing import Any, Protocol, runtime_checkable


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


class VLLMClient(OpenAIClient):
    """A model served by **vLLM** (a PyTorch Foundation project) over its OpenAI-compatible API.

    vLLM runs the model on PyTorch under the hood; from the cascade's side it is just an HTTP
    endpoint, so we reuse the OpenAI chat-completions wire format. Point it at a local vLLM server
    (``vllm serve <model>``) — no API key needed for a self-hosted server, so it stays air-gapped.
    """

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:8000/v1",
                 api_key: str | None = None, timeout: float = 60.0) -> None:
        # vLLM ignores the key for an open server; send a placeholder so the Authorization header
        # is well-formed and the parent's "key is set" guard passes.
        super().__init__(model=model, api_key=api_key or "EMPTY", base_url=base_url, timeout=timeout)


class TorchTransformersClient:
    """A model run **in-process on PyTorch** via 🤗 Transformers — the most literal PyTorch tier.

    This loads a real ``torch.nn.Module`` with ``AutoModelForCausalLM`` and runs ``model.generate``
    on CPU (or CUDA if present). It is heavy, so ``torch``/``transformers`` are imported lazily and
    live behind the ``pytorch`` extra; the base install stays dependency-free. A small model run
    this way genuinely mis-resolves on hard questions — exactly the cheap-but-fallible tier the
    cost cascade is designed to make *safe* (the independent verifier catches the misses).
    """

    def __init__(self, model: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
                 max_new_tokens: int = 96, device: str | None = None) -> None:
        self.model_name = model
        self.max_new_tokens = max_new_tokens
        self._device = device
        self._tok: Any = None  # transformers tokenizer, loaded lazily
        self._model: Any = None  # torch.nn.Module, loaded lazily

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch  # lazy — only when a real PyTorch run is requested
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._device = device
        self._tok = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype=torch.float32
        ).to(device)
        self._model.eval()

    def complete(self, prompt: str) -> str:
        import torch

        self._ensure_loaded()
        assert self._tok is not None and self._model is not None
        messages = [{"role": "user", "content": prompt}]
        text = self._tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tok(text, return_tensors="pt").to(self._device)
        with torch.no_grad():
            out = self._model.generate(
                **inputs, max_new_tokens=self.max_new_tokens, do_sample=False,
                pad_token_id=self._tok.eos_token_id,
            )
        generated = out[0][inputs["input_ids"].shape[1]:]
        return str(self._tok.decode(generated, skip_special_tokens=True))
