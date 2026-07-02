VERDICT: yes-with-fixes. The scaffold is structurally sound and contract-complete for
the fixture layer. Four defects will bite the prompt-meat implementor at the keyboard:
an import-time side effect, a missing sentinel for empty system prompts, an unenforced
visual spec invariant, and a silent fallback that contradicts the fail-closed design.

---

MUST-FIX BEFORE BUILD

1. [catalogs.py:386] Module-level file I/O at import time.
   `VISUAL_STYLES.update(_load_visual_style_fixtures())` runs unconditionally when
   `upstream_story_lab.catalogs` is first imported. Because ComfyUI calls INPUT_TYPES
   at startup for every registered node, `_visual_style_choices()` in
   `nodes.py:78-81` triggers this import during the ComfyUI boot sequence, reading
   and parsing 5 JSON files before any user action. ComfyUI custom-node invariant #5
   prohibits side effects at import time; a missing or corrupt fixture file will
   crash the entire node pack at startup.
   Fix: replace the module-level `update()` call with a lazy-init guard:
     _VISUAL_STYLES_LOADED = False
     def _ensure_styles_loaded(): ...
   Call `_ensure_styles_loaded()` at the top of `get_visual_style_policy()` and
   `_visual_style_choices()`. Remove the top-level `update()` call.

2. [contracts.py:67-96, catalogs.py:233-317] `StoryPromptProfile` system-prompt fields
   default to `""` with no sentinel for "this stage does not apply to this source bank."
   The `science_news` profile (catalogs.py:234-250) leaves `pitch_room_system_prompt`,
   `story_select_system_prompt`, `style_picker_inventor_system_prompt`,
   `style_picker_chooser_system_prompt`, and `style_picker_chooser_user_template` as
   empty strings. The `public_domain_story` profile (catalogs.py:286-317) also omits
   the three style-picker fields. When the prompt-meat orchestrator iterates pipeline
   stages, an empty string is indistinguishable from a bug-produced blank — it could
   silently submit an empty system prompt to an LLM rather than skipping the stage.
   Fix: change those five fields in `StoryPromptProfile` to `Optional[str] = None`.
   Update `get_profile()` callsites to assign `None` where absent. Add a guard in any
   future orchestrator: `if profile.pitch_room_system_prompt is None: skip`.

3. [contracts.py:161-172] `LedgerWritingSpec` does not enforce consistency between
   `visual_style_id` (default `"sci_fi_radio"`) and `visual_policy` (default `None`).
   A consumer that reads `spec.visual_style_id` and a consumer that reads
   `spec.visual_policy` can observe contradictory values from the same object.
   `build_spec_from_material()` (preview.py:114-122) always sets both fields
   consistently, but the model allows a hand-constructed spec where they diverge.
   When the next implementor builds a production caller, this is the first footgun
   they will hit.
   Fix: add a Pydantic `@model_validator(mode="after")` that resolves `visual_policy`
   from `visual_style_id` via `get_visual_style_policy()` when `visual_policy is None`.
   Alternatively, remove `Optional` from `visual_policy` and require callers to supply
   it explicitly.

4. [nodes.py:111-118, 328-339] `_find_source_packet()` returns `None` for unrecognized
   source bank IDs, and the `preview()` method at line 339 silently falls back to
   `"\n".join(pack.prompt_stages.values())` as the preview text. This contradicts the
   fail-closed design stated in the module docstring and the explicit `custom_source_bank`
   guard. If a new `source_bank_id` is added to `SOURCE_BANK_CHOICES` without a
   corresponding entry in `_find_source_packet()`, the node will appear to work while
   silently producing prompt-stage text instead of a real spec.
   Fix: replace `return None` at nodes.py:118 with:
     raise RuntimeError(f"No source packet registered for source_bank_id={source_bank_id!r}")

---

SHOULD-FIX

