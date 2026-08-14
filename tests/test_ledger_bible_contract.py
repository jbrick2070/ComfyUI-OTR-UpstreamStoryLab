"""Executable checks for the Story Lab Ledger Bible v2 boundary."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from upstream_story_lab.ledger_contract import (
    CANONICALIZATION_ID,
    ENVELOPE_SCHEMA_VERSION,
    FINAL_SEAL_SCHEMA_VERSION,
    LedgerContractError,
    LedgerEnvelope,
    MINIMUM_CONTRACT_ID,
    STORY_SCHEMA_VERSION,
    StoryBody,
    StoryLedger,
    assert_story_unchanged,
    build_story_seal,
    canonical_bytes,
    canonical_sha256,
    verify_story_envelope,
)
from upstream_story_lab.ledger_io import (
    LEDGER_JSON_FORMAT_ID,
    STORY_TO_PRODUCTION_ADAPTER_ID,
    STORY_TO_PRODUCTION_ADAPTER_VERSION,
)
from upstream_story_lab.production_contract import (
    PRODUCTION_STATE_SCHEMA_VERSION,
    STORY_REF_KINDS,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
RECOVERY = ROOT / "fixtures" / "story_recovery"

ZERO_SHA = "0" * 64
ONE_SHA = "1" * 64


def _valid_body_dict() -> dict:
    return {
        "context": {
            "episode_title": "The Clock at Patuxent",
            "story_seed": "A small disagreement reveals why a refuge matters.",
            "setting": "Patuxent Research Refuge",
            "act_count": 1,
        },
        "source_packet": {
            "packet_id": "packet_001",
            "source_bank_id": "science_news",
            "packet_sha256": ZERO_SHA,
            "sources": [
                {
                    "source_id": "source_001",
                    "title": "Refuge research note",
                    "locator": "fixture://source_001",
                    "content_sha256": ONE_SHA,
                }
            ],
            "facts": [
                {
                    "fact_id": "F01",
                    "claim": "The refuge protects 105 acres.",
                    "source_refs": [
                        {
                            "source_id": "source_001",
                            "evidence_locator": "normalized:0-34",
                        }
                    ],
                }
            ],
        },
        "cast": [
            {
                "char_id": "announcer",
                "name": "ANNOUNCER",
                "cast_role": "announcer",
                "character_description": "The program host.",
            },
            {
                "char_id": "c01",
                "name": "MARA VALE",
                "cast_role": "character",
                "character_description": "A field researcher.",
            },
        ],
        "story_arc": {
            "summary": (
                "Mara turns a disagreement over a map into a decision to "
                "protect the refuge."
            ),
            "act_ids": ["a001"],
        },
        "acts": [
            {
                "act_id": "a001",
                "act_number": 1,
                "spine": (
                    "Mara challenges the false promise and commits to the "
                    "ground it represents."
                ),
                "entry_state": "The refuge map is treated as sufficient.",
                "exit_state": "Protection of the actual refuge becomes the choice.",
                "speaking_char_ids": ["c01"],
                "beat_ids": ["b002"],
            }
        ],
        "scenes": [
            {
                "scene_id": "s001",
                "description": "One complete radio scene.",
                "setting": "Patuxent Research Refuge",
                "time": "ten PM",
                "shot_ids": ["sh001"],
            }
        ],
        "shots": [
            {
                "shot_id": "sh001",
                "scene_id": "s001",
                "description": "The broadcast desk and refuge map.",
                "beat_ids": ["b001", "b002", "b003"],
            }
        ],
        "beats": [
            {
                "beat_id": "b001",
                "act_id": None,
                "scene_id": "s001",
                "shot_id": "sh001",
                "intent": "Introduce place, time, story, and character.",
                "line_ids": ["l001"],
            },
            {
                "beat_id": "b002",
                "act_id": "a001",
                "scene_id": "s001",
                "shot_id": "sh001",
                "intent": "Let the fictional disagreement play.",
                "line_ids": ["l002"],
            },
            {
                "beat_id": "b003",
                "act_id": None,
                "scene_id": "s001",
                "shot_id": "sh001",
                "intent": "Summarize the captured news fact.",
                "line_ids": ["l003"],
            },
        ],
        "lines": [
            {
                "line_id": "l001",
                "scene_id": "s001",
                "shot_id": "sh001",
                "beat_id": "b001",
                "char_id": "announcer",
                "speaker": "ANNOUNCER",
                "speaker_role": "announcer",
                "text": "At ten PM at Patuxent, Mara Vale begins tonight's story.",
                "fact_ids": [],
            },
            {
                "line_id": "l002",
                "scene_id": "s001",
                "shot_id": "sh001",
                "beat_id": "b002",
                "char_id": "c01",
                "speaker": "MARA VALE",
                "speaker_role": "character",
                "text": "The map is not a promise unless we protect the ground.",
                "fact_ids": [],
            },
            {
                "line_id": "l003",
                "scene_id": "s001",
                "shot_id": "sh001",
                "beat_id": "b003",
                "char_id": "announcer",
                "speaker": "ANNOUNCER",
                "speaker_role": "announcer",
                "text": "The real report says the refuge protects 105 acres.",
                "fact_ids": ["F01"],
            },
        ],
        "music_cues": [
            {
                "cue_id": "music_open",
                "description": "Opening radio theme.",
                "generation_prompt": "Brief vintage radio opening theme.",
                "request_authority": "compiler_bookend",
            },
            {
                "cue_id": "music_close",
                "description": "Closing radio theme.",
                "generation_prompt": "Brief vintage radio closing theme.",
                "request_authority": "compiler_bookend",
            },
        ],
        "sequence": [
            {
                "sequence_id": "q001",
                "sequence_role": "music_open",
                "ref_kind": "music_cue",
                "ref_id": "music_open",
            },
            {
                "sequence_id": "q002",
                "sequence_role": "announcer_open",
                "ref_kind": "line",
                "ref_id": "l001",
            },
            {
                "sequence_id": "q003",
                "sequence_role": "character_dialogue",
                "ref_kind": "line",
                "ref_id": "l002",
            },
            {
                "sequence_id": "q004",
                "sequence_role": "announcer_news_coda",
                "ref_kind": "line",
                "ref_id": "l003",
            },
            {
                "sequence_id": "q005",
                "sequence_role": "music_close",
                "ref_kind": "music_cue",
                "ref_id": "music_close",
            },
        ],
    }


def _valid_body_for_act_count(act_count: int) -> dict:
    body = _valid_body_dict()
    dialogue_beats = []
    dialogue_lines = []
    acts = []
    for index in range(1, act_count + 1):
        beat_id = f"b{index + 1:03d}"
        line_id = f"l{index + 1:03d}"
        act_id = f"a{index:03d}"
        dialogue_beats.append(
            {
                "beat_id": beat_id,
                "act_id": act_id,
                "scene_id": "s001",
                "shot_id": "sh001",
                "intent": f"Advance act {index} through character dialogue.",
                "line_ids": [line_id],
            }
        )
        dialogue_lines.append(
            {
                "line_id": line_id,
                "scene_id": "s001",
                "shot_id": "sh001",
                "beat_id": beat_id,
                "char_id": "c01",
                "speaker": "MARA VALE",
                "speaker_role": "character",
                "text": f"This is the spoken choice that changes act {index}.",
                "fact_ids": [],
            }
        )
        acts.append(
            {
                "act_id": act_id,
                "act_number": index,
                "spine": f"Act {index} turns the prior choice into a new one.",
                "entry_state": f"The story enters act {index} unresolved.",
                "exit_state": f"The story leaves act {index} changed.",
                "speaking_char_ids": ["c01"],
                "beat_ids": [beat_id],
            }
        )

    coda_beat_id = f"b{act_count + 2:03d}"
    coda_line_id = f"l{act_count + 2:03d}"
    open_beat = copy.deepcopy(body["beats"][0])
    open_line = copy.deepcopy(body["lines"][0])
    coda_beat = copy.deepcopy(body["beats"][-1])
    coda_beat["beat_id"] = coda_beat_id
    coda_beat["line_ids"] = [coda_line_id]
    coda_line = copy.deepcopy(body["lines"][-1])
    coda_line["line_id"] = coda_line_id
    coda_line["beat_id"] = coda_beat_id

    body["context"]["act_count"] = act_count
    body["story_arc"] = {
        "summary": "Each act turns one choice into the next and resolves the story.",
        "act_ids": [act["act_id"] for act in acts],
    }
    body["acts"] = acts
    body["beats"] = [open_beat, *dialogue_beats, coda_beat]
    body["shots"][0]["beat_ids"] = [
        beat["beat_id"] for beat in body["beats"]
    ]
    body["lines"] = [open_line, *dialogue_lines, coda_line]
    body["sequence"] = [
        body["sequence"][0],
        body["sequence"][1],
        *[
            {
                "sequence_id": f"q{index + 3:03d}",
                "sequence_role": "character_dialogue",
                "ref_kind": "line",
                "ref_id": line["line_id"],
            }
            for index, line in enumerate(dialogue_lines)
        ],
        {
            "sequence_id": f"q{act_count + 3:03d}",
            "sequence_role": "announcer_news_coda",
            "ref_kind": "line",
            "ref_id": coda_line_id,
        },
        {
            "sequence_id": f"q{act_count + 4:03d}",
            "sequence_role": "music_close",
            "ref_kind": "music_cue",
            "ref_id": "music_close",
        },
    ]
    return body


def _valid_story() -> StoryLedger:
    body = StoryBody.model_validate(_valid_body_dict())
    body_sha = canonical_sha256(body)
    return StoryLedger.model_validate(
        {
            "schema_version": STORY_SCHEMA_VERSION,
            "episode_id": "episode_001",
            "body": body.model_dump(mode="json"),
            "validation": {
                "body_sha256": body_sha,
                "contract_id": MINIMUM_CONTRACT_ID,
                "outcomes": {
                    "ledger_integrity": {
                        "validator_id": "graph_validator",
                        "validator_version": "1",
                        "evidence_refs": [],
                    },
                    "news_capture": {
                        "validator_id": "news_validator",
                        "validator_version": "1",
                        "evidence_refs": [
                            {"kind": "source_packet", "ref_id": "packet_001"},
                            {"kind": "fact", "ref_id": "F01"},
                        ],
                    },
                    "announcer_open": {
                        "validator_id": "open_validator",
                        "validator_version": "1",
                        "evidence_refs": [{"kind": "line", "ref_id": "l001"}],
                    },
                    "announcer_news_coda": {
                        "validator_id": "coda_validator",
                        "validator_version": "1",
                        "evidence_refs": [
                            {"kind": "line", "ref_id": "l003"},
                            {"kind": "fact", "ref_id": "F01"},
                        ],
                    },
                    "music_bookends": {
                        "validator_id": "music_validator",
                        "validator_version": "1",
                        "evidence_refs": [
                            {"kind": "music_cue", "ref_id": "music_open"},
                            {"kind": "music_cue", "ref_id": "music_close"},
                        ],
                    },
                },
            },
        }
    )


def _trusted_receipt_verifiers() -> dict:
    def accept(_body, _receipt) -> bool:
        return True

    return {
        ("ledger_integrity", "graph_validator", "1"): accept,
        ("news_capture", "news_validator", "1"): accept,
        ("announcer_open", "open_validator", "1"): accept,
        ("announcer_news_coda", "coda_validator", "1"): accept,
        ("music_bookends", "music_validator", "1"): accept,
    }


def _valid_envelope() -> LedgerEnvelope:
    story = _valid_story()
    seal = build_story_seal(
        story,
        sealed_at=datetime(2026, 8, 13, 22, 0, tzinfo=timezone.utc),
        receipt_verifiers=_trusted_receipt_verifiers(),
    )
    return LedgerEnvelope(
        story_ledger=story,
        story_seal=seal,
        production_state=None,
        final_seal=None,
    )


def test_valid_story_envelope_is_ledger_only_and_sealed() -> None:
    envelope = _valid_envelope()

    assert envelope.schema_version == ENVELOPE_SCHEMA_VERSION
    assert envelope.story_seal.canonicalization == CANONICALIZATION_ID
    assert envelope.story_seal.story_sha256 == canonical_sha256(
        envelope.story_ledger
    )
    assert envelope.production_state is None
    assert envelope.final_seal is None


def test_canonical_story_bytes_are_stable_and_float_free() -> None:
    first = _valid_story()
    second = StoryLedger.model_validate(first.model_dump(mode="json"))

    assert canonical_bytes(first) == canonical_bytes(second)
    assert canonical_sha256(first) == canonical_sha256(second)
    with pytest.raises(LedgerContractError, match="floating point"):
        canonical_bytes({"not_story_state": 1.25})


@pytest.mark.parametrize("act_count", range(1, 9))
def test_act_count_one_through_eight_builds_exact_locked_act_topology(
    act_count: int,
) -> None:
    body = StoryBody.model_validate(_valid_body_for_act_count(act_count))

    assert body.context.act_count == act_count
    assert len(body.acts) == act_count
    assert [act.act_number for act in body.acts] == list(
        range(1, act_count + 1)
    )
    assert body.story_arc.act_ids == [act.act_id for act in body.acts]
    assert all(act.beat_ids and act.speaking_char_ids for act in body.acts)


@pytest.mark.parametrize("act_count", [0, 9, "3"])
def test_act_count_rejects_out_of_range_or_non_integer_input(act_count) -> None:
    body = _valid_body_dict()
    body["context"]["act_count"] = act_count

    with pytest.raises(ValidationError):
        StoryBody.model_validate(body)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda data: data["context"].__setitem__("act_count", 2),
            "exact number of acts",
        ),
        (
            lambda data: data["acts"][0].__setitem__("act_number", 2),
            "ordered range",
        ),
        (
            lambda data: data["story_arc"].__setitem__("act_ids", ["a999"]),
            "ordered act table",
        ),
        (
            lambda data: data["acts"][0].__setitem__("beat_ids", ["b999"]),
            "invalid beat",
        ),
        (
            lambda data: data["acts"][0].__setitem__(
                "speaking_char_ids", ["announcer"]
            ),
            "speaking_char_ids",
        ),
        (
            lambda data: data["beats"][1].__setitem__("act_id", None),
            "invalid beat|act beat projections|outside acts",
        ),
        (
            lambda data: (
                data["beats"][0].__setitem__("act_id", "a001"),
                data["acts"][0]["beat_ids"].insert(0, "b001"),
            ),
            "only character dialogue",
        ),
    ],
)
def test_act_arc_spine_and_beat_contract_fails_closed(mutate, message: str) -> None:
    body = _valid_body_dict()
    mutate(body)

    with pytest.raises((LedgerContractError, ValidationError), match=message):
        StoryBody.model_validate(body)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda data: data["sequence"].__setitem__(
                0, {**data["sequence"][0], "sequence_role": "music_close"}
            ),
            "bookend|exactly one",
        ),
        (
            lambda data: data["sequence"].__setitem__(
                1, {**data["sequence"][1], "sequence_role": "character_dialogue"}
            ),
            "first spoken|speech routing",
        ),
        (
            lambda data: data["lines"][2].__setitem__("fact_ids", []),
            "coda must reference",
        ),
        (
            lambda data: data["lines"][1].__setitem__("speaker", "ANNOUNCER"),
            "speaker does not match",
        ),
        (
            lambda data: data["lines"][1].__setitem__("fact_ids", ["F99"]),
            "unknown facts",
        ),
        (
            lambda data: data["beats"][1].__setitem__("shot_id", "missing"),
            "invalid beat",
        ),
        (
            lambda data: data["lines"][1].__setitem__("text", " \n\t"),
            "required text cannot be blank",
        ),
        (
            lambda data: data["lines"].__setitem__(
                slice(0, 2), [data["lines"][1], data["lines"][0]]
            ),
            "spoken line table order",
        ),
        (
            lambda data: data["music_cues"].reverse(),
            "music cue table order",
        ),
        (
            lambda data: data["music_cues"][0].__setitem__(
                "request_authority", "script"
            ),
            "compiler-owned bookends",
        ),
        (
            lambda data: data["beats"].__setitem__(
                slice(0, 2), [data["beats"][1], data["beats"][0]]
            ),
            "beat table order",
        ),
    ],
)
def test_story_graph_and_program_fail_closed(mutate, message: str) -> None:
    body = _valid_body_dict()
    mutate(body)

    with pytest.raises((LedgerContractError, ValidationError), match=message):
        StoryBody.model_validate(body)


def test_shot_table_order_matches_scene_child_projection() -> None:
    body = _valid_body_dict()
    body["scenes"][0]["shot_ids"] = ["sh001", "sh002"]
    body["shots"][0]["beat_ids"] = ["b001", "b002"]
    body["shots"].append(
        {
            "shot_id": "sh002",
            "scene_id": "s001",
            "description": "The broadcast returns to the refuge map.",
            "beat_ids": ["b003"],
        }
    )
    body["beats"][2]["shot_id"] = "sh002"
    body["lines"][2]["shot_id"] = "sh002"
    assert len(StoryBody.model_validate(body).shots) == 2

    body["shots"].reverse()
    with pytest.raises(
        (LedgerContractError, ValidationError), match="shot table order"
    ):
        StoryBody.model_validate(body)


def test_sequence_role_and_speaker_role_are_separate_axes() -> None:
    body = StoryBody.model_validate(_valid_body_dict())
    open_item = body.sequence[1]
    open_line = next(row for row in body.lines if row.line_id == open_item.ref_id)

    assert open_item.sequence_role == "announcer_open"
    assert open_line.speaker_role == "announcer"
    assert open_item.sequence_role != open_line.speaker_role


def test_music_inter_requires_explicit_script_request_and_body_position() -> None:
    body = _valid_body_dict()
    body["music_cues"].insert(
        1,
        {
            "cue_id": "music_inter_01",
            "description": "A short transition.",
            "generation_prompt": "Short radio bridge.",
            "request_authority": "compiler_bookend",
        },
    )
    body["sequence"].insert(
        3,
        {
            "sequence_id": "q003b",
            "sequence_role": "music_inter",
            "ref_kind": "music_cue",
            "ref_id": "music_inter_01",
        },
    )

    with pytest.raises(
        (LedgerContractError, ValidationError), match="explicitly requested"
    ):
        StoryBody.model_validate(body)

    body["music_cues"][1]["request_authority"] = "script"
    assert StoryBody.model_validate(body).sequence[3].sequence_role == "music_inter"


def test_story_validation_receipt_binds_exact_body() -> None:
    story = _valid_story().model_dump(mode="json")
    story["body"]["lines"][1]["text"] += " Changed."

    with pytest.raises(
        (LedgerContractError, ValidationError), match="body_sha256"
    ):
        StoryLedger.model_validate(story)


@pytest.mark.parametrize("field", ["production_state", "final_seal"])
def test_malformed_production_or_nonnull_final_plane_fails(field: str) -> None:
    envelope = _valid_envelope().model_dump(mode="json")
    envelope[field] = {}

    with pytest.raises(ValidationError):
        LedgerEnvelope.model_validate(envelope)


def test_story_mutation_is_detected_even_if_nested_model_was_changed() -> None:
    before = _valid_envelope()
    after = before.model_copy(deep=True)
    after.story_ledger.body.lines[1].text += " Changed."

    with pytest.raises(LedgerContractError, match="mutated story_ledger"):
        assert_story_unchanged(before, after)


def test_story_seal_receipt_is_immutable_during_production_extension() -> None:
    before = _valid_envelope()
    after = before.model_copy(deep=True)
    after.story_seal.sealed_at = datetime(
        2026, 8, 13, 22, 1, tzinfo=timezone.utc
    )

    with pytest.raises(LedgerContractError, match="mutated story_seal"):
        assert_story_unchanged(before, after)


def test_seal_builder_revalidates_mutated_story_before_hashing() -> None:
    story = _valid_story()
    story.body.lines[1].text += " Changed after validation."

    with pytest.raises((LedgerContractError, ValidationError), match="body_sha256"):
        build_story_seal(
            story,
            sealed_at=datetime(2026, 8, 13, 22, 0, tzinfo=timezone.utc),
            receipt_verifiers=_trusted_receipt_verifiers(),
        )


def test_seal_builder_requires_trusted_receipt_verifiers() -> None:
    with pytest.raises(LedgerContractError, match="no trusted receipt verifier"):
        build_story_seal(
            _valid_story(),
            sealed_at=datetime(2026, 8, 13, 22, 0, tzinfo=timezone.utc),
            receipt_verifiers={},
        )


def test_trusted_envelope_admission_reruns_receipt_verifiers() -> None:
    envelope = _valid_envelope()
    reject = _trusted_receipt_verifiers()
    reject[("announcer_open", "open_validator", "1")] = (
        lambda _body, _receipt: False
    )

    with pytest.raises(LedgerContractError, match="failed trusted"):
        verify_story_envelope(envelope, receipt_verifiers=reject)


def test_trusted_receipt_verifier_cannot_mutate_its_inputs() -> None:
    verifiers = _trusted_receipt_verifiers()

    def mutate(body, _receipt) -> bool:
        body.lines[0].text += " Mutated by verifier."
        return True

    verifiers[("announcer_open", "open_validator", "1")] = mutate

    with pytest.raises(LedgerContractError, match="mutated its sealed input"):
        build_story_seal(
            _valid_story(),
            sealed_at=datetime(2026, 8, 13, 22, 0, tzinfo=timezone.utc),
            receipt_verifiers=verifiers,
        )


@pytest.mark.parametrize(
    "sealed_at",
    [
        datetime(2026, 8, 13, 22, 0),
        datetime.fromisoformat("2026-08-13T23:00:00+01:00"),
    ],
)
def test_story_seal_time_requires_timezone_aware_utc(sealed_at: datetime) -> None:
    with pytest.raises((LedgerContractError, ValidationError), match="UTC"):
        build_story_seal(
            _valid_story(),
            sealed_at=sealed_at,
            receipt_verifiers=_trusted_receipt_verifiers(),
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda body: body["source_packet"]["sources"].append(
                {
                    "source_id": "source_002",
                    "title": "Unused source",
                    "locator": "fixture://source_002",
                    "content_sha256": "2" * 64,
                }
            ),
            "every source",
        ),
        (
            lambda body: body["source_packet"]["facts"].append(
                {
                    "fact_id": "F02",
                    "claim": "An accepted but uncited fact.",
                    "source_refs": [
                        {
                            "source_id": "source_001",
                            "evidence_locator": "normalized:35-60",
                        }
                    ],
                }
            ),
            "every accepted fact",
        ),
        (
            lambda body: body["cast"].append(
                {
                    "char_id": "c02",
                    "name": "ELIAS NORTH",
                    "cast_role": "character",
                    "character_description": "An unused cast member.",
                }
            ),
            "every cast member",
        ),
    ],
)
def test_story_source_fact_and_cast_tables_reject_orphans(mutate, message: str) -> None:
    body = _valid_body_dict()
    mutate(body)

    with pytest.raises((LedgerContractError, ValidationError), match=message):
        StoryBody.model_validate(body)


@pytest.mark.parametrize(
    ("outcome", "evidence_refs", "message"),
    [
        (
            "news_capture",
            [{"kind": "source_packet", "ref_id": "packet_001"}],
            "source packet and a fact",
        ),
        (
            "announcer_open",
            [{"kind": "line", "ref_id": "l002"}],
            "exact opening line",
        ),
        (
            "announcer_news_coda",
            [{"kind": "line", "ref_id": "l003"}],
            "coda line and its fact",
        ),
        (
            "music_bookends",
            [{"kind": "music_cue", "ref_id": "music_open"}],
            "opening and closing cues",
        ),
    ],
)
def test_outcome_receipts_require_typed_exact_evidence(
    outcome: str, evidence_refs: list[dict[str, str]], message: str
) -> None:
    story = _valid_story().model_dump(mode="json")
    story["validation"]["outcomes"][outcome]["evidence_refs"] = evidence_refs

    with pytest.raises((LedgerContractError, ValidationError), match=message):
        StoryLedger.model_validate(story)


def test_outcome_receipt_rejects_duplicate_typed_evidence() -> None:
    story = _valid_story().model_dump(mode="json")
    evidence = story["validation"]["outcomes"]["announcer_open"][
        "evidence_refs"
    ]
    evidence.append(copy.deepcopy(evidence[0]))

    with pytest.raises(
        (LedgerContractError, ValidationError), match="repeats an evidence"
    ):
        StoryLedger.model_validate(story)


def test_machine_bible_matches_executable_contract() -> None:
    bible = json.loads(
        (CONTRACTS / "ledger_bible_v2.json").read_text(encoding="utf-8")
    )

    assert bible["versions"]["envelope"] == ENVELOPE_SCHEMA_VERSION
    assert bible["versions"]["story_ledger"] == STORY_SCHEMA_VERSION
    assert bible["versions"]["canonicalization"] == CANONICALIZATION_ID
    assert bible["versions"]["minimum_contract"] == MINIMUM_CONTRACT_ID
    assert bible["versions"]["production_state"] == (
        PRODUCTION_STATE_SCHEMA_VERSION
    )
    assert bible["versions"]["final_seal"] == FINAL_SEAL_SCHEMA_VERSION
    assert bible["routing_enums"]["story_ref_kind"] == list(STORY_REF_KINDS)
    assert bible["act_authoring"]["visible_length_control"] == "act_count"
    assert (bible["act_authoring"]["minimum"], bible["act_authoring"]["maximum"]) == (1, 8)
    assert bible["act_authoring"]["word_count"] == (
        "not_a_control_or_acceptance_rule"
    )
    assert bible["act_authoring"]["stable_job_count"] == (
        "4 * act_count + 7"
    )
    assert bible["act_authoring"]["base_model_job_count"] == (
        "4 * act_count + 4"
    )
    assert bible["routing_enums"]["speaker_role"] == [
        "announcer",
        "character",
    ]
    assert bible["routing_enums"]["music_request_authority"] == [
        "compiler_bookend",
        "script",
    ]
    assert bible["routing_enums"]["sequence_role"] == [
        "music_open",
        "announcer_open",
        "character_dialogue",
        "music_inter",
        "announcer_news_coda",
        "music_close",
    ]
    assert bible["minimum_ship_outcomes"] == [
        "ledger_integrity",
        "news_capture",
        "announcer_open",
        "announcer_news_coda",
        "music_bookends",
    ]
    assert set(bible["minimum_ship_evidence"]) == set(
        bible["minimum_ship_outcomes"]
    )
    assert "typed append-only production_state" in bible["boundary"][
        "current_executable_scope"
    ]
    assert "typed terminal final_seal" in bible["boundary"][
        "current_executable_scope"
    ]
    assert bible["status"] == (
        "enshrined_story_lab_constitution_not_yet_transplanted"
    )
    persistence = bible["adapter_and_persistence"]
    assert persistence["adapter_id"] == STORY_TO_PRODUCTION_ADAPTER_ID
    assert persistence["adapter_version"] == STORY_TO_PRODUCTION_ADAPTER_VERSION
    assert persistence["json_format"] == LEDGER_JSON_FORMAT_ID
    assert persistence["legacy_or_l4_migration"] == "forbidden"
    phases = bible["production_phase_registry"]
    phase_ids = [row["phase_id"] for row in phases]
    assert len(phase_ids) == len(set(phase_ids))
    assert phase_ids == [
        "workspace_identity",
        "cast_routing",
        "voice_render",
        "music_render",
        "speech_timeline",
        "audio_enhance",
        "master_audio",
        "procgen_video",
        "visual_plan",
        "image_render",
        "video_render",
        "silent_composite",
        "scopes",
        "post_blend",
        "captions",
        "credits",
        "publication",
        "audit",
    ]
    assert len({row["owner"] for row in phases}) == len(phases)


def test_human_bible_carries_machine_versions_and_role_axes() -> None:
    machine = json.loads(
        (CONTRACTS / "ledger_bible_v2.json").read_text(encoding="utf-8")
    )
    human = (ROOT / "docs" / "LEDGER_BIBLE.md").read_text(encoding="utf-8")

    for version in machine["versions"].values():
        assert version in human
    for role in machine["routing_enums"]["sequence_role"]:
        assert role in human
    assert "speaker_role" in human
    assert "sequence_role" in human
    assert "production_state=null" in human
    assert "final_seal=null" in human


def test_consumer_matrix_records_current_mutability_and_agy_corrections() -> None:
    matrix = json.loads(
        (CONTRACTS / "ledger_consumer_matrix_l4.json").read_text(encoding="utf-8")
    )
    records = {row["component"]: row for row in matrix["records"]}

    assert matrix["current_freeze_verdict"] == {
        "whole_ledger_immutable": False,
        "authored_core_save_guard_present": False,
        "phase_10_behavior": (
            "validates selected structure and stamps status metadata"
        ),
        "cleanup_locked_production_readers": 0,
        "post_phase_10_mutation_is_normal": True,
    }
    assert records["SilentComposite"]["classification"] == (
        "checked_not_a_ledger_consumer"
    )
    assert records["CaptionBurn"]["writes"] == []
    assert records["CreditsRoll"]["writes"] == []
    assert "clips_filesystem_and_manifest" in records["VideoRenderBatch"][
        "durability"
    ]
    assert records["MasterAudioMux"]["failure_policy"].startswith(
        "publication may succeed"
    )
    assert records["SaveToEpisodeWorkspace"]["reads"] == [
        "active durable root episode_id"
    ]
    assert records["SaveToEpisodeWorkspace"]["durability"].startswith(
        "filesystem_only"
    )
    assert records["BuildSilentTestEpisode"]["classification"] == (
        "consumer_transformer"
    )
    assert records["BuildSilentTestEpisode"]["durability"].startswith(
        "separate_offline_fixture_artifacts"
    )
    assert {row["verdict"] for row in matrix["agy_claim_adjudication"]} == {
        "disagree",
        "partial",
    }


def test_requirements_file_uses_two_seals_not_monolithic_freeze() -> None:
    requirements = json.loads(
        (RECOVERY / "ledger_requirements_v2.json").read_text(encoding="utf-8")
    )

    assert requirements["artifact_boundary"]["required_planes"] == [
        "story_ledger",
        "story_seal",
    ]
    assert requirements["artifact_boundary"]["story_lab_null_planes"] == [
        "production_state",
        "final_seal",
    ]
    freeze = requirements["freeze_semantics"]
    assert freeze["story_ledger_post_acceptance_mutation"] == "forbidden"
    assert freeze["story_seal_requires_trusted_receipt_registry"] is True
    assert freeze["production_state_post_acceptance_mutation"] == (
        "phase_owned_append_only"
    )
    assert freeze["final_seal_after"] == "publication_and_audit"
    assert freeze["current_executable_non_null_production_or_final_plane"] == (
        "typed_production_state_and_typed_final_seal_allowed"
    )
    assert freeze["current_l4_cleanup_locked_is_not_enforcement"] is True


def test_pydantic_schema_is_strict_at_every_story_object_boundary() -> None:
    schema = LedgerEnvelope.model_json_schema()

    assert schema["additionalProperties"] is False
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False


def test_unknown_story_field_and_unknown_schema_version_fail() -> None:
    body = _valid_body_dict()
    body["lines"][0]["delivery_note"] = "whisper this"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StoryBody.model_validate(body)

    story = _valid_story().model_dump(mode="json")
    story["schema_version"] = "l4-2026-08-07"
    with pytest.raises(ValidationError, match="otr.story_ledger.v2"):
        StoryLedger.model_validate(story)


def test_reordering_an_accepted_story_changes_its_digest() -> None:
    story = _valid_story()
    changed = copy.deepcopy(story.model_dump(mode="json"))
    changed["body"]["sequence"][1], changed["body"]["sequence"][2] = (
        changed["body"]["sequence"][2],
        changed["body"]["sequence"][1],
    )

    assert canonical_sha256(changed) != canonical_sha256(story)
