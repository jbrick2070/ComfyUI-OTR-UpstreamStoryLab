# Episode length experiment

Updated: 2026-08-13

## Locked UI contract

Use one visible variable:

```text
episode_length_tier = ultra_short | medium | long | extra_long
```

The dropdown order is fixed:

1. `ultra_short` — fast testing and contract smokes
2. `medium`
3. `long`
4. `extra_long`

Do not add a visible target-word field beside it. Do not silently translate an
unknown tier through a default.

## What the tier means

The tier requests *story opportunity*, not a quota. A bank-owned, versioned
plan translates it into semantic units appropriate to that source:

- `scifi_news`: source-fact coverage, dramatic movements, scenes, character
  turns, and a fixed factual coda;
- `media_archive` / original material: movements, discoveries, reversals, and
  conversational-turn opportunities;
- public-domain prose: a contiguous performable source window;
- plays / Shakespeare: contiguous scene or passage coverage while preserving
  verbatim language and physical cast constraints.

Opening music, announcer introduction, announcer factual close, and closing
music are fixed structural reservations. They do not consume the body-story
opportunity supplied by a larger tier.

## Direct answer: it is a process, not a length prompt

Do not send `medium` or `extra_long` to an LLM and hope it interprets the label
consistently. The tier is resolved before generation:

```text
operator tier
  -> bank-owned length plan
  -> compiler-owned story movements and locked row opportunities
  -> bounded writing chunks
  -> intact ledger validation
  -> one validated ledger
  -> optional downstream OTR duration observation for later calibration
```

For the first experiment, a *movement* is the useful scaling unit: a bounded
piece of story with a clear entry state, dramatic job, and exit state. The lab
may start with a simple monotonic hypothesis such as one movement for
`ultra_short`, then successively more movements for `medium`, `long`, and
`extra_long`. The exact counts are experimental and bank-owned; they are not a
universal contract.

The compiler expands each movement into locked rows or turn opportunities.
Each call receives only the current bounded chunk plus the source facts, cast,
prior state, and exact speaker-owned row IDs it must fill. A representative
instruction is:

```text
Fulfill movement M02: the characters test the discovery and must leave this
chunk facing a concrete choice. Author spoken text only for locked rows l006
through l010. Preserve each row's speaker and fact references. Return no scene
directions and do not add, remove, or reorder rows.
```

That request asks for a dramatic job, not a quantity. Code controls how many
jobs exist. The Story Lab stops after the ledger is valid. When OTR later
speaks that ledger, measured audio can tell us how long the result became.

## What the model receives

The model should receive the compiled semantic plan for its current bounded
chunk. It should not receive instructions to count words, lines, or seconds.

A longer story grows through more bounded rows or chunks. It must not grow by
raising a single-string ceiling. Chunk boundaries and IDs are compiler-owned;
each writing call can author only the rows assigned to it and cannot change
speaker identity, fact authority, or bookend order.

Different LLMs—and later revisions of the same LLM—will realize the same plan
differently. The experiment must therefore compare receipts from actual model
runs instead of assuming one prompt-to-length formula is universal. A model
may influence prose and pacing; it may not decide whether the ledger, source
capture, announcer bookends, or music bookends exist.

## Bank plan contract to prototype

Every runnable bank must declare all four mappings in JSON. Python validates
the plan before any model call. A plan should describe concepts such as:

```text
plan_version
bank_id
tier
body_movements
scene_opportunities
turn_opportunities
source_coverage_policy
chunking_policy
fixed_bookends
physical_capacity_required
```

Those fields are not all necessarily universal; the experiment should find
the smallest shared contract and keep bank-specific semantics in the bank
pack. No global fallback may invent a missing mapping.

## Receipt contract

Each run records:

- requested `episode_length_tier`;
- bank and mapping version;
- resolved semantic plan and chunk count;
- actual scenes, beats/turns, spoken rows, and words as ledger telemetry;
- downstream audio seconds only when a later OTR consumer supplies them;
- source coverage and `source_limited` where applicable;
- liveness rerolls and accepted-attempt provenance.

Actual seconds and words are measurements, not acceptance criteria. Audio
seconds may be `not_evaluated` in a pure Story Lab run. A short or long
realization can still be semantically valid; later receipts give the lab data
needed to tune the next mapping version.

## Experiment order

1. **No-model resolver test:** every bank resolves all four tiers, unknown or
   missing values fail loudly, plans are monotonic, and bookends remain fixed.
2. **Fixture replay:** prove the semantic receipt is independent of requested
   tier and word telemetry.
3. **`ultra_short` live ledger arm:** test topology, speaker ownership, coda
   grounding, chunk handoff, liveness, and receipt completeness cheaply. Stop
   after the validated ledger.
4. **`medium` calibration:** add body opportunity using ledger outcomes and,
   when available, downstream OTR audio observations; do not scale string
   ceilings.
5. **`long` then `extra_long`:** expand physical array/chunk capacity before
   running. The current production ceiling of 3 scenes / 12 beats / 24 lines is
   not sufficient evidence for either tier.
6. **Cross-bank calibration:** compare semantic completeness and source
   coverage, not raw word parity between fundamentally different media.

No minutes or topology counts are locked in this document. Repeated ledger
runs and optional downstream audio observations decide them. If later UI
labels display approximate minutes, those remain expectations and receipt
context, never generation or publish gates.

## Invariants across all four tiers

- Same explicit music/announcer/body/coda order.
- Same score-owned speaker and fact authority.
- Same two independent decode-liveness signals.
- Same bounded repair/candidate policy.
- No target-word rejection or padding.
- No invented material when a public-domain source is too short; return the
  closest performable contiguous window and stamp `source_limited`.
