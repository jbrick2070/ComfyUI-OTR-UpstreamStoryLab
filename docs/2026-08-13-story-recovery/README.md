# Story recovery evidence pack

This directory is the handoff for restarting story work in the Story Lab
without copying the current production writer wholesale.

- `LEDGER_BIBLE_AUDIT_PLAN.md` makes the current first gate a code-first audit
  of the complete ledger lifecycle and every downstream consumer.
- `CODEX_LEDGER_BIBLE_AUDIT.md` is the independent grounded audit.
- `LEDGER_BIBLE_SYNTHESIS.md` records reviewer convergence and corrections.
- `../LEDGER_BIBLE.md` is the human target contract; the machine authority is
  under `../../contracts/` and executable in
  `../../src/upstream_story_lab/ledger_contract.py`.
- `AGY_LEDGER_BIBLE_AUDIT_PROMPT.md` is the standalone universal prompt;
  `AGY_LEDGER_BIBLE_AUDIT.md` is its preserved raw report. Verified claims and
  corrections are already incorporated into the synthesis.
- `SONNET_LEDGER_BIBLE_AUDIT_PROMPT.md` is a separate read-only Sonnet
  red-team prompt. Its preserved raw output is
  `SONNET_LEDGER_BIBLE_AUDIT.md` (Sonnet 5 evidence, Fable 5 organization-only
  final pass); grounded agreements and corrections are in
  `LEDGER_BIBLE_SYNTHESIS.md`. Neither file overwrites the AGY or Codex lanes.
- `PROBLEM_STATEMENT.md` defines the observed failures and the desired story
  contract.
- `RECOVERY_MATRIX.md` says which old/current OTR mechanisms are worth
  restoring, porting, comparing, or excluding.
- `LENGTH_TIER_EXPERIMENT.md` defines the four-value length experiment and
  keeps words out of the acceptance contract.
- `DEEP_RESEARCH_BRIEF.md` is a paste-ready academic/technical research prompt
  for pressure-testing the scalable chunk hierarchy.
- `../../fixtures/story_recovery/` contains hash-pinned projections of one
  clean legacy `science_news` episode and the 2026-08-13 rendered-but-bad
  `scifi_news` episode, plus the machine-readable
  `ledger_requirements_v1.json` contract.
- `../../scripts/extract_story_recovery_cases.py` is the deterministic
  extractor for those projections.
- `../../tests/test_story_recovery_artifacts.py` verifies that the checked-in
  evidence has not drifted.

Status: the AGY, Codex, and Sonnet audits have been preserved and reconciled;
the live l4 lifecycle/consumer audit and structural Story Lab story-plane
contract are complete. Trusted semantic validators, production-state receipt
schemas, schema generation, and an explicit digest-preserving OTR adapter are
next. Source-bank story paths and length work remain blocked. No production
writer, prompt, workflow, or render lane was changed by this staging chunk.
