# GO FORWARD PLAN — OTR Story Recovery Lab

Updated: 2026-08-13. This is the current Story Lab handoff. The superseded
2026-07-02 production-transplant plan remains available in git at `7df7c80`.

## WHAT IS ACTUALLY LEFT

The live-ledger audit is complete and the Story Lab's structural story-plane
boundary is now executable. Trusted semantic validators, production receipts,
and the final seal are intentionally not executable yet. Do not change
source-bank story paths, prompts, length
planning, production OTR, or the parked render campaign until the remaining
contract-transplant prerequisites below are complete.

The order is:

1. **DONE:** trace every live ledger producer, validator, serializer, mutator,
   reload path, and downstream consumer across workflow code, scripts, tests,
   offline tools, manifests, and filesystem joins.
2. **DONE:** publish the code-cited current-l4 consumer matrix and chronological
   mutation audit; retain the raw AGY report and grounded corrections.
3. **DONE:** bless the one-JSON target envelope and make the strict
   `story_ledger` + `story_seal` boundary executable. Non-null
   `production_state` and `final_seal` fail until their typed models land.
4. **DONE:** preserve and reconcile the Sonnet 5 red-team against live code;
   retain its raw report and incorporate only grounded deltas.
5. **DONE:** build and register the five trusted semantic outcome verifiers
   over the sealed control/challenger evidence, then add a complete normative
   v1 fixture and rejected mutation corpus. Receipt JSON alone is not trust.
6. Define strict production-state receipt schemas, emit static JSON Schema,
   and implement the explicit digest-preserving Story Lab→OTR adapter. No
   silent l4 migration.
7. Add save-guard and consumer-adapter tests proving every production phase
   preserves the story digest, then define terminal audit/final-seal ordering.
8. Then resume source-bank story-path work: four-tier bank-owned length-plan
   experiments, compiler-owned bookends, speaker authority, narrow
   spoken-correctness checks, and executable A/B adapters.
9. Transplant proven pieces into OTR in small green chunks, recreate the parked
   seven-leg runner against the changed code, and run those proofs last.

## LEDGER CONSTITUTION GATE — operator-locked 2026-08-13

Steps 5–7 are one hard gate delivered as small independently green commits.
Do not call Ledger Bible v1 enshrined, and do not resume story generation,
until all of these are executable:

1. **DONE:** one complete normative v1 ledger fixture;
2. **DONE:** five code-owned trusted semantic validators;
3. **DONE:** a rejected mutation fixture for every invariant;
4. generated static JSON Schema with executable human/machine parity checks;
5. one type, default law, lifecycle owner, mutation phase, durability rule,
   and failure policy for every ledger field;
6. typed append-only production receipts and a terminal final seal;
7. adapter, save-path, and consumer tests proving sealed story bytes and digest
   remain unchanged through every legal production phase; and
8. explicit registered migrations only—never silent repair or promotion of an
   old ledger into v1.

Until all eight pass: no source-bank prompt/path rewrite, length-tier
experiment, Lemmy work, production OTR transplant, GPU render, or parked gate
leg. The ledger is the ABI; downstream systems adapt to it.

The raw Antigravity, Codex, and Sonnet lanes are preserved separately under
`docs/2026-08-13-story-recovery/`. Their grounded convergence and corrections
live only in `LEDGER_BIBLE_SYNTHESIS.md`.

## Minimum ship contract

These five outcomes are hard. Everything else is theory until tested:

1. The ledger is intact and internally coherent.
2. The selected news and usable factual evidence are captured.
3. The announcer opens by introducing the story, setting, and characters.
4. The announcer ends by summarizing the real news from captured evidence.
5. Music is first and last.

LLMs are replaceable and variable. They may author prose inside locked rows;
they do not own these outcomes.

The Story Lab emits one validated ledger JSON. It does not synthesize speech,
render media, publish an episode, or require a GPU. Downstream OTR may later
return duration observations, but the lab stops at the ledger boundary.

## Length control — operator-locked

One visible variable: `episode_length_tier`.

```text
ultra_short
medium
long
extra_long
```

