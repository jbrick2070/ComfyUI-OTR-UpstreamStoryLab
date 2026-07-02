"""Pure preview helpers for lab fixtures."""

from __future__ import annotations

from .catalogs import (
    get_profile,
    get_story_model,
    get_visual_style_policy,
    resolve_visual_style_id,
)
from .contracts import LedgerWritingSpec, SourceMaterialPacket, StoryInputPacket

FORBIDDEN_MEDIA_ARCHIVE_PROMPT_TERMS = (
    "science-fiction audio drama",
    "sci-fi radio drama",
    "real science",
    "news facts",
    "star trek",
    "spaceship",
    "mission control",
    "lab containment",
    "laboratory containment",
)


def interpret_fixture_material(
    material: SourceMaterialPacket,
    *,
    story_model_id: str = "auto",
) -> StoryInputPacket:
    """Create an interpreted packet without LLM calls."""

    if material.source_bank_id == "media_archive":
        model = get_story_model("media_archive", story_model_id)
        return StoryInputPacket(
            source_bank_id="media_archive",
            story_model_id=model.story_model_id,
            source_label=material.source_label,
            casting_brief=(
                "Characters orbit the care, recovery, and meaning of a media "
                f"artifact: {material.source_title or 'untitled'}"
            ),
            script_brief=material.source_summary,
            close_brief=(
                "Archive note: preservation work can change what a community "
                "remembers and who gets heard."
            ),
            key_terms=["archive", "restoration", "broadcast history"],
            source_fidelity_rules=[
                "Do not convert the archive object into a futuristic invention.",
                "Keep conflict non-violent and media-cultural.",
            ],
            adaptation_trace={
                "story_model_id": model.story_model_id,
                "fixture": True,
            },
            source_material=material,
        )
    if material.source_bank_id == "science_news":
        model = get_story_model("science_news", story_model_id)
        return StoryInputPacket(
            source_bank_id="science_news",
            story_model_id=model.story_model_id,
            source_label=material.source_label,
            casting_brief="Science/news fixture casting brief.",
            script_brief=material.source_summary,
            close_brief="Science note: fixture close brief.",
            key_terms=["science", "sensor", "ocean"],
            source_material=material,
        )
    if material.source_bank_id == "public_domain_story":
        model = get_story_model("public_domain_story", story_model_id)
        title = material.source_title or "public-domain source"
        author = material.source_author or "unknown author"
        return StoryInputPacket(
            source_bank_id="public_domain_story",
            story_model_id=model.story_model_id,
            source_label=material.source_label,
            casting_brief=(
                "Preserve the named characters, relationships, major turns, "
                f"and ending from {title} by {author}."
            ),
            script_brief=material.raw_text or material.source_summary,
            close_brief=(
                f"Source attribution: adapted from {title} by {author}, "
                "public-domain source material."
            ),
            key_terms=[
                "public domain",
                material.source_kind or "source text",
                title,
            ],
            source_fidelity_rules=[
                "Preserve named characters from the supplied source.",
                "Preserve the major turns and ending unless the source is marked as an excerpt.",
                "Do not replace the source with an unrelated original plot.",
            ],
            adaptation_trace={
                "story_model_id": model.story_model_id,
                "source_kind": material.source_kind,
                "fixture": True,
            },
            source_material=material,
        )
    raise ValueError(f"unsupported source_bank_id={material.source_bank_id!r}")


def build_spec_from_material(
    material: SourceMaterialPacket,
    *,
    story_model_id: str = "auto",
    story_pipeline_id: str = "legacy_many_pass",
    visual_style_id: str = "auto",
) -> LedgerWritingSpec:
    """Build a fixture-only ledger-writing spec."""

    story_input = interpret_fixture_material(material, story_model_id=story_model_id)
    profile = get_profile(material.source_bank_id, story_input.story_model_id)
    resolved_visual_style_id = resolve_visual_style_id(
        material.source_bank_id,
        visual_style_id,
    )
    visual_policy = get_visual_style_policy(resolved_visual_style_id)
    return LedgerWritingSpec(
        source_bank_id=material.source_bank_id,
        story_model_id=story_input.story_model_id,
        story_pipeline_id=story_pipeline_id,
        visual_style_id=visual_policy.style_id,
        source_material=material,
        story_input=story_input,
        prompt_profile=profile,
        visual_policy=visual_policy,
    )


def build_legacy_news_mirror(spec: LedgerWritingSpec) -> dict:
    """Compatibility mirror shape for current `meta.news` consumers."""

    material = spec.source_material
    story = spec.story_input
    return {
        "title": material.source_title,
        "headline": material.source_title,
        "script_brief": story.script_brief,
        "news_close_brief": story.close_brief,
        "casting_brief": story.casting_brief,
        "key_terms": list(story.key_terms),
        "link": material.source_url,
        "source_hash": material.source_hash,
    }


def render_prompt_preview(spec: LedgerWritingSpec) -> str:
    """Return a simple prompt preview string for leakage checks."""

    profile = spec.prompt_profile
    model = get_story_model(spec.source_bank_id, spec.story_model_id)
    parts = [
        profile.outline_system_prompt,
        f"Story form: {profile.story_form_label}",
        f"Source material: {profile.source_material_label}",
        f"Develop verb: {profile.source_develop_verb}",
        f"Grounding: {profile.source_grounding_label}",
        f"Line instruction: {profile.line_grounding_instruction}",
        "Tone guardrails: " + "; ".join(model.tone_guardrails),
        # Keep forbidden examples as metadata, not generative prompt text. Some
        # image/text models copy negated terms, so the live prompt should not
        # contain phrases we want to suppress.
        f"Forbidden pattern count: {len(model.forbidden_plot_patterns)}",
    ]
    return "\n".join(p for p in parts if p)


def find_forbidden_media_archive_terms(text: str) -> list[str]:
    """Return forbidden terms found in a media-archive prompt preview."""

    low = (text or "").lower()
    return [term for term in FORBIDDEN_MEDIA_ARCHIVE_PROMPT_TERMS if term in low]
