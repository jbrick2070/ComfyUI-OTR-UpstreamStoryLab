# OTR Story Recovery Lab — grounded problem statement

Updated: 2026-08-13

## Operating rung and review route

- Model / credit rung: local evidence, local tests, and Codex code audit;
  external model spend for this staging chunk is `$0`.
- Review routing actually read: operator directive dated 2026-08-11. The
  standing full-kibitz gate is suspended. Use a Codex consult only for a
  genuine quandary or third swing, and Sonnet 5 for post-coding QA.
- This repo is the experimentation base. The live OTR writer is evidence and a
  donor of selected mechanisms, not the implementation to copy wholesale.

## The outcome we need

### Minimum ship contract — hard

Only these outcomes are non-negotiable at the start of the new lab:

1. **The ledger is intact and frozen.** It validates, every ID/reference and
   speaker row is coherent, the accepted source/story surfaces and receipts
   survive, and no model response or downstream consumer can silently drop,
   reassign, or mutate required rows.
2. **The news is captured.** The selected source packet and its usable factual
   claims are preserved as typed evidence before fiction is written.
3. **The announcer opens the program.** The opening introduces the story,
   setting, and characters.
4. **The announcer closes the program.** The final spoken row summarizes the
   real news from the captured evidence and clearly sits after the fictional
   drama.
5. **Music bookends the program.** Opening music is first and closing music is
   last.

Everything else—including the best model, number of passes, chunk size,
duration mapping, story-planning method, and prompt wording—is a lab
hypothesis. Models differ and change; none of those choices may become an
implicit authority over the five outcomes above.

The ledger sequence contains only announcer speech, character dialogue, and
music declarations. Action, stage direction, third-person narration, and
delivery notes are not spoken rows. Planning and continuity metadata may
describe story state, but it is never a line a speech consumer can read.

Every news-derived radio story must have this typed, compiler-owned order:

```text
music_open
  -> announcer_open
  -> character story beats, with music_inter only where the script requests it
  -> announcer_factual_coda
  -> music_close
```

The announcer opening establishes the place, time, people, and real-news
premise without spoiling the fictional outcome. Character rows contain only
words the assigned character can speak; actions and scene description stay in
non-spoken metadata. The closing announcer clearly pivots from the fictional
story to a source-backed summary of the real news.

The score owns line order, character identity, semantic role, source-fact
references, and music placement. A later writing pass may author spoken text
for those locked rows but may not reassign speakers or topology.

The generator is therefore replaceable. A model upgrade, downgrade, local
checkpoint change, or provider change may alter prose, but it cannot alter the
minimum ledger/news/announcer/music contract.

Render success and story-content success are independent receipts. A video can
be mechanically valid while its story contract is invalid.

## Artifact boundary — the lab emits one ledger

The Story Lab's product is one validated ledger-envelope JSON and nothing
downstream of it. Its sealed story plane contains the captured source/news
evidence, cast, story structure, speaker-owned spoken rows, opening/closing
music declarations, announcer bookends, and provenance/acceptance receipts.

The lab does not synthesize speech, render images or video, assemble an
episode, publish to OBS, or require a GPU. Those are OTR consumers of the
ledger. Later downstream runs may report actual audio duration back to the lab
to improve tier mappings, but absence of downstream media never prevents the
lab from emitting or evaluating its ledger.

The accepted `story_ledger` is canonicalized, hashed, and deeply immutable.
Downstream OTR records derived artifacts and receipts only under its separate
phase-owned `production_state`. After publication and audit, a final seal makes
the completed envelope immutable. Current l4 consumers mutate one mixed dict;
the audit established that this is migration debt, not evidence that authored
story truth should remain mutable.

## First recovery task — audit the Ledger Bible against consumers

Before prompts, models, chunking, or length tiers, enumerate every real
producer, mutator, and downstream reader in live OTR. Reconcile the exact
fields, types, IDs, order assumptions, defaults, and writes into one versioned
machine schema and consumer matrix. Then prove every production consumer keeps
the sealed story digest unchanged and writes only its declared production
phase. Prove complete immutability again at the terminal seal.

The executable method and artifact set are defined in
`LEDGER_BIBLE_AUDIT_PLAN.md`. This consumer-backed contract—not a writer-owned
guess—becomes the starting point for the fresh lab.

## Live failure that admitted this work

The 2026-08-13 `wan_ti2v` episode
`signal_lost_the_light_of_possibility_20260813_172801` rendered and published
successfully:

- render engine `wan_ti2v`, exit `0`, 179.8 minutes;
- 13 clips covered the audio;
- published MP4 SHA-256
  `ef35bada7cca3e35b0c338d6825c7b0ab5ff502ef50d53a2005a321d1b9d1d4c`;
- exact render receipt and compiled story artifacts are frozen in
  `fixtures/story_recovery/scifi_news_bad_20260813.json`.

Its content was not fit to publish:

- the first spoken row belongs to Dr. Ada, not the announcer;
- the only announcer row is interior (`l003`), factless, and frames a fictional
  personal struggle rather than introducing the news;
