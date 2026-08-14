"""Every source bank authors a sealed act-based story and obeys the ledger.

One proof per bank: the bank's own declared guidance steers the prompts, the
story is admitted through the code-owned verifier registry, the committed
fixture regenerates byte-for-byte, and no word-count authority appears
anywhere on the staged path.
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
    ULTRASHORT_GUIDANCE,
    ModelJobRequest,
    author_story_ledger,
)
from upstream_story_lab.ledger_contract import canonical_bytes  # noqa: E402
from upstream_story_lab.ledger_io import load_ledger_envelope  # noqa: E402
from upstream_story_lab.ledger_verifiers import (  # noqa: E402
    build_trusted_receipt_verifiers,
)
from upstream_story_lab.registry import Registry  # noqa: E402
from upstream_story_lab.scripted_provider import (  # noqa: E402
    ScriptedStoryProvider,
)
from generate_bank_act_proofs import (  # noqa: E402
    BANK_PROOFS,
    PACKETS_DIR,
    PROOF_SEALED_AT,
    author_bank_proof,
    build_bank_brief,
    proof_path,
)
from generate_staged_authoring_fixture import (  # noqa: E402
    FIXTURE_PATH,
    PACKET_PATH,
    author_fixture,
    build_fixture_brief,
)

FORBIDDEN_WORD_AUTHORITY = (
    "word count",
    "word_count",
    "target_words",
    "target words",
    "max_words",
    "min_words",
    "word budget",
)

ALL_BANK_IDS = ("scifi_news", *BANK_PROOFS)


class RecordingProvider(ScriptedStoryProvider):
    def __init__(self) -> None:
        self.requests: list[ModelJobRequest] = []

    def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
        self.requests.append(request)
        return super().run_job(request)


def bank_brief(source_bank_id: str):
    if source_bank_id == "scifi_news":
        return build_fixture_brief()
    return build_bank_brief(source_bank_id)


def bank_fixture_path(source_bank_id: str) -> Path:
    if source_bank_id == "scifi_news":
        return FIXTURE_PATH
    return proof_path(source_bank_id)


def bank_packet_path(source_bank_id: str) -> Path:
    if source_bank_id == "scifi_news":
        return PACKET_PATH
    return PACKETS_DIR / str(BANK_PROOFS[source_bank_id]["packet_file"])


def author_proof(source_bank_id: str):
    if source_bank_id == "scifi_news":
        return author_fixture(save_path=None)
    return author_bank_proof(source_bank_id, save_path=None)


@pytest.mark.parametrize("source_bank_id", ALL_BANK_IDS)
def test_bank_proof_fixture_is_current(source_bank_id: str) -> None:
    result = author_proof(source_bank_id)
    target = bank_fixture_path(source_bank_id)
    assert target.is_file(), f"run the proof generator --write for {source_bank_id}"
    assert target.read_bytes() == canonical_bytes(result.envelope) + b"\n"


def carried_sources_for(source_bank_id: str) -> dict:
    """An adaptation lane's proof needs the windows its acts authored against.

    A version 4 ledger-integrity receipt fails closed without them, which is
    the point: a receipt claiming a carriage exemption cannot be trusted by a
    reader who was never given the source to check it against.
    """

    brief = bank_brief(source_bank_id)
    document = getattr(brief, "source_document", None)
    if document is None:
        return {}
    from upstream_story_lab.source_window import select_act_window

    return {
        f"a{act_number:03d}": select_act_window(
            document,
            act_number=act_number,
            act_count=brief.act_count,
            max_chars=brief.source_window_max_chars,
        )
        for act_number in range(1, brief.act_count + 1)
    }


@pytest.mark.parametrize("source_bank_id", ALL_BANK_IDS)
def test_bank_proof_obeys_the_ledger_from_disk(source_bank_id: str) -> None:
    packet_bytes = bank_packet_path(source_bank_id).read_bytes()
    registry = build_trusted_receipt_verifiers(
        packet_artifacts={
            hashlib.sha256(packet_bytes).hexdigest(): packet_bytes
        },
        carried_sources=carried_sources_for(source_bank_id),
    )
    envelope = load_ledger_envelope(
        bank_fixture_path(source_bank_id), receipt_verifiers=registry
    )
    body = envelope.story_ledger.body
    assert body.source_packet.source_bank_id == source_bank_id
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


@pytest.mark.parametrize("source_bank_id", ALL_BANK_IDS)
def test_bank_guidance_steers_prompts_without_word_authority(
    source_bank_id: str,
) -> None:
    provider = RecordingProvider()
    brief = bank_brief(source_bank_id)
    author_story_ledger(
        brief, provider, sealed_at=PROOF_SEALED_AT, save_path=None
    )

    declared = Registry(ROOT).bank(source_bank_id).staged_authoring_guidance
    assert brief.guidance.beats_per_act_low == declared.beats_per_act_low
    assert brief.guidance.beats_per_act_high == declared.beats_per_act_high

    beats_prompts = [
        request.prompt
        for request in provider.requests
        if request.kind == "act_beats"
    ]
    assert len(beats_prompts) == 3
    for prompt in beats_prompts:
        assert (
            f"[\n      {declared.beats_per_act_low},\n"
            f"      {declared.beats_per_act_high}\n    ]"
        ) in prompt or str(declared.beats_per_act_low) in prompt
        assert '"authority": "guidance"' in prompt

    for request in provider.requests:
        haystack = request.prompt.casefold()
        for token in FORBIDDEN_WORD_AUTHORITY:
            assert token not in haystack, (
                f"{request.job_id} prompt carries word-count authority "
                f"{token!r}"
            )


def test_ultrashort_guidance_authors_smallest_complete_drama() -> None:
    brief = build_fixture_brief().model_copy(
        update={"act_count": 1, "guidance": ULTRASHORT_GUIDANCE}
    )
    result = author_story_ledger(
        brief,
        ScriptedStoryProvider(),
        sealed_at=PROOF_SEALED_AT,
        save_path=None,
    )
    body = result.envelope.story_ledger.body
    assert len(body.acts) == 1
    assert len(body.acts[0].beat_ids) == 2
    # open + (2 beats x 2 exchanges) + coda
    assert len(body.lines) == 6
    # 4 * 1 + 7: the single act still gets its own cleanup pass.
    assert len(result.journal) == 11
