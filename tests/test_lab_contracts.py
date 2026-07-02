from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from upstream_story_lab.catalogs import get_visual_style_ids
from upstream_story_lab.contracts import LedgerWritingSpec, SourceMaterialPacket
from upstream_story_lab.preview import build_spec_from_material


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_domain_spec_builds_with_pipeline_id() -> None:
    packet = SourceMaterialPacket(
        **_load_json(ROOT / "fixtures" / "source_packets" / "public_domain_book_chapter.json")
    )
    spec = build_spec_from_material(
        packet,
        story_model_id="faithful_radio_adaptation",
        story_pipeline_id="legacy_many_pass",
        visual_style_id="archival_documentary",
    )
    assert spec.source_bank_id == "public_domain_story"
    assert spec.story_model_id == "faithful_radio_adaptation"
    assert spec.story_pipeline_id == "legacy_many_pass"
    assert spec.visual_style_id == "archival_documentary"


def test_visual_style_fixtures_are_registered() -> None:
    fixture_ids = {
        _load_json(path)["style_id"]
        for path in (ROOT / "fixtures" / "visual_styles").glob("*.json")
    }
    assert fixture_ids
    assert fixture_ids.issubset(set(get_visual_style_ids()))


def test_ledger_spec_rejects_mismatched_visual_policy() -> None:
    packet = SourceMaterialPacket(
        **_load_json(ROOT / "fixtures" / "source_packets" / "science_news_baseline.json")
    )
    spec = build_spec_from_material(packet)
    data = spec.model_dump(mode="json")
    data["visual_style_id"] = "archival_documentary"
    with pytest.raises(ValueError, match="visual_policy.style_id"):
        LedgerWritingSpec(**data)


def test_ledger_spec_rejects_mismatched_story_ids() -> None:
    packet = SourceMaterialPacket(
        **_load_json(ROOT / "fixtures" / "source_packets" / "public_domain_book_chapter.json")
    )
    spec = build_spec_from_material(packet, story_model_id="faithful_radio_adaptation")
    data = spec.model_dump(mode="json")
    data["story_model_id"] = "chapter_digest_drama"
    with pytest.raises(ValueError, match="story_input.story_model_id"):
        LedgerWritingSpec(**data)


def test_custom_source_bank_preview_fails_loudly() -> None:
    spec = importlib.util.spec_from_file_location("story_lab_nodes", ROOT / "nodes.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["story_lab_nodes"] = module
    spec.loader.exec_module(module)
    previewer = module.OTR_StoryPackPreview()

    with pytest.raises(RuntimeError, match="custom_source_bank is visible but not runnable"):
        previewer.preview(
            "custom_source_bank",
            "simple_4_prompt_experimental",
            "simple_4_prompt_experimental",
            "custom_source_bank / simple_4_prompt_experimental / simple_4_prompt_experimental",
            "anime",
        )
