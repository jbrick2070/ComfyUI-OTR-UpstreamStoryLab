"""Staged authoring executor: scheduling, retry ownership, admission.

Every test drives the real locked schedule with the deterministic scripted
provider (or a tampering wrapper around it), so acceptance failures exercise
the actual retry routing and every accepted story passes the code-owned
verifier registry.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "src", ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from upstream_story_lab.authoring_executor import (  # noqa: E402
    AuthoringExecutionError,
    ModelJobRequest,
    StagedAuthoringResult,
    assign_story_facts,
    author_story_ledger,
    find_decode_runaway,
)
from upstream_story_lab.ledger_contract import canonical_bytes  # noqa: E402
from upstream_story_lab.ledger_io import load_ledger_envelope  # noqa: E402
from upstream_story_lab.ledger_verifiers import (  # noqa: E402
    build_trusted_receipt_verifiers,
)
from upstream_story_lab.scripted_provider import (  # noqa: E402
    ScriptedStoryProvider,
)
from upstream_story_lab.story_authoring import (  # noqa: E402
    build_authoring_schedule,
)
from generate_staged_authoring_fixture import (  # noqa: E402
    FIXTURE_PATH,
    FIXTURE_SEALED_AT,
    PACKET_PATH,
    author_fixture,
    build_fixture_brief,
)


class TamperingProvider:
    """Scripted provider that corrupts chosen attempts of one job."""

    def __init__(
        self,
        job_id: str,
        attempt_numbers: set[int],
        mutate,
    ) -> None:
        self.inner = ScriptedStoryProvider()
        self.job_id = job_id
        self.attempt_numbers = attempt_numbers
        self.mutate = mutate
        self.requests: list[ModelJobRequest] = []

    def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
        self.requests.append(request)
        payload = self.inner.run_job(request)
        if (
            request.job_id == self.job_id
            and request.attempt_number in self.attempt_numbers
        ):
            return self.mutate(dict(payload), request)
        return payload


def run_lab(
    provider=None,
    *,
    act_count: int = 3,
    max_attempts: int = 3,
    save_path=None,
) -> StagedAuthoringResult:
    brief = build_fixture_brief().model_copy(
        update={
            "act_count": act_count,
            "max_attempts_per_job": max_attempts,
        }
    )
    return author_story_ledger(
        brief,
        provider if provider is not None else ScriptedStoryProvider(),
        sealed_at=FIXTURE_SEALED_AT,
        save_path=save_path,
    )


def attempts_for(result: StagedAuthoringResult, job_id: str):
    return [record for record in result.journal if record.job_id == job_id]


def test_schedule_walk_matches_canonical_schedule() -> None:
    result = run_lab()
    schedule = build_authoring_schedule(3)
    assert [record.job_id for record in result.journal] == [
        job.job_id for job in schedule.jobs
    ]
    assert all(record.status == "accepted" for record in result.journal)
    assert all(record.attempt_number == 1 for record in result.journal)
    model_records = [
        record for record in result.journal if record.executor == "model"
    ]
    assert len(model_records) == 4 * 3 + 4
    # Every act gets its own model cleanup pass; code never edits prose.
    assert [
        record.job_id for record in result.journal if record.kind == "act_cleanup"
    ] == ["act_01.cleanup", "act_02.cleanup", "act_03.cleanup"]


def test_three_act_story_topology() -> None:
    result = run_lab()
    body = result.envelope.story_ledger.body

    assert body.context.act_count == 3
    assert len(body.acts) == 3
    roles = [item.sequence_role for item in body.sequence]
    assert roles[0] == "music_open" and roles[-1] == "music_close"
    spoken_roles = [
        item.sequence_role
        for item in body.sequence
        if item.ref_kind == "line"
    ]
    assert spoken_roles[0] == "announcer_open"
    assert spoken_roles[-1] == "announcer_news_coda"
    assert set(spoken_roles[1:-1]) == {"character_dialogue"}

    # The unused locked character must be swept, never given filler dialogue.
    assert [row.char_id for row in body.cast] == ["announcer", "c02", "c03"]

    # Every act beat is enacted by actual character dialogue.
    act_beat_ids = {
        beat_id for act in body.acts for beat_id in act.beat_ids
    }
    character_line_beats = {
        line.beat_id for line in body.lines if line.speaker_role == "character"
    }
    assert act_beat_ids == character_line_beats

    opener = body.lines[0]
    for phrase in (
        body.context.episode_title,
        body.context.setting,
        body.scenes[0].time,
        "OYA REEVES",
        "ED STEELE",
    ):
        assert phrase.casefold() in opener.text.casefold()

    coda = body.lines[-1]
    assert coda.fact_ids == ["F02"]
    closing_claim = next(
        fact.claim
        for fact in body.source_packet.facts
        if fact.fact_id == "F02"
    )
    assert closing_claim in coda.text

    interstitials = [
        cue for cue in body.music_cues if cue.request_authority == "script"
    ]
    assert [cue.cue_id for cue in interstitials] == ["music_inter_01"]
    inter_index = roles.index("music_inter")
    assert roles.index("character_dialogue") < inter_index
    assert inter_index < roles.index("announcer_news_coda")


def test_every_fact_is_cited_by_assignment() -> None:
    result = run_lab()
    body = result.envelope.story_ledger.body
    cited = {fact_id for line in body.lines for fact_id in line.fact_ids}
    assert cited == {"F01", "F02"}
    act_one_lines = [
        line
        for line in body.lines
        if line.beat_id in set(body.acts[0].beat_ids)
    ]
    assert any("F01" in line.fact_ids for line in act_one_lines)


def test_assign_story_facts_distribution() -> None:
    per_act, closing = assign_story_facts(["F01", "F02", "F03", "F04"], 2)
    assert closing == "F04"
    assert per_act == {1: ("F01", "F03"), 2: ("F02",)}
    per_act_single, closing_single = assign_story_facts(["F01"], 3)
    assert closing_single == "F01"
    assert per_act_single == {1: (), 2: (), 3: ()}


def test_save_reload_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "staged_authoring_roundtrip.json"
    result = run_lab(save_path=target)
    assert result.roundtrip_verified
    assert result.saved_path == str(target)
    packet_bytes = PACKET_PATH.read_bytes()
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={
            hashlib.sha256(packet_bytes).hexdigest(): packet_bytes
        }
    )
    loaded = load_ledger_envelope(target, receipt_verifiers=registry)
    assert canonical_bytes(loaded) == canonical_bytes(result.envelope)


def test_runs_are_deterministic() -> None:
    first = run_lab()
    second = run_lab()
    assert canonical_bytes(first.envelope) == canonical_bytes(second.envelope)


@pytest.mark.parametrize(
    ("act_count", "expected_jobs"),
    [(1, 11), (5, 27), (8, 39)],
)
def test_act_count_bounds_seal(act_count: int, expected_jobs: int) -> None:
    result = run_lab(act_count=act_count)
    assert len(result.journal) == expected_jobs
    body = result.envelope.story_ledger.body
    assert len(body.acts) == act_count
    assert body.context.act_count == act_count


def test_embedded_direction_retries_only_the_owning_act() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = "[She turns away] " + rows[0]["text"]
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_02.dialogue", {1}, mutate)
    result = run_lab(provider)

    records = attempts_for(result, "act_02.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any(
        "stage direction" in reason for reason in records[0].reasons
    )
    for record in result.journal:
        if record.job_id != "act_02.dialogue":
            assert record.status == "accepted"
            assert record.attempt_number == 1
    assert len(result.envelope.story_ledger.body.acts) == 3


def test_retry_feedback_reaches_the_next_attempt() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = "[She turns away] " + rows[0]["text"]
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_02.dialogue", {1}, mutate)
    run_lab(provider)
    retry_requests = [
        request
        for request in provider.requests
        if request.job_id == "act_02.dialogue"
        and request.attempt_number == 2
    ]
    assert len(retry_requests) == 1
    assert retry_requests[0].feedback
    assert "FEEDBACK ON YOUR PREVIOUS REJECTED ATTEMPT" in (
        retry_requests[0].prompt
    )


def test_standalone_direction_row_is_dropped_without_retry() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["rows"] = [
            *payload["rows"],
            {"role": "stage_direction", "text": "The lights dim."},
        ]
        return payload

    provider = TamperingProvider("act_01.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.dialogue")
    assert [record.status for record in records] == ["accepted"]
    assert any("dropped draft row" in note for note in records[0].notes)
    assert all(
        "The lights dim." not in line.text
        for line in result.envelope.story_ledger.body.lines
    )


def test_missing_beat_coverage_retries() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        last_beat_id = request.context["beats"][-1]["beat_id"]
        payload["rows"] = [
            row
            for row in payload["rows"]
            if row.get("beat_id") != last_beat_id
        ]
        return payload

    provider = TamperingProvider("act_03.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_03.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any(
        "no actual character dialogue" in reason
        for reason in records[0].reasons
    )


def test_beat_order_violation_retries() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["rows"] = list(reversed(payload["rows"]))
        return payload

    provider = TamperingProvider("act_01.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("beat order" in reason for reason in records[0].reasons)


def test_missing_assigned_fact_retries() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        for row in rows:
            row["fact_ids"] = []
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_01.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("F01" in reason for reason in records[0].reasons)


def test_opener_missing_character_name_retries() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["text"] = payload["text"].replace("ED STEELE", "a colleague")
        return payload

    provider = TamperingProvider("announcer_open", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "announcer_open")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("ED STEELE" in reason for reason in records[0].reasons)


def test_wrong_coda_fact_retries() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["fact_id"] = "F01"
        return payload

    provider = TamperingProvider("announcer_news_coda", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "announcer_news_coda")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("closing fact" in reason for reason in records[0].reasons)


def test_exhausted_retries_fail_loud() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = "[She turns away] " + rows[0]["text"]
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_01.dialogue", {1, 2}, mutate)
    with pytest.raises(AuthoringExecutionError) as excinfo:
        run_lab(provider, max_attempts=2)
    assert "act_01.dialogue" in str(excinfo.value)


def test_find_decode_runaway_spares_rhetoric_and_catches_loops() -> None:
    # Dramatic repetition passes: five repeats of one word is rhetoric.
    assert find_decode_runaway("Never, never, never, never, never.") is None
    assert (
        find_decode_runaway(
            "I checked the figures twice tonight, and the answer refuses "
            "to change."
        )
        is None
    )
    # A looping decoder repeating one phrase is caught.
    assert find_decode_runaway("the smoke will fall " * 8) is not None
    assert find_decode_runaway("no " * 30) is not None


def test_dialogue_decode_runaway_retries_owning_act() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = "the smoke will fall " * 8
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_01.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("decode runaway" in reason for reason in records[0].reasons)


def test_repeated_dialogue_line_retries_owning_act() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        for row in rows:
            if row.get("role") == "character_dialogue":
                row["text"] = "The same words again, exactly as before."
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_02.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_02.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("decode liveness" in reason for reason in records[0].reasons)


def test_payload_caps_reject_runaway_length() -> None:
    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["story_seed"] = "smoke and signal " * 400
        return payload

    provider = TamperingProvider("story_seed", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "story_seed")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("2000" in reason for reason in records[0].reasons)


def test_every_model_request_carries_a_decode_guard() -> None:
    class Recording(ScriptedStoryProvider):
        def __init__(self) -> None:
            self.requests: list[ModelJobRequest] = []

        def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
            self.requests.append(request)
            return super().run_job(request)

    provider = Recording()
    run_lab(provider)
    assert provider.requests
    for request in provider.requests:
        guard = request.decode_guard
        assert guard.max_new_tokens >= 1
        assert guard.recommended_repetition_penalty == 1.03
        assert guard.repetition_penalty_ceiling == 1.2
    dialogue_guards = {
        request.decode_guard.max_new_tokens
        for request in provider.requests
        if request.kind == "act_dialogue"
    }
    assert dialogue_guards == {2400}


def _cast(*rows: tuple[str, str, str]):
    from upstream_story_lab.ledger_contract import CastMember

    return tuple(
        CastMember(
            char_id=char_id,
            name=name,
            cast_role=role,
            character_description="A voice in tonight's drama.",
        )
        for char_id, name, role in rows
    )


ANNOUNCER_ROW = ("announcer", "ANNOUNCER", "announcer")


class CountingProvider(ScriptedStoryProvider):
    def __init__(self) -> None:
        self.calls = 0

    def run_job(self, request: ModelJobRequest):
        self.calls += 1
        return super().run_job(request)


def test_blind_cast_is_refused_before_any_model_call() -> None:
    """A shared name variant silently disables the narration detector.

    "MR. DARCY" also answers to "DARCY", so pairing the two makes the policy
    drop that variant from both rows.  Narrated prose then passes every gate
    and seals into the ledger - the exact defect the spoken-only law exists to
    stop - so the cast itself must be refused.
    """

    brief = build_fixture_brief().model_copy(
        update={
            "act_count": 1,
            "cast": _cast(
                ANNOUNCER_ROW,
                ("c02", "DARCY", "character"),
                ("c03", "MR. DARCY", "character"),
            ),
        }
    )
    provider = CountingProvider()
    with pytest.raises(Exception, match="blinds the narration detector"):
        author_story_ledger(
            brief, provider, sealed_at=FIXTURE_SEALED_AT, save_path=None
        )
    assert provider.calls == 0, "an unsafe brief must not buy any model work"


def test_blind_cast_would_otherwise_seal_narration() -> None:
    """Document why the refusal exists, using the detector directly."""

    from upstream_story_lab.spoken_text_policy import audit_spoken_text

    line = [
        {
            "line_id": "l001",
            "char_id": "c02",
            "speaker": "DARCY",
            "speaker_role": "character",
            "text": "Darcy turns away now.",
        }
    ]
    colliding = [
        {"char_id": "announcer", "name": "ANNOUNCER", "cast_role": "announcer"},
        {"char_id": "c02", "name": "DARCY", "cast_role": "character"},
        {"char_id": "c03", "name": "MR. DARCY", "cast_role": "character"},
    ]
    distinct = [row for row in colliding if row["char_id"] != "c03"]

    assert not audit_spoken_text(line, colliding)
    assert [f.code for f in audit_spoken_text(line, distinct)] == [
        "third_person_stage_business"
    ]


def test_non_nfc_operator_text_is_refused() -> None:
    import unicodedata

    brief = build_fixture_brief().model_copy(
        update={
            "cast": _cast(
                ANNOUNCER_ROW,
                ("c02", unicodedata.normalize("NFD", "RENÉE VOSS"), "character"),
                ("c03", "ED STEELE", "character"),
            )
        }
    )
    with pytest.raises(Exception, match="NFC"):
        author_story_ledger(
            brief,
            ScriptedStoryProvider(),
            sealed_at=FIXTURE_SEALED_AT,
            save_path=None,
        )


@pytest.mark.parametrize(
    "update",
    [
        {"scene_time": "--"},
        {
            "cast": _cast(
                ANNOUNCER_ROW,
                ("c02", "-", "character"),
                ("c03", "ED STEELE", "character"),
            )
        },
    ],
)
def test_unpronounceable_operator_text_is_refused(update: dict) -> None:
    """The opening validator must be satisfiable before work is scheduled."""

    brief = build_fixture_brief().model_copy(update=update)
    with pytest.raises(Exception, match="pronounceable"):
        author_story_ledger(
            brief,
            ScriptedStoryProvider(),
            sealed_at=FIXTURE_SEALED_AT,
            save_path=None,
        )


@pytest.mark.parametrize(
    "narration",
    [
        # Caught by the draft sanitizer's pronoun rule...
        "She turns away from the desk now.",
        # ...and this one falls through to the spoken-text policy's name rule.
        "Oya Reeves turns away from the desk now.",
    ],
)
def test_narration_is_caught_per_act_with_a_distinct_cast(
    narration: str,
) -> None:
    """Two independent layers reject narrated prose in a character row."""

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = narration
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_01.dialogue", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.dialogue")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("narrat" in reason for reason in records[0].reasons)
    assert all(
        "turns away" not in line.text
        for line in result.envelope.story_ledger.body.lines
    )


def test_bare_first_name_narration_is_a_known_v1_gap() -> None:
    """Pin the measured edge of the current policy.

    ``otr.spoken-text-only.v1`` recognizes a cast name and its
    honorific-stripped form, not a bare first name, so narration that uses
    only a first name escapes when the cast name has several words.  Widening
    this is a v2 decision, not a silent change: common first names collide
    with ordinary words.  This test documents the boundary so a future policy
    version has to move it deliberately.
    """

    from upstream_story_lab.spoken_text_policy import audit_spoken_text

    cast = [
        {"char_id": "announcer", "name": "ANNOUNCER", "cast_role": "announcer"},
        {"char_id": "c02", "name": "OYA REEVES", "cast_role": "character"},
    ]

    def audit(text: str) -> list[str]:
        return [
            finding.code
            for finding in audit_spoken_text(
                [
                    {
                        "line_id": "l001",
                        "char_id": "c02",
                        "speaker": "OYA REEVES",
                        "speaker_role": "character",
                        "text": text,
                    }
                ],
                cast,
            )
        ]

    assert audit("She turns away from the desk now.") == [
        "third_person_stage_business"
    ]
    assert audit("Oya Reeves turns away from the desk now.") == [
        "third_person_stage_business"
    ]
    assert audit("Oya turns away from the desk now.") == []


def test_cleanup_cannot_reassign_a_speaker() -> None:
    """Cleanup may reword, convert or drop a row; it may not re-assign one.

    A silent speaker swap would seal one character's words under another's
    voice, and would also keep a character the cast sweep should have removed.
    """

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        for row in rows:
            if row.get("char_id") == "c02":
                row["char_id"] = "c04"  # the deliberately unused cast row
                break
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_01.cleanup", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_01.cleanup")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("did not speak it" in reason for reason in records[0].reasons)
    # The unused character is still swept, and no line changed voice.
    assert [row.char_id for row in result.envelope.story_ledger.body.cast] == [
        "announcer",
        "c02",
        "c03",
    ]


def test_rejected_cleanup_leaves_the_act_intact() -> None:
    """A rejected cleanup must not half-replace the act it was repairing."""

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        rows = [dict(row) for row in payload["rows"]]
        rows[0]["text"] = "[Aside.] " + rows[0]["text"]
        payload["rows"] = rows
        return payload

    provider = TamperingProvider("act_02.cleanup", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_02.cleanup")
    assert [record.status for record in records] == ["rejected", "accepted"]
    body = result.envelope.story_ledger.body
    assert all("[Aside.]" not in line.text for line in body.lines)
    act_two_beats = set(body.acts[1].beat_ids)
    covered = {
        line.beat_id for line in body.lines if line.beat_id in act_two_beats
    }
    assert covered == act_two_beats, "every beat survived the rejected pass"


def test_unsayable_title_is_caught_where_it_is_authored() -> None:
    """The announcer must literally say the title.

    A title with no pronounceable word can never satisfy that, so without this
    guard the whole run dies at announcer_open - after every act has been paid
    for, with no attempt left to spend on a defect authored at the very start.
    """

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["episode_title"] = "***"
        return payload

    provider = TamperingProvider("story_seed", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "story_seed")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("pronounceable" in reason for reason in records[0].reasons)


@pytest.mark.parametrize(
    ("job_id", "key"),
    [
        ("story_seed", "episode_title"),
        ("story_arc", "summary"),
        ("act_01.spine", "spine"),
    ],
)
def test_composed_text_is_rejected_by_the_job_that_wrote_it(
    job_id: str, key: str
) -> None:
    """Canonical story bytes must be NFC, and the seal only says so at the end.

    Discovering it at final_admission loses the entire run; discovering it here
    costs one attempt.  Rejected with feedback, never silently normalized.
    """

    import unicodedata

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload[key] = unicodedata.normalize("NFD", "Café Nocturne rises")
        return payload

    provider = TamperingProvider(job_id, {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, job_id)
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("NFC" in reason for reason in records[0].reasons)


def test_coda_reports_both_faults_on_the_same_attempt() -> None:
    """Reporting one fault at a time would cost an attempt the run lacks."""

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["fact_id"] = "F01"
        payload["text"] = "And now, the news."
        return payload

    provider = TamperingProvider("announcer_news_coda", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "announcer_news_coda")
    assert [record.status for record in records] == ["rejected", "accepted"]
    reasons = records[0].reasons
    assert len(reasons) == 2
    assert any("closing fact" in reason for reason in reasons)
    # The expected claim is echoed, so the retry can carry it verbatim.
    assert any("Wildfires continue to spread" in reason for reason in reasons)


def test_cleanup_cannot_drop_an_authored_music_cue() -> None:
    """Cleanup may create a cue by conversion; it may not lose one it was given.

    An authored interstitial is already speakable-as-music and has nothing to
    repair, so losing it is content loss rather than cleanup.
    """

    def mutate(payload: dict[str, Any], request: ModelJobRequest):
        payload["rows"] = [
            row for row in payload["rows"] if row.get("role") != "music_inter"
        ]
        return payload

    provider = TamperingProvider("act_02.cleanup", {1}, mutate)
    result = run_lab(provider)
    records = attempts_for(result, "act_02.cleanup")
    assert [record.status for record in records] == ["rejected", "accepted"]
    assert any("dropped the music cue" in reason for reason in records[0].reasons)
    assert [
        cue.cue_id for cue in result.envelope.story_ledger.body.music_cues
    ] == ["music_open", "music_inter_01", "music_close"]


def test_seal_excuses_a_line_only_with_its_own_act_window() -> None:
    """The seal must apply the rule the act gate applied.

    Auditing against the whole document would let a line quote a region its
    own act never saw and pass a check its act job would have rejected.
    """

    from upstream_story_lab.source_window import (
        build_lab_source_document,
        select_act_window,
    )

    scene = (
        ROOT
        / "fixtures"
        / "source_banks"
        / "shakespeare"
        / "sources"
        / "king_lear__act1_scene1.txt"
    )
    document = build_lab_source_document(
        "lear", scene.read_text(encoding="utf-8")
    )
    first = select_act_window(document, act_number=1, act_count=3)
    third = select_act_window(document, act_number=3, act_count=3)

    # Text from the third act's region, which act one never received.
    foreign = third.text[200:280]
    assert document.contains(foreign), "the whole document does carry it"
    assert not first.contains(foreign), "act one's own window does not"
    assert first.end <= third.start, "the windows are disjoint"


def test_committed_fixture_is_current_and_loadable() -> None:
    result = author_fixture(save_path=None)
    expected = canonical_bytes(result.envelope) + b"\n"
    assert FIXTURE_PATH.is_file(), "run generate_staged_authoring_fixture.py --write"
    assert FIXTURE_PATH.read_bytes() == expected

    packet_bytes = PACKET_PATH.read_bytes()
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={
            hashlib.sha256(packet_bytes).hexdigest(): packet_bytes
        }
    )
    loaded = load_ledger_envelope(FIXTURE_PATH, receipt_verifiers=registry)
    assert canonical_bytes(loaded) == canonical_bytes(result.envelope)
