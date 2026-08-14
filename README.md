# OTR Upstream Story Lab

Status: story-recovery evidence and experimentation workspace as of
2026-08-13. Start with `docs/GO_FORWARD_PLAN.md` and
`docs/LEDGER_BIBLE.md`. The current l4 ledger and its downstream consumers have
been characterized; the Story Lab now has a strict two-plane/two-seal target
contract. Source-bank story paths stay parked until its production-state
receipts and OTR adapter are implemented.

The July transplant workspace remains preserved here as historical material.
The v1 standalone lab lives in git history at commit `41c6512`; recover any
piece with `git show 41c6512:<path>`. The frozen production mirror is not a
live production checkout.

## What this folder is now

```text
production_mirror/   pristine copies of the production files the transplant
                     will touch, pinned to ComfyUI-OldTimeRadio commit
                     d48a9d76 (post rip-sfx-broll). Read-only reference.
fixtures/story_recovery/
                     hash-pinned clean-control and live-regression evidence.
contracts/           machine Ledger Bible and current-l4 consumer matrix.
src/upstream_story_lab/ledger_contract.py
                     strict story graph, canonical hash and seal guard.
docs/2026-08-13-story-recovery/
                     current problem, recovery matrix, and length experiment.
workflows/           historical July working copy; not the live OTR workflow
                     and not an output of the ledger-only recovery lab.
docs/                current handoff plus preserved July planning/review
                     history.
kibitz-runs/         review-run history from the v1 lab phase.
```

See `PRODUCTION_MIRROR_MANIFEST.md` for the exact file list, hashes, and the
drift-check rule.

## Hard rules

- The lab emits one validated ledger JSON; it does not render or publish media.
- Production `ComfyUI-OldTimeRadio` stays unchanged until a lab result earns a
  separate transplant chunk.
- No hidden fallbacks; unknown source/story/style ids fail loudly.
- JSON owns content and configuration; Python owns validation, routing,
  execution, and fail-loud errors.
- `production_mirror/` and `workflows/` are historical references, not editable
  production surfaces.
- The old SFX surface is deleted (rip-sfx-broll 6bad6e5b); nothing here may
  reintroduce the `sfx` speaker role, `scene_broll`/`background_abstract`
  video roles, or `[SFX:]` tokens.

## Where the current plan lives

1. `docs/GO_FORWARD_PLAN.md` - current handoff and exact parking order.
2. `docs/LEDGER_BIBLE.md` - blessed Story Lab ledger boundary.
3. `docs/2026-08-13-story-recovery/LEDGER_BIBLE_SYNTHESIS.md` - independent
   review convergence and grounded corrections.
4. `docs/2026-08-13-story-recovery/LEDGER_BIBLE_AUDIT_PLAN.md` - completed
   consumer/freeze audit gate and next contract chunks.
5. `docs/2026-08-13-story-recovery/AGY_LEDGER_BIBLE_AUDIT_PROMPT.md` -
   standalone independent audit prompt.
6. `docs/2026-08-13-story-recovery/AGY_LEDGER_BIBLE_AUDIT.md` - preserved raw
   Antigravity report; corrected claims live in the synthesis.
7. `docs/2026-08-13-story-recovery/SONNET_LEDGER_BIBLE_AUDIT_PROMPT.md` -
   isolated Sonnet red-team prompt and output contract.
8. `docs/2026-08-13-story-recovery/SONNET_LEDGER_BIBLE_AUDIT.md` - preserved
   raw Sonnet 5 evidence report with its final organization-only Fable 5 pass;
   grounded agreements and corrections live in the synthesis.
9. `docs/2026-08-13-story-recovery/PROBLEM_STATEMENT.md` - hard outcomes and
   live evidence.
10. `docs/2026-08-13-story-recovery/RECOVERY_MATRIX.md` - what to save and what
   not to revive.
11. `docs/2026-08-13-story-recovery/LENGTH_TIER_EXPERIMENT.md` - the four-value
   duration experiment.
12. `docs/2026-08-13-story-recovery/DEEP_RESEARCH_BRIEF.md` - a paste-ready
   primary-source research task for the scalable chunk architecture.

The July review, prompt-surgery checklist, transplant manifest, and mirror
audit remain useful history, but they no longer define the next action.