- the last row belongs to the Ethics Board and carries no source fact;
- opening and closing music are anchored to character rows;
- character rows contain third-person action and stage prose;
- `l005`, `l006`, and `l011` visibly cross speaker ownership;
- the ledger's own word-budget telemetry records target `45` and actual total
  voiced words `357`; its policy is explicitly
  `requested_context_actual_count_only`, so the number is evidence, not an
  acceptance authority.

The credits correctly named `scifi_news`; this was not a mislabeled source
bank. The ledger is genuinely a `scifi_news` artifact.

## Clean control

The 2026-07-16 legacy `science_news` episode
`signal_lost_folder_of_red_stamps_20260716_152501` is the control:

- its first announcer line explicitly supplies a time and place;
- its three middle rows are direct character dialogue;
- its final announcer line contains the exact source-backed wildfire close;
- its ledger and final video both survive and are hash-pinned in
  `fixtures/story_recovery/science_news_good_20260716.json`;
- measured audio duration is 54.7177 seconds and word count is retained only as
  105-word telemetry.

The legacy ledger has no structured music-cue rows. Music topology is therefore
`not_evaluated` for this control, never silently inferred as a pass.

## Root cause established so far

The August liveness guard did not fire during the accepted story and did not
rewrite it. The accepted P3 and P5 calls were ordinary bounded outputs. Do not
revert the guard.

The regression is an authority and topology loss:

1. Commit `e679b754` introduced a compact P5 context that omitted the
   score-owned speaker name and cast mapping while its prompt still told the
   model to obey “the graph's speaker.”
2. The current P3 compiler checks that every cast member appears somewhere,
   but has no required `announcer_open` or `announcer_factual_coda` roles.
3. Commit `2129ce84` narrowed current spoken-text acceptance; commit
   `314dd481` then retired the shared narration/stage-direction detector stack
   and its regression corpus.
4. The current `scifi_news` custom route returns directly into the writer tail
   and bypasses the legacy dedicated announcer intro/coda composition path.
5. The old coda guarantee lived partly in prompt text and partly in dedicated
   composition. Once that path was retired, no typed invariant replaced it.

The separate length-design problem is not the cause of the missing announcer,
but it must be solved in this lab before the story architecture is transplanted.

The retired corpus also contains the known unparenthesized director-note leak
(`proof7`, “Lab Race Against Time,” `b003`), parked in the prior plan at
`7df7c80`. It is now covered by the explicit no-delivery-note/no-action spoken
contract rather than left as an orphaned historical TODO.

## Length authority — locked operator intent

The one user-facing control is `episode_length_tier`, with exactly these values
and this order:

1. `ultra_short` — testing
2. `medium`
3. `long`
4. `extra_long`

No minute, word, line, scene, or beat counts are locked yet. The lab must
calibrate each tier from measured audio and story results. Each media bank may
translate the same tier into different semantic opportunities. Words remain
telemetry and may be an internal drafting hint, but they never decide whether
a story passes.

## Scope of the fresh lab

The lab should answer, with executable evidence:

1. Which typed row roles guarantee the announcer and music bookends?
2. Which compact score fields give a writer enough speaker authority without
   inviting it to echo or rewrite the full score?
3. Which narrow, high-precision checks reject spoken narration, stage business,
   and another character's speech without reviving subjective prose scoring?
4. How does each bank map the four length tiers to its own scenes, movements,
   source coverage, beats, and exchange opportunities?
5. How should bounded chunks be authored so longer stories grow by adding
   bounded rows rather than enlarging a string or asking a model to count?
6. Which receipts separately prove transport, source grounding, story content,
   and the complete ledger? Render delivery remains a downstream OTR receipt.

## Non-goals

- Do not restore the retired many-pass pipeline wholesale.
- Do not copy the current production writer wholesale.
- Do not reinstate subjective cliché, thesis, “one breath,” style, or global
  quality vetoes.
- Do not use word count as an acceptance gate.
- Do not ask a model to count words, lines, or seconds.
- Do not fabricate missing raw transports or legacy music evidence.
- Do not split or simplify the two-signal liveness guard when live generation
  is eventually connected.
- Do not modify production OTR or its canonical workflow during fixture/lab
  exploration.

## Admission gates before any production transplant

1. Checked-in fixtures verify against all pinned hashes without reading the
   external output tree.
2. A pure semantic receipt passes the legacy control and fails the challenger
   for the exact observed defects.
3. The receipt reports legacy music as `not_evaluated`.
4. Every runnable bank resolves all four length tiers before any model call;
   unknown/missing mappings fail loudly.
5. Tier plans are monotonic in bank-owned story opportunity, while announcer
   and music reservations remain fixed.
6. Actual words and seconds are reported but never create a length pass/fail.
7. The live lab adapter integrates both liveness signals and bounded rerolls;
   no dead guard code is staged ahead of a real model call seam.
8. A fresh lab-generated `scifi_news` ledger proves the content contract before
   transplant. A later canonical OTR episode proves downstream consumption
   before the seven parked render legs are recreated and run against shipping
   code.
