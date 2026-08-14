from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from upstream_story_lab.ledger_contract import StoryBody
from upstream_story_lab.story_authoring import (
    DIALOGUE_JOB_INSTRUCTIONS,
    AuthoringSchedule,
    StoryAuthoringError,
    build_authoring_schedule,
    make_authoring_attempt,
    sanitize_draft_sequence,
    sweep_cast_after_dialogue,
)

@pytest.mark.parametrize("act_count", range(1, 6))
def test_schedule_has_exact_stable_jobs_and_dependencies(act_count: int) -> None:
    schedule = build_authoring_schedule(act_count)
    expected_ids = ["story_seed", "story_arc"]
    for act_number in range(1, act_count + 1):
        expected_ids.extend(
            [
                f"act_{act_number:02d}.spine",
                f"act_{act_number:02d}.beats",
                f"act_{act_number:02d}.dialogue",
            ]
        )
    expected_ids.extend(
        [
            "cast_sweep",
            "announcer_open",
            "announcer_news_coda",
            "music_bookends",
            "final_admission",
        ]
    )

    assert schedule.act_count == act_count
    assert [job.job_id for job in schedule.jobs] == expected_ids
    assert len(schedule.jobs) == 3 * act_count + 7
    assert len([job for job in schedule.jobs if job.executor == "model"]) == (
        3 * act_count + 4
    )
    assert schedule.jobs[0].depends_on == ()
    assert schedule.jobs[1].depends_on == ("story_seed",)

    by_id = {job.job_id: job for job in schedule.jobs}
    for act_number in range(1, act_count + 1):
        spine = by_id[f"act_{act_number:02d}.spine"]
        beats = by_id[f"act_{act_number:02d}.beats"]
        dialogue = by_id[f"act_{act_number:02d}.dialogue"]
        expected_spine_dependencies = ["story_arc"]
        if act_number > 1:
            expected_spine_dependencies.append(
                f"act_{act_number - 1:02d}.dialogue"
            )
        assert spine.depends_on == tuple(expected_spine_dependencies)
        assert beats.depends_on == (spine.job_id,)
        assert dialogue.depends_on == (beats.job_id,)
        assert dialogue.instructions == DIALOGUE_JOB_INSTRUCTIONS
        assert dialogue.act_number == act_number

    dialogue_ids = tuple(
        f"act_{act_number:02d}.dialogue"
        for act_number in range(1, act_count + 1)
    )
    assert by_id["cast_sweep"].depends_on == dialogue_ids
    assert by_id["announcer_open"].act_number is None
    assert by_id["announcer_news_coda"].act_number is None
    assert by_id["music_bookends"].executor == "compiler"
    assert by_id["final_admission"].executor == "admission"

    positions = {job.job_id: index for index, job in enumerate(schedule.jobs)}
    for job in schedule.jobs:
        assert all(positions[dependency] < positions[job.job_id] for dependency in job.depends_on)


@pytest.mark.parametrize("value", [0, 6, -1, True, False, 3.0, "3", None])
def test_act_count_is_a_strict_integer_between_one_and_five(value) -> None:
    with pytest.raises(StoryAuthoringError):
        build_authoring_schedule(value)


def test_schedule_has_no_source_bank_or_global_word_control() -> None:
    dumped = build_authoring_schedule(5).model_dump(mode="json")
    serialized = json.dumps(dumped, sort_keys=True).casefold()

    assert "source_bank" not in serialized
    assert "target_words" not in serialized
    assert "word_count" not in serialized
    assert "duration" not in serialized


def test_canonical_schedule_cannot_be_reordered_or_extended() -> None:
    schedule = build_authoring_schedule(2)
    jobs = list(schedule.jobs)
    jobs[2], jobs[3] = jobs[3], jobs[2]

    with pytest.raises(
        (StoryAuthoringError, ValidationError),
        match="canonical schedule",
    ):
        AuthoringSchedule(act_count=2, jobs=tuple(jobs))


def test_retries_are_attempts_on_the_same_job_not_new_acts() -> None:
    schedule = build_authoring_schedule(3)
    dialogue_job = next(
        job for job in schedule.jobs if job.job_id == "act_02.dialogue"
    )

    first = make_authoring_attempt(dialogue_job, 1)
    retry = make_authoring_attempt(dialogue_job, 2)

    assert first.attempt_id == "act_02.dialogue.attempt_001"
    assert retry.attempt_id == "act_02.dialogue.attempt_002"
    assert retry.job_id == first.job_id == dialogue_job.job_id
    assert retry.kind == first.kind == "act_dialogue"
    assert retry.act_number == first.act_number == 2
    assert retry.depends_on == first.depends_on == dialogue_job.depends_on
    assert len(schedule.jobs) == 16
    assert len([job for job in schedule.jobs if job.kind == "act_spine"]) == 3

    for invalid in (0, -1, True, 1.5, "2"):
        with pytest.raises(StoryAuthoringError):
            make_authoring_attempt(dialogue_job, invalid)


def test_dialogue_contract_is_repeated_verbatim_for_every_act() -> None:
    schedule = build_authoring_schedule(5)
    dialogue_jobs = [job for job in schedule.jobs if job.kind == "act_dialogue"]

    assert len(dialogue_jobs) == 5
    assert {job.instructions for job in dialogue_jobs} == {
        DIALOGUE_JOB_INSTRUCTIONS
    }
    joined = " ".join(DIALOGUE_JOB_INSTRUCTIONS).casefold()
    assert "actual spoken dialogue" in joined
    assert "assigned speaker" in joined
    assert "stage directions" in joined
    assert "narration" in joined