The order and labels above are fixed. Exact minutes, scenes, beats, lines, and
chunk sizes are deliberately not fixed yet. Each bank maps the same tier to
its own semantic opportunity. Actual audio duration and words are receipts;
neither is a publish gate, and models are never asked to count them.

Length is mainly a process, not a prompt: tier -> bank plan -> compiler-owned
movements/rows -> bounded writing chunks -> intact ledger. The model is asked
to fulfill a dramatic job for exact locked rows, not to “write a medium
story.” Optional downstream audio measurements calibrate later mapping
versions; they are not a Story Lab output.

## Staged evidence

- Human Ledger Bible:
  `docs/LEDGER_BIBLE.md`
- Machine Ledger Bible:
  `contracts/ledger_bible_v1.json`
- Current-l4 consumer matrix:
  `contracts/ledger_consumer_matrix_l4.json`
- Executable target contract:
  `src/upstream_story_lab/ledger_contract.py`
- Code-owned trusted semantic validators:
  `src/upstream_story_lab/ledger_verifiers.py`
- Complete normative v1 envelope and captured source packet:
  `fixtures/story_recovery/v1/`
- Rejected mutation corpus covering all 17 machine-Bible story invariants:
  `fixtures/story_recovery/v1/rejected_mutations_v1.json`
- Independent Codex audit:
  `docs/2026-08-13-story-recovery/CODEX_LEDGER_BIBLE_AUDIT.md`
- Review synthesis:
  `docs/2026-08-13-story-recovery/LEDGER_BIBLE_SYNTHESIS.md`

- Ledger Bible code-audit plan:
  `docs/2026-08-13-story-recovery/LEDGER_BIBLE_AUDIT_PLAN.md`
- Independent Antigravity audit prompt:
  `docs/2026-08-13-story-recovery/AGY_LEDGER_BIBLE_AUDIT_PROMPT.md`
- Independent Sonnet audit/red-team prompt:
  `docs/2026-08-13-story-recovery/SONNET_LEDGER_BIBLE_AUDIT_PROMPT.md`
- Preserved raw Sonnet audit:
  `docs/2026-08-13-story-recovery/SONNET_LEDGER_BIBLE_AUDIT.md`
- Problem statement:
  `docs/2026-08-13-story-recovery/PROBLEM_STATEMENT.md`
- Port/restore/compare/exclude decisions:
  `docs/2026-08-13-story-recovery/RECOVERY_MATRIX.md`
- Length experiment:
  `docs/2026-08-13-story-recovery/LENGTH_TIER_EXPERIMENT.md`
- Paste-ready academic deep-research brief:
  `docs/2026-08-13-story-recovery/DEEP_RESEARCH_BRIEF.md`
- Clean control:
  `fixtures/story_recovery/science_news_good_20260716.json`
- Render-pass/content-fail challenger:
  `fixtures/story_recovery/scifi_news_bad_20260813.json`
- Machine-readable hard contract:
  `fixtures/story_recovery/ledger_requirements_v1.json`
- Deterministic extractor:
  `scripts/extract_story_recovery_cases.py`
- Evidence-integrity tests:
  `tests/test_story_recovery_artifacts.py`

The clean control is the July 16 legacy `science_news` episode “Folder of Red
Stamps.” The challenger is the August 13 `scifi_news` / `wan_ti2v` episode “The
Light of Possibility.” All copied surfaces and final assets are SHA-256 pinned.
The challenger truthfully records `render_pass=true` and
`story_content_pass=false`.

## Current technical facts

- Repo: `ComfyUI-OTR-UpstreamStoryLab`, branch `main`.
- Baseline before this staging chunk: `7df7c80`, clean and equal to origin.
- Ledger Constitution Step 5 checkpoints: trusted validators/normative fixture
  `1b1baac`; 17-invariant mutation corpus `eb35af8`; both pushed to
  `origin/main` with HEAD verified equal to origin after each chunk.
- Current staging gates: 144 tests passed; `validate_lab.py` reports 4 banks,
  12 packs, 55 validated specs, 5 visual styles, 3 public-domain manifests,
  and no mirror drift; node smoke passed; tree verification reports 59 Python
  files, 38 JSON files, and 0 errors.
