# Sonnet Ledger Bible Audit

**Model:** Claude Sonnet 5 (`claude-sonnet-5`) for all evidence-gathering, adjudication, and the original
write; a final organization-only editing pass (no findings changed) ran on Claude Fable 5
(`claude-fable-5`) at the operator's request. Running as Claude Code (not the Cowork MCP dual-filesystem
setup CLAUDE.md warns about -- this session's Read/Grep/Bash/Write tools hit the real Windows filesystem
directly; no Linux-mount lag was encountered or needed to be worked around).

**Credit / spend rung:** $0 external spend. No GPU job, no cloud API, no OpenRouter/paid panel call. All
evidence-gathering ran as same-family Claude subagents inside this session (a 9-agent background `Workflow`
fan-out: 7 independent grounded tracers + an adversarial steelman/refute pair, ~1.5M subagent tokens, 440
tool calls), followed by my own direct spot-verification of the highest-stakes single-line claims against
the live files, plus a supplementary sweep of six `nodes/` subdirectories none of the seven tracers covered.

**Review-routing directive and date actually read:** `docs/GO_FORWARD_PLAN.md` (Story Lab repo), "Review
routing" section: *"The active operator directive is dated 2026-08-11: full r1-r4 kibitz is suspended. Use
a Codex consult only for a genuine quandary or third attempt and Sonnet 5 for post-coding QA."* This audit
is not a coding item -- it is the standalone "Independent Sonnet audit/red-team" track the same
`GO_FORWARD_PLAN.md` names in its own staged-evidence list, run in parallel with the AGY (Antigravity) and
Codex tracks, not a post-coding QA pass -- so the kibitz-suspension directive does not gate it and no
`/kibitz` panel was invoked. No production code, Story Lab code, workflow JSON, test, prompt, source bank,
render runner, or existing report was edited. No file was written except this one.

---

## 0. Scope and method

Read, in full, before auditing: production `AGENTS.md` and `CLAUDE.md`; Story Lab
`docs/GO_FORWARD_PLAN.md` (including the 2026-08-11 review-routing block); Story Lab
`docs/2026-08-13-story-recovery/LEDGER_BIBLE_AUDIT_PLAN.md`; Story Lab
`docs/2026-08-13-story-recovery/AGY_LEDGER_BIBLE_AUDIT.md` (the full 458-line report, both halves).

I then ran a background `Workflow` of 9 grounded subagents, each instructed to read only the real files
(never to trust AGY's report, which they were never shown), cite exact `file:line` evidence for every
claim, and label every finding `CONFIRMED` / `INFERENCE` / `UNKNOWN` / `CHECKED_NOT_A_CONSUMER`:

- **A -- core ledger + Phase 0-10 freeze cascade** (`_otr_ledger.py`, `production_ledger.py`,
  `_otr_ledger_freeze.py`, `_otr_freeze_cascade.py`, `OTR_LedgerFreezeCascade.py`,
  `_otr_content_authorship.py`, `_otr_casting.py`, `_otr_cast_contract.py`, the SciFi/Fable2/news story
  packs)
- **B -- cast lock through episode assembly** (`cast_lock.py`, `_otr_voice_node_common.py`,
  `batch_character_voices.py`, `announcer_voice.py`, `stable_audio_theme.py`, `scene_sequencer.py`,
  `audio_enhance.py`)
- **C -- visual pipeline** (`otr_shot_lock.py`, `otr_meta_brief_image_prompt.py`,
  `otr_image_gen_dispatcher.py`, `otr_video_render_batch.py`, `_otr_video_engines/` -- all 19 engine
  adapters plus `acceptance.py`/`frame_contract.py`/`coverage_plan.py`/`registry.py` --
  `otr_silent_composite.py`, `otr_post_upscale_procgen_blend.py`, `otr_scene_aware_scopes.py`)
- **D -- terminal delivery** (`otr_caption_burn.py`, `_otr_captions.py`, `otr_credits_roll.py`,
  `otr_master_audio_mux.py`, `video_engine.py`'s `OTR_SignalLostVideo`/rename trigger,
  `production_ledger.py::rename_episode`)
- **E -- sweep of every remaining `nodes/*.py` file (127 files) + `scripts/*.py`** for missed consumers
  and non-consumers
- **F -- test inventory**, opening every ledger-referencing test file AGY cited to confirm it exists and
  does what AGY says
- **G -- Story Lab side** (`ledger_requirements_v1.json`, `PROBLEM_STATEMENT.md`, `RECOVERY_MATRIX.md`,
  both fixture episodes, `ledger_contract.py`, `extract_story_recovery_cases.py`)
- **Steelman / Refute pair** -- one agent built the strongest possible case that AGY's "strictly frozen at
  Phase 10" claim is true; a second, independently, built the strongest possible case it is false. Neither
  saw the other's work.

After the workflow returned, I personally re-read the exact lines behind the highest-stakes claims
(`cast_lock.py:495-534`, `_otr_ledger_freeze.py:895-959`, `otr_master_audio_mux.py:515-613`, the whole-repo
`cleanup_locked` grep, `scene_sequencer.py:1760-1834`, `_otr_content_authorship.py:28-95`) and confirmed
every quote below word-for-word against the live file. I then closed one scope gap the sweep agent (E)
explicitly flagged as out of its bounds: `nodes/` subdirectories other than `_otr_video_engines/`
(`_otr_shared/`, `_otr_audio_engines/`, `_otr_image_engines/`, `_otr_google_api/`, `_voice_backends/`,
`story_packs/`). That sweep found one real, previously-unreported ledger mutator --
`_otr_shared/portrait_ledger.py::stamp_portrait()` -- documented in section 3.

**Probes run** (all read-only, no GPU): repo-wide `grep` passes (via the `Grep`/`Bash` tools) for
`cleanup_locked`, `speaker_role` write-sites, `fact_id(s)`, `stamp_portrait`/`portrait_ledger`, and ledger
persistence calls (`stamp_durable|save_ledger_safe|led\.set_|led\.save\(|in_flight_ledger_path`) across six
previously-unswept `nodes/` subdirectories. The Story Lab agent (G) additionally ran, from the Story Lab
venv: `git status --short src/upstream_story_lab/ledger_contract.py` (confirms the file is untracked), a
one-line import probe of that module (confirms it imports cleanly and is real, runnable code), and
`pytest -q tests/test_story_recovery_artifacts.py` (14 passed). No other test suite was run and no GPU job
was launched by me or by any subagent.

---

## 1. Executive verdict

**Verdict: AGY's two-plane framing is directionally right but its headline claim is FALSE as stated. The
"narrative/structural plane" is not strictly frozen at Phase 10 -- it is validated and timestamped once,
then structurally rewritten, in production, by at least three different post-freeze nodes, none of which
are blocked by any enforcement mechanism, because no such mechanism exists anywhere in the codebase.**
Confidence: **high** -- this rests on three independent lines of evidence that converged without seeing
each other's work (cluster A's code read of the freeze module itself, cluster B's trace of `cast_lock.py`
and `EpisodeAssembler`, and the dedicated steelman/refute pair), plus my own direct re-read of every quoted
line.

### 1.1 The ten adjudicated claims at a glance

The audit prompt named ten claims requiring special adjudication from executable code. All ten resolved:

| # | Claim to adjudicate | Verdict | Evidence anchor |
|---|---|---|---|
| 1 | Does `meta.cleanup_locked` have any production reader that blocks mutation? | **NO -- CONFIRMED** | Written once (`_otr_ledger_freeze.py:949`), read by zero production code paths; repo-wide grep (sec. 1.4) |
| 2 | Does Phase 10 deep-copy, wrap, hash, or protect the whole authored structure? | **NO -- CONFIRMED** | Same mutable dict throughout, no copy, no wrapper, no whole-structure hash (sec. 1.2) |
| 3 | Does `_sha256_content_authorship` cover cast, scenes, shots, beats, speaker ownership, facts, and authored music? | **NO -- CONFIRMED** | Voiced `lines[].{line_id,text}` only; none of the seven named surfaces (sec. 1.4; sec. 7 row 4) |
| 4 | Can CastLock rewrite `lines[].speaker_role` after Phase 10? | **YES -- CONFIRMED** | `cast_lock.py:522-523`, silent in-place rewrite on live wiring (sec. 1.3) |
| 5 | Can EpisodeAssembler append music mirrors to and reorder `lines[]`? | **YES -- CONFIRMED** | `scene_sequencer.py:1779-1830`, mint + append + full re-sort + reassign (sec. 1.3) |
| 6 | Are SciFi `fact_ids` preserved into the durable production ledger? | **NO -- CONFIRMED** | Dropped at `_assemble_ledger` (`_otr_scifi_codex.py:3200`); survive only as `meta.scifi_codex.fact_index` forensics (sec. 1.6) |
| 7 | Do SilentComposite, CaptionBurn, CreditsRoll, and video-engine adapters actually persist ledger writes? | **NO, all four -- the AGY claims are false -- CONFIRMED** | Zero persistence calls in any of them; AGY's claimed stamp fields do not exist anywhere in the repo (sec. 7 row 9) |
| 8 | Are clip/shot/image mutations durable writes, wire-only state, or result-manifest changes? | **Mixed -- CONFIRMED** | ShotLock's `video` section is wire-only; most VideoRenderBatch mutations are transient and discarded; durable = `images` section, `meta.render_engines`, `audio_motion_profiles`, post-upscale stamp (sec. 3) |
| 9 | Can publication succeed when the final ledger writeback fails? | **YES -- CONFIRMED by code read; no runtime test exists** | `"obs_publish OK"` is recorded before a ledger stamp that can never raise (sec. 2 step 4; sec. 3) |
| 10 | Do both ledger save paths use the same schema-version and merge policy? | **NO, on both axes -- CONFIRMED** | Blind-overwrite + preserve-foreign-version vs. row-merge + always-stamp-current, plus a third strict-equality gate at Phase 10 that conflicts with both (sec. 6) |

Each verdict is expanded with quoted code in the sections cited.

### 1.2 What Phase 10 actually does

