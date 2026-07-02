"""Live ComfyUI nodes for the OTR upstream story lab.

These nodes expose the isolated lab as a visible custom node package without
touching the production OldTimeRadio workflow. Unknown source/story/style
choices raise hard errors; there are no hidden compatibility fallbacks here.
"""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

LAB_ROOT = Path(__file__).resolve().parent
LAB_SRC = LAB_ROOT / "src"
FIXTURES = LAB_ROOT / "fixtures"
PACK_DIR = FIXTURES / "story_packs"
SOURCE_PACKET_DIR = FIXTURES / "source_packets"
VISUAL_STYLE_DIR = FIXTURES / "visual_styles"
_STORY_PACK_CHOICE_MAP_CACHE: tuple[str, dict[str, Path]] | None = None

SOURCE_BANK_CHOICES = [
    "science_news",
    "media_archive",
    "public_domain_story",
    "custom_source_bank",
]
STORY_PIPELINE_CHOICES = [
    "legacy_many_pass",
    "simple_4_prompt_experimental",
]


def _ensure_lab_importable() -> None:
    if not LAB_SRC.exists():
        raise RuntimeError(f"Upstream Story Lab source folder missing: {LAB_SRC}")
    lab_src = str(LAB_SRC)
    if lab_src not in sys.path:
        sys.path.insert(0, lab_src)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required Upstream Story Lab fixture is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _story_pack_paths() -> list[Path]:
    if not PACK_DIR.exists():
        raise RuntimeError(f"Story pack fixture folder missing: {PACK_DIR}")
    return sorted(PACK_DIR.rglob("*.json"))


def _story_pack_choice_map() -> dict[str, Path]:
    global _STORY_PACK_CHOICE_MAP_CACHE
    stamp = _lab_state_digest()
    if _STORY_PACK_CHOICE_MAP_CACHE is not None:
        cached_stamp, cached_map = _STORY_PACK_CHOICE_MAP_CACHE
        if cached_stamp == stamp:
            return dict(cached_map)

    choices: dict[str, Path] = {}
    _ensure_lab_importable()
    from upstream_story_lab.contracts import StoryPack

    for path in _story_pack_paths():
        pack = StoryPack(**_load_json(path))
        key = (
            f"{pack.source_bank_id} / {pack.story_model_id} / "
            f"{pack.story_pipeline_id}"
        )
        if key in choices:
            raise RuntimeError(f"Duplicate story pack key {key!r}: {path}")
        choices[key] = path
    if not choices:
        raise RuntimeError(f"No story pack fixtures found under {PACK_DIR}")
    _STORY_PACK_CHOICE_MAP_CACHE = (stamp, dict(choices))
    return choices


def _story_model_choices() -> list[str]:
    _ensure_lab_importable()
    from upstream_story_lab.contracts import StoryPack

    models = set()
    for path in _story_pack_paths():
        pack = StoryPack(**_load_json(path))
        if pack.status == "experimental":
            continue
        models.add(pack.story_model_id)
    return sorted(models)


def _visual_style_choices() -> list[str]:
    _ensure_lab_importable()
    from upstream_story_lab.catalogs import get_visual_style_ids

    return get_visual_style_ids()


def _state_files() -> list[Path]:
    paths: list[Path] = [LAB_ROOT / "__init__.py", LAB_ROOT / "nodes.py"]
    for folder in (LAB_ROOT / "src", FIXTURES):
        if folder.exists():
            paths.extend(
                p for p in folder.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix != ".pyc"
            )
    return sorted(paths)


def _lab_state_digest() -> str:
    digest = hashlib.sha256()
    for path in _state_files():
        try:
            rel = path.relative_to(LAB_ROOT).as_posix()
            stat = path.stat()
            digest.update(rel.encode("utf-8"))
            digest.update(str(stat.st_size).encode("utf-8"))
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        except OSError as exc:
            digest.update(f"{path}:ERROR:{exc}".encode("utf-8"))
    return digest.hexdigest()


def _default_story_pack_choice() -> str:
    for choice in _story_pack_choice_map():
        if "media_archive / media_restoration_adventure /" in choice:
            return choice
    return next(iter(_story_pack_choice_map()))


def _find_source_packet(source_bank_id: str) -> dict[str, Any] | None:
    if source_bank_id == "science_news":
        return _load_json(SOURCE_PACKET_DIR / "science_news_baseline.json")
    if source_bank_id == "media_archive":
        return _load_json(SOURCE_PACKET_DIR / "media_archive_restoration_adventure.json")
    if source_bank_id == "public_domain_story":
        return _load_json(SOURCE_PACKET_DIR / "public_domain_book_chapter.json")
    raise RuntimeError(f"No source packet registered for source_bank_id={source_bank_id!r}")


