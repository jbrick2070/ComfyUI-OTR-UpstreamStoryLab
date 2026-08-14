"""Provider-neutral staged authoring executor over the locked act schedule.

This module turns the canonical authoring schedule from
:mod:`upstream_story_lab.story_authoring` into one accepted, sealed Story
Ledger v2 envelope.  Model jobs run through an injected provider; compiler and
admission jobs are code-owned.  A rejected draft retries only its owning job
with explicit feedback, and admission never repairs accepted bytes.

The executor adds no acceptance authority of its own.  Story acceptance
remains the code-owned verifier registry, the story seal, and the strict
save/load path.  There is no word-count target or gate anywhere on this path;
the only visible length input is the schedule's strict ``act_count``.  Beat
and exchange counts appear only as soft per-bank guidance inside prompts.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from .ledger_contract import (
    ID_PATTERN,
    Beat,
    CastMember,
    EvidenceRef,
    LedgerEnvelope,
    MinimumOutcomes,
    MusicCue,
    NonBlankText,
    OutcomeReceipt,
    Scene,
    SequenceItem,
    Shot,
    SourcePacket,
    SpokenLine,
    StoryAct,
    StoryArc,
    StoryBody,
    StoryContext,
    StoryLedger,
    StoryValidation,
    build_story_seal,
    canonical_bytes,
    canonical_sha256,
    verify_story_envelope,
)
from .ledger_io import load_ledger_envelope, save_ledger_envelope
from .ledger_verifiers import (
    CapturedSourcePacketArtifact,
    LEDGER_INTEGRITY_ADAPTATION_VALIDATOR_VERSION,
    TRUSTED_VALIDATOR_IDENTITIES,
    _contains_normalized_phrase,
    _normalized_words,
    build_trusted_receipt_verifiers,
)
from .source_window import (
    MAX_BLOCK_CHARS,
    LabSourceDocument,
    render_source_block,
    select_act_window,
)
from .spoken_text_policy import (
    # The blind-cast guard below must ask the detector itself which names it
    # can still recognize; re-deriving that logic here would let the two drift
    # apart and silently reopen the hole.
    _unique_name_variants,
    audit_spoken_text,
)
from .story_authoring import (
    AuthoringJob,
    JobExecutor,
    JobKind,
    _draft_role,
    build_authoring_schedule,
    make_authoring_attempt,
    sanitize_draft_sequence,
    sweep_cast_after_dialogue,
)


class AuthoringExecutionError(ValueError):
    """A staged authoring run could not produce an admissible story."""


class StrictExecutorModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
    )


class StagedAuthoringGuidance(StrictExecutorModel):
    """Soft per-bank shaping for beats and exchanges.

    ``authority`` is pinned to ``guidance`` because these numbers may steer a
    prompt but may never become an admission gate: the ledger deliberately has
    no count-based acceptance law.
    """

    authority: Literal["guidance"] = "guidance"
    beats_per_act_low: int = Field(default=5, strict=True, ge=1)
    beats_per_act_high: int = Field(default=7, strict=True, ge=1)
    exchanges_per_beat_low: int = Field(default=2, strict=True, ge=1)
    exchanges_per_beat_high: int = Field(default=4, strict=True, ge=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> "StagedAuthoringGuidance":
        if self.beats_per_act_low > self.beats_per_act_high:
            raise AuthoringExecutionError(
                "beats_per_act_low cannot exceed beats_per_act_high"
            )
        if self.exchanges_per_beat_low > self.exchanges_per_beat_high:
            raise AuthoringExecutionError(
                "exchanges_per_beat_low cannot exceed exchanges_per_beat_high"
            )
        return self


#: Rapid-fire testing preset: the smallest complete drama shape. Still
#: guidance only - it steers prompts and never gates admission.
ULTRASHORT_GUIDANCE = StagedAuthoringGuidance(
    beats_per_act_low=2,
    beats_per_act_high=2,
    exchanges_per_beat_low=2,
    exchanges_per_beat_high=2,
)


class AuthoringBrief(StrictExecutorModel):
    """Everything one staged authoring run needs besides the model provider."""

    episode_id: str = Field(pattern=ID_PATTERN)
    setting: NonBlankText
    scene_time: NonBlankText
    act_count: int = Field(strict=True, ge=1, le=8)
    cast: tuple[CastMember, ...] = Field(min_length=2)
    source_packet_bytes: bytes
    #: Adaptation lanes only.  When present, each act grounds on its own
    #: frozen window of this body, and literally carried words are exempt from
    #: the heuristic spoken-text findings.  Absent on original-drama lanes,
    #: which keep full v1 strictness.
    source_document: Any | None = None
    #: Speech prefixes printed by the source (Folger provenance records them).
    #: Handed to the cleanup pass as context so a model can strip a leaked
    #: label; never used as a Python rejection rule.
    source_speaker_labels: tuple[str, ...] = ()
    #: Bound on the source text carried in one prompt, so a small local model
    #: can hold it.  ``None`` hands over the act's whole window.
    source_window_max_chars: int | None = Field(
        default=MAX_BLOCK_CHARS, strict=True
    )
    #: This bank's own direction per job, from the resolved pack's
    #: ``job_prompts``.  Creative voice belongs to the bank; the shared
    #: instructions above it stay identical for every bank.
    bank_job_prompts: dict[str, str] = Field(default_factory=dict)
    guidance: StagedAuthoringGuidance = Field(
        default_factory=StagedAuthoringGuidance
    )
    max_attempts_per_job: int = Field(default=3, strict=True, ge=1, le=10)

    @model_validator(mode="after")
    def validate_locked_cast(self) -> "AuthoringBrief":
        char_ids = [row.char_id for row in self.cast]
        if len(char_ids) != len(set(char_ids)):
            raise AuthoringExecutionError("locked cast char_ids must be unique")
        announcers = [row for row in self.cast if row.cast_role == "announcer"]
        characters = [row for row in self.cast if row.cast_role == "character"]
        if len(announcers) != 1:
            raise AuthoringExecutionError(
                "locked cast requires exactly one announcer"
            )
        if not characters:
            raise AuthoringExecutionError(
                "locked cast requires at least one character"
            )

        # A cast whose names share a variant blinds the narration detector.
        # "MR. DARCY" also answers to "DARCY", so pairing it with a separate
        # "DARCY" makes the policy drop that variant from both rows and stop
        # recognizing either name.  Narrated prose then passes every gate and
        # seals into the ledger, which is precisely the defect the spoken-only
        # law exists to stop.  Refuse the cast instead of authoring blind.
        blind = [
            row.name
            for row, variants in zip(
                self.cast,
                _unique_name_variants(
                    {row.char_id: row.name for row in self.cast}
                ).values(),
                strict=True,
            )
            if not variants
        ]
        if blind:
            raise AuthoringExecutionError(
                f"locked cast names {blind} share a name variant with another "
                "cast row, which blinds the narration detector for them; "
                "rename one of the rows"
            )

        for label, value in (
            ("setting", self.setting),
            ("scene_time", self.scene_time),
            *[(f"cast name {row.char_id}", row.name) for row in self.cast],
            *[
                (f"cast description {row.char_id}", row.character_description)
                for row in self.cast
            ],
        ):
            # Canonical story bytes must already be NFC; a composed string
            # would only fail at the seal, after the whole schedule is paid for.
            if unicodedata.normalize("NFC", value) != value:
                raise AuthoringExecutionError(
                    f"{label} must already be Unicode NFC; the story seal "
                    "rejects composed strings"
                )

        # The opening validator proves the announcer literally named the
        # setting, time, and every character.  A value with no word tokens can
        # never satisfy that, so the announcer job would burn every attempt.
        for label, value in (
            ("setting", self.setting),
            ("scene_time", self.scene_time),
            *[
                (f"cast name {row.char_id}", row.name)
                for row in self.cast
                if row.cast_role == "character"
            ],
        ):
            if not _normalized_words(value):
                raise AuthoringExecutionError(
                    f"{label} has no pronounceable word the announcer opening "
                    "could name"
                )

        if self.source_document is not None and not isinstance(
            self.source_document, LabSourceDocument
        ):
            raise AuthoringExecutionError(
                "source_document must be a LabSourceDocument"
            )
        return self


class DecodeGuard(StrictExecutorModel):
    """Provider-facing anti-runaway decode hints for one job.

    Runaway guards, not content targets: a generous per-job output budget and
    a gentle repetition penalty (production doctrine: 1.03 gentle, clamp at
    1.2, 1.0 disables) so a looping decoder cannot burn the context.
    """

    max_new_tokens: int = Field(strict=True, ge=1)
    recommended_repetition_penalty: float = 1.03
    repetition_penalty_ceiling: float = 1.2


_DECODE_TOKEN_BUDGETS: dict[str, int] = {
    "story_seed": 400,
    "story_arc": 900,
    "act_spine": 600,
    "act_beats": 800,
    "act_dialogue": 2400,
    "act_cleanup": 2400,
    "announcer_open": 500,
    "announcer_news_coda": 500,
}


class ModelJobRequest(StrictExecutorModel):
    """One provider call: a schedule attempt plus its complete context."""

    attempt_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    kind: JobKind
    act_number: int | None = Field(default=None, strict=True, ge=1, le=8)
    attempt_number: int = Field(strict=True, ge=1)
    instructions: tuple[str, ...]
    context: dict[str, Any]
    feedback: tuple[str, ...] = ()
    prompt: str = Field(min_length=1)
    decode_guard: DecodeGuard


class StagedModelProvider(Protocol):
    """A model route that answers one authoring job with a JSON object.

    Transport-level retries (timeouts, connection errors) belong inside the
    provider; the executor only retries content that failed acceptance.
    """

    def run_job(self, request: ModelJobRequest) -> Mapping[str, Any]: ...


class AttemptRecord(StrictExecutorModel):
    attempt_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    kind: JobKind
    executor: JobExecutor
    attempt_number: int = Field(strict=True, ge=1)
    status: Literal["accepted", "rejected"]
    reasons: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class StagedAuthoringResult(StrictExecutorModel):
    envelope: LedgerEnvelope
    journal: tuple[AttemptRecord, ...]
    saved_path: str | None = None
    roundtrip_verified: bool = False


# Every payload surface carries a generous-but-finite cap: a runaway guard,
# not a content target, so a looping decoder cannot blow out the context.
class SeedPayload(StrictExecutorModel):
    episode_title: NonBlankText = Field(max_length=200)
    story_seed: NonBlankText = Field(max_length=2000)


class ArcPayload(StrictExecutorModel):
    summary: NonBlankText = Field(max_length=2000)
    act_premises: tuple[
        Annotated[NonBlankText, Field(max_length=600)], ...
    ] = Field(min_length=1, max_length=8)


class ActSpinePayload(StrictExecutorModel):
    spine: NonBlankText = Field(max_length=1500)
    entry_state: NonBlankText = Field(max_length=1500)
    exit_state: NonBlankText = Field(max_length=1500)


class ActBeatsPayload(StrictExecutorModel):
    beat_intents: tuple[
        Annotated[NonBlankText, Field(max_length=500)], ...
    ] = Field(min_length=1, max_length=24)


class ActDialoguePayload(StrictExecutorModel):
    rows: tuple[dict[str, Any], ...] = Field(min_length=1, max_length=240)


class AnnouncerOpenPayload(StrictExecutorModel):
    text: NonBlankText = Field(max_length=2500)


class AnnouncerCodaPayload(StrictExecutorModel):
    text: NonBlankText = Field(max_length=2500)
    fact_id: str = Field(pattern=ID_PATTERN)


_SPEECH_TEXT_RUNAWAY_CAP = 1200
_MUSIC_TEXT_RUNAWAY_CAP = 500
_RUNAWAY_REPEAT_FLOOR = 4
_RUNAWAY_REPEAT_BUDGET = 24
_RUNAWAY_MAX_WINDOW = 10
_REPEATED_ROW_LIMIT = 3
_RUNAWAY_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def find_decode_runaway(text: str) -> str | None:
    """Deterministic decode-liveness check for one accepted text surface.

    Catches the documented glitch where a decoder loops one phrase until it
    blows out the context.  The consecutive-repeat threshold scales with
    window size - short windows need many repeats - so legitimate dramatic
    rhetoric (a word said five times) passes while a true runaway cannot.
    """

    words = [word.casefold() for word in _RUNAWAY_WORD_RE.findall(text)]
    for size in range(1, _RUNAWAY_MAX_WINDOW + 1):
        required = max(
            _RUNAWAY_REPEAT_FLOOR, -(-_RUNAWAY_REPEAT_BUDGET // size)
        )
        for start in range(0, len(words) - size + 1):
            window = words[start : start + size]
            repeats = 1
            position = start + size
            while words[position : position + size] == window:
                repeats += 1
                position += size
            if repeats >= required:
                return (
                    f"decode runaway: {' '.join(window)!r} repeats "
                    f"{repeats} times consecutively"
                )
    return None


def _decode_runaway_reasons(surfaces: Mapping[str, str]) -> list[str]:
    reasons: list[str] = []
    for label, text in surfaces.items():
        finding = find_decode_runaway(text)
        if finding is not None:
            reasons.append(f"{label}: {finding}")
    return reasons


class _AcceptedSpeechRow(StrictExecutorModel):
    beat_id: str
    char_id: str
    text: str
    fact_ids: tuple[str, ...] = ()


class _AcceptedMusicRow(StrictExecutorModel):
    description: str
    generation_prompt: str


_OPEN_BEAT_INTENT = "Introduce the story, setting, time, and characters."
_CODA_BEAT_INTENT = "Return to the captured real-news fact."
_SCENE_DESCRIPTION = "A complete studio drama framed by the announcer."
_OPEN_SHOT_DESCRIPTION = (
    "The announcer introduces the program before the drama begins."
)
_CODA_SHOT_DESCRIPTION = (
    "The announcer returns to the captured news before the close."
)
_MUSIC_OPEN_CUE = MusicCue(
    cue_id="music_open",
    description="Opening period-radio theme.",
    generation_prompt="Brief tense vintage radio opening theme.",
    request_authority="compiler_bookend",
)
_MUSIC_CLOSE_CUE = MusicCue(
    cue_id="music_close",
    description="Closing period-radio theme.",
    generation_prompt="Brief reflective vintage radio closing theme.",
    request_authority="compiler_bookend",
)

_OUTPUT_CONTRACTS: dict[str, str] = {
    "story_seed": (
        'Return one JSON object and nothing else: {"episode_title": "...", '
        '"story_seed": "..."}. No markdown fences, no commentary, no extra '
        "keys. Both values are plain planning text. Neither value may hold a "
        "line of dialogue, a speaker name, or quoted speech."
    ),
    "story_arc": (
        'Return one JSON object and nothing else: {"summary": "...", '
        '"act_premises": ["...", "..."]}. No markdown fences, no commentary, '
        "no extra keys. act_premises is a flat list of plain strings in act "
        "order, one string per act; do not number them, do not give them IDs, "
        "and do not make them objects. summary and every premise are planning "
        "text, never dialogue."
    ),
    "act_spine": (
        'Return one JSON object and nothing else: {"spine": "...", '
        '"entry_state": "...", "exit_state": "..."}. No markdown fences, no '
        "commentary, no extra keys. All three values are plain planning text, "
        "never dialogue and never a speaker's words."
    ),
    "act_beats": (
        'Return one JSON object and nothing else: {"beat_intents": ["...", '
        '"..."]}. No markdown fences, no commentary, no extra keys. '
        "beat_intents is a flat list of plain strings in the order the beats "
        "happen, one string per beat; do not number the beats, do not give "
        "them IDs, and do not make them objects, because the beat IDs are "
        "assigned later by code. Every string says what happens, never what "
        "anyone says."
    ),
    "act_dialogue": (
        'Return one JSON object and nothing else: {"rows": [...]}. No markdown '
        "fences, no commentary, no extra keys. Every element of rows is "
        'exactly one of two shapes. A spoken row is {"role": '
        '"character_dialogue", "beat_id": "...", "char_id": "...", "text": '
        '"...", "fact_ids": ["..."]}, where beat_id is copied from the beats '
        "list, char_id is copied from a locked_cast row whose cast_role is "
        '"character", text holds only the bare words spoken aloud, and '
        "fact_ids is a list of fact ID strings that is [] when the row cites "
        'none. A music row is {"role": "music_inter", "description": "...", '
        '"generation_prompt": "..."}, where both fields are filled in and the '
        "row carries no beat_id, no char_id and no fact_ids. Use no other role "
        "and no other field; never add an action, stage_direction, narration "
        "or delivery_note field to any row. Put the rows in beat order, from "
        "this act's first beat to its last. A music row may not be the first "
        "row of act 1 or the last row of the final act. Never return the same "
        "spoken line twice, and never repeat the same word or phrase over and "
        "over inside one line."
    ),
    "act_cleanup": (
        'Return one JSON object and nothing else: {"rows": [...]}. No markdown '
        "fences, no commentary, no extra keys. Every element of rows is exactly "
        'one of two shapes. A spoken line is {"role": "character_dialogue", '
        '"beat_id": "...", "char_id": "...", "text": "...", "fact_ids": '
        '["..."]}, where beat_id, char_id and fact_ids are copied unchanged '
        "from that draft row and text holds only the bare words spoken aloud. "
        'A music cue is {"role": "music_inter", "description": "...", '
        '"generation_prompt": "..."}, where both fields are filled in and the '
        "row carries no beat_id, no char_id and no fact_ids. Use no other role "
        "and no other field; never add an action, stage_direction, narration "
        "or delivery_note field to any row. Keep the rows in the order the "
        "draft gave them. A row that could become neither spoken words nor a "
        "music cue is simply left out of the array; never replace it with an "
        "empty row, a placeholder, or an explanation."
    ),
    "announcer_open": (
        'Return one JSON object and nothing else: {"text": "..."}. No markdown '
        "fences, no commentary, no other key. text is one plain string holding "
        "only the words the announcer says out loud. Every phrase in "
        "required_literal_mentions must appear inside text, its words in order "
        "with no other word between them. text must contain no square "
        "brackets, no curly braces and no asterisks."
    ),
    "announcer_news_coda": (
        'Return one JSON object and nothing else: {"text": "...", "fact_id": '
        '"..."}. No markdown fences, no commentary, no other key. text is one '
        "plain string holding only the words the announcer says out loud, and "
        "it must contain every word of closing_fact_claim in order with no "
        "other word between them. fact_id is the exact value CONTEXT gives for "
        "closing_fact_id, copied as a plain string. text must contain no "
        "square brackets, no curly braces and no asterisks. Do not repeat the "
        "same word or phrase over and over."
    ),
}


def render_job_prompt(
    job: AuthoringJob,
    *,
    attempt_number: int,
    context: Mapping[str, Any],
    feedback: tuple[str, ...] = (),
    bank_direction: str = "",
) -> str:
    """Render one deterministic provider-neutral prompt for a model job.

    The same shape every time, so a small model sees familiar sections: what
    the job is, the shared rules, this bank's own direction, the context, and
    the exact output shape.
    """

    parts: list[str] = [
        "STORY LAB STAGED AUTHORING JOB",
        f"job_id: {job.job_id}",
        f"kind: {job.kind}",
        f"attempt: {attempt_number}",
        "",
        "INSTRUCTIONS:",
    ]
    parts.extend(
        f"{index}. {instruction}"
        for index, instruction in enumerate(job.instructions, start=1)
    )
    if bank_direction.strip():
        parts.extend(["", "BANK DIRECTION:", bank_direction.strip()])
    parts.extend(
        [
            "",
            "CONTEXT (JSON):",
            json.dumps(
                dict(context), ensure_ascii=False, indent=2, sort_keys=True
            ),
            "",
            "OUTPUT CONTRACT:",
            _OUTPUT_CONTRACTS[job.kind],
        ]
    )
    if feedback:
        parts.extend(["", "FEEDBACK ON YOUR PREVIOUS REJECTED ATTEMPT:"])
        parts.extend(f"- {reason}" for reason in feedback)
    return "\n".join(parts)


def assign_story_facts(
    fact_ids: list[str], act_count: int
) -> tuple[dict[int, tuple[str, ...]], str]:
    """Deterministically give every captured fact one owning spoken surface.

    The ledger graph requires every accepted fact to be cited by a spoken
    line.  The last fact closes the episode in the announcer coda; the rest
    cycle across acts in order so a missing citation always has exactly one
    retryable dialogue job.
    """

    if not fact_ids:
        raise AuthoringExecutionError("source packet must carry facts")
    closing_fact_id = fact_ids[-1]
    per_act: dict[int, list[str]] = {
        act_number: [] for act_number in range(1, act_count + 1)
    }
    for index, fact_id in enumerate(fact_ids[:-1]):
        per_act[(index % act_count) + 1].append(fact_id)
    return (
        {
            act_number: tuple(assigned)
            for act_number, assigned in per_act.items()
        },
        closing_fact_id,
    )


def _out_of_order(what: str) -> AuthoringExecutionError:
    return AuthoringExecutionError(
        f"schedule ran out of order: {what} is not accepted yet"
    )


def _require_seed(seed: "SeedPayload | None") -> "SeedPayload":
    if seed is None:
        raise _out_of_order("the story seed")
    return seed


def _require_arc(arc: "ArcPayload | None") -> "ArcPayload":
    if arc is None:
        raise _out_of_order("the story arc")
    return arc


def _require_act_number(act_number: int | None) -> int:
    if act_number is None:
        raise AuthoringExecutionError("an act job must carry an act_number")
    return act_number


def _require_text(value: str | None, what: str) -> str:
    if value is None:
        raise _out_of_order(what)
    return value


def _validation_reasons(exc: ValidationError) -> tuple[str, ...]:
    return tuple(
        f"{'.'.join(str(part) for part in error['loc']) or 'payload'}: "
        f"{error['msg']}"
        for error in exc.errors()
    )


class _StagedRun:
    def __init__(
        self,
        brief: AuthoringBrief,
        provider: StagedModelProvider,
        *,
        sealed_at: datetime,
        save_path: str | Path | None,
    ) -> None:
        self.brief = brief
        self.provider = provider
        self.sealed_at = sealed_at
        self.save_path = Path(save_path) if save_path is not None else None
        self.journal: list[AttemptRecord] = []

        self.packet_sha256 = hashlib.sha256(
            brief.source_packet_bytes
        ).hexdigest()
        try:
            self.artifact = CapturedSourcePacketArtifact.model_validate_json(
                brief.source_packet_bytes
            )
        except (ValidationError, ValueError) as exc:
            raise AuthoringExecutionError(
                "source packet bytes are not a valid captured packet artifact"
            ) from exc
        self.source_packet = SourcePacket(
            packet_id=self.artifact.packet_id,
            source_bank_id=self.artifact.source_bank_id,
            packet_sha256=self.packet_sha256,
            sources=self.artifact.sources,
            facts=self.artifact.facts,
        )
        self.fact_ids = [fact.fact_id for fact in self.artifact.facts]
        self.fact_claims = {
            fact.fact_id: fact.claim for fact in self.artifact.facts
        }
        self.assigned_facts, self.closing_fact_id = assign_story_facts(
            self.fact_ids, brief.act_count
        )
        self.characters = {
            row.char_id: row
            for row in brief.cast
            if row.cast_role == "character"
        }

        self.source_document = brief.source_document
        self.seed: SeedPayload | None = None
        self.arc: ArcPayload | None = None
        self.spines: dict[int, ActSpinePayload] = {}
        self.act_beats: dict[int, list[tuple[str, str]]] = {}
        self.act_rows: dict[
            int, list[_AcceptedSpeechRow | _AcceptedMusicRow]
        ] = {}
        self.final_cast: list[CastMember] = []
        self.open_text: str | None = None
        self.coda_text: str | None = None
        self.envelope: LedgerEnvelope | None = None
        self.roundtrip_verified = False

    # ---- schedule walk ---------------------------------------------------

    def run(self) -> StagedAuthoringResult:
        schedule = build_authoring_schedule(self.brief.act_count)
        for job in schedule.jobs:
            if job.executor == "model":
                self._run_model_job(job)
            elif job.kind == "cast_sweep":
                self._run_cast_sweep(job)
            elif job.kind == "music_bookends":
                self._run_music_bookends(job)
            else:
                self._run_final_admission(job)
        if self.envelope is None:
            raise AuthoringExecutionError(
                "schedule completed without an admitted envelope"
            )
        return StagedAuthoringResult(
            envelope=self.envelope,
            journal=tuple(self.journal),
            saved_path=(
                str(self.save_path) if self.save_path is not None else None
            ),
            roundtrip_verified=self.roundtrip_verified,
        )

    def _record(
        self,
        job: AuthoringJob,
        attempt_number: int,
        status: Literal["accepted", "rejected"],
        reasons: tuple[str, ...] = (),
        notes: tuple[str, ...] = (),
    ) -> None:
        attempt = make_authoring_attempt(job, attempt_number)
        self.journal.append(
            AttemptRecord(
                attempt_id=attempt.attempt_id,
                job_id=job.job_id,
                kind=job.kind,
                executor=job.executor,
                attempt_number=attempt_number,
                status=status,
                reasons=reasons,
                notes=notes,
            )
        )

    def _run_model_job(self, job: AuthoringJob) -> None:
        feedback: tuple[str, ...] = ()
        for attempt_number in range(1, self.brief.max_attempts_per_job + 1):
            attempt = make_authoring_attempt(job, attempt_number)
            context = self._job_context(job)
            request = ModelJobRequest(
                attempt_id=attempt.attempt_id,
                job_id=job.job_id,
                kind=job.kind,
                act_number=job.act_number,
                attempt_number=attempt_number,
                instructions=job.instructions,
                context=context,
                feedback=feedback,
                prompt=render_job_prompt(
                    job,
                    attempt_number=attempt_number,
                    context=context,
                    feedback=feedback,
                    bank_direction=self.brief.bank_job_prompts.get(job.kind, ""),
                ),
                decode_guard=DecodeGuard(
                    max_new_tokens=_DECODE_TOKEN_BUDGETS[job.kind]
                ),
            )
            payload = self.provider.run_job(request)
            if not isinstance(payload, Mapping):
                reasons: tuple[str, ...] = (
                    "model payload must be a JSON object",
                )
                notes: tuple[str, ...] = ()
            else:
                reasons, notes = self._accept_model_payload(job, dict(payload))
            if reasons:
                self._record(
                    job, attempt_number, "rejected", reasons=reasons, notes=notes
                )
                feedback = reasons
                continue
            self._record(job, attempt_number, "accepted", notes=notes)
            return
        raise AuthoringExecutionError(
            f"job {job.job_id!r} failed after "
            f"{self.brief.max_attempts_per_job} attempts: "
            f"{'; '.join(feedback)}"
        )

    # ---- per-job context -------------------------------------------------

    def _act_window(self, act_number: int):
        """Return act ``act_number``'s frozen source window, if adapting."""

        if self.source_document is None:
            return None
        return select_act_window(
            self.source_document,
            act_number=act_number,
            act_count=self.brief.act_count,
            max_chars=self.brief.source_window_max_chars,
        )

    def _common_context(self) -> dict[str, Any]:
        return {
            "episode_id": self.brief.episode_id,
            "setting": self.brief.setting,
            "scene_time": self.brief.scene_time,
            "act_count": self.brief.act_count,
            "source_bank_id": self.artifact.source_bank_id,
            "sources": [
                {"source_id": row.source_id, "title": row.title}
                for row in self.artifact.sources
            ],
            "facts": [
                {"fact_id": fact.fact_id, "claim": fact.claim}
                for fact in self.artifact.facts
            ],
            "locked_cast": [
                {
                    "char_id": row.char_id,
                    "name": row.name,
                    "cast_role": row.cast_role,
                    "character_description": row.character_description,
                }
                for row in self.brief.cast
            ],
        }

    def _arc_context(self) -> dict[str, Any]:
        seed, arc = _require_seed(self.seed), _require_arc(self.arc)
        return {
            "episode_title": self.seed.episode_title,
            "story_seed": self.seed.story_seed,
            "summary": self.arc.summary,
            "act_premises": list(self.arc.act_premises),
        }

    def _job_context(self, job: AuthoringJob) -> dict[str, Any]:
        context = self._common_context()
        if job.kind == "story_seed":
            return context
        seed = _require_seed(self.seed)
        if job.kind == "story_arc":
            context["accepted_story_seed"] = {
                "episode_title": self.seed.episode_title,
                "story_seed": self.seed.story_seed,
            }
            return context

        if job.kind in {
            "act_spine",
            "act_beats",
            "act_dialogue",
            "act_cleanup",
        }:
            act_number = job.act_number
            act_number = _require_act_number(act_number)
            context["story_arc"] = self._arc_context()
            context["act_number"] = act_number
            if act_number > 1:
                context["prior_act_exit_state"] = self.spines[
                    act_number - 1
                ].exit_state
            if job.kind == "act_spine":
                return context
            spine = self.spines[act_number]
            context["act_spine"] = {
                "spine": spine.spine,
                "entry_state": spine.entry_state,
                "exit_state": spine.exit_state,
            }
            if job.kind == "act_beats":
                context["guidance"] = {
                    "authority": self.brief.guidance.authority,
                    "beats_per_act": [
                        self.brief.guidance.beats_per_act_low,
                        self.brief.guidance.beats_per_act_high,
                    ],
                }
                return context
            context["beats"] = [
                {"beat_id": beat_id, "intent": intent}
                for beat_id, intent in self.act_beats[act_number]
            ]
            window = self._act_window(act_number)
            if window is not None:
                # An adaptation's arc should be the source's arc, so act i of
                # n grounds on region i of n.  The block is quoted data, and
                # its receipt is offsets and a digest, never prose.
                context["source_block"] = render_source_block(window)
                context["source_grounding"] = window.receipt()
            context["assigned_fact_ids"] = list(
                self.assigned_facts[act_number]
            )
            if job.kind == "act_cleanup":
                context["draft_rows"] = [
                    row.model_dump() for row in self.act_rows.get(act_number, ())
                ]
                context["ledger_law"] = (
                    "The sealed ledger may contain only announcer speech, "
                    "character dialogue, and music cues."
                )
                if self.brief.source_speaker_labels:
                    context["source_speaker_labels"] = list(
                        self.brief.source_speaker_labels
                    )
            context["guidance"] = {
                "authority": self.brief.guidance.authority,
                "exchanges_per_beat": [
                    self.brief.guidance.exchanges_per_beat_low,
                    self.brief.guidance.exchanges_per_beat_high,
                ],
            }
            return context

        context["story_arc"] = self._arc_context()
        context["final_cast"] = [
            {
                "char_id": row.char_id,
                "name": row.name,
                "cast_role": row.cast_role,
            }
            for row in self.final_cast
        ]
        if job.kind == "announcer_open":
            context["episode_title"] = self.seed.episode_title
            context["required_literal_mentions"] = [
                self.seed.episode_title,
                self.brief.setting,
                self.brief.scene_time,
                *[
                    row.name
                    for row in self.final_cast
                    if row.cast_role == "character"
                ],
            ]
            return context
        context["closing_fact_id"] = self.closing_fact_id
        context["closing_fact_claim"] = self.fact_claims[self.closing_fact_id]
        return context

    # ---- per-job acceptance ----------------------------------------------

    def _accept_model_payload(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        acceptors = {
            "story_seed": self._accept_seed,
            "story_arc": self._accept_arc,
            "act_spine": self._accept_spine,
            "act_beats": self._accept_beats,
            "act_dialogue": self._accept_dialogue,
            "act_cleanup": self._accept_cleanup,
            "announcer_open": self._accept_open,
            "announcer_news_coda": self._accept_coda,
        }
        return acceptors[job.kind](job, payload)

    def _accept_seed(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        try:
            seed = SeedPayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        reasons = _decode_runaway_reasons(
            {
                "episode_title": seed.episode_title,
                "story_seed": seed.story_seed,
            }
        )
        if reasons:
            return tuple(reasons), ()
        self.seed = seed
        return (), ()

    def _accept_arc(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        try:
            arc = ArcPayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        if len(arc.act_premises) != self.brief.act_count:
            return (
                (
                    f"arc must contain exactly {self.brief.act_count} act "
                    f"premises, got {len(arc.act_premises)}"
                ),
            ), ()
        reasons = _decode_runaway_reasons(
            {
                "summary": arc.summary,
                **{
                    f"act_premises[{index}]": premise
                    for index, premise in enumerate(arc.act_premises)
                },
            }
        )
        if reasons:
            return tuple(reasons), ()
        self.arc = arc
        return (), ()

    def _accept_spine(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        act_number = _require_act_number(job.act_number)
        try:
            spine = ActSpinePayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        reasons = _decode_runaway_reasons(
            {
                "spine": spine.spine,
                "entry_state": spine.entry_state,
                "exit_state": spine.exit_state,
            }
        )
        if reasons:
            return tuple(reasons), ()
        self.spines[job.act_number] = spine
        return (), ()

    def _accept_beats(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        act_number = job.act_number
        act_number = _require_act_number(act_number)
        try:
            beats = ActBeatsPayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        runaway = _decode_runaway_reasons(
            {
                f"beat_intents[{index}]": intent
                for index, intent in enumerate(beats.beat_intents)
            }
        )
        if runaway:
            return tuple(runaway), ()
        # b001 is the compiler-owned announcer opening beat; act beats are
        # globally numbered in program order after it.
        offset = 2 + sum(
            len(self.act_beats[prior])
            for prior in range(1, act_number)
        )
        self.act_beats[act_number] = [
            (f"b{offset + index:03d}", intent)
            for index, intent in enumerate(beats.beat_intents)
        ]
        return (), ()

    def _accept_dialogue(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        act_number = job.act_number
        act_number = _require_act_number(act_number)
        try:
            dialogue = ActDialoguePayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()

        carried = self._act_window(act_number)
        sanitized = sanitize_draft_sequence(
            dialogue.rows, carried_source=carried
        )
        notes = tuple(
            f"dropped draft row {issue.row_index} "
            f"({issue.role or 'unknown'}): {issue.reason}"
            for issue in sanitized.dropped_rows
        )
        if sanitized.rewrite_rows:
            return (
                tuple(
                    f"row {issue.row_index} ({issue.role or 'unknown'}): "
                    f"{issue.reason}"
                    for issue in sanitized.rewrite_rows
                ),
                notes,
            )

        act_beat_ids = [beat_id for beat_id, _ in self.act_beats[act_number]]
        beat_positions = {
            beat_id: index for index, beat_id in enumerate(act_beat_ids)
        }
        reasons: list[str] = []
        typed: list[_AcceptedSpeechRow | _AcceptedMusicRow] = []
        last_beat_position = -1
        for index, row in enumerate(sanitized.admission_rows()):
            role = _draft_role(row)
            if role == "music_inter":
                description = row.get("description")
                generation_prompt = row.get("generation_prompt")
                if not (
                    isinstance(description, str)
                    and description.strip()
                    and isinstance(generation_prompt, str)
                    and generation_prompt.strip()
                ):
                    reasons.append(
                        f"row {index}: music_inter requires description and "
                        "generation_prompt"
                    )
                    continue
                if (
                    len(description) > _MUSIC_TEXT_RUNAWAY_CAP
                    or len(generation_prompt) > _MUSIC_TEXT_RUNAWAY_CAP
                ):
                    reasons.append(
                        f"row {index}: music_inter text exceeds the "
                        f"{_MUSIC_TEXT_RUNAWAY_CAP}-char runaway guard"
                    )
                    continue
                typed.append(
                    _AcceptedMusicRow(
                        description=description,
                        generation_prompt=generation_prompt,
                    )
                )
                continue
            if role != "character_dialogue":
                reasons.append(
                    f"row {index}: role {role!r} is not owned by an act "
                    "dialogue job"
                )
                continue
            beat_id = str(row.get("beat_id") or "").strip()
            char_id = str(row.get("char_id") or "").strip()
            text = row.get("text")
            raw_fact_ids = row.get("fact_ids") or []
            if beat_id not in beat_positions:
                reasons.append(
                    f"row {index}: beat_id {beat_id!r} is not one of this "
                    f"act's beats {act_beat_ids}"
                )
                continue
            if beat_positions[beat_id] < last_beat_position:
                reasons.append(
                    f"row {index}: dialogue must follow beat order without "
                    "returning to an earlier beat"
                )
                continue
            last_beat_position = beat_positions[beat_id]
            if char_id not in self.characters:
                reasons.append(
                    f"row {index}: char_id {char_id!r} is not a locked "
                    "character"
                )
                continue
            if not isinstance(text, str) or not text.strip():
                reasons.append(f"row {index}: text must be non-blank speech")
                continue
            if len(text) > _SPEECH_TEXT_RUNAWAY_CAP:
                reasons.append(
                    f"row {index}: speech text exceeds the "
                    f"{_SPEECH_TEXT_RUNAWAY_CAP}-char runaway guard"
                )
                continue
            runaway = find_decode_runaway(text)
            if runaway is not None:
                reasons.append(f"row {index}: {runaway}")
                continue
            if not isinstance(raw_fact_ids, (list, tuple)) or any(
                not isinstance(fact_id, str) for fact_id in raw_fact_ids
            ):
                reasons.append(
                    f"row {index}: fact_ids must be a list of fact IDs"
                )
                continue
            fact_ids = tuple(raw_fact_ids)
            if len(fact_ids) != len(set(fact_ids)):
                reasons.append(f"row {index}: fact_ids repeat a fact")
                continue
            unknown_facts = [
                fact_id
                for fact_id in fact_ids
                if fact_id not in self.fact_claims
            ]
            if unknown_facts:
                reasons.append(
                    f"row {index}: unknown fact_ids {unknown_facts}"
                )
                continue
            typed.append(
                _AcceptedSpeechRow(
                    beat_id=beat_id,
                    char_id=char_id,
                    text=text,
                    fact_ids=fact_ids,
                )
            )
        if reasons:
            return tuple(reasons), notes

        speech_rows = [
            row for row in typed if isinstance(row, _AcceptedSpeechRow)
        ]
        repeated_rows = Counter(
            " ".join(row.text.split()).casefold() for row in speech_rows
        )
        worst_repeat = max(repeated_rows.values(), default=0)
        if worst_repeat >= _REPEATED_ROW_LIMIT:
            reasons.append(
                "decode liveness: the same dialogue line appears "
                f"{worst_repeat} times across rows"
            )
        covered_beats = {row.beat_id for row in speech_rows}
        for beat_id in act_beat_ids:
            if beat_id not in covered_beats:
                reasons.append(
                    f"beat {beat_id!r} has no actual character dialogue"
                )
        cited = {
            fact_id for row in speech_rows for fact_id in row.fact_ids
        }
        missing_facts = [
            fact_id
            for fact_id in self.assigned_facts[act_number]
            if fact_id not in cited
        ]
        if missing_facts:
            reasons.append(
                f"assigned facts {missing_facts} are not cited by any "
                "dialogue row in this act"
            )
        if act_number == 1 and typed and isinstance(
            typed[0], _AcceptedMusicRow
        ):
            reasons.append(
                "music_inter cannot precede the first dialogue row of act 1"
            )
        if act_number == self.brief.act_count and typed and isinstance(
            typed[-1], _AcceptedMusicRow
        ):
            reasons.append(
                "music_inter cannot follow the final dialogue row of the "
                "last act"
            )
        if reasons:
            return tuple(reasons), notes

        audit_lines = [
            {
                "line_id": f"{job.job_id}.row{index:02d}",
                "char_id": row.char_id,
                "speaker": self.characters[row.char_id].name,
                "speaker_role": "character",
                "text": row.text,
            }
            for index, row in enumerate(typed)
            if isinstance(row, _AcceptedSpeechRow)
        ]
        findings = audit_spoken_text(
            audit_lines,
            [row.model_dump() for row in self.brief.cast],
            carried_source=carried,
        )
        if findings:
            return (
                tuple(
                    f"{finding.line_id}: {finding.code}: {finding.detail}"
                    for finding in findings
                ),
                notes,
            )
        self.act_rows[act_number] = typed
        return (), notes

    def _accept_cleanup(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Admit the model's cleaned rows for this act.

        The cleanup pass is where a draft is made speakable.  Code judges the
        result and says why it failed; it never edits the prose itself, so a
        rejected cleanup returns to this same model job with the reasons.
        """

        act_number = _require_act_number(job.act_number)
        before = self.act_rows.get(act_number, ())
        reasons, notes = self._accept_dialogue(job, payload)
        if reasons:
            # Leave the accepted draft in place; a rejected cleanup must not
            # half-replace the act it was asked to repair.
            self.act_rows[act_number] = before
            return reasons, notes
        after = self.act_rows.get(act_number, ())

        # Cleanup may reword, convert, or drop a row.  It may not re-assign
        # one: a speaker or beat it never received is drift, not repair, and
        # would seal another character's words under the wrong voice.
        def owned(rows) -> set[tuple[str, str]]:
            return {
                (row.beat_id, row.char_id)
                for row in rows
                if isinstance(row, _AcceptedSpeechRow)
            }

        invented = sorted(owned(after) - owned(before))
        if invented:
            self.act_rows[act_number] = before
            return (
                tuple(
                    f"cleanup assigned beat {beat_id!r} to {char_id!r}, which "
                    "did not speak it in the draft; keep each row's beat and "
                    "speaker exactly as given"
                    for beat_id, char_id in invented
                ),
                notes,
            )

        changed = sum(
            1
            for old, new in zip(before, after)
            if getattr(old, "text", None) != getattr(new, "text", None)
        ) + abs(len(after) - len(before))
        return (), notes + (
            f"cleanup pass changed {changed} row(s)"
            if changed
            else "cleanup pass found nothing to change",
        )

    def _announcer(self) -> CastMember:
        return next(
            row for row in self.final_cast if row.cast_role == "announcer"
        )

    def _accept_announcer_text(
        self,
        *,
        text: str,
        sequence_role: str,
        provisional_line_id: str,
    ) -> tuple[str, ...]:
        sanitized = sanitize_draft_sequence(
            [{"sequence_role": sequence_role, "text": text}]
        )
        if sanitized.rewrite_rows:
            return tuple(
                f"{sequence_role}: {issue.reason}"
                for issue in sanitized.rewrite_rows
            )
        runaway = find_decode_runaway(text)
        if runaway is not None:
            return (f"{sequence_role}: {runaway}",)
        announcer = self._announcer()
        findings = audit_spoken_text(
            [
                {
                    "line_id": provisional_line_id,
                    "char_id": announcer.char_id,
                    "speaker": announcer.name,
                    "speaker_role": "announcer",
                    "text": text,
                }
            ],
            [row.model_dump() for row in self.final_cast],
        )
        return tuple(
            f"{finding.line_id}: {finding.code}: {finding.detail}"
            for finding in findings
        )

    def _accept_open(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        seed = _require_seed(self.seed)
        try:
            open_payload = AnnouncerOpenPayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        reasons = list(
            self._accept_announcer_text(
                text=open_payload.text,
                sequence_role="announcer_open",
                provisional_line_id="announcer_open.draft",
            )
        )
        required_mentions = [
            self.seed.episode_title,
            self.brief.setting,
            self.brief.scene_time,
            *[
                row.name
                for row in self.final_cast
                if row.cast_role == "character"
            ],
        ]
        missing = [
            phrase
            for phrase in required_mentions
            if not _contains_normalized_phrase(open_payload.text, phrase)
        ]
        if missing:
            reasons.append(
                "opening must literally include the story title, setting, "
                f"scene time, and every final character name; missing: "
                f"{missing}"
            )
        if reasons:
            return tuple(reasons), ()
        self.open_text = open_payload.text
        return (), ()

    def _accept_coda(
        self, job: AuthoringJob, payload: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        try:
            coda = AnnouncerCodaPayload.model_validate(payload)
        except ValidationError as exc:
            return _validation_reasons(exc), ()
        reasons = list(
            self._accept_announcer_text(
                text=coda.text,
                sequence_role="announcer_news_coda",
                provisional_line_id="announcer_news_coda.draft",
            )
        )
        if coda.fact_id != self.closing_fact_id:
            reasons.append(
                f"coda must cite the assigned closing fact "
                f"{self.closing_fact_id!r}, got {coda.fact_id!r}"
            )
        elif not _contains_normalized_phrase(
            coda.text, self.fact_claims[self.closing_fact_id]
        ):
            reasons.append(
                "coda must contain the complete claim of the closing fact "
                "verbatim"
            )
        if reasons:
            return tuple(reasons), ()
        self.coda_text = coda.text
        return (), ()

    # ---- compiler jobs ---------------------------------------------------

    def _all_speech_rows(self) -> list[_AcceptedSpeechRow]:
        return [
            row
            for act_number in sorted(self.act_rows)
            for row in self.act_rows[act_number]
            if isinstance(row, _AcceptedSpeechRow)
        ]

    def _run_cast_sweep(self, job: AuthoringJob) -> None:
        dialogue_rows = [
            {"sequence_role": "character_dialogue", "char_id": row.char_id}
            for row in self._all_speech_rows()
        ]
        swept = sweep_cast_after_dialogue(
            [row.model_dump() for row in self.brief.cast], dialogue_rows
        )
        self.final_cast = [CastMember.model_validate(row) for row in swept]
        kept_ids = {row.char_id for row in self.final_cast}
        notes = tuple(
            f"swept unused character {row.char_id!r} ({row.name})"
            for row in self.brief.cast
            if row.char_id not in kept_ids
        )
        self._record(job, 1, "accepted", notes=notes)

    def _interstitial_cues(self) -> list[MusicCue]:
        cues: list[MusicCue] = []
        for act_number in sorted(self.act_rows):
            for row in self.act_rows[act_number]:
                if isinstance(row, _AcceptedMusicRow):
                    cues.append(
                        MusicCue(
                            cue_id=f"music_inter_{len(cues) + 1:02d}",
                            description=row.description,
                            generation_prompt=row.generation_prompt,
                            request_authority="script",
                        )
                    )
        return cues

    def _run_music_bookends(self, job: AuthoringJob) -> None:
        interstitials = self._interstitial_cues()
        notes = (
            f"compiler bookends {_MUSIC_OPEN_CUE.cue_id!r} and "
            f"{_MUSIC_CLOSE_CUE.cue_id!r}",
            f"{len(interstitials)} script-requested interstitial cue(s)",
        )
        self._record(job, 1, "accepted", notes=notes)

    # ---- final compilation and admission ---------------------------------

    def _compile_story_ledger(self) -> StoryLedger:
        seed, arc = _require_seed(self.seed), _require_arc(self.arc)
        open_text = _require_text(self.open_text, "announcer opening")
        coda_text = _require_text(self.coda_text, "announcer news coda")
        act_count = self.brief.act_count
        act_ids = {
            act_number: f"a{act_number:03d}"
            for act_number in range(1, act_count + 1)
        }
        scene_id = "s001"
        open_shot_id = "sh001"
        act_shot_ids = {
            act_number: f"sh{act_number + 1:03d}"
            for act_number in range(1, act_count + 1)
        }
        coda_shot_id = f"sh{act_count + 2:03d}"
        open_beat_id = "b001"
        total_act_beats = sum(
            len(self.act_beats[act_number]) for act_number in self.act_beats
        )
        coda_beat_id = f"b{2 + total_act_beats:03d}"
        announcer = self._announcer()

        lines: list[SpokenLine] = []
        sequence: list[SequenceItem] = []
        interstitial_cues = self._interstitial_cues()
        beat_line_ids: dict[str, list[str]] = {}
        speaking_order: dict[int, list[str]] = {
            act_number: [] for act_number in range(1, act_count + 1)
        }

        def add_sequence(
            sequence_role: str, ref_kind: str, ref_id: str
        ) -> None:
            sequence.append(
                SequenceItem(
                    sequence_id=f"q{len(sequence) + 1:03d}",
                    sequence_role=sequence_role,
                    ref_kind=ref_kind,
                    ref_id=ref_id,
                )
            )

        def add_line(
            *,
            shot_id: str,
            beat_id: str,
            cast_row: CastMember,
            text: str,
            fact_ids: list[str],
            sequence_role: str,
        ) -> None:
            line = SpokenLine(
                line_id=f"l{len(lines) + 1:03d}",
                scene_id=scene_id,
                shot_id=shot_id,
                beat_id=beat_id,
                char_id=cast_row.char_id,
                speaker=cast_row.name,
                speaker_role=cast_row.cast_role,
                text=text,
                fact_ids=fact_ids,
            )
            lines.append(line)
            beat_line_ids.setdefault(beat_id, []).append(line.line_id)
            add_sequence(sequence_role, "line", line.line_id)

        add_sequence("music_open", "music_cue", _MUSIC_OPEN_CUE.cue_id)
        add_line(
            shot_id=open_shot_id,
            beat_id=open_beat_id,
            cast_row=announcer,
            text=self.open_text,
            fact_ids=[],
            sequence_role="announcer_open",
        )
        interstitial_index = 0
        for act_number in range(1, act_count + 1):
            for row in self.act_rows[act_number]:
                if isinstance(row, _AcceptedMusicRow):
                    cue = interstitial_cues[interstitial_index]
                    interstitial_index += 1
                    add_sequence("music_inter", "music_cue", cue.cue_id)
                    continue
                cast_row = self.characters[row.char_id]
                if cast_row.char_id not in speaking_order[act_number]:
                    speaking_order[act_number].append(cast_row.char_id)
                add_line(
                    shot_id=act_shot_ids[act_number],
                    beat_id=row.beat_id,
                    cast_row=cast_row,
                    text=row.text,
                    fact_ids=list(row.fact_ids),
                    sequence_role="character_dialogue",
                )
        add_line(
            shot_id=coda_shot_id,
            beat_id=coda_beat_id,
            cast_row=announcer,
            text=self.coda_text,
            fact_ids=[self.closing_fact_id],
            sequence_role="announcer_news_coda",
        )
        add_sequence("music_close", "music_cue", _MUSIC_CLOSE_CUE.cue_id)

        beats: list[Beat] = [
            Beat(
                beat_id=open_beat_id,
                act_id=None,
                scene_id=scene_id,
                shot_id=open_shot_id,
                intent=_OPEN_BEAT_INTENT,
                line_ids=beat_line_ids[open_beat_id],
            )
        ]
        shots: list[Shot] = [
            Shot(
                shot_id=open_shot_id,
                scene_id=scene_id,
                description=_OPEN_SHOT_DESCRIPTION,
                beat_ids=[open_beat_id],
            )
        ]
        acts: list[StoryAct] = []
        for act_number in range(1, act_count + 1):
            current_beat_ids = [
                beat_id for beat_id, _ in self.act_beats[act_number]
            ]
            beats.extend(
                Beat(
                    beat_id=beat_id,
                    act_id=act_ids[act_number],
                    scene_id=scene_id,
                    shot_id=act_shot_ids[act_number],
                    intent=intent,
                    line_ids=beat_line_ids[beat_id],
                )
                for beat_id, intent in self.act_beats[act_number]
            )
            shots.append(
                Shot(
                    shot_id=act_shot_ids[act_number],
                    scene_id=scene_id,
                    description=f"Act {act_number} of the character drama.",
                    beat_ids=current_beat_ids,
                )
            )
            spine = self.spines[act_number]
            acts.append(
                StoryAct(
                    act_id=act_ids[act_number],
                    act_number=act_number,
                    spine=spine.spine,
                    entry_state=spine.entry_state,
                    exit_state=spine.exit_state,
                    speaking_char_ids=speaking_order[act_number],
                    beat_ids=current_beat_ids,
                )
            )
        beats.append(
            Beat(
                beat_id=coda_beat_id,
                act_id=None,
                scene_id=scene_id,
                shot_id=coda_shot_id,
                intent=_CODA_BEAT_INTENT,
                line_ids=beat_line_ids[coda_beat_id],
            )
        )
        shots.append(
            Shot(
                shot_id=coda_shot_id,
                scene_id=scene_id,
                description=_CODA_SHOT_DESCRIPTION,
                beat_ids=[coda_beat_id],
            )
        )

        body = StoryBody(
            context=StoryContext(
                episode_title=self.seed.episode_title,
                story_seed=self.seed.story_seed,
                setting=self.brief.setting,
                act_count=act_count,
            ),
            source_packet=self.source_packet,
            cast=self.final_cast,
            story_arc=StoryArc(
                summary=self.arc.summary,
                act_ids=[
                    act_ids[act_number]
                    for act_number in range(1, act_count + 1)
                ],
            ),
            acts=acts,
            scenes=[
                Scene(
                    scene_id=scene_id,
                    description=_SCENE_DESCRIPTION,
                    setting=self.brief.setting,
                    time=self.brief.scene_time,
                    shot_ids=[shot.shot_id for shot in shots],
                )
            ],
            shots=shots,
            beats=beats,
            lines=lines,
            music_cues=[
                _MUSIC_OPEN_CUE,
                *interstitial_cues,
                _MUSIC_CLOSE_CUE,
            ],
            sequence=sequence,
        )

        open_line_id = lines[0].line_id
        coda_line_id = lines[-1].line_id

        def receipt(
            outcome: str, evidence: list[tuple[str, str]]
        ) -> OutcomeReceipt:
            validator_id, validator_version = TRUSTED_VALIDATOR_IDENTITIES[
                outcome
            ]
            if outcome == "ledger_integrity" and self.source_document is not None:
                # Adaptation lanes declare the version whose meaning includes
                # the source-carried exemption, rather than quietly widening
                # what a version 3 receipt claims.
                validator_version = (
                    LEDGER_INTEGRITY_ADAPTATION_VALIDATOR_VERSION
                )
            return OutcomeReceipt(
                validator_id=validator_id,
                validator_version=validator_version,
                evidence_refs=[
                    EvidenceRef(kind=kind, ref_id=ref_id)
                    for kind, ref_id in evidence
                ],
            )

        validation = StoryValidation(
            body_sha256=canonical_sha256(body),
            outcomes=MinimumOutcomes(
                ledger_integrity=receipt("ledger_integrity", []),
                news_capture=receipt(
                    "news_capture",
                    [
                        ("source_packet", self.source_packet.packet_id),
                        *[("fact", fact_id) for fact_id in self.fact_ids],
                    ],
                ),
                announcer_open=receipt(
                    "announcer_open", [("line", open_line_id)]
                ),
                announcer_news_coda=receipt(
                    "announcer_news_coda",
                    [
                        ("line", coda_line_id),
                        ("fact", self.closing_fact_id),
                    ],
                ),
                music_bookends=receipt(
                    "music_bookends",
                    [
                        ("music_cue", _MUSIC_OPEN_CUE.cue_id),
                        ("music_cue", _MUSIC_CLOSE_CUE.cue_id),
                    ],
                ),
            ),
        )
        return StoryLedger(
            episode_id=self.brief.episode_id,
            body=body,
            validation=validation,
        )

    def _run_final_admission(self, job: AuthoringJob) -> None:
        registry = build_trusted_receipt_verifiers(
            packet_artifacts={
                self.packet_sha256: self.brief.source_packet_bytes
            },
            carried_sources=(
                () if self.source_document is None else (self.source_document,)
            ),
        )
        try:
            story_ledger = self._compile_story_ledger()
            story_seal = build_story_seal(
                story_ledger,
                sealed_at=self.sealed_at,
                receipt_verifiers=registry,
            )
            envelope = LedgerEnvelope(
                story_ledger=story_ledger,
                story_seal=story_seal,
            )
            verify_story_envelope(envelope, receipt_verifiers=registry)
        except AuthoringExecutionError:
            raise
        except Exception as exc:
            raise AuthoringExecutionError(
                f"final admission failed: {exc}"
            ) from exc

        notes = [f"story_sha256 {story_seal.story_sha256}"]
        if self.save_path is not None:
            saved = save_ledger_envelope(
                self.save_path, envelope, receipt_verifiers=registry
            )
            loaded = load_ledger_envelope(
                self.save_path, receipt_verifiers=registry
            )
            if canonical_bytes(loaded) != canonical_bytes(saved):
                raise AuthoringExecutionError(
                    "reloaded ledger does not match the sealed story bytes"
                )
            self.roundtrip_verified = True
            notes.append(f"saved and reloaded {self.save_path}")
        self.envelope = envelope
        self._record(job, 1, "accepted", notes=tuple(notes))


def author_story_ledger(
    brief: AuthoringBrief,
    provider: StagedModelProvider,
    *,
    sealed_at: datetime,
    save_path: str | Path | None = None,
) -> StagedAuthoringResult:
    """Run the complete staged schedule and return one sealed v2 envelope."""

    # ``model_copy(update=...)`` builds a brief without re-running field
    # validators, so an unsafe cast can reach this entry point unchecked.
    # Revalidate before scheduling any work.
    return _StagedRun(
        AuthoringBrief.model_validate(brief),
        provider,
        sealed_at=sealed_at,
        save_path=save_path,
    ).run()


__all__ = [
    "AttemptRecord",
    "AuthoringBrief",
    "AuthoringExecutionError",
    "DecodeGuard",
    "ModelJobRequest",
    "StagedAuthoringGuidance",
    "StagedAuthoringResult",
    "StagedModelProvider",
    "ULTRASHORT_GUIDANCE",
    "assign_story_facts",
    "author_story_ledger",
    "find_decode_runaway",
    "render_job_prompt",
]