`_otr_ledger_freeze.py::phase_10_gap_audit_post_and_freeze` (lines 901-962) does exactly three things:
run a schema/shape validator (`run_gap_audit`) over the live in-memory dict, raise `FreezeAssertionError`
if it finds a critical gap, otherwise stamp three `meta` keys (`cleanup_locked=True`, `freeze_timestamp`,
`freeze_verdict`) onto the **same mutable dict object** it was handed (`ledger_data = led.data`,
`_otr_freeze_cascade.py:723` -- no copy). It is a **schema validator plus a metadata stamp**, not a
diff/immutability check: a well-formed rewrite of any field passes exactly as cleanly as the truth, because
the checks never compare "this value now" against "this value at an earlier baseline" (with one narrow
exception, below).

### 1.3 Three confirmed post-freeze rewrites of the "frozen" narrative plane

All three touch fields AGY explicitly names as part of the frozen narrative plane:

1. **`nodes/cast_lock.py:522-523`** -- `OTR_CastLock._resolve_character_voices_fail_soft()` does
   `ln["speaker_role"] = "announcer"` in place, on a line dict living inside the same `lines[]` list the
   freeze cascade just sealed, whenever a `speaker_role=="character"` row's `char_id`/cast-row identity
   says announcer and it has no resolvable voice preset. Framed in the code's own comment as "a routing
   CORRECTION, not a fallback" -- but nothing rejects it; it succeeds silently with a one-line info note.
   I re-read this exact block myself and confirm it verbatim.
2. **`nodes/scene_sequencer.py:1651-1830`** (`OTR_EpisodeAssembler.assemble()`) -- mints brand-new
   `lines[]` rows (`speaker_role` in `{music_open, music_inter, music_close}`, with `speaker`, `text`,
   `start_s`, `shot_id`, ...) that never existed in the writer's or Phase 10's output, appends them, then
   **re-sorts the entire `lines[]` array** by `start_s` and reassigns `_led["lines"] = _lines_for_music`
   (line 1830). I re-read this block myself and confirm it verbatim.
3. **`nodes/otr_shot_lock.py`'s `overlay_audio_timing(strict=True)`** (called unconditionally whenever
   `audio_done` is set, i.e. every normal render) filters, replaces, and re-sorts `lines[]` again, then
   reassigns `ledger["lines"] = base_lines`.

### 1.4 Why nothing catches these

The one real diff-based integrity check that does exist (`_otr_freeze_cascade.py:1007-1018`, comparing
`_sha256_lines_text`/`_sha256_content_authorship` at cascade entry vs. exit) is real but narrow: it fires
only for the `content_owned_readonly` freeze policy (inline-safety-cleanup banks never hit it at all), it
only compares entry-of-this-call against exit-of-this-same-call (no memory of any earlier freeze, so it
cannot catch a mutation that happens after `run_freeze_cascade()` returns -- which is exactly where all
three rewrites above happen), and its two hashes are discarded after the call, never persisted for a later
run to re-check against.

`meta.cleanup_locked` -- the literal "lock" flag -- is written at exactly one place
(`_otr_ledger_freeze.py:949`) and read at zero places in production code (confirmed by a repo-wide grep: the
only other hits are the writing module's own docstrings and one test file asserting the stamp landed). The
function's own docstring even documents that calling Phase 10 twice on an already-"locked" ledger is
"idempotent," i.e. it re-runs and re-stamps rather than refusing. Of the seven post-freeze audio-cluster
nodes, exactly one (`OTR_CastLock`) checks `meta.freeze_verdict` at all, and it has a documented bypass env
var (`OTR_BYPASS_FREEZE_HALT=1`) with no re-gate anywhere downstream. Nothing in the visual pipeline or
terminal-delivery cluster checks either flag.

### 1.5 The exact proposed freeze boundary

The corrected, evidence-grounded version of AGY's claim: Phase 10 freezes *shape and referential
validity*, not *content*. The only content genuinely protected by any mechanism today
is `lines[].text` for **voiced** lines (via `_sha256_content_authorship`, scoped to the
`content_owned_readonly` policy only) and, within a single cascade call, all lines' text (via
`_sha256_lines_text`). Everything else -- `cast[]`, `scenes[]`, `beats[]`, `shots[]`, `music[]`,
`speaker_role`, and `lines[]`'s own cardinality/order -- is unprotected after Phase 10 returns, and in
practice gets mutated by name-checked production nodes on every normal render.

### 1.6 The `fact_ids` drop (independent structural finding)

SciFi/news `fact_ids` are minted and validated during generation but are silently and permanently
dropped at the score-to-ledger assembly boundary (`_otr_scifi_codex.py::_assemble_ledger`, lines 3151-3262) -- they never land on any
`beats[]`/`lines[]`/`scenes[]` row, only inside `meta.scifi_codex.fact_index` as forensic metadata. Phase
10's gap-audit has no rule that would notice this, because the field was never expected on a row in the
first place. This means the freeze cascade cannot detect a fact-grounding regression on the exact lane
(`scifi_news`) whose failure is the reason this whole recovery effort exists.

### 1.7 Recommended target contract (central question 4)

Neither "one immutable JSON object" nor a clean "immutable authored-story projection + mutable production
state" split -- because that split does not exist in the current data model and inventing it wholesale is a
bigger redesign than the evidence supports. The smallest design consistent with every confirmed consumer:

1. Stop conflating authored dialogue rows and synthetic timeline rows in one `lines[]` array. `EpisodeAssembler`
   and `ShotLock` both have a real, legitimate need to inject timed music-mirror rows that downstream
   consumers (`OTR_CaptionBurn`, `OTR_CreditsRoll`, the video-shot pipeline) currently read off `lines[]`
   alongside real dialogue. Give them their own array (e.g. `timeline[]`) keyed by `line_id` reference plus
   synthetic-row payload, and stop appending to/re-sorting the authored `lines[]` array itself.
2. Make `lines[].{line_id,char_id,scene_id,shot_id,speaker,speaker_role,text}` write-once, enforced (not
   merely validated) once `meta.cleanup_locked` is true -- e.g. a real guard inside `patch_line_fields`/
   `stamp_durable`/`save_ledger_safe` that rejects a change to those seven fields on a frozen ledger, with
   one explicit, audited exception path for the announcer mis-stamp correction CastLock currently performs
   silently (make it a first-class, logged, `meta`-recorded repair instead of a silent dict write).
3. Split `cast[i]`'s identity fields (`char_id`, `name`, `cast_role`) from its voice/production fields
   (`voice_preset`, `voice_route_id`, `voice_spec`, `presentation_gender`, `tts_model`,
   `portrait_content_hash`, ...) into a nested `cast[i].voice`/`cast[i].portrait` sub-object, so "cast is
   frozen" can mean identity is frozen while production state is legitimately still being filled in.
4. Preserve `fact_ids` through `_assemble_ledger` onto `beats[]`/`lines[]` (not only inside
   `meta.scifi_codex.fact_index`), and add a Phase-10 gap-audit rule requiring the closing
   announcer/news-coda row's `fact_ids` to be non-empty on news-grounded source banks -- this is exactly the
   rule the Story Lab's own already-written but unwired `ledger_contract.py` already encodes
   (`SequenceItem`/`announcer_news_coda` validator, lines 327-337).
5. Reconcile the two save paths' schema-version and merge policies (`save_ledger_safe` preserves a foreign
   version; `Ledger.save()`/`stamp_durable` always stamps current; `_otr_ledger_freeze.py`'s own gate
   hard-fails on anything but current) -- today a ledger legitimately saved through `save_ledger_safe`'s
   documented anti-regression policy can be hard-rejected by Phase 10 if it is ever re-run through the
   cascade.
6. Make `OTR_MasterAudioMux`'s terminal ledger stamp fail loud (or at minimum log at ERROR and reflect the
   failure in its returned status string) instead of silently swallowing a `save_ledger_safe` failure --
   today `"obs_publish OK"` can be truthfully printed and returned while the ledger's own record of that
   publish (`final_audio_path`, `final_video_path`, `meta.obs_final_path`) never lands on disk.

### 1.8 What the Story Lab must emit (central question 5)

Grounded in the two hash-pinned fixtures, `ledger_requirements_v1.json`, and the Story Lab's own
`ledger_contract.py` (all read in full; the fixture-integrity suite ran live, 14 passed):

1. **A typed six-role `sequence` array as real emitted data, not an array-position convention.** Today
   neither fixture has one: the clean control encodes "announcer first/last" only by array index +
   `speaker_role` string, and the challenger encodes music only via `placement`/`anchor_line_id` on cue
   objects. The only place the typed shape exists is `src/upstream_story_lab/ledger_contract.py`
   (`SequenceRole`, lines 32-39) -- which is **untracked in git, imported by nothing, and tested by
   nothing** (confirmed by probe: `git status` shows `??`, a repo-wide grep finds zero importers, and no
   test names it). It is the right design, currently existing only as aspiration.
2. **Cast-bound speaker authority on every line**: a `speaker` name + `char_id` pair machine-checkable
   against `cast[]`. The challenger's P5 lines carry no `speaker` key at all -- the
   `P5_SPEAKER_AUTHORITY_MISSING` regression, proven by `test_story_recovery_artifacts.py:214`
   (`assert all("speaker" not in line ...)`). `ledger_contract.py:243-250` already encodes exactly the
   needed check (`line.speaker == cast_row.name`, `line.speaker_role == cast_row.cast_role`).
3. **Typed `fact_ids` that actually reach the closing announcer row.** The challenger's per-line fact
   typing is genuinely better than the control's (which has none at all), but its one announcer row
   carries `fact_ids: []` -- the capability exists and is wired to the wrong row. `ledger_contract.py:333-337`
   already requires the `announcer_news_coda` line to cite at least one source fact. This must pair with
   production-side preservation (recommendation 4 in section 1.7), or the field dies at `_assemble_ledger`
   regardless of what the Story Lab emits.
4. **Music anchors bound to row role, not just "some line."** Both challenger bookend cues anchor to
   character rows (`MUSIC_OPEN_ANCHOR_NOT_ANNOUNCER` / `MUSIC_CLOSE_ANCHOR_NOT_ANNOUNCER`, reproduced by
   `test_challenger_music_bookends_anchor_to_character_rows`).
5. **One closed ID namespace across cast/scene/shot/beat/line/cue.** Not yet true even in the clean
   control: its announcer lines carry `char_id="announcer"` while its own cast row says `c01`, and its
   `line_id`s literally equal its `beat_id`s (the legacy shape has no separate namespace). Production's
   CastLock happens to tolerate the announcer alias via its `announcer_ids` set; a strict emitted contract
   must settle the alias question explicitly rather than inherit the ambiguity.
