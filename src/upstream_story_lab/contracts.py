"""Strict pure contracts for the isolated upstream story lab."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceMaterialPacket(BaseModel):
    """Raw source material before interpretation."""

    model_config = ConfigDict(extra="forbid")

    packet_version: int = 1
    source_bank_id: str
    source_mode: str = "fixture"
    source_kind: str = ""
    source_label: str = ""
    rights_status: Literal[
        "unknown",
        "public_domain",
        "licensed",
        "fair_use_research",
    ] = "unknown"
    source_title: str = ""
    source_author: str = ""
    source_url: str = ""
    source_hash: str = ""
    source_text_ref: str = ""
    source_summary: str = ""
    raw_text: str = ""


class PublicDomainSourceManifest(BaseModel):
    """Source-folder manifest for public-domain books, comics, plays, etc."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_bank_id: Literal["public_domain_story"] = "public_domain_story"
    source_kind: str
    title: str
    author: str = ""
    publication_year: int | None = None
    rights_status: Literal["public_domain"] = "public_domain"
    source_url: str = ""
    text_files: list[str] = Field(default_factory=list)
    image_files: list[str] = Field(default_factory=list)
    adaptation_mode: str
    required_fidelity: list[str] = Field(default_factory=list)


class StoryModelSpec(BaseModel):
    """Source-scoped dramatic/tonal writing lane."""

    model_config = ConfigDict(extra="forbid")

    source_bank_id: str
    story_model_id: str
    label: str
    tone_guardrails: list[str] = Field(default_factory=list)
    forbidden_plot_patterns: list[str] = Field(default_factory=list)
    outline_rules_extra: str = ""


class StoryPromptProfile(BaseModel):
    """Prompt persona and source labels for ledger-writing prompts."""

    model_config = ConfigDict(extra="forbid")

    source_bank_id: str
    story_model_id: str
    story_form_label: str
    source_material_label: str
    source_develop_verb: str
    source_grounding_label: str
    key_terms_label: str = "KEY TERMS"
    close_brief_label: str = "source note"
    coda_mode: Literal[
        "real_news_report",
        "archive_source_note",
        "source_attribution",
        "none",
    ]
    title_form_label: str
    line_grounding_instruction: str
    outline_rules_extra: str = ""
    tone_guardrails: list[str] = Field(default_factory=list)
    forbidden_plot_patterns: list[str] = Field(default_factory=list)
    outline_system_prompt: str | None = None
    pitch_room_system_prompt: str | None = None
    story_select_system_prompt: str | None = None
    style_picker_inventor_system_prompt: str | None = None
    style_picker_chooser_system_prompt: str | None = None
    style_picker_chooser_user_template: str | None = None


class StoryPack(BaseModel):
    """Cloneable prompt/content pack for one source/story/pipeline lane."""

    model_config = ConfigDict(extra="forbid")

    source_bank_id: str
    story_model_id: str
    story_pipeline_id: str = "legacy_many_pass"
    label: str
    status: Literal[
        "ready_fixture",
        "experimental",
        "not_implemented",
    ] = "ready_fixture"
    prompt_stages: dict[str, str] = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)
    tone_guardrails: list[str] = Field(default_factory=list)
    forbidden_plot_patterns: list[str] = Field(default_factory=list)
    forbidden_leakage_terms: list[str] = Field(default_factory=list)
    source_requirements: list[str] = Field(default_factory=list)
    ledger_validation_notes: list[str] = Field(default_factory=list)


class StoryInputPacket(BaseModel):
    """Interpreted story material ready for a ledger-writing spec."""

    model_config = ConfigDict(extra="forbid")

    packet_version: int = 1
    source_bank_id: str
    story_model_id: str = "auto"
    source_label: str = ""
    casting_brief: str = ""
    script_brief: str = ""
    close_brief: str = ""
    key_terms: list[str] = Field(default_factory=list)
    source_fidelity_rules: list[str] = Field(default_factory=list)
    adaptation_trace: dict[str, Any] = Field(default_factory=dict)
    source_material: SourceMaterialPacket


class VisualStylePolicy(BaseModel):
    """Still/video rendering policy, independent from source/story model."""

    model_config = ConfigDict(extra="forbid")

    style_id: str
    label: str = ""
    positive_tail: str = ""
    image_grade_tail: str = ""
    broadcast_tail: str = ""
    allow_radio_tails: bool = True
    forbidden_terms: list[str] = Field(default_factory=list)
    announcer_visual_subject: str = ""
    music_visual_subject: str = ""
    scene_open_subject: str = ""
    character_portrait_style: str = ""
    character_scene_style: str = ""
    motion_prompts: dict[str, str] = Field(default_factory=dict)
    ledger_directives: dict[str, Any] = Field(default_factory=dict)


class LedgerWritingSpec(BaseModel):
    """Control plane for filling the existing production ledger."""

    model_config = ConfigDict(extra="forbid")

    source_bank_id: str
    story_model_id: str
    story_pipeline_id: str = "legacy_many_pass"
    visual_style_id: str = "sci_fi_radio"
    source_material: SourceMaterialPacket
    story_input: StoryInputPacket
    prompt_profile: StoryPromptProfile
    visual_policy: VisualStylePolicy

    @model_validator(mode="after")
    def _ids_are_consistent(self) -> "LedgerWritingSpec":
        if self.visual_policy.style_id != self.visual_style_id:
            raise ValueError(
                "visual_policy.style_id must match visual_style_id: "
                f"{self.visual_policy.style_id!r} != {self.visual_style_id!r}"
            )
        if self.story_input.source_bank_id != self.source_bank_id:
            raise ValueError(
                "story_input.source_bank_id must match source_bank_id: "
                f"{self.story_input.source_bank_id!r} != {self.source_bank_id!r}"
            )
        if self.story_input.story_model_id != self.story_model_id:
            raise ValueError(
                "story_input.story_model_id must match story_model_id: "
                f"{self.story_input.story_model_id!r} != {self.story_model_id!r}"
            )
        if self.prompt_profile.source_bank_id != self.source_bank_id:
            raise ValueError(
                "prompt_profile.source_bank_id must match source_bank_id: "
                f"{self.prompt_profile.source_bank_id!r} != {self.source_bank_id!r}"
            )
        if self.prompt_profile.story_model_id != self.story_model_id:
            raise ValueError(
                "prompt_profile.story_model_id must match story_model_id: "
                f"{self.prompt_profile.story_model_id!r} != {self.story_model_id!r}"
            )
        return self
