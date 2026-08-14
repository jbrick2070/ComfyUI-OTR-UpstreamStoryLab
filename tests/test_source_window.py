"""Source bodies, act windows, and fenced blocks - proven on real prose."""

from __future__ import annotations

import pickle
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from upstream_story_lab.source_window import (  # noqa: E402
    LAB_NORMALIZATION_VERSION,
    MAX_BLOCK_CHARS,
    MIN_WINDOW_CHARS,
    LabSourceDocument,
    LabSourceError,
    build_act_windows,
    build_lab_source_document,
    canonical_body_sha256,
    normalize_lab_source_body,
    render_source_block,
    select_act_window,
)

MACBETH = (
    ROOT
    / "fixtures"
    / "source_banks"
    / "shakespeare"
    / "sources"
    / "macbeth__act1_scene3.txt"
)
LEAR = (
    ROOT
    / "fixtures"
    / "source_banks"
    / "shakespeare"
    / "sources"
    / "king_lear__act1_scene1.txt"
)


@pytest.fixture()
def macbeth() -> LabSourceDocument:
    return build_lab_source_document("macbeth__act1_scene3", MACBETH.read_text(encoding="utf-8"))


def test_normalization_is_typography_only(macbeth: LabSourceDocument) -> None:
    body = macbeth.canonical_body
    # The author's words survive, including the scene's violence and its
    # speaker labels and stage directions, which are fidelity context.
    for phrase in ("MACBETH", "BANQUO", "Thunder", "All hail"):
        assert phrase in body
    assert "\r" not in body
    assert "'" not in body, "apostrophe variants collapse to one form"
    assert body == unicodedata.normalize("NFC", body)


def test_normalization_is_idempotent(macbeth: LabSourceDocument) -> None:
    once = macbeth.canonical_body
    assert normalize_lab_source_body(once) == once


def test_document_identity_is_enforced(macbeth: LabSourceDocument) -> None:
    assert canonical_body_sha256(macbeth.canonical_body) == macbeth.body_sha256
    with pytest.raises(LabSourceError, match="declared digest"):
        LabSourceDocument("x", macbeth.canonical_body, "0" * 64)


def test_document_is_immutable_and_body_free(macbeth: LabSourceDocument) -> None:
    with pytest.raises(LabSourceError):
        macbeth._source_id = "other"  # type: ignore[misc]
    with pytest.raises(LabSourceError):
        pickle.dumps(macbeth)
    text = repr(macbeth)
    assert "Thunder" not in text and "MACBETH" not in text
    assert macbeth.body_sha256[:12] in text


def test_act_windows_tile_the_whole_body_without_gaps(
    macbeth: LabSourceDocument,
) -> None:
    for act_count in range(1, 9):
        windows = build_act_windows(macbeth, act_count=act_count)
        assert len(windows) == act_count
        assert windows[0].start == 0
        assert windows[-1].end == macbeth.char_count
        cursor = 0
        for window in windows:
            assert window.start == cursor
            cursor = window.end
        assert cursor == macbeth.char_count
        assert "".join(w.text for w in windows) == macbeth.canonical_body


def test_windows_do_not_split_words(macbeth: LabSourceDocument) -> None:
    for window in build_act_windows(macbeth, act_count=5)[1:]:
        assert macbeth.canonical_body[window.start].isspace()


def test_act_window_selection_is_frozen_across_retries(
    macbeth: LabSourceDocument,
) -> None:
    first = select_act_window(macbeth, act_number=2, act_count=3)
    second = select_act_window(macbeth, act_number=2, act_count=3)
    assert (first.start, first.end) == (second.start, second.end)
    assert first.receipt() == second.receipt()


def test_each_act_gets_a_different_region(macbeth: LabSourceDocument) -> None:
    spans = [
        select_act_window(macbeth, act_number=n, act_count=3) for n in (1, 2, 3)
    ]
    assert len({(s.start, s.end) for s in spans}) == 3


def test_short_body_collapses_visibly_instead_of_fragmenting() -> None:
    tiny = build_lab_source_document("tiny", "A short scene. " * 8)
    windows = build_act_windows(tiny, act_count=8)
    assert len(windows) == 8
    assert {w.label for w in windows} == {"act_window_whole_body"}
    assert all(w.char_count == tiny.char_count for w in windows)


