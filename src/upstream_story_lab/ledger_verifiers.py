"""Code-owned trusted outcome verifiers for Story Ledger v1.

The structural models in :mod:`upstream_story_lab.ledger_contract` prove that
the story graph is closed and that receipt evidence points at real rows.  This
module owns the additional deterministic outcome checks required before those
receipts are trusted.  No verifier calls an LLM, performs network I/O, or
silently repairs its input.

The prose policy is deliberately conservative: semantic claims pass only
when their normalized literal evidence is present.  The announcer opening must
name the setting, scene time, every story character, and the episode premise.
The news coda must literally contain at least one complete fact claim that it
cites.  A later fuzzy or model-assisted policy would need a new validator
version; it cannot silently change these receipts.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal

from pydantic import Field, ValidationError

from .ledger_contract import (
    ID_PATTERN,
    LedgerContractError,
    OutcomeReceipt,
    ReceiptVerifier,
    ReceiptVerifierKey,
    SourceFact,
    SourceRecord,
    StoryBody,
    StrictModel,
    canonical_bytes,
)
from .spoken_text_policy import SPOKEN_TEXT_POLICY_ID, spoken_text_is_clean


CAPTURED_SOURCE_PACKET_SCHEMA_VERSION = "otr.captured_source_packet.v1"
TRUSTED_VALIDATOR_VERSION = "1"
LEDGER_INTEGRITY_VALIDATOR_VERSION = "2"

TRUSTED_VALIDATOR_IDENTITIES: Final[Mapping[str, tuple[str, str]]] = (
    MappingProxyType(
        {
            "ledger_integrity": (
                "otr.story_validator.ledger_integrity",
                LEDGER_INTEGRITY_VALIDATOR_VERSION,
            ),
            "news_capture": (
                "otr.story_validator.news_capture",
                TRUSTED_VALIDATOR_VERSION,
            ),
            "announcer_open": (
                "otr.story_validator.announcer_open",
                TRUSTED_VALIDATOR_VERSION,
            ),
            "announcer_news_coda": (
                "otr.story_validator.announcer_news_coda",
                TRUSTED_VALIDATOR_VERSION,
            ),
            "music_bookends": (
                "otr.story_validator.music_bookends",
                TRUSTED_VALIDATOR_VERSION,
            ),
        }
    )
)
TRUSTED_VALIDATOR_VERSIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        outcome: version
        for outcome, (_validator_id, version) in (
            TRUSTED_VALIDATOR_IDENTITIES.items()
        )
    }
)


class CapturedSourcePacketArtifact(StrictModel):
    """Strict external packet bytes projected into an accepted story.

    ``packet_sha256`` intentionally does not appear here: the story ledger
    hashes these complete external bytes, avoiding a recursive self-hash.
    """

    schema_version: Literal[CAPTURED_SOURCE_PACKET_SCHEMA_VERSION] = (
        CAPTURED_SOURCE_PACKET_SCHEMA_VERSION
    )
    packet_id: str = Field(pattern=ID_PATTERN)
    source_bank_id: str = Field(pattern=ID_PATTERN)
    sources: list[SourceRecord] = Field(min_length=1)
    facts: list[SourceFact] = Field(min_length=1)


_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _normalized_words(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).casefold()
    return " ".join(_WORD_RE.findall(normalized))


def _contains_normalized_phrase(text: str, phrase: str) -> bool:
    haystack = _normalized_words(text)
    needle = _normalized_words(phrase)
    return bool(needle) and f" {needle} " in f" {haystack} "


def _has_identity(outcome_name: str, receipt: OutcomeReceipt) -> bool:
    validator_id, validator_version = TRUSTED_VALIDATOR_IDENTITIES[outcome_name]
    return (
        receipt.validator_id == validator_id
        and receipt.validator_version == validator_version
    )


def _evidence(receipt: OutcomeReceipt) -> set[tuple[str, str]]:
    return {(row.kind, row.ref_id) for row in receipt.evidence_refs}


def verify_ledger_integrity(
    body: StoryBody,
    receipt: OutcomeReceipt,
) -> bool:
    """Re-run the graph plus the v1 spoken-only policy without repair."""

    if not _has_identity("ledger_integrity", receipt):
        return False
    try:
        validated = StoryBody.model_validate(body.model_dump(mode="json"))
    except (LedgerContractError, ValidationError):
        return False
    return (
        canonical_bytes(validated) == canonical_bytes(body)
        and spoken_text_is_clean(validated.lines, validated.cast)
    )


def verify_news_capture(
    body: StoryBody,
    receipt: OutcomeReceipt,
    *,
    packet_artifacts: Mapping[str, bytes],
) -> bool:
    if not _has_identity("news_capture", receipt):
        return False

    packet = body.source_packet
    evidence = _evidence(receipt)
    if ("source_packet", packet.packet_id) not in evidence:
        return False
    evidenced_fact_ids = {
        ref_id for kind, ref_id in evidence if kind == "fact"
    }
    if not evidenced_fact_ids:
        return False

    payload = packet_artifacts.get(packet.packet_sha256)
    if payload is None or hashlib.sha256(payload).hexdigest() != packet.packet_sha256:
        return False
    try:
        captured = CapturedSourcePacketArtifact.model_validate_json(payload)
    except (LedgerContractError, ValidationError, ValueError):
        return False

    if (
        captured.packet_id != packet.packet_id
        or captured.source_bank_id != packet.source_bank_id
        or captured.sources != packet.sources
        or captured.facts != packet.facts
    ):
        return False
    return evidenced_fact_ids <= {fact.fact_id for fact in captured.facts}


def verify_announcer_open(
    body: StoryBody,
    receipt: OutcomeReceipt,
) -> bool:
    """Verify the exact first spoken row introduces the required context."""

    if not _has_identity("announcer_open", receipt):
        return False
    open_items = [
        item for item in body.sequence if item.sequence_role == "announcer_open"
    ]
    spoken_items = [item for item in body.sequence if item.ref_kind == "line"]
    if len(open_items) != 1 or not spoken_items or spoken_items[0] != open_items[0]:
        return False
    open_item = open_items[0]
    if ("line", open_item.ref_id) not in _evidence(receipt):
        return False
    line = next((row for row in body.lines if row.line_id == open_item.ref_id), None)
    scene = next(
        (row for row in body.scenes if line is not None and row.scene_id == line.scene_id),
        None,
    )
    if line is None or scene is None or line.speaker_role != "announcer":
        return False

    required_mentions = [
        body.context.setting,
        scene.time,
        *[row.name for row in body.cast if row.cast_role == "character"],
    ]
    introduces_story = _contains_normalized_phrase(
        line.text,
        body.context.premise,
    )
    return introduces_story and all(
        _contains_normalized_phrase(line.text, phrase)
        for phrase in required_mentions
    )


def verify_announcer_news_coda(
    body: StoryBody,
    receipt: OutcomeReceipt,
) -> bool:
    """Verify the last spoken row contains a complete captured fact claim."""

    if not _has_identity("announcer_news_coda", receipt):
        return False
    coda_items = [
        item
        for item in body.sequence
        if item.sequence_role == "announcer_news_coda"
    ]
    spoken_items = [item for item in body.sequence if item.ref_kind == "line"]
    if len(coda_items) != 1 or not spoken_items or spoken_items[-1] != coda_items[0]:
        return False
    coda_item = coda_items[0]
    evidence = _evidence(receipt)
    if ("line", coda_item.ref_id) not in evidence:
        return False
    line = next((row for row in body.lines if row.line_id == coda_item.ref_id), None)
    if line is None or line.speaker_role != "announcer":
        return False

    evidenced_facts = {
        ref_id for kind, ref_id in evidence if kind == "fact"
    } & set(line.fact_ids)
    facts = {
        fact.fact_id: fact
        for fact in body.source_packet.facts
        if fact.fact_id in evidenced_facts
    }
    return bool(facts) and any(
        _contains_normalized_phrase(line.text, fact.claim)
        for fact in facts.values()
    )


def verify_music_bookends(
    body: StoryBody,
    receipt: OutcomeReceipt,
) -> bool:
    """Verify the exact evidenced compiler-owned cues are first and last."""

    if not _has_identity("music_bookends", receipt) or not body.sequence:
        return False
    first = body.sequence[0]
    last = body.sequence[-1]
    if first.sequence_role != "music_open" or last.sequence_role != "music_close":
        return False
    if first.ref_kind != "music_cue" or last.ref_kind != "music_cue":
        return False
    evidence = _evidence(receipt)
    if not {
        ("music_cue", first.ref_id),
        ("music_cue", last.ref_id),
    }.issubset(evidence):
        return False
    cues = {row.cue_id: row for row in body.music_cues}
    return (
        first.ref_id in cues
        and last.ref_id in cues
        and cues[first.ref_id].request_authority == "compiler_bookend"
        and cues[last.ref_id].request_authority == "compiler_bookend"
    )


def build_trusted_receipt_verifiers(
    *,
    packet_artifacts: Mapping[str, bytes],
) -> Mapping[ReceiptVerifierKey, ReceiptVerifier]:
    """Return the immutable five-entry Story Ledger v1 trust registry.

    ``packet_artifacts`` is keyed by the SHA-256 named in
    ``source_packet.packet_sha256``.  Values are snapshotted so later caller
    mutation cannot change what the news verifier observes.
    """

    frozen_packets: dict[str, bytes] = {}
    for digest, payload in packet_artifacts.items():
        if not isinstance(digest, str):
            raise LedgerContractError("packet artifact digest keys must be strings")
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise LedgerContractError("packet artifact values must be bytes")
        frozen_packets[digest] = bytes(payload)
    packet_view: Mapping[str, bytes] = MappingProxyType(frozen_packets)

    by_outcome: dict[str, ReceiptVerifier] = {
        "ledger_integrity": verify_ledger_integrity,
        "news_capture": lambda body, receipt: verify_news_capture(
            body,
            receipt,
            packet_artifacts=packet_view,
        ),
        "announcer_open": verify_announcer_open,
        "announcer_news_coda": verify_announcer_news_coda,
        "music_bookends": verify_music_bookends,
    }
    registry = {
        (outcome, *TRUSTED_VALIDATOR_IDENTITIES[outcome]): verifier
        for outcome, verifier in by_outcome.items()
    }
    return MappingProxyType(registry)


__all__ = [
    "CAPTURED_SOURCE_PACKET_SCHEMA_VERSION",
    "CapturedSourcePacketArtifact",
    "LEDGER_INTEGRITY_VALIDATOR_VERSION",
    "SPOKEN_TEXT_POLICY_ID",
    "TRUSTED_VALIDATOR_IDENTITIES",
    "TRUSTED_VALIDATOR_VERSION",
    "TRUSTED_VALIDATOR_VERSIONS",
    "build_trusted_receipt_verifiers",
    "verify_announcer_news_coda",
    "verify_announcer_open",
    "verify_ledger_integrity",
    "verify_music_bookends",
    "verify_news_capture",
]
