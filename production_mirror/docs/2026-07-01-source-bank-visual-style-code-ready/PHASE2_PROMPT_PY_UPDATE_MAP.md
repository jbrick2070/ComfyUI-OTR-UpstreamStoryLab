# Phase 2 Prompt/Python Update Map

Status: focused handoff for the content/prompt-meat phase.

Grounded in:

- `STORY_AND_VISUAL_SCI_FI_REMNANTS_ARTIFACT.html`
- `LEDGER_PROMPT_AUDIT.md`
- `VISUAL_PROMPT_AUDIT.md`
- live prompt/Python sites under `nodes/`
- Codex-only R1-R4 notes in
  `kibitz-runs/2026-07-01-source-bank-prompt-meat-v2/`

Do not edit `workflows/otr_scifi_16gb_full.json` for this phase.

## Core Decision

First transplant keeps the current broad many-pass story architecture.

The work is not to invent a mega-template. The work is to create cloneable
story/source packs that replace sci-fi/news prompt meat and Python routing where
the current code assumes science fiction.

The ledger stays fixed. The upstream source/story logic becomes swappable.

Treat the source lanes as separate models/pipelines from the start:

- science RSS/news model
- media RSS/archive model
- public-domain adaptation model
- simple 4-prompt experimental model
- custom source-bank model

For the first build, clone the current many-pass scaffolding where useful, then
edit the cloned prompt meat and source-specific Python routing. Do not build one
shared mega-model with conditionals for every source. Later, one model/pipeline
can change its LLM scaffolding without risking the others.

Rules:

- Expose planned lanes.
- No hidden fallbacks.
- No unpromoted dormant behavior.
- If a visible lane cannot run, fail loudly with `source_bank`,
  `story_model`, and `story_pipeline`.
- If a lane does not pan out, remove it rather than hiding it.

## First New Story Pack Shape

Each pack should be a concrete content artifact, not scattered strings:

```text
story_packs/<source_bank>/<story_model>.json
```

Minimum fields:

```text
source_bank_id
story_model_id
story_pipeline_id
label
story_form_label
source_material_label
source_develop_verb
source_grounding_label
outline_system_prompt
outline_user_rules
pitch_room_system_prompt
pitch_seed_strategy
story_select_system_prompt
dramatic_state_system_prompt
line_grounding_instruction
coda_mode
coda_system_prompt
coda_examples
title_system_prompt
style_picker_inventor_system_prompt
style_picker_chooser_system_prompt
tone_guardrails
forbidden_plot_patterns
forbidden_leakage_terms
ledger_validation_notes
```

Python selects a pack, validates it, and routes its stage prompts into the
existing ledger-writing stages.

## Source Banks

### `science_news`

Purpose: preserve current science/news sci-fi behavior.

Prompt treatment:

- Move existing science/sci-fi wording into `science_news_default`.
- Keep phrases like `science-fiction audio drama`, `science story`, and
  `news facts` only in this pack.
- Keep current RSS fetch path only here.

Python treatment:

- `OTR_LedgerScriptWriter._resolve_inputs()` may call
  `_fetch_rss_seed_or_die()` only when `source_bank == "science_news"`.
- `nodes/news_interpreter.py` can remain the science source brain.
- Existing `meta.news` shape remains valid.
- Later experiments to science RSS scaffolding should happen inside the
  science model/pipeline only, not through shared media/public-domain code.

### `media_archive`

Purpose: RSS/feed/archive/media-history stories that fill the same ledger
without sci-fi anthology drift.

Prompt treatment:

- Replace science/news language with archive/media source language.
- Story form: `archive-inspired radio drama`.
- Source label: `media archive item` or `media RSS item`.
- Grounding label: `archive material`.
- Coda mode: `archive_source_note`.

Python treatment:

- Add a source brain separate from science RSS.
- Suggested modules:
  - `nodes/_otr_source_packets.py`
  - `nodes/_otr_source_brains.py`
  - `nodes/_otr_media_archive_sources.py`
