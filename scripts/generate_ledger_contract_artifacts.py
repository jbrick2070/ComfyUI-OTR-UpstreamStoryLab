"""Write or verify the generated Ledger Constitution artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from upstream_story_lab.ledger_artifacts import (  # noqa: E402
    render_contract_artifacts,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or verify the static ledger contract artifacts."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help="write all generated artifacts",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify artifacts without changing the filesystem",
    )
    return parser


def _write_artifacts(root: Path, artifacts: dict[str, str]) -> int:
    for relative_path, rendered in artifacts.items():
        target = root / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rendered.encode("utf-8"))
        print(f"WROTE {relative_path}")
    return 0


def _check_artifacts(root: Path, artifacts: dict[str, str]) -> int:
    failures = 0
    for relative_path, rendered in artifacts.items():
        target = root / Path(relative_path)
        if not target.is_file():
            print(f"MISSING {relative_path}")
            failures += 1
            continue
        if target.read_bytes() != rendered.encode("utf-8"):
            print(f"STALE {relative_path}")
            failures += 1
    if failures:
        print(
            f"ledger contract artifact check failed: {failures} "
            "missing or stale file(s)"
        )
        return 1
    print("ledger contract artifacts are current")
    return 0


def main(
    argv: list[str] | None = None, *, root: Path | None = None
) -> int:
    args = _parser().parse_args(argv)
    target_root = ROOT if root is None else root
    artifacts = render_contract_artifacts()
    if args.write:
        return _write_artifacts(target_root, artifacts)
    return _check_artifacts(target_root, artifacts)


if __name__ == "__main__":
    raise SystemExit(main())
