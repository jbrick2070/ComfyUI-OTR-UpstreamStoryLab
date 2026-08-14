"""Render a sealed ledger as a readable radio script.

Judging a story means reading it, not squinting at JSON.  This prints the
program in broadcast order - music, announcer, the acts, the coda, music - with
the act boundaries marked, so the drama can be read the way a listener hears
it.  It reads only; it never writes or repairs a ledger.

    python scripts/read_story.py <ledger.json> [--plan] [--facts]

    --plan   also show the planning metadata that never reaches TTS:
             the story seed, the arc summary, each act's spine and states,
             and every beat intent
    --facts  also show the captured source facts and who cites them
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

WIDTH = 78


def _wrap(text: str, indent: str = "      ") -> str:
    return textwrap.fill(
        " ".join(text.split()),
        width=WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
    )


def _rule(title: str = "") -> str:
    if not title:
        return "-" * WIDTH
    return f"--- {title} " + "-" * max(0, WIDTH - len(title) - 5)


def read_story(path: Path, show_plan: bool, show_facts: bool) -> int:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    ledger = envelope["story_ledger"]
    body = ledger["body"]
    context = body["context"]
    packet = body["source_packet"]

    lines = {row["line_id"]: row for row in body["lines"]}
    cues = {row["cue_id"]: row for row in body["music_cues"]}
    beats = {row["beat_id"]: row for row in body["beats"]}
    acts = {row["act_id"]: row for row in body["acts"]}
    scene = body["scenes"][0]
    cast = {row["char_id"]: row for row in body["cast"]}
    facts = {row["fact_id"]: row for row in packet["facts"]}

    print()
    print("=" * WIDTH)
    print(f"  {context['episode_title'].upper()}")
    print(f"  {context['act_count']}-act drama | {scene['setting']} | {scene['time']}")
    print(f"  bank: {packet['source_bank_id']}   episode: {ledger['episode_id']}")
    print("=" * WIDTH)
    print()
    print("  CAST")
    for row in body["cast"]:
        role = "announcer" if row["cast_role"] == "announcer" else "character"
        print(f"    {row['name']:<22} ({role})")
        if row.get("character_description"):
            print(_wrap(row["character_description"], "        "))
    print()

    if show_plan:
        print(_rule("PLANNING (never spoken)"))
        print(_wrap(f"seed: {context['story_seed']}", "  "))
        print(_wrap(f"arc:  {body['story_arc']['summary']}", "  "))
        for act_id in body["story_arc"]["act_ids"]:
            act = acts[act_id]
            print()
            print(f"  ACT {act['act_number']}")
            print(_wrap(f"spine: {act['spine']}", "    "))
            print(_wrap(f"enters: {act['entry_state']}", "    "))
            print(_wrap(f"exits:  {act['exit_state']}", "    "))
        print()

    if show_facts:
        print(_rule("CAPTURED SOURCE"))
        for source in packet["sources"]:
            print(f"  {source['title']}")
            print(f"    {source['locator']}")
        for fact_id, fact in facts.items():
            citers = [
                lines[l]["speaker"]
                for l in lines
                if fact_id in lines[l]["fact_ids"]
            ]
            print()
            print(_wrap(f"[{fact_id}] {fact['claim']}", "  "))
            print(f"      cited by: {', '.join(citers) if citers else 'NOBODY'}")
        print()

    print(_rule("AS BROADCAST"))
    print()
    current_act = None
    spoken = 0
    for item in body["sequence"]:
        role = item["sequence_role"]
        if item["ref_kind"] == "music_cue":
            cue = cues[item["ref_id"]]
            label = {
                "music_open": "MUSIC UP",
                "music_close": "MUSIC OUT",
                "music_inter": "MUSIC",
            }[role]
            print(f"  [{label}] {cue['description']}")
            print()
            continue

        line = lines[item["ref_id"]]
        beat = beats[line["beat_id"]]
        act_id = beat.get("act_id")
        if act_id != current_act:
            current_act = act_id
            if act_id is not None:
                act = acts[act_id]
                print(_rule(f"ACT {act['act_number']}"))
                print()
        if show_plan and act_id is not None:
            print(f"      . beat {beat['beat_id']}: {beat['intent']}")
        print(f"  {line['speaker']}:")
        print(_wrap(line["text"]))
        if line["fact_ids"]:
            print(f"      [cites {', '.join(line['fact_ids'])}]")
        print()
        spoken += 1

    print(_rule())
    outcomes = ledger["validation"]["outcomes"]
    print(f"  {spoken} spoken rows | {len(body['music_cues'])} music cues | "
          f"{len(body['beats'])} beats")
    print(f"  receipts: {', '.join(sorted(outcomes))}")
    print(f"  sealed:   {envelope['story_seal']['story_sha256'][:32]}...")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--facts", action="store_true")
    args = parser.parse_args(argv)
    if not args.ledger.is_file():
        print(f"no such ledger: {args.ledger}")
        return 1
    return read_story(args.ledger, args.plan, args.facts)


if __name__ == "__main__":
    raise SystemExit(main())
