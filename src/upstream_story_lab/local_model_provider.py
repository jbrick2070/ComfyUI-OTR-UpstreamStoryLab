"""A real staged-authoring provider for any OpenAI-compatible local server.

Works with LM Studio, llama.cpp's server, Ollama's compatible endpoint, vLLM -
anything exposing ``/v1/chat/completions``.  Standard library only: the lab
takes no new dependency to talk to a model.

The point of this provider is to prove the prompts survive a small local model,
so it is deliberately forgiving about *packaging* and strict about *content*:

* a small model wraps JSON in ``` fences, prefixes it with "Here is the JSON:",
  or trails a closing remark.  None of that is a story defect, so the parser
  recovers the object rather than burning an attempt on it.
* what the model actually *said* is passed through untouched.  This module
  never edits prose, never trims a line, and never repairs a story - the
  executor's acceptance rules and the cleanup model pass own that.

Decode guards ride along with each request: the per-job token budget and the
gentle repetition penalty the executor computed, so a looping decoder is
bounded by the server rather than by hope.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from .authoring_executor import ModelJobRequest


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class LocalModelError(RuntimeError):
    """The local server could not be reached, or returned nothing usable."""


def extract_json_object(text: str) -> dict[str, Any]:
    """Recover the JSON object a model meant to send.

    Tolerates markdown fences, a chatty preamble, and trailing commentary,
    because a 7B wrapping its answer is a packaging quirk rather than a defect
    in the story it wrote.  Raises when there is genuinely no object present.
    """

    if not text or not text.strip():
        raise LocalModelError("model returned an empty response")

    candidates: list[str] = []
    fenced = _FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(text)

    for candidate in candidates:
        candidate = candidate.strip()
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            # Fall back to the outermost balanced {...} span.
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end <= start:
                continue
            try:
                parsed = json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
        if isinstance(parsed, dict):
            return parsed
    raise LocalModelError(
        "model response contained no JSON object: "
        f"{' '.join(text.split())[:200]}"
    )


class LocalModelProvider:
    """Answer authoring jobs from an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = 0.8,
        timeout: float = 300.0,
        api_key: str = "not-needed",
        echo: bool = False,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.api_key = api_key
        self.echo = echo
        #: Every exchange, for reading afterwards.  Prompts and raw replies are
        #: kept verbatim so a disappointing story can be traced to the call
        #: that produced it.
        self.transcript: list[dict[str, Any]] = []

    def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
        guard = request.decode_guard
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a writers' room for period radio drama. "
                        "Answer only with the JSON object the job asks for."
                    ),
                },
                {"role": "user", "content": request.prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": guard.max_new_tokens,
            # Sent under both spellings so llama.cpp-style and OpenAI-style
            # servers each see the one they understand; an unknown field is
            # ignored rather than fatal on every server tested.
            "repeat_penalty": guard.recommended_repetition_penalty,
            "frequency_penalty": 0.0,
        }
        body = json.dumps(payload).encode("utf-8")
        http = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        if self.echo:
            print(f"  -> {request.job_id} (attempt {request.attempt_number})")
        try:
            with urllib.request.urlopen(http, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise LocalModelError(
                f"cannot reach {self.base_url}: {exc}. Start a local server "
                "and load a model first."
            ) from exc
        except TimeoutError as exc:
            raise LocalModelError(
                f"{request.job_id} timed out after {self.timeout}s"
            ) from exc

        try:
            text = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LocalModelError(f"unexpected server response: {raw}") from exc

        self.transcript.append(
            {
                "job_id": request.job_id,
                "attempt": request.attempt_number,
                "prompt": request.prompt,
                "raw_reply": text,
                "feedback_in": list(request.feedback),
            }
        )
        return extract_json_object(text)


__all__ = [
    "DEFAULT_BASE_URL",
    "LocalModelError",
    "LocalModelProvider",
    "extract_json_object",
]
