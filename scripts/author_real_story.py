"""Author one real story through a local model and save the sealed ledger.

This is the run the fake model cannot do: a genuine drama, written by an
actual model, admitted through the same acceptance rules and sealed the same
way.  Nothing about the ledger changes because the writer changed - that is
the whole point of a provider-neutral executor.

    # start a local server first (LM Studio, llama.cpp, Ollama...), then:
    python scripts/author_real_story.py --model <model-id> --bank science_news

Read the result with:

    python scripts/read_story.py output/real_stories/<file>.json --plan
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "src", ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from upstream_story_lab.authoring_executor import (  # noqa: E402
    AuthoringExecutionError,
    author_story_ledger,
)
from upstream_story_lab.local_model_provider import (  # noqa: E402
    DEFAULT_BASE_URL,
    LocalModelError,
    LocalModelProvider,
)
from upstream_story_lab.registry import Registry  # noqa: E402

OUT_DIR = ROOT / "output" / "real_stories"


def _brief_for(bank: str, act_count: int):
    """Reuse the committed proof briefs so only the writer changes."""

    if bank in {"science_news", "scifi_news"}:
        from generate_staged_authoring_fixture import build_fixture_brief

        brief = build_fixture_brief()
    else:
        from generate_bank_act_proofs import build_bank_brief

        brief = build_bank_brief(bank)
    return brief.model_copy(update={"act_count": act_count})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="model id on the server")
    parser.add_argument("--bank", default="science_news")
    parser.add_argument("--acts", type=int, default=3)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="attempts per job before the run fails loud",
    )
    parser.add_argument(
        "--save-transcript",
        action="store_true",
        help="also write every prompt and raw reply beside the ledger",
    )
    args = parser.parse_args(argv)

    known = sorted(Registry(ROOT).banks)
    if args.bank not in known:
        print(f"unknown bank {args.bank!r}; known: {known}")
        return 1

    brief = _brief_for(args.bank, args.acts).model_copy(
        update={"max_attempts_per_job": args.attempts}
    )
    provider = LocalModelProvider(
        args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        echo=True,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"{args.bank}_{args.acts}act_{stamp}.json"

    print(f"authoring {args.acts} acts on {args.bank} via {args.model}")
    print(f"schedule: {4 * args.acts + 7} jobs, {4 * args.acts + 4} model calls")
    print()
    try:
        result = author_story_ledger(
            brief,
            provider,
            sealed_at=datetime.now(timezone.utc).replace(microsecond=0),
            save_path=target,
        )
    except LocalModelError as exc:
        print(f"\nlocal model unavailable: {exc}")
        return 1
    except AuthoringExecutionError as exc:
        print(f"\nthe run did not produce an admissible story:\n  {exc}")
        if args.save_transcript and provider.transcript:
            path = target.with_suffix(".transcript.json")
            path.write_text(
                json.dumps(provider.transcript, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"transcript: {path}")
        return 1

    retries = [row for row in result.journal if row.status == "rejected"]
    print()
    print(f"SEALED {target}")
    print(f"  story_sha256 {result.envelope.story_seal.story_sha256}")
    print(f"  jobs {len(result.journal)}, rejected attempts {len(retries)}")
    for row in retries:
        print(f"    retry {row.job_id}: {row.reasons[0][:88] if row.reasons else ''}")
    if args.save_transcript:
        path = target.with_suffix(".transcript.json")
        path.write_text(
            json.dumps(provider.transcript, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  transcript {path}")
    print()
    print(f"read it:  python scripts/read_story.py {target} --plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
