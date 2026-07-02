"""Fixture-first catalogs for the upstream story lab."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import StoryModelSpec, StoryPromptProfile, VisualStylePolicy


class UnknownStoryModelError(ValueError):
    """Raised when a story model id is not valid for a source bank."""


class UnknownVisualStyleError(ValueError):
    """Raised when a visual style id is unknown."""


MEDIA_ARCHIVE_MODELS: dict[str, StoryModelSpec] = {
    "media_restoration_adventure": StoryModelSpec(
        source_bank_id="media_archive",
        story_model_id="media_restoration_adventure",
        label="Media restoration adventure",
        tone_guardrails=[
            "Center preservation, recovery, cataloging, damaged media, or rediscovery.",
            "Keep stakes warm, human, and non-violent.",
            "Make the archive object culturally meaningful.",
        ],
        forbidden_plot_patterns=[
            "Star-Trek-style mission plot",
            "Amazing-Stories-style twist anthology",
            "spaceship rescue",
            "laboratory containment breach",
            "generic science experiment emergency",
        ],
        outline_rules_extra=(
            "Build suspense from fragile media, missing context, deadlines, "
            "or institutional pressure, not from futuristic danger."
        ),
    ),
    "cinematic_humorous": StoryModelSpec(
        source_bank_id="media_archive",
        story_model_id="cinematic_humorous",
        label="Cinematic humorous media story",
        tone_guardrails=[
            "Use polished comic timing and affectionate media-culture detail.",
            "Keep conflict social, logistical, or interpretive.",
        ],
        forbidden_plot_patterns=[
            "spaceship",
            "alien signal",
            "doomsday device",
        ],
    ),
    "happy_archive_mystery": StoryModelSpec(
        source_bank_id="media_archive",
        story_model_id="happy_archive_mystery",
        label="Happy archive mystery",
        tone_guardrails=[
            "Let discovery, recognition, or repair create an upbeat ending.",
            "Use mystery as puzzle and memory, not menace.",
        ],
        forbidden_plot_patterns=[
            "violent conspiracy",
            "horror haunting",
            "lab containment",
        ],
    ),
    "gentle_thriller": StoryModelSpec(
        source_bank_id="media_archive",
        story_model_id="gentle_thriller",
        label="Gentle media thriller",
        tone_guardrails=[
            "Use suspense from time pressure, fragile evidence, and public reveal.",
            "Stay non-violent and non-horror.",
        ],
        forbidden_plot_patterns=[
            "body count",
            "armed chase",
            "monster reveal",
        ],
    ),
    "broadcast_history_comedy": StoryModelSpec(
        source_bank_id="media_archive",
        story_model_id="broadcast_history_comedy",
        label="Broadcast history comedy",
        tone_guardrails=[
            "Use production mishaps, reception history, fandom, or scholarship.",
            "Keep the comedy kind and character-driven.",
        ],
        forbidden_plot_patterns=[
            "space fleet",
            "laboratory alarm",
            "interdimensional portal",
        ],
    ),
}

PUBLIC_DOMAIN_MODELS: dict[str, StoryModelSpec] = {
    "faithful_radio_adaptation": StoryModelSpec(
        source_bank_id="public_domain_story",
        story_model_id="faithful_radio_adaptation",
        label="Faithful radio adaptation",
        tone_guardrails=[
            "Preserve named characters, major turns, ending, and attribution.",
            "Faithfulness outranks novelty.",
        ],
        forbidden_plot_patterns=[
            "invented protagonist",
            "changed ending",
            "unrelated framing story",
        ],
        outline_rules_extra=(
            "Adapt the source while preserving its characters, turns, and ending."
        ),
    ),
    "chapter_digest_drama": StoryModelSpec(
        source_bank_id="public_domain_story",
        story_model_id="chapter_digest_drama",
        label="Chapter digest drama",
        tone_guardrails=[
            "Compress one chapter into a clear radio episode.",
            "Do not imply the full book was adapted when only a chapter was supplied.",
        ],
        forbidden_plot_patterns=[
            "whole-book summary when source is one chapter",
            "invented ending",
        ],
    ),
    "comic_panel_radio_adaptation": StoryModelSpec(
        source_bank_id="public_domain_story",
        story_model_id="comic_panel_radio_adaptation",
        label="Comic panel radio adaptation",
        tone_guardrails=[
            "Translate panels into audio beats.",
            "Preserve page order and named characters.",
        ],
        forbidden_plot_patterns=[
            "ignoring page order",
            "invented replacement cast",
            "changed punchline",
        ],
    ),
    "stage_play_radio_adaptation": StoryModelSpec(
        source_bank_id="public_domain_story",
        story_model_id="stage_play_radio_adaptation",
        label="Stage play radio adaptation",
        tone_guardrails=[
            "Preserve character names, relationships, scene turns, and ending.",
            "Make stage action audible through dialogue, announcer, or sound.",
        ],
        forbidden_plot_patterns=[
            "renamed characters",
            "changed scene outcome",
        ],
    ),
    "storybook_puppet_show": StoryModelSpec(
        source_bank_id="public_domain_story",
        story_model_id="storybook_puppet_show",
        label="Storybook puppet show",
        tone_guardrails=[
            "Family-friendly and whimsical.",
            "Preserve the source ending unless the manifest marks an excerpt.",
        ],
        forbidden_plot_patterns=[
            "cynical parody",
            "horror turn",
            "changed moral",
        ],
    ),
}

DEFAULT_STORY_MODEL_BY_SOURCE = {
    "media_archive": "media_restoration_adventure",
    "science_news": "science_news_default",
    "public_domain_story": "faithful_radio_adaptation",
}

DEFAULT_VISUAL_STYLE_BY_SOURCE = {
    "media_archive": "archival_documentary",
    "science_news": "sci_fi_radio",
    "public_domain_story": "archival_documentary",
}

SCIENCE_NEWS_DEFAULT = StoryModelSpec(
    source_bank_id="science_news",
    story_model_id="science_news_default",
    label="Science news default",
    tone_guardrails=[
        "Preserve current science/news-driven radio-drama behavior.",
    ],
)


def resolve_story_model_id(source_bank_id: str, story_model_id: str) -> str:
    """Resolve auto to a concrete source-scoped model id."""

    requested = (story_model_id or "auto").strip()
    source = (source_bank_id or "").strip()
    if requested == "auto":
        try:
            return DEFAULT_STORY_MODEL_BY_SOURCE[source]
        except KeyError as exc:
            raise UnknownStoryModelError(
                f"no default story model for source_bank_id={source!r}"
            ) from exc
    return requested


def get_story_model(source_bank_id: str, story_model_id: str) -> StoryModelSpec:
    """Return a story model, fail-closed on unknown ids."""

    resolved = resolve_story_model_id(source_bank_id, story_model_id)
    if source_bank_id == "science_news" and resolved == "science_news_default":
        return SCIENCE_NEWS_DEFAULT
    if source_bank_id == "media_archive":
        try:
            return MEDIA_ARCHIVE_MODELS[resolved]
        except KeyError as exc:
            raise UnknownStoryModelError(
                f"unknown media_archive story_model_id={resolved!r}"
            ) from exc
    if source_bank_id == "public_domain_story":
        try:
            return PUBLIC_DOMAIN_MODELS[resolved]
        except KeyError as exc:
            raise UnknownStoryModelError(
                f"unknown public_domain_story story_model_id={resolved!r}"
            ) from exc
    raise UnknownStoryModelError(
        f"unknown source/story model pair: {source_bank_id!r}/{resolved!r}"
    )


def get_profile(source_bank_id: str, story_model_id: str) -> StoryPromptProfile:
    """Build a prompt profile from a source bank and concrete story model."""

    model = get_story_model(source_bank_id, story_model_id)
    if source_bank_id == "science_news":
        return StoryPromptProfile(
            source_bank_id="science_news",
            story_model_id=model.story_model_id,
            story_form_label="science-fiction audio drama",
            source_material_label="Science story",
            source_develop_verb="extrapolate dramatically from this science story",
            source_grounding_label="news facts",
            coda_mode="real_news_report",
            title_form_label="sci-fi radio drama",
            line_grounding_instruction=(
                "Ground this line in the news facts and this scene's premise."
            ),
            outline_system_prompt=(
                "You are a story editor for short science-fiction audio dramas "
                "grounded in real science."
            ),
            pitch_room_system_prompt=(
                "Create distinct science-news-inspired radio-drama pitches "
                "grounded in the supplied source facts."
            ),
            story_select_system_prompt=(
                "Grade science-news radio-drama candidates for source grounding, "
                "clear stakes, and coherent audio-drama structure."
            ),
        )
    if source_bank_id == "media_archive":
        return StoryPromptProfile(
            source_bank_id="media_archive",
            story_model_id=model.story_model_id,
            story_form_label="archive-inspired radio drama",
            source_material_label="Media archive item",
            source_develop_verb=(
                "build a fictional story from this archive/media-history material"
            ),
            source_grounding_label="archive material",
            coda_mode="archive_source_note",
            title_form_label="archive-inspired radio drama",
            line_grounding_instruction=(
                "Ground this line in the archive material and the scene premise."
            ),
            outline_rules_extra=model.outline_rules_extra,
            tone_guardrails=list(model.tone_guardrails),
            forbidden_plot_patterns=list(model.forbidden_plot_patterns),
            outline_system_prompt=(
                "You are a radio-drama story editor for warm, cinematic, "
                "non-violent archive and media-restoration stories."
            ),
            pitch_room_system_prompt=(
                "Create distinct media-archive story pitches without sci-fi "
                "anthology defaults."
            ),
            story_select_system_prompt=(
                "Grade archive-inspired radio-drama candidates for human stakes, "
                "source fidelity, and non-violent media-culture craft."
            ),
            style_picker_inventor_system_prompt=(
                "You are a media-history radio-drama showrunner, not a sci-fi "
                "anthology writer."
            ),
            style_picker_chooser_system_prompt=(
                "Choose a visual style that supports media-history, restoration, "
                "or archive-source storytelling without sci-fi defaults."
            ),
            style_picker_chooser_user_template=(
                "Choose the best visual style for this media-archive story: "
                "{story_summary}"
            ),
        )
    if source_bank_id == "public_domain_story":
        return StoryPromptProfile(
            source_bank_id="public_domain_story",
            story_model_id=model.story_model_id,
            story_form_label="public-domain radio adaptation",
            source_material_label="Public-domain source text",
            source_develop_verb=(
                "adapt this source while preserving its characters, turns, "
                "and ending"
            ),
            source_grounding_label="source text",
            coda_mode="source_attribution",
            title_form_label="public-domain radio adaptation",
            line_grounding_instruction=(
                "Ground this line in the public-domain source text and the "
                "current scene."
            ),
            outline_rules_extra=model.outline_rules_extra,
            tone_guardrails=list(model.tone_guardrails),
            forbidden_plot_patterns=list(model.forbidden_plot_patterns),
            outline_system_prompt=(
                "You are adapting public-domain source material into radio "
                "drama while preserving source fidelity."
            ),
            pitch_room_system_prompt=(
                "Create adaptation approaches, not unrelated replacement plots."
            ),
            story_select_system_prompt=(
                "Grade public-domain adaptations for source fidelity, clear "
                "audio drama, and valid compression."
            ),
            style_picker_inventor_system_prompt=(
                "You are adapting public-domain source material for visual radio "
                "storytelling while preserving source fidelity."
            ),
            style_picker_chooser_system_prompt=(
                "Choose a visual style that supports the supplied public-domain "
                "source and does not replace the source with a new genre premise."
            ),
            style_picker_chooser_user_template=(
                "Choose the best visual style for this public-domain adaptation: "
                "{story_summary}"
            ),
        )
    raise UnknownStoryModelError(f"no prompt profile for source_bank_id={source_bank_id!r}")


_BASE_VISUAL_STYLES: dict[str, VisualStylePolicy] = {
    "sci_fi_radio": VisualStylePolicy(
        style_id="sci_fi_radio",
        label="Sci-Fi Radio",
        positive_tail="cinematic, 35mm film look, subtle film grain",
        image_grade_tail="anamorphic lens, heavy vignette, muted color grade, sharp focus",
        broadcast_tail="35mm film grain, broadcast-distressed cinematic radio still",
        allow_radio_tails=True,
    ),
    "archival_documentary": VisualStylePolicy(
        style_id="archival_documentary",
        label="Media Archive",
        positive_tail=(
            "archival documentary still, careful restoration texture, tactile "
            "paper and film materials, grounded natural lighting"
        ),
        image_grade_tail="subtle archival patina, clean readable composition",
        broadcast_tail="broadcast-history atmosphere without futuristic equipment",
        allow_radio_tails=False,
        forbidden_terms=[
            "spaceship",
            "mission control",
            "laboratory containment",
            "35mm sci-fi film grain",
            "futuristic console",
        ],
    ),
    "anime": VisualStylePolicy(
        style_id="anime",
        label="Anime",
        positive_tail="anime style, expressive linework, cel-shaded color",
        allow_radio_tails=False,
        forbidden_terms=["photorealistic", "35mm film", "film grain"],
    ),
    "cartoon": VisualStylePolicy(
        style_id="cartoon",
        label="Cartoon",
        positive_tail="bright cartoon illustration, clean shapes, expressive faces",
        allow_radio_tails=False,
        forbidden_terms=["35mm film", "film grain", "photorealistic"],
    ),
    "paper_origami": VisualStylePolicy(
        style_id="paper_origami",
        label="Paper Origami",
        positive_tail="folded paper diorama, papercraft texture, handmade paper edges",
        allow_radio_tails=False,
        forbidden_terms=["photorealistic", "cinematic 35mm", "film grain"],
    ),
}

_VISUAL_STYLES_CACHE: dict[str, VisualStylePolicy] | None = None
_VISUAL_STYLES_STAMP: str | None = None


def _load_visual_style_fixtures() -> dict[str, VisualStylePolicy]:
    """Load visual style JSON fixtures, overriding the built-in catalog."""

    fixture_dir = Path(__file__).resolve().parents[2] / "fixtures" / "visual_styles"
    if not fixture_dir.exists():
        return {}
    styles: dict[str, VisualStylePolicy] = {}
    for path in sorted(fixture_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        policy = VisualStylePolicy(**data)
        styles[policy.style_id] = policy
    return styles


def _visual_style_fixture_stamp() -> str:
    fixture_dir = Path(__file__).resolve().parents[2] / "fixtures" / "visual_styles"
    digest = hashlib.sha256()
    if not fixture_dir.exists():
        return "missing"
    for path in sorted(fixture_dir.glob("*.json")):
        try:
            stat = path.stat()
            digest.update(path.name.encode("utf-8"))
            digest.update(str(stat.st_size).encode("utf-8"))
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        except OSError as exc:
            digest.update(f"{path}:ERROR:{exc}".encode("utf-8"))
    return digest.hexdigest()


def get_visual_styles() -> dict[str, VisualStylePolicy]:
    """Return visual styles with JSON fixture overrides loaded lazily."""

    global _VISUAL_STYLES_CACHE, _VISUAL_STYLES_STAMP
    stamp = _visual_style_fixture_stamp()
    if _VISUAL_STYLES_CACHE is None or _VISUAL_STYLES_STAMP != stamp:
        styles = dict(_BASE_VISUAL_STYLES)
        styles.update(_load_visual_style_fixtures())
        _VISUAL_STYLES_CACHE = styles
        _VISUAL_STYLES_STAMP = stamp
    return _VISUAL_STYLES_CACHE


def get_visual_style_ids() -> list[str]:
    """Return all known visual style ids."""

    return sorted(get_visual_styles())


def resolve_visual_style_id(source_bank_id: str, visual_style_id: str) -> str:
    """Resolve auto to a source-scoped default visual style."""

    requested = (visual_style_id or "auto").strip()
    source = (source_bank_id or "").strip()
    if requested == "auto":
        try:
            return DEFAULT_VISUAL_STYLE_BY_SOURCE[source]
        except KeyError as exc:
            raise UnknownVisualStyleError(
                f"no default visual style for source_bank_id={source!r}"
            ) from exc
    return requested


def get_visual_style_policy(style_id: str) -> VisualStylePolicy:
    """Return a visual policy, fail-closed on unknown ids."""

    key = (style_id or "").strip()
    try:
        return get_visual_styles()[key]
    except KeyError as exc:
        raise UnknownVisualStyleError(f"unknown visual style id={key!r}") from exc
