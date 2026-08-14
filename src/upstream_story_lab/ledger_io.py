"""Trusted Story Ledger adapter and deterministic atomic JSON persistence.

This module has no legacy migration path.  It accepts only the exact current
typed envelope, re-runs the code-owned story verifiers, and asks the existing
production contract to initialize or validate the append-only journal.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from .ledger_contract import (
    ENVELOPE_SCHEMA_VERSION,
    STORY_SCHEMA_VERSION,
    LedgerEnvelope,
    ReceiptVerifier,
    ReceiptVerifierKey,
    RunPhase,
    canonical_bytes,
    initialize_production_state,
    verify_final_seal,
    verify_production_state,
    verify_story_envelope,
)
from .production_contract import PRODUCTION_STATE_SCHEMA_VERSION


STORY_TO_PRODUCTION_ADAPTER_ID = "otr.story-lab.production-adapter"
STORY_TO_PRODUCTION_ADAPTER_VERSION = "1"
LEDGER_JSON_FORMAT_ID = "otr.ledger-json.v1"


class LedgerIOError(ValueError):
    """A ledger was untrusted, non-current, malformed, or not durably saved."""


def _validate_for_io(
    envelope: LedgerEnvelope,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    if type(envelope) is not LedgerEnvelope:
        raise LedgerIOError(
            "ledger I/O accepts only an exact current LedgerEnvelope instance"
        )
    try:
        validated = verify_story_envelope(
            envelope,
            receipt_verifiers=receipt_verifiers,
        )
        if validated.production_state is not None:
            verify_production_state(
                validated,
                receipt_verifiers=receipt_verifiers,
            )
        if validated.final_seal is not None:
            verify_final_seal(
                validated,
                receipt_verifiers=receipt_verifiers,
            )
        canonical_bytes(validated)
        return validated
    except LedgerIOError:
        raise
    except Exception as exc:
        raise LedgerIOError("ledger failed trusted validation") from exc


def adapt_story_envelope_to_production(
    envelope: LedgerEnvelope,
    *,
    run_id: str,
    created_at: datetime,
    run_plan: Sequence[RunPhase],
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
    adapter_id: str = STORY_TO_PRODUCTION_ADAPTER_ID,
    adapter_version: str = STORY_TO_PRODUCTION_ADAPTER_VERSION,
) -> LedgerEnvelope:
    """Attach an empty typed production journal without touching story bytes."""

    if (
        adapter_id != STORY_TO_PRODUCTION_ADAPTER_ID
        or adapter_version != STORY_TO_PRODUCTION_ADAPTER_VERSION
    ):
        raise LedgerIOError("unknown story-to-production adapter identity")
    trusted = _validate_for_io(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if trusted.production_state is not None:
        raise LedgerIOError("adapter requires a story-only envelope")
    if trusted.final_seal is not None:
        raise LedgerIOError("adapter cannot extend a terminally sealed envelope")

    story_bytes = canonical_bytes(trusted.story_ledger)
    body_bytes = canonical_bytes(trusted.story_ledger.body)
    seal_bytes = canonical_bytes(trusted.story_seal)
    seal_digest = trusted.story_seal.story_sha256
    try:
        adapted = initialize_production_state(
            trusted,
            run_id=run_id,
            created_at=created_at,
            run_plan=list(run_plan),
            receipt_verifiers=receipt_verifiers,
        )
        verify_production_state(
            adapted,
            receipt_verifiers=receipt_verifiers,
        )
    except Exception as exc:
        raise LedgerIOError("production-state initialization failed") from exc

    if canonical_bytes(adapted.story_ledger) != story_bytes:
        raise LedgerIOError("adapter changed canonical story_ledger bytes")
    if canonical_bytes(adapted.story_ledger.body) != body_bytes:
        raise LedgerIOError("adapter changed canonical story body bytes")
    if canonical_bytes(adapted.story_seal) != seal_bytes:
        raise LedgerIOError("adapter changed StorySeal fields")
    if adapted.story_seal.story_sha256 != seal_digest:
        raise LedgerIOError("adapter changed the sealed story digest")
    return adapted


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise LedgerIOError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise LedgerIOError(f"non-finite JSON constant {value!r} is forbidden")


def _parse_strict_json(payload: bytes) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise LedgerIOError("UTF-8 BOM is forbidden")
    if b"\r" in payload:
        raise LedgerIOError("ledger JSON must use LF line endings")
    try:
        text = payload.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except LedgerIOError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LedgerIOError("ledger file is not strict UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise LedgerIOError("ledger JSON root must be an object")
    return parsed


def _require_current_schema(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != ENVELOPE_SCHEMA_VERSION:
        raise LedgerIOError(
            "only the exact current ledger-envelope schema is accepted"
        )
    story = payload.get("story_ledger")
    if (
        not isinstance(story, dict)
        or story.get("schema_version") != STORY_SCHEMA_VERSION
    ):
        raise LedgerIOError(
            "only the exact current story-ledger schema is accepted"
        )
    production = payload.get("production_state")
    if production is not None and (
        not isinstance(production, dict)
        or production.get("schema_version") != PRODUCTION_STATE_SCHEMA_VERSION
    ):
        raise LedgerIOError(
            "only the exact current production-state schema is accepted"
        )


def _load_ledger_bytes(
    payload: bytes,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    parsed = _parse_strict_json(payload)
    _require_current_schema(parsed)
    try:
        envelope = LedgerEnvelope.model_validate(parsed)
    except Exception as exc:
        raise LedgerIOError("ledger JSON violates the typed envelope") from exc
    return _validate_for_io(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )


def load_ledger_envelope(
    path: str | os.PathLike[str],
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Load and freshly verify an exact current ledger artifact."""

    target = Path(path)
    try:
        payload = target.read_bytes()
    except OSError as exc:
        raise LedgerIOError(f"cannot read ledger file {target}") from exc
    return _load_ledger_bytes(
        payload,
        receipt_verifiers=receipt_verifiers,
    )


def save_ledger_envelope(
    path: str | os.PathLike[str],
    envelope: LedgerEnvelope,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Validate, roundtrip, then atomically replace one deterministic file."""

    target = Path(path)
    if not target.parent.is_dir():
        raise LedgerIOError("ledger target directory does not exist")
    validated = _validate_for_io(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    payload = canonical_bytes(validated) + b"\n"

    # The in-memory roundtrip happens before a temporary or target file moves.
    roundtripped = _load_ledger_bytes(
        payload,
        receipt_verifiers=receipt_verifiers,
    )
    if canonical_bytes(roundtripped) != canonical_bytes(validated):
        raise LedgerIOError("serialized ledger did not roundtrip exactly")

    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

        disk_roundtrip = load_ledger_envelope(
            temporary,
            receipt_verifiers=receipt_verifiers,
        )
        if canonical_bytes(disk_roundtrip) != canonical_bytes(validated):
            raise LedgerIOError("temporary ledger did not roundtrip exactly")
        os.replace(temporary, target)
        temporary = None
    except LedgerIOError:
        raise
    except OSError as exc:
        raise LedgerIOError(f"cannot atomically save ledger file {target}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return validated


__all__ = [
    "LEDGER_JSON_FORMAT_ID",
    "STORY_TO_PRODUCTION_ADAPTER_ID",
    "STORY_TO_PRODUCTION_ADAPTER_VERSION",
    "LedgerIOError",
    "adapt_story_envelope_to_production",
    "load_ledger_envelope",
    "save_ledger_envelope",
]
