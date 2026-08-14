# GO FORWARD PLAN — OTR Act-Based Story Lab

Updated: 2026-08-14. This is the current handoff. The Story Lab ledger is
enshrined and pushed; production OTR has not been changed.

## Outcome now locked

The final playable script may contain only:

```text
music
announcer opening
character dialogue
announcer factual news/media/science coda
music
```

Optional interstitial music may appear only inside the character drama. No
action row, stage direction, third-person narration, or delivery note may be
sealed or sent to TTS. Planning metadata may describe story, arc, acts, scenes,
states, beats, and intent, but it is never a spoken row.

The pre-seal cleaner drops clearly standalone non-spoken draft rows. If prose is
embedded ambiguously inside a proposed speech row, that act returns to its
dialogue job. Trusted admission never rewrites an accepted StoryBody. After
dialogue, the cast sweep keeps exactly one announcer plus only characters that
own accepted dialogue; it never invents filler dialogue.

This directly guards the two observed failures in “The Light of Possibility”:
character rows contained stage/novel narration, and the opening failed to
introduce the scene and final speaking characters. The pinned challenger is:

- video:
  `C:\Users\jeffr\Documents\ComfyUI\output\otr\obs\signal_lost_the_light_of_possibility_20260813_172801_silent_procgen_blended_captioned_with_credits_final.mp4`
- live ledger:
  `C:\Users\jeffr\Documents\ComfyUI\output\otr\episodes\signal_lost_the_light_of_possibility_20260813_172801\audio\signal_lost_the_light_of_possibility_20260813_172801_ledger.json`
- frozen recovery projection:
  `fixtures/story_recovery/scifi_news_bad_20260813.json`

## One hard length knob

The only visible story-length control is strict integer `act_count=1..5`.
There is no `auto`, global target-word variable, word-count admission gate, or
hardware-derived act count. Words and rendered minutes are observations.

`act_count` creates actual scheduled model work rather than merely appearing in
one large prompt:

```text
source packet
  -> story seed
  -> one X-act arc
  -> for each ordered act: spine -> beats -> dialogue
  -> cast sweep
  -> announcer opening
  -> factual announcer coda
  -> compiler-owned music bookends
  -> trusted admission and story seal
```

The stable schedule is `3 * act_count + 7` jobs. The base model schedule is
`3 * act_count + 4` calls before retries: 7 calls for one act through 19 calls
for five acts. A retry is another attempt on the same job and never creates an
extra act.

Beat count, exchange count, and approximate duration may be soft per-bank or
per-model guidance. They are not universal ledger laws. The hard requirement
is that every accepted beat is enacted by actual character dialogue and every
act contains coherent entry, development, and exit state.

A 3060, 5090, or cloud route may change provider, model size, batching,
latency, context packing, and retry cost. It must not change the ledger shape,
act count, or spoken-only rule.

## Central compiler, creative banks

All four runnable banks retain control over source selection, tone, factual
material, and creative prompt content:

- `custom_source_bank`
- `media_archive`
- `public_domain_story`
- `science_news`

Every bank now declares the same central compiler and exact act schedule. No
bank may bypass draft cleanup, cast sweep, semantic admission, or the story
seal. This keeps upstream creative freedom while giving downstream production
one trustworthy ABI.

## Ledger constitution — complete in Story Lab

The v2 envelope now has executable:

- immutable `story_ledger` plus five code-owned semantic receipts;
- `story_seal` over exact canonical story bytes;
- typed append-only `production_state` for all 18 registered phases;
- terminal `final_seal` after active publication and successful terminal audit;
- strict v2-only adapter `otr.story-lab.production-adapter` version `1`;
- deterministic UTF-8/LF/no-BOM atomic save/load with fresh story, production,
  and final-seal verification;
- generated Draft 2020-12 schema and 1,322-path lifecycle reference.

The adapter proves canonical StoryBody, StoryLedger, every StorySeal field, and
`story_sha256` remain exact when production state is attached. v1 recovery
fixtures and current-l4 ledgers are evidence only; there is no silent migration.

Authorities:

