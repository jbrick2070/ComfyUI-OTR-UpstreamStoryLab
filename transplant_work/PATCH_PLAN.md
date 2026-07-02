# Transplant Patch Plan (module-level; hunks generated at transplant time)

Scope rule (kibitz r1/r2): NO line-cited hunks here - production HEAD moves
nightly; exact diffs are generated against live HEAD in the transplant chunk.
This plan names each file's changes at module level, its new-module partners,
and the tests that gate it. Nothing in this folder is installed anywhere.

New modules ready to drop into `ComfyUI-OldTimeRadio/nodes/` (staged in
`transplant_work/production_new_modules/`, each with lab-side pure tests):

- `_otr_ledger_input_adapter.py` - validates a bridge artifact; production
  passes the real NewsBriefs class for full validation.
- `_otr_story_prompt_profile.py` - profile -> OutlineRequest fields,
  style-picker override kwargs, coda_mode routing, dramatic-state labels.
- `_otr_visual_style_policy.py` - policy validation, meta.visual_style
  stamp/read (refuses conflicting restamp), tail overrides, motion prompt
  accessor (dead roles rejected).
- `_otr_source_interpreter.py` - facade: science requires
  news_briefs_builder (build_news_briefs wired verbatim); archive/PD are
  packet-driven v1 (bridge story_input); custom raises with guide pointer.

## Production edit map (module-level)

1. `nodes/OTR_LedgerScriptWriter.py`
   - `_resolve_inputs()`: add source_bank/story_model/story_pipeline/
     visual_style resolution BEFORE source fetch; RSS branch
     (`_fetch_rss_seed_or_die`) reachable ONLY when
     `source_bank == "science_news"`; packet-driven lanes enter through the
     existing custom-premise-shaped article dict (`adapter_news_article`,
     seed_source="bridge_packet").
   - PRECEDENCE (kibitz r2, Codex M5): existing `style`/`style_custom`
     widgets remain the TONAL preset lane for science_news only; non-science
     banks ignore the style slug (story_model owns tone) - add a test proving
     a non-science run never reads the style slug for content.
   - Title prompt: `title_form_label` from profile (science default
     preserves current text).
   - Coda routing: call `compose_source_coda` facade keyed by
     `coda_mode(profile)`; science mode delegates to `compose_news_coda`
     unchanged.
   - Stamp `meta.source_bank`, `meta.story_model`, `meta.story_pipeline`,
     `meta.visual_style` (+ provenance block from the bridge artifact).
   - New widgets appended ONLY at the end of INPUT_TYPES; forceInput for
     policy/bridge JSON sockets.
2. `nodes/_otr_line_composer.py`
   - Add `compose_source_coda(*, coda_mode, ...)` facade returning
     `LineResult`; `compose_news_coda` stays the real_news_report
     implementation; archive_source_note / source_attribution composers are
     new, fed by profile coda_system_prompt + coda_examples; mode "none"
     skips the coda pass explicitly (recorded, not silent).
   - Line grounding: instruction from `line_grounding_instruction(profile)`;
     science default byte-identical.
3. `nodes/_otr_style_picker.py`
   - `pick_style()` gains the locked kwargs (inventor_system_prompt,
     chooser_system_prompt, chooser_user_template; empty = current
     constants).
   - FALLBACK_INVENTORY decisions: candidate PADDING + first-candidate
     chooser fallback stay GRANDFATHERED for science_news (operator
     directive 2026-06-18); for non-science lanes both fail loud in v1.
4. `nodes/news_interpreter.py` - unchanged; science-only confinement happens
   at the writer/facade layer. (No edits = no risk.)
5. `nodes/_otr_outline.py` - `OutlineRequest` gains keyword-defaulted fields
   from `outline_request_fields(profile)`; system prompt override path per
   locked r4 (empty -> resolve_creative_system_prompt unchanged).
6. `nodes/_otr_pitch_room.py` / `_otr_story_select.py` /
   `_otr_dramatic_state_llm.py` - system prompts + labels from profile;
   science defaults preserved byte-identically (baseline pin test).
7. `nodes/_otr_story_brief_helpers.py` - `finish_visual_prompt` /
   `compose_still_prompt` consult `_otr_visual_style_policy.tail_overrides`
   + `allow_radio_tails` when `meta.visual_style` is stamped; unstamped
   ledgers keep current constants (byte-identical default).
8. `nodes/otr_meta_brief_image_prompt.py` / `otr_shot_lock.py` /
   `_otr_video_engines/render_driver.py` - VISUAL STAGE (separate, staged,
   after 7 proves byte-identical defaults; deep render_driver prompts one at
   a time with leakage tests).
9. Whitelists: `scripts/otr_api.py` + `nodes/_otr_workflow_apply.py` gain the
   four new creative keys when the widgets land (same chunk as widgets).
10. `workflows/otr_scifi_16gb_full.json` - LAST: append-only widgets +
    forceInput sockets; validator + round-trip + link audit + widget audit
    green first (gates in docs/FABLE_FINAL_REVIEW_2026-07-02.md).

## FALLBACK_INVENTORY (kibitz r2 complete list)

| Site | Current behavior | science_news v1 | non-science v1 |
|---|---|---|---|
| style picker inventor padding (_otr_style_picker) | pad to 5 stock descriptors | keep (grandfathered) | fail loud |
| style picker chooser first-candidate (_otr_style_picker) | fallback to candidates[0] | keep (grandfathered) | fail loud |
| RSS slug substitution -> mission_control_procedural (writer) | substitute default slug | keep (science-only path) | unreachable (RSS gated) |
| title regen -> outline.title (writer) | deterministic floor | keep | keep (content-neutral floor; uses source-grounded outline) |
| announcer outro resolved fallback (_otr_line_composer) | deterministic outro | keep | keep for v1 (fed by profile close_brief, not news prose) - revisit after first archive render |
| news briefs degrade meta.news=None (writer) | degrade + warn | keep | n/a (bridge always supplies briefs; adapter requires them) |

Every row gets a test at transplant time proving the non-science decision.
