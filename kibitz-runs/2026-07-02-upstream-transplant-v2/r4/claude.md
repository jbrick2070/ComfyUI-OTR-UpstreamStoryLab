VERDICT: yes-with-fixes. One code-vs-test contradiction in the landed tree blocks a green test run today; one PATCH_PLAN ambiguity would force an implementor to guess at transplant time.

MUST-FIX BEFORE BUILD:

1. [r4/input Applied #1 + PATCH_PLAN New modules, _otr_source_interpreter] The source interpreter facade has a CODE vs TEST contradiction that cannot both be right. _otr_source_interpreter.py:78 calls `news_briefs_builder(article=article, **builder_kwargs)`, passing `article` as a keyword argument. But production build_news_briefs (news_interpreter.py:731-746) accepts `technical_fn`, `full_text`, `headline`, `summary`, `outlet`, `pub_date`, `style`, `seed` -- it does NOT accept `article`. And the test at test_transplant_modules.py:133-139 explicitly asserts `"article" not in calls` and expects mapped keywords like `calls["headline"]`, `calls["outlet"]`, `calls["pub_date"]`. The code and the test are incompatible; running pytest today would fail on `test_facade_science_wraps_builder_verbatim`. The r3 synthesis claims "46 pytest green" (r4/input.md:5) but this test cannot pass against the current code. Concrete fix: update _otr_source_interpreter.py lines 62-85 to map the article dict fields to the production build_news_briefs keyword signature before calling the builder. Specifically, the science branch should do:

    mapped = {}
    if article:
        mapped["full_text"] = article.get("full_text", "")
        mapped["headline"] = article.get("headline", "")
        mapped["summary"] = article.get("summary", "")
        mapped["outlet"] = article.get("source", "")
        mapped["pub_date"] = article.get("date", "")
    mapped.update(builder_kwargs)
    briefs = news_briefs_builder(**mapped)

This aligns with what the test already expects and what production build_news_briefs actually accepts.

2. [PATCH_PLAN #1, lines 44-47] "non-science banks ignore the style slug" is ambiguous enough to produce incompatible implementations. Production _resolve_inputs uses the resolved style variable downstream for cast locking (OTR_LedgerScriptWriter.py:3010), outline (3178), metadata (5286), and the visual plan (5415-5417). The plan must specify: (a) what value resolved["style"] takes for non-science banks (empty string? the story_model_id? a constant like "profile_driven"?), (b) whether the style/style_custom widgets are hidden via forceInput or simply ignored by code branching, and (c) a test assertion proving the value. Without this, two builders could wire style handling differently and produce silently different metadata stamps.

SHOULD-FIX:

1. [GO_FORWARD_PLAN, line 21] Test count is stale: GO_FORWARD says "41 pytest" but r4/input says "46 pytest green" and I count 43 `def test_` functions across 6 test files (some may be parameterized). Either reconcile to the actual collected count or replace hardcoded counts with "all tests in `pytest tests/` pass" which cannot drift.

2. [GO_FORWARD_PLAN Chunk T1, lines 47-64] The _fetch_science_news verify step from PATCH_PLAN:16-19 ("VERIFY-AT-TRANSPLANT: the live RSS path imports story_orchestrator._fetch_science_news") is not reflected in GO_FORWARD_PLAN's T1 step sequence. It should be step 0 or 1a, since the writer edits in step 2 depend on knowing this import exists and its failure mode is compatible. A builder following GO_FORWARD_PLAN alone would miss it.

3. [PATCH_PLAN #9 vs nodes.py:198-201 + contracts.py:388] Widget names vs whitelist key names use different vocabularies without an explicit mapping. PATCH_PLAN #9 says whitelist keys are `source_bank`, `story_model`, `story_pipeline`, `visual_style` (matching ResolutionDecision.axis values). But the INPUT_TYPES widget names in the lab are `source_bank_id`, `story_model_id`, etc. (nodes.py:198-201), and the LedgerWritingSpec fields use `_id` suffixes (contracts.py:430-433). The PATCH_PLAN should state: writer INPUT_TYPES widgets will be named `source_bank_id` / `story_model_id` / `story_pipeline_id` / `visual_style_id` (matching production convention), while the otr_api.py and _otr_workflow_apply.py routing whitelists use the axis names without `_id`. This is probably the intent but a builder reading the plan cold could conflate them.

OPTIONAL / NICE-TO-HAVE:

1. The emit filename test (test_bridge_e2e.py:89-94) hashes `spec.model_dump(mode="json")` but nodes.py:290-292 hashes `artifact.ledger_writing_spec.model_dump(mode="json")`. These are semantically equivalent today (spec IS the ledger_writing_spec), but the test should use the same expression as the production code for clarity and to catch any future divergence.

CUT THESE:

1. [GO_FORWARD_PLAN lines 21-22] Hardcoded historical test counts ("41 pytest"). They already drifted (r4/input says 46, actual is ~43-46 depending on parameterization) and add no safety beyond the gate commands themselves. Replace with "pytest tests/ green" and move on.

VERIFY-AT-BUILD checklist:

1. _fetch_science_news import and failure behavior: story_orchestrator.py is NOT mirrored (confirmed: PRODUCTION_MIRROR_MANIFEST.md lists 22 files; story_orchestrator is absent). Before writer edits land, run `from nodes import story_orchestrator; story_orchestrator._fetch_science_news` in the production venv and confirm the failure path (feedparser unavailable) produces the expected deterministic synthetic seed, not an unhandled crash.

2. Re-mirror check: production HEAD must still be d48a9d76f39db6db16c758d9b2c1c22a9af38d3f. The provenance test (test_bridge_e2e.py:73-75) pins this exact hash against PRODUCTION_MIRROR_MANIFEST.md:13. If production moved, refresh production_mirror/, rerun drift tests, update the manifest, and re-pin the test.

3. n_optional assertion: currently 16 (OTR_LedgerScriptWriter.py:5738). The transplant appends new widgets (source_bank_id, story_model_id, story_pipeline_id, visual_style_id, bridge_artifact_path at minimum). The assertion value must be updated to 16 + N in the SAME chunk as the widget append (PATCH_PLAN ATOMICITY section covers this, but the exact new value must be determined at transplant against the live INPUT_TYPES).

4. Whitelist parity: after adding keys to otr_api.py and _otr_workflow_apply.py, run the parity test asserting both whitelists carry the same key set (PATCH_PLAN #9, r4/input Applied #8).

5. Adapter vs real NewsBriefs: production-side test must instantiate `NewsBriefs(**bridge_artifact["meta_mirrors"]["news"])` with the real production class, not just pinned key-set validation. The adapter supports this path (news_briefs_model parameter at _otr_ledger_input_adapter.py:57) but it is only exercised when wired in the production test suite.

6. Source interpreter facade: after fixing MUST-FIX #1, rerun the full test suite including test_facade_science_wraps_builder_verbatim to confirm the article-to-kwargs mapping matches production build_news_briefs exactly. Wire a production-side test calling the facade with the real build_news_briefs function (not a mock) against a fixture article dict.
