VERDICT: yes-with-fixes. The lab's internal wiring is mostly sound, but three
defects -- stale visual-style cache, __pycache__ pollution of IS_CHANGED, and
story_pipeline_id silently dropped from LedgerWritingSpec -- each break a
different layer before any bridge node can safely touch the production workflow.

---

MUST-FIX BEFORE BUILD

[1] Stale _VISUAL_STYLES_CACHE after IS_CHANGED re-runs
    File: src/upstream_story_lab/catalogs.py:405-430
    Defect: _VISUAL_STYLES_CACHE is a module global set once, never cleared.
    IS_CHANGED returns a new digest when fixture mtimes change, so ComfyUI re-runs
    the node in the same Python process -- but get_visual_styles() still returns the
    cached dict from the first run. A user who edits fixtures/visual_styles/*.json
    will get stale visual policy applied silently until ComfyUI restarts.
    The _BASE_VISUAL_STYLES+fixture merge is only done once per interpreter
    lifetime regardless of how many IS_CHANGED triggers fire.
    Fix: add a version stamp (e.g., the digest string) alongside the cache, check
    it on every get_visual_styles() call, and rebuild when the stamp is stale. One
    module-level dict for (stamp -> policy_dict) is sufficient.

[2] __pycache__ files included in _lab_state_digest()
    File: nodes.py:89-94
    Defect: _state_files() calls folder.rglob("*") over LAB_ROOT/"src", which
    picks up src/upstream_story_lab/__pycache__/*.pyc. Python writes/updates .pyc
    files on every import, including every cold ComfyUI startup. This means
    IS_CHANGED returns a new digest on every restart -- every cached node output is
    immediately invalidated. Downstream: every graph load triggers a full node
    re-run even with zero fixture changes.
    Fix: in _state_files(), skip paths whose any parent component is "__pycache__"
    and skip files with suffix ".pyc". One condition in the list comprehension
    at line 93 closes this.

[3] story_pipeline_id not carried into LedgerWritingSpec
    Files: contracts.py:161-181, nodes.py:298-365
    Defect: OTR_StoryPackPreview accepts story_pipeline_id as an input widget,
    validates it against the pack key, then discards it. LedgerWritingSpec has no
    story_pipeline_id field. The validated spec handed to the bridge node carries
    no routing signal for which LLM pipeline to run (legacy_many_pass vs
    simple_4_prompt_experimental). Any bridge or transplant node that consumes
    LedgerWritingSpec cannot route correctly without this field.
    This is the single biggest interface gap before a bridge node is written.
    Fix: add story_pipeline_id: str field to LedgerWritingSpec (default
    "legacy_many_pass"); thread it through build_spec_from_material(); verify
    the Pydantic validator still passes. The model_validator at line 174 only
    checks visual_policy -- it does not conflict.

[4] build_legacy_news_mirror() not verified against production meta.news key set
    Files: preview.py:134-148, TRANSPLANT_MANIFEST.md (gate: "Compatibility mirror
    to meta.news.* is exact and centralized")
    Defect: the mirror returns 8 hardcoded keys. No test checks these against
    the real key contract expected by the production ledger nodes
    (verify: ComfyUI-OldTimeRadio/nodes/_otr_ledger_writing_spec.py or
    OTR_LedgerScriptWriter.py -- not visible from this repo). If production
    expects "close_brief" but the mirror emits "news_close_brief", the bridge will
    produce silently malformed ledger dicts. The validate_lab.py check at line
    144-158 tests that the mirror contains those 8 keys, but that test was written
    here, not derived from the production contract.
    This is a transplant gate condition per TRANSPLANT_MANIFEST.md and is unmet.
    Fix: read the production meta.news field list from its authoritative source
    (the ledger schema or OTR_LedgerScriptWriter usage), add a test that compares
    build_legacy_news_mirror() output keys against that canonical set before the
    bridge node exists.

[5] No formal test suite -- all TRANSPLANT_MANIFEST.md gate conditions are unmet
    File: TRANSPLANT_MANIFEST.md (gates section), scripts/validate_lab.py
    Defect: validate_lab.py is a standalone assertion script, not a pytest suite.
    The manifest lists six gate conditions (contracts have pure tests, catalog has
    source-scoped tests, prompt profiles have negative tests, visual styles have
    negative tests, mirror is exact, workflow validation plan is written). None of
    these are satisfied. "Gate condition" implies something that can be checked
    mechanically before a PR is merged; a one-file CLI script that the developer
    runs manually does not meet that bar.
    Fix: convert validate_lab.py into pytest parametrize cases or add a tests/
    directory with at minimum: one test per contract class, one negative test per
    source bank profile (forbidden term leakage), and one test that asserts
    build_legacy_news_mirror() keys against the canonical production set.

---

SHOULD-FIX

[6] validate_lab.py visual style assertion compares merged catalog to fixture-only
    list -- passes by accident today
    File: scripts/validate_lab.py:74-78
    Defect: get_visual_style_ids() returns the union of _BASE_VISUAL_STYLES + fixture
    overrides. The RHS of the assertion globs only fixture files. Today all 5 base
    styles have matching fixture files so both sides produce the same sorted list.
    Add a sixth style to _BASE_VISUAL_STYLES without a fixture file and the
    assertion fires with a confusing message ("fixtures do not match catalog") for
    code that is actually correct. Add a fixture file for a new style before
    registering it in _BASE_VISUAL_STYLES and the assertion passes silently even
    though the base catalog is out of sync.
    Fix: replace the equality check with: (a) verify every fixture file round-trips
    cleanly (already done in the loop above it), and (b) verify every fixture
    style_id is present in get_visual_style_ids(). Drop the strict equality.

[7] _story_pack_choice_map() called 3-4 times per INPUT_TYPES invocation
    File: nodes.py:274, 286, 112-115
    Defect: INPUT_TYPES for OTR_StoryPackPreview calls _story_pack_choice_map()
    at line 274 (explicit) and again via _default_story_pack_choice() at line 286.
    _default_story_pack_choice() itself calls _story_pack_choice_map() at line 113
    and potentially again at line 115 (if the fallback path is taken). Each call
    loads and Pydantic-validates all 12 fixture JSONs from disk. IS_CHANGED
    triggers INPUT_TYPES re-evaluation. No in-process caching exists for this path
    even though the _VISUAL_STYLES_CACHE pattern is already present in catalogs.py.
    Fix: add a module-level _story_pack_choice_map_cache similar to
    _VISUAL_STYLES_CACHE, keyed by the same lab-state digest, cleared when the
    digest changes.

[8] _find_source_packet() couples all story models for a source bank to one fixture
    File: nodes.py:118-125, 357
    Defect: every media_archive story model (cinematic_humorous, gentle_thriller,
    happy_archive_mystery, broadcast_history_comedy) receives the same
    "media_archive_restoration_adventure.json" source packet in preview(). The
    preview output for these models will show restoration-adventure source material
    regardless of which model is selected. This is not noted anywhere in the
    fixture, the function docstring, or the preview output JSON.
    This will produce misleading previews before per-model fixture packets exist.
    Fix: either document the placeholder explicitly in the function and in the
    preview result JSON ("source_packet_note": "shared fixture, not model-specific"),
    or add per-model fixture routing stubs.

[9] simple_4_prompt_experimental appears in the story_model_id dropdown
    Files: nodes.py:74-79, validate_lab.py:130
    Defect: _story_model_choices() extracts story_model_id from every pack file,
    including the experimental one. "simple_4_prompt_experimental" appears in the
    story_model_id dropdown next to narrative model IDs like "faithful_radio_adaptation".
    Selecting it with source_bank_id != "custom_source_bank" triggers get_story_model()
    which raises UnknownStoryModelError -- a hard error with no context for the user.
    Selecting it with source_bank_id == "custom_source_bank" bypasses the catalog
    entirely (the skip guard at nodes.py:161) but still calls get_profile() which
    will raise UnknownStoryModelError.
    Fix: exclude packs with story_pipeline_id == story_model_id (or status ==
    "experimental") from the story_model dropdown, or give the experimental pack a
    distinct story_model_id that is clearly not a narrative model.

---

OPTIONAL / NICE-TO-HAVE

- The required_pack_keys set in validate_lab.py:118-133 is a hardcoded manual
  manifest. It will silently diverge as packs are added. Could be auto-derived by
  scanning the fixture directory and comparing against the expected registry.

- _default_story_pack_choice() calls _story_pack_choice_map() at line 113, and
  again at line 115 if the substring match fails. A local variable would prevent
  the second scan.

- [ASSUMPTION] The sys.path.insert(0, str(LAB_SRC)) in _ensure_lab_importable()
  is safe as long as no other ComfyUI node imports upstream_story_lab without
  routing through this package. If another node tries to import upstream_story_lab
  before _ensure_lab_importable() runs (e.g., at module top), the import will fail
  with no path in sys.path. This is low risk given the current sibling-repo layout
  but fragile if the package is ever vendored into a different repo.

---

CUT THESE

[10] The strict equality assertion get_visual_style_ids() == sorted(fixture style_ids)
     in validate_lab.py:74-78 -- replace with the simpler membership check
     described in SHOULD-FIX [6]. The equality check is over-engineering a
     correctness property that the current architecture (base catalog + fixture
     overrides) cannot satisfy by construction. It will cause false failures as
     the catalog grows.

[11] The "Future Transplant Script" (scripts/plan_transplant.py --dry-run/--apply)
     described in TRANSPLANT_MANIFEST.md -- do not build this until: the bridge
     node exists, all gate conditions have tests, and at least one dry-run transplant
     patch has been manually reviewed. Building the apply machinery before the target
     state is well-defined is scope creep that adds risk, not safety. The checklist
     form in TRANSPLANT_MANIFEST.md is sufficient for now.

---

[ASSUMPTION] markers:
- "verify: production meta.news key set" -- the authoritative key list lives in
  ComfyUI-OldTimeRadio (not visible from this repo). Every claim about
  build_legacy_news_mirror() correctness depends on reading that file before
  the bridge node is written.
- "verify: ComfyUI-OldTimeRadio/nodes/_otr_ledger_writing_spec.py and
  OTR_LedgerScriptWriter.py" -- the downstream ledger consumer key set is not
  visible here. TRANSPLANT_MANIFEST.md lists these as transplant targets but
  they have not been read in this review.
- [ASSUMPTION] No other custom node in the ComfyUI session imports
  upstream_story_lab at module top. The sys.path mutation ordering is safe only
  under this assumption.
