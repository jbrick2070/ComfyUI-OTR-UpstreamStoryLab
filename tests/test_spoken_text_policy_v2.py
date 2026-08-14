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


def test_whole_corpus_admission_rate_improves(lear) -> None:
    """Carrying a whole scene's speeches must not be a losing proposition."""

    body = lear.canonical_body
    speeches = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("[")
    ][:60]
    rejected_v1 = sum(1 for text in speeches if codes(text))
    rejected_v2 = sum(1 for text in speeches if codes(text, lear))
    assert rejected_v2 < rejected_v1
