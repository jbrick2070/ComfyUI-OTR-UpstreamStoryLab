"""The source-carried exemption: otr.spoken-text-only.v2.

v1 rejects genuine spoken Shakespeare because a lexical rule cannot tell
`Sir, there she stands.` from `Ada turns to Leo...`.  v2 resolves that by
asking a different question - did these words come from the author? - and only
for the findings that infer authorship from prose shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from upstream_story_lab.source_window import (  # noqa: E402
    build_lab_source_document,
)
from upstream_story_lab.spoken_text_policy import (  # noqa: E402
    HEURISTIC_FINDING_CODES,
    SPOKEN_TEXT_POLICY_ID,
    SPOKEN_TEXT_POLICY_V2_ID,
    audit_spoken_text,
)
from upstream_story_lab.story_authoring import (  # noqa: E402
    sanitize_draft_sequence,
)

SCENES = ROOT / "fixtures" / "source_banks" / "shakespeare" / "sources"

CAST = [
    {"char_id": "announcer", "name": "ANNOUNCER", "cast_role": "announcer"},
    {"char_id": "c02", "name": "LEAR", "cast_role": "character"},
    {"char_id": "c03", "name": "CORDELIA", "cast_role": "character"},
]


@pytest.fixture()
def lear():
    return build_lab_source_document(
        "lear", (SCENES / "king_lear__act1_scene1.txt").read_text(encoding="utf-8")
    )


@pytest.fixture()
def macbeth():
    return build_lab_source_document(
        "macbeth", (SCENES / "macbeth__act1_scene3.txt").read_text(encoding="utf-8")
    )


def codes(text: str, source=None, *, char_id: str = "c02") -> list[str]:
    speaker = next(row["name"] for row in CAST if row["char_id"] == char_id)
    return [
        finding.code
        for finding in audit_spoken_text(
            [
                {
                    "line_id": "l001",
                    "char_id": char_id,
                    "speaker": speaker,
                    "speaker_role": "character",
                    "text": text,
                }
            ],
            CAST,
            carried_source=source,
        )
    ]


def test_policy_ids_are_distinct() -> None:
    assert SPOKEN_TEXT_POLICY_ID == "otr.spoken-text-only.v1"
    assert SPOKEN_TEXT_POLICY_V2_ID == "otr.spoken-text-only.v2"
    assert HEURISTIC_FINDING_CODES == {
        "quoted_novel_dialogue",
        "third_person_stage_business",
        "cross_speaker_attribution",
    }


@pytest.mark.parametrize(
    ("text", "char_id"),
    [
        # Lear, speaking aloud about someone standing in front of him.
        ("Sir, there she stands.", "c02"),
        # Cordelia, naming herself; verse wraps across lines, and a spoken
        # line joins them with a space.
        (
            "The jewels of our father, with washed eyes Cordelia leaves you.",
            "c03",
        ),
    ],
)
def test_faithfully_carried_shakespeare_is_exempt(
    lear, text: str, char_id: str
) -> None:
    assert codes(text, char_id=char_id) == [
        "third_person_stage_business"
    ], "v1 rejects it"
    assert codes(text, lear, char_id=char_id) == [], (
        "v2 admits the author's own words"
    )


def test_invented_narration_is_still_caught(lear) -> None:
    invented = "Lear turns to Cordelia, his hands shaking as he reaches for the map."
    assert codes(invented, lear) == ["third_person_stage_business"]


def test_exemption_is_bound_to_the_actual_source(lear, macbeth) -> None:
    """Carriage is proven against one body, not against 'sounds classical'."""

    text = "Sir, there she stands."
    assert codes(text, lear) == []
    assert codes(text, macbeth) == ["third_person_stage_business"]


def test_paraphrase_is_not_carriage(lear) -> None:
    """The exemption requires literal carriage, so a rewrite stays subject."""

    assert not lear.contains("Sir, there my daughter stands waiting.")
    assert codes("Sir, there she stands and waits for him.", lear) == [
        "third_person_stage_business"
    ]


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("[Thunder.]", "delimited_stage_direction"),
        ("SFX: the door slams.", "production_cue"),
    ],
)
def test_absolute_rules_are_never_exempt(macbeth, text: str, code: str) -> None:
    """A direction the source itself prints is still never speakable."""

    assert code in codes(text, macbeth)


def test_whole_line_stage_cue_is_never_exempt() -> None:
    """A row that is only a cue cannot ride the exemption."""

    source = build_lab_source_document("stagey", "The door slams. " * 40)
    assert source.contains("The door slams.")
    assert "third_person_stage_business" in codes("The door slams.", source)


@pytest.mark.parametrize(
    ("scene", "narration"),
    [
        ("king_lear__act1_scene1.txt", "He exits."),
        ("as_you_like_it__act3_scene2.txt", "They exit."),
    ],
)
def test_bracket_stripped_stage_direction_is_never_exempt(
    scene: str, narration: str
) -> None:
    """A source prints directions, so they are quotable from it.

    "[He exits.]" appears verbatim in the vendored text.  Strip the brackets
    and the line is literally carried, which would otherwise let a pure stage
    direction ride the exemption into the sealed ledger.  A row that is
    entirely stage action is never exempt, whoever wrote it.
    """

    document = build_lab_source_document(
        scene, (SCENES / scene).read_text(encoding="utf-8")
    )
    assert f"[{narration}]" in document.canonical_body
    assert document.contains(narration), "it really is carried text"
    assert codes(narration) == ["third_person_stage_business"]
    assert codes(narration, document) == ["third_person_stage_business"]


def test_sanitizer_applies_the_same_exemption(lear) -> None:
    """Both admission layers must agree, or faithful text still dies."""

    def rewrite(text: str, source=None) -> bool:
        return bool(
            sanitize_draft_sequence(
                [{"sequence_role": "character_dialogue", "text": text}],
                carried_source=source,
            ).rewrite_rows
        )

    carried = "Sir, there she stands."
    invented = "She turns away from the desk now."
    assert rewrite(carried) and not rewrite(carried, lear)
    assert rewrite(invented) and rewrite(invented, lear)


def test_v1_behaviour_is_untouched_without_a_source(lear) -> None:
    for text in (
        "Sir, there she stands.",
        "I checked the figures twice tonight.",
        "[Thunder.]",
    ):
        assert codes(text) == codes(text, None)


def test_exemption_only_ever_admits_never_rejects(lear) -> None:
    """v2 must be a strict relaxation: it can clear a finding, never add one.

    Measured over the vendored corpus, the exemption is narrow on purpose - it
    recovers the handful of genuinely carried lines v1 rejected and leaves
    everything else exactly as v1 judged it.
    """

    samples = [
        # Genuinely carried, and rejected by v1: these are what v2 exists for.
        ("Sir, there she stands.", "c02"),
        # Carried, but a whole stage action: must stay rejected.
        ("He exits.", "c02"),
        # Not carried at all.
        ("Lear turns to Cordelia and reaches for the map.", "c02"),
        # Ordinary speech neither policy objects to.
        ("I loved her most.", "c02"),
        ("Nothing will come of nothing. Speak again.", "c02"),
    ]
    recovered = 0
    for text, char_id in samples:
        v1 = set(codes(text, char_id=char_id))
        v2 = set(codes(text, lear, char_id=char_id))
        assert v2 <= v1, f"v2 invented a finding for {text!r}"
        recovered += len(v1 - v2)
    assert recovered >= 1, "the exemption must recover genuinely carried lines"