- Media archive must never call `_fetch_rss_seed_or_die()`.
- Empty/missing archive source should raise, not fetch science news.
- Media RSS/archive is its own model/pipeline. It may initially clone the
  science many-pass shape, but later prompt-count or scaffold experiments stay
  local to this lane.
- Archive feed normalization should produce:
  - title
  - source/publisher
  - URL
  - date
  - summary/body
  - rights/provenance when available
  - source hash

### `public_domain_story`

Purpose: books, comics, plays, poems, short stories, serial chapters, and other
public-domain sources.

Prompt treatment:

- Story form: `public-domain radio adaptation`.
- Source label: `public-domain source text`.
- Grounding label: `source text`.
- Coda mode: `source_attribution`.
- Prompts must preserve named characters, major turns, ending, and attribution.

Python treatment:

- Add a manifest/folder loader, not a fallback.
- Suggested folder:

```text
upstream_story_lab/fixtures/public_domain_sources/<source_id>/
  manifest.json
  source.txt
```

- Comic sources may include page text/image references.
- Validate `rights_status == "public_domain"` unless an explicit licensed mode
  is later implemented.
- Missing source text, unknown rights, or invalid manifest raises loudly.

### `custom_source_bank`

Purpose: exposed guided extension lane.

Prompt treatment:

- No default generic story prompts.
- User must provide a valid schema/prompt pack.

Python treatment:

- Selecting it without a valid schema raises with a pointer to
  `CUSTOM_SOURCE_BANK_GUIDE.md`.

## Story Models

### `science_news_default`

Prompt changes:

- Preserve current prompts as the science pack:
  - `nodes/_otr_outline.py`: science-fiction outline wording.
  - `nodes/_otr_pitch_room.py`: sci-fi pitch wording.
  - `nodes/_otr_story_select.py`: sci-fi grading wording.
  - `nodes/_otr_dramatic_state_llm.py`: news-event conflict wording.
  - `nodes/_otr_line_composer.py`: news facts and real-news coda.
  - `nodes/OTR_LedgerScriptWriter.py`: sci-fi title prompt.
  - `nodes/_otr_style_picker.py`: sci-fi radio drama descriptor picker.

Python changes:

- Use this as the compatibility baseline.
- Tests should prove science/default prompt previews are unchanged or
  intentionally equivalent.

Forbidden leakage:

- None; this is the only lane where science/news/sci-fi words are allowed.

### `media_restoration_adventure`

Prompt changes:

- Outline: “Plan an archive-restoration radio adventure about recovering,
  preserving, or interpreting fragile media.”
- Pitch room: create three restoration/adventure pitches with different
  protagonists, archive objects, and institutional pressures.
- Dramatic state: wants are rooted in the archive object, provenance, access,
  deadline, or public meaning.
- Line grounding: ground lines in archive material and scene premise.
- Coda: close with an archive/source note, not a news report.
- Title: title an archive-inspired radio episode from physical details in the
  story.

Python changes:

- Route source through media archive source brain.
- Use archive pack prompts in `_otr_outline`, `_otr_pitch_room`,
  `_otr_story_select`, `_otr_dramatic_state_llm`, `_otr_line_composer`,
  `_otr_style_picker`, and title regeneration.

Forbidden leakage:

- `science-fiction audio drama`
- `real science`
- `news facts`
- `spaceship`
- `mission control`
- `laboratory containment`

### `cinematic_humorous`

Prompt changes:

- Outline: polished comic media-culture story, non-violent conflict.
- Pitch room: build humor from production mishap, archival misunderstanding,
  fandom, bureaucracy, restoration surprise, or scholarly ego.
- Dramatic state: wants are social/logistical/interpersonal, not disaster
  stakes.
- Coda: affectionate media-history note.

Python changes:

- Same archive source brain.
- Pack supplies comedy-specific pitch seed strategy and grading rubric.
- Story selector grades comic timing, human stakes, and source relevance.

Forbidden leakage:

- doomsday device
- alien signal
- mission plot
- lab alarm

### `happy_archive_mystery`

Prompt changes:

- Outline: puzzle/memory/discovery mystery with upbeat resolution.
- Pitch room: each pitch centers a missing label, misfiled reel, disputed
  credit, forgotten performer, or recovered broadcast.
