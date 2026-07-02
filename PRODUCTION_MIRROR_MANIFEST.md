# Production Mirror Manifest

Created: 2026-07-02. This lab was cleared and rebuilt as a transplant
workspace. The v1 standalone lab (contracts/catalogs/fixtures/preview/nodes)
is preserved in git history at commit `41c6512` (snapshot) / `cf14138`
(merge); nothing was lost.

## Baseline

Mirrored from `ComfyUI-OldTimeRadio` at:

```text
commit d48a9d76f39db6db16c758d9b2c1c22a9af38d3f
date   2026-07-02 00:22:46 -0700
title  talking-radio B: LTX-only mouth-forward radio-face still (ltx_radio_mouth), split from HuMo hosts
```

This baseline is AFTER rip-sfx-broll (6bad6e5b, 2026-07-01): the workflow and
all mirrored code are the SFX-free surface.

## Layout And Rules

- `production_mirror/` - pristine read-only reference copies. Never edit.
  Diff transplant work against these.
- `workflows/otr_scifi_16gb_full.json` - the editable working copy of the
  SFX-free canonical workflow. Transplant edits happen HERE first, validated
  here, and only later applied to production in one explicit chunk.
- `production_mirror/workflows/otr_scifi_16gb_full.json` - the untouched
  baseline of the same file (hash below) for diffing.
- Production repo stays untouched until the transplant chunk. Nothing in this
  lab is imported by production.
- Before applying any transplant chunk to production, re-run the drift check:
  compare `production_mirror` hashes against the live files; if production
  moved past `d48a9d76`, re-mirror and re-validate first.
- Gates for touching the real workflow JSON:
  `docs/FABLE_FINAL_REVIEW_2026-07-02.md` (TEST / VALIDATION GATES section).

## Copied Files (SHA256 first 16 hex, size bytes)

```text
C32F5FD68B71944F  workflows\otr_scifi_16gb_full.json  35277
B4555AFC5D005098  nodes\OTR_LedgerScriptWriter.py  306585
0570C37EFB937FEA  nodes\OTR_LedgerFreezeCascade.py  23096
8D22076839E1196A  nodes\news_interpreter.py  37801
59242F82C2827555  nodes\_otr_outline.py  114108
8012F63D052ED54C  nodes\_otr_pitch_room.py  22793
432FF00F164A2375  nodes\_otr_story_select.py  40874
4BE72865ACF974D1  nodes\_otr_dramatic_state_llm.py  24218
4EE0FF1208B3622B  nodes\_otr_line_composer.py  174648
6B49E5CA1B3CAEA5  nodes\_otr_casting.py  85560
837ABE6C24B22E8C  nodes\_otr_style_picker.py  35301
24A6E12A888CE4C6  nodes\_otr_story_quality_l12.py  38405
349029FA70668436  nodes\_otr_story_spine.py  45973
6321913E9C3E3919  nodes\_otr_story_brief_helpers.py  27120
E84818347238ADCF  nodes\otr_meta_brief_image_prompt.py  67286
BEF96B6667EDF9B4  nodes\otr_shot_lock.py  41955
187ADE4D8F780D58  nodes\_otr_video_engines\render_driver.py  133716
041F04E9893A3464  nodes\_otr_ledger_freeze.py  32789
134629DAAFD9F30E  nodes\_otr_legacy_to_stage1_adapter.py  25581
53E857A9354E87AA  nodes\_otr_speaker_role.py  9828
CBC385C962E984FD  nodes\_otr_workflow_apply.py  22587
C4B5C7463704D5E9  nodes\_workflow_validation.py  17366
29EFFD324A6A385A  nodes\_otr_workflow_validator.py  19389
04D2141B7576FF9E  nodes\_otr_shared\role_slots.py  5263
6789B1C0C3CCB2CF  nodes\_otr_shared\role_compat.py  6294
DAED2580842493CC  scripts\otr_api.py  38916
611BE254E0663DF8  docs\...\LEDGER_PROMPT_AUDIT.md  8492
D2FB4F7ED0643A0D  docs\...\PHASE2_PROMPT_PY_UPDATE_MAP.md  24623
96CC7B6320601833  docs\...\VISUAL_PROMPT_AUDIT.md  8706
769F8EC1143C9FDA  docs\...\STORY_AND_VISUAL_SCI_FI_REMNANTS_ARTIFACT.html  18958
FAC600B554CAED6C  docs\...\VISUAL_SCI_FI_REMNANTS_ARTIFACT.html  14549
```

Selection rationale: every file named as a transplant edit site or gate
reference in `docs/FABLE_FINAL_REVIEW_2026-07-02.md`, `PROMPT_SURGERY_CHECKLIST.md`,
and the production Phase 2 map - prompt sites (story + visual), the meta.news /
news_seed shape owners, role vocabulary, workflow validators, and the
API/apply whitelists.
