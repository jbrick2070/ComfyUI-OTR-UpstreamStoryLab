"""Write or verify the staged-authoring three-act v2 ledger fixture.

The fixture is the go-forward proof that the staged executor can author one
complete fresh story through the locked schedule with a deterministic fake
model: sealed, admitted through the code-owned verifier registry, saved and
reloaded byte-for-byte.
"""

from __future__ import annotations

import argparse
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
from upstream_story_lab.scripted_provider import (  # noqa: E402
    ScriptedStoryProvider,
)

PACKET_PATH = (
    ROOT
    / "fixtures"
    / "story_recovery"
    / "v2"
    / "source_packets"
    / "science_news_folder_red_stamps_20260716.json"
)
FIXTURE_PATH = (
    ROOT / "fixtures" / "story_recovery" / "v2" / "staged_authoring_three_act.json"
)
FIXTURE_SEALED_AT = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)


def build_fixture_brief() -> AuthoringBrief:
    return AuthoringBrief(
        episode_id="staged_authoring_three_act_20260814",
        setting="Signal Lost studios",
        scene_time="nine o'clock PM",
        act_count=3,
        cast=(
            CastMember(
                char_id="announcer",
                name="ANNOUNCER",
                cast_role="announcer",
                character_description=(
                    "The period radio host who owns the program boundaries."
                ),
            ),
            CastMember(
                char_id="c02",
                name="OYA REEVES",
                cast_role="character",
                character_description=(
                    "A researcher carrying the weight of a dangerous "
                    "disclosure."
                ),
            ),
            CastMember(
                char_id="c03",
                name="ED STEELE",
                cast_role="character",
                character_description=(
                    "Oya's colleague, forced to confront the cost of their "
                    "work."
                ),
            ),
            CastMember(
                char_id="c04",
                name="DR. MARA VOSS",
                cast_role="character",
                character_description=(
                    "A station scientist who never enters tonight's drama; "
                    "the cast sweep must remove her."
                ),
            ),
        ),
        source_packet_bytes=PACKET_PATH.read_bytes(),
    )


def author_fixture(
    save_path: Path | None = None,
) -> StagedAuthoringResult:
    return author_story_ledger(
        build_fixture_brief(),
        ScriptedStoryProvider(),
        sealed_at=FIXTURE_SEALED_AT,
        save_path=save_path,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or verify the staged-authoring ledger fixture."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="author and save the fixture"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the fixture without changing the filesystem",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.write:
        result = author_fixture(save_path=FIXTURE_PATH)
        print(f"WROTE {FIXTURE_PATH.relative_to(ROOT)}")
        print(f"story_sha256 {result.envelope.story_seal.story_sha256}")
        return 0

    result = author_fixture(save_path=None)
    expected = canonical_bytes(result.envelope) + b"\n"
    if not FIXTURE_PATH.is_file():
        print(f"MISSING {FIXTURE_PATH.relative_to(ROOT)}")
        return 1
    if FIXTURE_PATH.read_bytes() != expected:
        print(f"STALE {FIXTURE_PATH.relative_to(ROOT)}")
        return 1
    print("staged-authoring fixture is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
