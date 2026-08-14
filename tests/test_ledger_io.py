"""Trusted adapter and atomic persistence proofs for the Ledger envelope."""

from __future__ import annotations

import json
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from upstream_story_lab import ledger_io
from upstream_story_lab.ledger_contract import (
    AcceptanceEvent,
    AttemptEvent,
    LedgerEnvelope,
    accept_production_attempt,
    append_production_attempt,
    canonical_bytes,
    verify_production_state,
)
from upstream_story_lab.ledger_io import (
    LEDGER_JSON_FORMAT_ID,
    STORY_TO_PRODUCTION_ADAPTER_ID,
    STORY_TO_PRODUCTION_ADAPTER_VERSION,
    LedgerIOError,
    adapt_story_envelope_to_production,
    load_ledger_envelope,
    save_ledger_envelope,
)
from upstream_story_lab.ledger_verifiers import build_trusted_receipt_verifiers
from upstream_story_lab.production_contract import (
    PhaseAcceptance,
    WorkspaceIdentityAttempt,
    default_run_plan,
    production_sha256,
)
from tests.test_final_seal import _minted as _minted_final_envelope


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "fixtures" / "story_recovery" / "v2"
NORMATIVE = V2 / "normative_ledger_envelope.json"
PACKET = V2 / "source_packets" / "science_news_folder_red_stamps_20260716.json"
LEGACY_V1 = (
    ROOT
    / "fixtures"
    / "story_recovery"
    / "v1"
    / "normative_ledger_envelope.json"
)
CURRENT_L4 = ROOT / "fixtures" / "story_recovery" / "scifi_news_bad_20260813.json"
NOW = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
RUN_ID = "run.ledger-io-001"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _story_only() -> LedgerEnvelope:
    return LedgerEnvelope.model_validate(_json(NORMATIVE))


def _registry(envelope: LedgerEnvelope):
    digest = envelope.story_ledger.body.source_packet.packet_sha256
    return build_trusted_receipt_verifiers(
        packet_artifacts={digest: PACKET.read_bytes()}
    )


def _adapted() -> LedgerEnvelope:
    envelope = _story_only()
    return adapt_story_envelope_to_production(
        envelope,
        run_id=RUN_ID,
        created_at=NOW,
        run_plan=default_run_plan(),
        receipt_verifiers=_registry(envelope),
    )


def _workspace_attempt(envelope: LedgerEnvelope) -> WorkspaceIdentityAttempt:
    state = envelope.production_state
    assert state is not None
    return WorkspaceIdentityAttempt.model_validate(
        {
            "attempt_id": "attempt.workspace.1",
            "attempt_number": 1,
            "episode_id": state.episode_id,
            "run_id": state.run_id,
            "story_sha256": state.story_sha256,
            "started_at": NOW,
            "completed_at": NOW,
            "producer": {
                "component_id": "episode_workspace",
                "component_version": "1.0.0",
                "source_revision": "ledger-io-test",
                "config_sha256": "c" * 64,
            },
            "dependencies": [],
            "input_artifacts": [],
            "produced_artifacts": [
                {
                    "artifact_id": "artifact.workspace-manifest",
                    "artifact_kind": "workspace_manifest",
                    "media_type": "application/json",
                    "storage_root_id": "episode-root",
                    "relative_path": "runs/ledger-io/workspace.json",
                    "content_sha256": "a" * 64,
                    "size_bytes": 137,
                    "durability": "episode_local",
                    "story_refs": [],
                }
            ],
            "story_refs": [],
            "result": {
                "status": "succeeded",
                "receipt": {
                    "input_artifact_ids": [],
                    "output_artifact_ids": ["artifact.workspace-manifest"],
                    "operation": "initialize",
                    "workspace_id": "workspace.ledger-io",
                    "storage_root_id": "episode-root",
                    "relative_workspace_path": "runs/ledger-io",
                },
            },
        }
    )


def _workspace_acceptance(
    envelope: LedgerEnvelope,
    attempt: WorkspaceIdentityAttempt,
) -> PhaseAcceptance:
    state = envelope.production_state
    assert state is not None
    return PhaseAcceptance(
        acceptance_id="acceptance.workspace.1",
        phase_id="workspace_identity",
        owner="episode_workspace",
        episode_id=state.episode_id,
        run_id=state.run_id,
        story_sha256=state.story_sha256,
        accepted_attempt_id=attempt.attempt_id,
        accepted_attempt_sha256=production_sha256(attempt),
        validator_id="test.workspace-validator",
        validator_version="1.0.0",
        accepted_at=NOW,
    )


