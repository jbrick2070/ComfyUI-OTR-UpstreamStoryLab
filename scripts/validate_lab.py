"""Validate the isolated upstream story lab fixtures.

This script is intentionally standalone and imports only the lab package.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from upstream_story_lab.catalogs import get_story_model, get_visual_style_ids
from upstream_story_lab.contracts import (
    PublicDomainSourceManifest,
    SourceMaterialPacket,
    StoryPack,
    VisualStylePolicy,
)
from upstream_story_lab.preview import (
    build_legacy_news_mirror,
    build_spec_from_material,
    find_forbidden_media_archive_terms,
    render_prompt_preview,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_story_packs(pack_dir: Path) -> list[StoryPack]:
    packs: list[StoryPack] = []
    for path in sorted(pack_dir.rglob("*.json")):
        packs.append(StoryPack(**_load_json(path)))
    return packs


def _validate_public_domain_manifests(root: Path) -> int:
    count = 0
    for path in sorted(root.glob("*/manifest.json")):
        manifest = PublicDomainSourceManifest(**_load_json(path))
        base = path.parent
        for rel in manifest.text_files + manifest.image_files:
            if not (base / rel).exists():
                raise AssertionError(
                    f"public-domain manifest {path} references missing file {rel!r}"
                )
        count += 1
    if count == 0:
        raise AssertionError("no public-domain source manifests found")
    return count


def main() -> int:
    source_dir = ROOT / "fixtures" / "source_packets"
    visual_dir = ROOT / "fixtures" / "visual_styles"
    pack_dir = ROOT / "fixtures" / "story_packs"

    science = SourceMaterialPacket(
        **_load_json(source_dir / "science_news_baseline.json")
    )
    archive = SourceMaterialPacket(
        **_load_json(source_dir / "media_archive_restoration_adventure.json")
    )
    public_domain = SourceMaterialPacket(
        **_load_json(source_dir / "public_domain_book_chapter.json")
    )
    fixture_style_ids = []
    for path in sorted(visual_dir.glob("*.json")):
        fixture_style_ids.append(VisualStylePolicy(**_load_json(path)).style_id)
    missing_fixture_ids = sorted(set(fixture_style_ids).difference(get_visual_style_ids()))
    if missing_fixture_ids:
        raise AssertionError(
            f"visual style fixtures missing from catalog: {missing_fixture_ids}"
        )

    archive_spec = build_spec_from_material(
        archive,
        story_model_id="media_restoration_adventure",
        visual_style_id="archival_documentary",
    )
    science_spec = build_spec_from_material(science)
    public_domain_spec = build_spec_from_material(
        public_domain,
        story_model_id="faithful_radio_adaptation",
        visual_style_id="archival_documentary",
    )
    packs = _load_story_packs(pack_dir)
    if not packs:
        raise AssertionError("no story packs found")

    seen = set()
    for pack in packs:
        key = (
            pack.source_bank_id,
            pack.story_model_id,
            pack.story_pipeline_id,
        )
        if key in seen:
            raise AssertionError(f"duplicate story pack key: {key!r}")
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
                raise AssertionError(
                    f"{pack.story_model_id} prompt stages leaked {leaked}"
                )

    required_pack_keys = {
        ("science_news", "science_news_default", "legacy_many_pass"),
        ("media_archive", "media_restoration_adventure", "legacy_many_pass"),
        ("media_archive", "cinematic_humorous", "legacy_many_pass"),
        ("media_archive", "happy_archive_mystery", "legacy_many_pass"),
        ("media_archive", "gentle_thriller", "legacy_many_pass"),
        ("media_archive", "broadcast_history_comedy", "legacy_many_pass"),
        ("public_domain_story", "faithful_radio_adaptation", "legacy_many_pass"),
        ("public_domain_story", "chapter_digest_drama", "legacy_many_pass"),
        ("public_domain_story", "comic_panel_radio_adaptation", "legacy_many_pass"),
        ("public_domain_story", "stage_play_radio_adaptation", "legacy_many_pass"),
        ("public_domain_story", "storybook_puppet_show", "legacy_many_pass"),
        ("custom_source_bank", "simple_4_prompt_experimental", "simple_4_prompt_experimental"),
    }
    missing_packs = sorted(required_pack_keys.difference(seen))
    if missing_packs:
        raise AssertionError(f"missing required story packs: {missing_packs!r}")

    preview = render_prompt_preview(archive_spec)
    forbidden = find_forbidden_media_archive_terms(preview)
    if forbidden:
        raise AssertionError(f"media archive prompt leaked forbidden terms: {forbidden}")

    pd_manifest_count = _validate_public_domain_manifests(
        ROOT / "fixtures" / "public_domain_sources"
    )

    mirror = build_legacy_news_mirror(archive_spec)
    required = {
        "title",
        "headline",
        "script_brief",
        "news_close_brief",
        "casting_brief",
        "key_terms",
        "link",
        "source_hash",
    }
    missing = sorted(required.difference(mirror))
    if missing:
        raise AssertionError(f"legacy mirror missing keys: {missing}")

    print("OK upstream_story_lab")
    print(f"science story_model={science_spec.story_model_id}")
    print(f"archive story_model={archive_spec.story_model_id}")
    print(f"public_domain story_model={public_domain_spec.story_model_id}")
    print(f"archive visual_style={archive_spec.visual_style_id}")
    print(f"public_domain_manifests={pd_manifest_count}")
    print(f"story_packs={len(packs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
