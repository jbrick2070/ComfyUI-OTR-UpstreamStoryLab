# Story Lab staged authoring: implemented system under QA

Repo: `ComfyUI-OTR-UpstreamStoryLab`, branch `main` at `bbeeb55`.
Suite: 409 passing. This is **implemented, wired code**, not a proposal. Judge
the code against the laws below and report defects, not style preferences.

## What the system does

One bank packet becomes one sealed Story Ledger v2 envelope. The only visible
length control is a strict integer `act_count` from 1 through 8. The schedule
is fixed at `4 * act_count + 7` jobs, of which `4 * act_count + 4` are model
calls:

```
story_seed -> story_arc
  then per act, ONE ACT AT A TIME:
    act_spine -> act_beats -> act_dialogue -> act_cleanup
  cast_sweep (compiler)
  announcer_open -> announcer_news_coda
  music_bookends (compiler)
  final_admission (code)
```

Act N's spine depends on act N-1's cleanup, so acts are authored sequentially,
each grounded in the arc and the previous act's accepted exit state.

## The laws

1. **The sealed ledger holds only announcer speech, character dialogue, and
   music cues.** Never a stage direction, action row, narration, or delivery
   note.
2. **Before the seal a draft may be rewritten freely; after the seal nothing
   may be.** The rewriting is done by **model passes, not by code**. Code may
   detect a defect and explain it; it must never rewrite an author's prose.
   Every act has an `act_cleanup` model job for exactly that.
3. **No word-count authority anywhere** - no target, budget, cap, or gate. The
   runaway caps that exist are code-internal and must never appear as prompt
   instructions.
4. **No content guardrails anywhere.** No profanity, violence, weapon, gore, or
   family-friendly filtering. A source's own violence is carried as the author
   wrote it. (Production once discouraged "guns/knives" while adapting Macbeth;
   that is the defect this law exists to prevent.)
5. **Prompts must work unchanged on small local models (7B class) and frontier
   models alike, local or remote.** No tiering, no per-model variants, no
   conditional branches the model must choose between.
6. **No bare `assert` in shipped code** - `python -O` strips it, so a gate
   built on `assert` silently passes while checking nothing.

## Key files

- `src/upstream_story_lab/authoring_executor.py` - the executor: schedule walk,
  per-job context assembly, prompt rendering, acceptance for every job kind,
  retry routing, final compilation, seal, save/reload.
- `src/upstream_story_lab/story_authoring.py` - the canonical schedule, the job
  instruction tuples, and the draft sanitizer.
- `src/upstream_story_lab/source_window.py` - act-proportional frozen source
  windows, gapless tiling, hash-derived fence tokens, body-free receipts, and a
  `MAX_BLOCK_CHARS` excerpt bound so a 7B model can hold the block.
- `src/upstream_story_lab/spoken_text_policy.py` - `otr.spoken-text-only.v1`,
  plus the v2 source-carried exemption.
- `src/upstream_story_lab/ledger_verifiers.py` - the five trusted outcome
  verifiers and the v4 adaptation form of ledger integrity.
- `src/upstream_story_lab/ledger_contract.py` - the sealed contract.
- `fixtures/story_packs/**/*.json` - twelve packs, each carrying a
  `job_prompts` block keyed by the eight prompt-bearing jobs.

## The v2 source-carried exemption (highest-risk area)

Measured: the live policy rejects genuine spoken Shakespeare. `Sir, there she
stands.` and `with washed eyes Cordelia leaves you.` are rejected by the same
`third_person_stage_business` detector that correctly rejects invented
narration like `Ada turns to Leo...`. No lexical rule separates them.

So on adaptation lanes only, a line is exempt from the three **heuristic**
findings (`third_person_stage_business`, `cross_speaker_attribution`,
`quoted_novel_dialogue`) when its words are literally carried from that act's
frozen source window. Carriage compares whitespace-flattened and case-folded,
because verse wraps across lines.

Never exempt on any lane: `production_cue`, `delimited_stage_direction`, and a
row that is **entirely** a stage action. That last carve-out exists because
sources print directions in brackets, so `He exits.` is literally quotable from
King Lear with the brackets stripped and would otherwise ride the exemption
into the sealed ledger.

**Question for review: can the exemption be abused to smuggle narration into a
sealed ledger?** For example by quoting a stray fragment, by a short carried
phrase excusing a long invented line, or by carriage from the wrong region.

## Known open items (do not report these as new)

- `presented_gender` / `age_band` are not yet sealed on `CastMember`. Decided
  and documented; it is a sealed-schema migration queued as its own slice.
- A leaked speaker prefix in a line (`MACBETH So foul and fair...`) is not
  rejected by any acceptance function on either lane; it is currently defended
  only by a cleanup instruction.
- A Shakespeare fifth bank is not yet registered.
- The rendered prompt is barely covered by tests.

## Review EVERY source-bank path end to end

This is a required part of the review, not an optional extra. Walk each bank
from its declaration through to a sealed ledger and report what would actually
break on that lane:

1. **`science_news`** - real news facts, coda is a factual news read. One pack.
2. **`media_archive`** - archive objects and preservation labor. Five packs:
   `media_restoration_adventure`, `gentle_thriller`, `happy_archive_mystery`,
   `cinematic_humorous`, `broadcast_history_comedy`.
3. **`public_domain_story`** - adaptation lane, carries source text. Five packs:
   `faithful_radio_adaptation`, `stage_play_radio_adaptation`,
   `chapter_digest_drama`, `comic_panel_radio_adaptation`,
   `storybook_puppet_show`.
4. **`custom_source_bank`** - operator-supplied material, currently
   `runnable: false`, one experimental pack.
5. **`shakespeare`** - not yet registered as a bank, but its data is already
   vendored under `fixtures/source_banks/shakespeare/` (14 Folger scenes with
   provenance sidecars and a gender roster). Report what registering it would
   break.

For each bank and pack, check at least:

- Does `fixtures/banks.json` agree with the packs? `required_seams` still lists
  retired many-pass seams while the executor now reads `job_prompts` - does any
  gate reject a pack that has migrated, or accept one that has not?
- Does every pack declare all eight `job_prompts`, and does each prompt match
  what that job's acceptance code actually enforces for that lane?
- Do the bank's `forbidden_leakage_terms` and `forbidden_plot_patterns` still
  hold, and does anything in the new `job_prompts` violate another bank's
  leakage list?
- Does the lane's coda mode match what `verify_announcer_news_coda` requires -
  a literal complete fact claim - or does the pack promise a different kind of
  close (an archive note, a source attribution) that the validator will reject?
- On adaptation lanes, does the source actually reach the jobs that need it?
  Note that `act_spine` and `act_beats` return from `_job_context` before the
  source block is attached, so those acts are planned without the source.
- `profiles.py` hard-requires a non-empty `prompt_stages.line_grounding` and
  raises otherwise. Is that now stale, and does it block the migration?

## What to look for

Real defects, demonstrated or precisely justified:

- Any way non-dialogue reaches the sealed ledger.
- Any way the cleanup pass corrupts an act - dropping a beat's last line,
  orphaning an assigned fact, reassigning a speaker or beat, losing a music
  cue, or leaving act state half-updated on rejection.
- Any acceptance rule a prompt contradicts, or any rejection a prompt never
  warns about, that would burn retries or lose a whole run.
- Off-by-one or coverage bugs in act window tiling, the collapse floor, or the
  excerpt bound.
- Any surviving word-count authority, content guardrail, prose-rewriting code,
  prompt tiering, or bare assert.
- Anything that would behave differently, or fail, on a small local model.
