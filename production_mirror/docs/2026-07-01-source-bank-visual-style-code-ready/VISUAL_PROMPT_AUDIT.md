# Visual Prompt Audit

Status: live artifact for kibitz/code planning.

Goal: identify still/video prompt sites that currently hardcode a visual look
instead of reading `meta.visual_style`, and separate style language from role
safety constraints.

Legend:

- `STYLE`: move behind `VisualStylePolicy` / visual-style catalog.
- `ROLE`: keep as role safety or engine routing unless a style explicitly
  overrides it with tests.
- `SEAM`: central place where style should be applied.
- `COMPAT`: legacy/current behavior to preserve until transplant.

## Known Material Visual Prompt Sites

| File | Lines | Visual role | Classification | Notes / variable target |
|---|---:|---|---|---|
| `nodes/_otr_story_brief_helpers.py` | 229-232 | Default era/style tails | STYLE + SEAM | `ERA_TAIL_DEFAULT` and `STYLE_TAIL_DEFAULT` hardcode timeless/cinematic/35mm/film grain. These become default `sci_fi_radio` or `cinematic_35mm` policy tails. |
| `nodes/_otr_story_brief_helpers.py` | 246-251 | Radio broadcast scene tail | STYLE | `RADIO_BROADCAST_TAIL` is a current radio/OTR look. It should be owned by `sci_fi_radio` or `media_archive`, not always appended to every eligible scene. |
| `nodes/_otr_story_brief_helpers.py` | 348-358 | Radio/open beat subject | STYLE + ROLE | Vintage radio/studio subjects are a current bookend visual identity. Style-aware policy should be able to produce anime/cartoon/origami equivalents while preserving announcer/music bookend semantics. |
| `nodes/_otr_story_brief_helpers.py` | 371-385 | Still framing constants | STYLE + ROLE | "cinematic three-quarter" and "cinematic medium shot" are visual style language. Whole-head/framing constraints are role safety. Split them. |
| `nodes/_otr_story_brief_helpers.py` | 390-458 | `compose_still_prompt` | SEAM | Calls `finish_visual_prompt`; should pass through `meta.visual_style` for style tail, radio tail, and style-specific subject language. |
| `nodes/_otr_story_brief_helpers.py` | 458-488 | `finish_visual_prompt` | SEAM | Central style seam. Must read `_meta(meta).get("visual_style")`, apply policy tails/scrubs, and avoid hardcoded cinematic-only default in wired new path. |
| `nodes/otr_meta_brief_image_prompt.py` | 92-105 | Portrait/scene anchors | STYLE + ROLE | "cinematic", "dramatic film lighting" are style. Head/face/full-body/framing are role safety. |
| `nodes/otr_meta_brief_image_prompt.py` | 121-126 | Announcer portrait anchor | STYLE | Hardcoded vintage 1940s radio announcer/microphone look. Should become style policy subject/directive for `sci_fi_radio`; anime/cartoon/origami need alternate announcer visual language. |
| `nodes/otr_meta_brief_image_prompt.py` | 209-217 | Wide scene / radio host subject | STYLE | "wide 16:9 cinematic scene", "period-accurate set", radio host subject are style-specific. |
| `nodes/otr_meta_brief_image_prompt.py` | 452-492 | Character prompt LLM instructions | ROLE + STYLE | "Do not include film-stock..." is deliberate because finisher owns style tail. Keep this boundary, but make style owner `VisualStylePolicy`. "Do not mention radios..." is role safety for character prompts. |
| `nodes/otr_meta_brief_image_prompt.py` | 542-556 | Character scene fallback/finish | SEAM | Uses `finish_visual_prompt(meta, ...)`; should inherit visual style once `meta.visual_style` is injected. |
| `nodes/otr_meta_brief_image_prompt.py` | 581-587 | Mesh fodder subjects | ROLE + STYLE | Isolated figure/radio mesh subjects are role/engine requirements; the visual rendering language should be style-aware. |
| `nodes/otr_meta_brief_image_prompt.py` | 619-623 | Background plate finish | SEAM | Uses `finish_visual_prompt`; style propagates if meta is injected. |
| `nodes/otr_meta_brief_image_prompt.py` | 651-656, 764-801 | Gear scrub / announcer exception | ROLE | Keep as safety: character portraits should not drift into radio/mic/studio gear, except announcer/radio-role prompts. |
| `nodes/otr_meta_brief_image_prompt.py` | 804-829 | Final portrait finish + image grade | STYLE + SEAM | Adds film/grade tails after `finish_visual_prompt`. Needs policy control so anime/cartoon/origami do not get cinematic film grade. |
| `nodes/otr_shot_lock.py` | 78 | Fallback setting | STYLE | "a vintage radio studio" is current default setting; should come from visual/story spec when style/source changes. |
| `nodes/otr_shot_lock.py` | 499-514 | M4 batch prompt | ROLE + STYLE | "You are a film director" and "do not include film-stock..." are current style assumptions. Keep "do not duplicate style tails" boundary but make role label/style owner configurable. |
| `nodes/otr_shot_lock.py` | 601-640 | Deterministic prompt fallback + finish | SEAM | Calls `finish_visual_prompt(meta, text_prompt)`. Style propagates if ShotLock stamps `meta.visual_style` before M4 derivation. |
| `nodes/_otr_video_engines/render_driver.py` | 254 | Soak fixture default prompt | DEAD/TEST or STYLE | "1940s radio studio" fixture. Keep test-only or make fixture explicit for current style. |
| `nodes/_otr_video_engines/render_driver.py` | 538-567 | LTX motion prompt table | STYLE + ROLE | Motion-only radio-console prompts currently assume radio. Style-aware bookend motion prompts may be needed for anime/cartoon/origami/media archive. |
| `nodes/_otr_video_engines/render_driver.py` | 630-632 | Character face fallback prompt | STYLE + ROLE | "cinematic portrait", "1940s costume", "dramatic film lighting" are style. Face-centered fallback is role safety. |
| `nodes/_otr_video_engines/render_driver.py` | 781-851 | Radio-is-host enforcement | ROLE + STYLE | Current operator rule for radio bookends. Keep as current style/role guard, but style catalog needs a way to define non-radio bookend analogs. |
| `nodes/_otr_video_engines/render_driver.py` | 1317-1415 | Text-engine scene fallback | SEAM + STYLE | Has env override, radio motion prompts, and `finish_visual_prompt(... style_tail=False)`. Policy positive tail must still apply when style_tail is false. |
| `nodes/_otr_video_engines/render_driver.py` | 1540-1572 | Lipsync base prompt | STYLE + ROLE | "1940s radio actor speaking into a studio" is current style fallback. Needs visual-style catalog if used under non-radio styles. |