5. [nodes.py:245-263, 104-108, 285] `INPUT_TYPES` calls `_story_pack_choice_map()` three
   independent times (once for `pack_choices`, once inside `_default_story_pack_choice()`,
   and once inside `_story_model_choices()` via `_story_pack_paths()`). `preview()` adds
   a fourth call at line 285. Each call scans the fixture directory and parses all 12
   JSON pack files. ComfyUI calls `INPUT_TYPES` on every prompt queue and UI refresh, so
   this is 48+ JSON parses per user action with the current pack count.
   Fix: extract a module-level `_PACK_MAP_CACHE: dict[str, Path] | None = None` and a
   `_get_pack_map()` getter that populates it once. IS_CHANGED already invalidates the
   node on fixture changes, so a process-lifetime cache is safe.

6. [preview.py:108] `build_spec_from_material()` defaults `visual_style_id="sci_fi_radio"`.
   For `media_archive` and `public_domain_story` sources, this default attaches sci-fi
   radio visuals to archive/adaptation stories — the exact mismatch the
   `archival_documentary` forbidden-terms list is designed to prevent. The validate
   script always passes `visual_style_id` explicitly, so this default never fires in
   tests, hiding the footgun.
   Fix: change the default to `"auto"` and add a per-source-bank default lookup
   parallel to `resolve_story_model_id()`:
     VISUAL_STYLE_DEFAULT_BY_SOURCE = {"media_archive": "archival_documentary",
                                        "science_news": "sci_fi_radio",
                                        "public_domain_story": "archival_documentary"}

7. [nodes.py:55-66] `_story_pack_choice_map()` accesses `data['source_bank_id']` and
   `data['story_model_id']` directly on the raw dict without going through `StoryPack`
   validation. A pack JSON missing either key raises an unguarded `KeyError` with no
   indication of which file is bad. All other loading paths (validate_lab.py,
   _validate_story_packs) use `StoryPack(**data)` and get a clean Pydantic error.
   Fix: call `pack = StoryPack(**data)` first; use `pack.source_bank_id`,
   `pack.story_model_id`, `pack.story_pipeline_id` to build the key.

---

OPTIONAL / NICE-TO-HAVE

- [validate_lab.py:74-78] The VISUAL_STYLES catalog assertion is logically correct but
  its invariant is non-obvious: it catches hardcoded-only styles (no fixture file) but
  NOT fixture-only styles (already in VISUAL_STYLES by the time the check runs). A
  comment explaining the direction of the check would prevent future confusion.

- [contracts.py:54-65] `StoryModelSpec.outline_rules_extra: str = ""` and the optional
  system prompt fields follow the same empty-string-as-absence pattern throughout.
  A shared `Optional[str] = None` convention across the contract layer would make the
  "no content specified" signal uniform before the prompt-meat layer is written.

---

CUT THESE (over-engineering)

None identified. The deferred items from R1 (compatibility matrix, simple_4_prompt
portability, widget consolidation) are correctly out of scope. The current fixture
layer is minimal and the right amount of structure for the next coding step.

---

ASSUMPTIONS

[ASSUMPTION] ComfyUI calls INPUT_TYPES for all node classes during startup (to build
the frontend schema). This is the standard ComfyUI boot behavior but not confirmed
against the specific ComfyUI version in use. Verify: check ComfyUI server startup logs
for "Loading: OTR_StoryPackPreview" followed by any file-read errors.

[ASSUMPTION] The prompt-meat orchestrator will consume `StoryPromptProfile` fields
by name (e.g., `profile.pitch_room_system_prompt`), not by iterating `prompt_stages`
from the pack. If it only uses `StoryPack.prompt_stages`, finding 2 above is lower
severity. Verify: check the production OTR pipeline entry point for how it reads
prompt content.

[ASSUMPTION] `_load_visual_style_fixtures()` at catalogs.py:375 uses
`Path(__file__).resolve().parents[2] / "fixtures" / "visual_styles"`. With
`__file__` at `src/upstream_story_lab/catalogs.py`, parents[2] resolves to the
project root. Verified against the actual directory layout.