- Dramatic state: suspense comes from incomplete context, not danger.
- Coda: source note celebrates preservation or rediscovery.

Python changes:

- Pack should add `mystery_without_menace` guardrail.
- Story selector should reject horror/conspiracy/violent mystery drift.

Forbidden leakage:

- violent conspiracy
- horror haunting
- corpse/body-count plot
- generic supernatural twist

### `gentle_thriller`

Prompt changes:

- Outline: non-violent suspense from time pressure, damaged evidence, public
  reveal, funding deadline, or fragile media.
- Pitch room: high urgency, low harm.
- Dramatic state: competing wants are about access, truth, credit, care, or
  disclosure.
- Coda: archive source note after tension resolves.

Python changes:

- Pack needs stricter forbidden-pattern list because “thriller” can drift.
- Story selector grades “suspense without violence.”

Forbidden leakage:

- armed chase
- body count
- monster reveal
- explosive countdown

### `broadcast_history_comedy`

Prompt changes:

- Outline: comedy about broadcast history, production lore, reception, fans,
  scholarship, or station culture.
- Pitch room: use production mishaps and media-history specificity.
- Dramatic state: conflict is reputational, interpretive, or logistical.
- Coda: broadcast-history note, not news.

Python changes:

- Pack should include broadcast-specific key term labels.
- Keep radio-drama craft, but do not force sci-fi radio anthology premises.

Forbidden leakage:

- space fleet
- interdimensional portal
- futuristic console

### `faithful_radio_adaptation`

Prompt changes:

- Outline: adapt source while preserving characters, major turns, ending.
- Pitch room may be bypassed or constrained; do not invent a brand-new premise.
- Dramatic state must come from source text.
- Coda: attribution/adaptation note.

Python changes:

- Public-domain source loader must pass source text and manifest metadata.
- `adaptation_trace` records source files, compression choices, and preserved
  turns.
- Selector grades fidelity before novelty.

Forbidden leakage:

- invented protagonist
- changed ending
- unrelated news/source framing

### `chapter_digest_drama`

Prompt changes:

- Compress a chapter into a radio episode.
- Preserve chapter arc and ending; combine minor incidents only when needed.
- Coda names source/chapter.

Python changes:

- Manifest loader must support chapter/section ids.
- Ledger meta should store source chapter reference.

Forbidden leakage:

- whole-book claims when only a chapter is provided
- invented ending

### `comic_panel_radio_adaptation`

Prompt changes:

- Convert panel-by-panel action into audio beats.
- Translate visual gags into sound, dialogue, announcer framing, or action.
- Preserve page/order and named characters.

Python changes:

- Manifest supports `pages/*.txt` and optional image refs.
- `adaptation_trace` stores page ids and panel refs.
- Prompt pack includes “panel-to-sound” rules.

Forbidden leakage:

- describing panels as on-screen text
- ignoring page order
- inventing characters to replace source characters

### `stage_play_radio_adaptation`

Prompt changes:

- Convert scenes/acts into radio form.
- Preserve dialogue intent, character relations, and scene turns.
- Use narrator/announcer only where needed for audibility.

Python changes:

- Loader supports scene/act metadata.
- Pack may map source speakers to ledger cast.

Forbidden leakage:

- changing character names
- replacing play setting without selected adaptation mode

### `storybook_puppet_show`

Prompt changes:

- Gentle playful adaptation of public-domain material.
- Family-friendly, whimsical, clear character voices.
- Preserve source ending unless excerpted.

Python changes:

- Pack adds tone guardrails and no-violence/no-cruelty filters.
- Visual style can later pair with cartoon/origami, but story model remains
  source/fidelity driven.

Forbidden leakage:

- cynical parody
- horror turn
- changed moral/ending

## Experimental Story Pipeline

### `simple_4_prompt_experimental`

Expose as a story pipeline option, not a hidden fallback.

Passes:

1. Creative story pass.
   - Writes a complete story from the selected source/story pack.
   - Must obey source constraints and tone guardrails.