- `legacy_many_pass` is descriptive-only and the lab runner refuses it.
- Only `simple_4_prompt_experimental` currently executes, through an injected
  string-callable; it is not a live production writer.
- `production_mirror` is pinned to OTR `d48a9d76`. It is historical and mostly
  drifted from current OTR; never treat `mirror_drift=none` as live parity.
- The current OTR liveness guard did not cause the bad episode. Its accepted P3
  and P5 never fired the guard.
- Do not copy current OTR wholesale: it is the challenger and contains the
  speaker/topology regression this lab exists to fix.
- Do not restore old OTR wholesale: its useful announcer/coda boundaries are
  mixed with retired word and subjective-quality machinery.

## Step 5 implementation receipt

- Changed code/contracts: `src/upstream_story_lab/ledger_verifiers.py`,
  `src/upstream_story_lab/ledger_contract.py`,
  `src/upstream_story_lab/__init__.py`, `contracts/ledger_bible_v1.json`, and
  `docs/LEDGER_BIBLE.md`.
- Added evidence/tests: `fixtures/story_recovery/v1/`,
  `tests/test_ledger_semantic_verifiers.py`, and
  `tests/test_ledger_mutation_corpus.py`.
- The official registry contains exactly five immutable validator identities.
  News admission re-hashes exact caller-supplied captured-packet bytes and
  compares the complete strict source/fact projection. Opening and coda prose
  use a versioned normalized-literal policy; no LLM or network call is trusted.
- The July control calibrates the positive opening/coda content and remains
  historical evidence with music explicitly not evaluated. The August
  challenger calibrates rejection findings and remains content-fail evidence.
  Neither is silently promoted into v1.
- No Bug Bible runner exists in this Story Lab repo. Focused tests, the full
  suite, all three repo validation scripts, `git diff --check`, push, and
  HEAD/origin equality checks were green for both chunks.
- Active build threads or blockers: none. Production OTR and the GPU were not
  touched.

## Production and render parking lot

Production OTR remains separate and unchanged by this Story Lab staging chunk.
The live render gate is 14/21 after the fresh-seed `wan_ti2v` pass. Seven legs
remain parked:

- `wan_i2v`
- `humo`
- `humo_14B_169`
- `humo_1.7B`
- `humo_1.7B_169`
- `minimax_h3_video`
- `minimax_h3_audio_in`

Purpose: those legs must prove the post-story/Lemmy code that will ship, not
stale pre-fix code. Recreate their runner and re-read every profile's own
`launch.env` after the writer/Lemmy changes; never reuse the old temporary
seven-leg runner blindly. Keep the one-coder-window law while story code moves.

## Review routing

The active operator directive is dated 2026-08-11: full r1-r4 kibitz is
suspended. Use a Codex consult only for a genuine quandary or third attempt and
Sonnet 5 for post-coding QA. Do not resurrect stale “mandatory full kibitz”
language from the July artifacts.

## Next-window kickoff

“State your MODEL & CREDIT BUDGET rung first. Read the 2026-08-11 review-routing
directive here; full r1–r4 kibitz remains suspended. Open
`docs/LEDGER_BIBLE.md`, `contracts/ledger_bible_v1.json`,
`contracts/ledger_consumer_matrix_l4.json`, and
`docs/2026-08-13-story-recovery/LEDGER_BIBLE_SYNTHESIS.md`. Step 5 is green at
`eb35af8`. Execute only the first independently green Step 6 slices: define one
type/default/lifecycle owner/mutation phase/durability/failure policy for every
production-state field, implement strict append-only attempt/receipt schemas
for every registered production phase, then generate static JSON Schema with
executable human/machine parity. Keep `final_seal` non-executable until terminal
audit ordering is defined. Do not implement the Story Lab→OTR adapter, touch a
production save path, rewrite source-bank stories, change length tiers, resume
Lemmy, use the GPU, or run any parked render leg in this window. Run focused
tests, the full Story Lab suite, `validate_lab.py`, `smoke_nodes.py`, and
`verify_tree.py`; commit and push each green chunk to Story Lab `main`, then
verify HEAD equals origin.”
