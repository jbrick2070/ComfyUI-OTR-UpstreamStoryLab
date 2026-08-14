"""Pack -> resolved StoryPromptProfile. Validation and merging only.

The profile is a RESOLVED VIEW of (bank defaults + pack). Every string in it
comes from JSON; this module never invents prose. Missing required content is
a hard error naming the pack file.
"""

from __future__ import annotations

from .contracts import (
    AUTHORING_JOB_SEAMS,
    CODA_MODES,
    BankDefaults,
    SourceBankSpec,
    StoryPack,
    StoryPromptProfile,
)
from .registry import Registry, RegistryError


def _merged_labels(bank: SourceBankSpec, pack: StoryPack) -> BankDefaults:
    """Single-level merge: pack label overrides bank default when non-empty."""

    merged = {}
    for field in BankDefaults.model_fields:
        pack_value = getattr(pack.labels, field)
        bank_value = getattr(bank.defaults, field)
        merged[field] = pack_value if str(pack_value).strip() else bank_value
    return BankDefaults(**merged)


def resolve_profile(registry: Registry, source_bank_id: str, story_model_id: str,
                    story_pipeline_id: str) -> StoryPromptProfile:
    bank = registry.bank(source_bank_id)
    pack = registry.pack(source_bank_id, story_model_id, story_pipeline_id)
    pack_path = registry.pack_path(source_bank_id, story_model_id, story_pipeline_id)
    labels = _merged_labels(bank, pack)

    coda_mode = (pack.coda_mode or labels.coda_mode or "").strip()
    if coda_mode not in CODA_MODES:
        raise RegistryError(
            f"{pack_path}: no valid coda_mode resolved (pack={pack.coda_mode!r}, "
            f"bank default={bank.defaults.coda_mode!r}); allowed: {CODA_MODES}. "
            "No default coda is invented."
        )

    required_labels = (
        "story_form_label",
        "source_material_label",
        "source_develop_verb",
        "source_grounding_label",
        "title_form_label",
    )
    missing = [f for f in required_labels if not str(getattr(labels, f)).strip()]
    if missing:
        raise RegistryError(
            f"{pack_path}: unresolved required labels {missing} - supply them in "
            "the pack labels block or the bank defaults (JSON owns content)."
        )

    # A pack carries its bank direction ONE of two ways: the retired many-pass
    # seams (line_grounding among them), or the eight authoring job_prompts the
    # staged executor actually runs. Demanding line_grounding of a
    # job_prompts-only pack would force invented prose for a seam its pipeline
    # never reaches, so the requirement follows the seams, not the pack.
    line_grounding = pack.prompt_stages.get("line_grounding", "").strip()
    if not line_grounding and set(pack.job_prompts) != set(AUTHORING_JOB_SEAMS):
        raise RegistryError(
            f"{pack_path}: carries neither prompt_stages.line_grounding nor the "
            f"full job_prompts set {sorted(AUTHORING_JOB_SEAMS)} - a pack must "
            "declare its bank direction one way or the other; no grounding "
            "instruction is invented in Python."
        )

    def stage(name: str) -> str | None:
        value = pack.prompt_stages.get(name, "").strip()
        return value or None

    return StoryPromptProfile(
        source_bank_id=bank.source_bank_id,
        story_model_id=pack.story_model_id,
        story_form_label=labels.story_form_label,
        source_material_label=labels.source_material_label,
        source_develop_verb=labels.source_develop_verb,
        source_grounding_label=labels.source_grounding_label,
        key_terms_label=labels.key_terms_label,
        close_brief_label=labels.close_brief_label,
        coda_mode=coda_mode,  # type: ignore[arg-type]
        title_form_label=labels.title_form_label,
        line_grounding_instruction=line_grounding,
        outline_rules_extra=pack.outline_rules_extra,
        tone_guardrails=list(pack.tone_guardrails),
        forbidden_plot_patterns=list(pack.forbidden_plot_patterns),
        outline_system_prompt=stage("outline_system"),
        pitch_room_system_prompt=stage("pitch_room_system"),
        story_select_system_prompt=stage("story_select_system"),
        dramatic_state_system_prompt=stage("dramatic_state_system"),
        coda_system_prompt=stage("coda_system"),
        coda_examples=list(pack.coda_examples),
        title_system_prompt=stage("title_system"),
        style_picker_inventor_system_prompt=stage("style_pick_inventor"),
        style_picker_chooser_system_prompt=stage("style_pick_chooser"),
        style_picker_chooser_user_template=stage("style_pick_chooser_user_template"),
    )