def _validate_public_domain_manifests() -> int:
    _ensure_lab_importable()
    from upstream_story_lab.contracts import PublicDomainSourceManifest

    root = FIXTURES / "public_domain_sources"
    count = 0
    for path in sorted(root.glob("*/manifest.json")):
        manifest = PublicDomainSourceManifest(**_load_json(path))
        base = path.parent
        for rel in manifest.text_files + manifest.image_files:
            rel_path = Path(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                raise RuntimeError(
                    f"Public-domain manifest {path} uses unsafe relative path {rel!r}"
                )
            if not (base / rel_path).exists():
                raise RuntimeError(
                    f"Public-domain manifest {path} references missing file {rel!r}"
                )
        count += 1
    if count == 0:
        raise RuntimeError(f"No public-domain manifests found under {root}")
    return count


def _validate_story_packs() -> list[Any]:
    _ensure_lab_importable()
    from upstream_story_lab.catalogs import get_story_model
    from upstream_story_lab.contracts import StoryPack

    packs = []
    seen = set()
    for path in _story_pack_paths():
        pack = StoryPack(**_load_json(path))
        key = (pack.source_bank_id, pack.story_model_id, pack.story_pipeline_id)
        if key in seen:
            raise RuntimeError(f"Duplicate story pack key: {key!r}")
        seen.add(key)
        if pack.source_bank_id != "custom_source_bank":
            get_story_model(pack.source_bank_id, pack.story_model_id)
        stage_text = "\n".join(pack.prompt_stages.values()).lower()
        if pack.source_bank_id != "science_news":
            leaked = [
                term for term in pack.forbidden_leakage_terms
                if term.lower() in stage_text
            ]
            if leaked:
                raise RuntimeError(
                    f"{pack.story_model_id} prompt stages leaked forbidden terms: {leaked}"
                )
        packs.append(pack)
    return packs


class OTR_UpstreamStoryLabValidator:
    """Validate the fixture-first upstream story architecture."""

    CATEGORY = "OTR/Upstream Story Lab"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report",)
    FUNCTION = "validate"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, dict[str, Any]]:
        return {"required": {}}

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> str:
        return _lab_state_digest()

    def validate(self) -> tuple[str]:
        _ensure_lab_importable()
        from upstream_story_lab.contracts import SourceMaterialPacket, VisualStylePolicy
        from upstream_story_lab.preview import (
            build_legacy_news_mirror,
            build_spec_from_material,
            find_forbidden_media_archive_terms,
            render_prompt_preview,
        )

        science = SourceMaterialPacket(
            **_load_json(SOURCE_PACKET_DIR / "science_news_baseline.json")
        )
        archive = SourceMaterialPacket(
            **_load_json(SOURCE_PACKET_DIR / "media_archive_restoration_adventure.json")
        )
        public_domain = SourceMaterialPacket(
            **_load_json(SOURCE_PACKET_DIR / "public_domain_book_chapter.json")
        )
        VisualStylePolicy(**_load_json(VISUAL_STYLE_DIR / "archival_documentary.json"))

        science_spec = build_spec_from_material(science)
        archive_spec = build_spec_from_material(
            archive,
            story_model_id="media_restoration_adventure",
            visual_style_id="archival_documentary",
        )
        public_domain_spec = build_spec_from_material(
            public_domain,
            story_model_id="faithful_radio_adaptation",
            visual_style_id="archival_documentary",
        )
        pd_manifest_count = _validate_public_domain_manifests()
        packs = _validate_story_packs()

        preview = render_prompt_preview(archive_spec)
        forbidden = find_forbidden_media_archive_terms(preview)
        if forbidden:
            raise RuntimeError(
                f"Media archive prompt preview leaked forbidden terms: {forbidden}"
            )

        mirror = build_legacy_news_mirror(archive_spec)
        required_mirror_keys = {
            "title",
            "headline",
            "script_brief",
            "news_close_brief",
            "casting_brief",
            "key_terms",
            "link",
            "source_hash",
        }
        missing = sorted(required_mirror_keys.difference(mirror))
        if missing:
            raise RuntimeError(f"Legacy mirror missing keys: {missing}")

        lines = [
            "OK Upstream Story Lab live custom node",
            f"lab_root={LAB_ROOT}",
            f"science story_model={science_spec.story_model_id}",
            f"archive story_model={archive_spec.story_model_id}",
            f"public_domain story_model={public_domain_spec.story_model_id}",
            f"archive visual_style={archive_spec.visual_style_id}",
            f"public_domain_manifests={pd_manifest_count}",
            f"story_packs={len(packs)}",
            "production_workflow=not touched by this lab node",
        ]
        return ("\n".join(lines),)


