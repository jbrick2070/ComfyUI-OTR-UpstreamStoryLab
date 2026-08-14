"""Trusted semantic checks and the complete normative Story Ledger v2."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from upstream_story_lab import (
    CAPTURED_SOURCE_PACKET_SCHEMA_VERSION,
    CapturedSourcePacketArtifact,
    LedgerContractError,
    LedgerEnvelope,
    StoryBody,
    StoryLedger,
    TRUSTED_VALIDATOR_IDENTITIES,
    build_story_seal,
    build_trusted_receipt_verifiers,
    canonical_sha256,
    verify_story_envelope,
)
from upstream_story_lab.ledger_verifiers import TRUSTED_VALIDATOR_VERSIONS
from upstream_story_lab.spoken_text_policy import (
    SPOKEN_TEXT_POLICY_ID,
    audit_spoken_text,
)


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "fixtures" / "story_recovery"
V2 = RECOVERY / "v2"
LEGACY_V1 = RECOVERY / "v1" / "normative_ledger_envelope.json"
NORMATIVE = V2 / "normative_ledger_envelope.json"
PACKET = (
    V2
    / "source_packets"
    / "science_news_folder_red_stamps_20260716.json"
)
CONTROL = RECOVERY / "science_news_good_20260716.json"
CHALLENGER = RECOVERY / "scifi_news_bad_20260813.json"
MACHINE_BIBLE = ROOT / "contracts" / "ledger_bible_v2.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normative_envelope() -> LedgerEnvelope:
    return LedgerEnvelope.model_validate(_json(NORMATIVE))


def _registry(
    envelope: LedgerEnvelope,
    *,
    payload: bytes | None = None,
):
    packet_bytes = PACKET.read_bytes() if payload is None else payload
    packet_sha = envelope.story_ledger.body.source_packet.packet_sha256
    return build_trusted_receipt_verifiers(
        packet_artifacts={packet_sha: packet_bytes}
    )


def _rebound_story(
    mutate: Callable[[dict], None],
) -> StoryLedger:
    raw = _json(NORMATIVE)["story_ledger"]
    mutate(raw)
    body = StoryBody.model_validate(raw["body"])
    raw["body"] = body.model_dump(mode="json")
    raw["validation"]["body_sha256"] = canonical_sha256(body)
    return StoryLedger.model_validate(raw)


def _audit_character_text(text: str):
    return audit_spoken_text(
        [
            {
                "line_id": "probe",
                "char_id": "c01",
                "speaker_role": "character",
                "text": text,
            }
        ],
        [
            {"char_id": "c01", "name": "EDNA"},
            {"char_id": "c02", "name": "PETER"},
        ],
    )


def test_registry_has_exactly_five_immutable_code_owned_identities() -> None:
    envelope = _normative_envelope()
    registry = _registry(envelope)
    expected = {
        (outcome, validator_id, validator_version)
        for outcome, (validator_id, validator_version) in (
            TRUSTED_VALIDATOR_IDENTITIES.items()
        )
    }

    assert set(registry) == expected
    assert len(registry) == 5
    with pytest.raises(TypeError):
        registry[next(iter(registry))] = lambda _body, _receipt: True  # type: ignore[index]


def test_machine_bible_locks_validator_identities_and_policies() -> None:
    bible = _json(MACHINE_BIBLE)
    contract = bible["trusted_semantic_validators"]

    assert bible["versions"]["captured_source_packet"] == (
        CAPTURED_SOURCE_PACKET_SCHEMA_VERSION
    )
    assert contract["captured_packet_schema"] == (
        CAPTURED_SOURCE_PACKET_SCHEMA_VERSION
    )
    assert contract["validator_versions"] == dict(TRUSTED_VALIDATOR_VERSIONS)
    assert contract["identities"] == {
        outcome: validator_id
        for outcome, (validator_id, _version) in (
            TRUSTED_VALIDATOR_IDENTITIES.items()
        )
    }
    assert set(contract["policies"]) == set(TRUSTED_VALIDATOR_IDENTITIES)
    assert contract["spoken_text_policy"]["policy_id"] == SPOKEN_TEXT_POLICY_ID
    assert contract["network_or_llm_calls"] == "forbidden"


def test_normative_packet_digest_binds_exact_external_bytes() -> None:
    envelope = _normative_envelope()
    packet_bytes = PACKET.read_bytes()
    captured = CapturedSourcePacketArtifact.model_validate_json(packet_bytes)
    projected = envelope.story_ledger.body.source_packet

    assert hashlib.sha256(packet_bytes).hexdigest() == projected.packet_sha256
    assert captured.packet_id == projected.packet_id
    assert captured.source_bank_id == projected.source_bank_id
    assert captured.sources == projected.sources
    assert captured.facts == projected.facts


def test_normative_fixture_passes_all_five_and_recomputes_exact_seal() -> None:
    envelope = _normative_envelope()
    registry = _registry(envelope)

    admitted = verify_story_envelope(
        envelope,
        receipt_verifiers=registry,
    )
    rebuilt = build_story_seal(
        envelope.story_ledger,
        sealed_at=envelope.story_seal.sealed_at,
        receipt_verifiers=registry,
    )

    assert admitted == envelope
    assert rebuilt == envelope.story_seal
    assert envelope.production_state is None
    assert envelope.final_seal is None
    assert [row.sequence_role for row in envelope.story_ledger.body.sequence] == [
        "music_open",
        "announcer_open",
        "character_dialogue",
        "character_dialogue",
        "music_inter",
        "character_dialogue",
        "announcer_news_coda",
        "music_close",
    ]


def test_v1_fixture_is_preserved_but_never_silently_promoted_to_v2() -> None:
    legacy_bytes = LEGACY_V1.read_bytes()

    assert hashlib.sha256(legacy_bytes).hexdigest() == (
        "afc723d8a854450a7b848f1132a350dbb947aac97eae988e14a053341c40fa82"
    )
    with pytest.raises(ValidationError, match="otr.ledger_envelope.v2"):
        LedgerEnvelope.model_validate_json(legacy_bytes)


def test_packet_byte_change_fails_news_capture_verification() -> None:
    envelope = _normative_envelope()
    tampered = PACKET.read_bytes() + b" "

    with pytest.raises(
        LedgerContractError,
        match="news_capture.*failed trusted",
    ):
        build_story_seal(
            envelope.story_ledger,
            sealed_at=envelope.story_seal.sealed_at,
            receipt_verifiers=_registry(envelope, payload=tampered),
        )


def test_packet_projection_change_fails_even_when_new_bytes_match_new_digest() -> None:
    changed_packet = _json(PACKET)
    changed_packet["facts"][0]["claim"] = "A substituted claim."
    changed_bytes = json.dumps(changed_packet, ensure_ascii=False).encode("utf-8")
    changed_sha = hashlib.sha256(changed_bytes).hexdigest()

    story = _rebound_story(
        lambda raw: raw["body"]["source_packet"].__setitem__(
            "packet_sha256",
            changed_sha,
        )
    )
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={changed_sha: changed_bytes}
    )

    with pytest.raises(
        LedgerContractError,
        match="news_capture.*failed trusted",
    ):
        build_story_seal(
            story,
            sealed_at=_normative_envelope().story_seal.sealed_at,
            receipt_verifiers=registry,
        )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Folder of Red Stamps", "Tonight's unnamed story"),
        ("Signal Lost studios", "the studio"),
        ("ten:zero PM", "late tonight"),
        ("Oya Reeves", "one researcher"),
        ("Ed Steele", "her colleague"),
    ],
)
def test_opening_names_story_scene_time_and_final_speaking_cast(
    old: str,
    new: str,
) -> None:
    def mutate(raw: dict) -> None:
        text = raw["body"]["lines"][0]["text"]
        assert old.casefold() in text.casefold()
        start = text.casefold().index(old.casefold())
        raw["body"]["lines"][0]["text"] = (
            text[:start] + new + text[start + len(old) :]
        )

    story = _rebound_story(mutate)
    envelope = _normative_envelope()

    with pytest.raises(
        LedgerContractError,
        match="announcer_open.*failed trusted",
    ):
        build_story_seal(
            story,
            sealed_at=envelope.story_seal.sealed_at,
            receipt_verifiers=_registry(envelope),
        )


def test_coda_fact_id_without_literal_claim_is_not_semantic_evidence() -> None:
    story = _rebound_story(
        lambda raw: raw["body"]["lines"][4].__setitem__(
            "text",
            "Beyond tonight's drama, the real report remains important.",
        )
    )
    envelope = _normative_envelope()

    with pytest.raises(
        LedgerContractError,
        match="announcer_news_coda.*failed trusted",
    ):
        build_story_seal(
            story,
            sealed_at=envelope.story_seal.sealed_at,
            receipt_verifiers=_registry(envelope),
        )


def test_normative_fixture_uses_control_evidence_without_promoting_legacy() -> None:
    control_bytes = CONTROL.read_bytes()
    control = json.loads(control_bytes)
    packet = CapturedSourcePacketArtifact.model_validate_json(PACKET.read_bytes())
    envelope = _normative_envelope()
    body = envelope.story_ledger.body

    assert packet.sources[0].content_sha256 == hashlib.sha256(
        control_bytes
    ).hexdigest()
    assert packet.source_bank_id == control["provenance"]["source_bank"]
    assert packet.sources[0].title == control["artifacts"]["news_seed"]["headline"]
    assert packet.facts[0].claim == control["artifacts"]["news"]["script_brief"]
    assert packet.facts[1].claim == control["artifacts"]["news"]["news_close_brief"]
    assert body.lines[0].text != control["artifacts"]["lines"][0]["text"]
    assert body.context.episode_title in body.lines[0].text
    assert all(
        row.name.casefold() in body.lines[0].text.casefold()
        for row in body.cast
        if row.cast_role == "character"
    )
    assert body.lines[-1].text == control["artifacts"]["lines"][-1]["text"]
    assert control["expected"]["presentation_topology_pass"] == "not_evaluated"

    with pytest.raises(ValidationError):
        LedgerEnvelope.model_validate(control)


def test_challenger_remains_rejection_calibration_not_a_v2_candidate() -> None:
    challenger = _json(CHALLENGER)
    lines = challenger["artifacts"]["p5"]["compiled"]["lines"]
    findings = set(challenger["expected"]["finding_codes"])

    assert lines[0]["speaker_role"] == "character"
    assert lines[-1]["speaker_role"] == "character"
    assert {
        "ANNOUNCER_OPEN_MISSING",
        "ANNOUNCER_CODA_MISSING",
        "FACTUAL_CODA_MISSING",
    } <= findings
    with pytest.raises(ValidationError):
        StoryBody.model_validate(challenger["artifacts"]["p5"]["compiled"])


def test_challenger_proves_both_independent_story_failures() -> None:
    challenger = _json(CHALLENGER)
    compiled = challenger["artifacts"]["p5"]["compiled"]
    cast = challenger["authorities"]["cast_plan"]["cast"]
    expected = challenger["expected"]
    findings = audit_spoken_text(compiled["lines"], cast)

    assert {
        "ANNOUNCER_OPEN_MISSING",
        "ANNOUNCER_CODA_MISSING",
        "FACTUAL_CODA_MISSING",
    } <= set(expected["finding_codes"])
    assert compiled["lines"][0]["speaker_role"] == "character"
    assert compiled["lines"][-1]["speaker_role"] == "character"

    narration_or_stage_line_ids = {
        finding.line_id
        for finding in findings
        if finding.code != "cross_speaker_attribution"
    }
    cross_speaker_line_ids = {
        finding.line_id
        for finding in findings
        if finding.code == "cross_speaker_attribution"
    }
    assert narration_or_stage_line_ids == set(
        expected["narration_or_stage_line_ids"]
    )
    assert cross_speaker_line_ids == set(expected["cross_speaker_line_ids"])
    assert {finding.line_id for finding in findings} == (
        narration_or_stage_line_ids | cross_speaker_line_ids
    )


def test_integrity_v3_rejects_novel_prose_after_all_hashes_are_rebound() -> None:
    story = _rebound_story(
        lambda raw: raw["body"]["lines"][1].__setitem__(
            "text",
            "Oya turns to Ed. 'The smoke is already here.' Her voice trembles.",
        )
    )
    envelope = _normative_envelope()

    with pytest.raises(
        LedgerContractError,
        match="ledger_integrity.*failed trusted",
    ):
        build_story_seal(
            story,
            sealed_at=envelope.story_seal.sealed_at,
            receipt_verifiers=_registry(envelope),
        )


def test_normative_story_is_clean_spoken_text() -> None:
    body = _normative_envelope().story_ledger.body

    assert audit_spoken_text(body.lines, body.cast) == ()


def test_historical_control_is_clean_spoken_text() -> None:
    control = _json(CONTROL)["artifacts"]

    assert audit_spoken_text(control["lines"], control["cast"]) == ()


@pytest.mark.parametrize(
    "text",
    [
        "She says the code is wrong.",
        "Peter says the code is wrong.",
        'They called it "safe," but I saw the smoke.',
        "the code’s not just numbers—it’s a map of who’ll breathe it in.",
        "I heard the door slam.",
        "Looks like rain, Watson.",
    ],
)
def test_legitimate_spoken_surfaces_do_not_trip_narrow_policy(text: str) -> None:
    assert _audit_character_text(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "Door slams.",
        "Music swells.",
        "The telephone rings.",
        "Footsteps approach.",
        "snaps off the cap, cracks the seal, drains the vial",
    ],
)
def test_whole_line_stage_business_is_rejected(text: str) -> None:
    findings = _audit_character_text(text)

    assert {finding.code for finding in findings} == {
        "third_person_stage_business"
    }


def test_packet_registry_snapshots_mutable_bytes() -> None:
    envelope = _normative_envelope()
    mutable = bytearray(PACKET.read_bytes())
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={
            envelope.story_ledger.body.source_packet.packet_sha256: mutable
        }
    )
    mutable[-1] ^= 1

    verify_story_envelope(envelope, receipt_verifiers=registry)


def test_fixture_copy_is_not_needed_for_admission() -> None:
    """Guard against validators mutating a caller-owned golden object."""

    envelope = _normative_envelope()
    before = copy.deepcopy(envelope.model_dump(mode="json"))

    verify_story_envelope(envelope, receipt_verifiers=_registry(envelope))

    assert envelope.model_dump(mode="json") == before
