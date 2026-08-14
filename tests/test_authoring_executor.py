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
    assert len(model_records) == 3 * 3 + 4


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
    [(1, 10), (5, 22)],
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
