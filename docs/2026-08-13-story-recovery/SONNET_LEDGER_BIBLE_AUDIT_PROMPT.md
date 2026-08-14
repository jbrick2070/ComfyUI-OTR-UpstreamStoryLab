# Sonnet Ledger Bible audit prompt

You are the independent Sonnet reviewer for the OldTimeRadio Ledger Bible.
Work from the real Windows repositories below. Do not rely on summaries,
historical mirrors, or another reviewer's confidence labels when the live code
can answer the question.

Production OTR:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OldTimeRadio`

Story Lab:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab`

Before auditing, read completely:

1. Production `AGENTS.md` and `CLAUDE.md`.
2. Production `docs\GO_FORWARD_PLAN.md`, especially the review-routing block
   dated 2026-08-11. The full-kibitz gate is suspended.
3. Story Lab `docs\GO_FORWARD_PLAN.md`.
4. Story Lab
   `docs\2026-08-13-story-recovery\LEDGER_BIBLE_AUDIT_PLAN.md`.
5. Story Lab
   `docs\2026-08-13-story-recovery\AGY_LEDGER_BIBLE_AUDIT.md`.

At the top of your report, state the exact model, credit/spend rung, and the
review-routing directive and date you actually read.

## Scope and independence

This is a read-only code audit and red-team, not an implementation pass. Do
not edit production OTR, Story Lab code, workflow JSON, tests, prompts, source
banks, render runners, or existing reports. Do not run a GPU job. You may run
focused CPU-only tests or read-only probes when they resolve a factual claim.

Your only allowed write is this new, separate report:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab\docs\2026-08-13-story-recovery\SONNET_LEDGER_BIBLE_AUDIT.md`

Do not overwrite or append to the AGY report. Do not wait for a Codex report.
Reach your own verdict from live code, then compare your evidence with AGY.

## Central questions

1. What is the complete current episode-ledger contract actually implemented
   by production OTR?
2. Which authored fields are truly immutable after Phase 10, and where is that
   immutability enforced? Distinguish a validation/status stamp from a
   save-time mutation guard.
3. Which fields are legally added or changed during voice, music, timing,
   image, video, compositing, captions, credits, mux, publish, resume, cache,
   audit, and recovery?
4. Should the target contract be one immutable JSON object, an immutable
   authored-story projection plus mutable/append-only production state, or
   something else? Give the smallest design consistent with every confirmed
   consumer.
5. What must the Story Lab emit so production can consume it without losing
   facts, speaker authority, semantic row purpose, music topology, IDs, or
   provenance?

## Required exhaustive coverage

Trace the authoritative canonical workflow and every relevant branch:

- ledger constructors, typed artifacts, adapters, validators, cleanup,
  serializers, save/merge/reload, singleton discovery, rename/rebase, resume,
  crash recovery, cache, and audit paths;
- cast lock, character voice, announcer voice, theme/music generation, scene
  sequencing, audio enhance, episode assembly, and master-audio identity;
- ShotLock, image prompt/dispatch, portrait and still paths, video render
  planning/dispatch/acceptance, every conditional engine family, clip
  persistence, scopes, composite, post-upscale blend, caption burn, credits,
  final mux, OBS publish, and post-run audits;
- offline render scripts, graders, validators, fixtures, compatibility tools,
  and tests;
- major nearby branches checked and proven not to consume or mutate the episode
  ledger. Explicitly record `CHECKED_NOT_A_CONSUMER` rather than omitting them.

The standard macOS/FFmpeg upscaler is proven and closed. Do not reopen its
quality or implementation. Mention it only where a node directly reads or
writes ledger fields.

## Claims that require special adjudication

Verify these from executable code; do not accept either outcome in advance:

- Does `meta.cleanup_locked` have any production reader that blocks mutation?
- Does Phase 10 deep-copy, wrap, hash, or protect the whole authored structure?
- Does `_sha256_content_authorship` cover cast, scenes, shots, beats, speaker
  ownership, facts, and authored music, or only a narrower surface?
- Can CastLock rewrite `lines[].speaker_role` after Phase 10?
- Can EpisodeAssembler append music mirrors to and reorder `lines[]`?
- Are SciFi `fact_ids` preserved into the durable production ledger?
- Do SilentComposite, CaptionBurn, CreditsRoll, and individual video-engine
  adapters actually persist ledger writes, or are any such AGY claims false?
- Are clip/shot/image mutations durable ledger writes, transformed wire-only
  state, or result-manifest changes?
- Can publication succeed when the final ledger writeback fails?
- Do both ledger save paths use the same schema-version and merge policy?

## Required report structure

1. Executive verdict with confidence and the exact proposed freeze boundary.
2. Canonical workflow/lifecycle diagram.
3. Exhaustive consumer matrix with component, file/function/line evidence,
   fields read, fields written, lifecycle phase, requiredness/fallback,
   durability (`wire`, `disk`, `manifest`, or `none`), and test coverage.
4. Chronological mutation ledger from draft creation through terminal audit.
5. Field-ownership table separating:
   - immutable authored story truth;
   - derived production state and receipts;
   - renameable/path identity;
   - telemetry;
   - final delivery seal.
6. Referential-integrity, ordering, cardinality, and version/migration rules.
7. AGY claim review table with `AGREE`, `PARTIAL`, or `DISAGREE`, exact code
   evidence, and corrected language. Pay special attention to AGY's statement
   that the narrative plane is "strictly frozen at Phase 10."
8. Missing coverage and false-confidence tests.
9. Recommended machine-readable Ledger Bible artifact set.
10. First bounded CPU-only implementation chunk and precise acceptance tests.
11. Runtime unknowns that static inspection cannot honestly settle.

Use `CONFIRMED`, `INFERENCE`, `UNKNOWN`, and `CHECKED_NOT_A_CONSUMER`
consistently. Every `CONFIRMED` assertion needs an exact live file/function or
test reference. Do not call a field frozen merely because a validator once
checked it. Do not propose prompt, story-quality, length-tier, Lemmy, render,
or upscaler work in this report.

Stop after writing and rereading
`SONNET_LEDGER_BIBLE_AUDIT.md`. Report its absolute path and any tests/probes
you ran. Do not make any other change.