class OTR_StoryPackPreview:
    """Preview one explicit source/story/pipeline/visual-style selection."""

    CATEGORY = "OTR/Upstream Story Lab"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("preview_json",)
    FUNCTION = "preview"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, dict[str, Any]]:
        pack_choices = list(_story_pack_choice_map())
        return {
            "required": {
                "source_bank_id": (SOURCE_BANK_CHOICES, {"default": "media_archive"}),
                "story_model_id": (
                    _story_model_choices(),
                    {"default": "media_restoration_adventure"},
                ),
                "story_pipeline_id": (
                    STORY_PIPELINE_CHOICES,
                    {"default": "legacy_many_pass"},
                ),
                "story_pack": (pack_choices, {"default": _default_story_pack_choice()}),
                "visual_style_id": (
                    _visual_style_choices(),
                    {"default": "archival_documentary"},
                ),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> str:
        return _lab_state_digest()

    def preview(
        self,
        source_bank_id: str,
        story_model_id: str,
        story_pipeline_id: str,
        story_pack: str,
        visual_style_id: str,
    ) -> tuple[str]:
        _ensure_lab_importable()
        from upstream_story_lab.catalogs import get_profile, get_story_model
        from upstream_story_lab.contracts import SourceMaterialPacket, StoryPack
        from upstream_story_lab.preview import (
            build_spec_from_material,
            render_prompt_preview,
        )

        pack_path = _story_pack_choice_map().get(story_pack)
        if pack_path is None:
            raise RuntimeError(f"Unknown story pack choice: {story_pack!r}")
        pack = StoryPack(**_load_json(pack_path))

        requested_key = (source_bank_id, story_model_id, story_pipeline_id)
        pack_key = (pack.source_bank_id, pack.story_model_id, pack.story_pipeline_id)
        if requested_key != pack_key:
            raise RuntimeError(
                "Selected dropdowns do not match the selected story pack. "
                f"dropdowns={requested_key!r} pack={pack_key!r}"
            )

        result: dict[str, Any] = {
            "status": "ok",
            "lab_root": str(LAB_ROOT),
            "story_pack_path": str(pack_path),
            "selection": {
                "source_bank_id": source_bank_id,
                "story_model_id": story_model_id,
                "story_pipeline_id": story_pipeline_id,
                "visual_style_id": visual_style_id,
            },
            "story_pack": pack.model_dump(mode="json"),
            "notes": [
                "This is a live upstream lab preview only.",
                "It does not edit or run the production OTR workflow JSON.",
                "Invalid source/story/style combinations fail loudly.",
            ],
        }

        if source_bank_id == "custom_source_bank":
            raise RuntimeError(
                "custom_source_bank is visible but not runnable yet. "
                "Create and validate a custom schema, source packet, and story pack first. "
                f"Guide: {LAB_ROOT / 'CUSTOM_SOURCE_BANK_GUIDE.md'}"
            )
        else:
            get_story_model(source_bank_id, story_model_id)
            result["prompt_profile"] = get_profile(
                source_bank_id,
                story_model_id,
            ).model_dump(mode="json")
            material_json = _find_source_packet(source_bank_id)
            material = SourceMaterialPacket(**material_json)
            result["source_packet_note"] = (
                f"{source_bank_id} preview currently uses a shared source-packet "
                "fixture for all story models in this source bank."
            )
            spec = build_spec_from_material(
                material,
                story_model_id=story_model_id,
                story_pipeline_id=story_pipeline_id,
                visual_style_id=visual_style_id,
            )
            result["ledger_writing_spec"] = spec.model_dump(mode="json")
            result["prompt_preview"] = render_prompt_preview(spec)

        return (json.dumps(result, indent=2, ensure_ascii=False),)


NODE_CLASS_MAPPINGS = {
    "OTR_UpstreamStoryLabValidator": OTR_UpstreamStoryLabValidator,
    "OTR_StoryPackPreview": OTR_StoryPackPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OTR_UpstreamStoryLabValidator": "OTR Upstream Story Lab Validator",
    "OTR_StoryPackPreview": "OTR Story Pack Preview",
}
