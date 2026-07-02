VERDICT: yes-with-fixes. All R3 MUST-FIX items are confirmed resolved in live
code. Two R3 SHOULD-FIX items remain open in code and were never explicitly
deferred -- they will mislead bridge developers reading preview output and
confuse users before a transplant can begin.

---

MUST-FIX BEFORE BUILD

None -- plan converged on MUST-FIX items. All six R3 MUST-FIX defects are
confirmed closed against the actual source:

- [R3-1] Stale _VISUAL_STYLES_CACHE: fixed. catalogs.py:406-450 adds
  _VISUAL_STYLES_STAMP; cache rebuilds when stamp changes.
- [R3-2] __pycache__ in _lab_state_digest: fixed. nodes.py:104-107 filters
  `"__pycache__" not in p.parts and p.suffix != ".pyc"`.
- [R3-3] story_pipeline_id dropped from LedgerWritingSpec: fixed.
  contracts.py:168 adds the field; preview.py:108-133 threads it through
  build_spec_from_material(); nodes.py:373-379 passes it in OTR_StoryPackPreview.
- [R3-4] requirements.txt missing: fixed. requirements.txt:1 is
  `pydantic>=2.0,<3.0`.
- [R3-5] No formal test suite: fixed. tests/test_lab_contracts.py has 4 passing
  tests covering public-domain spec, visual-style fixture registration,
  mismatched-policy rejection, and custom-source-bank fail-loud behavior.
- [R3-6] pytest import broken on hyphenated folder: fixed. __init__.py:8-16 uses
  try/except ImportError to fall back to absolute import for pytest.

---

SHOULD-FIX

1. [R3-SHOULD-8] [nodes.py:132-139] _find_source_packet() always returns the same
   source packet for every media_archive story model.
   Defect: OTR_StoryPackPreview.preview() with source_bank_id="media_archive"
   and story_model_id="cinematic_humorous", "gentle_thriller",
   "happy_archive_mystery", or "broadcast_history_comedy" all receive the
   "media_archive_restoration_adventure.json" packet. The resulting
   result["ledger_writing_spec"] will show restoration-adventure source material
   regardless of which model was selected. A bridge developer reading these
   previews will conclude that every media_archive model draws from the same
   source story, which is wrong. The issue was flagged in R3 and never deferred
   explicitly -- it was silently carried forward.
   Fix: add a "source_packet_note" field to the preview result JSON
   ("shared fixture, not model-specific") OR add per-model fixture packet routing
   stubs in _find_source_packet(). The note approach is a one-line change
   and is sufficient for a lab fixture.

2. [R3-SHOULD-9] [nodes.py:83-88] _story_model_choices() includes
   "simple_4_prompt_experimental" in the story_model_id dropdown.
   Defect: _story_model_choices() collects story_model_id from every pack
   including fixtures/story_packs/experimental/simple_4_prompt_experimental.json.
   The dropdown shows "simple_4_prompt_experimental" alongside narrative model
   IDs. If a user selects source_bank_id="media_archive" and
   story_model_id="simple_4_prompt_experimental", get_story_model() at
   nodes.py:366 raises UnknownStoryModelError with no context about why
   "simple_4_prompt_experimental" is not a valid narrative model for that bank.
   The cross-validation at nodes.py:329-339 (story_pack key mismatch) would also
   fire before this, but the error message "Selected dropdowns do not match the
   selected story pack" is equally opaque for a new user.
   Was flagged in R3, never deferred explicitly.
   Fix: exclude packs where story_pipeline_id == story_model_id from
   _story_model_choices(). One condition in the set comprehension at line 84-87.
   This excludes the experimental pack from the model dropdown without hiding it
   from the story_pack dropdown, where it belongs.

---

OPTIONAL / NICE-TO-HAVE

- [nodes.py:83-88] _story_model_choices() has no stamp-based cache, unlike
  _visual_style_choices() (which uses get_visual_style_ids() -> get_visual_styles()
  which IS cached). On every INPUT_TYPES call it loads all 12 pack JSON files
  just to extract story_model_id. Not a correctness issue, but the inconsistency
  with the cached pattern is visible.

- [tests/test_lab_contracts.py:64-65] test_custom_source_bank_preview_fails_loudly
  registers "story_lab_nodes" into sys.modules with no teardown. If pytest
  re-imports this module in a later test in the same process, it gets the cached
  partial module. Not a current issue (only 4 tests, all isolated), but a fragile
  test fixture pattern. Add a finalizer or use importlib in a narrower scope.

- [src/upstream_story_lab/__init__.py] PublicDomainSourceManifest and StoryPack
  are defined in contracts.py but not re-exported from the package __init__.py.
  Neither nodes.py nor validate_lab.py uses the package-level import for these
  (both import directly from upstream_story_lab.contracts), so there is no
  runtime error. But the package interface is incomplete and will surprise
  a future bridge developer doing `from upstream_story_lab import StoryPack`.

