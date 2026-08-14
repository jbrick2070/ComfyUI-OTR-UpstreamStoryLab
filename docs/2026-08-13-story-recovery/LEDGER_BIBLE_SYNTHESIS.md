# Ledger Bible review synthesis

Updated: 2026-08-13

Inputs preserved separately:

- `AGY_LEDGER_BIBLE_AUDIT.md` — raw Antigravity audit
- `CODEX_LEDGER_BIBLE_AUDIT.md` — independent grounded Codex audit
- `SONNET_LEDGER_BIBLE_AUDIT.md` — preserved raw Sonnet 5 evidence/red-team
  with a final organization-only Fable 5 pass; its claims were independently
  regrounded before incorporation here

## Converged result

Antigravity and Codex independently found the same underlying problem: the
current OTR ledger mixes accepted story truth with progressively measured media
truth. A single whole-object freeze at Phase 10 is incompatible with the real
consumer chain.

The adopted contract is one JSON envelope with:

1. an immutable `story_ledger`;
2. a canonical `story_seal`;
3. phase-owned append-only `production_state`;
4. a terminal `final_seal` after publish and audit.

The machine decision is `contracts/ledger_bible_v1.json`; the human contract is
`docs/LEDGER_BIBLE.md`.

## Reviewer agreement

Both audits support these points:

- Phase 10 is not a whole-document freeze.
- Legal downstream writes include voice, timing, music, image, render,
  path/publication, and audit truth.
- ComfyUI wire JSON, active disk ledger, derived manifests, and filesystem
  artifacts are distinct representations.
- Every field needs one lifecycle owner and an explicit durability/failure
  policy.
- Facts, speaker authority, sequence topology, and music bookends belong in the
  accepted story contract.
- The current l4 schema needs an explicit adapter/migration decision rather
  than silent promotion.
- The first implementation work is CPU-only contract characterization, not a
  prompt rewrite or render campaign.

## Grounded corrections to AGY

AGY's report is valuable but its confidence labels do not override live code.
Codex grounded six material corrections:

1. The narrative plane is not “strictly frozen” at Phase 10. Validation and
   narrow hashes exist; enforcement after later saves does not.
2. The present one-dict system reveals two categories of truth but does not
   already implement the explicit two-plane target.
3. SilentComposite is a clip-manifest/media consumer, not an episode-ledger
   writer.
4. CaptionBurn reads the timed ledger and writes ASS/video, not ledger state.
5. CreditsRoll reads the live singleton and renders credits; it does not stamp
   `meta.credits_receipt`.
6. Canonical video rendering does not durably populate root `clips` or the
   enriched `video.shots`: those truths live in wire/state capture,
   filesystem, and clip manifest. Only selected meta receipts are durable.

These corrections are executable assertions in
`tests/test_ledger_bible_contract.py` and explicit rows in
`contracts/ledger_consumer_matrix_l4.json`.

## Grounded reconciliation of Sonnet 5

Sonnet's nine-agent report independently confirms the governing result: Phase
10 is a status/structural gate, not a whole-ledger freeze; accepted story truth
is later mixed with cast, timing, music, visual, publication, and audit truth.
It also confirms the SciFi fact-ID loss, post-Phase-10 speaker-role mutation,
different save/merge policies, and the possibility that publication succeeds
before its final ledger stamp does.

Useful verified deltas are now recorded without changing the target contract:

- the July control is historical evidence, not a valid v1 fixture: its cast
  identifies the announcer as `c01` while its lines use `announcer`, so any
  promotion requires an explicit identity migration;
- `OTR_AudioEnhance` has no direct node-level test in the current production
  suite, reinforcing the need for phase-owned receipt tests; and
- Sonnet's proposed separate timeline and nested voice/portrait state are
  concrete examples of the already-adopted story/production split, not a
  reason to preserve the mixed mutable l4 dictionary.

Six Sonnet claims required correction after checking the live tree and git
history:

1. AGY's `_otr_ledger_reviewer.py::apply_deterministic_cast_repairs` citation
   is stale, not fabricated. The file and function existed through the parent
   of OTR commit `314dd481`; that commit retired the source. Its historical
   guard refused a proposed character-to-announcer **char-id remap**. Current
   `cast_lock.py` performs a different repair: when an existing announcer
   `char_id` is mislabeled `speaker_role=character`, it reroutes the role to
   announcer. Neither historical behavior establishes a current freeze guard.