2. Creative ledger fill pass.
   - Uses the story to fill the production ledger shape.
   - Must include cast, lines, beats, meta/source, and visual directives.

3. Technical schema cleanup pass.
   - Repairs JSON/schema issues.
   - Enforces required fields, ids, enum values, and basic shape.

4. Technical ledger consistency audit.
   - Checks cast vs line speakers.
   - Checks character ids and speaker roles.
   - Checks beat ids, line ids, order, duration/word constraints.
   - Checks source metadata and coda/source note.
   - Checks visual directives and downstream required meta.

Python role:

- Validate, repair, and fail loudly.
- Do not inject hidden story workarounds.
- Do not fall back to `legacy_many_pass` if the experiment fails.

Expected result:

- It may fail at first. That is useful data.
- If stronger models can satisfy the ledger in four passes, this becomes the
  clean path for future story architecture experiments.

Optional extension:

### `adaptive_technical_cleanup_experimental`

This is the "keep cleaning until the ledger is actually clean" experiment.

Shape:

1. Run the simple story/ledger passes.
2. Run deterministic ledger validators.
3. Ask the technical model whether another cleanup pass is needed.
4. The model may propose:
   - cleanup target, such as cast ids, line ids, beat continuity, source fields,
     visual directives, or schema repair
   - an approved local technical model from the configured model registry
   - a short cleanup prompt for the next pass
5. Python checks the proposal against an allowlist.
6. Continue only while validators still fail and the loop is under the hard cap.

Hard rules:

- Never loop only because the model "feels" uncertain.
- Stop when deterministic validators pass.
- Stop and fail loudly when `max_cleanup_passes` or token/runtime budget is hit.
- No arbitrary model selection; choose only from approved local technical models.
- No fallback to science RSS, legacy builder, or hidden compatibility path.

Suggested cap:

```text
max_cleanup_passes = 4
```

The model can recommend cleanup; Python owns the stop condition.

## Python Prompt Sites To Update

### `nodes/OTR_LedgerScriptWriter.py`

Current sci-fi/news remnants:

- `_fetch_rss_seed_or_die()` is science RSS.
- `_resolve_inputs()` falls to RSS when `custom_premise` is empty.
- title prompt says `sci-fi radio drama`.
- style picker sees article/news seed.
- coda routing calls `compose_news_coda()`.

Required update:

- Add source/story/pipeline resolution before source fetch.
- Only `science_news` can call `_fetch_rss_seed_or_die()`.
- Add `source_bank`, `story_model`, `story_pipeline`, and `visual_style` later
  as append-only widgets.
- Route selected story pack to:
  - source brain
  - source interpreter
  - outline
  - pitch room
  - story selector
  - dramatic state
  - line composer
  - coda
  - title
  - style/story descriptor picker
- Stamp `meta.source_bank`, `meta.story_model`, `meta.story_pipeline`,
  `meta.visual_style`.
- Keep `meta.news` only as a compatibility mirror, never as conceptual meaning.

### `nodes/news_interpreter.py`

Current sci-fi/news remnants:

- User prompt says `news article`.
- Field label says `news_close_brief`.
- Closing note says `closing news read`.

Required update:

- Either keep this file science-only and call it only for `science_news`, or
  wrap it behind a new `source_interpreter` facade.
- For media/public-domain, use separate prompts and output the same logical
  fields: `casting_brief`, `script_brief`, `close_brief`, `key_terms`.

### `nodes/_otr_outline.py`

Current remnants:

- System prompt says science-fiction audio drama grounded in real science.
- User prompt says `Science story`.
- Macro/phase/beat prompts say science-fiction audio drama.

Required update:

- `OutlineRequest` gets pack fields or a packed prompt profile.
- System prompts come from pack.
- Source line uses `source_material_label`.
- Develop verb uses `source_develop_verb`.
- Outline rules append pack guardrails and forbidden patterns without planting
  forbidden image/story terms in places the LLM may copy.

### `nodes/_otr_pitch_room.py`

Current remnants:

- System says short science-fiction audio drama.
- Source material is generic; pitch seeds are current story-engine shaped.

