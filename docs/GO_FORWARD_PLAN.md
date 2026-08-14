# GO FORWARD PLAN — OTR Act-Based Story Lab

Updated: 2026-08-14 (second pass). This is the current handoff. The Story Lab
ledger is enshrined, and the provider-neutral staged authoring executor now
exists and is proven with a deterministic fake model. Production OTR has not
been changed.

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

The only visible story-length control is strict integer `act_count=1..8`.
There is no `auto`, global target-word variable, word-count admission gate, or
hardware-derived act count. Words and rendered minutes are observations.

`act_count` creates actual scheduled model work rather than merely appearing in
one large prompt:

```text
source packet
  -> story seed
  -> one X-act arc
  -> for each ordered act: spine -> beats -> dialogue -> cleanup
  -> cast sweep
  -> announcer opening
  -> factual announcer coda
  -> compiler-owned music bookends
  -> trusted admission and story seal
```

The stable schedule is `4 * act_count + 7` jobs. The base model schedule is
`4 * act_count + 4` calls before retries: 8 calls for one act through 36 calls
for eight acts. A retry is another attempt on the same job and never creates an
extra act.

Beat count, exchange count, and approximate duration may be soft per-bank or
per-model guidance. They are not universal ledger laws. The hard requirement
is that every accepted beat is enacted by actual character dialogue and every
act contains coherent entry, development, and exit state.

A 3060, 5090, or cloud route may change provider, model size, batching,
latency, context packing, and retry cost. It must not change the ledger shape,
act count, or spoken-only rule.

## Central compiler, creative banks

All six runnable banks retain control over source selection, tone, factual
material, and creative prompt content; `custom_source_bank` stays visible
but not runnable until an operator supplies their own lane:

- `scifi_news`
- `scifi_news_pro`
- `media_archive`
- `public_domain`
- `shakespeare`
- `original`
- `custom_source_bank` (visible, not runnable)

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
- Full suite: 358 passed (enshrinement + staged executor + per-bank act
  proofs + runaway guards + 1..8 ceiling migration).
- Generated artifact `--check`: passed; staged fixture and per-bank act proof
  `--check`: passed.
- `validate_lab.py`: 4 banks, 12 packs, 55 specs, 5 visual styles, 3
  public-domain manifests, no mirror drift.
- `smoke_nodes.py`: passed.
- `verify_tree.py`: 70 Python files, 45 JSON files, 0 errors.
- `git diff --check`: passed.
- No Bug Bible runner exists in this repository.

## Source-bank roster receipt (2026-08-14)

The roster now matches production. `science_news` was renamed to `scifi_news`
and `public_domain_story` to `public_domain`; `scifi_news_pro`, `shakespeare`,
and `original` were added.

- `validate_lab.py`: 7 banks, 7 packs, 30 specs, 5 visual styles, 3
  public-domain manifests, no mirror drift.
- Full suite: 450 passed.
- `smoke_nodes.py`: passed, asserting the full seven-id dropdown roster.
- `verify_source_banks.py`: 65 public-domain sources, 14 curated scenes, 14
  provenance digests verified, no word budgets.
- `verify_tree.py`: 85 Python files, 75 JSON files, 0 errors.
- Staged fixture and per-bank act proof `--check`: passed. Six sealed per-bank
  act proofs, one per runnable lane plus `custom_source_bank`.

Deliberately NOT renamed, and this is a decision rather than an oversight:

- `fixtures/story_recovery/v1/` in full, plus `contracts/ledger_bible_v1.json`.
  The Bible declares the legacy corpus non-migratable; a rename there is a
  contract violation, not a cleanup.
- `fixtures/story_recovery/science_news_good_20260716.json` and its challenger
  `scifi_news_bad_20260813.json`. These are historical captures of what
  production actually emitted in July, used as the ledger Bible's calibration
  control. Renaming them would falsify the evidence.