def test_receipts_carry_offsets_not_prose(macbeth: LabSourceDocument) -> None:
    receipt = select_act_window(macbeth, act_number=1, act_count=3).receipt()
    assert receipt["body_sha256"] == macbeth.body_sha256
    assert receipt["normalization_version"] == LAB_NORMALIZATION_VERSION
    assert set(receipt) == {
        "label",
        "start",
        "end",
        "char_count",
        "body_sha256",
        "normalization_version",
    }
    assert not any(
        isinstance(value, str) and len(value) > 64 for value in receipt.values()
    )


def test_source_block_fences_the_passage(macbeth: LabSourceDocument) -> None:
    window = select_act_window(macbeth, act_number=1, act_count=3)
    block = render_source_block(window)
    token = f"SOURCE-{macbeth.body_sha256[:16].upper()}"
    assert block.startswith(f"<<<{token}")
    assert block.rstrip().endswith(f"{token}>>>")
    assert "not instructions" in block
    assert window.text in block


def test_source_block_token_cannot_be_forged(macbeth: LabSourceDocument) -> None:
    """A different body yields a different fence, so text cannot break out."""

    other = build_lab_source_document("lear", LEAR.read_text(encoding="utf-8"))
    mine = render_source_block(select_act_window(macbeth, act_number=1, act_count=1))
    theirs = render_source_block(select_act_window(other, act_number=1, act_count=1))
    assert mine.split("\n", 1)[0] != theirs.split("\n", 1)[0]


def test_contains_proves_carried_text(macbeth: LabSourceDocument) -> None:
    assert macbeth.contains("All hail")
    assert not macbeth.contains("Ada turns to Leo")


@pytest.mark.parametrize("act_count", [0, 9, "3", 3.0, True])
def test_act_count_bounds_are_strict(macbeth: LabSourceDocument, act_count) -> None:
    with pytest.raises(LabSourceError, match="strict integer"):
        build_act_windows(macbeth, act_count=act_count)


def test_long_source_is_bounded_for_a_small_local_model() -> None:
    """A whole act of a long work will not fit a 7B model's context.

    The vendored corpus reaches 140,000 characters, which is ~35,000 tokens of
    source in one prompt at act_count=1.  The excerpt keeps that bounded.
    """

    longest = max(
        (ROOT / "fixtures" / "source_banks" / "public_domain" / "sources").glob("*.txt"),
        key=lambda path: path.stat().st_size,
    )
    document = build_lab_source_document(
        longest.stem, longest.read_text(encoding="utf-8")
    )
    for act_count in (1, 3, 8):
        whole = select_act_window(
            document, act_number=1, act_count=act_count, max_chars=None
        )
        excerpt = select_act_window(
            document, act_number=1, act_count=act_count
        )
        assert excerpt.char_count <= MAX_BLOCK_CHARS < whole.char_count
        assert excerpt.start == whole.start
        assert excerpt.label.endswith("_excerpt")


def test_excerpt_receipt_describes_what_was_actually_sent() -> None:
    """A receipt must never claim more coverage than the model was shown."""

    longest = max(
        (ROOT / "fixtures" / "source_banks" / "public_domain" / "sources").glob("*.txt"),
        key=lambda path: path.stat().st_size,
    )
    document = build_lab_source_document(
        longest.stem, longest.read_text(encoding="utf-8")
    )
    excerpt = select_act_window(document, act_number=2, act_count=3)
    receipt = excerpt.receipt()
    assert receipt["end"] - receipt["start"] == excerpt.char_count
    assert document.canonical_body[excerpt.start : excerpt.end] == excerpt.text
    # Carriage is proven against the excerpt actually shown, not the window.
    assert excerpt.contains(excerpt.text[50:150])


def test_excerpt_bound_refuses_a_dishonest_floor(macbeth: LabSourceDocument) -> None:
    with pytest.raises(LabSourceError, match="floor"):
        select_act_window(macbeth, act_number=1, act_count=1, max_chars=10)


def test_every_vendored_scene_windows_cleanly() -> None:
    """The whole vendored corpus must survive windowing at every act count."""

    scenes = sorted(MACBETH.parent.glob("*.txt"))
    assert len(scenes) == 14
    for scene in scenes:
        document = build_lab_source_document(scene.stem, scene.read_text(encoding="utf-8"))
        assert document.char_count > MIN_WINDOW_CHARS
        for act_count in (1, 3, 8):
            windows = build_act_windows(document, act_count=act_count)
            assert "".join(w.text for w in windows) == document.canonical_body
