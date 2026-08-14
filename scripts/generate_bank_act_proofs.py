"""Write or verify one sealed act-based proof story per source bank.

Each bank on the roster authors one complete three-act story through the same
staged executor, with the guidance its own `fixtures/banks.json` entry
declares, and is admitted through the code-owned verifier registry.  This is
the receipt that every bank now runs on simplified act logic rather than
word-count logic while obeying the ledger.  The `scifi_news` proof is the
original executor fixture owned by `generate_staged_authoring_fixture.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from upstream_story_lab.authoring_executor import (  # noqa: E402
    AuthoringBrief,
    StagedAuthoringResult,
    author_story_ledger,
)
from upstream_story_lab.ledger_contract import (  # noqa: E402
    CastMember,
    canonical_bytes,
)
from upstream_story_lab.registry import Registry  # noqa: E402
from upstream_story_lab.scripted_provider import (  # noqa: E402
    ScriptedStoryProvider,
)
from upstream_story_lab.source_window import (  # noqa: E402
    build_lab_source_document,
)

PACKETS_DIR = ROOT / "fixtures" / "story_recovery" / "v2" / "source_packets"
PROOFS_DIR = ROOT / "fixtures" / "story_recovery" / "v2" / "bank_act_proofs"
#: Vendored Folger scene text + provenance sidecars, read by a proof that
#: declares `source_scene` so the adaptation lane proves itself against real
#: source prose rather than a synthetic stand-in.
SHAKESPEARE_SOURCES = ROOT / "fixtures" / "source_banks" / "shakespeare" / "sources"
PROOF_SEALED_AT = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)

BANK_PROOFS: dict[str, dict[str, str | tuple[tuple[str, str], ...]]] = {
    "media_archive": {
        "episode_id": "bank_act_proof_media_archive_20260814",
        "packet_file": "media_archive_wax_cylinders_20260814.json",
        "characters": (
            ("c02", "RUTH ADLER"),
            ("c03", "TOM BELL"),
        ),
    },
    "public_domain": {
        "episode_id": "bank_act_proof_public_domain_20260814",
        "packet_file": "public_domain_tell_tale_heart_20260814.json",
        "characters": (
            ("c02", "NORA QUINN"),
            ("c03", "SILAS PAGE"),
        ),
    },
    "custom_source_bank": {
        "episode_id": "bank_act_proof_custom_source_20260814",
        "packet_file": "custom_lighthouse_logbook_20260814.json",
        "characters": (
            ("c02", "JUNE HALE"),
            ("c03", "KEEPER ROSS"),
        ),
    },
    "scifi_news_pro": {
        "episode_id": "bank_act_proof_scifi_news_pro_20260814",
        "packet_file": "scifi_news_pro_slow_clock_20260814.json",
        "characters": (
            ("c02", "VERA LINDQVIST"),
            ("c03", "AMOS TATE"),
        ),
    },
    # The proof cast is the scene's own: this lane adapts a named Folger scene
    # rather than inventing speakers for it.
    "shakespeare": {
        "episode_id": "bank_act_proof_shakespeare_20260814",
        "packet_file": "shakespeare_macbeth_heath_20260814.json",
        "characters": (
            ("c02", "MACBETH"),
            ("c03", "BANQUO"),
        ),
        # Grounded on the real vendored scene, so this proof exercises what no
        # other lane does: act-proportional source windows, the fenced source
        # block, and the v4 carriage verifier that admits an adaptation.
        "source_scene": "macbeth__act1_scene3",
    },
    "original": {
        "episode_id": "bank_act_proof_original_20260814",
        "packet_file": "original_night_switchboard_20260814.json",
        "characters": (
            ("c02", "IRENE MADDOX"),
            ("c03", "WALT PEARSON"),
        ),
    },
}


def proof_path(source_bank_id: str) -> Path:
    return PROOFS_DIR / f"{source_bank_id}_three_act.json"


def build_bank_brief(source_bank_id: str) -> AuthoringBrief:
    spec = BANK_PROOFS[source_bank_id]
    bank = Registry(ROOT).bank(source_bank_id)
    cast = [
        CastMember(
            char_id="announcer",
            name="ANNOUNCER",
            cast_role="announcer",
            character_description=(
                "The period radio host who owns the program boundaries."
            ),
        )
    ]
    cast.extend(
        CastMember(
            char_id=char_id,
            name=name,
            cast_role="character",
            character_description=(
                f"A lead voice in tonight's {bank.label} drama."
            ),
        )
        for char_id, name in spec["characters"]
    )
    extra: dict[str, object] = {}
    scene = spec.get("source_scene")
    if scene:
        text = (SHAKESPEARE_SOURCES / f"{scene}.txt").read_text(encoding="utf-8")
        provenance = json.loads(
            (SHAKESPEARE_SOURCES / f"{scene}.provenance.json").read_text(
                encoding="utf-8"
            )
        )
        extra["source_document"] = build_lab_source_document(str(scene), text)
        extra["source_speaker_labels"] = tuple(provenance.get("speakers", ()))

    return AuthoringBrief(
        episode_id=str(spec["episode_id"]),
        setting="Signal Lost studios",
        scene_time="nine o'clock PM",
        act_count=3,
        cast=tuple(cast),
        source_packet_bytes=(PACKETS_DIR / str(spec["packet_file"])).read_bytes(),
        guidance=bank.staged_authoring_guidance,
        **extra,
    )


def author_bank_proof(
    source_bank_id: str, save_path: Path | None = None
) -> StagedAuthoringResult:
    return author_story_ledger(
        build_bank_brief(source_bank_id),
        ScriptedStoryProvider(),
        sealed_at=PROOF_SEALED_AT,
        save_path=save_path,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or verify per-bank act-logic proof fixtures."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="author and save every proof"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify every proof without changing the filesystem",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.write:
        PROOFS_DIR.mkdir(parents=True, exist_ok=True)
        for source_bank_id in BANK_PROOFS:
            result = author_bank_proof(
                source_bank_id, save_path=proof_path(source_bank_id)
            )
            print(
                f"WROTE {proof_path(source_bank_id).relative_to(ROOT)} "
                f"story_sha256 {result.envelope.story_seal.story_sha256}"
            )
        return 0

    failures = 0
    for source_bank_id in BANK_PROOFS:
        target = proof_path(source_bank_id)
        result = author_bank_proof(source_bank_id, save_path=None)
        expected = canonical_bytes(result.envelope) + b"\n"
        if not target.is_file():
            print(f"MISSING {target.relative_to(ROOT)}")
            failures += 1
        elif target.read_bytes() != expected:
            print(f"STALE {target.relative_to(ROOT)}")
            failures += 1
    if failures:
        print(f"bank act proofs failed: {failures} missing or stale file(s)")
        return 1
    print("bank act proofs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
