"""Integrity and ground-truth checks for the 2026-08-13 recovery cases.

These tests deliberately use only checked-in fixtures.  They do not read the
operator's output tree, import the stale production mirror, call an LLM, or
touch a GPU.  Their job is to keep the problem statement tied to immutable
evidence while the replacement story design is explored.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "fixtures" / "story_recovery"


def _load(name: str) -> dict[str, Any]:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bad_objects(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "cast_plan": case["authorities"]["cast_plan"],
        "fact_index": case["authorities"]["fact_index"],
        "p3_compiled": case["artifacts"]["p3"]["compiled"],
        "p5_compiled": case["artifacts"]["p5"]["compiled"],
        "p3_request_receipt": case["request_receipts"][
            "radio_score_draft_surface"
        ],
        "p5_request_receipt": case["request_receipts"]["script_transport"],
        "word_budget_telemetry": case["artifacts"]["word_budget_telemetry"],
        "render_result": case["render_receipt"]["result"],
    }


@pytest.mark.parametrize(
    ("fixture_name", "expected_ledger_sha"),
    [
        (
            "science_news_good_20260716.json",
            "ad5285a08a88d7682ad707baf44dea2e8c094b9c08e153f466a7233d8af2ee8f",
        ),
        (
            "scifi_news_bad_20260813.json",
            "a1146b22dcf0e122348e901070969089c5bfc92604f7b41395dca092212546fe",
        ),
    ],
)
def test_cases_pin_the_exact_source_ledgers(
    fixture_name: str,
    expected_ledger_sha: str,
) -> None:
    case = _load(fixture_name)
    assert case["schema_version"] == "otr_story_recovery_case.v1"
    assert case["provenance"]["source_ledger_sha256"] == expected_ledger_sha
    assert not case["provenance"]["source_ledger_path_hint"].startswith("C:")


def test_good_case_projection_is_hash_pinned() -> None:
    case = _load("science_news_good_20260716.json")
    objects = case["artifacts"]
    assert {
        name: _canonical_sha256(value)
        for name, value in objects.items()
    } == case["object_sha256"]
    assert _canonical_sha256(objects) == case["projection_sha256"]
    assert case["projection_sha256"] == (
        "f39af1b39ce58083628d78ed63ce2a4055be639d52f67c9218ca6a0e7f42cb45"
    )


def test_bad_case_projection_is_hash_pinned() -> None:
    case = _load("scifi_news_bad_20260813.json")
    objects = _bad_objects(case)
    assert {
        name: _canonical_sha256(value)
        for name, value in objects.items()
    } == case["object_sha256"]
    assert _canonical_sha256(objects) == case["projection_sha256"]
    assert case["projection_sha256"] == (
        "ac3aeb3899e91e518afad874ccf3ccbba1d42cc1300caf2d7b0ebf156a98e29a"
    )


def test_one_byte_semantic_mutation_breaks_the_pin() -> None:
    case = _load("science_news_good_20260716.json")
    changed = copy.deepcopy(case["artifacts"]["lines"])
    changed[0]["text"] += "x"
    assert _canonical_sha256(changed) != case["object_sha256"]["lines"]


def test_legacy_control_preserves_the_news_story_shape() -> None:
    case = _load("science_news_good_20260716.json")
    lines = case["artifacts"]["lines"]
    news = case["artifacts"]["news"]

    assert case["arm"] == "control"
    assert case["provenance"]["source_bank"] == "science_news"
    assert lines[0]["speaker_role"] == "announcer"
    assert lines[-1]["speaker_role"] == "announcer"
    assert all(line["speaker_role"] == "character" for line in lines[1:-1])
    assert "ten:zero PM" in lines[0]["text"]
    assert "Signal Lost studios" in lines[0]["text"]
    assert news["news_close_brief"].casefold() in lines[-1]["text"].casefold()
    assert case["expected"]["story_content_pass"] is True
    assert case["expected"]["presentation_topology_pass"] == "not_evaluated"
    assert case["capabilities"]["music_topology"] is False


def test_legacy_control_keeps_words_as_telemetry_only() -> None:
    receipt = _load("science_news_good_20260716.json")["render_receipt"]
    assert receipt["render_pass"] is True
    assert receipt["spoken_word_count_telemetry"] == 105
    assert receipt["audio_duration_seconds"] == pytest.approx(54.7177, abs=0.0001)


def test_challenger_proves_render_pass_content_fail_split() -> None:
    case = _load("scifi_news_bad_20260813.json")
    render = case["render_receipt"]

    assert case["arm"] == "challenger"
    assert render["render_pass"] is True
    assert render["result"][0]["ok"] is True
    assert render["result"][0]["engine"] == "wan_ti2v"
    assert render["published_asset_bytes"] == 158_445_244
    assert case["expected"]["story_content_pass"] is False
    assert case["expected"]["presentation_topology_pass"] is False


def test_challenger_pins_word_count_as_telemetry_not_authority() -> None:
    telemetry = _load("scifi_news_bad_20260813.json")["artifacts"][
        "word_budget_telemetry"
    ]

    assert telemetry["target_words"] == 45
    assert telemetry["actual_character_words"] == 331
    assert telemetry["actual_announcer_words"] == 26
    assert telemetry["actual_total_voiced_words"] == 357
    assert telemetry["policy"] == "requested_context_actual_count_only"


def test_challenger_lacks_announcer_bookends_and_factual_coda() -> None:
    case = _load("scifi_news_bad_20260813.json")
    score = case["artifacts"]["p3"]["compiled"]
    lines = case["artifacts"]["p5"]["compiled"]["lines"]
    beats = [beat for scene in score["scenes"] for beat in scene["beats"]]

    assert beats[0]["speaker_role"] == "character"
    assert beats[-1]["speaker_role"] == "character"
    assert [beat["beat_id"] for beat in beats if beat["speaker_role"] == "announcer"] == [
        "b001"
    ]
    assert lines[0]["speaker_role"] == "character"
    assert lines[-1]["speaker_role"] == "character"
    assert [line["line_id"] for line in lines if line["speaker_role"] == "announcer"] == [
        "l003"
    ]
    assert lines[-1]["fact_ids"] == []

    findings = set(case["expected"]["finding_codes"])
    assert {
        "ANNOUNCER_OPEN_MISSING",
        "ANNOUNCER_CODA_MISSING",
        "ANNOUNCER_INTERIOR_ONLY",
        "FACTUAL_CODA_MISSING",
    } <= findings


def test_challenger_music_bookends_anchor_to_character_rows() -> None:
    case = _load("scifi_news_bad_20260813.json")
    score = case["artifacts"]["p3"]["compiled"]
    lines = {
        line["line_id"]: line
        for line in case["artifacts"]["p5"]["compiled"]["lines"]
    }
    cues = {cue["cue_id"]: cue for cue in score["music_cues"]}

    assert lines[cues["music_open"]["anchor_line_id"]]["speaker_role"] == "character"
    assert lines[cues["music_close"]["anchor_line_id"]]["speaker_role"] == "character"


def test_challenger_preserves_exact_spoken_ownership_failures() -> None:
    case = _load("scifi_news_bad_20260813.json")
    lines = {
        line["line_id"]: line
        for line in case["artifacts"]["p5"]["compiled"]["lines"]
    }

    assert lines["l002"]["char_id"] == "c01"
    assert lines["l002"]["text"].startswith("Ada's fingers drum")
    assert lines["l005"]["char_id"] == "c01"
    assert lines["l005"]["text"].startswith("Leo's face clouds")
    assert lines["l006"]["char_id"] == "c02"
    assert "Ada whispers" in lines["l006"]["text"]
    assert lines["l011"]["char_id"] == "c03"
    assert lines["l011"]["text"].startswith("Ada leaves the room")
    assert all("speaker" not in line for line in lines.values())
    assert case["expected"]["narration_or_stage_line_ids"] == [
        "l001",
        "l002",
        "l004",
        "l005",
        "l007",
        "l008",
        "l009",
        "l010",
        "l011",
    ]
    assert case["expected"]["cross_speaker_line_ids"] == ["l005", "l006", "l011"]


def test_raw_transport_and_legacy_music_are_explicitly_unavailable() -> None:
    good = _load("science_news_good_20260716.json")
    bad = _load("scifi_news_bad_20260813.json")

    assert good["capabilities"]["raw_transport"] is False
    assert good["capabilities"]["music_topology"] is False
    assert bad["capabilities"]["raw_transport"] is False
    assert bad["capabilities"]["music_topology"] is True
    assert any("not evaluated" in note.lower() for note in good["evidence_limits"])
    assert any("not persisted" in note.lower() for note in bad["evidence_limits"])


def test_machine_readable_contract_locks_only_the_operator_requirements() -> None:
    contract = _load("ledger_requirements_v1.json")

    assert contract["schema_version"] == "otr_story_lab.ledger_requirements.v1"
    assert contract["artifact_boundary"]["output"] == (
        "validated_ledger_envelope_json"
    )
    assert contract["artifact_boundary"]["ledger_only"] is True
    assert set(contract["minimum_ship_contract"]) == {
        "ledger_integrity",
        "news_capture",
        "announcer_open",
        "announcer_news_coda",
        "music_bookends",
    }
    assert all(
        requirement["required"] is True
        for requirement in contract["minimum_ship_contract"].values()
    )
    assert contract["row_contract"]["allowed_sequence_roles"] == [
        "music_open",
        "announcer_open",
        "character_dialogue",
        "music_inter",
        "announcer_news_coda",
        "music_close",
    ]
    assert contract["row_contract"][
        "music_inter_is_optional_and_script_requested"
    ] is True
    assert set(contract["row_contract"]["forbidden_spoken_content"]) == {
        "action",
        "stage_direction",
        "third_person_narration",
        "delivery_note",
    }
    assert contract["freeze_semantics"] == {
        "draft_mutation_allowed_before_validation": True,
        "freeze_requires_full_contract_validation": True,
        "freeze_is_atomic": True,
        "story_ledger_requires_canonical_sha256": True,
        "story_seal_requires_trusted_receipt_registry": True,
        "story_ledger_post_acceptance_mutation": "forbidden",
        "production_state_post_acceptance_mutation": "phase_owned_append_only",
        "current_executable_non_null_production_or_final_plane": (
            "rejected_until_strict_schemas_land"
        ),
        "final_seal_after": "publication_and_audit",
        "post_final_seal_mutation": "forbidden",
        "contract_change": "new_schema_version_and_explicit_migration",
        "current_l4_cleanup_locked_is_not_enforcement": True,
    }
    assert contract["episode_length_tier"]["values_in_ui_order"] == [
        "ultra_short",
        "medium",
        "long",
        "extra_long",
    ]
    assert contract["episode_length_tier"]["words_are_telemetry_only"] is True
    assert contract["episode_length_tier"][
        "model_receives_resolved_chunk_not_length_label"
    ] is True
    assert "movement_count_per_tier" in contract["explicitly_experimental"]
    assert "approximate_minutes_per_tier" in contract["explicitly_experimental"]
