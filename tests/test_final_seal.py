"""Terminal final-seal ordering, digest, trust, and immutability laws."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from upstream_story_lab import (
    FINAL_SEAL_SCHEMA_VERSION,
    AcceptanceEvent,
    ArtifactRef,
    DependencyRef,
    LedgerContractError,
    LedgerEnvelope,
    PhaseAcceptance,
    RunPhase,
    accept_production_attempt,
    append_production_attempt,
    assert_production_append_only,
    build_trusted_receipt_verifiers,
    canonical_sha256,
    initialize_production_state,
    mint_final_seal,
    production_sha256,
    verify_final_seal,
)
from upstream_story_lab.production_contract import (
    PRODUCTION_PHASE_REGISTRY,
    AuditAttempt,
    PublicationAttempt,
)


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "fixtures" / "story_recovery" / "v2"
NORMATIVE = V2 / "normative_ledger_envelope.json"
PACKET = V2 / "source_packets" / "science_news_folder_red_stamps_20260716.json"
T0 = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
RUN_ID = "run.final-seal-001"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normative() -> LedgerEnvelope:
    return LedgerEnvelope.model_validate(_json(NORMATIVE))


def _trusted_registry(envelope: LedgerEnvelope):
    packet_sha = envelope.story_ledger.body.source_packet.packet_sha256
    return build_trusted_receipt_verifiers(
        packet_artifacts={packet_sha: PACKET.read_bytes()}
    )


def _terminal_plan(
    *,
    required_extra: str | None = None,
    optional_extra: str | None = "workspace_identity",
) -> list[RunPhase]:
    rows = []
    for phase_id, owner in PRODUCTION_PHASE_REGISTRY:
        if phase_id in {"publication", "audit", required_extra}:
            disposition = "required"
            omission_reason = None
        elif phase_id == optional_extra:
            disposition = "optional"
            omission_reason = None
        else:
            disposition = "omitted"
            omission_reason = "This terminal-contract route does not execute the phase."
        rows.append(
            RunPhase(
                phase_id=phase_id,
                owner=owner,
                disposition=disposition,
                omission_reason=omission_reason,
                depends_on=["publication"] if phase_id == "audit" else [],
            )
        )
    return rows


def _producer(component_id: str) -> dict:
    return {
        "component_id": component_id,
        "component_version": "1.0.0",
        "source_revision": "final-seal-test",
        "config_sha256": "c" * 64,
    }


def _artifact(
    artifact_id: str,
    artifact_kind: str,
    content_sha256: str,
) -> dict:
    extension = "json" if artifact_kind in {"obs_scene_collection", "audit_report"} else "bin"
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "media_type": "application/octet-stream",
        "storage_root_id": "episode-root",
        "relative_path": f"runs/final-seal/{artifact_id}.{extension}",
        "content_sha256": content_sha256,
        "size_bytes": 100,
        "durability": "published",
    }


def _publication_attempt(
    envelope: LedgerEnvelope,
    *,
    attempt_number: int = 1,
) -> PublicationAttempt:
    state = envelope.production_state
    assert state is not None
    suffix = str(attempt_number)
    ids = {
        "master": f"artifact.master-audio.{suffix}",
        "terminal": f"artifact.terminal-video.{suffix}",
        "audio": f"artifact.final-audio.{suffix}",
        "video": f"artifact.final-video.{suffix}",
        "obs": f"artifact.obs.{suffix}",
    }
    hashes = {
        key: (str(index + attempt_number) * 64)[:64]
        for index, key in enumerate(ids)
    }
    produced = [
        _artifact(ids["master"], "publication_audio", hashes["master"]),
        _artifact(ids["terminal"], "publication_video", hashes["terminal"]),
        _artifact(ids["audio"], "publication_audio", hashes["audio"]),
        _artifact(ids["video"], "publication_video", hashes["video"]),
        _artifact(ids["obs"], "obs_scene_collection", hashes["obs"]),
    ]
    return PublicationAttempt.model_validate(
        {
            "attempt_id": f"attempt.publication.{suffix}",
            "attempt_number": attempt_number,
            "episode_id": state.episode_id,
            "run_id": state.run_id,
            "story_sha256": state.story_sha256,
            "started_at": T0 + timedelta(minutes=attempt_number),
            "completed_at": T0 + timedelta(minutes=attempt_number, seconds=30),
            "producer": _producer("master_audio_mux"),
            "dependencies": [],
            "input_artifacts": [],
            "produced_artifacts": produced,
            "story_refs": [],
            "result": {
                "status": "succeeded",
                "receipt": {
                    "input_artifact_ids": [],
                    "output_artifact_ids": list(ids.values()),
                    "master_audio_artifact_id": ids["master"],
                    "terminal_video_artifact_id": ids["terminal"],
                    "final_audio_artifact_id": ids["audio"],
                    "final_video_artifact_id": ids["video"],
                    "obs_scene_collection_artifact_id": ids["obs"],
                    "destinations": [
                        {
                            "destination_id": "test.destination",
                            "locator": "test://terminal-output",
                            "published_artifact_ids": [ids["audio"], ids["video"]],
                        }
                    ],
                },
            },
        }
    )


def _acceptance(
    envelope: LedgerEnvelope,
    attempt,
    *,
    acceptance_id: str,
    accepted_at: datetime,
    supersedes: str | None = None,
) -> PhaseAcceptance:
    state = envelope.production_state
    assert state is not None
    return PhaseAcceptance(
        acceptance_id=acceptance_id,
        phase_id=attempt.phase_id,
        owner=attempt.owner,
        episode_id=state.episode_id,
        run_id=state.run_id,
        story_sha256=state.story_sha256,
        accepted_attempt_id=attempt.attempt_id,
        accepted_attempt_sha256=production_sha256(attempt),
        validator_id="test.terminal-validator",
        validator_version="1.0.0",
        accepted_at=accepted_at,
        supersedes_acceptance_id=supersedes,
    )


def _audit_attempt(
    envelope: LedgerEnvelope,
    publication_attempt: PublicationAttempt,
    publication_acceptance: PhaseAcceptance,
    *,
    pre_audit_sha256: str | None = None,
    publication_acceptance_id: str | None = None,
    check_status: str = "pass",
) -> AuditAttempt:
    state = envelope.production_state
    assert state is not None
    final_audio = publication_attempt.result.receipt.final_audio_artifact_id
    published_artifact = next(
        row
        for row in publication_attempt.produced_artifacts
        if row.artifact_id == final_audio
    )
    dependency = DependencyRef(
        phase_id="publication",
        acceptance_id=publication_acceptance.acceptance_id,
        accepted_attempt_id=publication_attempt.attempt_id,
        acceptance_sha256=production_sha256(publication_acceptance),
    )
    input_artifact = ArtifactRef(
        phase_id="publication",
        acceptance_id=publication_acceptance.acceptance_id,
        accepted_attempt_id=publication_attempt.attempt_id,
        artifact_id=published_artifact.artifact_id,
        content_sha256=published_artifact.content_sha256,
    )
    return AuditAttempt.model_validate(
        {
            "attempt_id": "attempt.audit.1",
            "attempt_number": 1,
            "episode_id": state.episode_id,
            "run_id": state.run_id,
            "story_sha256": state.story_sha256,
            "started_at": T0 + timedelta(minutes=4),
            "completed_at": T0 + timedelta(minutes=5),
            "producer": _producer("full_run_audit"),
            "dependencies": [dependency],
            "input_artifacts": [input_artifact],
            "produced_artifacts": [
                _artifact("artifact.audit-report.1", "audit_report", "f" * 64)
            ],
            "story_refs": [],
            "result": {
                "status": "succeeded",
                "receipt": {
                    "input_artifact_ids": [published_artifact.artifact_id],
                    "output_artifact_ids": ["artifact.audit-report.1"],
                    "policy_id": "terminal-audit",
                    "policy_version": "1.0.0",
                    "story_sha256": state.story_sha256,
                    "pre_audit_production_sha256": (
                        pre_audit_sha256 or production_sha256(state)
                    ),
                    "publication_acceptance_id": (
                        publication_acceptance_id
                        or publication_acceptance.acceptance_id
                    ),
                    "checks": [
                        {
                            "check_id": "terminal-integrity",
                            "status": check_status,
                            "evidence_artifact_ids": [],
                            "message": "Terminal integrity was evaluated.",
                        }
                    ],
                    "report_artifact_id": "artifact.audit-report.1",
                },
            },
        }
    )


def _accepted_terminal_state(
    *,
    required_extra: str | None = None,
    optional_extra: str | None = "workspace_identity",
    pre_audit_sha256: str | None = None,
    publication_acceptance_id: str | None = None,
    check_status: str = "pass",
):
    original = _normative()
    initialized = initialize_production_state(
        original,
        run_id=RUN_ID,
        created_at=T0,
        run_plan=_terminal_plan(
            required_extra=required_extra,
            optional_extra=optional_extra,
        ),
        receipt_verifiers=_trusted_registry(original),
    )
    publication_attempt = _publication_attempt(initialized)
    after_publication_attempt = append_production_attempt(
        initialized,
        publication_attempt,
        receipt_verifiers=_trusted_registry(initialized),
    )
    publication_acceptance = _acceptance(
        after_publication_attempt,
        publication_attempt,
        acceptance_id="acceptance.publication.1",
        accepted_at=T0 + timedelta(minutes=3),
    )
    published = accept_production_attempt(
        after_publication_attempt,
        publication_acceptance,
        receipt_verifiers=_trusted_registry(after_publication_attempt),
    )
    audit_attempt = _audit_attempt(
        published,
        publication_attempt,
        publication_acceptance,
        pre_audit_sha256=pre_audit_sha256,
        publication_acceptance_id=publication_acceptance_id,
        check_status=check_status,
    )
    after_audit_attempt = append_production_attempt(
        published,
        audit_attempt,
        receipt_verifiers=_trusted_registry(published),
    )
    audit_acceptance = _acceptance(
        after_audit_attempt,
        audit_attempt,
        acceptance_id="acceptance.audit.1",
        accepted_at=T0 + timedelta(minutes=6),
    )
    terminal = accept_production_attempt(
        after_audit_attempt,
        audit_acceptance,
        receipt_verifiers=_trusted_registry(after_audit_attempt),
    )
    return {
        "original": original,
        "initialized": initialized,
        "publication_attempt": publication_attempt,
        "publication_acceptance": publication_acceptance,
        "published": published,
        "audit_attempt": audit_attempt,
        "audit_acceptance": audit_acceptance,
        "terminal": terminal,
    }


def _minted():
    context = _accepted_terminal_state()
    terminal = context["terminal"]
    sealed = mint_final_seal(
        terminal,
        sealed_at=T0 + timedelta(minutes=7),
        receipt_verifiers=_trusted_registry(terminal),
    )
    context["sealed"] = sealed
    return context


def test_mint_binds_terminal_state_and_nonrecursive_payload_without_mutation() -> None:
    context = _accepted_terminal_state()
    terminal = context["terminal"]
    before = copy.deepcopy(terminal.model_dump(mode="json"))

    sealed = mint_final_seal(
        terminal,
        sealed_at=T0 + timedelta(minutes=7),
        receipt_verifiers=_trusted_registry(terminal),
    )
    seal = sealed.final_seal
    state = sealed.production_state
    assert seal is not None
    assert state is not None
    assert terminal.model_dump(mode="json") == before
    assert terminal.final_seal is None
    assert seal.schema_version == FINAL_SEAL_SCHEMA_VERSION
    assert seal.algorithm == "sha256"
    assert seal.canonicalization == "otr.canonical-json.v1"
    assert seal.episode_id == sealed.story_ledger.episode_id
    assert seal.run_id == state.run_id
    assert seal.story_sha256 == sealed.story_seal.story_sha256
    assert seal.production_state_sha256 == production_sha256(state)

    metadata = seal.model_dump(mode="json", exclude={"final_payload_sha256"})
    preimage = sealed.model_dump(mode="json")
    preimage["final_seal"] = metadata
    assert seal.final_payload_sha256 == canonical_sha256(preimage)
    assert seal.final_payload_sha256 != canonical_sha256(seal)
    assert verify_final_seal(
        LedgerEnvelope.model_validate_json(sealed.model_dump_json()),
        receipt_verifiers=_trusted_registry(sealed),
    ) == sealed


def test_optional_phase_may_be_skipped_and_omitted_phases_stay_absent() -> None:
    context = _minted()
    state = context["sealed"].production_state
    assert state is not None
    assert next(row for row in state.run_plan if row.phase_id == "workspace_identity").disposition == "optional"
    assert all(
        event.attempt.phase_id not in {"workspace_identity", "cast_routing"}
        for event in state.journal
        if not isinstance(event, AcceptanceEvent)
    )


def test_mint_requires_production_and_every_required_phase_acceptance() -> None:
    original = _normative()
    with pytest.raises(LedgerContractError, match="requires production_state"):
        mint_final_seal(
            original,
            sealed_at=T0,
            receipt_verifiers=_trusted_registry(original),
        )

    context = _accepted_terminal_state(required_extra="workspace_identity")
    terminal = context["terminal"]
    with pytest.raises(
        LedgerContractError,
        match="required phase 'workspace_identity' has no active acceptance",
    ):
        mint_final_seal(
            terminal,
            sealed_at=T0 + timedelta(minutes=7),
            receipt_verifiers=_trusted_registry(terminal),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"pre_audit_sha256": "0" * 64},
            "does not bind the exact pre-audit production_state",
        ),
        (
            {"publication_acceptance_id": "acceptance.wrong"},
            "does not bind the active publication acceptance",
        ),
        (
            {"check_status": "fail"},
            "contains a failed check",
        ),
    ],
)
def test_terminal_audit_evidence_must_be_exact(kwargs, message: str) -> None:
    context = _accepted_terminal_state(**kwargs)
    terminal = context["terminal"]
    with pytest.raises(LedgerContractError, match=message):
        mint_final_seal(
            terminal,
            sealed_at=T0 + timedelta(minutes=7),
            receipt_verifiers=_trusted_registry(terminal),
        )


def test_audit_acceptance_must_be_the_terminal_production_event() -> None:
    context = _accepted_terminal_state()
    terminal = context["terminal"]
    late_raw = _audit_attempt(
        terminal,
        context["publication_attempt"],
        context["publication_acceptance"],
    ).model_dump(mode="json")
    late_raw.update(
        {
            "attempt_id": "attempt.audit.2",
            "attempt_number": 2,
            "result": {
                "status": "failed",
                "failure": {
                    "code": "LATE_AUDIT_PROBE",
                    "message": "A late event must prevent finalization.",
                    "retriable": True,
                    "diagnostic_artifact_ids": [],
                },
            },
            "produced_artifacts": [],
            "input_artifacts": [],
        }
    )
    late_attempt = AuditAttempt.model_validate(late_raw)
    extended = append_production_attempt(
        terminal,
        late_attempt,
        receipt_verifiers=_trusted_registry(terminal),
    )

    with pytest.raises(LedgerContractError, match="terminal production event"):
        mint_final_seal(
            extended,
            sealed_at=T0 + timedelta(minutes=7),
            receipt_verifiers=_trusted_registry(extended),
        )


def test_superseding_a_dependency_invalidates_terminal_audit_acceptance() -> None:
    context = _accepted_terminal_state()
    terminal = context["terminal"]
    publication_attempt = _publication_attempt(terminal, attempt_number=2)
    attempted = append_production_attempt(
        terminal,
        publication_attempt,
        receipt_verifiers=_trusted_registry(terminal),
    )
    publication_acceptance = _acceptance(
        attempted,
        publication_attempt,
        acceptance_id="acceptance.publication.2",
        accepted_at=T0 + timedelta(minutes=7),
        supersedes=context["publication_acceptance"].acceptance_id,
    )
    superseded = accept_production_attempt(
        attempted,
        publication_acceptance,
        receipt_verifiers=_trusted_registry(attempted),
    )

    with pytest.raises(LedgerContractError, match="stale accepted dependency"):
        mint_final_seal(
            superseded,
            sealed_at=T0 + timedelta(minutes=8),
            receipt_verifiers=_trusted_registry(superseded),
        )


def test_story_trust_is_reverified_for_mint_and_fresh_verification() -> None:
    context = _accepted_terminal_state()
    terminal = context["terminal"]
    before = copy.deepcopy(terminal.model_dump(mode="json"))

    with pytest.raises(LedgerContractError, match="no trusted receipt verifier"):
        mint_final_seal(
            terminal,
            sealed_at=T0 + timedelta(minutes=7),
            receipt_verifiers={},
        )
    assert terminal.model_dump(mode="json") == before

    sealed = mint_final_seal(
        terminal,
        sealed_at=T0 + timedelta(minutes=7),
        receipt_verifiers=_trusted_registry(terminal),
    )
    with pytest.raises(LedgerContractError, match="no trusted receipt verifier"):
        verify_final_seal(sealed, receipt_verifiers={})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("episode_id", "different-episode", "exact episode_id"),
        ("run_id", "different-run", "exact run_id"),
        ("story_sha256", "0" * 64, "story_sha256"),
        ("production_state_sha256", "0" * 64, "complete production_state"),
        ("final_payload_sha256", "0" * 64, "non-recursive final payload"),
    ],
)
def test_final_seal_field_mutations_fail_fresh_load(
    field: str,
    value: str,
    message: str,
) -> None:
    sealed = _minted()["sealed"]
    raw = sealed.model_dump(mode="json")
    raw["final_seal"][field] = value

    with pytest.raises(ValidationError, match=message):
        LedgerEnvelope.model_validate(raw)


def test_seal_time_and_complete_production_mutations_fail_fresh_load() -> None:
    sealed = _minted()["sealed"]
    changed_time = sealed.model_dump(mode="json")
    changed_time["final_seal"]["sealed_at"] = (
        T0 + timedelta(minutes=8)
    ).isoformat()
    with pytest.raises(ValidationError, match="non-recursive final payload"):
        LedgerEnvelope.model_validate(changed_time)

    changed_state = sealed.model_dump(mode="json")
    changed_state["production_state"]["created_at"] = (
        T0 + timedelta(seconds=1)
    ).isoformat()
    with pytest.raises(ValidationError, match="complete production_state"):
        LedgerEnvelope.model_validate(changed_state)

    non_utc = sealed.model_dump(mode="json")
    non_utc["final_seal"]["sealed_at"] = "2026-08-14T08:07:00+01:00"
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        LedgerEnvelope.model_validate(non_utc)


def test_all_production_writes_and_resealing_reject_atomically_after_seal() -> None:
    context = _minted()
    sealed = context["sealed"]
    before = copy.deepcopy(sealed.model_dump(mode="json"))
    late_attempt = _publication_attempt(sealed, attempt_number=2)

    operations = [
        lambda: initialize_production_state(
            sealed,
            run_id="run.illegal",
            created_at=T0,
            run_plan=_terminal_plan(),
            receipt_verifiers=_trusted_registry(sealed),
        ),
        lambda: append_production_attempt(
            sealed,
            late_attempt,
            receipt_verifiers=_trusted_registry(sealed),
        ),
        lambda: accept_production_attempt(
            sealed,
            context["audit_acceptance"],
            receipt_verifiers=_trusted_registry(sealed),
        ),
        lambda: mint_final_seal(
            sealed,
            sealed_at=T0 + timedelta(minutes=8),
            receipt_verifiers=_trusted_registry(sealed),
        ),
        lambda: assert_production_append_only(sealed, sealed),
    ]

    for operation in operations:
        with pytest.raises(LedgerContractError, match="final_seal"):
            operation()
        assert sealed.model_dump(mode="json") == before