Required update:

- System prompt from pack.
- Pitch seed strategy from pack.
- Archive models get restoration/comedy/mystery/thriller/broadcast seed pools.
- Public-domain faithful modes should constrain or bypass divergent invention.

### `nodes/_otr_story_select.py`

Current remnants:

- Grader says short science-fiction audio drama.

Required update:

- Grader system prompt from pack.
- Media archive rubric: source relevance, human stakes, non-violent archive
  craft.
- Public-domain rubric: fidelity first, compression allowed only when declared.
- Simple 4-prompt pipeline uses a stronger ledger-level technical grader.

### `nodes/_otr_dramatic_state_llm.py`

Current remnants:

- Prompt says premise comes from a real news item.
- Labels `NEWS KEY TERMS` and `NEWS PREMISE`.
- Ending/change references the news.

Required update:

- Labels from pack:
  - `ARCHIVE KEY TERMS`
  - `ARCHIVE PREMISE`
  - `SOURCE KEY TERMS`
  - `SOURCE PREMISE`
- Wants line says rooted in active source material.
- Ending change references the source/story model, not news.

### `nodes/_otr_line_composer.py`

Current remnants:

- Fallback grounding says `news facts`.
- Dynamic coda is `compose_news_coda()`.
- Coda system says `real news report`.

Required update:

- Line grounding instruction from pack.
- Add `compose_source_coda()` facade:
  - `real_news_report`
  - `archive_source_note`
  - `source_attribution`
  - `none`
- Keep `compose_news_coda()` as science/default implementation.
- Coda examples from pack.
- `news_close_brief` may stay as compatibility field but should be populated
  from source-neutral `close_brief`.

### `nodes/_otr_style_picker.py`

Current remnants:

- Inventor says sci-fi radio drama showrunner.
- Chooser says adapting article into a sci-fi radio drama.
- Chooser fallback returns first candidate.

Required update:

- Accept prompt overrides:
  - `inventor_system_prompt`
  - `inventor_user_template`
  - `chooser_system_prompt`
  - `chooser_user_template`
- For non-science lanes, do not use sci-fi defaults.
- Decide whether chooser fallback is allowed only for science/default. For new
  lanes, prefer loud failure over hidden first-candidate fallback.

### `nodes/_otr_casting.py`

Current remnants:

- Mostly reusable radio casting craft.
- Some names such as `news_seed` are compatibility baggage.

Required update:

- Feed active `casting_brief`.
- Public-domain packs should support source character preservation.
- Media archive packs can invent characters from archive context.

### `nodes/_otr_story_quality_l12.py` and `nodes/_otr_story_spine.py`

Current remnants:

- Read `meta.news` fields.

Required update:

- Add source-neutral accessor.
- Keep `meta.news` mirror until consumers migrate.
- Tests must prove archive/public-domain values do not require science/news
  semantics.

## Visual Prompt Sites To Update

Visual transplant can be staged after source/story packs, but the prompt map is:

### `nodes/_otr_story_brief_helpers.py`

Current remnants:

- `ERA_TAIL_DEFAULT = timeless cinematic aesthetic`
- `STYLE_TAIL_DEFAULT = cinematic, 35mm film look...`
- `IMAGE_GRADE_TAIL`
- `RADIO_BROADCAST_TAIL`
- open subjects use vintage radio set/studio/tubes/dials
- `finish_visual_prompt()` appends cinematic tails.

Required update:

- Add visual policy catalog.
- `finish_visual_prompt()` reads `meta.visual_style`.
- `compose_still_prompt()` uses policy subjects/tails.
- `sci_fi_radio` preserves current behavior.

### `nodes/otr_meta_brief_image_prompt.py`

Current remnants:

- `STYLE_ANCHOR` and wide anchor say cinematic/dramatic film lighting.
- announcer anchor says chrome microphone, broadcast studio, ON AIR.
- char-scene prompt says cinematic still.
- direct `IMAGE_GRADE_TAIL` appends after finisher.
- mesh fodder uses vintage radio announcer/tabletop radio.

Required update:

