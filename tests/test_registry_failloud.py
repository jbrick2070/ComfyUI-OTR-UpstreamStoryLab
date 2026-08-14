"""Registry fail-loud + no-fallback contract."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from upstream_story_lab.registry import Registry, RegistryError, UnknownIdError

ROOT = Path(__file__).resolve().parents[1]


def _copy_fixtures(tmp_path: Path) -> Path:
    root = tmp_path / "lab"
    shutil.copytree(ROOT / "fixtures", root / "fixtures")
    return root


#: The authoritative source-bank roster, mirroring production. Every id, its
#: operator-visible label, and whether the lane can actually be run.
#: custom_source_bank is the add-your-own lane: visible, never runnable until
#: the operator supplies their own schema, packet, and pack.
BANK_ROSTER = {
    "scifi_news": ("Sci-Fi News - Proof-Pressure Radio", True),
    "scifi_news_pro": ("Sci-Fi News Pro (LLM-first multipass)", True),
    "media_archive": ("Media RSS / Archive", True),
    "public_domain": ("Public Domain", True),
    "shakespeare": ("Shakespeare / Folger", True),
    "original": ("Original Radio Drama", True),
    "custom_source_bank": ("+ Add Your Own", False),
}


def test_registry_loads_real_fixtures(registry) -> None:
    assert set(registry.banks) == set(BANK_ROSTER)
    for bank_id, (label, runnable) in BANK_ROSTER.items():
        bank = registry.bank(bank_id)
        assert bank.label == label, bank_id
        assert bank.dropdown_label == label, bank_id
        assert bank.runnable is runnable, bank_id
    # One pack per bank: the bake-off chose a winner per lane.
    assert len(registry.packs) == len(BANK_ROSTER)
    assert set(registry.styles) == {
        "anime", "archival_documentary", "cartoon", "paper_origami", "sci_fi_radio",
    }
    assert set(registry.pipelines) == {"legacy_many_pass", "simple_4_prompt_experimental"}


def test_every_runnable_bank_has_a_source_packet(registry) -> None:
    """A runnable lane that cannot resolve its own packet is a broken lane."""

    for bank_id, (_label, runnable) in BANK_ROSTER.items():
        if not runnable:
            continue
        packet, path = registry.source_packet(bank_id)
        assert packet.source_bank_id == bank_id, path


def test_unknown_ids_raise(registry) -> None:
    with pytest.raises(UnknownIdError):
        registry.bank("mystery_bank")
    with pytest.raises(UnknownIdError):
        registry.pack("media_archive", "space_opera", "legacy_many_pass")
    with pytest.raises(UnknownIdError):
        registry.style("vaporwave")
    with pytest.raises(UnknownIdError):
        registry.pipeline("nine_pass_hyperloop")


def test_missing_fixture_dir_fails_loud(tmp_path) -> None:
    root = _copy_fixtures(tmp_path)
    shutil.rmtree(root / "fixtures" / "visual_styles")
    with pytest.raises(RegistryError, match="visual style folder missing"):
        Registry(root)


def test_missing_style_file_is_not_silently_served(tmp_path) -> None:
    """The v1 silent Python fallback is dead: deleting a style JSON that a
    bank defaults to must fail loudly at load."""

    root = _copy_fixtures(tmp_path)
    (root / "fixtures" / "visual_styles" / "archival_documentary.json").unlink()
    with pytest.raises(RegistryError, match="default_visual_style"):
        Registry(root)


def test_duplicate_pack_key_fails(tmp_path) -> None:
    root = _copy_fixtures(tmp_path)
    src = root / "fixtures" / "story_packs" / "media_archive" / "media_restoration_adventure.json"
    dup = src.with_name("media_restoration_adventure_copy.json")
    dup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate story pack key"):
        Registry(root)


def test_undeclared_template_variable_fails_at_load(tmp_path) -> None:
    root = _copy_fixtures(tmp_path)
    path = root / "fixtures" / "story_packs" / "media_archive" / "media_restoration_adventure.json"
    pack = json.loads(path.read_text(encoding="utf-8"))
    pack["prompt_stages"]["line_grounding"] = "Ground this in {sourec_label}."
    path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(RegistryError, match="undeclared variables"):
        Registry(root)


def test_motion_prompt_dead_role_rejected(tmp_path) -> None:
    root = _copy_fixtures(tmp_path)
    path = root / "fixtures" / "visual_styles" / "archival_documentary.json"
    style = json.loads(path.read_text(encoding="utf-8"))
    style["motion_prompts"]["scene_broll"] = "slow move through an archive"
    path.write_text(json.dumps(style), encoding="utf-8")
    with pytest.raises(Exception, match="scene_broll"):
        Registry(root)


def test_custom_source_bank_not_runnable(registry) -> None:
    with pytest.raises(RegistryError, match="not\\s+runnable"):
        registry.source_packet("custom_source_bank")


def test_pd_manifests_validate_and_paths_are_safe(registry) -> None:
    manifests = registry.public_domain_manifests()
    assert len(manifests) == 3
    for manifest, _path in manifests:
        assert manifest.rights_status == "public_domain"


def test_pd_unsafe_path_rejected(tmp_path) -> None:
    root = _copy_fixtures(tmp_path)
    path = root / "fixtures" / "public_domain_sources" / "book_chapter_sample" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["text_files"] = ["../escape.txt"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RegistryError, match="unsafe path"):
        Registry(root).public_domain_manifests()