6. **Provenance**: keep the extractor's SHA-256 pinning discipline -- both fixtures are already byte-pinned
   and test-guarded, and that is the strongest provenance mechanism anywhere in either repo today.

**Interop warning**: three mutually incompatible ledger shapes currently coexist in the Story Lab repo --
the legacy flat control shape, the P3/P5 compiled challenger shape, and `ledger_contract.py`'s `StoryBody`
shape -- with **no adapter between any two of them** (repo-wide grep: nothing imports `ledger_contract`).
As of today the Story Lab emits nothing that production, or even its own contract module, can ingest
without a still-unwritten mapping layer. Wiring, committing, and testing `ledger_contract.py` is the
single highest-leverage Story Lab step this audit found.

---

## 2. Canonical workflow/lifecycle diagram

```
DRAFT / PRE-FREEZE (single owner: the writer + its internal helper modules; freely mutable)
================================================================================================
OTR_LedgerScriptWriter (OTR_LedgerScriptWriter.py:2866, entry led = new_ledger() @4026)
  |-- casting: _otr_casting.py (lock_cast, precompute_ensemble_slots, python_assign_voice_preset)
  |-- cast durable stamp: cast_lock.py -> stamp_durable(sections={"cast":...})  [pre-freeze first pass]
  |-- outline/beats: _otr_outline.py, production_ledger.py::init_lines_from_outline
  |-- dialogue composition: _otr_line_composer.py, _otr_speaker_role.py
  |-- story-pack overlay (bank-specific; each owns cast/scenes/shots/beats/lines/music wholesale):
  |     _otr_scifi_codex.py::_assemble_ledger (P0-P5 compiler; fact_ids minted here, DROPPED here too)
  |     _otr_scifi_fable2.py, _otr_shakespeare_sources.py, _otr_public_domain_sources.py, ...
  |-- content-authorship receipt: _otr_content_authorship.py::stamp_receipt -> meta.content_authorship
  |     (voiced lines[].text only -- see section 5)
  |-- writer-tail cleanup: _otr_ledger_cleanup.py, _otr_ledger_consistency.py, _otr_ledger_scrub.py
  |-- readiness/telemetry: _otr_readiness.py (Phase 7 text_for_tts), _otr_word_delivery.py
  `-- repeated led.save() at 11 call sites through the writer's run (4129..6845)
                                        |
                                        v  wire: script_json  (disk: <ep>_ledger.json, via Ledger.save())
================================================================================================
FREEZE CASCADE -- SCHEMA/SHAPE VALIDATION + METADATA STAMP, NOT AN IMMUTABILITY BOUNDARY
================================================================================================
OTR_LedgerFreezeCascade.run() (OTR_LedgerFreezeCascade.py:206-431)
  `-- run_freeze_cascade() (_otr_freeze_cascade.py:709-1149), same in-memory dict throughout, no copy:
        Phase 0 gap audit (pre, warn-only) -> freeze-policy resolution -> [inline-safety-cleanup XOR
        read-only structural check, per bank] -> D3 pre-freeze role sweep -> Phase 7 audio readiness ->
        text-metrics refresh -> Phase 8 video readiness -> [content_owned_readonly banks only: entry/exit
        SHA re-compare, terminal-fails on divergence] -> Phase 10 gap audit (post) + SEAL:
              meta.cleanup_locked = True        <-- written once, READ BY ZERO production code paths
              meta.freeze_timestamp = ISO-8601
              meta.freeze_verdict = frozen_clean | frozen_with_warns | needs_full_rerun
        -> post-seal verdict refinement (STILL mutating meta after the "seal") -> capability receipt
        -> _persist_cascade_meta() -> led.save()
                                        |
                                        v  wire: v2_ledger_json / script_json   (disk: singleton via Ledger.save())
================================================================================================
POST-FREEZE AUDIO EXECUTION -- ONLY ONE NODE CHECKS THE FREEZE FLAG; THE SAME NODE ALSO REWRITES
A NARRATIVE FIELD THE FLAG WAS SUPPOSED TO PROTECT
================================================================================================
OTR_CastLock (cast_lock.py:177-319)
  |-- _enforce_freeze_gate(meta): halts on freeze_verdict=="needs_full_rerun"
  |     (bypass: OTR_BYPASS_FREEZE_HALT=1, no downstream re-gate)               <-- ONLY gate in the chain
  |-- cast[].voice_preset/voice_route_id/voice_spec/presentation_gender/... stamped
  |-- lines[i].speaker_role REWRITTEN "character"->"announcer" for mis-stamped announcer rows (silent)
  `-- stamp_durable(sections={"cast":...}) -> disk (singleton)
        |
        v  wire: ledger_json
OTR_BatchCharacterVoices / OTR_AnnouncerVoice (_otr_voice_node_common.py, shared base)
  `-- per-line durable stamp (tts_engine, render_ms, audio_sample_hash, ...) to meta.paths.ledger_path
        (a THIRD, independently-resolved ledger file path -- not the in-flight singleton path)
OTR_StableAudioTheme -- renders cue WAVs, stamps meta.music_engine durably; cue_manifest_json is wire-only
        until EpisodeAssembler reconciles it into ledger.music[]
OTR_SceneSequencer (scene_sequencer.py:793-1155) -- fail-loud on unresolved lines/bus mismatch; writes
        start_s/dur_s/start_s_space (+ speaker_role REASSERT, unconditional overwrite) to the ON-DISK
        singleton copy -- a separate load from the script_json it was handed
OTR_AudioEnhance -- pure DSP; only phase/gate metadata written; ZERO TEST COVERAGE (section 8)
OTR_EpisodeAssembler (scene_sequencer.py:1229-1936) -- terminal audio sink:
  |-- shifts lines[]/clips[]/music[] start_s from scene_audio -> master_mix space
  |-- APPENDS synthetic music_open/music_inter/music_close rows to lines[]
  |-- RE-SORTS the entire lines[] array by start_s, reassigns _led["lines"]
  |-- stamps audio.master_audio_sha256 / audio.ledger_frozen=True
  `-- emits audio_done (the topological gate for the deferred video/FLUX branch)
                                        |
                                        v  wire: audio_done + script_json/patched_ledger_json
================================================================================================
POST-FREEZE VISUAL PIPELINE -- NO NODE HERE CHECKS THE FREEZE FLAG AT ALL; MOST MUTATIONS ARE
WIRE-ONLY OR PURELY IN-MEMORY-AND-DISCARDED, NOT DURABLE
================================================================================================
OTR_ShotLock (otr_shot_lock.py:1782-1942)
  |-- overlay_audio_timing(strict=True): filters/replaces/re-sorts lines[] AGAIN, reassigns
  |-- stamps ledger["video"] wire-only (patched_ledger_json) -- NEVER calls save_ledger_safe/stamp_durable
  `-- no freeze-flag check
OTR_MetaBriefImagePromptGen -- read-only; emits a separate image_prompts_json (result-manifest)
OTR_ImageGenDispatcher (otr_image_gen_dispatcher.py:838-1721)
  |-- ledger["images"]={...} + meta.image_engines -> stamp_durable(sections={"images":...})  DURABLE, LOUD
  |-- portrait_ledger.stamp_portrait() stamps cast[i].portrait_content_hash on the LOCAL dict only --
  |     NOT included in the stamp_durable sections={"images":...} call -- likely wire-only durability
  |     (new finding, this pass; see section 3)
  `-- also emits patched_ledger_json (wire) carrying the same images section redundantly
OTR_VideoRenderBatch / render_driver.py (otr_video_render_batch.py:368-495)
  |-- route resolution, still-spine repair, motion-clause pass, per-shot render (deep-copied ledger inside
  |     run_episode) -- ALL four of these mutate an in-memory copy that is NEVER persisted or emitted
  |-- build_clip_manifest -> clip_manifest_json (result-manifest, not the ledger)
  |-- _stamp_render_engines_meta -> stamp_durable(meta.render_engines)          DURABLE, LOUD
  `-- _stamp_audio_motion_profiles -> direct save_ledger_safe seam              DURABLE, fail-soft
19 video-engine adapters (eng_*.py) -- render_clip() returns a local clip dict only; ZERO ledger I/O
OTR_SilentComposite / OTR_SceneAwareScopes -- consume clip_manifest_json only; ZERO ledger I/O
OTR_PostUpscaleProcgenBlend -- on successful blend only: direct save_ledger_safe seam, fail-soft,
        stamps final_video_path + meta.post_upscale_blend
                                        |
                                        v  clip_manifest_json + video streams
================================================================================================
TERMINAL DELIVERY -- CAPTIONS AND CREDITS ARE READ-ONLY; ONLY THE MUX NODE WRITES, AND ITS WRITE
IS BEST-EFFORT, ATTEMPTED AFTER THE DELIVERABLE IS ALREADY PUBLISHED
================================================================================================
OTR_SignalLostVideo (video_engine.py:2618-2673) -- rename_episode() trigger: episode_id finalized,
        every episode-local absolute string path rewritten repo-wide (not a field allow-list -- a
        path-containment walk); wrapped in a broad try/except that only WARNS on failure -- render
        continues either way
OTR_CaptionBurn -- reads the ledger, burns a .ass + new mp4; NO ledger persistence call anywhere
        (confirmed: the claim "stamps meta.phase_ms.caption_burn" does not exist anywhere in the repo)
OTR_CreditsRoll -- reads the in-memory singleton (get_ledger(), no disk I/O), strict no-fallback on 6
        meta fields (raises CreditsDataError); appends a credits mp4 tail; NO ledger persistence call
        anywhere (the claim "stamps meta.credits_receipt" does not exist anywhere in the repo)
OTR_MasterAudioMux (otr_master_audio_mux.py:551-613) -- the terminal step, in REAL EXECUTION ORDER:
  1. mux_master_audio()      -- writes the archival final mp4; fail-closed (raises ValueError/OSError)
  2. _publish_to_obs(final)  -- writes otr/obs/<ep>.mp4; fail-closed (raises OSError)
  3. report.append("obs_publish OK -> ...")     <-- recorded as true HERE, before any ledger write
  4. _stamp_terminal_paths() -- the ONLY ledger mutation in the whole terminal cluster; wrapped in its
        own try/except that can never raise and an `if not save_ledger_safe(...): return "...failed..."`
        guard that also never raises -- ALWAYS returns a plain string, logged at INFO, never reaches the
        function's one fail-closed handler (except (ValueError, OSError), step 1/2 only)
  `-- return (final, "OTR_MasterAudioMux OK -> " + final + ...)   <-- unconditionally reports success