- `fixtures/story_recovery/v2/source_packets/science_news_folder_red_stamps_20260716.json`
  and `fixtures/story_recovery/v2/normative_ledger_envelope.json`. The envelope
  has no generator and binds that packet's digest, so the rename was made
  additively: a `scifi_news` twin of the packet was added alongside it and only
  the staged-authoring fixture was repointed and regenerated.

Production OTR remains unchanged at `707b39e9` on `v2.0-alpha`, equal to its
remote at the last read-only check. Its existing untracked operator files were
not touched. The production mirror in this lab is historical characterization,
not authority for the current production head.

## Staged authoring executor — built and proven with a fake model

The provider-neutral executor and prompt layer now exist:

- `src/upstream_story_lab/authoring_executor.py` walks the locked
  `4 * act_count + 7` schedule, assembles per-job context (locked cast, source
  facts, full arc, act spine/states, prior exit state, exact beat IDs and
  intents), renders deterministic prompts, and repeats the spoken-only law in
  every dialogue job.
- Draft acceptance runs the enshrined sanitizer and the spoken-text policy per
  act; safe standalone cues are dropped with a journal note, and every other
  defect retries only its owning job with explicit feedback. Exhausted retries
  fail loud. A retry never creates an act.
- Because the graph law demands every captured fact be cited by a spoken line,
  `assign_story_facts` deterministically gives the closing fact to the coda and
  cycles the rest across acts, so a missing citation always has exactly one
  retryable dialogue job.
- The compiler owns the cast sweep, announcer-opening literal-mention check,
  coda claim-verbatim check, music bookends, and final compilation into a v2
  envelope admitted through the code-owned verifier registry, sealed, saved,
  reloaded, and byte-compared.
- `src/upstream_story_lab/scripted_provider.py` is the injected deterministic
  fake model. `scripts/generate_staged_authoring_fixture.py --write/--check`
  produces the sealed proof fixture
  `fixtures/story_recovery/v2/staged_authoring_three_act.json`
  (`scifi_news`, `act_count=3`, one script-requested interstitial, one
  unused locked character swept).
- Soft shaping is now declared per bank in `fixtures/banks.json` as
  `staged_authoring_guidance` (beats_per_act 5–7, exchanges_per_beat 2–4,
  `authority: "guidance"`). It steers prompts only; there is still no
  count-based acceptance law and this field must never become one.
  `ULTRASHORT_GUIDANCE` (2 beats/act, 2 exchanges/beat) exists for rapid-fire
  testing.
- The documented anti-runaway doctrine is baked in (operator directive
  2026-08-14, mirroring production's "cap is a runaway guard, not a content
  target" rules): every model payload surface has a generous finite cap;
  every model request carries a `DecodeGuard` (per-job `max_new_tokens`
  budget, repetition penalty 1.03 recommended, 1.2 ceiling); and two
  deterministic decode-liveness signals reject a looping decoder —
  `find_decode_runaway` (consecutive phrase repetition, threshold scaled so
  dramatic rhetoric passes) and a repeated-identical-line check across a
  dialogue payload. All of it retries only the owning job and none of it is
  a word-count gate.
- The act ceiling is now `act_count=1..8` (operator decision 2026-08-14,
  pre-transplant contract widening while v2 has no external consumer): 8
  acts schedule 31 jobs / 28 base model calls.

## Production fidelity-lane intelligence (read-only diff, 2026-08-14)

A read-only comparison of live production OTR against this lab found the lab's
packs matched production's frozen 2026-07-05 blueprints, not the live
2026-08-05 prompts. The best of production's fidelity prose is now folded into
the lab packs (microphone-not-a-rewrite framing, faithfulness-outranks-craft,
source-spine restatement, faithful-cut coverage rule, verse preservation and
stage-direction conversion for plays, essential-speakers cast rule,
carry-the-source's-own-violence fidelity line, bridge-only codas with no URL
read aloud, archive source-truth rule and beat vocabulary). Facts that matter
for the later transplant:

- Production's fidelity lanes live in `nodes/story_packs/` (`shakespeare/`,
  `public_domain/`, `media_archive/`) plus `_otr_shakespeare_sources.py`,
  `_otr_public_domain_sources.py`, `_otr_media_archive_interpreter.py`,
  `_otr_source_document.py`, `_otr_source_grounding.py`,
  `_otr_source_world.py`; design doc
  `docs/2026-08-03-adaptation-fidelity-PLAN.md`. Production renamed the bank
  `public_domain_story` -> `public_domain` and the pipeline to
  `legacy_many_pass_adapt`; production's seam vocabulary differs from the
  lab's, so folding is re-authoring, never file copy.
