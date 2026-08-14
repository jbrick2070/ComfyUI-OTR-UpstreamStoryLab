"""Run staged authoring on the model ComfyUI already has loaded.

The ComfyUI workflow writes the ledger, so the model lives in that process and
the lab must not load a second one.  Production's writer already builds exactly
the callable needed::

    generate_fn(messages, *, temperature, max_new_tokens, stop=None) -> str

It closes over the tokenizer, the context cap and the episode sampling knobs
from the workflow widgets, and left-truncates an oversized prompt.  This module
adapts that callable to :class:`StagedModelProvider`, so the executor drops
into the existing plumbing at transplant time instead of inventing a second way
to reach a model.

The adapter stays deliberately thin.  It chooses no model, owns no sampling
policy beyond the per-job decode guard the executor computed, and never edits
what the model wrote.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from .authoring_executor import ModelJobRequest
from .local_model_provider import LocalModelError, extract_json_object


SYSTEM_PROMPT = (
    "You are a writers' room for period radio drama. "
    "Answer only with the JSON object the job asks for."
)


class GenerateFn(Protocol):
    """The callable production's writer node already builds."""

    def __call__(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_new_tokens: int,
        stop: list[str] | None = None,
    ) -> str: ...


class GenerateFnProvider:
    """Answer authoring jobs through an in-process ``generate_fn``.

    ``temperature`` is the one sampling control this provider chooses, because
    the executor's decode guard owns the token budget and the repetition
    penalty is an episode-level widget captured by the closure.  Planning jobs
    can run cooler than dialogue jobs, which is the only place a story is
    actually written, so the split is exposed rather than hidden.
    """

    #: Jobs that plan rather than write.  Lower temperature keeps a small
    #: model from inventing structure it was told to derive.
    PLANNING_JOBS = frozenset(
        {"story_seed", "story_arc", "act_spine", "act_beats"}
    )

    def __init__(
        self,
        generate_fn: GenerateFn,
        *,
        planning_temperature: float = 0.6,
        writing_temperature: float = 0.85,
        system_prompt: str = SYSTEM_PROMPT,
        on_call: Callable[[ModelJobRequest], None] | None = None,
    ) -> None:
        self.generate_fn = generate_fn
        self.planning_temperature = planning_temperature
        self.writing_temperature = writing_temperature
        self.system_prompt = system_prompt
        self.on_call = on_call
        #: Every exchange, verbatim, so a disappointing story can be traced
        #: back to the call that produced it.
        self.transcript: list[dict[str, Any]] = []

    def temperature_for(self, request: ModelJobRequest) -> float:
        if request.kind in self.PLANNING_JOBS:
            return self.planning_temperature
        return self.writing_temperature

    def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
        if self.on_call is not None:
            self.on_call(request)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": request.prompt},
        ]
        try:
            reply = self.generate_fn(
                messages,
                temperature=self.temperature_for(request),
                max_new_tokens=request.decode_guard.max_new_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced with job context
            raise LocalModelError(
                f"{request.job_id} attempt {request.attempt_number} failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        self.transcript.append(
            {
                "job_id": request.job_id,
                "attempt": request.attempt_number,
                "kind": request.kind,
                "temperature": self.temperature_for(request),
                "max_new_tokens": request.decode_guard.max_new_tokens,
                "prompt": request.prompt,
                "raw_reply": reply,
                "feedback_in": list(request.feedback),
            }
        )
        # Forgiving about packaging, strict about content: a small model that
        # fences its JSON has not written a bad story.
        return extract_json_object(reply if isinstance(reply, str) else str(reply))


__all__ = ["GenerateFn", "GenerateFnProvider", "SYSTEM_PROMPT"]