def test_adapter_identity_and_story_bytes_are_exact() -> None:
    original = _story_only()
    registry = _registry(original)
    story_bytes = canonical_bytes(original.story_ledger)
    body_bytes = canonical_bytes(original.story_ledger.body)
    seal_bytes = canonical_bytes(original.story_seal)

    adapted = adapt_story_envelope_to_production(
        original,
        run_id=RUN_ID,
        created_at=NOW,
        run_plan=default_run_plan(),
        receipt_verifiers=registry,
    )

    assert STORY_TO_PRODUCTION_ADAPTER_ID == "otr.story-lab.production-adapter"
    assert STORY_TO_PRODUCTION_ADAPTER_VERSION == "1"
    assert LEDGER_JSON_FORMAT_ID == "otr.ledger-json.v1"
    assert original.production_state is None
    assert adapted.production_state is not None
    assert adapted.production_state.journal == []
    assert adapted.production_state.story_sha256 == original.story_seal.story_sha256
    assert canonical_bytes(adapted.story_ledger) == story_bytes
    assert canonical_bytes(adapted.story_ledger.body) == body_bytes
    assert canonical_bytes(adapted.story_seal) == seal_bytes
    assert adapted.story_seal == original.story_seal

    with pytest.raises(LedgerIOError, match="unknown.*adapter"):
        adapt_story_envelope_to_production(
            original,
            run_id=RUN_ID,
            created_at=NOW,
            run_plan=default_run_plan(),
            receipt_verifiers=registry,
            adapter_version="2",
        )


@pytest.mark.parametrize("legacy", [LEGACY_V1, CURRENT_L4])
def test_adapter_never_migrates_legacy_or_lossy_shapes(legacy: Path) -> None:
    envelope = _story_only()

    with pytest.raises(LedgerIOError, match="exact current LedgerEnvelope"):
        adapt_story_envelope_to_production(
            _json(legacy),  # type: ignore[arg-type]
            run_id=RUN_ID,
            created_at=NOW,
            run_plan=default_run_plan(),
            receipt_verifiers=_registry(envelope),
        )


def test_story_only_save_is_deterministic_utf8_lf_and_roundtrips(
    tmp_path: Path,
) -> None:
    envelope = _story_only()
    registry = _registry(envelope)
    target = tmp_path / "episode.ledger.json"

    saved = save_ledger_envelope(
        target,
        envelope,
        receipt_verifiers=registry,
    )
    payload = target.read_bytes()
    loaded = load_ledger_envelope(target, receipt_verifiers=registry)

    assert payload == canonical_bytes(envelope) + b"\n"
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in payload
    assert payload.endswith(b"\n")
    assert canonical_bytes(saved) == canonical_bytes(envelope)
    assert canonical_bytes(loaded) == canonical_bytes(envelope)


def test_production_attempt_and_acceptance_roundtrip(tmp_path: Path) -> None:
    initialized = _adapted()
    registry = _registry(initialized)
    attempt = _workspace_attempt(initialized)
    attempted = append_production_attempt(
        initialized,
        attempt,
        receipt_verifiers=registry,
    )
    acceptance = _workspace_acceptance(attempted, attempt)
    accepted = accept_production_attempt(
        attempted,
        acceptance,
        receipt_verifiers=registry,
    )
    target = tmp_path / "production.ledger.json"

    save_ledger_envelope(target, accepted, receipt_verifiers=registry)
    loaded = load_ledger_envelope(target, receipt_verifiers=registry)
    state = verify_production_state(loaded, receipt_verifiers=registry)

    assert canonical_bytes(loaded) == canonical_bytes(accepted)
    assert len(state.journal) == 2
    assert isinstance(state.journal[0], AttemptEvent)
    assert isinstance(state.journal[1], AcceptanceEvent)
    assert state.journal[0].attempt == attempt
    assert state.journal[1].acceptance == acceptance
    assert canonical_bytes(loaded.story_ledger) == canonical_bytes(
        initialized.story_ledger
    )
    assert loaded.story_seal == initialized.story_seal


