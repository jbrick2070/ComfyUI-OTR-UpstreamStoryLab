"""Executable Story Ledger v2 contract for the recovery lab.

The Story Lab owns one thing: a validated, hash-sealed authored story.  Media
production may append receipts to a separate production plane, but it may not
rewrite the story plane.  This module intentionally contains no model, audio,
image, video, ComfyUI, or GPU integration.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .production_contract import (
    AcceptanceEvent,
    AttemptEvent,
    PRODUCTION_PHASE_IDS,
    PhaseAcceptance,
    PhaseAttempt,
    ProductionEvent,
    ProductionState,
    RunPhase,
    SucceededResult,
    active_acceptance,
    iter_story_refs,
    production_sha256,
)


ENVELOPE_SCHEMA_VERSION = "otr.ledger_envelope.v2"
STORY_SCHEMA_VERSION = "otr.story_ledger.v2"
STORY_SEAL_SCHEMA_VERSION = "otr.story_seal.v1"
FINAL_SEAL_SCHEMA_VERSION = "otr.final_seal.v1"
CANONICALIZATION_ID = "otr.canonical-json.v1"
MINIMUM_CONTRACT_ID = "otr.minimum_ship.v2"

HEX64_PATTERN = r"^[0-9a-f]{64}$"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"

CastRole = Literal["announcer", "character"]
SpeakerRole = Literal["announcer", "character"]
SequenceRole = Literal[
    "music_open",
    "announcer_open",
    "character_dialogue",
    "music_inter",
    "announcer_news_coda",
    "music_close",
]
SequenceRefKind = Literal["line", "music_cue"]
EvidenceKind = Literal["source_packet", "fact", "line", "music_cue"]
MusicRequestAuthority = Literal["compiler_bookend", "script"]


def _require_non_blank(value: str) -> str:
    if not value.strip():
        raise LedgerContractError("required text cannot be blank")
    return value


NonBlankText = Annotated[str, AfterValidator(_require_non_blank)]


class LedgerContractError(ValueError):
    """The proposed story ledger violates the candidate v2 contract."""


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        revalidate_instances="always",
        validate_assignment=True,
    )


class SourceRecord(StrictModel):
    source_id: str = Field(pattern=ID_PATTERN)
    title: NonBlankText
    locator: NonBlankText
    content_sha256: str = Field(pattern=HEX64_PATTERN)


class FactSourceRef(StrictModel):
    source_id: str = Field(pattern=ID_PATTERN)
    evidence_locator: NonBlankText


class SourceFact(StrictModel):
    fact_id: str = Field(pattern=ID_PATTERN)
    claim: NonBlankText
    source_refs: list[FactSourceRef] = Field(min_length=1)


class SourcePacket(StrictModel):
    packet_id: str = Field(pattern=ID_PATTERN)
    source_bank_id: str = Field(pattern=ID_PATTERN)
    packet_sha256: str = Field(
        pattern=HEX64_PATTERN,
        description=(
            "SHA-256 of the captured upstream packet artifact before this "
            "accepted-story projection; verified by the news-capture validator"
        ),
    )
    sources: list[SourceRecord] = Field(min_length=1)
    facts: list[SourceFact] = Field(min_length=1)


class CastMember(StrictModel):
    char_id: str = Field(pattern=ID_PATTERN)
    name: NonBlankText
    cast_role: CastRole
    character_description: str = ""


class StoryArc(StrictModel):
    summary: NonBlankText
    act_ids: list[str] = Field(min_length=1, max_length=8)


class StoryAct(StrictModel):
    act_id: str = Field(pattern=ID_PATTERN)
    act_number: int = Field(ge=1, le=8, strict=True)
    spine: NonBlankText
    entry_state: NonBlankText
    exit_state: NonBlankText
    speaking_char_ids: list[str] = Field(min_length=1)
    beat_ids: list[str] = Field(min_length=1)


class Scene(StrictModel):
    scene_id: str = Field(pattern=ID_PATTERN)
    description: NonBlankText
    setting: NonBlankText
    time: NonBlankText
    shot_ids: list[str] = Field(min_length=1)


class Shot(StrictModel):
    shot_id: str = Field(pattern=ID_PATTERN)
    scene_id: str = Field(pattern=ID_PATTERN)
    description: NonBlankText
    beat_ids: list[str] = Field(min_length=1)


class Beat(StrictModel):
    beat_id: str = Field(pattern=ID_PATTERN)
    act_id: Annotated[str, Field(pattern=ID_PATTERN)] | None = None
    scene_id: str = Field(pattern=ID_PATTERN)
    shot_id: str = Field(pattern=ID_PATTERN)
    intent: NonBlankText
    line_ids: list[str] = Field(min_length=1)


class SpokenLine(StrictModel):
    line_id: str = Field(pattern=ID_PATTERN)
    scene_id: str = Field(pattern=ID_PATTERN)
    shot_id: str = Field(pattern=ID_PATTERN)
    beat_id: str = Field(pattern=ID_PATTERN)
    char_id: str = Field(pattern=ID_PATTERN)
    speaker: NonBlankText
    speaker_role: SpeakerRole
    text: NonBlankText
    fact_ids: list[str]


class MusicCue(StrictModel):
    cue_id: str = Field(pattern=ID_PATTERN)
    description: NonBlankText
    generation_prompt: NonBlankText
    request_authority: MusicRequestAuthority


class SequenceItem(StrictModel):
    sequence_id: str = Field(pattern=ID_PATTERN)
    sequence_role: SequenceRole
    ref_kind: SequenceRefKind
    ref_id: str = Field(pattern=ID_PATTERN)


class StoryContext(StrictModel):
    episode_title: NonBlankText
    story_seed: NonBlankText
    setting: NonBlankText
    act_count: int = Field(ge=1, le=8, strict=True)


class StoryBody(StrictModel):
    context: StoryContext
    source_packet: SourcePacket
    cast: list[CastMember] = Field(min_length=2)
    story_arc: StoryArc
    acts: list[StoryAct] = Field(min_length=1, max_length=8)
    scenes: list[Scene] = Field(min_length=1)
    shots: list[Shot] = Field(min_length=1)
    beats: list[Beat] = Field(min_length=1)
    lines: list[SpokenLine] = Field(min_length=3)
    music_cues: list[MusicCue] = Field(min_length=2)
    sequence: list[SequenceItem] = Field(min_length=5)

    @model_validator(mode="after")
    def validate_graph_and_program(self) -> "StoryBody":
        def unique(rows: list[Any], attr: str, label: str) -> dict[str, Any]:
            values = [str(getattr(row, attr)) for row in rows]
            if len(values) != len(set(values)):
                raise LedgerContractError(f"{label} IDs must be unique")
            return dict(zip(values, rows, strict=True))

        source_by_id = unique(
            self.source_packet.sources, "source_id", "source"
        )
        fact_by_id = unique(self.source_packet.facts, "fact_id", "fact")
        cast_by_id = unique(self.cast, "char_id", "cast")
        act_by_id = unique(self.acts, "act_id", "act")
        scene_by_id = unique(self.scenes, "scene_id", "scene")
        shot_by_id = unique(self.shots, "shot_id", "shot")
        beat_by_id = unique(self.beats, "beat_id", "beat")
        line_by_id = unique(self.lines, "line_id", "line")
        cue_by_id = unique(self.music_cues, "cue_id", "music cue")
        unique(self.sequence, "sequence_id", "sequence")

        announcers = [row for row in self.cast if row.cast_role == "announcer"]
        if len(announcers) != 1:
            raise LedgerContractError("cast must contain exactly one announcer")
        if not any(row.cast_role == "character" for row in self.cast):
            raise LedgerContractError("cast must contain at least one character")

        if len(self.acts) != self.context.act_count:
            raise LedgerContractError(
                "context.act_count must equal the exact number of acts"
            )
        expected_numbers = list(range(1, self.context.act_count + 1))
        if [act.act_number for act in self.acts] != expected_numbers:
            raise LedgerContractError(
                "act_number values must be the exact ordered range 1..act_count"
            )
        if self.story_arc.act_ids != [act.act_id for act in self.acts]:
            raise LedgerContractError(
                "story_arc.act_ids must exactly match the ordered act table"
            )

        for fact in self.source_packet.facts:
            for ref in fact.source_refs:
                if ref.source_id not in source_by_id:
                    raise LedgerContractError(
                        f"fact {fact.fact_id!r} references unknown source "
                        f"{ref.source_id!r}"
                    )

        referenced_sources = {
            ref.source_id
            for fact in self.source_packet.facts
            for ref in fact.source_refs
        }
        if referenced_sources != set(source_by_id):
            raise LedgerContractError(
                "every source must support at least one accepted fact"
            )

        for scene in self.scenes:
            if len(scene.shot_ids) != len(set(scene.shot_ids)):
                raise LedgerContractError(
                    f"scene {scene.scene_id!r} repeats a shot reference"
                )
            for shot_id in scene.shot_ids:
                shot = shot_by_id.get(shot_id)
                if shot is None or shot.scene_id != scene.scene_id:
                    raise LedgerContractError(
                        f"scene {scene.scene_id!r} has invalid shot {shot_id!r}"
                    )

        for shot in self.shots:
            if shot.scene_id not in scene_by_id:
                raise LedgerContractError(
                    f"shot {shot.shot_id!r} references unknown scene"
                )
            if len(shot.beat_ids) != len(set(shot.beat_ids)):
                raise LedgerContractError(
                    f"shot {shot.shot_id!r} repeats a beat reference"
                )
            for beat_id in shot.beat_ids:
                beat = beat_by_id.get(beat_id)
                if beat is None or beat.shot_id != shot.shot_id:
                    raise LedgerContractError(
                        f"shot {shot.shot_id!r} has invalid beat {beat_id!r}"
                    )

        for beat in self.beats:
            shot = shot_by_id.get(beat.shot_id)
            if shot is None or beat.scene_id != shot.scene_id:
                raise LedgerContractError(
                    f"beat {beat.beat_id!r} has an invalid scene/shot join"
                )
            if len(beat.line_ids) != len(set(beat.line_ids)):
                raise LedgerContractError(
                    f"beat {beat.beat_id!r} repeats a line reference"
                )
            for line_id in beat.line_ids:
                line = line_by_id.get(line_id)
                if line is None or line.beat_id != beat.beat_id:
                    raise LedgerContractError(
                        f"beat {beat.beat_id!r} has invalid line {line_id!r}"
                    )
            if beat.act_id is not None and beat.act_id not in act_by_id:
                raise LedgerContractError(
                    f"beat {beat.beat_id!r} references unknown act"
                )

        for line in self.lines:
            beat = beat_by_id.get(line.beat_id)
            cast_row = cast_by_id.get(line.char_id)
            if beat is None or (
                line.shot_id != beat.shot_id or line.scene_id != beat.scene_id
            ):
                raise LedgerContractError(
                    f"line {line.line_id!r} has an invalid graph join"
                )
            if cast_row is None:
                raise LedgerContractError(
                    f"line {line.line_id!r} references unknown cast"
                )
            if line.speaker != cast_row.name:
                raise LedgerContractError(
                    f"line {line.line_id!r} speaker does not match cast authority"
                )
            if line.speaker_role != cast_row.cast_role:
                raise LedgerContractError(
                    f"line {line.line_id!r} role does not match cast authority"
                )
            unknown_facts = sorted(set(line.fact_ids) - set(fact_by_id))
            if unknown_facts:
                raise LedgerContractError(
                    f"line {line.line_id!r} references unknown facts "
                    f"{unknown_facts}"
                )

        referenced_cast = {line.char_id for line in self.lines}
        if referenced_cast != set(cast_by_id):
            raise LedgerContractError(
                "every cast member must own at least one spoken line"
            )

        declared_act_beats: list[str] = []
        for act in self.acts:
            if len(act.beat_ids) != len(set(act.beat_ids)):
                raise LedgerContractError(
                    f"act {act.act_id!r} repeats a beat reference"
                )
            if len(act.speaking_char_ids) != len(set(act.speaking_char_ids)):
                raise LedgerContractError(
                    f"act {act.act_id!r} repeats a speaking character"
                )
            actual_speakers: list[str] = []
            for beat_id in act.beat_ids:
                beat = beat_by_id.get(beat_id)
                if beat is None or beat.act_id != act.act_id:
                    raise LedgerContractError(
                        f"act {act.act_id!r} has invalid beat {beat_id!r}"
                    )
                for line_id in beat.line_ids:
                    line = line_by_id[line_id]
                    if line.speaker_role != "character":
                        raise LedgerContractError(
                            "act beats may contain only character dialogue"
                        )
                    if line.char_id not in actual_speakers:
                        actual_speakers.append(line.char_id)
            if act.speaking_char_ids != actual_speakers:
                raise LedgerContractError(
                    f"act {act.act_id!r} speaking_char_ids must exactly match "
                    "its dialogue in first-speaking order"
                )
            declared_act_beats.extend(act.beat_ids)

        actual_act_beats = [
            beat.beat_id for beat in self.beats if beat.act_id is not None
        ]
        if declared_act_beats != actual_act_beats:
            raise LedgerContractError(
                "act beat projections must exactly cover the ordered act beats"
            )
        for beat in self.beats:
            if beat.act_id is not None:
                continue
            if any(
                line_by_id[line_id].speaker_role != "announcer"
                for line_id in beat.line_ids
            ):
                raise LedgerContractError(
                    "beats outside acts are reserved for compiler-owned "
                    "announcer bookends"
                )

        sequence_line_ids: list[str] = []
        sequence_cue_ids: list[str] = []
        for item in self.sequence:
            is_music = item.sequence_role.startswith("music_")
            expected_kind = "music_cue" if is_music else "line"
            if item.ref_kind != expected_kind:
                raise LedgerContractError(
                    f"{item.sequence_role} must reference {expected_kind}"
                )
            if item.ref_kind == "line":
                line = line_by_id.get(item.ref_id)
                if line is None:
                    raise LedgerContractError(
                        f"sequence references unknown line {item.ref_id!r}"
                    )
                sequence_line_ids.append(item.ref_id)
                expected_role = (
                    "character"
                    if item.sequence_role == "character_dialogue"
                    else "announcer"
                )
                if line.speaker_role != expected_role:
                    raise LedgerContractError(
                        f"{item.sequence_role} has wrong speech routing role"
                    )
            else:
                cue = cue_by_id.get(item.ref_id)
                if cue is None:
                    raise LedgerContractError(
                        f"sequence references unknown cue {item.ref_id!r}"
                    )
                sequence_cue_ids.append(item.ref_id)
                if (
                    item.sequence_role == "music_inter"
                    and cue.request_authority != "script"
                ):
                    raise LedgerContractError(
                        "music_inter must be explicitly requested by the script"
                    )
                if item.sequence_role in {"music_open", "music_close"} and (
                    cue.request_authority != "compiler_bookend"
                ):
                    raise LedgerContractError(
                        "opening and closing music are compiler-owned bookends"
                    )

        if set(sequence_line_ids) != set(line_by_id) or (
            len(sequence_line_ids) != len(line_by_id)
        ):
            raise LedgerContractError(
                "every spoken line must appear exactly once in sequence"
            )
        if sequence_line_ids != [line.line_id for line in self.lines]:
            raise LedgerContractError(
                "spoken line table order must match the sequence projection"
            )
        if set(sequence_cue_ids) != set(cue_by_id) or (
            len(sequence_cue_ids) != len(cue_by_id)
        ):
            raise LedgerContractError(
                "every music cue must appear exactly once in sequence"
            )
        if sequence_cue_ids != [cue.cue_id for cue in self.music_cues]:
            raise LedgerContractError(
                "music cue table order must match the sequence projection"
            )

        roles = [item.sequence_role for item in self.sequence]
        if roles[0] != "music_open" or roles[-1] != "music_close":
            raise LedgerContractError("music_open/music_close must bookend sequence")
        for required in (
            "music_open",
            "announcer_open",
            "announcer_news_coda",
            "music_close",
        ):
            if roles.count(required) != 1:
                raise LedgerContractError(
                    f"sequence must contain exactly one {required}"
                )
        if roles.count("character_dialogue") < 1:
            raise LedgerContractError(
                "sequence must contain character dialogue"
            )

        spoken = [item for item in self.sequence if item.ref_kind == "line"]
        if spoken[0].sequence_role != "announcer_open":
            raise LedgerContractError("first spoken row must be announcer_open")
        if spoken[-1].sequence_role != "announcer_news_coda":
            raise LedgerContractError(
                "last spoken row must be announcer_news_coda"
            )
        coda = line_by_id[spoken[-1].ref_id]
        if not coda.fact_ids:
            raise LedgerContractError(
                "announcer_news_coda must reference at least one source fact"
            )
        referenced_facts = {
            fact_id for line in self.lines for fact_id in line.fact_ids
        }
        if referenced_facts != set(fact_by_id):
            raise LedgerContractError(
                "every accepted fact must be cited by at least one spoken line"
            )
        first_character = roles.index("character_dialogue")
        coda_index = roles.index("announcer_news_coda")
        if first_character >= coda_index:
            raise LedgerContractError("character dialogue must precede the coda")
        for index, role in enumerate(roles):
            if role == "music_inter" and not (first_character < index < coda_index):
                raise LedgerContractError(
                    "music_inter must occur within the character-story body"
                )

        ordered_shots = [shot_id for scene in self.scenes for shot_id in scene.shot_ids]
        ordered_beats = [beat_id for shot in self.shots for beat_id in shot.beat_ids]
        ordered_lines = [line_id for beat in self.beats for line_id in beat.line_ids]
        if set(ordered_shots) != set(shot_by_id):
            raise LedgerContractError("every shot must belong to exactly one scene")
        if set(ordered_beats) != set(beat_by_id):
            raise LedgerContractError("every beat must belong to exactly one shot")
        if set(ordered_lines) != set(line_by_id):
            raise LedgerContractError("every line must belong to exactly one beat")
        if ordered_shots != [shot.shot_id for shot in self.shots]:
            raise LedgerContractError(
                "shot table order must match the scene child projection"
            )
        if ordered_beats != [beat.beat_id for beat in self.beats]:
            raise LedgerContractError(
                "beat table order must match the shot child projection"
            )
        if ordered_lines != [line.line_id for line in self.lines]:
            raise LedgerContractError(
                "line table order must match the beat child projection"
            )
        return self


class EvidenceRef(StrictModel):
    kind: EvidenceKind
    ref_id: str = Field(pattern=ID_PATTERN)


class OutcomeReceipt(StrictModel):
    status: Literal["pass"] = "pass"
    validator_id: str = Field(pattern=ID_PATTERN)
    validator_version: NonBlankText
    evidence_refs: list[EvidenceRef]


class MinimumOutcomes(StrictModel):
    ledger_integrity: OutcomeReceipt
    news_capture: OutcomeReceipt
    announcer_open: OutcomeReceipt
    announcer_news_coda: OutcomeReceipt
    music_bookends: OutcomeReceipt


class StoryValidation(StrictModel):
    body_sha256: str = Field(pattern=HEX64_PATTERN)
    contract_id: Literal[MINIMUM_CONTRACT_ID] = MINIMUM_CONTRACT_ID
    outcomes: MinimumOutcomes


class StoryLedger(StrictModel):
    schema_version: Literal[STORY_SCHEMA_VERSION] = STORY_SCHEMA_VERSION
    episode_id: str = Field(pattern=ID_PATTERN)
    body: StoryBody
    validation: StoryValidation

    @model_validator(mode="after")
    def validate_receipt_binding(self) -> "StoryLedger":
        actual = canonical_sha256(self.body)
        if self.validation.body_sha256 != actual:
            raise LedgerContractError(
                "validation.body_sha256 does not bind the exact story body"
            )
        known_refs = {
            "source_packet": {self.body.source_packet.packet_id},
            "fact": {row.fact_id for row in self.body.source_packet.facts},
            "line": {row.line_id for row in self.body.lines},
            "music_cue": {row.cue_id for row in self.body.music_cues},
        }
        for name, receipt in self.validation.outcomes:
            typed_refs = [(ref.kind, ref.ref_id) for ref in receipt.evidence_refs]
            if len(typed_refs) != len(set(typed_refs)):
                raise LedgerContractError(
                    f"outcome {name!r} repeats an evidence reference"
                )
            unknown = sorted(
                (ref.kind, ref.ref_id)
                for ref in receipt.evidence_refs
                if ref.ref_id not in known_refs[ref.kind]
            )
            if unknown:
                raise LedgerContractError(
                    f"outcome {name!r} has unknown evidence refs {unknown}"
                )

        open_item = next(
            item
            for item in self.body.sequence
            if item.sequence_role == "announcer_open"
        )
        coda_item = next(
            item
            for item in self.body.sequence
            if item.sequence_role == "announcer_news_coda"
        )
        open_cue = next(
            item for item in self.body.sequence if item.sequence_role == "music_open"
        )
        close_cue = next(
            item for item in self.body.sequence if item.sequence_role == "music_close"
        )
        coda_line = next(
            line for line in self.body.lines if line.line_id == coda_item.ref_id
        )
        facts = {fact.fact_id for fact in self.body.source_packet.facts}
        evidence = {
            name: {(ref.kind, ref.ref_id) for ref in receipt.evidence_refs}
            for name, receipt in self.validation.outcomes
        }
        if (
            "source_packet",
            self.body.source_packet.packet_id,
        ) not in evidence["news_capture"] or not (
            evidence["news_capture"] & {("fact", fact_id) for fact_id in facts}
        ):
            raise LedgerContractError(
                "news_capture evidence must name the source packet and a fact"
            )
        if ("line", open_item.ref_id) not in evidence["announcer_open"]:
            raise LedgerContractError(
                "announcer_open evidence must name the exact opening line"
            )
        if ("line", coda_item.ref_id) not in evidence[
            "announcer_news_coda"
        ] or not (
            evidence["announcer_news_coda"]
            & {("fact", fact_id) for fact_id in coda_line.fact_ids}
        ):
            raise LedgerContractError(
                "announcer_news_coda evidence must name the coda line and its fact"
            )
        if not {
            ("music_cue", open_cue.ref_id),
            ("music_cue", close_cue.ref_id),
        }.issubset(
            evidence["music_bookends"]
        ):
            raise LedgerContractError(
                "music_bookends evidence must name the exact opening and closing cues"
            )
        return self


class StorySeal(StrictModel):
    schema_version: Literal[STORY_SEAL_SCHEMA_VERSION] = STORY_SEAL_SCHEMA_VERSION
    algorithm: Literal["sha256"] = "sha256"
    canonicalization: Literal[CANONICALIZATION_ID] = CANONICALIZATION_ID
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    sealed_at: datetime

    @field_validator("sealed_at")
    @classmethod
    def validate_sealed_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise LedgerContractError("story seal time must be timezone-aware UTC")
        return value


class FinalSeal(StrictModel):
    """Terminal, non-recursive digest over the complete accepted envelope."""

    schema_version: Literal[FINAL_SEAL_SCHEMA_VERSION] = FINAL_SEAL_SCHEMA_VERSION
    algorithm: Literal["sha256"] = "sha256"
    canonicalization: Literal[CANONICALIZATION_ID] = CANONICALIZATION_ID
    episode_id: str = Field(pattern=ID_PATTERN)
    run_id: str = Field(pattern=ID_PATTERN)
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    production_state_sha256: str = Field(pattern=HEX64_PATTERN)
    sealed_at: datetime
    final_payload_sha256: str = Field(pattern=HEX64_PATTERN)

    @field_validator("sealed_at")
    @classmethod
    def validate_sealed_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise LedgerContractError("final seal time must be timezone-aware UTC")
        return value


class LedgerEnvelope(StrictModel):
    schema_version: Literal[ENVELOPE_SCHEMA_VERSION] = ENVELOPE_SCHEMA_VERSION
    story_ledger: StoryLedger
    story_seal: StorySeal
    production_state: ProductionState | None = None
    final_seal: FinalSeal | None = None

    @model_validator(mode="after")
    def validate_story_seal(self) -> "LedgerEnvelope":
        actual = canonical_sha256(self.story_ledger)
        if self.story_seal.story_sha256 != actual:
            raise LedgerContractError(
                "story_seal does not bind the exact story_ledger"
            )
        if self.production_state is not None:
            self._validate_production_bindings()
        if self.final_seal is not None:
            self._validate_final_seal_bindings()
        return self

    def _validate_production_bindings(self) -> None:
        state = self.production_state
        if state is None:
            return
        if state.episode_id != self.story_ledger.episode_id:
            raise LedgerContractError(
                "production_state does not bind story_ledger.episode_id"
            )
        if state.story_sha256 != self.story_seal.story_sha256:
            raise LedgerContractError(
                "production_state does not bind story_seal.story_sha256"
            )

        body = self.story_ledger.body
        namespaces = {
            "source_packet": {body.source_packet.packet_id},
            "source": {row.source_id for row in body.source_packet.sources},
            "fact": {row.fact_id for row in body.source_packet.facts},
            "cast": {row.char_id for row in body.cast},
            "act": {row.act_id for row in body.acts},
            "scene": {row.scene_id for row in body.scenes},
            "shot": {row.shot_id for row in body.shots},
            "beat": {row.beat_id for row in body.beats},
            "line": {row.line_id for row in body.lines},
            "music_cue": {row.cue_id for row in body.music_cues},
            "sequence": {row.sequence_id for row in body.sequence},
        }
        for ref in iter_story_refs(state):
            if ref.ref_id not in namespaces[ref.kind]:
                raise LedgerContractError(
                    f"production {ref.kind!r} reference {ref.ref_id!r} does not "
                    "resolve into the sealed story"
                )

        required_coverage = {
            "cast_routing": ("cast", namespaces["cast"]),
            "voice_render": ("line", namespaces["line"]),
            "music_render": ("music_cue", namespaces["music_cue"]),
            "speech_timeline": ("sequence", namespaces["sequence"]),
        }
        for event in state.journal:
            if not isinstance(event, AttemptEvent):
                continue
            attempt = event.attempt
            if not isinstance(attempt.result, SucceededResult):
                continue
            coverage = required_coverage.get(attempt.phase_id)
            if coverage is None:
                if attempt.phase_id == "audit":
                    receipt = attempt.result.receipt
                    if receipt.story_sha256 != self.story_seal.story_sha256:
                        raise LedgerContractError(
                            "audit receipt does not bind the sealed story"
                        )
                continue
            kind, expected_ids = coverage
            receipt_refs = [
                ref.ref_id
                for ref in iter_story_refs(attempt.result.receipt)
                if ref.kind == kind
            ]
            if len(receipt_refs) != len(set(receipt_refs)):
                raise LedgerContractError(
                    f"{attempt.phase_id} receipt contains duplicate {kind} coverage"
                )
            if set(receipt_refs) != expected_ids:
                raise LedgerContractError(
                    f"{attempt.phase_id} succeeded receipt must cover every {kind}"
                )

    def _validate_final_seal_bindings(self) -> None:
        seal = self.final_seal
        state = self.production_state
        if seal is None:
            return
        if state is None:
            raise LedgerContractError("final_seal requires production_state")
        if seal.episode_id != self.story_ledger.episode_id:
            raise LedgerContractError("final_seal does not bind the exact episode_id")
        if seal.run_id != state.run_id:
            raise LedgerContractError("final_seal does not bind the exact run_id")
        if seal.story_sha256 != self.story_seal.story_sha256:
            raise LedgerContractError("final_seal does not bind story_sha256")
        if seal.production_state_sha256 != production_sha256(state):
            raise LedgerContractError(
                "final_seal does not bind the complete production_state"
            )
        _assert_terminal_production_ready(state, sealed_at=seal.sealed_at)
        if seal.final_payload_sha256 != _final_payload_sha256(self, seal):
            raise LedgerContractError(
                "final_seal does not bind the non-recursive final payload"
            )


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _assert_canonical_value(value: Any, path: str = "$") -> None:
    """Reject values our deliberately small canonical-json-v1 cannot encode."""

    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise LedgerContractError(f"non-NFC string at {path}")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        raise LedgerContractError(
            f"floating point is outside story canonical-json-v1 at {path}"
        )
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_canonical_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LedgerContractError(f"non-string object key at {path}")
            _assert_canonical_value(key, f"{path}.<key>")
            _assert_canonical_value(item, f"{path}.{key}")
        return
    raise LedgerContractError(
        f"unsupported canonical value {type(value).__name__} at {path}"
    )


def canonical_bytes(value: Any) -> bytes:
    """Return the exact UTF-8 bytes for ``otr.canonical-json.v1``.

    Story v2 deliberately excludes floats. Combined with NFC strings, strict
    models, sorted keys, compact separators, and ``allow_nan=False``, this gives
    the lab and production adapter a small reproducible cross-process surface.
    A future canonicalization algorithm is a schema migration, never a silent
    change to existing seals.
    """

    plain = _plain(value)
    _assert_canonical_value(plain)
    return json.dumps(
        plain,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _final_payload_sha256(
    envelope: LedgerEnvelope,
    seal: FinalSeal | Mapping[str, Any],
) -> str:
    """Hash the terminal envelope with only its digest field omitted.

    Including the other final-seal metadata binds the seal time and identities;
    omitting ``final_payload_sha256`` itself keeps the preimage non-recursive.
    """

    if isinstance(seal, FinalSeal):
        seal_metadata = seal.model_dump(
            mode="json",
            exclude={"final_payload_sha256"},
        )
    else:
        seal_metadata = dict(seal)
        sealed_at = seal_metadata.get("sealed_at")
        if isinstance(sealed_at, datetime):
            seal_metadata["sealed_at"] = sealed_at.isoformat().replace(
                "+00:00", "Z"
            )
    preimage = {
        "schema_version": envelope.schema_version,
        "story_ledger": envelope.story_ledger.model_dump(mode="json"),
        "story_seal": envelope.story_seal.model_dump(mode="json"),
        "production_state": (
            envelope.production_state.model_dump(mode="json")
            if envelope.production_state is not None
            else None
        ),
        "final_seal": seal_metadata,
    }
    return canonical_sha256(preimage)


def _assert_terminal_production_ready(
    state: ProductionState,
    *,
    sealed_at: datetime,
) -> None:
    """Fail closed unless ``state`` ends at one accepted terminal audit."""

    if sealed_at.tzinfo is None or sealed_at.utcoffset() != timedelta(0):
        raise LedgerContractError("final seal time must be timezone-aware UTC")

    attempts: dict[str, PhaseAttempt] = {}
    attempt_indices: dict[str, int] = {}
    latest_acceptances: dict[str, PhaseAcceptance] = {}
    acceptance_indices: dict[str, int] = {}
    for index, event in enumerate(state.journal):
        if isinstance(event, AttemptEvent):
            attempts[event.attempt.attempt_id] = event.attempt
            attempt_indices[event.attempt.attempt_id] = index
        else:
            acceptance = event.acceptance
            latest_acceptances[acceptance.phase_id] = acceptance
            acceptance_indices[acceptance.acceptance_id] = index

    active: dict[str, PhaseAcceptance] = {}
    for phase_id in PRODUCTION_PHASE_IDS:
        acceptance = active_acceptance(state, phase_id)
        if acceptance is not None:
            active[phase_id] = acceptance

    for phase_id, latest in latest_acceptances.items():
        current = active.get(phase_id)
        if current is None or current.acceptance_id != latest.acceptance_id:
            raise LedgerContractError(
                f"phase {phase_id!r} has a stale accepted dependency"
            )

    for row in state.run_plan:
        if row.disposition != "required":
            continue
        acceptance = active.get(row.phase_id)
        if acceptance is None:
            raise LedgerContractError(
                f"required phase {row.phase_id!r} has no active acceptance"
            )
        attempt = attempts[acceptance.accepted_attempt_id]
        if not isinstance(attempt.result, SucceededResult):
            raise LedgerContractError(
                f"required phase {row.phase_id!r} did not accept a succeeded attempt"
            )

    publication = active.get("publication")
    audit = active.get("audit")
    if publication is None:
        raise LedgerContractError(
            "final_seal requires an active publication acceptance"
        )
    if audit is None:
        raise LedgerContractError("final_seal requires an active audit acceptance")

    audit_attempt = attempts[audit.accepted_attempt_id]
    publication_index = acceptance_indices[publication.acceptance_id]
    audit_attempt_index = attempt_indices[audit_attempt.attempt_id]
    audit_index = acceptance_indices[audit.acceptance_id]
    if not publication_index < audit_attempt_index < audit_index:
        raise LedgerContractError(
            "publication must be accepted before the terminal audit"
        )
    if audit_index != len(state.journal) - 1:
        raise LedgerContractError(
            "the active audit acceptance must be the terminal production event"
        )
    if sealed_at < audit.accepted_at:
        raise LedgerContractError(
            "final seal time cannot precede the terminal audit acceptance"
        )

    if not isinstance(audit_attempt.result, SucceededResult):
        raise LedgerContractError("terminal audit attempt did not succeed")
    receipt = audit_attempt.result.receipt
    if receipt.publication_acceptance_id != publication.acceptance_id:
        raise LedgerContractError(
            "terminal audit does not bind the active publication acceptance"
        )
    if any(check.status != "pass" for check in receipt.checks):
        raise LedgerContractError("terminal audit contains a failed check")

    prefix_payload = state.model_dump(mode="json")
    prefix_payload["journal"] = prefix_payload["journal"][:audit_attempt_index]
    pre_audit_state = ProductionState.model_validate(prefix_payload)
    if receipt.pre_audit_production_sha256 != production_sha256(pre_audit_state):
        raise LedgerContractError(
            "terminal audit does not bind the exact pre-audit production_state"
        )


ReceiptVerifier = Callable[[StoryBody, OutcomeReceipt], bool]
ReceiptVerifierKey = tuple[str, str, str]


def verify_story_acceptance(
    story_ledger: StoryLedger,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> StoryLedger:
    """Revalidate a story and run the code-owned receipt-verifier registry.

    Receipt JSON is evidence, not trust.  The caller owns the trusted registry;
    an unknown validator identity or a verifier miss fails closed.  This keeps a
    caller-authored ``status=pass`` from becoming a seal by assertion alone.
    """

    validated = StoryLedger.model_validate(story_ledger.model_dump(mode="json"))
    for outcome_name, receipt in validated.validation.outcomes:
        key = (outcome_name, receipt.validator_id, receipt.validator_version)
        verifier = receipt_verifiers.get(key)
        if verifier is None:
            raise LedgerContractError(
                f"outcome {outcome_name!r} has no trusted receipt verifier"
            )
        verifier_body = validated.body.model_copy(deep=True)
        verifier_receipt = receipt.model_copy(deep=True)
        before_body = canonical_bytes(verifier_body)
        before_receipt = canonical_bytes(verifier_receipt)
        try:
            accepted = verifier(verifier_body, verifier_receipt)
        except Exception as exc:
            raise LedgerContractError(
                f"outcome {outcome_name!r} verifier raised {type(exc).__name__}"
            ) from exc
        if (
            canonical_bytes(verifier_body) != before_body
            or canonical_bytes(verifier_receipt) != before_receipt
        ):
            raise LedgerContractError(
                f"outcome {outcome_name!r} verifier mutated its sealed input"
            )
        if accepted is not True:
            raise LedgerContractError(
                f"outcome {outcome_name!r} failed trusted receipt verification"
            )
    return validated


def build_story_seal(
    story_ledger: StoryLedger,
    *,
    sealed_at: datetime,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> StorySeal:
    validated = verify_story_acceptance(
        story_ledger,
        receipt_verifiers=receipt_verifiers,
    )
    return StorySeal(
        story_sha256=canonical_sha256(validated),
        sealed_at=sealed_at,
    )


def verify_story_envelope(
    envelope: LedgerEnvelope,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Trusted Story Lab admission; structural parsing alone is not acceptance."""

    validated = LedgerEnvelope.model_validate(envelope.model_dump(mode="json"))
    verify_story_acceptance(
        validated.story_ledger,
        receipt_verifiers=receipt_verifiers,
    )
    return validated