```

---

## 3. Exhaustive downstream consumer matrix

`R/D/M/S/P` = read / derive / mutate / serialize / publish. `Durability`: **disk** (singleton or direct
`save_ledger_safe` seam, survives a process restart) / **wire** (only inside a `*_json` string handed to
the next node's input socket) / **manifest** (a separate result object, not the ledger) / **none**.

### Ledger construction, freeze, and core plumbing

| Component | File : function/class : lines | Fields touched | R/D/M/S/P | Phase | Requiredness / fallback | Durability | Test |
|---|---|---|---|---|---|---|---|
| Ledger constructor | `production_ledger.py::Ledger.__init__` L705-731 | fresh empty schema (`cast/scenes/shots/beats/lines/music/clips: []`, `schema_version`) | mutate | draft | required | disk on first `.save()` | -- |
| **`OTR_LedgerScriptWriter`** -- the primary producer node, **not on AGY's consumer list at all** | `OTR_LedgerScriptWriter.py::OTR_LedgerScriptWriter` L2866+, 11 `led.save()` sites (4129-6845) | writes essentially every pre-freeze field: `cast`, `beats`, `lines`, `meta.{cast_status,source_bank,bank_roll,text_metrics,content_authorship,cast_contract,...}` | derive+mutate+serialize+publish | draft | required | disk (11 saves) | 89 files reference it by name; the one I opened (`test_writer_stamps_episode_title.py`) is a **static source-string assertion**, not a live `.run()` call -- coverage depth on the remaining 88 is unverified this pass |
| Cast lock (pre-freeze first pass) | `cast_lock.py::CastLock.lock` L280-319 -> `stamp_durable` | `cast[]`, `meta.cast_lock_revision` | mutate+publish | pre-freeze | required | disk | `tests/test_credits_s2_durable_stamps.py:46-70` |
| Casting engine | `_otr_casting.py::lock_cast` etc. L701-1868 | builds `cast[]` rows locally, passed to `cast_lock.py` | derive+mutate | pre-freeze | required | owned by caller | -- |
| SciFi codex assembly | `_otr_scifi_codex.py::_assemble_ledger` L3151-3262 | `cast/scenes/shots/beats/lines/music/clips` wholesale via `led.set_*`; **drops `fact_ids`** (present on the internal `BeatPlanV4`/`RadioScoreDraftBeatV4` models, absent from the six-key `beats[]` dict comprehension at L3200 and from `lines[]`) | mutate | pre-freeze | required for this lane | disk (caller's save) | `tests/test_scifi_codex_lane.py` (not re-opened) |
| Fable2 assembly | `_otr_scifi_fable2.py` L2727/2919/2921 | `cast`, `scenes`, `beats` | mutate | pre-freeze | required for this lane | disk | not opened |
| Content-authorship receipt | `_otr_content_authorship.py::build_receipt/stamp_receipt` L80-217 | `meta.content_authorship` -- only **voiced** `lines[].{line_id,text}` (filters `skip`, `skip_tts`, non-sayable text; `_voiced_rows`, L28-61) | derive+mutate+publish | pre-freeze | conditional (content-owned lanes) | disk | `tests/test_content_authorship.py` |
| Freeze orchestrator | `_otr_freeze_cascade.py::run_freeze_cascade` L709-1149 | `meta.freeze_policy`, `meta.freeze_capability_receipt`, `meta.role_coercions`, `meta.word_delivery_telemetry`, `meta.freeze_warn_taxonomy`, `meta.freeze_disposition`, `meta.freeze_phase_telemetry` | mutate+publish | Phases 0/7/8/10 | required | disk, every exit | -- |
| Phase 10 seal | `_otr_ledger_freeze.py::phase_10_gap_audit_post_and_freeze` L901-962 | `meta.{gap_audit_post,cleanup_locked,freeze_timestamp,freeze_verdict}` | mutate | Phase 10 | required, hard gate | disk (via cascade) | `tests/test_lfc_phase_0_10_gap_audit.py` |
| ComfyUI node wrapper | `OTR_LedgerFreezeCascade.py::run` L206-431 | invokes the above; `meta.freeze_unload_ok` | mutate+serialize | node boundary | required | disk | not opened |
| Cast-contract module | `_otr_cast_contract.py` (whole file) | would touch `cast_contract`/`cast_contract_version` | **CHECKED_NOT_A_CONSUMER of the live pipeline** | n/a | n/a | n/a -- own docstring: "not yet wired into story_orchestrator.py or production_ledger.py"; its only importer (`_otr_cast_repair.py`) has zero production callers either | `tests/test_cast_repair.py` exercises it in isolation only |
| Blind-overwrite save | `_otr_ledger.py::save_ledger_safe` L335-453 | `schema_version` (**preserves a foreign version if present**), `meta.schema_version`, `meta.paths` | serialize+publish | any | required for 6 named callers | disk, atomic | -- |
| Merge-aware save | `production_ledger.py::Ledger.save` / `_merge_with_disk` L1432-1663 | full ledger, row-keyed merge-forward of durable render fields; **always stamps `schema_version` = current, regardless of what was on disk or in memory** | serialize+publish | any | required (primary path) | disk, atomic | -- |
| Durable stamp helper | `production_ledger.py::stamp_durable` L527-571 | arbitrary `sections`/`meta_updates`, delegates to `Ledger.save()` | mutate+serialize+publish | pre/post-freeze | required for 4+ named call sites | disk / in-memory-only in `OTR_TEST_MODE=1` | `tests/test_credits_s2_durable_stamps.py` |
| Freeze schema gate | `_otr_ledger_freeze.py::_check_meta_invariants` L597-613 | reads `schema_version`, **hard-fails (`FreezeAssertionError`) on anything but the current literal** -- a THIRD, independently-enforced schema policy, in direct tension with `save_ledger_safe`'s deliberate foreign-version preservation | read (hard gate) | Phase 10 | required, CRITICAL | n/a | `tests/test_lfc_phase_0_10_gap_audit.py` |
| Resume / cross-process discovery | `_otr_ledger.py::in_flight_ledger_path` L460-531 | resolves via the in-process singleton if live, else a pure **mtime walk** of `<ep>/audio/*_ledger.json` -- **zero schema-version or content check** | read | any | best-effort | n/a | historical bug note in the code itself (`BUG-LOCAL-021`) |
| Shared read-only consumer library | `_otr_ledger_consumers.py` (whole file, 313 lines) | `load_ledger`, `iter_lines`, `cast_lookup`, `voice_assignments_from_cast`, `audit_post_freeze_writeback` | read/derive only, **zero mutation anywhere** | post-freeze | n/a | none (pure) | `tests/test_otr_ledger_consumers.py` |

### Cast lock -> voice -> music -> sequencing -> assembly

| Component | File : function : lines | Fields touched | R/D/M/S/P | Phase | Requiredness / fallback | Durability | Freeze-gate check | Test |
|---|---|---|---|---|---|---|---|---|
| **`OTR_CastLock`** | `cast_lock.py::CastLock.lock` L177-319; rewrite at L522-523 | reads `meta.freeze_verdict`, `cast[]`, `lines[]`; writes `cast[].{voice_preset,voice_route_id,voice_spec,presentation_gender,tts_model,...}`, `meta.cast_lock_revision`/`cast_voice_policy`/`voice_bank_id`/..., **`lines[i].speaker_role`** (announcer reroute) | read/derive/mutate/serialize/publish | post-freeze, first | **required, only freeze-gate enforcer** | disk (`stamp_durable(sections={"cast":...})`) + wire | **YES** -- `_enforce_freeze_gate`, L322-352; bypass `OTR_BYPASS_FREEZE_HALT=1` | `tests/test_bark_freeze_halt_bypass.py` (genuinely calls `CastLock().lock()`, asserts the raise + bypass) |
| `OTR_BatchCharacterVoices` | `_otr_voice_node_common.py::generate/_render_per_line` L432-1234 | `cast[]` voice fields (read), `lines[]` filtered `speaker_role=="character"` | read/derive/(conditional)mutate | post-freeze | conditional: 0 in-role lines short-circuits; unresolvable route raises | disk, per-line, via `meta.paths.ledger_path` (a third, independent path) | NO | `tests/test_batch_character_voices.py` |
| `OTR_AnnouncerVoice` | same base, `speaker_role=="announcer"` filter | same mechanism | same | post-freeze | same | same third path | NO | `tests/test_announcer_voice.py` |
| `OTR_StableAudioTheme` | `stable_audio_theme.py::generate` L130-379 | `music[]` cue prompts (read), WAV files (disk), `meta.music_engine` (durable) | read/derive/serialize/publish | post-freeze | conditional: empty cue set never raises | disk (WAV + meta) + wire (`cue_manifest_json`, not yet in `music[]`) | NO | `tests/test_stable_audio_theme.py` |
| `OTR_SceneSequencer` | `scene_sequencer.py::sequence` L793-1155 | all `lines[]` (no role filter), `tts_audio_clips` | read/derive/mutate(disk copy)/serialize | post-freeze | **fail-loud**: unknown `speaker_role` raises; missing clip raises; bus-count mismatch raises | disk (best-effort write-back, try/except-warn only) | NO | `tests/test_sequencer_ledger.py` (mocks `load_ledger_safe` -- see section 8) |
| `OTR_AudioEnhance` | `audio_enhance.py::enhance` L324-473 | AUDIO tensor only; no ledger content read | derive/mutate(disk copy, metadata only) | post-freeze | best-effort | disk (best-effort) | NO | **NONE FOUND** -- zero test files reference this node at all |
| **`OTR_EpisodeAssembler`** | `scene_sequencer.py::assemble` L1229-1936 | on-disk singleton copy (no `script_json`/`ledger_json` input at all): shifts `lines[]/clips[]/music[]` start_s; **appends + re-sorts `lines[]`**; stamps `audio.master_audio_sha256`/`ledger_frozen=True` | read/derive/**mutate(structural)**/serialize/publish | post-freeze, terminal audio sink | best-effort write-back; master WAV save itself best-effort | disk (best-effort) | NO | `tests/test_sequencer_ledger.py::test_episode_assembler_materializes_bookends_and_mirrors_by_placement` (real call, asserts append; **does not** assert final sort order). `tests/test_episode_assembler_offset_shift.py` does **NOT** call the real class -- tests a duplicated local reimplementation only |

