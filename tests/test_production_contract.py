"""Executable laws for the append-only Ledger Bible v1 production plane."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from upstream_story_lab import (
    LedgerContractError,
    LedgerEnvelope,
    build_trusted_receipt_verifiers,
)
from upstream_story_lab.ledger_contract import (
    accept_production_attempt,
    append_production_attempt,
    assert_production_append_only,
    initialize_production_state,
    verify_production_state,
)
from upstream_story_lab.production_contract import (
    AcceptanceEvent,
    ArtifactReceipt,
    ArtifactRef,
    AttemptEvent,
    CastRoutingAttempt,
    DependencyRef,
    PHASE_ATTEMPT_TYPES,
    PRODUCTION_PHASE_IDS,
    PRODUCTION_PHASE_OWNERS,
    PRODUCTION_PHASE_REGISTRY,
    PhaseAcceptance,
    PhaseAttempt,
    ProductionContractError,
    ProductionState,
    StoryRef,
    WorkspaceIdentityAttempt,
    active_acceptance,
    default_run_plan,
    production_canonical_bytes,
    production_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "fixtures" / "story_recovery" / "v1"
NORMATIVE = V1 / "normative_ledger_envelope.json"
PACKET = V1 / "source_packets" / "science_news_folder_red_stamps_20260716.json"
NOW = datetime(2026, 8, 14, 6, 0, tzinfo=timezone.utc)
RUN_ID = "run.production-contract-001"
ARTIFACT_SHA = "a" * 64


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normative_envelope() -> LedgerEnvelope:
    return LedgerEnvelope.model_validate(_json(NORMATIVE))


def _trusted_registry(envelope: LedgerEnvelope):
    packet_sha = envelope.story_ledger.body.source_packet.packet_sha256
    return build_trusted_receipt_verifiers(
        packet_artifacts={packet_sha: PACKET.read_bytes()}
    )


def _initialized(*, run_plan=None) -> LedgerEnvelope:
    envelope = _normative_envelope()
    return initialize_production_state(
        envelope,
        run_id=RUN_ID,
        created_at=NOW,
        run_plan=default_run_plan() if run_plan is None else run_plan,
        receipt_verifiers=_trusted_registry(envelope),
    )


def _failed_attempt_payload(
    envelope: LedgerEnvelope,
    phase_id: str,
    *,
    attempt_number: int = 1,
    attempt_id: str | None = None,
    dependencies: list[DependencyRef] | None = None,
    input_artifacts: list[ArtifactRef] | None = None,
    story_refs: list[StoryRef] | None = None,
) -> dict:
    state = envelope.production_state
    assert state is not None
    return {
        "phase_id": phase_id,
        "owner": PRODUCTION_PHASE_OWNERS[phase_id],
        "attempt_id": attempt_id or f"attempt.{phase_id}.{attempt_number}",
        "attempt_number": attempt_number,
        "episode_id": state.episode_id,
        "run_id": state.run_id,
        "story_sha256": state.story_sha256,
        "started_at": NOW,
        "completed_at": NOW,
        "producer": {
            "component_id": "test.producer",
            "component_version": "1.0.0",
            "source_revision": "test-revision",
            "config_sha256": "c" * 64,
        },
        "dependencies": dependencies or [],
        "input_artifacts": input_artifacts or [],
        "produced_artifacts": [],
        "story_refs": story_refs or [],
        "result": {
            "status": "failed",
            "failure": {
                "code": "TEST_FAILURE",
                "message": "Deliberate completed failure for contract testing.",
                "retriable": True,
                "diagnostic_artifact_ids": [],
            },
        },
    }


def _failed_attempt(
    envelope: LedgerEnvelope,
    phase_id: str,
    **kwargs,
):
    attempt_type = {
        row.model_fields["phase_id"].default: row for row in PHASE_ATTEMPT_TYPES
    }[phase_id]
    return attempt_type.model_validate(
        _failed_attempt_payload(envelope, phase_id, **kwargs)
    )


def _workspace_attempt(
    envelope: LedgerEnvelope,
    *,
    story_refs: list[StoryRef] | None = None,
) -> WorkspaceIdentityAttempt:
    state = envelope.production_state
    assert state is not None
    refs = story_refs or []
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
                "source_revision": "test-revision",
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
                    "relative_path": "runs/production-contract/workspace.json",
                    "content_sha256": ARTIFACT_SHA,
                    "size_bytes": 137,
                    "durability": "episode_local",
                    "story_refs": refs,
                }
            ],
            "story_refs": refs,
            "result": {
                "status": "succeeded",
                "receipt": {
                    "input_artifact_ids": [],
                    "output_artifact_ids": ["artifact.workspace-manifest"],
                    "operation": "initialize",
                    "workspace_id": "workspace.production-contract",
                    "storage_root_id": "episode-root",
                    "relative_workspace_path": "runs/production-contract",
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


def _accepted_workspace(*, run_plan=None):
    initialized = _initialized(run_plan=run_plan)
    attempt = _workspace_attempt(initialized)
    attempted = append_production_attempt(
        initialized,
        attempt,
        receipt_verifiers=_trusted_registry(initialized),
    )
    acceptance = _workspace_acceptance(attempted, attempt)
    accepted = accept_production_attempt(
        attempted,
        acceptance,
        receipt_verifiers=_trusted_registry(attempted),
    )
    return initialized, attempt, attempted, acceptance, accepted


def test_schema_exposes_exactly_18_discriminated_typed_phase_attempts() -> None:
    schema = LedgerEnvelope.model_json_schema()
    attempt_schema = schema["$defs"]["AttemptEvent"]["properties"]["attempt"]
    mapping = attempt_schema["discriminator"]["mapping"]

    assert tuple(mapping) == tuple(sorted(PRODUCTION_PHASE_IDS))
    assert len(attempt_schema["oneOf"]) == len(PRODUCTION_PHASE_IDS) == 18
    assert {
        item["$ref"].removeprefix("#/$defs/")
        for item in attempt_schema["oneOf"]
    } == {attempt_type.__name__ for attempt_type in PHASE_ATTEMPT_TYPES}

    for attempt_type in PHASE_ATTEMPT_TYPES:
        result_schema = schema["$defs"][attempt_type.__name__]["properties"][
            "result"
        ]
        receipt_name = attempt_type.__name__.removesuffix("Attempt") + "Receipt"
        assert result_schema["discriminator"]["mapping"] == {
            "failed": "#/$defs/FailedResult",
            "succeeded": f"#/$defs/SucceededResult_{receipt_name}_",
        }


@pytest.mark.parametrize(
    "attempt_type",
    PHASE_ATTEMPT_TYPES,
    ids=lambda row: row.model_fields["phase_id"].default,
)
def test_each_registered_phase_parses_to_its_exact_attempt_type(attempt_type) -> None:
    initialized = _initialized()
    phase_id = attempt_type.model_fields["phase_id"].default
    parsed = TypeAdapter(PhaseAttempt).validate_python(
        _failed_attempt_payload(initialized, phase_id)
    )

    assert type(parsed) is attempt_type
    assert parsed.owner == PRODUCTION_PHASE_OWNERS[phase_id]
    assert parsed.result.status == "failed"


def test_initialization_is_trusted_story_bound_empty_and_non_mutating() -> None:
    original = _normative_envelope()
    original_bytes = copy.deepcopy(original.model_dump(mode="json"))
    plan = default_run_plan()

    initialized = initialize_production_state(
        original,
        run_id=RUN_ID,
        created_at=NOW,
        run_plan=plan,
        receipt_verifiers=_trusted_registry(original),
    )
    state = verify_production_state(
        initialized,
        receipt_verifiers=_trusted_registry(initialized),
    )

    assert original.model_dump(mode="json") == original_bytes
    assert original.production_state is None
    assert state.episode_id == original.story_ledger.episode_id
    assert state.story_sha256 == original.story_seal.story_sha256
    assert state.run_id == RUN_ID
    assert state.journal == []
    assert [(row.phase_id, row.owner) for row in state.run_plan] == list(
        PRODUCTION_PHASE_REGISTRY
    )
    assert_production_append_only(original, initialized)

    with pytest.raises(LedgerContractError, match="already initialized"):
        initialize_production_state(
            initialized,
            run_id="run.second",
            created_at=NOW,
            run_plan=plan,
            receipt_verifiers=_trusted_registry(initialized),
        )


def test_succeeded_workspace_attempt_and_acceptance_are_two_atomic_events() -> None:
    initialized, attempt, attempted, acceptance, accepted = _accepted_workspace()

    assert initialized.production_state is not None
    assert initialized.production_state.journal == []
    assert attempted.production_state is not None
    assert len(attempted.production_state.journal) == 1
    assert isinstance(attempted.production_state.journal[0], AttemptEvent)
    assert attempted.production_state.journal[0].attempt == attempt
    assert accepted.production_state is not None
    assert len(accepted.production_state.journal) == 2
    assert isinstance(accepted.production_state.journal[1], AcceptanceEvent)
    assert active_acceptance(accepted.production_state, "workspace_identity") == (
        acceptance
    )
    assert_production_append_only(initialized, attempted)
    assert_production_append_only(attempted, accepted)
    assert verify_production_state(
        accepted,
        receipt_verifiers=_trusted_registry(accepted),
    ) == accepted.production_state


def test_failed_attempt_cannot_be_accepted_and_rejection_is_atomic() -> None:
    initialized = _initialized()
    failed = _failed_attempt(initialized, "workspace_identity")
    attempted = append_production_attempt(
        initialized,
        failed,
        receipt_verifiers=_trusted_registry(initialized),
    )
    acceptance = PhaseAcceptance(
        acceptance_id="acceptance.failed",
        phase_id="workspace_identity",
        owner="episode_workspace",
        episode_id=failed.episode_id,
        run_id=failed.run_id,
        story_sha256=failed.story_sha256,
        accepted_attempt_id=failed.attempt_id,
        accepted_attempt_sha256=production_sha256(failed),
        validator_id="test.workspace-validator",
        validator_version="1.0.0",
        accepted_at=NOW,
    )
    before = copy.deepcopy(attempted.model_dump(mode="json"))

    with pytest.raises(ValidationError, match="failed attempt cannot be accepted"):
        accept_production_attempt(
            attempted,
            acceptance,
            receipt_verifiers=_trusted_registry(attempted),
        )

    assert attempted.model_dump(mode="json") == before
    assert attempted.production_state is not None
    assert len(attempted.production_state.journal) == 1


def test_append_guard_requires_one_event_and_an_exact_history_prefix() -> None:
    initialized, _, attempted, _, accepted = _accepted_workspace()

    with pytest.raises(
        LedgerContractError,
        match="must append exactly one event",
    ):
        assert_production_append_only(initialized, accepted)

    second = _failed_attempt(
        attempted,
        "workspace_identity",
        attempt_number=2,
        attempt_id="attempt.workspace.2",
    )
    rewritten = attempted.model_dump(mode="json")
    rewritten["production_state"]["journal"][0]["attempt"]["producer"][
        "component_version"
    ] = "rewritten"
    rewritten["production_state"]["journal"].append(
        AttemptEvent(attempt=second).model_dump(mode="json")
    )
    valid_but_rewritten = LedgerEnvelope.model_validate(rewritten)

    with pytest.raises(
        LedgerContractError,
        match="history is not an exact prefix",
    ):
        assert_production_append_only(attempted, valid_but_rewritten)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("episode_id", "different-episode", "does not bind story_ledger"),
        ("story_sha256", "0" * 64, "does not bind story_seal"),
    ],
)
def test_production_root_must_bind_the_exact_story_envelope(
    field: str,
    bad_value: str,
    message: str,
) -> None:
    initialized = _initialized()
    payload = initialized.model_dump(mode="json")
    payload["production_state"][field] = bad_value

    with pytest.raises(ValidationError, match=message):
        LedgerEnvelope.model_validate(payload)


def test_attempt_and_acceptance_identity_must_bind_the_production_root() -> None:
    initialized = _initialized()
    bad_attempt = _failed_attempt_payload(initialized, "workspace_identity")
    bad_attempt["run_id"] = "run.someone-else"
    attempt = WorkspaceIdentityAttempt.model_validate(bad_attempt)

    with pytest.raises(ValidationError, match="attempt identity does not bind"):
        append_production_attempt(
            initialized,
            attempt,
            receipt_verifiers=_trusted_registry(initialized),
        )

    _, workspace_attempt, attempted, _, _ = _accepted_workspace()
    bad_acceptance = _workspace_acceptance(attempted, workspace_attempt).model_copy(
        update={"episode_id": "different-episode"}
    )
    with pytest.raises(ValidationError, match="acceptance identity does not bind"):
        accept_production_attempt(
            attempted,
            bad_acceptance,
            receipt_verifiers=_trusted_registry(attempted),
        )


def test_run_plan_locks_complete_owner_order_and_earlier_dependencies() -> None:
    initialized = _initialized()
    state_payload = initialized.production_state.model_dump(mode="json")

    swapped = copy.deepcopy(state_payload)
    swapped["run_plan"][0], swapped["run_plan"][1] = (
        swapped["run_plan"][1],
        swapped["run_plan"][0],
    )
    with pytest.raises(ValidationError, match="canonical order"):
        ProductionState.model_validate(swapped)

    wrong_owner = copy.deepcopy(state_payload)
    wrong_owner["run_plan"][0]["owner"] = "cast_lock"
    with pytest.raises(ValidationError, match="wrong lifecycle owner"):
        ProductionState.model_validate(wrong_owner)

    forward_dependency = copy.deepcopy(state_payload)
    forward_dependency["run_plan"][0]["depends_on"] = ["cast_routing"]
    with pytest.raises(ValidationError, match="dependency is not earlier"):
        ProductionState.model_validate(forward_dependency)


def _workspace_dependent_plan():
    return [
        row.model_copy(
            update={
                "depends_on": (
                    ["workspace_identity"] if row.phase_id == "cast_routing" else []
                )
            }
        )
        for row in default_run_plan()
    ]


def _cast_dependency_attempt(
    accepted: LedgerEnvelope,
    workspace_attempt: WorkspaceIdentityAttempt,
    acceptance: PhaseAcceptance,
) -> CastRoutingAttempt:
    dependency = DependencyRef(
        phase_id="workspace_identity",
        acceptance_id=acceptance.acceptance_id,
        accepted_attempt_id=workspace_attempt.attempt_id,
        acceptance_sha256=production_sha256(acceptance),
    )
    input_artifact = ArtifactRef(
        phase_id="workspace_identity",
        acceptance_id=acceptance.acceptance_id,
        accepted_attempt_id=workspace_attempt.attempt_id,
        artifact_id="artifact.workspace-manifest",
        content_sha256=ARTIFACT_SHA,
    )
    return CastRoutingAttempt.model_validate(
        _failed_attempt_payload(
            accepted,
            "cast_routing",
            dependencies=[dependency],
            input_artifacts=[input_artifact],
        )
    )


def test_dependency_and_input_artifact_bind_active_accepted_receipts() -> None:
    _, workspace_attempt, _, acceptance, accepted = _accepted_workspace(
        run_plan=_workspace_dependent_plan()
    )
    cast_attempt = _cast_dependency_attempt(
        accepted,
        workspace_attempt,
        acceptance,
    )

    extended = append_production_attempt(
        accepted,
        cast_attempt,
        receipt_verifiers=_trusted_registry(accepted),
    )

    assert extended.production_state is not None
    assert len(extended.production_state.journal) == 3
    assert extended.production_state.journal[-1].attempt == cast_attempt


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda raw: raw["dependencies"].clear(),
            "must bind its declared dependencies",
        ),
        (
            lambda raw: raw["dependencies"][0].__setitem__(
                "acceptance_sha256", "0" * 64
            ),
            "dependency phase.*is stale",
        ),
        (
            lambda raw: raw["input_artifacts"][0].__setitem__(
                "content_sha256", "0" * 64
            ),
            "input artifact does not resolve by ID and digest",
        ),
    ],
)
def test_stale_or_incomplete_dependency_bindings_fail_closed(
    mutation,
    message: str,
) -> None:
    _, workspace_attempt, _, acceptance, accepted = _accepted_workspace(
        run_plan=_workspace_dependent_plan()
    )
    attempt = _cast_dependency_attempt(
        accepted,
        workspace_attempt,
        acceptance,
    )
    raw = attempt.model_dump(mode="json")
    mutation(raw)
    mutated = CastRoutingAttempt.model_validate(raw)
    before = copy.deepcopy(accepted.model_dump(mode="json"))

    with pytest.raises(ValidationError, match=message):
        append_production_attempt(
            accepted,
            mutated,
            receipt_verifiers=_trusted_registry(accepted),
        )

    assert accepted.model_dump(mode="json") == before


def _known_story_refs(envelope: LedgerEnvelope) -> list[StoryRef]:
    body = envelope.story_ledger.body
    return [
        StoryRef(kind="source_packet", ref_id=body.source_packet.packet_id),
        StoryRef(kind="source", ref_id=body.source_packet.sources[0].source_id),
        StoryRef(kind="fact", ref_id=body.source_packet.facts[0].fact_id),
        StoryRef(kind="cast", ref_id=body.cast[0].char_id),
        StoryRef(kind="scene", ref_id=body.scenes[0].scene_id),
        StoryRef(kind="shot", ref_id=body.shots[0].shot_id),
        StoryRef(kind="beat", ref_id=body.beats[0].beat_id),
        StoryRef(kind="line", ref_id=body.lines[0].line_id),
        StoryRef(kind="music_cue", ref_id=body.music_cues[0].cue_id),
        StoryRef(kind="sequence", ref_id=body.sequence[0].sequence_id),
    ]


def test_every_typed_story_reference_namespace_closes_against_sealed_story() -> None:
    initialized = _initialized()
    refs = _known_story_refs(initialized)
    attempt = _workspace_attempt(initialized, story_refs=refs)

    extended = append_production_attempt(
        initialized,
        attempt,
        receipt_verifiers=_trusted_registry(initialized),
    )

    assert extended.production_state is not None
    assert list(extended.production_state.journal[0].attempt.story_refs) == refs


@pytest.mark.parametrize(
    "kind",
    [
        "source_packet",
        "source",
        "fact",
        "cast",
        "scene",
        "shot",
        "beat",
        "line",
        "music_cue",
        "sequence",
    ],
)
def test_unresolved_typed_story_reference_fails_atomically(kind: str) -> None:
    initialized = _initialized()
    attempt = _workspace_attempt(
        initialized,
        story_refs=[StoryRef(kind=kind, ref_id="missing.story-row")],
    )
    before = copy.deepcopy(initialized.model_dump(mode="json"))

    with pytest.raises(ValidationError, match="does not resolve into the sealed story"):
        append_production_attempt(
            initialized,
            attempt,
            receipt_verifiers=_trusted_registry(initialized),
        )

    assert initialized.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "bad_timestamp",
    [
        "2026-08-14T06:00:00",
        "2026-08-14T07:00:00+01:00",
    ],
)
def test_production_timestamps_must_be_explicit_utc(bad_timestamp: str) -> None:
    initialized = _initialized()
    raw = initialized.production_state.model_dump(mode="json")
    raw["created_at"] = bad_timestamp

    with pytest.raises(ValidationError, match="timestamps must be UTC"):
        ProductionState.model_validate(raw)


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute/output.wav",
        "C:\\output\\file.wav",
        "runs/../escape.wav",
        "runs//empty.wav",
    ],
)
def test_artifact_paths_are_strict_relative_posix_paths(bad_path: str) -> None:
    with pytest.raises(ValidationError, match="relative POSIX|dot segments"):
        ArtifactReceipt.model_validate(
            {
                "artifact_id": "artifact.bad-path",
                "artifact_kind": "master_audio",
                "media_type": "audio/wav",
                "storage_root_id": "episode-root",
                "relative_path": bad_path,
                "content_sha256": ARTIFACT_SHA,
                "size_bytes": 1,
                "durability": "episode_local",
            }
        )


def test_floating_point_values_are_forbidden_from_canonical_production_data() -> None:
    with pytest.raises(ProductionContractError, match="floating point is forbidden"):
        production_canonical_bytes({"duration_seconds": 1.25})

    with pytest.raises(ValidationError):
        ArtifactReceipt.model_validate(
            {
                "artifact_id": "artifact.float-size",
                "artifact_kind": "master_audio",
                "media_type": "audio/wav",
                "storage_root_id": "episode-root",
                "relative_path": "runs/output.wav",
                "content_sha256": ARTIFACT_SHA,
                "size_bytes": 1.25,
                "durability": "episode_local",
            }
        )