- `docs/LEDGER_BIBLE.md`
- `contracts/ledger_bible_v2.json`
- `contracts/ledger_envelope_v2.schema.json`
- `contracts/ledger_field_laws_v2.json`
- `src/upstream_story_lab/ledger_contract.py`
- `src/upstream_story_lab/story_authoring.py`
- `src/upstream_story_lab/ledger_io.py`
- `fixtures/story_recovery/v2/`

## Current receipt

- Repo/branch: `ComfyUI-OTR-UpstreamStoryLab`, `main`.
- Enshrined implementation baseline (before this handoff-only commit):
  `183298160142acd139e0120462c65e64ce28a4db`, pushed to `origin/main`.
- Main constitution chunks:
  - `e999c40` — typed production journal;
  - `6033098` — act-based ledger v2 and spoken-only authoring compiler;
  - `b01ef65` — generated v2 schema and field laws;
  - `74c2c1b` — terminal seal plus strict adapter/save/load proof;
  - `1832981` — enshrined human/machine constitution.
- Full suite: 312 passed.
- Generated artifact `--check`: passed.
- `validate_lab.py`: 4 banks, 12 packs, 55 specs, 5 visual styles, 3
  public-domain manifests, no mirror drift.
- `smoke_nodes.py`: passed.
- `verify_tree.py`: 70 Python files, 45 JSON files, 0 errors.
- `git diff --check`: passed.
- No Bug Bible runner exists in this repository.

Production OTR remains unchanged at `707b39e9` on `v2.0-alpha`, equal to its
remote at the last read-only check. Its existing untracked operator files were
not touched. The production mirror in this lab is historical characterization,
not authority for the current production head.

## What is next — prove one fresh story in the Lab

Do not jump directly into another production render. The next implementation
slice is a provider-neutral staged authoring executor and prompt layer over the
already locked schedule:

1. Compile one bank packet into a source-grounded story-seed job.
2. Ask for one coherent arc containing exactly the operator-selected acts.
3. For each act in order, run separate spine, beat-plan, and dialogue jobs.
4. Give every dialogue job the locked cast, source facts, full arc, current act
   spine/states, prior exit state, and exact beat IDs/intents.
5. Repeat in every dialogue prompt: output only words spoken aloud by the
   assigned character; no stage directions, action, narration, delivery notes,
   or another speaker’s words.
6. Sanitize the draft. Drop safe standalone cues; retry only the owning act for
   ambiguous embedded prose or missing dialogue.
7. Sweep unused characters, then write the announcer opening from the final
   title/setting/scene/time/cast and the coda from captured source facts.
8. Add compiler music bookends, admit all five outcomes, seal, save, reload,
   and compare exact story bytes.

Start with an injected deterministic fake model so scheduling, retry ownership,
context assembly, and ledger compilation are testable without a GPU. Then run
one real Lab story through a deliberately chosen local or cloud route. The
proof is a newly authored v2 ledger that passes admission and visibly contains
only music, announcer, and character dialogue—not a word-count score.

## Production transplant after that proof

Once the fresh Lab story passes, inspect the latest production OTR head and
transplant one proven boundary at a time:

1. exact v2 envelope loader and Story Lab→production adapter;
2. visible `act_count` 1–5 wiring and centralized staged authoring path;
3. removal or isolation of legacy word-count/tier/auto authority on that path;
4. spoken-only cleaner, cast sweep, announcer introduction/coda, and music
   topology;
5. phase receipt appends, guarded save/reload, and terminal seal.

Keep current-l4 historical ledgers read-only. Do not use a lossy compatibility
shim and do not mutate the user’s unrelated production files. Unit and
fixture-level gates come first; GPU renders and the parked seven-leg campaign
resume only after the transplanted story path is green.

## Next-window kickoff

“Read this file plus `docs/LEDGER_BIBLE.md`. Confirm Story Lab `main` equals
`origin/main` and leave production OTR untouched. Implement only the
provider-neutral staged authoring executor/prompt layer over
`story_authoring.py`, with deterministic fake-model tests. The executor must
honor hard `act_count=1..5`, keep retries on the owning job, continually demand
actual dialogue, sanitize before admission, sweep unused cast, and compile the
exact music→announcer→dialogue→announcer→music sequence. Generate one complete
new v2 ledger fixture and run the full Story Lab gates. Do not add a word-count
gate, run a GPU render, or transplant into production in that first slice.”