def test_draft_sanitizer_drops_only_standalone_non_spoken_rows() -> None:
    rows = [
        {"sequence_role": "music_open", "ref_id": "m_open"},
        {"sequence_role": "announcer_open", "text": "Tonight, our story begins."},
        {"sequence_role": "action", "text": "A door opens."},
        {"sequence_role": "character_dialogue", "text": "I heard you the first time."},
        {"sequence_role": "stage_direction", "text": "She crosses the room."},
        {"sequence_role": "narration", "text": "The storm grows."},
        {"sequence_role": "delivery_note", "text": "Read softly."},
        {"sequence_role": "announcer_news_coda", "text": "The real report follows."},
        {"sequence_role": "music_close", "ref_id": "m_close"},
    ]
    before = copy.deepcopy(rows)

    result = sanitize_draft_sequence(rows)

    assert rows == before
    assert [row["sequence_role"] for row in result.retained_rows] == [
        "music_open",
        "announcer_open",
        "character_dialogue",
        "announcer_news_coda",
        "music_close",
    ]
    assert [issue.role for issue in result.dropped_rows] == [
        "action",
        "stage_direction",
        "narration",
        "delivery_note",
    ]
    assert result.rewrite_rows == ()
    assert result.ready_for_admission is True
    assert result.admission_rows() == result.retained_rows


@pytest.mark.parametrize(
    "row",
    [
        {
            "sequence_role": "character_dialogue",
            "text": "[turns away] I cannot answer that.",
        },
        {
            "sequence_role": "character_dialogue",
            "text": "She turns toward the window. I cannot answer that.",
        },
        {
            "sequence_role": "character_dialogue",
            "text": "Door slams.",
        },
        {
            "sequence_role": "announcer_open",
            "text": "ACTION: Raise the curtain.",
        },
        {
            "sequence_role": "character_dialogue",
            "text": "I cannot answer that.",
            "delivery_note": "whispered",
        },
        {"sequence_role": "uncertain_prose", "text": "Perhaps a line."},
    ],
)
def test_embedded_or_ambiguous_prose_is_marked_not_rewritten(row: dict) -> None:
    original = copy.deepcopy(row)
    result = sanitize_draft_sequence([row])

    assert row == original
    assert len(result.rewrite_rows) == 1
    assert result.ready_for_admission is False
    if row["sequence_role"] in {
        "announcer_open",
        "character_dialogue",
    }:
        assert result.retained_rows == (original,)
    else:
        assert result.retained_rows == ()
    with pytest.raises(StoryAuthoringError, match="require rewrite"):
        result.admission_rows()


def test_draft_sanitizer_rejects_an_accepted_story_body() -> None:
    # The draft-only boundary rejects by model type before it can inspect or
    # serialize any accepted-story fields.  model_construct keeps this test
    # independent of whichever complete golden fixture owns the current schema.
    body = StoryBody.model_construct()

    with pytest.raises(StoryAuthoringError, match="accepted story body"):
        sanitize_draft_sequence(body)  # type: ignore[arg-type]


def test_draft_sanitizer_keeps_legitimate_reported_speech() -> None:
    row = {
        "sequence_role": "character_dialogue",
        "text": "She says the code is wrong, and I believe her.",
    }

    result = sanitize_draft_sequence([row])

    assert result.ready_for_admission is True
    assert result.retained_rows == (row,)


def test_cast_sweep_keeps_announcer_and_only_dialogue_owners() -> None:
    cast = [
        {"char_id": "announcer", "cast_role": "announcer", "name": "ANNOUNCER"},
        {"char_id": "c01", "cast_role": "character", "name": "ADA"},
        {"char_id": "c02", "cast_role": "character", "name": "LEO"},
        {"char_id": "c03", "cast_role": "character", "name": "MARA"},
    ]
    dialogue = [
        {
            "sequence_role": "character_dialogue",
            "char_id": "c02",
            "text": "We should tell them now.",
        },
        {
            "speaker_role": "character",
            "char_id": "c01",
            "text": "Not until the evidence is safe.",
        },
        {
            "sequence_role": "announcer_open",
            "speaker_role": "announcer",
            "char_id": "announcer",
            "text": "Tonight's story begins.",
        },
        {
            "char_id": "c03",
            "text": "Unlabeled planning prose must not retain this character.",
        },
    ]
    cast_before = copy.deepcopy(cast)
    dialogue_before = copy.deepcopy(dialogue)

    swept = sweep_cast_after_dialogue(cast, dialogue)

    assert cast == cast_before
    assert dialogue == dialogue_before
    assert [row["char_id"] for row in swept] == ["announcer", "c01", "c02"]
    assert [row["text"] for row in dialogue] == [
        "We should tell them now.",
        "Not until the evidence is safe.",
        "Tonight's story begins.",
        "Unlabeled planning prose must not retain this character.",
    ]


def test_cast_sweep_never_invents_unknown_dialogue_owner() -> None:
    cast = [
        {"char_id": "announcer", "cast_role": "announcer"},
        {"char_id": "c01", "cast_role": "character"},
    ]

    with pytest.raises(StoryAuthoringError, match="not in the locked cast"):
        sweep_cast_after_dialogue(
            cast,
            [{"char_id": "c99", "speaker_role": "character", "text": "Hello."}],
        )


def test_cast_sweep_requires_one_announcer_and_unique_cast_ids() -> None:
    with pytest.raises(StoryAuthoringError, match="exactly one announcer"):
        sweep_cast_after_dialogue(
            [{"char_id": "c01", "cast_role": "character"}],
            [],
        )
    with pytest.raises(StoryAuthoringError, match="must be unique"):
        sweep_cast_after_dialogue(
            [
                {"char_id": "announcer", "cast_role": "announcer"},
                {"char_id": "announcer", "cast_role": "character"},
            ],
            [],
        )