### Visual pipeline

| Component | File : function : lines | Fields / classification | R/D/M/S/P | Phase | Requiredness / fallback | Durability | Test |
|---|---|---|---|---|---|---|---|
| `OTR_ShotLock` | `otr_shot_lock.py::lock` L1782-1942 | `ledger["video"]`, `meta.video_revision`; `overlay_audio_timing(strict=True)` filters/replaces/re-sorts `lines[]` again | mutate+serialize | post-freeze | required, raises on route mismatch | **wire-only** (never calls `save_ledger_safe`/`stamp_durable`) | none found (`OTRShotLock`/`otr_shot_lock` not imported by any test) |
| `OTR_MetaBriefImagePromptGen` | `otr_meta_brief_image_prompt.py::generate` L2261-2324 | reads `meta/cast/lines`; emits separate `image_prompts_json` | read/derive | post-freeze | required inputs, LLM-fallback to template | none (manifest, wire) | none found |
| `OTR_ImageGenDispatcher` | `otr_image_gen_dispatcher.py::dispatch_images` L838-1592 | `ledger["images"]`, `meta.image_engines` -> `stamp_durable(sections={"images":...})`; **also** `portrait_ledger.stamp_portrait()` (L1335) sets `cast[i].portrait_content_hash` on the same local dict | mutate+serialize(wire)+publish(durable, `images`/`meta` only) | post-freeze | required, LOUD (`LedgerStampError` propagates) | disk (singleton, `images` section) + wire; **`cast[i].portrait_content_hash` is NOT in the `stamp_durable` `sections` argument -- likely wire-only durability, see finding below** | `tests/test_credits_s2_durable_stamps.py::test_image_dispatcher_stamps_singleton` |
| `OTR_VideoRenderBatch` / `render_driver.py` | `otr_video_render_batch.py::_render_episode` L368-495 | route resolution, still-spine repair, motion-clause pass, per-shot render (`run_episode`, deep-copies the ledger) -- **all four discarded, never persisted or emitted**; `build_clip_manifest` -> result-manifest; `_stamp_render_engines_meta` -> `stamp_durable(meta.render_engines)`; `_stamp_audio_motion_profiles` -> direct `save_ledger_safe` seam | mutate (mostly transient) + publish (2 of ~6 passes) | post-freeze | render-engines stamp required/LOUD; audio-motion stamp optional/fail-soft (explicit "must NEVER fail the render" docstring) | disk for 2 of 6 mutation passes; 4 discarded in-memory | `tests/test_credits_s2_durable_stamps.py`, `tests/test_audio_motion_foldin.py`, `tests/test_route_freeze*.py`, `tests/test_still_spine_helpers.py`, `tests/test_video_render_driver*.py` |
| 19 video-engine adapters (`eng_*.py`) | `render_clip()` per file | returns a local clip dict only | none | n/a | n/a | **none** -- zero ledger I/O in any of the 19 | per-engine test files (render-output shape only) |
| `acceptance.py`/`frame_contract.py`/`coverage_plan.py`/`registry.py` | various | `acceptance.py` reads `ledger` for QA grading only (zero write hits); the other three never take a `ledger` parameter | read-only or none | n/a | n/a | none | `tests/test_wire_w5_acceptance_grader.py`, `tests/test_multiclip_coverage_stamp.py` |
| `OTR_SilentComposite` | `otr_silent_composite.py::composite` L1439+ | reads `clip_manifest_json` only | none | n/a | n/a | **CHECKED_NOT_A_CONSUMER** | none found |
| `OTR_PostUpscaleProcgenBlend` | `otr_post_upscale_procgen_blend.py::blend` L829-1059, helper L156-232 | `final_video_path`, `meta.post_upscale_blend.*` -- **only on a successful real blend** | publish | post-freeze, terminal video | optional/fail-soft, never raises | disk (direct seam) | `tests/test_post_upscale_procgen_blend.py` (4 scenarios opened) |
| `OTR_SceneAwareScopes` | `otr_scene_aware_scopes.py::render_scopes` L413+ | reads `clip_manifest_json` only | none | n/a | n/a | **CHECKED_NOT_A_CONSUMER** | `tests/test_video_scene_aware_scopes.py` |
| **`_otr_shared/portrait_ledger.py::stamp_portrait`** -- newly found this pass, outside all 7 tracers' declared scope | called only from `otr_image_gen_dispatcher.py:1335` | `entry["portrait_content_hash"] = h` on the `cast[i]` dict passed by reference | mutate | post-freeze | conditional (`require_cast_entry`) | **none confirmed** -- the caller's only persistence call (`stamp_durable(sections={"images":...})`) does not include `cast`; I found zero callers anywhere of the module's own read side (`resolve_portrait_path`/`portrait_hash_for_char`), so this looks like a live write with no confirmed live reader today -- an orphaned mechanism, not a proven bug | no test found referencing `portrait_ledger`/`stamp_portrait` |

### Terminal delivery

| Component | File : function : lines | Fields / classification | R/D/M/S/P | Phase | Requiredness / fallback | Durability | Test |
|---|---|---|---|---|---|---|---|
| `OTR_SignalLostVideo` rename trigger | `video_engine.py::render_video` L2618-2673 -> `production_ledger.py::Ledger.rename_episode` L735-970+ | `episode_id`; **every episode-local absolute string value repo-wide** (path-containment walk, not a field allow-list -- proven by test at `test_production_ledger.py:301-394` reaching an arbitrarily-named nested field); `meta.paths.*` re-derived on next `.save()` | mutate (structural identity) | rename boundary | conditional -- whole block wrapped in a broad `except Exception` that only **warns**; a rename/save failure does **not** stop the render | disk (dir move + ledger move + atomic write) when it succeeds | `tests/test_production_ledger.py::test_rename_rebases_shared_six_bank_episode_paths`, `::test_path_rebase_handles_windows_slashes_and_component_boundaries` (real). No test drives a rename failure through `render_video` itself |
| `OTR_CaptionBurn` | `otr_caption_burn.py::burn` L304-354, `_resolve_ledger_path` L134-178 | reads the ledger; burns a `.ass` + new mp4 | read/derive(video file) | post-freeze | optional, 3-tier path fallback | **none** -- confirmed no `save_ledger_safe`/`stamp_durable`/`.save()` call anywhere in the file; the string `phase_ms.caption_burn` does not exist anywhere in the repo | `tests/test_caption_burn_cw4.py`, `tests/test_caption_burn_fails_closed_on_title.py` |
| `OTR_CreditsRoll` | `otr_credits_roll.py::roll` L1479-1558, `build_credits_layout` L266-390 | reads `get_ledger()` (in-memory singleton, no disk I/O); strict no-fallback on 6 `meta` fields + `cast` (raises `CreditsDataError`) | read/derive(video+PNG files) | post-freeze | **required**, no-fallback contract | **none** -- confirmed no persistence call anywhere; `meta.credits_receipt` does not exist anywhere in the repo | `tests/test_credits_roll_spec.py` |
| **`OTR_MasterAudioMux`** | `otr_master_audio_mux.py::mux` L551-613, `_publish_to_obs` L458-498, `_stamp_terminal_paths` L517-544 | `final_audio_path`, `final_video_path`, `meta.obs_final_path`, `meta.paths.obs_final` | mutate+publish(file) | post-freeze, terminal | obs-publish itself fail-closed (raises `OSError`); **the ledger stamp is best-effort and can never raise** -- see section 2 for the exact ordering and swallow mechanism | disk when it succeeds; **silently absent when it fails, with no trace above INFO level** | `tests/test_video_render_path_cw4.py:287-322` (direct stamp call, real save), `:326-356` (full `.mux()`, asserts `"obs_publish OK"`). **No test drives a `_stamp_terminal_paths` failure through the full `.mux()` and asserts the run still reports success** -- confirmed gap |

---

## 4. Chronological mutation ledger (draft creation through terminal audit)

1. `Ledger.__init__` -- fresh empty schema.
2. `_otr_casting.py::lock_cast` -- builds `cast[]` locally.
3. `cast_lock.py` (pre-freeze pass) -> `stamp_durable` -- `cast[]` + voice-policy meta durably stamped.
4. Story-pack overlay (`_otr_scifi_codex.py::_assemble_ledger` or bank equivalent) -- `cast/scenes/shots/beats/lines/music/clips` written wholesale; `fact_ids` dropped here.
5. `_otr_content_authorship.py::stamp_receipt` -- `meta.content_authorship` (voiced lines only).
6. Freeze-cascade entry: VRAM telemetry, Phase 0 gap audit (pre, warn-only), freeze-policy resolution, entry-hash capture.
7. D3 pre-freeze `speaker_role` coercion sweep (inline-safety-cleanup banks only) -> `meta.role_coercions`.
8. Phase 7 audio readiness -> `lines[].text_for_tts`.
9. Text-metrics refresh -> `meta.{character,announcer,total}_word_count`.
10. Phase 8 video readiness -> `meta.video_readiness`.
11. Readonly-policy mutation-detection check (`content_owned_readonly` banks only) -- entry-vs-exit SHA re-compare, terminal-fails on divergence.
12. **Phase 10 gap audit (post) + seal** -- `meta.{gap_audit_post,cleanup_locked=True,freeze_timestamp,freeze_verdict}`. This is the boundary AGY calls "strictly frozen." Per section 1, it is unenforced from here on.
13. Post-seal verdict refinement -- `meta.freeze_warn_taxonomy`, possible upgrade of `freeze_verdict`, **still mutating `meta` after the "seal."**
14. Capability receipt, disposition/telemetry stamps, `_persist_cascade_meta` -> disk.
15. **`OTR_CastLock`** -- freeze-gate enforced; `cast[]` voice identity stamped; **`lines[i].speaker_role` rewritten** for mis-stamped announcer rows; `stamp_durable(sections={"cast":...})`.
16. `OTR_BatchCharacterVoices` / `OTR_AnnouncerVoice` -- per-line durable stamps to a third, independent ledger path.
17. `OTR_StableAudioTheme` -- cue WAVs to disk; `meta.music_engine` durable; `cue_manifest_json` wire-only.
18. `OTR_SceneSequencer` -- `lines[].{start_s,dur_s,start_s_space,speaker_role(reassert)}` to the on-disk singleton copy; fail-loud on any unresolved line.
19. `OTR_AudioEnhance` -- phase/gate metadata only; zero content read.
20. **`OTR_EpisodeAssembler`** -- `music[]` reconciled into the ledger; `lines[]/clips[]/music[]` shifted to master-mix space; **synthetic music rows appended to `lines[]`; entire array re-sorted and reassigned**; `audio.master_audio_sha256`/`ledger_frozen=True` stamped; `audio_done` emitted.
21. `OTR_SignalLostVideo` -- procgen base video written; **`rename_episode()`** fires (episode_id finalized, every episode-local path rewritten repo-wide); `set_final_paths()`; `meta.procgen_path`; whole block fail-soft (warn-only) on any error.
22. `OTR_ShotLock` -- `overlay_audio_timing(strict=True)` filters/replaces/re-sorts `lines[]` a third time; `ledger["video"]` stamped **wire-only**.
23. `OTR_MetaBriefImagePromptGen` -- read-only; emits `image_prompts_json`.
24. `OTR_ImageGenDispatcher` -- `ledger["images"]`/`meta.image_engines` durably stamped (LOUD); `cast[i].portrait_content_hash` stamped on the local dict only (durability unconfirmed, see section 3).
25. `OTR_VideoRenderBatch` -- route resolution / still-spine repair / motion-clause / per-shot render all transient and discarded; `clip_manifest_json` built; `meta.render_engines` durably stamped (LOUD); `audio_motion_profiles` durably stamped (fail-soft).
26. `OTR_SilentComposite` / `OTR_SceneAwareScopes` -- zero ledger interaction.
27. `OTR_PostUpscaleProcgenBlend` -- on success only: `final_video_path`/`meta.post_upscale_blend` via direct seam, fail-soft.
28. `OTR_CaptionBurn` -- read-only; no ledger mutation.
29. `OTR_CreditsRoll` -- read-only; no ledger mutation.
30. **`OTR_MasterAudioMux`** -- archival mux (fail-closed) -> OBS publish (fail-closed, `"obs_publish OK"` recorded here) -> **`_stamp_terminal_paths()`** (the only mutation in this whole cluster: `final_audio_path`, `final_video_path`, `meta.obs_final_path`; best-effort, can never raise, failure invisible above INFO level) -> janitor sweep (fail-soft, unrelated).