- Split role safety from visual style.
- Character face/headroom constraints remain.
- Style language comes from `VisualStylePolicy`.
- Direct image-grade tail appends move behind policy.
- Announcer/music subjects come from policy.

### `nodes/otr_shot_lock.py`

Current remnants:

- fallback setting is `a vintage radio studio`.
- batch prompt says film director and blocks film-stock terms because finisher
  appends them.
- final finisher always uses current cinematic tail.

Required update:

- Fallback setting from source/story/visual policy.
- Batch role label may stay “director” but style assumptions must be policy.
- Stamp/read `meta.visual_style` before prompt finishing.

### `nodes/_otr_video_engines/render_driver.py`

Current remnants:

- LTX motion prompts assume radio console/dial/tubes/speaker.
- character face fallback says cinematic portrait/1940s costume/dramatic film.
- text fallback uses cinematic establishing shot and slow cinematic drift.
- lipsync base prompt uses 1940s radio actor/studio microphone.

Required update:

- Stage as V3 after shared visual policy works.
- Policy supplies role motion prompts:
  - announcer
  - music_open
  - music_close
  - music_inter
  - sfx
  - lipsync base
- Keep face-centered functional requirements for lipsync, but style words vary.

## Visual Style Packs

### `sci_fi_radio`

- Preserve current radio/cinematic look.
- Allows radio tails, 35mm, film grain, broadcast distress.

### `archival_documentary`

- Archive-documentary stills, restoration texture, paper/film material.
- No futuristic console/lab/spaceship drift.
- Announcer/music subjects can be archive table, film reel, tape machine, card
  catalog, screening room, or restoration bench.

### `cinematic_35mm`

- Allows cinematic/35mm/film grain.
- Does not require radio studio objects.

### `noir`

- High-contrast noir, practical shadows, restrained palette.
- Avoid generic sci-fi consoles unless source/story calls for them.

### `anime`

- Anime/cel-shaded linework.
- Forbid photorealistic, 35mm, film grain unless explicitly allowed.

### `cartoon`

- Bright expressive cartoon shapes.
- Forbid photorealistic/35mm/film-grain defaults.

### `paper_origami`

- Folded-paper diorama, papercraft texture, handmade edges.
- Forbid photorealistic/cinematic 35mm/film grain defaults.

## Tests

Add focused tests before transplant:

- `tests/test_source_story_pack_catalog.py`
  - every exposed source/model pair resolves or intentionally raises a named
    not-implemented error
  - invalid pairs fail loudly

- `tests/test_story_prompt_leakage.py`
  - media archive prompts contain no science/sci-fi/news leakage
  - public-domain prompts contain no science/news fallback language
  - science default still allows science/news language

- `tests/test_source_resolver_no_fallback.py`
  - `media_archive` never calls `_fetch_rss_seed_or_die`
  - `public_domain_story` never calls science RSS
  - `custom_source_bank` without schema raises loudly

- `tests/test_public_domain_source_loader.py`
  - manifest required fields
  - rights status validation
  - source text exists
  - comic page refs validate

- `tests/test_simple_4_prompt_pipeline.py`
  - fake LLM can produce story -> ledger -> repair -> final audit
  - bad cast/line ids are caught in pass 4
  - no fallback to legacy builder

- `tests/test_visual_style_leakage.py`
  - anime/cartoon/origami do not emit 35mm/film grain/radio studio tails
  - sci_fi_radio preserves current tails

Transplant tests later:

- append-only widget check
- workflow validator
- JSON round-trip
- link audit
- widget/input audit
- API/workflow creative whitelist parity

## Build Order

1. Extend lab contracts for story packs and `simple_4_prompt_experimental`.
2. Add fixture story packs for all listed source/story models.
3. Add public-domain fixture source folders.
4. Add prompt preview renderer per pack and leakage tests.
5. Add source resolver/no-fallback tests.
6. Add production pure modules, still not wired into workflow.
7. Parameterize prompt sites.
8. Add writer resolver controls and runtime routing.
9. Update whitelists.
10. Only then append workflow widgets and validate the canonical JSON.
