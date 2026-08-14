"""Replay the rejected Story Ledger v1 mutation corpus."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from upstream_story_lab import (
    LedgerEnvelope,
    StoryBody,
    StoryLedger,
    build_story_seal,
    build_trusted_receipt_verifiers,
    canonical_sha256,
    verify_story_envelope,
)


ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "fixtures" / "story_recovery" / "v1"
CORPUS_PATH = V1 / "rejected_mutations_v1.json"
MACHINE_BIBLE_PATH = ROOT / "contracts" / "ledger_bible_v1.json"
PACKET_PATH = (
    V1
    / "source_packets"
    / "science_news_folder_red_stamps_20260716.json"
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise AssertionError(f"JSON pointer must start with '/': {pointer!r}")
    return [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer[1:].split("/")
    ]


def _get(document: Any, pointer: str) -> Any:
    value = document
    for token in _pointer_parts(pointer):
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _parent(document: Any, pointer: str) -> tuple[Any, str]:
    parts = _pointer_parts(pointer)
    if not parts:
        raise AssertionError("corpus operations cannot replace the document root")
    value = document
    for token in parts[:-1]:
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value, parts[-1]


def _set(document: Any, pointer: str, value: Any, *, add: bool = False) -> None:
    parent, token = _parent(document, pointer)
    if isinstance(parent, list):
        index = int(token)
        if add:
            parent.insert(index, value)
        else:
            parent[index] = value
    else:
        if not add and token not in parent:
            raise AssertionError(f"replace target does not exist: {pointer}")
        parent[token] = value


def _remove(document: Any, pointer: str) -> None:
    parent, token = _parent(document, pointer)
    if isinstance(parent, list):
        parent.pop(int(token))
    else:
        del parent[token]


def _apply_operations(document: dict[str, Any], operations: list[dict]) -> None:
    for operation in operations:
        op = operation["op"]
        if op == "add":
            _set(
                document,
                operation["path"],
                copy.deepcopy(operation["value"]),
                add=True,
            )
        elif op == "replace":
            _set(
                document,
                operation["path"],
                copy.deepcopy(operation["value"]),
            )
        elif op == "remove":
            _remove(document, operation["path"])
        elif op == "swap":
            first = copy.deepcopy(_get(document, operation["path"]))
            second = copy.deepcopy(_get(document, operation["other"]))
            _set(document, operation["path"], second)
            _set(document, operation["other"], first)
        else:
            raise AssertionError(f"unsupported corpus operation: {op!r}")


def _rejection(
    candidate: dict[str, Any],
    *,
    base_envelope: LedgerEnvelope,
) -> tuple[str, Exception] | None:
    """Rebind legal dependent hashes, then return the first rejection gate."""

    try:
        body = StoryBody.model_validate(candidate["story_ledger"]["body"])
    except Exception as exc:  # the test asserts the exact expected type/message
        return "body_validate", exc

    candidate["story_ledger"]["body"] = body.model_dump(mode="json")
    candidate["story_ledger"]["validation"]["body_sha256"] = canonical_sha256(
        body
    )
    try:
        story = StoryLedger.model_validate(candidate["story_ledger"])
    except Exception as exc:
        return "story_validate", exc

    packet_sha = story.body.source_packet.packet_sha256
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={packet_sha: PACKET_PATH.read_bytes()}
    )
    try:
        seal = build_story_seal(
            story,
            sealed_at=base_envelope.story_seal.sealed_at,
            receipt_verifiers=registry,
        )
    except Exception as exc:
        return "trusted_admit", exc

    candidate["story_ledger"] = story.model_dump(mode="json")
    candidate["story_seal"] = seal.model_dump(mode="json")
    try:
        envelope = LedgerEnvelope.model_validate(candidate)
    except Exception as exc:
        return "envelope_validate", exc
    try:
        verify_story_envelope(envelope, receipt_verifiers=registry)
    except Exception as exc:
        return "trusted_admit", exc
    return None


def test_corpus_base_file_is_raw_byte_pinned_and_normatively_admitted() -> None:
    corpus = _json(CORPUS_PATH)
    base_path = V1 / corpus["base_fixture"]
    base_bytes = base_path.read_bytes()
    envelope = LedgerEnvelope.model_validate_json(base_bytes)
    packet_sha = envelope.story_ledger.body.source_packet.packet_sha256
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={packet_sha: PACKET_PATH.read_bytes()}
    )

    assert hashlib.sha256(base_bytes).hexdigest() == corpus["base_file_sha256"]
    verify_story_envelope(envelope, receipt_verifiers=registry)


def test_corpus_has_exactly_one_rejected_case_per_machine_invariant() -> None:
    corpus = _json(CORPUS_PATH)
    bible = _json(MACHINE_BIBLE_PATH)
    expected = [row["code"] for row in bible["story_invariants"]]
    actual = [case["invariant_code"] for case in corpus["cases"]]
    case_ids = [case["case_id"] for case in corpus["cases"]]

    assert len(expected) == 18
    assert len(actual) == len(set(actual))
    assert set(actual) == set(expected)
    assert len(case_ids) == len(set(case_ids))


def test_machine_bible_names_the_executable_fixture_set() -> None:
    bible = _json(MACHINE_BIBLE_PATH)

    assert bible["executable_fixture_corpus"] == {
        "normative_envelope": (
            "fixtures/story_recovery/v1/normative_ledger_envelope.json"
        ),
        "captured_packet": (
            "fixtures/story_recovery/v1/source_packets/"
            "science_news_folder_red_stamps_20260716.json"
        ),
        "rejected_mutations": (
            "fixtures/story_recovery/v1/rejected_mutations_v1.json"
        ),
        "mutation_coverage_authority": "story_invariants[].code",
        "dependent_digest_policy": (
            "recompute body and story digests before later-gate admission checks"
        ),
        "historical_control_and_challenger": (
            "calibration_evidence_only_never_silent_v1_promotion"
        ),
    }


def test_corpus_is_story_only_and_keeps_future_planes_out_of_scope() -> None:
    corpus = _json(CORPUS_PATH)

    assert corpus["scope"] == "current executable story-plane boundary only"
    assert set(corpus["excluded"]) == {
        "production receipt schemas",
        "Story Lab to OTR adapter",
        "terminal final seal",
    }
    for case in corpus["cases"]:
        for operation in case["operations"]:
            for key in ("path", "other"):
                pointer = operation.get(key, "")
                assert not pointer.startswith("/production_state")
                assert not pointer.startswith("/final_seal")


def test_control_and_challenger_calibration_pins_are_live() -> None:
    corpus = _json(CORPUS_PATH)
    calibration = corpus["evidence_calibration"]
    control = _json((V1 / calibration["control_fixture"]).resolve())
    challenger = _json((V1 / calibration["challenger_fixture"]).resolve())
    cited_findings = {
        code
        for case in corpus["cases"]
        for code in case["challenger_finding_codes"]
    }

    assert control["projection_sha256"] == calibration[
        "control_projection_sha256"
    ]
    assert challenger["projection_sha256"] == calibration[
        "challenger_projection_sha256"
    ]
    assert cited_findings <= set(challenger["expected"]["finding_codes"])
    assert {
        "ANNOUNCER_OPEN_MISSING",
        "ANNOUNCER_CODA_MISSING",
        "FACTUAL_CODA_MISSING",
        "P5_SPEAKER_AUTHORITY_MISSING",
    } <= cited_findings


@pytest.mark.parametrize(
    "case",
    _json(CORPUS_PATH)["cases"],
    ids=lambda case: case["case_id"],
)
def test_every_corpus_mutation_rejects_at_its_declared_gate(case: dict) -> None:
    corpus = _json(CORPUS_PATH)
    base_raw = _json(V1 / corpus["base_fixture"])
    base_envelope = LedgerEnvelope.model_validate(copy.deepcopy(base_raw))
    candidate = copy.deepcopy(base_raw)
    _apply_operations(candidate, case["operations"])

    assert candidate != base_raw
    rejection = _rejection(candidate, base_envelope=base_envelope)

    assert rejection is not None, f"mutation was incorrectly admitted: {case}"
    gate, error = rejection
    assert gate == case["expected_gate"]
    assert re.search(case["expected_message_regex"], str(error), re.IGNORECASE), (
        f"{case['case_id']} rejected with unexpected error: {error}"
    )