---

CUT THESE

None. No over-engineering remains in the current code. The validate_lab.py
required_pack_keys set (lines 119-132) was flagged as potentially diverging in
R3, but it is a closed set that matches the 12 confirmed fixtures and is
appropriate for a green-gate validation script.

---

VERIFY-AT-BUILD checklist

These items were marked UNVERIFIABLE in prior rounds and remain unresolvable
from this repo. Each requires a concrete step at bridge/transplant build time.

V1. [preview.py:136-150] build_legacy_news_mirror() key set vs production
    meta.news contract.
    Verify: before writing the bridge node, open
    ComfyUI-OldTimeRadio/nodes/_otr_ledger_writing_spec.py (or wherever
    meta.news fields are consumed) and confirm the 8 keys returned by
    build_legacy_news_mirror() -- title, headline, script_brief, news_close_brief,
    casting_brief, key_terms, link, source_hash -- exactly match what the
    production ledger consumers read. Add a test that asserts these keys against
    the authoritative production list before the bridge node is wired.

V2. [TRANSPLANT_MANIFEST.md] Production ledger node key contract.
    Verify: read ComfyUI-OldTimeRadio/nodes/_otr_ledger_writing_spec.py,
    _otr_source_packets.py, and OTR_LedgerScriptWriter.py before the transplant
    begins. The TRANSPLANT_MANIFEST.md gate "Compatibility mirror to meta.news.*
    is exact and centralized" is NOT met by the current lab-internal hardcoded
    key list in validate_lab.py:147-156. The lab test was written here, not
    derived from the production contract.

V3. [TRANSPLANT_MANIFEST.md gates] Five of the eight ready-to-transplant gates
    listed in TRANSPLANT_MANIFEST.md are not covered by any test in
    tests/test_lab_contracts.py:
    - "Story model catalog has source-scoped tests" -- no negative test for
      each source bank rejecting invalid story_model_id values.
    - "Prompt profile rendering has negative tests for forbidden sci-fi/news
      phrases" -- test_public_domain_spec_builds_with_pipeline_id does not
      assert forbidden-term absence.
    - "Visual style policies have negative tests for hardcoded cinematic/radio
      tails" -- no test.
    - "Compatibility mirror to meta.news.* is exact and centralized" -- blocked
      on V2 above.
    - "Canonical workflow JSON validation plan is written" -- TRANSPLANT_MANIFEST.md
      lists steps but no concrete validation command is specified.
    These gates must be satisfied before the bridge/transplant chunk starts.

---

INTERNAL CONSISTENCY CHECK

- R3 final states "4 passed in 0.04s" -- confirmed against
  tests/test_lab_contracts.py (4 tests, no skips visible in cache).
- R3 final states "story_packs=12" -- confirmed: 12 JSON files under
  fixtures/story_packs/ (5 media_archive, 5 public_domain, 1 science_news,
  1 experimental).
- R3 final states "public_domain_manifests=3" -- confirmed: 3 manifest.json
  files under fixtures/public_domain_sources/ (book_chapter_sample,
  comic_page_sample, play_scene_sample).
- R3 final states "production_workflow not touched" -- confirmed:
  git diff output shows no change to otr_scifi_16gb_full.json.
- NODE_CLASS_MAPPINGS wires OTR_UpstreamStoryLabValidator and OTR_StoryPackPreview;
  both have matching NODE_DISPLAY_NAME_MAPPINGS entries. CATEGORY, FUNCTION,
  RETURN_TYPES, RETURN_NAMES all set correctly.
- No IMAGE/LATENT tensors in these nodes; tensor layout invariants are not
  applicable.
- No heavy imports at nodes.py module top level; pydantic is lazy-imported
  inside function bodies.
- IS_CHANGED returns _lab_state_digest() on both nodes; this is correct since
  both depend on fixture files. The digest excludes __pycache__ and .pyc files
  (R3-2 fix confirmed).
- LedgerWritingSpec.story_pipeline_id field has default "legacy_many_pass" with
  no Literal constraint. Any string is accepted by Pydantic. This is not a
  defect -- the widget is dropdown-constrained at the ComfyUI layer. Acceptable.

[ASSUMPTION] The R3 validation run output shown in input.md reflects the current
code state. The pytest cache confirms tests/test_lab_contracts.py ran against
cpython-312; no source changes are visible that would invalidate those results.

[ASSUMPTION] No other ComfyUI custom node in the session imports
upstream_story_lab at module top level. The sys.path mutation ordering in
_ensure_lab_importable() is safe only under this condition.
