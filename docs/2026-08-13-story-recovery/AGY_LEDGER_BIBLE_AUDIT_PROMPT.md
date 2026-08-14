# Universal audit prompt — ledger and downstream consumers

Audit the ledger in this repository as a production data contract, then audit
every downstream consumer of that ledger. Derive the proposed **Ledger Bible**
from executable code and tests—not from assumptions, handoff prose, or a desired
future story architecture.

Production repository:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OldTimeRadio`

Story Lab repository:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab`

Use the real Windows files. Begin by reading the production repository's
`AGENTS.md`, `CLAUDE.md`, and current `docs\GO_FORWARD_PLAN.md`. State the exact
model used, credit/spend rung, and review-routing directive and date actually
read. The 2026-08-11 directive suspended the full-kibitz gate.

This is an independent, read-only audit. Another window is performing the same
audit and the operator will synthesize the results. Do not inspect that window's
in-progress conclusions. Do not change production code, tests, workflow JSON,
fixtures, or plans. Do not run a render or GPU workload.

Your only permitted write is:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab\docs\2026-08-13-story-recovery\AGY_LEDGER_BIBLE_AUDIT.md`

## Central question

What is the ledger's complete, actual contract today, what does every downstream
consumer require from it, and where must the ledger be validated and frozen so
all downstream consumers can treat it as immutable input?

## Required audit

1. Trace the ledger lifecycle from creation through every validator, serializer,
   persistence/reload path, adapter, mutator, and downstream consumer.
2. Find every code path that reads any ledger field, including loose dictionary
   access, aliases, legacy fields, metadata blobs, fallbacks, and optional paths.
   Search the complete repository, workflow wiring, scripts, and tests—not only
   modules importing a ledger helper. Include every conditional engine and every
   audio, music, timing, image, portrait, video, clip, scope, composite, upscaler,
   caption, credits, mux, publish, resume, cache, audit, and recovery path. If a
   path does not touch the ledger, record it as checked-and-not-a-consumer so the
   coverage boundary is explicit.
3. Build a consumer matrix containing:
   - consumer/component and purpose;
   - exact file, function/class, and line evidence;
   - every field/path read;
   - expected type, cardinality, ordering, and ID relationships;
   - required/optional behavior and fallback/defaults;
   - whether it mutates the ledger or nested values;
   - tests that prove or fail to prove the behavior.
4. Locate the real freeze boundary, if one exists. Identify final validation,
   canonical serialization, hashes, persistence, shallow-copy hazards, and every
   mutation or persisted update after that boundary.
5. Reconcile all executable schema definitions, typed models, validators,
   producers, fixtures, migrations, and consumers. Identify contradictions,
   undocumented fields, producer-only fields, consumer-only assumptions, stale
   aliases, and lossy projections.
6. Inventory all executable contract coverage: schema, ordering, IDs,
   referential integrity, persistence/reload, immutability, hashes, compatibility,
   and consumer behavior. Identify tests that provide false confidence because
   they do not execute the real consumer path.
7. Propose the smallest artifact set needed to bless and document the ledger as
   the Ledger Bible before any source-bank or story-path changes proceed.

## Required report

Write `AGY_LEDGER_BIBLE_AUDIT.md` with:

1. Executive verdict: whether one coherent, frozen ledger contract exists today.
2. Ledger lifecycle diagram.
3. Exhaustive downstream-consumer matrix.
4. Chronological mutation ledger, separating construction from post-freeze writes.
5. Field-level contract table with type, owner, requirement status, consumers,
   invariants, defaults, and compatibility notes.
6. Schema/producer/consumer contradictions and lossy boundaries.
7. Test inventory and uncovered risks.
8. Recommended Ledger Bible artifact set.
9. First bounded, no-GPU implementation chunk to establish the contract and its
   executable tests.
10. Runtime unknowns that static inspection genuinely cannot answer.

Mark every material conclusion as:

- `CONFIRMED` — directly supported by code, tests, or a persisted artifact;
- `INFERENCE` — reasoned from cited evidence;
- `UNVERIFIED` — requires a focused runtime probe.

Use exact file/function/line citations for all material findings. Do not design
new stories, prompts, source banks, length tiers, audio, images, or video. Stop
after writing the audit report.