## Visual Style Language To Extract

These should move into `VisualStylePolicy` / `_otr_visual_style_catalog.py`:

- `cinematic`
- `35mm film look`
- `subtle film grain`
- `film-stock`
- `dramatic film lighting`
- `broadcast-distressed`
- `vintage 1940s radio`
- `1940s radio station studio`
- `radio set warming up`
- `period-accurate set`
- `1940s costume`
- `radio actor speaking into a studio`

## Role Safety To Preserve

These are not merely style and should not be removed casually:

- exact cast/person anchoring for character prompts
- whole head / face / headroom constraints
- no stage text / no on-screen text
- no radios/microphones/studios in ordinary character portraits
- announcer/music visual bookend semantics
- mesh-fodder subject isolation
- face-centered fallback for lipsync/face engines
- prompt hash after final style application
- LOUD failure on missing prompts or unsafe engine fallbacks

## Proposed Visual Policy Fields

Minimum fields for `VisualStylePolicy`:

```
style_id
label
positive_tail
negative_or_forbidden_terms
base_tail_strategy
image_grade_tail
radio_broadcast_tail_replacement
announcer_visual_subject
music_visual_subject
scene_open_subject
character_portrait_style
character_scene_style
motion_prompt_profile
ledger_directives
```

Example intent:

`sci_fi_radio`:

```
positive_tail = "cinematic, 35mm film look, subtle film grain..."
announcer_visual_subject = "vintage 1940s radio announcer..."
music_visual_subject = "vintage tabletop radio receiver..."
```

`anime`:

```
positive_tail = "anime style, hand-drawn cel shading, expressive linework..."
forbidden_terms = ["photorealistic", "35mm film", "film grain"]
announcer_visual_subject = "anime radio host at a stylized broadcast desk..."
```

`paper_origami`:

```
positive_tail = "folded paper diorama, papercraft texture, handmade paper edges..."
forbidden_terms = ["photorealistic", "cinematic 35mm", "film grain"]
announcer_visual_subject = "folded-paper radio host figure in a paper broadcast set..."
```

## Code-Ready Takeaway

Do not just add a style suffix. The visual transplant needs three layers:

1. catalog-defined style policy
2. `meta.visual_style` stamped into the patched ledger
3. shared prompt seams and fallback/default prompts reading that policy

Tests should fail if `anime`, `cartoon`, or `paper_origami` still emit hardcoded
`35mm`, `film grain`, `1940s radio studio`, or `cinematic film lighting` unless
that phrase is explicitly allowed by the chosen style.

