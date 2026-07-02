"""Minimal lab runner for lab-executable pipelines (simple_4 only, v1 scope).

Python owns pass sequencing, pass status, and failure reporting. The runner
refuses descriptive pipelines, refuses to skip a failed pass, and never falls
back to another pipeline (kibitz r1: without this runner the experimental
pipeline is fiction; with more than this it is scope creep).
"""

from __future__ import annotations

from typing import Callable

from .contracts import PipelineSpec, StoryPack


class PipelineRunError(RuntimeError):
    """A pass failed. Message names the exact pass. No fallback exists."""


#: FakeLLM signature: (slot_role, pass_id, prompt) -> output text.
LlmCallable = Callable[[str, str, str], str]


def run_pipeline(pack: StoryPack, pipeline: PipelineSpec,
                 llm: LlmCallable) -> dict[str, str]:
    if not pipeline.executable_in_lab:
        raise PipelineRunError(
            f"pipeline {pipeline.story_pipeline_id!r} is descriptive metadata "
            "(production-native); the lab runner refuses to execute it"
        )
    if pack.story_pipeline_id != pipeline.story_pipeline_id:
        raise PipelineRunError(
            f"pack {pack.story_model_id!r} declares pipeline "
            f"{pack.story_pipeline_id!r}, not {pipeline.story_pipeline_id!r}"
        )
    outputs: dict[str, str] = {}
    for decl in pipeline.passes:
        if not decl.seam_refs:
            raise PipelineRunError(
                f"pass {decl.pass_id!r} declares no seam prompt to execute"
            )
        seam = decl.seam_refs[0]
        prompt = (pack.prompt_stages.get(seam) or "").strip()
        if not prompt:
            raise PipelineRunError(
                f"pass {decl.pass_id!r}: pack {pack.story_model_id!r} has no "
                f"prompt for seam {seam!r} (JSON owns content; nothing is invented)"
            )
        try:
            result = llm(decl.slot, decl.pass_id, prompt)
        except Exception as exc:
            raise PipelineRunError(
                f"pass {decl.pass_id!r} raised: {exc} - failing loudly; "
                "no fallback pipeline exists"
            ) from exc
        if not (result or "").strip():
            raise PipelineRunError(
                f"pass {decl.pass_id!r} returned empty output - failing loudly; "
                "no fallback pipeline exists"
            )
        outputs[decl.pass_id] = result
    return outputs