2. The portrait helper is not untested: production directly tests
   `stamp_portrait()` and `resolve_portrait_path()` in
   `test_image_platform_c1.py` and `test_video_platform_aseam.py`. Its cast
   hash is still wire-only under the canonical dispatcher's durable stamp.
3. The grounded Codex matrix already includes `LedgerScriptWriter`,
   `VRAMContextTest`, `SaveToEpisodeWorkspace`, and the portrait helper paths
   that Sonnet correctly found missing from AGY's inventory.
4. Reusing the literal `b001` as a legacy `line_id` and `beat_id` is not a v1
   collision. IDs are typed and unique within their own tables; every
   cross-table reference is validated by kind. A future migration may rename
   them for clarity, but v1 does not invent a global ID namespace.
5. Sonnet is correct that AGY named two nonexistent current test paths,
   `test_otr_ledger_freeze.py` and `test_otr_freeze_cascade.py`. The relevant
   production coverage is distributed across
   `test_lfc_phase_0_10_gap_audit.py`, `test_g8_line_id_uniqueness.py`,
   `test_provenance_v4.py`, and `test_scene_guard_v4.py`; the raw AGY report is
   preserved rather than silently repaired.
6. `ledger_contract.py` is no longer an orphaned draft: it is exported by the
   package, exercised by the contract suite, and bound to the machine/human
   Bible artifacts. The production adapter and runtime emission path remain
   intentionally pending, which is different from an unwired production
   claim.

Sonnet's proposed minimal in-place retrofit is therefore not the Story Lab
architecture. Repairs such as speaker-role correction must happen before
acceptance or fail closed; they do not get a post-seal mutation escape. The
one-envelope/two-plane/two-seal design remains the judged convergence.

## Executable hardening after the independent audit

A final code review found places where the first executable draft promised
more than it enforced. The lab contract now:

- rejects non-null `production_state` and `final_seal` until their strict typed
  schemas exist;
- uses typed `{kind, ref_id}` outcome evidence and verifies the exact packet,
  fact, line, and cue classes required by each outcome;
- refuses to build/admit a seal unless a code-owned trusted verifier registry
  accepts all five receipts;
- revalidates a fresh story serialization before hashing, rejects blank
  required text, and rejects unused source, fact, or cast rows;
- requires a timezone-aware UTC seal time and guards the complete seal receipt,
  not only its digest.

This does not pretend that the real semantic validators or production receipt
schemas already exist. Both remain explicit pre-transplant work.

## Decisions now locked for Story Lab

- One output file, not a loose set of media or sidecar artifacts.
- Story Lab stops after `story_ledger` + `story_seal`.
- `episode_id` is stable story-edition identity; production gets a separate
  `run_id` and renameable workspace identity.
- `speaker_role` (`announcer|character`) is separate from program
  `sequence_role`.
- `fact_ids` survive into every spoken-line row and the coda references at
  least one source fact.
- Exact sequence authority is music open, announcer open, character story,
  optional script-requested interstitials, factual announcer coda, music close.
- No action, stage direction, third-person narration, or delivery note is a
  spoken row.
- Word count and measured duration are telemetry, not Story Ledger acceptance.
- Changing accepted story content requires a new sealed story, not an in-place
  repair after acceptance.
- Current l4 has no automatic migration because lost facts/semantic roles
  cannot be reconstructed honestly.

## What remains before production transplant

1. Build and register the five trusted semantic outcome verifiers over the
   sealed control/challenger evidence, then add a complete normative v1 fixture
   plus rejected mutation corpus.
2. Define strict production-state attempt/receipt schemas per phase.
3. Generate static JSON Schema and documentation from the executable models.
4. Build the explicit Story Lab→OTR adapter and prove story-byte/digest
   preservation.
5. Move current post-acceptance writers behind phase ownership and enforce the
   story seal at both save paths and all wire/disk joins.
6. Define terminal audit ordering and final-seal enforcement.

Only then should source-bank story paths, the four length-tier process, Lemmy,
or the seven parked render legs resume.