@pytest.mark.parametrize(
    "tamper",
    [
        "body_sha256",
        "story_sha256",
        "production_story_sha256",
    ],
)
def test_load_rejects_tampered_story_and_production_digests(
    tmp_path: Path,
    tamper: str,
) -> None:
    envelope = _adapted()
    registry = _registry(envelope)
    target = tmp_path / f"tampered-{tamper}.json"
    save_ledger_envelope(target, envelope, receipt_verifiers=registry)
    raw = json.loads(target.read_text(encoding="utf-8"))
    if tamper == "body_sha256":
        raw["story_ledger"]["validation"]["body_sha256"] = "0" * 64
    elif tamper == "story_sha256":
        raw["story_seal"]["story_sha256"] = "0" * 64
    else:
        raw["production_state"]["story_sha256"] = "0" * 64
    target.write_bytes(
        json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    )

    with pytest.raises(LedgerIOError):
        load_ledger_envelope(target, receipt_verifiers=registry)


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b"\xef\xbb\xbf{}\n",
        b"{}\r\n",
        b'{"schema_version":"one","schema_version":"two"}\n',
        b'{"schema_version":"otr.ledger_envelope.v1"}\n',
        b'{"schema_version":"otr.ledger_envelope.v999"}\n',
        b'{"schema":"l4-2026-05-14","lines":[]}\n',
    ],
)
def test_load_rejects_malformed_duplicate_unknown_and_legacy_json(
    tmp_path: Path,
    payload: bytes,
) -> None:
    envelope = _story_only()
    target = tmp_path / "invalid.ledger.json"
    target.write_bytes(payload)

    with pytest.raises(LedgerIOError):
        load_ledger_envelope(target, receipt_verifiers=_registry(envelope))


def test_failed_disk_roundtrip_preserves_existing_target_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = _story_only()
    registry = _registry(envelope)
    target = tmp_path / "existing.ledger.json"
    original = b"existing target must survive byte-for-byte\n"
    target.write_bytes(original)

    def fail_roundtrip(*_args, **_kwargs):
        raise LedgerIOError("deliberate temporary-file roundtrip failure")

    monkeypatch.setattr(ledger_io, "load_ledger_envelope", fail_roundtrip)
    with pytest.raises(LedgerIOError, match="deliberate"):
        save_ledger_envelope(target, envelope, receipt_verifiers=registry)

    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_non_null_final_seal_is_freshly_verified_on_save_and_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sealed = _minted_final_envelope()["sealed"]
    registry = _registry(sealed)
    target = tmp_path / "terminal.ledger.json"
    real_verify_final_seal = ledger_io.verify_final_seal
    verified: list[bytes] = []

    def track_verification(envelope, *, receipt_verifiers):
        verified.append(canonical_bytes(envelope))
        return real_verify_final_seal(
            envelope,
            receipt_verifiers=receipt_verifiers,
        )

    monkeypatch.setattr(ledger_io, "verify_final_seal", track_verification)
    save_ledger_envelope(target, sealed, receipt_verifiers=registry)
    loaded = load_ledger_envelope(target, receipt_verifiers=registry)

    assert canonical_bytes(loaded) == canonical_bytes(sealed)
    assert len(verified) == 4
    assert all(payload == canonical_bytes(sealed) for payload in verified)
    assert "final_seal_verifier" not in inspect.signature(
        save_ledger_envelope
    ).parameters
    assert "final_seal_verifier" not in inspect.signature(
        load_ledger_envelope
    ).parameters


def test_load_rejects_tampered_final_seal_digest(tmp_path: Path) -> None:
    sealed = _minted_final_envelope()["sealed"]
    registry = _registry(sealed)
    target = tmp_path / "tampered-final-seal.ledger.json"
    save_ledger_envelope(target, sealed, receipt_verifiers=registry)
    raw = json.loads(target.read_text(encoding="utf-8"))
    raw["final_seal"]["final_payload_sha256"] = "0" * 64
    target.write_bytes(
        json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    )

    with pytest.raises(LedgerIOError):
        load_ledger_envelope(target, receipt_verifiers=registry)