---

## 5. Field-ownership table

**Immutable authored story truth** *(intended; currently only weakly/inconsistently enforced -- see
section 1)*: `cast[].{char_id, name, cast_role/presentation identity}`, `scenes[]`, `beats[].{goal,
conflict, emotional_shift, target_words, speaker}`, `lines[].{line_id, char_id, scene_id, shot_id,
speaker, speaker_role, text}` for real dialogue rows. **Confirmed live counter-examples**: `speaker_role`
rewritten by `cast_lock.py:523`; the whole `lines[]` array appended-to and re-sorted twice
(`EpisodeAssembler`, `ShotLock`'s `overlay_audio_timing`).

**Derived production state and receipts** *(legitimately mutable post-freeze)*: `cast[].{voice_preset,
voice_route_id, voice_spec, presentation_gender, tts_model, portrait_content_hash}`; `lines[].{start_s,
dur_s, start_s_space, tts_engine, render_ms, audio_sample_hash, sample_rate, voice_route_id,
audio_cache_key, audio_sha256, provider_model_id}`; `music[].{wav_path, start_s, dur_s, cue_spec_sha256,
music_render_status}`; `video.*` (whole section, ShotLock-owned, wire-only); `images.*` (whole section,
ImageGenDispatcher-owned, durable); `clips[].*`; `audio_motion_profiles[]`; `audio_gates[]`;
`transitions[]`; `meta.{phase_ms.*, render_engines, image_engines, music_engine, cast_lock_revision,
cast_voice_policy, voice_bank_id, video_revision, image_gen_receipt}`.

**Renameable / path identity**: `episode_id`; every `*_path`/`*_dir` field anywhere in the tree (rewritten
en masse by `rename_episode`'s path-containment walk, not a named list); `meta.paths.*`; `meta.title_card_plan`.

**Telemetry**: `meta.{vram_at_cascade_entry_gb, word_delivery_telemetry, text_metrics, gap_audit_pre,
gap_audit_post, freeze_phase_telemetry, freeze_capability_receipt, git_commit, vram_test_results[]}`.

**Final delivery seal** *(the weakest link -- see section 1.7, recommendation 6)*: `final_audio_path`,
`final_video_path`, `meta.obs_final_path` -- stamped by a best-effort call that can silently no-op even
after the deliverable is already published. `meta.credits_receipt` and `meta.phase_ms.caption_burn`,
despite appearing in AGY's report, **do not exist anywhere in the codebase** (section 7).

---

## 6. Referential-integrity, ordering, cardinality, and version/migration rules

- **Schema-version policy is internally inconsistent across three independent gates**: `save_ledger_safe`
  deliberately *preserves* a foreign/older `schema_version` if one is already present (a documented
  anti-regression policy, `_otr_ledger.py:369-381`, protecting ledgers from being silently reclassified);
  `Ledger.save()`/`stamp_durable` *always* stamp the current literal, unconditionally; `_otr_ledger_freeze.py`
  *hard-fails* Phase 10 on anything but an exact match to the current literal. A ledger that legitimately
  took the first path can be legitimately rejected by the third if it is ever re-run through the cascade.
- **Two structurally different merge policies coexist**: `save_ledger_safe` is a blind full overwrite of
  whatever the caller's in-memory dict already contains (never reads the on-disk file first);
  `Ledger.save()`/`_merge_with_disk` performs a real field/row-level merge (top-level preserve-list,
  per-key `meta` merge, row-keyed durable-field copy-forward gated on a content-identity hash). Which path a
  given writer chooses determines whether concurrent, out-of-band durable fields survive a save.
- **`line_id` uniqueness is enforced** (G8 gap-audit gate, confirmed both by `_otr_ledger_freeze.py` reading
  and by `tests/test_g8_line_id_uniqueness.py`), but only at Phase 10 -- nothing re-checks it after
  `EpisodeAssembler`/`ShotLock` mint and append new `music_<cue>_NNN`-namespaced rows post-freeze (the
  namespace is designed to avoid collision with writer-assigned `l00N` IDs, but this is convention, not an
  enforced invariant on the appended rows).
- **`fact_ids` referential closure is enforced only inside the SciFi codex's own internal generation
  contract** (`compile_radio_score_draft`, checks uniqueness + existence in the accepted fact set) and is
  never re-checked once the score is materialized into the ledger, because the field does not survive
  materialization at all (section 1). The Phase-10 gap-audit's required-top-level-list check
  (`_REQUIRED_TOP_LEVEL_LISTS`) does not mention `fact_ids`/`fact_index`.
- **`char_id="announcer"` sentinel vs. a real cast row `char_id`**: production's `cast_lock.py` maintains a
  separate `announcer_ids` set alongside real cast `char_id`s specifically to resolve this sentinel
  (`is_ann = cid in announcer_ids or (row.name == "ANNOUNCER")`, `cast_lock.py:518-521`) -- so production
  code does account for the alias, but the exact resolution mechanism for `announcer_ids` itself was not
  independently traced in this pass (**UNKNOWN** -- would need a dedicated read of wherever `announcer_ids`
  is populated). Separately and on the Story Lab side, agent G found the *clean control* fixture's own
  `char_id="announcer"` line rows do not match its own `cast[0].char_id="c01"` -- i.e. even the "good"
  reference episode would fail a strict `char_id`-in-`cast[]` closure check as written in the Story Lab's
  own (currently unwired) `ledger_contract.py`. This is a genuine identity-assumption gap that predates and
  is independent of the freeze-boundary question.
- **`line_id`/`beat_id` are the same literal value in the legacy control fixture** (Story Lab side, agent
  G) -- the pre-P3/P5-compiler shape has no independent line-vs-beat ID namespace at all, which the Story
  Lab's newer `ledger_contract.py` schema assumes is always true and is not.
- **Cardinality of `lines[]` is not stable across the pipeline**: the writer/freeze-cascade's line count is
  the one Phase 10's gap-audit validates; `EpisodeAssembler` and `ShotLock` each independently add rows to
  the same array afterward. Any offline script or test that assumes `len(lines)` is fixed post-freeze must
  filter on `mirrored_from is None` -- confirmed as the intended convention by `_otr_scifi_codex.py`'s and
  `EpisodeAssembler`'s own inline comments, but not independently proven against every offline script in
  this pass (marked `UNKNOWN` by the test-inventory agent, section 8).
- **Three independent "which ledger file is current" resolution seams exist simultaneously**:
  (1) the process-singleton (`production_ledger.peek_ledger()`), (2) `in_flight_ledger_path()`'s mtime-walk
  fallback (zero schema/content check), (3) `meta.paths.ledger_path` (used by the per-line voice stamps,
  resolved independently of the other two). A node using seam 2 or 3 does not see writes made through seam
  1 in the same process unless it re-reads disk. This is the concrete mechanism behind several of the
  "durable vs. wire vs. discarded" splits documented in section 3.

---

## 7. AGY claim review table

`AGREE` / `PARTIAL` / `DISAGREE`, each with the corrected language and the exact evidence that decided it.

| # | AGY claim | Verdict | Corrected language / evidence |
|---|---|---|---|
| 1 | Executive verdict: "the narrative/structural plane ... is strictly frozen at Phase 10." | **DISAGREE** | Phase 10 is a schema validator plus a metadata stamp; nothing reads `meta.cleanup_locked` to block a write anywhere in the codebase (confirmed by a repo-wide grep -- zero readers). `cast_lock.py:522-523` rewrites `lines[].speaker_role`; `EpisodeAssembler` appends+re-sorts `lines[]`; `ShotLock.overlay_audio_timing(strict=True)` does so a third time -- all on live, name-checked production wiring. Both my independent steelman and refute agents, working from the raw code with no knowledge of each other, converged on **FALSE**. |
| 2 | The two-plane framing itself (narrative/structural plane vs. media-execution/telemetry plane). | **PARTIAL** | The distinction is real and useful, but the "narrative/structural plane" is not actually a plane with a boundary anything enforces -- it is one mutable dict that some nodes are more disciplined about than others. The corrected framing (section 1) treats "frozen" as a spectrum by field, not a hard boundary by phase. |
| 3 | `_otr_ledger_freeze.py:382-430` / `nodes/_otr_freeze_cascade.py:900-1120` / `nodes/_otr_ledger_freeze.py:720-960` as the freeze boundary's implementation. | **AGREE on file identity, PARTIAL on framing** | These are the right files and roughly the right line ranges (confirmed: `phase_10_gap_audit_post_and_freeze` is L901-962, not L720-960 as cited, though the surrounding module is correct). The framing that this constitutes "structural immutability" is the part that does not hold up (see #1). |
| 4 | `_sha256_content_authorship` "verifies" the freeze. | **PARTIAL** | Real function, real evidence-checking, but its actual coverage is narrower than the name implies: **voiced `lines[].text` only** (filtered by `skip`/`skip_tts`/sayability) -- never `cast`, `scenes`, `beats`, `shots`, `music`, or `speaker_role`. Confirmed by direct read of `_otr_content_authorship.py:28-95` and `_otr_freeze_cascade.py:214-233`. |
| 5 | The whole exhaustive consumer matrix (section 3 of AGY's report, ~22 rows). | **PARTIAL, materially incomplete** | Every node AGY names does exist and its file/line citations are largely accurate on spot-check. But AGY's matrix **omits the actual primary producer node, `OTR_LedgerScriptWriter`**, entirely -- a significant gap for a report whose stated purpose is an exhaustive consumer inventory. It also omits `OTR_VRAMContextTest` (a live diagnostic mutator with zero test coverage), `OTR_SaveToEpisodeWorkspace`, and `_otr_shared/portrait_ledger.py::stamp_portrait` (found this pass). |
| 6 | "`nodes/_otr_ledger_reviewer.py:apply_deterministic_cast_repairs` explicitly refuses to map character lines onto the announcer (BUG-LOCAL-276/271 fix)." | **DISAGREE, confirmed fabricated citation** | `nodes/_otr_ledger_reviewer.py` **does not exist anywhere in the repository** (confirmed: a full `nodes/*.py` listing plus a case-insensitive `review` grep across the whole tree returns zero matches under any name). Worse, the described behavior is the **opposite** of what the real code does: `cast_lock.py:522-523` actively **remaps** a mis-stamped character line onto the announcer role, in place, unguarded -- it is the single most damaging counter-example to AGY's own freeze claim, found independently by two different agents in this audit and personally re-verified by me. This is a serious citation defect, not a minor imprecision -- it invents a file and describes behavior contradicting the real code. |
| 7 | AGY's `OTR_CastLock` matrix row lists only voice fields as mutated, omitting `lines[].speaker_role` entirely. | **DISAGREE by omission** | CastLock does rewrite `speaker_role` post-freeze (`cast_lock.py:522-523`, section 1.3); this omission is what let AGY's "strictly frozen" framing stand uncontested in its own report. |
| 8 | Does `EpisodeAssembler` append music mirrors to and reorder `lines[]`? | **AGREE** | AGY's own contradiction #1 (section 6 of its report) states this correctly and in reasonable detail; I independently re-derived the same finding from the raw code and confirm it. |
| 9 | Do `SilentComposite`, `CaptionBurn`, `CreditsRoll`, and video-engine adapters persist ledger writes? | **DISAGREE for all four named categories** | AGY's own consumer-matrix rows list `OTR_SilentComposite` as "Mutates disk: stamps meta.phase_ms.silent_composite" and `OTR_CaptionBurn`/`OTR_CreditsRoll` as stamping `meta.phase_ms.caption_burn`/`meta.credits_receipt`. All three of those exact strings were searched for repo-wide and **do not exist anywhere in the codebase**. Confirmed by direct read of all three files: none of them calls `save_ledger_safe`, `stamp_durable`, or `.save()` anywhere. The video-engine adapters (19 files) also confirmed zero ledger I/O, consistent with AGY not claiming otherwise for them. |
| 10 | `OTR_PostUpscaleProcgenBlend` stamps `meta.phase_ms.post_upscale_procgen_blend`. | **PARTIAL** | It does durably stamp `meta.post_upscale_blend.*` (not the `phase_ms.*` key name AGY used) plus `final_video_path`, via the direct `save_ledger_safe` seam, on a successful blend only -- fail-soft otherwise. Substance close, exact field name off. |
| 11 | Are clip/shot/image mutations durable ledger writes, wire-only, or result-manifest changes? | **PARTIAL** | AGY's matrix presents these largely as durable stamps. The real picture (section 3) is a mix: `ShotLock`'s `video` section is wire-only (never persisted); most of `VideoRenderBatch`'s internal route/still/motion/per-shot mutations are transient and discarded entirely (never even wire-emitted); only `render_engines` (LOUD) and `audio_motion_profiles` (fail-soft) are genuinely durable. AGY's report does not distinguish these three outcomes at the granularity the underlying code actually has. |
| 12 | (Not addressed by AGY) Can publication succeed when the final ledger writeback fails? | **NEW FINDING -- AGY silent** | Confirmed **yes** -- the obs publish and its `"obs_publish OK"` line precede a ledger stamp that can never raise (sections 2 and 3). Arguably the single highest-severity gap in the whole audit; AGY's report does not surface it. |
| 13 | (Not addressed by AGY) Do both ledger save paths share one schema-version and merge policy? | **NEW FINDING -- AGY silent** | Confirmed **no**, on both axes, with a third conflicting strict-equality policy at Phase 10 -- section 6. |
| 14 | Test inventory (AGY section 7: five numbered claims + three uncovered-risk claims). | **PARTIAL to DISAGREE, itemized in section 8 below** | Two of AGY's five named test files do not exist (`test_otr_ledger_freeze.py`, `test_otr_freeze_cascade.py`); the coverage they describe is real but lives in four differently-named files AGY never cites. Full breakdown in section 8. |
| 15 | `OTR_WorkflowValidator`, `OTR_VideoDirector`, `OTR_ImageDirector` are non-consumers. | **AGREE** | Independently confirmed by two different agents (visual-pipeline cluster's spot-check and the dedicated sweep agent), by direct read of all three files -- zero ledger references beyond unrelated prose. |

---

## 8. Missing coverage and false-confidence tests

- **Two of AGY's five named "Freeze & Gap Audit Invariant" test files do not exist**
  (`tests/test_otr_ledger_freeze.py`, `tests/test_otr_freeze_cascade.py`). The real coverage lives in
  `tests/test_lfc_phase_0_10_gap_audit.py`, `tests/test_g8_line_id_uniqueness.py`,
  `tests/test_provenance_v4.py`, and `tests/test_scene_guard_v4.py` -- confirmed real by direct read of
  each, with specific test functions cited by line number in the underlying agent report.
- **`audit_post_freeze_writeback` is misattributed** to `test_otr_ledger_consumers.py` (which does not
  import it); its real coverage is `tests/test_post_freeze_writeback_audit.py`.
- **AGY's "content-owned read-only policy enforcement" claim overstates `tests/test_freeze_policy_readonly.py`**:
  that file only resolves which policy *name* a `source_bank` maps to; it never constructs a frozen ledger
  and never attempts a write against one.
- **"Audio sample hashing" is materially overstated**: the one true byte-identical audio hash gate
  (`test_audio_byte_identical_to_baseline`) is double-skipped in a normal run (`skipif not _HAS_BASELINE`
  **and** `skipif not os.environ.get("OTR_REGRESSION_RUNTIME")`) -- it does not execute in a default
  `pytest` pass, only the cheap structural fixture checks do.
- **No canonical whole-ledger SHA-256 "freeze receipt" test exists anywhere.** Confirmed by a targeted
  grep for `canonical_json`, `sort_keys`, and any `ledger`-scoped digest function -- every hit found is a
  per-field or per-row hash. There is no test (and, per section 1, no mechanism) that could make such a
  test pass.
- **No true mutation-rejection test exists on an already-frozen ledger, anywhere in the 280-file
  ledger-referencing test set searched.** Every `pytest.raises` found is one of: pre-freeze schema
  validation failure, a conflicting-sibling-artifact write on a *different* file (the cast-contract
  lockfile, not the episode ledger), or a halt-on-bad-verdict check (CastLock refusing to *proceed*, not a
  guard rejecting *mutation of already-frozen content*). This absence is not a testing oversight -- there is
  no source mechanism such a test could exercise.
- **No deep-immutability test and no wrapper-type test exist**, because no wrapper type of any kind exists
  (`MappingProxyType`/`FrozenLedger`/`@dataclass(frozen=True)` grepped across the whole repo -- zero hits
  on the ledger's content structures).
- **Two tests directly mock `load_ledger_safe`, bypassing the real disk/singleton cycle**:
  `tests/test_sequencer_ledger.py:123-124` and `tests/test_audio_motion_foldin.py:81`. Four more operate on
  bare Python dict literals with no serialization boundary at all
  (`test_lfc_phase_0_10_gap_audit.py`, `test_post_freeze_writeback_audit.py`, `test_g8_line_id_uniqueness.py`,
  `test_ledger_canon_parity.py`).
- **`tests/test_episode_assembler_offset_shift.py` does not exercise the real `EpisodeAssembler` class at
  all** -- its own docstring calls itself a "Mirror of the shift logic," testing a standalone
  reimplementation. The one test that does call the real class
  (`test_sequencer_ledger.py::test_episode_assembler_materializes_bookends_and_mirrors_by_placement`)
  confirms the append behavior but does **not** assert on final sort order, leaving the `.sort()` call's
  actual output ordering unverified.
- **`OTR_AudioEnhance` has zero test coverage of any kind** -- confirmed by a case-insensitive repo-wide
  grep for the class name and every one of its DSP helper functions, zero matches in `tests/`.
- **No test file references `OTR_ShotLock`, `OTR_SilentComposite`, `OTR_MetaBriefImagePromptGen`, or
  `portrait_ledger`/`stamp_portrait`** by class/module name (confirmed by grep). `ShotLock` and
  `SilentComposite` do have test files with adjacent names covering different concerns
  (`test_shot_lock_strict_join.py` for the strict-join contract, `test_otr_shot_lock.py` -- not opened this
  pass to confirm depth), but the sweep for the exact class import came back empty for the four named here.
- **No test drives a `_stamp_terminal_paths()` failure through the full `OTR_MasterAudioMux.mux()` call
  and asserts the run still reports `"obs_publish OK"`.** The swallow-on-failure behavior documented in
  sections 2 and 3 is proven by direct code reading (the call graph makes it unambiguous) but is **not**
  currently proven by any runtime test -- a real coverage gap on a high-stakes, silent-failure-mode finding.
- **`nodes/otr_workflow_validator.py`'s real filename is `_otr_workflow_validator.py`** -- the task prompt's
  own naming (matching AGY's) is off by one underscore; the file itself is correctly a non-consumer either
  way.

---

## 9. Recommended machine-readable Ledger Bible artifact set

Aligned with the Story Lab's own `LEDGER_BIBLE_AUDIT_PLAN.md` target artifact set (section D), corrected
for what this audit actually found production needs:

```
ledger_schema_v1.json           machine-readable shape + invariants, split into three tiers per field-
                                 ownership table (section 5): authored/immutable, derived/mutable,
                                 telemetry -- so a schema consumer can tell WHICH guarantee a field carries
ledger_consumer_matrix_v1.json  the code-grounded matrix in section 3 of this report, converted to data
ledger_migrations.json          explicit version transitions; must reconcile the three-way schema-version
                                 policy conflict in section 6 before this file can be written honestly
LEDGER_BIBLE.md                 generated FROM the two JSON files above, never hand-maintained separately
                                 (per the Story Lab plan's own explicit warning against drift)
fixtures/ledger/*.json          hash-pinned accepted/rejected cases -- extend the Story Lab's existing
                                 clean-control / challenger pair (already SHA-256 pinned) with a THIRD
                                 fixture that isolates the post-freeze speaker_role/lines[] mutation class
                                 found in this audit, since neither existing fixture currently exercises it
tests/test_ledger_contract.py   schema/reference/role/order rules -- start from the Story Lab's own
                                 already-written `ledger_contract.py` (orphaned, uncommitted, unwired,
                                 zero test coverage -- see section 11) rather than writing a new one
tests/test_frozen_ledger.py     the test class that does not exist today (section 8): must assert (a) a
                                 canonical whole-object digest is unchanged across every post-freeze
                                 consumer call, (b) a direct mutation attempt on the seven write-once fields
                                 named in section 1's recommendation 2 is REJECTED, not merely detectable
tests/test_ledger_consumers.py  one real (not mocked-`load_ledger_safe`) contract test per consumer in
                                 section 3, starting with the two currently-untested nodes (`AudioEnhance`,
                                 `ShotLock`) and the one currently-unproven high-stakes claim (`MasterAudioMux`
                                 publish-succeeds-despite-writeback-failure)
```

---

## 10. First bounded CPU-only implementation chunk and acceptance tests

**Objective**: prove the freeze boundary can be made real for the one field class with the clearest,
narrowest blast radius -- `lines[].speaker_role` -- without touching GPU workloads, workflow JSON, or any
node's happy-path behavior.

1. Add a single write-once guard inside `_otr_ledger.py::patch_line_fields` (the shared helper
   `SceneSequencer` already calls) and a parallel guard inside `stamp_durable`/`save_ledger_safe`'s
   row-merge path: if `meta.cleanup_locked is True` and an incoming write to a `lines[]` row would change
   `speaker_role`, `char_id`, `scene_id`, `shot_id`, or `text`, raise a new `FrozenLineMutationError`
   **unless** the caller passes an explicit `reason=` string, in which case allow it but append a
   `meta.freeze_repairs[]` entry recording `{line_id, field, old, new, reason, component}`.
2. Convert `cast_lock.py:522-523`'s silent `ln["speaker_role"] = "announcer"` into the first real caller of
   that `reason=` path (`reason="mis-stamped announcer line, re-routed to OTR_AnnouncerVoice"`), so the
   exact mutation this whole audit turned on becomes an audited, first-class repair instead of a silent
   dict write -- with zero behavior change to what actually gets voiced.
3. Write `tests/test_frozen_line_mutation_guard.py`:
   - `test_unguarded_speaker_role_rewrite_after_freeze_raises` -- build a minimal frozen ledger (reuse
     `test_lfc_phase_0_10_gap_audit.py`'s `_clean_ledger_data()` fixture pattern), call
     `patch_line_fields` with a `speaker_role` change and no `reason`, assert `FrozenLineMutationError`.
   - `test_guarded_rewrite_with_reason_succeeds_and_is_recorded` -- same setup, with `reason=`, assert the
     write succeeds and `meta.freeze_repairs[-1]` matches.
   - `test_cast_lock_announcer_reroute_still_works_and_is_now_audited` -- real call to
     `CastLock().lock()` against a fixture ledger containing exactly the mis-stamped-announcer shape
     `_resolve_character_voices_fail_soft` targets; assert the reroute still happens (no regression) **and**
     `meta.freeze_repairs` now contains the entry.
   - `test_unrelated_line_fields_still_mutate_freely_post_freeze` -- `start_s`/`dur_s`/`tts_engine`/etc.
     writes on a frozen ledger must still succeed unguarded, proving the guard is scoped to exactly the
     five fields named above and does not regress `SceneSequencer`/`EpisodeAssembler`'s legitimate timing
     writes.
4. Run via the Windows venv: `pytest -q tests/test_frozen_line_mutation_guard.py
   tests/test_lfc_phase_0_10_gap_audit.py tests/test_bark_freeze_halt_bypass.py
   tests/test_sequencer_ledger.py tests/test_cast_lock.py -p no:cacheprovider`. All must pass green,
   including the pre-existing suites, before this chunk is considered done -- the guard must not be the
   kind of "fix" that breaks the exact reroute mechanism it makes visible.

This chunk deliberately does **not** attempt the `lines[]` append/re-sort question (`EpisodeAssembler`,
`ShotLock`) or the schema-version/merge-policy reconciliation (section 6) -- both are real, larger design
decisions (a new `timeline[]` array; a chosen single merge/version policy) that need an operator call, not
a mechanical guard, and belong to a second chunk.

---

## 11. Runtime unknowns that static inspection cannot honestly settle

- **Does `find_most_recent_ledger()`'s pure mtime walk ever actually pick a stale sibling episode's ledger
  across a real queue boundary in production?** The code path exists and is explicitly referenced in its
  own comment as a known historical bug class (`BUG-LOCAL-021`), but confirming current-day frequency needs
  a live multi-process run, not a static read.
- **Does a `_stamp_terminal_paths()` failure inside `OTR_MasterAudioMux` ever actually occur in production,
  and if so, how often does the ledger's terminal-path record silently diverge from the real published
  file?** The swallow mechanism is proven by code reading (sections 2 and 3); its real-world hit rate
  is not observable without instrumenting a live render or mining historical logs for the
  `"terminal path stamp failed"` string, which does not appear to be searched for anywhere today.
- **Does `SignalLostVideo`'s episode-directory rename ever race a still-open file handle from an
  in-flight async image/video batch on Windows, producing a `PermissionError` in `os.replace`?** This is a
  genuine concurrency question that depends on real OS-level file-handle timing; the code's own broad
  `except Exception` around the whole rename block would silently absorb such a failure into a WARNING
  either way, so even a log-mining approach would need to specifically watch for that warning text across
  historical runs.
- **Is `cast[i].portrait_content_hash` (the newly-found `portrait_ledger.stamp_portrait` write, section 3)
  actually consumed by anything downstream in a live render, or is it dead weight?** Static reading found
  zero callers of its own read-side helpers (`resolve_portrait_path`/`portrait_hash_for_char`) anywhere in
  the repository, but a video-engine adapter (`eng_character_3d.py`, named in the module's own docstring as
  an intended consumer) could plausibly resolve portraits through some other path not traced in this
  audit's scope -- confirming "truly dead" vs. "consumed some other way" needs either a targeted trace of
  `eng_character_3d.py`'s actual portrait-resolution code (out of this audit's assigned scope) or a live
  render with the field deliberately withheld to see if anything breaks.
- **What is `announcer_ids` (`cast_lock.py:518`) actually populated from, and does it reliably cover every
  real production episode's announcer sentinel, including the `char_id="announcer"` vs. `cast[0].char_id="c01"`
  mismatch found on the Story Lab's clean-control fixture (section 6)?** Not independently traced to its
  source this pass; whether production's real cast rows ever exhibit the same mismatch the Story Lab
  fixture does is unknown without either reading that source or sampling real on-disk episode ledgers.
- **How many of the 89 test files that reference `OTR_LedgerScriptWriter` by name actually exercise its
  `.run()` end-to-end, versus performing only static source-string assertions like the one file I opened
  (`test_writer_stamps_episode_title.py`)?** This bears directly on how much real confidence exists in the
  writer's own pre-freeze field-stamping behavior, and was flagged as an open gap rather than resolved,
  given the scale of individually auditing 89 files.
- **Do any of the ~20 internal writer-helper modules whose exact caller line I could not independently
  trace this pass** (`_otr_audio_motion.py`, `_otr_cue_manifest.py`, `_otr_delivery_vector.py`,
  `_otr_dramatic_state_llm.py`, `_otr_story_brief.py`, `_otr_story_spine.py`, `_otr_word_delivery.py`,
  `_otr_provenance.py`, `_otr_gguf_backend.py`) **run more than once, or run out of the documented writer
  sequence, under any real production configuration?** Each was confirmed to write real ledger fields, but
  none was traced to a confirmed single call site with a confirmed single invocation count -- a static read
  cannot rule out a double-write or an ordering-dependent bug without either reading every caller
  exhaustively (deferred, given the audit's time budget) or observing a live run's log sequence.

---

## Bottom line

The ledger's "freeze" is a stamp, not a lock: Phase 10 validates shape once, writes
`meta.cleanup_locked=True`, and no code anywhere ever reads that flag to stop a write. Three production
nodes then rewrite the very fields the freeze was supposed to protect -- CastLock silently flips
`speaker_role`, and both EpisodeAssembler and ShotLock append to and re-sort `lines[]` -- while SciFi
`fact_ids` never even reach the ledger rows, and the terminal mux can log `obs_publish OK` even when its
own ledger writeback silently fails. AGY's report got the two-plane idea right but its "strictly frozen"
headline wrong; it also cited one source file and two test files that do not exist, and credited three
nodes with ledger stamps that appear nowhere in the code. The right next move is small: guard the authored
line fields behind a write-once check with one audited repair path (section 10), then split synthetic
timeline rows out of `lines[]`, reconcile the three conflicting schema-version policies, and wire up the
Story Lab's own orphaned `ledger_contract.py` before any emission format is finalized.

---

*End of audit. Written to
`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab\docs\2026-08-13-story-recovery\SONNET_LEDGER_BIBLE_AUDIT.md`.*