- Production's per-beat verbatim source grounding
  (`select_grounding`/`render_source_block`) is finished and tested but NOT
  wired on `v2.0-alpha` — the lab can adopt it cleanly and should treat the
  wiring as lab-first work.
- Do NOT import from production: the still-required
  `recommended_word_budget` manifest keys and allocation machinery, the
  retired-but-present `_otr_content_safety.py` vocabularies, or the residual
  "no murder, weapons / no violence" clauses still inside
  `media_restoration_adventure`'s live seams — production itself recorded that
  its safety clause discouraged "Is this a dagger which I see before me" while
  adapting Macbeth; G9 spoken-safety was removed 2026-08-05.
- The lab keeps its own structural strengths production lacks: the five-pack
  public-domain form spread (stage play, chapter digest, comic panel,
  storybook), and machine-checkable `forbidden_plot_patterns` /
  `forbidden_leakage_terms` lists.
- A dedicated Folger Shakespeare lane (real scene manifests, speaker
  extraction from Folger layout, act/scene metadata, gender roster) exists
  only in production; adopting it in the lab is future work under the
  stage-play pack's rules.

## What is next — one real story on the RTX 4060

The repo-local 4060 safety instructions are restored verbatim at
`.claude/skills/rtx-4060-lab/` (from `vram-recipe-lab`). Note the scope gap
before running: that skill currently enrolls only three fixed video plans and
forbids arbitrary free-text prompting, so executing staged story-model jobs on
the 4060 requires the operator to explicitly enroll a story-authoring plan (or
approve an equivalent scoped route) first — do not improvise around the skill.
Then implement one real `StagedModelProvider` for the chosen route, author one
fresh `scifi_news` `act_count=3` story, and admit it through the same
executor. The proof is the sealed ledger, not a word-count score. Never load
the story LLM on the 5080.

## Production transplant after that proof

Once the fresh Lab story passes, inspect the latest production OTR head and
transplant one proven boundary at a time:

1. exact v2 envelope loader and Story Lab→production adapter;
2. visible `act_count` 1–8 wiring and centralized staged authoring path;
3. removal or isolation of legacy word-count/tier/auto authority on that path;
4. spoken-only cleaner, cast sweep, announcer introduction/coda, and music
   topology;
5. phase receipt appends, guarded save/reload, and terminal seal.

Keep current-l4 historical ledgers read-only. Do not use a lossy compatibility
shim and do not mutate the user’s unrelated production files. Unit and
fixture-level gates come first; GPU renders and the parked seven-leg campaign
resume only after the transplanted story path is green.

## Next-window kickoff

“Read this file plus `docs/LEDGER_BIBLE.md` and
`.claude/skills/rtx-4060-lab/SKILL.md`. Confirm Story Lab `main` equals
`origin/main` and leave production OTR untouched. The staged executor and its
fake-model proof already exist; do not rebuild them. With the operator, enroll
an explicit 4060 story-authoring plan under the skill's rules (no improvised
free-text route), implement one real `StagedModelProvider` for that route, and
author one fresh `scifi_news` `act_count=3` story through
`author_story_ledger`, saving the sealed envelope. Do not add a word-count
gate, load an LLM on the 5080, or transplant into production until that real
story passes.”
