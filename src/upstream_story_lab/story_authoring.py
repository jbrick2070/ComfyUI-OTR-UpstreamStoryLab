"""Pure, source-bank-agnostic scheduling for story authoring.

This module owns authoring topology, not model execution.  It describes a
stable sequence of small jobs, models retries as attempts on those jobs, and
provides conservative cleanup helpers for draft-only data before a caller
constructs and admits a strict Story Ledger body.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


JobKind = Literal[
    "story_seed",
    "story_arc",
    "act_spine",
    "act_beats",
    "act_dialogue",
    "act_cleanup",
    "cast_sweep",
    "announcer_open",
    "announcer_news_coda",
    "music_bookends",
    "final_admission",
]
JobExecutor = Literal["model", "compiler", "admission"]

DIALOGUE_JOB_INSTRUCTIONS = (
    "Write actual spoken dialogue for every assigned beat.",
    "Each dialogue row must contain only words spoken aloud by its assigned speaker.",
    "Do not write stage directions, action, narration, delivery notes, or another speaker's words.",
    "Use only the beat IDs and character IDs you were given, keep the beats in the order listed, and make sure some row carries each assigned fact ID.",
)

#: The ledger may hold only dialogue and music.  Rather than let code rewrite
#: an author's prose, every act gets a model pass whose whole job is to turn a
#: draft into speakable rows: convert a stage direction into spoken
#: implication, radio business, or a music cue, drop what cannot become
#: either, and strip a speaker label that was copied into a line.
#: Written for a small local model and a frontier model alike: plain,
#: imperative, one decision per line, and defaulting to leaving text alone.
#: Each line also guards a real acceptance rule, so following it literally
#: produces an admissible act rather than a rejected one.
CLEANUP_JOB_INSTRUCTIONS = (
    "Your only job is to make every row speakable: each row you return holds either words a character says out loud or a music cue. Leave any row that already holds only spoken words exactly as it is, and when you are unsure about a row, leave it as it is.",
    "Turn any stage direction, action line, narration, production cue, or delivery note into words that same row's character says out loud, or into a music cue; remove it only when it can become neither. Words you write in place of a direction must still do the job that row's beat intent describes, and must fit this act's spine and its entry and exit state.",
    "Remove a speaker name, speech prefix, bracketed note, or parenthetical note that was copied into a line, and keep every spoken word that remains. text holds the bare spoken words, with no speaker name and no quotation marks around them. Never return a row whose text is empty: if nothing spoken is left, make the row a music cue or leave the row out.",
    "Never delete a row that has anything in fact_ids, and never turn such a row into a music cue, because a music cue carries no facts. Never delete the last remaining spoken row of a beat; rewrite its words instead. Never make a music cue the first row of act 1 or the last row of the final act.",
    "Keep every spoken row's beat_id, char_id, and fact_ids exactly as the draft gave them, and never invent a beat, a character, or a fact. Return the rows in the order you received them, and never move a row so that it goes back to an earlier beat.",
    "When the act adapts a source passage, keep the character's own words exactly as the source wrote them, however blunt or violent they are; do not reword, replace, cut, or soften any of them. Strip only a speaker label the draft copied in front of the line.",
    "Edit only to remove what is not spoken aloud. Never trim, tighten, condense, or summarize a spoken line, and never rewrite one just to make it read better; do not pad a line or add rows either.",
)

_MODEL_JOB_KINDS = frozenset(
    {
        "story_seed",
        "story_arc",
        "act_spine",
        "act_beats",
        "act_dialogue",
        "act_cleanup",
        "announcer_open",
        "announcer_news_coda",
    }
)
_ACT_JOB_KINDS = frozenset(
    {"act_spine", "act_beats", "act_dialogue", "act_cleanup"}
)
_ACT_STAGE_BY_KIND = {
    "act_spine": "spine",
    "act_beats": "beats",
    "act_dialogue": "dialogue",
    "act_cleanup": "cleanup",
}


def _act_job_id(act_number: int, stage: str) -> str:
    return f"act_{act_number:02d}.{stage}"


def _expected_job_id(kind: JobKind, act_number: int | None) -> str:
    if kind in _ACT_JOB_KINDS:
        if act_number is None:
            raise StoryAuthoringError("act job requires act_number")
        return _act_job_id(act_number, _ACT_STAGE_BY_KIND[kind])
    return kind


class StoryAuthoringError(ValueError):
    """The proposed authoring topology or draft projection is unsafe."""


class StrictAuthoringModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
    )


class AuthoringJob(StrictAuthoringModel):
    job_id: str = Field(min_length=1)
    kind: JobKind
    executor: JobExecutor
    act_number: int | None = Field(default=None, strict=True, ge=1, le=8)
    depends_on: tuple[str, ...] = ()
    instructions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_job_shape(self) -> "AuthoringJob":
        if self.kind in _ACT_JOB_KINDS:
            if self.act_number is None:
                raise StoryAuthoringError("act job requires act_number")
        elif self.act_number is not None:
            raise StoryAuthoringError("non-act job cannot carry act_number")
        if self.job_id != _expected_job_id(self.kind, self.act_number):
            raise StoryAuthoringError("job_id does not match kind and act_number")

        expected_executor: JobExecutor
        if self.kind in _MODEL_JOB_KINDS:
            expected_executor = "model"
        elif self.kind == "final_admission":
            expected_executor = "admission"
        else:
            expected_executor = "compiler"
        if self.executor != expected_executor:
            raise StoryAuthoringError(
                f"{self.kind} must use executor {expected_executor!r}"
            )
        if len(self.depends_on) != len(set(self.depends_on)):
            raise StoryAuthoringError("job dependencies must be unique")
        if self.job_id in self.depends_on:
            raise StoryAuthoringError("job cannot depend on itself")
        if self.kind == "act_dialogue" and (
            self.instructions != DIALOGUE_JOB_INSTRUCTIONS
        ):
            raise StoryAuthoringError(
                "every act dialogue job must repeat the spoken-only contract"
            )
        if self.kind == "act_cleanup" and (
            self.instructions != CLEANUP_JOB_INSTRUCTIONS
        ):
            raise StoryAuthoringError(
                "every act cleanup job must repeat the cleanup contract"
            )
        return self


def _authoring_jobs(act_count: int) -> tuple[AuthoringJob, ...]:
    jobs: list[AuthoringJob] = [
        AuthoringJob(
            job_id="story_seed",
            kind="story_seed",
            executor="model",
            instructions=(
                "Create one source-grounded story seed as planning text, not dialogue.",
            ),
        ),
        AuthoringJob(
            job_id="story_arc",
            kind="story_arc",
            executor="model",
            depends_on=("story_seed",),
            instructions=(
                f"Plan one coherent {act_count}-act arc from the accepted story seed.",
                "Keep the announcer opening, news coda, and music outside the act count.",
            ),
        ),
    ]

    dialogue_job_ids: list[str] = []
    for act_number in range(1, act_count + 1):
        spine_id = _act_job_id(act_number, "spine")
        beats_id = _act_job_id(act_number, "beats")
        dialogue_id = _act_job_id(act_number, "dialogue")
        cleanup_id = _act_job_id(act_number, "cleanup")
        spine_dependencies = ["story_arc"]
        if act_number > 1:
            spine_dependencies.append(_act_job_id(act_number - 1, "cleanup"))
        jobs.extend(
            [
                AuthoringJob(
                    job_id=spine_id,
                    kind="act_spine",
                    executor="model",
                    act_number=act_number,
                    depends_on=tuple(spine_dependencies),
                    instructions=(
                        f"Plan the dramatic spine for act {act_number}; planning text only.",
                    ),
                ),
                AuthoringJob(
                    job_id=beats_id,
                    kind="act_beats",
                    executor="model",
                    act_number=act_number,
                    depends_on=(spine_id,),
                    instructions=(
                        f"Expand act {act_number}'s spine into ordered dramatic beats; do not write final lines.",
                    ),
                ),
                AuthoringJob(
                    job_id=dialogue_id,
                    kind="act_dialogue",
                    executor="model",
                    act_number=act_number,
                    depends_on=(beats_id,),
                    instructions=DIALOGUE_JOB_INSTRUCTIONS,
                ),
                AuthoringJob(
                    job_id=cleanup_id,
                    kind="act_cleanup",
                    executor="model",
                    act_number=act_number,
                    depends_on=(dialogue_id,),
                    instructions=CLEANUP_JOB_INSTRUCTIONS,
                ),
            ]
        )
        dialogue_job_ids.append(cleanup_id)

    shared_announcer_dependencies = (
        "story_seed",
        "story_arc",
        "cast_sweep",
    )
    jobs.extend(
        [
            AuthoringJob(
                job_id="cast_sweep",
                kind="cast_sweep",
                executor="compiler",
                depends_on=tuple(dialogue_job_ids),
                instructions=(
                    "Retain the announcer and only characters that own final dialogue.",
                ),
            ),
            AuthoringJob(
                job_id="announcer_open",
                kind="announcer_open",
                executor="model",
                depends_on=shared_announcer_dependencies,
                instructions=(
                    "Write only the announcer's spoken opening words; no production cues or stage directions.",
                    "Say every phrase listed in required_literal_mentions, copied exactly, letter for letter: the story title, the setting, the scene time, and each character name.",
                    "Introduce the story and those characters in one short spoken passage; do not paraphrase or shorten any required phrase.",
                ),
            ),
            AuthoringJob(
                job_id="announcer_news_coda",
                kind="announcer_news_coda",
                executor="model",
                depends_on=shared_announcer_dependencies,
                instructions=(
                    "Write only the announcer's spoken source-grounded news coda; no production cues or stage directions.",
                    "Include the whole of closing_fact_claim word for word, exactly as given; do not paraphrase it, shorten it, or split it up.",
                    "You may add a short spoken bridge before that claim to turn from the drama to the real source; return closing_fact_id as fact_id.",
                ),
            ),
            AuthoringJob(
                job_id="music_bookends",
                kind="music_bookends",
                executor="compiler",
                depends_on=("announcer_open", "announcer_news_coda"),
                instructions=(
                    "Insert compiler-owned opening and closing music outside the act count.",
                ),
            ),
            AuthoringJob(
                job_id="final_admission",
                kind="final_admission",
                executor="admission",
                depends_on=("music_bookends",),
                instructions=(
                    "Admit only a complete strict story; never repair accepted story bytes.",
                ),
            ),
        ]
    )
    return tuple(jobs)


class AuthoringSchedule(StrictAuthoringModel):
    act_count: int = Field(strict=True, ge=1, le=8)
    jobs: tuple[AuthoringJob, ...]

    @model_validator(mode="after")
    def validate_exact_schedule(self) -> "AuthoringSchedule":
        expected = _authoring_jobs(self.act_count)
        if self.jobs != expected:
            raise StoryAuthoringError(
                "authoring jobs must equal the centralized canonical schedule"
            )
        positions = {job.job_id: index for index, job in enumerate(self.jobs)}
        if len(positions) != len(self.jobs):
            raise StoryAuthoringError("authoring job IDs must be unique")
        for index, job in enumerate(self.jobs):
            for dependency in job.depends_on:
                dependency_index = positions.get(dependency)
                if dependency_index is None or dependency_index >= index:
                    raise StoryAuthoringError(
                        f"job {job.job_id!r} has an unavailable dependency"
                    )
        return self


def build_authoring_schedule(act_count: int) -> AuthoringSchedule:
    """Return the one canonical authoring schedule for ``act_count``."""

    if type(act_count) is not int:
        raise StoryAuthoringError("act_count must be a strict integer")
    if not 1 <= act_count <= 8:
        raise StoryAuthoringError("act_count must be between 1 and 8")
    return AuthoringSchedule(
        act_count=act_count,
        jobs=_authoring_jobs(act_count),
    )


class AuthoringAttempt(StrictAuthoringModel):
    attempt_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    kind: JobKind
    act_number: int | None = Field(default=None, strict=True, ge=1, le=8)
    attempt_number: int = Field(strict=True, ge=1)
    depends_on: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_attempt_identity(self) -> "AuthoringAttempt":
        if self.kind in _ACT_JOB_KINDS and self.act_number is None:
            raise StoryAuthoringError("act attempt requires act_number")
        if self.kind not in _ACT_JOB_KINDS and self.act_number is not None:
            raise StoryAuthoringError("non-act attempt cannot carry act_number")
        if self.job_id != _expected_job_id(self.kind, self.act_number):
            raise StoryAuthoringError(
                "attempt job_id does not match kind and act_number"
            )
        expected = f"{self.job_id}.attempt_{self.attempt_number:03d}"
        if self.attempt_id != expected:
            raise StoryAuthoringError("attempt_id does not bind job and number")
        return self


def make_authoring_attempt(
    job: AuthoringJob, attempt_number: int
) -> AuthoringAttempt:
    """Create a retry attempt without creating or renumbering a job."""

    if type(attempt_number) is not int or attempt_number < 1:
        raise StoryAuthoringError(
            "attempt_number must be a positive strict integer"
        )
    return AuthoringAttempt(
        attempt_id=f"{job.job_id}.attempt_{attempt_number:03d}",
        job_id=job.job_id,
        kind=job.kind,
        act_number=job.act_number,
        attempt_number=attempt_number,
        depends_on=job.depends_on,
    )


AllowedDraftRole = Literal[
    "music_open",
    "music_inter",
    "music_close",
    "announcer_open",
    "character_dialogue",
    "announcer_news_coda",
]
DraftDisposition = Literal["drop", "rewrite"]

_ALLOWED_DRAFT_ROLES = frozenset(
    {
        "music_open",
        "music_inter",
        "music_close",
        "announcer_open",
        "character_dialogue",
        "announcer_news_coda",
    }
)
_STANDALONE_FORBIDDEN_ROLES = frozenset(
    {"action", "stage_direction", "narration", "delivery_note"}
)
_EXPLICIT_NON_SPOKEN_FIELDS = (
    "action",
    "stage_direction",
    "narration",
    "delivery_note",
)
_PRODUCTION_CUE_RE = re.compile(
    r"^\s*(?:ACTION|STAGE\s+DIRECTION|NARRATION|DELIVERY\s+NOTE|"
    r"SFX|FX|SOUND|CUE)\s*:",
    re.IGNORECASE,
)
_DELIMITED_DIRECTION_RE = re.compile(
    r"(?:\[[^\]\r\n]+\]|\{[^}\r\n]+\}|\*[^*\r\n]+\*|"
    r"\([^()\r\n]*(?:pause|sigh|laugh|whisper|turn|look|walk|"
    r"gesture|nod|shrug|cough|enter|exit|music|sound)[^()\r\n]*\))",
    re.IGNORECASE,
)
_CHARACTER_NARRATION_RE = re.compile(
    r"\b(?:he|she|they)\s+(?:turns|looks|walks|nods|shrugs|sighs|"
    r"pauses|reaches|stands|steps)\b",
    re.IGNORECASE,
)
_WHOLE_LINE_CUE_RE = re.compile(
    r"^\s*(?:(?:the\s+)?(?:door|window|telephone|phone|bell|alarm|"
    r"radio|static|music|footsteps?)\s+(?:slams?|creaks?|rings?|"
    r"opens?|closes?|buzzes?|chimes?|swells?|fades?|plays?|starts?|"
    r"stops?|crackles?|approach(?:es)?|recedes?)|(?:pause|silence))"
    r"\s*[.!?]*\s*$",
    re.IGNORECASE,
)


class DraftRowIssue(StrictAuthoringModel):
    row_index: int = Field(strict=True, ge=0)
    role: str
    disposition: DraftDisposition
    reason: str


class DraftSanitizationResult(StrictAuthoringModel):
    retained_rows: tuple[dict[str, Any], ...]
    dropped_rows: tuple[DraftRowIssue, ...]
    rewrite_rows: tuple[DraftRowIssue, ...]

    @property
    def ready_for_admission(self) -> bool:
        return not self.rewrite_rows

    def admission_rows(self) -> tuple[dict[str, Any], ...]:
        """Return retained rows only when no ambiguous row needs rewriting."""

        if self.rewrite_rows:
            indexes = [issue.row_index for issue in self.rewrite_rows]
            raise StoryAuthoringError(
                f"draft rows {indexes} require rewrite before admission"
            )
        return copy.deepcopy(self.retained_rows)


def _draft_role(row: Mapping[str, Any]) -> str:
    for key in ("sequence_role", "role", "row_type", "type", "kind"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().casefold()
    return ""


def _embedded_non_spoken_reason(
    row: Mapping[str, Any],
    role: str,
    carried: Any | None = None,
) -> str | None:
    for field_name in _EXPLICIT_NON_SPOKEN_FIELDS:
        value = row.get(field_name)
        if value not in (None, "", [], {}, ()):
            return f"allowed row carries non-spoken field {field_name!r}"
    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    # Absolute rules: a cue or a direction is never speakable, whoever wrote
    # it, so a carried source can never excuse these three.
    if _PRODUCTION_CUE_RE.search(text):
        return "spoken text begins with a production/non-spoken cue"
    if _DELIMITED_DIRECTION_RE.search(text):
        return "spoken text contains a delimited stage direction"
    if _WHOLE_LINE_CUE_RE.fullmatch(text):
        return "spoken text is a standalone action or sound cue"
    if role == "character_dialogue" and _CHARACTER_NARRATION_RE.search(text):
        # Heuristic rule: it infers a model invented narration.  Literal
        # carriage from the source disproves that premise.
        if carried is not None and carried(text):
            return None
        return "character text contains high-confidence narrated action"
    return None


def sanitize_draft_sequence(
    rows: Sequence[Mapping[str, Any]],
    *,
    carried_source: Any | None = None,
) -> DraftSanitizationResult:
    """Conservatively project generic draft rows toward the sealed program.

    Standalone non-spoken rows are safely removable.  An allowed row carrying
    embedded or ambiguous non-spoken material is retained byte-for-value and
    marked for rewrite; this function never edits prose.  Strict Pydantic
    bodies are rejected because accepted story objects are outside this
    draft-only boundary.
    """

    if isinstance(rows, BaseModel):
        raise StoryAuthoringError(
            "draft sanitizer cannot alter a strict or accepted story body"
        )
    if isinstance(rows, (str, bytes, bytearray, Mapping)):
        raise StoryAuthoringError("draft rows must be a sequence of mappings")

    carried = None
    if carried_source is not None:
        contains = getattr(carried_source, "contains", None)
        if callable(contains):
            carried = lambda text: bool(text.strip()) and bool(contains(text))
        elif callable(carried_source):
            carried = lambda text: bool(text.strip()) and bool(
                carried_source(text)
            )
        else:
            raise StoryAuthoringError(
                "carried_source must expose contains(text) or be callable"
            )

    retained: list[dict[str, Any]] = []
    dropped: list[DraftRowIssue] = []
    rewrite: list[DraftRowIssue] = []
    for index, source_row in enumerate(rows):
        if not isinstance(source_row, Mapping):
            raise StoryAuthoringError(f"draft row {index} is not a mapping")
        row = copy.deepcopy(dict(source_row))
        role = _draft_role(row)
        if role in _STANDALONE_FORBIDDEN_ROLES:
            dropped.append(
                DraftRowIssue(
                    row_index=index,
                    role=role,
                    disposition="drop",
                    reason="standalone non-spoken row",
                )
            )
            continue
        if role not in _ALLOWED_DRAFT_ROLES:
            rewrite.append(
                DraftRowIssue(
                    row_index=index,
                    role=role,
                    disposition="rewrite",
                    reason="unknown or ambiguous draft row role",
                )
            )
            continue

        retained.append(row)
        reason = _embedded_non_spoken_reason(row, role, carried)
        if reason is not None:
            rewrite.append(
                DraftRowIssue(
                    row_index=index,
                    role=role,
                    disposition="rewrite",
                    reason=reason,
                )
            )

    return DraftSanitizationResult(
        retained_rows=tuple(retained),
        dropped_rows=tuple(dropped),
        rewrite_rows=tuple(rewrite),
    )


def _mapping_rows(
    rows: Sequence[Mapping[str, Any]], label: str
) -> list[dict[str, Any]]:
    if isinstance(rows, (str, bytes, bytearray, Mapping, BaseModel)):
        raise StoryAuthoringError(f"{label} must be a sequence of mappings")
    copied: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise StoryAuthoringError(f"{label} row {index} is not a mapping")
        copied.append(copy.deepcopy(dict(row)))
    return copied


def sweep_cast_after_dialogue(
    cast_rows: Sequence[Mapping[str, Any]],
    dialogue_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Retain the announcer plus characters owning actual dialogue.

    Input order is preserved.  Unknown dialogue owners fail rather than
    causing a cast or line to be invented.
    """

    cast = _mapping_rows(cast_rows, "cast")
    dialogue = _mapping_rows(dialogue_rows, "dialogue")
    cast_ids = [str(row.get("char_id") or "").strip() for row in cast]
    if any(not char_id for char_id in cast_ids):
        raise StoryAuthoringError("every cast row requires char_id")
    if len(cast_ids) != len(set(cast_ids)):
        raise StoryAuthoringError("cast char_id values must be unique")
    cast_by_id = dict(zip(cast_ids, cast, strict=True))
    announcer_ids = {
        char_id
        for char_id, row in cast_by_id.items()
        if str(row.get("cast_role") or "").casefold() == "announcer"
    }
    if len(announcer_ids) != 1:
        raise StoryAuthoringError("cast sweep requires exactly one announcer")

    dialogue_owner_ids: set[str] = set()
    for index, row in enumerate(dialogue):
        sequence_role = str(row.get("sequence_role") or "").casefold()
        speaker_role = str(row.get("speaker_role") or "").casefold()
        is_character_dialogue = sequence_role == "character_dialogue" or (
            not sequence_role and speaker_role == "character"
        )
        if not is_character_dialogue:
            continue
        if sequence_role == "character_dialogue" and speaker_role not in {
            "",
            "character",
        }:
            raise StoryAuthoringError(
                f"dialogue row {index} has conflicting speaker_role"
            )
        char_id = str(row.get("char_id") or "").strip()
        if not char_id:
            raise StoryAuthoringError(
                f"dialogue row {index} requires char_id"
            )
        cast_row = cast_by_id.get(char_id)
        if cast_row is None:
            raise StoryAuthoringError(
                f"dialogue owner {char_id!r} is not in the locked cast"
            )
        if str(cast_row.get("cast_role") or "").casefold() != "character":
            raise StoryAuthoringError(
                f"dialogue owner {char_id!r} is not a character"
            )
        dialogue_owner_ids.add(char_id)

    keep = announcer_ids | dialogue_owner_ids
    return tuple(
        copy.deepcopy(row)
        for char_id, row in zip(cast_ids, cast, strict=True)
        if char_id in keep
    )


__all__ = [
    "CLEANUP_JOB_INSTRUCTIONS",
    "DIALOGUE_JOB_INSTRUCTIONS",
    "AuthoringAttempt",
    "AuthoringJob",
    "AuthoringSchedule",
    "DraftRowIssue",
    "DraftSanitizationResult",
    "StoryAuthoringError",
    "build_authoring_schedule",
    "make_authoring_attempt",
    "sanitize_draft_sequence",
    "sweep_cast_after_dialogue",
]
