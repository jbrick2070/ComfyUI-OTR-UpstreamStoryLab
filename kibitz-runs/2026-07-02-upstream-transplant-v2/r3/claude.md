VERDICT: yes-with-fixes. The lab-side code is solid and tested; the transplant
modules are well-isolated. Two interface mismatches and one sequencing gap
must be fixed before the production wiring chunks land.

---

MUST-FIX BEFORE BUILD

1. [PATCH_PLAN item 7 / _otr_visual_style_policy.py] tail_overrides() key
   names do not match VisualStylePolicy JSON field names -- production callers
   must know which key maps to which constant.
   DEFECT: tail_overrides() (transplant_work/production_new_modules/
   _otr_visual_style_policy.py:82-87) returns {"style_tail": policy.get(
   "positive_tail",...)}. The VisualStylePolicy model (contracts.py:312) names
   the field "positive_tail", the production constant is "STYLE_TAIL_DEFAULT",
   and the override dict key is "style_tail". That is THREE names for the same
   string across three layers. When production _otr_story_brief_helpers
   (production_mirror:504) wires the override, the caller must map "style_tail"
   -> STYLE_TAIL_DEFAULT. If ANY future maintainer adds a field "style_tail" to
   VisualStylePolicy JSON (a reasonable name), it will shadow the mapping
   silently.
   FIX: Add a one-line comment in tail_overrides() documenting the mapping
   ("style_tail" <- policy.positive_tail <- production STYLE_TAIL_DEFAULT) so
   the transplant hunk author does not misconnect. Alternatively, rename the
   override dict key to "positive_tail" to match the model and let the
   production consumer do the constant-name mapping -- but this changes the
   transplant module's contract, so decide now before any production code
   consumes it.

2. [PATCH_PLAN item 1 / _otr_source_interpreter.py] close_brief <->
   news_close_brief mapping is duplicated in two independent code paths with
   no shared constant.
   DEFECT: bridge.py:107 maps story.close_brief -> news["news_close_brief"].
   _otr_source_interpreter.py:83 maps data["news_close_brief"] -> out[
   "close_brief"] for the science_news path. These are two independent
   hard-coded string mappings of the same field rename. If either side drifts
   (e.g. a rename in NewsBriefs), the other silently breaks. The compat.py
   NEWS_BRIEFS_FIELDS pin protects the NewsBriefs shape but does NOT protect
   the interpreter facade's reverse mapping.
   FIX: Either (a) add an assertion in test_transplant_modules.py that
   verifies the round-trip: close_brief -> news_close_brief -> close_brief
   survives through both bridge.build_meta_mirrors and
   _otr_source_interpreter.interpret_source for science_news, or (b) extract a
   shared constant CLOSE_BRIEF_MIRROR_KEY = "news_close_brief" referenced by
   both modules. Option (a) is cheaper and more defensive.

