# Ledger-Filling Prompt Audit

Status: live artifact for kibitz/code planning.

Goal: show which material prompts help craft the production ledger, which parts
are source-specific sci-fi/science-news wording, and which parts are reusable
radio-drama craft.

Legend:

- `PROFILE`: move behind source-bank prompt profile.
- `SHARED`: good radio-drama / ledger craft; can stay common.
- `COMPAT`: legacy naming such as `meta.news`; may stay as compatibility while
  values come from the active source packet.
- `DEAD/TEST`: do not change unless the path is active.

## Known Material Prompt Sites

| File | Lines | Ledger role | Classification | Notes / variable target |
|---|---:|---|---|---|
| `nodes/news_interpreter.py` | 704-723 | Source article -> `casting_brief`, `script_brief`, `news_close_brief`, `key_terms` | PROFILE + COMPAT | "news article" and `news_close_brief` are source-specific. Keep output shape or compatibility mirror, but make the source interpreter prompt bank-aware. |
| `nodes/_otr_outline.py` | 538-565 | Legacy outline system prompt | PROFILE | Hardcoded "short science-fiction audio dramas grounded in real science" and "science story". Needs source profile fields. |
| `nodes/_otr_outline.py` | 568-588 | Legacy outline user prompt | PROFILE | Hardcoded "Science story (the factual seed)", "extrapolates from the science story", and "science-fiction audio drama outline". |
| `nodes/_otr_outline.py` | 1109-1145 | Multi-stage macro/phase/beat system prompts | PROFILE | Active prompts say "science-fiction audio drama". Keep schema/rules, swap source/story form wording. |
| `nodes/_otr_outline.py` | 1148-1165 | Macro user prompt source label | PROFILE | Hardcoded "Science story" and "extrapolate dramatically from this story". Source label and develop verb become profile fields. |
| `nodes/_otr_pitch_room.py` | 181-193 | Divergent pitch generation | PROFILE or bank-specific replacement | "short science-fiction audio drama" is source-specific. The "different protagonists/conflicts/emotional cores" craft is SHARED. |
| `nodes/_otr_pitch_room.py` | 199-215 | Pitch candidate requirements | SHARED | Good story craft: stageability, human want, final 20 seconds. Keep unless source profile wants a different pitch pack. |
| `nodes/_otr_story_select.py` | 144-178 | Story/refine grading | PROFILE + SHARED | "science-fiction audio drama" is source-specific. Structure grading, rising stakes, grounding, wants are reusable. |
| `nodes/_otr_dramatic_state_llm.py` | 401-445 | Dramatic state / central conflict | PROFILE + SHARED | "real news item", `NEWS KEY TERMS`, `NEWS PREMISE`, "rooted in the news event" must become source labels. Opposed/distinct wants and dramatic question are reusable. |
| `nodes/_otr_line_composer.py` | 1178, 1261+ | Per-beat line composer | SHARED with source-label edits | "radio drama" is reusable. Any "news facts" grounding text must become source-facts/source-material grounding. |
| `nodes/_otr_line_composer.py` | 1642-1643 | Per-line grounding instruction | PROFILE | "Ground this line in the news facts..." becomes profile text, e.g. source facts/archive material/source text. |
| `nodes/_otr_line_composer.py` | 2915-2974 | Announcer intro/outro systems | Mostly SHARED | "old-time radio drama", period host, no spoilers, physical final image are reusable. `news_close_brief` input name/meaning is COMPAT and should become close/source note in profile. |
| `nodes/_otr_line_composer.py` | 3294-3311 | News coda bridge | PROFILE | "turns from tonight's fictional tale to the real world" and "real news report" are science/news-specific. Media archive and public-domain need their own coda/source-note modes. |
| `nodes/_otr_line_composer.py` | 3316-3319 | News coda examples | PROFILE | Examples are useful but source-bank-specific examples should replace or extend them. |
| `nodes/_otr_casting.py` | 290-348 | Cast character prompt | Mostly SHARED + COMPAT | "Write a character for a radio drama" is reusable. `news_seed` name is compatibility; source profile should supply story/casting brief text. |
| `nodes/_otr_casting.py` | 1297-1318 | Cast naming prompt | Mostly SHARED + COMPAT | "Name the cast of a radio drama" is reusable. Story material should come from active packet/profile, not raw news naming. |
| `nodes/OTR_LedgerScriptWriter.py` | 935-950 | Title regeneration | PROFILE | "sci-fi radio drama" should become story form label. The physical-detail title process is reusable. |
| `nodes/OTR_LedgerScriptWriter.py` | 4897-4927 | News coda routing | PROFILE + COMPAT | The branch names/call helper are news-specific. Generalize to source coda mode while preserving same ledger close line. |
| `nodes/_otr_style_picker.py` | 297, 335 | Style/descriptor picker | PROFILE or verify dead path | "sci-fi radio drama" prompt text survives outside the original audit. If active, it must read story form/story model from the prompt profile; if inactive, mark test/dead with evidence. |
| `nodes/_otr_story_quality_l12.py` | 375-401, 724-830 | Deterministic story-quality shaping | Mostly SHARED + COMPAT | Premise-grounded conflict/beat roles are reusable. Reads `meta.news` fields; should read active source packet or compatibility mirror. |
| `nodes/_otr_story_spine.py` | 202-218 | Announcer recomposition context | COMPAT | Pulls `meta.news.script_brief/news_close_brief`; should receive active packet mirror or source-neutral accessors. |