def verify_final_seal(
    envelope: LedgerEnvelope,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Freshly verify story trust, terminal ordering, and every final digest."""

    validated = verify_story_envelope(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if validated.final_seal is None:
        raise LedgerContractError("final_seal is not minted")
    validated._validate_final_seal_bindings()
    return validated


def mint_final_seal(
    envelope: LedgerEnvelope,
    *,
    sealed_at: datetime,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Return a newly terminal envelope without mutating the accepted input."""

    before = verify_story_envelope(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if before.final_seal is not None:
        raise LedgerContractError("final_seal is already minted")
    state = before.production_state
    if state is None:
        raise LedgerContractError("final_seal requires production_state")
    _assert_terminal_production_ready(state, sealed_at=sealed_at)

    metadata: dict[str, Any] = {
        "schema_version": FINAL_SEAL_SCHEMA_VERSION,
        "algorithm": "sha256",
        "canonicalization": CANONICALIZATION_ID,
        "episode_id": before.story_ledger.episode_id,
        "run_id": state.run_id,
        "story_sha256": before.story_seal.story_sha256,
        "production_state_sha256": production_sha256(state),
        "sealed_at": sealed_at,
    }
    seal = FinalSeal(
        **metadata,
        final_payload_sha256=_final_payload_sha256(before, metadata),
    )
    payload = before.model_dump(mode="json")
    payload["final_seal"] = seal.model_dump(mode="json")
    after = LedgerEnvelope.model_validate(payload)
    return verify_final_seal(after, receipt_verifiers=receipt_verifiers)


def assert_story_unchanged(before: LedgerEnvelope, after: LedgerEnvelope) -> None:
    """Guard a production extension: the story bytes and digest cannot move."""

    if canonical_bytes(before.story_ledger) != canonical_bytes(after.story_ledger):
        raise LedgerContractError("production extension mutated story_ledger")
    if canonical_bytes(before.story_seal) != canonical_bytes(after.story_seal):
        raise LedgerContractError("production extension mutated story_seal")


def assert_production_append_only(
    before: LedgerEnvelope, after: LedgerEnvelope
) -> None:
    """Prove that one legal production event extended an unchanged envelope."""

    assert_story_unchanged(before, after)
    if before.final_seal is not None or after.final_seal is not None:
        raise LedgerContractError("production extension after final_seal is forbidden")
    old_state = before.production_state
    new_state = after.production_state
    if old_state is None:
        if new_state is None or new_state.journal:
            raise LedgerContractError(
                "production initialization must create an empty typed journal"
            )
        return
    if new_state is None:
        raise LedgerContractError("production_state cannot be removed")
    old_root = old_state.model_dump(mode="json", exclude={"journal"})
    new_root = new_state.model_dump(mode="json", exclude={"journal"})
    if canonical_bytes(old_root) != canonical_bytes(new_root):
        raise LedgerContractError("production root or run plan was rewritten")
    old_events = [canonical_bytes(event) for event in old_state.journal]
    new_events = [canonical_bytes(event) for event in new_state.journal]
    if len(new_events) != len(old_events) + 1:
        raise LedgerContractError("production extension must append exactly one event")
    if new_events[: len(old_events)] != old_events:
        raise LedgerContractError("production journal history is not an exact prefix")


def initialize_production_state(
    envelope: LedgerEnvelope,
    *,
    run_id: str,
    created_at: datetime,
    run_plan: list[RunPhase],
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Attach an empty, story-bound production journal atomically."""

    before = verify_story_envelope(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if before.final_seal is not None:
        raise LedgerContractError("production initialization after final_seal is forbidden")
    if before.production_state is not None:
        raise LedgerContractError("production_state is already initialized")
    state = ProductionState(
        episode_id=before.story_ledger.episode_id,
        run_id=run_id,
        story_sha256=before.story_seal.story_sha256,
        created_at=created_at,
        run_plan=run_plan,
        journal=[],
    )
    payload = before.model_dump(mode="json")
    payload["production_state"] = state.model_dump(mode="json")
    after = LedgerEnvelope.model_validate(payload)
    verify_story_envelope(after, receipt_verifiers=receipt_verifiers)
    assert_production_append_only(before, after)
    return after


def _append_production_event(
    envelope: LedgerEnvelope,
    event: ProductionEvent,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    before = verify_story_envelope(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if before.final_seal is not None:
        raise LedgerContractError("production append after final_seal is forbidden")
    if before.production_state is None:
        raise LedgerContractError("production_state is not initialized")
    payload = before.model_dump(mode="json")
    payload["production_state"]["journal"].append(event.model_dump(mode="json"))
    after = LedgerEnvelope.model_validate(payload)
    verify_story_envelope(after, receipt_verifiers=receipt_verifiers)
    assert_production_append_only(before, after)
    return after


def append_production_attempt(
    envelope: LedgerEnvelope,
    attempt: PhaseAttempt,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Return a new envelope with one immutable completed attempt appended."""

    event = AttemptEvent(attempt=attempt)
    return _append_production_event(
        envelope,
        event,
        receipt_verifiers=receipt_verifiers,
    )


def accept_production_attempt(
    envelope: LedgerEnvelope,
    acceptance: PhaseAcceptance,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> LedgerEnvelope:
    """Append an acceptance event; prior attempts and acceptances stay intact."""

    event = AcceptanceEvent(acceptance=acceptance)
    return _append_production_event(
        envelope,
        event,
        receipt_verifiers=receipt_verifiers,
    )


def verify_production_state(
    envelope: LedgerEnvelope,
    *,
    receipt_verifiers: Mapping[ReceiptVerifierKey, ReceiptVerifier],
) -> ProductionState:
    """Freshly validate both story trust and the complete production journal."""

    validated = verify_story_envelope(
        envelope,
        receipt_verifiers=receipt_verifiers,
    )
    if validated.production_state is None:
        raise LedgerContractError("production_state is not initialized")
    return validated.production_state


__all__ = [
    "CANONICALIZATION_ID",
    "ENVELOPE_SCHEMA_VERSION",
    "FINAL_SEAL_SCHEMA_VERSION",
    "FinalSeal",
    "LedgerContractError",
    "LedgerEnvelope",
    "MINIMUM_CONTRACT_ID",
    "OutcomeReceipt",
    "ReceiptVerifier",
    "ReceiptVerifierKey",
    "STORY_SCHEMA_VERSION",
    "STORY_SEAL_SCHEMA_VERSION",
    "StoryAct",
    "StoryArc",
    "StoryBody",
    "StoryLedger",
    "StorySeal",
    "accept_production_attempt",
    "append_production_attempt",
    "assert_production_append_only",
    "assert_story_unchanged",
    "build_story_seal",
    "canonical_bytes",
    "canonical_sha256",
    "initialize_production_state",
    "mint_final_seal",
    "verify_final_seal",
    "verify_story_acceptance",
    "verify_story_envelope",
    "verify_production_state",
]