3. [PATCH_PLAN item 1 / nodes.py] IS_CHANGED divergence between nodes.py
   _lab_state_digest() and registry.state_digest().
   DEFECT: nodes.py:36-55 _lab_state_digest() hashes __init__.py, nodes.py,
   src/, fixtures/, AND production_mirror/. registry.py:348-357
   state_digest() hashes ONLY fixtures/. The provenance.lab_state_digest field
   (bridge.py:70) is set from registry.state_digest(), which does NOT include
   production_mirror changes. Therefore: a mirror refresh changes IS_CHANGED
   (ComfyUI re-runs the validator node -- correct) but does NOT change the
   provenance stamp in the bridge artifact. A bridge artifact emitted before
   and after a mirror refresh will carry the same lab_state_digest despite the
   validator now seeing different drift-check inputs.
   FIX: Either (a) have registry.state_digest() also hash production_mirror/
   (matching the node's scope), or (b) document this as intentional: the
   provenance stamps fixture state only, and mirror state is a separate
   validation-time concern. If (a), propagate the root path to the registry
   digest or add a mirror_digest field to Provenance. The current behavior is
   not wrong per se, but it is a hidden inconsistency a transplant author will
   trip over.

---

SHOULD-FIX

1. [PATCH_PLAN item 3 / _otr_style_picker.py] style_picker_overrides()
   returns keys {inventor_system_prompt, chooser_system_prompt,
   chooser_user_template} (transplant_work/production_new_modules/
   _otr_story_prompt_profile.py:82-86). The patch plan says pick_style()
   "gains the locked kwargs" with these names. Verify: the actual production
   pick_style() signature in production_mirror/nodes/_otr_style_picker.py
   does NOT yet accept these kwargs (it is the pre-transplant mirror). The
   transplant hunk must add them as keyword-defaulted parameters; if the
   default is not empty-string (triggering "keep constants" behavior), any
   call site that omits them will get the wrong default.
   verify: production_mirror/nodes/_otr_style_picker.py pick_style()
   signature and how it handles missing kwargs.

2. [PATCH_PLAN item 5 / _otr_outline.py] outline_request_fields() returns
   "outline_system_prompt" as a key (profile.py:72). The patch plan says
   OutlineRequest gains keyword-defaulted fields. The transplant module
   (_otr_story_prompt_profile.py:60-73) returns this in the dict, but it
   also returns "forbidden_plot_patterns" as a list. Verify:
   OutlineRequest.__init__() in production accepts both
   outline_system_prompt:str and forbidden_plot_patterns:list[str] as keyword
   args. If OutlineRequest is a Pydantic model with extra="forbid", passing
   an unexpected key will hard-error at runtime.
   verify: production_mirror/nodes/_otr_outline.py OutlineRequest class
   definition and its extra= config.

3. [PATCH_PLAN item 1] The bridge artifact output path convention
   (bridge_out/) is hard-coded in nodes.py:267 but the adapter
   (load_bridge_artifact) takes an explicit path parameter. The r2 carry-
   forward asked whether bridge_out/ suits the production adapter's expected
   input location. This is STILL unanswered in the plan. The plan says
   "forceInput for policy/bridge JSON sockets" (item 1, line 43-44) and
   "the adapter never scans a conventional folder" (item 1, line 44-45),
   which is good -- but there is no documented convention for HOW the
   bridge_out/ path gets threaded to the production writer's forceInput
   socket. Is it a workflow-level literal path? A relative path? An
   environment variable? This must be specified before the workflow JSON
   chunk (item 10) lands.
   FIX: Document the path-threading convention: lab emits to bridge_out/,
   production socket receives an absolute or lab-relative path, and the
   adapter resolves it. One sentence in PATCH_PLAN suffices.

4. [PATCH_PLAN item 2 / _otr_line_composer.py] compose_source_coda is
   declared as a new facade (item 2) with modes archive_source_note and
   source_attribution as "new composers." These composers consume
   profile.coda_system_prompt + profile.coda_examples. The coda_system seam
   is in TEMPLATE_SEAMS (contracts.py:31) and required_seams for all three
   runnable banks (banks.json lines 24-29, 55-65, 89-99). But the science
   bank's required_seams list includes "coda_system" -- meaning every
   science pack MUST carry a coda_system prompt_stage. Verify: the
   science_news_default pack (fixtures/story_packs/science_news/
   science_news_default.json) actually carries coda_system in prompt_stages.
   If it does, this value will be threaded into profile.coda_system_prompt,
   and the compose_news_coda path must ignore it (since science_news uses
   the existing compose_news_coda implementation, not the profile-driven
   one). This is a potential double-prompt injection: the profile carries a
   coda_system_prompt that compose_news_coda does not consume, but a future
   refactor might accidentally wire it in.
   verify: fixtures/story_packs/science_news/science_news_default.json
   prompt_stages keys and whether coda_system is present.

5. [nodes.py] _registry() creates a NEW Registry(LAB_ROOT) on every call.
   Registry.__init__ loads and validates all fixtures from disk (banks.json,
   pipelines.json, all story packs, all visual styles, all PD manifests, and
   runs cross-validation). This is called from INPUT_TYPES class methods
   (_bank_choices, _model_choices, _pipeline_choices, _style_choices) which
   ComfyUI invokes at node registration time AND potentially on every
   workflow validation. There is no caching -- the IS_CHANGED digest is
   computed but the registry itself is rebuilt every time.
   FIX: Cache the registry behind the state digest. The infrastructure for
   this exists (state_digest and _lab_state_digest); add a module-level
   _CACHED_REGISTRY / _CACHED_DIGEST pair and return the cached instance
   when the digest matches.

---

OPTIONAL / NICE-TO-HAVE

1. The bridge artifact schema_version is "v2.0" (contracts.py:17) and the
   adapter supports only ("v2.0",) (_otr_ledger_input_adapter.py:41). When
   v2.1 ships, the adapter must be updated in lockstep. Consider supporting
   "v2.*" or a version range now to avoid a hard coupling on minor bumps.

2. dramatic_state_labels() (transplant _otr_story_prompt_profile.py:97-106)
   computes premise_label as f"{profile['source_material_label'].upper()}
   PREMISE". This embeds formatting logic (uppercase + " PREMISE" suffix) in
   Python rather than in JSON. If future banks want a different premise label
   shape, this is a code change, not a config change. Low priority since v1
   banks all follow this pattern.

---

CUT THESE (over-engineering)

1. [contracts.py] Provenance.production_baseline field (line 415). It is
   always passed as "" in build_spec (bridge.py:69) and there is no code
   path that ever sets it to anything else. It occupies space in every
   bridge artifact for a hypothetical git-hash stamping that was explicitly
   rejected in r2 (rejected item 1, "git-hash provenance fails for
   uncommitted fixture edits mid-session"). Safe to cut -- it is dead data.
   If it is kept for forward-compatibility, that is fine, but it should be
   acknowledged as such.

2. [contracts.py] FetchRequest model (lines 470-477). It is defined but
   never referenced by any code outside of its own file. No test
   instantiates it, no function accepts or returns it. It exists for a
   future fetcher binding that does not exist yet. If it stays, it should
   have a comment marking it as forward-declared; otherwise it looks like
   dead code.