## Sci-Fi / Science-Specific Language To Extract

These phrases are not inherently required for a good radio drama:

- `science-fiction audio drama`
- `sci-fi radio drama`
- `science story`
- `real science`
- `grounded in real science`
- `real news item`
- `news event`
- `NEWS PREMISE`
- `NEWS KEY TERMS`
- `real news report`
- `news facts`
- `news_close_brief`

Also extract or gate story-model drift phrases that push archive mode back into
generic sci-fi anthology territory.

## Reusable Radio-Drama Craft

These ideas are likely source-neutral and should remain shared unless a source
profile intentionally overrides them:

- short audio/radio drama form
- cast block / exact speaker names
- setup, complication, resolution
- phase and beat planning
- premise-grounded central conflict
- clear human want
- rising stakes
- final 20 seconds / on-stage climax
- no stage directions in spoken lines
- announcer intro/outro format
- period host voice, if the show identity remains OTR
- physical final image
- no invented proper names outside source/cast

## Proposed Prompt Profile Variables

Minimum variables for `nodes/_otr_story_prompt_profile.py`:

```
source_bank_id
source_intent_label
story_form_label
system_role_label
source_material_label
source_develop_verb
source_grounding_label
key_terms_label
close_brief_label
coda_mode
coda_system_prompt
line_grounding_instruction
title_form_label
outline_rules_extra
story_model_id
story_model_label
tone_guardrails
forbidden_plot_patterns
```

Example values:

`science_news`:

```
story_form_label = "science-fiction audio drama"
source_material_label = "Science story"
source_develop_verb = "extrapolate dramatically from this science story"
source_grounding_label = "news facts"
coda_mode = "real_news_report"
```

`media_archive`:

```
story_form_label = "archive-inspired radio drama"
source_material_label = "Media archive item"
source_develop_verb = "build a fictional story from this archive/media-history material"
source_grounding_label = "archive material"
coda_mode = "archive_source_note"
story_model_id = "media_restoration_adventure"  # or cinematic_humorous, happy_archive_mystery, gentle_thriller, broadcast_history_comedy
forbidden_plot_patterns = ["Star-Trek-style mission plot", "Amazing-Stories-style twist anthology unless explicitly selected"]
```

`public_domain_story`:

```
story_form_label = "public-domain adaptation for radio"
source_material_label = "Public-domain source text"
source_develop_verb = "adapt this source story while preserving its characters, turns, and ending"
source_grounding_label = "source text"
coda_mode = "source_attribution_or_adaptation_note"
```

## Code-Ready Takeaway

Do not rip out every prompt that says "radio drama." Instead:

1. Move source-specific ledger-writing language behind prompt-profile variables.
2. Keep source-neutral radio-drama craft shared.
3. Keep `meta.news` only as a compatibility mirror until consumers are migrated.
4. Add tests that fail if `media_archive` or `public_domain_story` prompts contain
   science/news-only phrases.
