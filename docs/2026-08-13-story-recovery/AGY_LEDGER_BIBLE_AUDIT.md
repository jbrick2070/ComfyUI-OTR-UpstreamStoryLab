# Universal Audit Report: Ledger Data Contract & Downstream Consumers (Ledger Bible Audit)

**Audit Date:** 2026-08-13  
**Auditor Agent:** Antigravity (Gemini 3.7 Flash - High)  
**Credit / Spend Rung:** $0 local / read-only audit  
**Review-Routing Directive:** 2026-08-11 Directive (read from `docs/GO_FORWARD_PLAN.md:140-160`; full-kibitz gate suspended in favor of Codex CLI consult + Sonnet 5 post-coding QA)  
**Story Quality Directive:** 2026-08-04 Operator Directive (read from `CLAUDE.md:13-17`; script acceptance as-is, correctness defects remain open)  
**Content Guardrails Directive:** 2026-08-03 / 2026-08-05 Operator Directive (read from `CLAUDE.md:18-20`; G9 deleted, same_story_safety_cleanup retired)  
**Production Repo:** `C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OldTimeRadio`  
**Story Lab Repo:** `C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab`  
**Primary Output File:** `C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab\docs\2026-08-13-story-recovery\AGY_LEDGER_BIBLE_AUDIT.md`  

---

## 1. Executive Verdict: The Coherence & Freeze Status of the Ledger Contract

**Verdict: PARTIALLY COHERENT DUAL-PLANE CONTRACT (CONFIRMED)**

Static code inspection and executable test tracing reveal that **no single, monolithic immutable ledger contract exists today**. Instead, the system implements a **two-plane, two-phase operational contract**:

1. **The Narrative / Structural Plane (Strictly Frozen at Phase 10):**
   - **Boundary:** `nodes/OTR_LedgerFreezeCascade.py:382-430` calling `nodes/_otr_freeze_cascade.py:900-1120` and `nodes/_otr_ledger_freeze.py:720-960`.
   - **Contract:** Once `meta.cleanup_locked = True`, `meta.freeze_timestamp`, and `meta.freeze_verdict` are stamped at Phase 10, the narrative content (`cast`, `scenes`, `beats`, `shots`, and narrative `lines` with `speaker_role`, `speaker`, `char_id`, `text`, `text_for_tts`, `scene_id`, `shot_id`) is treated as structurally immutable.
   - **Enforcement:** Verified by `_sha256_content_authorship` (`nodes/_otr_freeze_cascade.py:214-250`), `_readonly_structural_validation` (`nodes/_otr_freeze_cascade.py:350-410`), and Phase 10 invariants (`nodes/_otr_ledger_freeze.py:725-820`).

2. **The Media Execution & Telemetry Plane (Evolving, Multi-Writer, Disk-Merged):**
   - **Boundary:** Downstream nodes executing post-freeze (`OTR_CastLock`, `OTR_BatchCharacterVoices`, `OTR_AnnouncerVoice`, `OTR_StableAudioTheme`, `OTR_SceneSequencer`, `OTR_AudioEnhance`, `OTR_EpisodeAssembler`, `OTR_ShotLock`, `OTR_ImageGenDispatcher`, `OTR_VideoRenderBatch`, `OTR_SilentComposite`, `OTR_PostUpscaleProcgenBlend`, `OTR_CaptionBurn`, `OTR_CreditsRoll`, `OTR_MasterAudioMux`).
   - **Contract:** Downstream nodes mutate the ledger extensively after Phase 10. These mutations include:
     - **Voice Assignment & Route Resolution:** `cast[i].voice_preset`, `cast[i].voice_route_id`, `cast[i].voice_spec`, `meta.cast_voice_policy` (`nodes/cast_lock.py:270-316`).
     - **Audio Sample Receipts & Cache Keys:** `lines[i].render_ms`, `lines[i].audio_sample_hash`, `lines[i].generated_dur_s`, `lines[i].tts_engine` (`nodes/_otr_voice_node_common.py:1060-1140`).
     - **Music Cue Placement & Paths:** `music[i].wav_path`, `music[i].start_s`, `music[i].dur_s`, `music[i].start_s_space = "master_mix"` (`nodes/stable_audio_theme.py:280-330`, `nodes/scene_sequencer.py:1615-1640`).
     - **Timeline Assembly & Synthetic Music Injections:** `lines[i].start_s`, `lines[i].dur_s`, `lines[i].start_s_space = "scene_audio" -> "master_mix"`, plus **injection of synthetic mirror lines** `lines[].append({"mirrored_from": "music", ...})` and chronological re-sorting of `lines[]` (`nodes/scene_sequencer.py:1115-1135`, `1550-1570`, `1700-1830`).
     - **Episode Renaming & Path Rebasing:** `episode_id` mutated from `pending_<timestamp>` to title-based slug, directory moved on disk, and all internal paths rebased (`nodes/production_ledger.py:310-440`, `nodes/scene_sequencer.py` / `nodes/video_engine.py`).
     - **Visual Planning & Generation Stamping:** `video` top-level section added (`nodes/otr_shot_lock.py:1887-1928`), `images` section added (`nodes/otr_image_gen_dispatcher.py:1709`), `shots[i].png_path` stamped, `clips[]` array created/updated with per-clip render telemetry (`nodes/otr_video_render_batch.py:190-235`, `nodes/_otr_video_engines/render_driver.py:4550-4650`).
     - **Terminal Delivery Publishing:** `final_audio_path`, `final_video_path`, `meta.obs_final_path` stamped (`nodes/otr_master_audio_mux.py:530-545`).

**Critical Finding:** The term "ledger freeze" in the codebase strictly denotes the **freeze of narrative authorship and structural topology**, NOT the freeze of the JSON document as an immutable artifact. The system relies on a hybrid synchronization mechanism: in-memory wire dictionaries passed across ComfyUI sockets (`script_json`, `ledger_json`, `patched_ledger_json`) combined with out-of-band atomic filesystem saves via the in-flight singleton (`nodes/_otr_ledger.py:load_ledger_safe` / `save_ledger_safe` and `nodes/production_ledger.py:stamp_durable` with `_merge_with_disk`).

---

## 2. Ledger Lifecycle Diagram

```
+---------------------------------------------------------------------------------------------------+
| 1. PRE-FREEZE CONSTRUCTION & COMPOSITION (In-Memory + Pending Directory)                         |
|                                                                                                   |
|  [OTR_LedgerScriptWriter] (nodes/OTR_LedgerScriptWriter.py:6778)                                  |
|   ├── init_lines_from_outline() (nodes/production_ledger.py:740)                                  |
|   ├── compose_line() / compose_announcer_outro() (_otr_line_composer.py:400)                      |
|   ├── Story Pack Overlay (_otr_scifi_codex.py / _otr_scifi_fable2.py / _otr_news_wiring.py)       |
|   ├── Content Authorship Stamp (_otr_content_authorship.py:80)                                    |
|   └── Initial text metrics & meta paths (_build_meta_paths, nodes/_otr_ledger.py:430)             |
+---------------------------------------------------------------------------------------------------+
                                                │
                                                ▼ wire: script_json
+---------------------------------------------------------------------------------------------------+
| 2. FREEZE CASCADE & PHASE 10 BOUNDARY (Deterministic Narrative Seal)                               |
|                                                                                                   |
|  [OTR_LedgerFreezeCascade] (nodes/OTR_LedgerFreezeCascade.py:380 / nodes/_otr_freeze_cascade.py:900)  |
|   ├── Phase 0: Gap Audit Pre (nodes/_otr_ledger_freeze.py:700)                                    |
|   ├── Policy Resolution: content_owned_readonly vs inline_safety_cleanup (_otr_freeze_cascade:180) |
|   ├── D3 Role Sweep: Coerce char_id real cast to speaker_role="character" (_otr_freeze_cascade:450)  |
|   ├── Phase 7: Pronunciation / Audio Readiness (nodes/_otr_readiness.py:220)                      |
|   ├── Telemetry: stamp_actual(stage="freeze_pre_media") (nodes/_otr_word_delivery.py:280)        |
|   ├── Phase 8: Video Readiness (nodes/_otr_readiness.py:380)                                      |
|   ├── Phase 10: Final Structural Gap Audit (nodes/_otr_ledger_freeze.py:725)                       |
|   │     ├── Null rejection, list presence (cast, lines, beats, scenes, shots, music, clips)       |
|   │     ├── Unique G8 line_id uniqueness, G14 provenance check, G15 scene coherence               |
|   │     └── Validates G6 Bark prefix / cast voice spec invariants                                 |
|   ├── Seal Stamps: meta.cleanup_locked=True, meta.freeze_timestamp, meta.freeze_verdict           |
|   ├── Capability Receipt: meta.freeze_capability_receipt (nodes/_otr_freeze_cascade.py:530)       |
|   └── Persistence: _persist_cascade_meta() (nodes/_otr_freeze_cascade.py:80)                      |
+---------------------------------------------------------------------------------------------------+
                                                │
                                                ▼ wire: v2_ledger_json / script_json
+---------------------------------------------------------------------------------------------------+
| 3. POST-FREEZE AUDIO EXECUTION (Voice Locking, Synthesis & Timeline Muxing)                        |
|                                                                                                   |
|  [OTR_CastLock] (nodes/cast_lock.py:187)                                                          |
|   ├── Assigns voice_preset, presentation_gender, voice_route_id, voice_spec                       |
|   └── stamp_durable(sections={"cast"}, meta_updates={...}) -> disk + wire ledger_json             |
|                                                                                                   |
|  [OTR_BatchCharacterVoices / OTR_AnnouncerVoice] (nodes/_otr_voice_node_common.py:566)              |
|   ├── Renders TTS clips per line, computes audio_sample_hash, render_ms, generated_dur_s         |
|   └── Flushes per-line stamps via _persist_ledger_stamps() -> save_ledger_safe() to disk           |
|                                                                                                   |
|  [OTR_StableAudioTheme] (nodes/stable_audio_theme.py:260)                                         |
|   ├── Renders music cues, stamps music[i].wav_path, cue_spec_sha256, music_render_status          |
|   └── save_ledger_safe() to disk; emits cue_manifest_json                                         |
|                                                                                                   |
|  [OTR_SceneSequencer] (nodes/scene_sequencer.py:800)                                              |
|   ├── Sequences audio timeline; stamps lines[i].start_s, dur_s, start_s_space="scene_audio"       |
|   ├── Appends audio_gates["post_scene_sequencer"] (first 1024 bytes SHA256)                       |
|   └── save_ledger_safe() to disk                                                                  |
|                                                                                                   |
|  [OTR_AudioEnhance] (nodes/audio_enhance.py:440)                                                  |
|   └── Appends audio_gates["post_audio_enhance"], stamps phase_ms.audio_enhance -> disk             |
|                                                                                                   |
|  [OTR_EpisodeAssembler] (nodes/scene_sequencer.py:1450)                                           |
|   ├── Shifts lines[i], clips[i], music[i] start_s to start_s_space="master_mix"                   |
|   ├── Injects synthetic music lines: lines[].append({mirrored_from: "music", ...})                |
|   ├── Re-sorts lines[] chronologically by start_s; appends transitions[]                          |
|   └── Appends audio_gates["post_episode_assembler"] -> save_ledger_safe(); emits audio_done        |
+---------------------------------------------------------------------------------------------------+
                                                │
                                                ▼ wire: audio_done + script_json / patched_ledger_json
+---------------------------------------------------------------------------------------------------+
| 4. POST-FREEZE VISUAL & EPISODE WORKSPACE FINALIZATION                                            |
|                                                                                                   |
|  [OTR_SignalLostVideo] (nodes/scene_sequencer.py / nodes/video_engine.py)                         |
|   ├── Generates procgen fallback background video                                                 |
|   ├── Invokes Ledger.rename_episode(): renames pending_<ts> to slug, rebases internal paths       |
|   └── Emits title_card_plan_json                                                                  |
|                                                                                                   |
|  [OTR_ShotLock] (nodes/otr_shot_lock.py:1782)                                                     |
|   ├── overlay_audio_timing(strict=True): rehydrates disk audio timing onto wire ledger            |
|   ├── Plans shots, budgets frame counts per beat, binds roles_effective & routing snapshot        |
|   └── Stamps top-level ledger["video"] and meta.video_revision -> emits patched_ledger_json        |
|                                                                                                   |
|  [OTR_ImageGenDispatcher] (nodes/otr_image_gen_dispatcher.py:1698)                                |
|   ├── Dispatches portrait and scene still generations (Flux/Z-Image/SD)                           |
|   └── Stamps top-level ledger["images"], shots[i].png_path, cast[i].portrait_path -> stamp_durable|
|                                                                                                   |
|  [OTR_VideoRenderBatch] (nodes/otr_video_render_batch.py:238 / render_driver.py:4550)               |
|   ├── Renders video clips per shot/beat (Wan, HuMo, LTX, Minimax H3, visualizers)                 |
|   ├── Stamps per-clip render telemetry (humo_render_ms, mp4_dur_s, warmup_pad_ms, oom_recovery)  |
|   ├── Stamps meta.render_engines receipt via stamp_durable()                                      |
|   └── Stamps audio_motion_profiles via save_ledger_safe(); emits clip_manifest_json               |
+---------------------------------------------------------------------------------------------------+
                                                │
                                                ▼ wire: clip_manifest_json + video streams
+---------------------------------------------------------------------------------------------------+
| 5. COMPOSITING, CAPTIONS, CREDITS ROLL & TERMINAL OBS PUBLISH                                     |
|                                                                                                   |
|  [OTR_SilentComposite] (nodes/otr_silent_composite.py:180)                                        |
|   └── Composites rendered clips into continuous silent timeline mp4                               |
|                                                                                                   |
|  [OTR_CaptionBurn] (nodes/otr_caption_burn.py:80 / nodes/_otr_captions.py:84)                      |
|   ├── Reads lines[] (start_s, dur_s, text, speaker_role, char_id) & cast[]                        |
|   └── Burns open SDH captions + hero title cards (.ass via FFmpeg)                                |
|                                                                                                   |
|  [OTR_CreditsRoll] (nodes/otr_credits_roll.py:270)                                                |
|   ├── Reads durable ledger from disk: cast, meta.episode_title, visual_style, render_engines,     |
|   │     image_engines, music_engine, source_bank, news, provenance, git_commit                    |
|   ├── Renders 3-column Signal Lost console + scrolling script transcript                          |
|   └── Emits video_with_credits_path and declared_credits_tail_s                                   |
|                                                                                                   |
|  [OTR_MasterAudioMux] (nodes/otr_master_audio_mux.py:550)                                         |
|   ├── Muxes silent video + master audio + declared credits tail duration                          |
|   ├── Copies final deliverable to otr/obs/<episode_id>.mp4 (publish_to_obs)                       |
|   ├── Stamps final_audio_path, final_video_path, meta.obs_final_path -> save_ledger_safe()         |
|   └── Logs "obs_publish OK"                                                                       |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Exhaustive Downstream Consumer Matrix

| Component / Node | Evidence (File, Function/Class, Line) | Fields Read | Type / Cardinality / Ordering Expectations | Required vs Optional & Fallback | Ledger Mutation Behavior | Test Coverage & Quality Assessment | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OTR_CastLock** | `nodes/cast_lock.py:177-320` (`lock`) | `cast[]`, `lines[]`, `meta.freeze_verdict`, `meta.freeze_unload_ok`, `meta.cast_lock_revision`, `meta.cast_voice_policy`, `meta.voice_bank_id`, `meta.source_bank` | `cast` is list of dicts with unique `char_id`. `lines` is list of dicts. | Required: `cast`. `meta.freeze_verdict` raises if `"needs_full_rerun"` unless bypassed. `cast_voice_policy` defaults to `"preserve_ledger"`. | **Mutates in-memory & disk:** stamps `cast[i].voice_preset`, `cast[i].presentation_gender`, `cast[i].tts_model`, `cast[i].voice_params`, `cast[i].voice_route_id`, `cast[i].voice_spec`, `meta.cast_lock_revision`, `meta.cast_voice_policy`, `meta.voice_bank_id`. Calls `stamp_durable()`. | `tests/test_cast_contract.py`, `tests/test_phase3_ledger_reviewer.py`. High coverage of voice mapping. | **CONFIRMED** |
| **OTR_BatchCharacterVoices** | `nodes/batch_character_voices.py:9-40`, `nodes/_otr_voice_node_common.py:566-610` (`generate`), `613-1200` (`_render_per_line`) | `lines[]` (`text`, `text_for_tts`, `speaker_role`, `char_id`, `line_id`), `cast[]` (`char_id`, `voice_preset`, `voice_ref_path`, `voice_ref_id`, `gender`), `meta.episode_seed`, `meta.cast_lock_revision`, `meta.voice_device`, `meta.paths.audio_dir` | Filtered where `speaker_role == "character"`. Preserves line ordering. | Required: `lines`, `cast`. If 0 lines, emits empty batch. If unresolvable voice on policy route, raises `VoiceCastingError`. | **Mutates disk:** stamps per-line `tts_engine`, `voice_preset`, `render_ms`, `generated_dur_s`, `audio_sample_hash`, `sample_rate`, `voice_route_id`, `audio_cache_key`, `audio_sha256`, `provider_model_id` via `_persist_ledger_stamps()`. | `tests/test_audio_byte_identical.py`, `tests/test_engine_profiles.py`. Real execution tests present. | **CONFIRMED** |
| **OTR_AnnouncerVoice** | `nodes/announcer_voice.py:9-35`, `nodes/_otr_voice_node_common.py:566-1200` | Same as BatchCharacterVoices, filtered where `speaker_role == "announcer"` | `speaker_role == "announcer"` lines. | Required: announcer lines in `lines[]`. Kokoro picks one announcer voice per episode from `meta.episode_seed`. | **Mutates disk:** flushes per-line announcer audio metadata and sample hashes to disk ledger via `_persist_ledger_stamps()`. | `tests/test_announcer_voice.py`, `tests/test_kokoro_announcer.py`. | **CONFIRMED** |
| **OTR_StableAudioTheme** | `nodes/stable_audio_theme.py:50-90` (`_style_from_ledger`), `260-390` (`generate`) | `music[]` (`cue_id`, `placement`, `title`, `description`, `mood`), `meta.news`, `meta.style`, `meta.story_contract`, `meta.episode_seed`, `meta.voice_device` | `music` is list of cue dicts. | Optional: defaults to standard theme cues if `music[]` empty. | **Mutates disk:** stamps `music[i].wav_path`, `music[i].start_s`, `music[i].dur_s`, `music[i].cue_spec_sha256`, `music[i].music_render_status`, `meta.music_theme_render_ms`. Emits `cue_manifest_json`. | `tests/test_stable_audio_theme.py`, `tests/test_cue_manifest.py`. | **CONFIRMED** |
| **OTR_SceneSequencer** | `nodes/scene_sequencer.py:800-1155` (`sequence_scenes`) | `lines[]` (`speaker_role`, `line_id`, `text`), `beats[]`, `cast[]`, `music[]`, in-flight ledger path | Iterates `lines[start_line:end_line]`. Sequential time accumulation. | Required: `lines[]`. Unknown `speaker_role` (e.g. legacy `"sfx"`) raises `ValueError`. | **Mutates disk:** stamps `lines[i].start_s`, `lines[i].dur_s`, `lines[i].start_s_space = "scene_audio"`, `meta.phase_ms.scene_sequencer`, appends `audio_gates` (`"post_scene_sequencer"`). | `tests/test_sequencer_ledger.py`, `tests/test_scene_sequencer.py`. Comprehensive unit tests. | **CONFIRMED** |
| **OTR_AudioEnhance** | `nodes/audio_enhance.py:435-460` (`enhance_audio`) | In-flight ledger singleton, `audio_gates` | Global audio stream | Fail-soft: if ledger missing, logs warning and proceeds. | **Mutates disk:** appends `audio_gates` (`"post_audio_enhance"`), stamps `meta.phase_ms.audio_enhance`. | `tests/test_audio_enhance.py`. | **CONFIRMED** |
| **OTR_EpisodeAssembler** | `nodes/scene_sequencer.py:1450-1900` (`assemble_episode`) | `lines[]`, `music[]`, `clips[]`, `meta.episode_title`, `audio_gates`, in-flight disk ledger | Reads `lines[]`, shifts timings from `scene_audio` to `master_mix`. | Required: `lines[]`, `music[]`. | **Major Mutation:** Shifts `lines[i]`, `clips[i]`, `music[i]` `start_s` to `master_mix`. **Appends synthetic music lines** (`mirrored_from="music"`) chunked <= 22.0s. **Re-sorts `lines[]` chronologically.** Appends `transitions[]` and `audio_gates`. | `tests/test_sequencer_ledger.py`, `tests/test_episode_assembler.py`. | **CONFIRMED** |
| **OTR_SignalLostVideo** | `nodes/scene_sequencer.py:1920-2004`, `nodes/video_engine.py:2260-2380` (`render_video`) | `script_json`, `news_used`, `meta.episode_title`, `meta.visual_plan`, `lines[]` (for title card timing) | Wire ledger dict. | Optional news/title defaults. | **Mutates disk & FS:** Triggers `Ledger.rename_episode()`, renaming episode dir from `pending_<ts>` to slug, moving files on disk, rebasing internal paths. Stamps `final_audio_path`, `final_video_path`, `meta.paths`, `meta.title_card_plan`. | `tests/test_production_ledger.py::test_rename_episode_*`, `tests/test_video_engine.py`. | **CONFIRMED** |
| **OTR_ShotLock** | `nodes/otr_shot_lock.py:1782-1943` (`lock`) | `script_json` (wire), `video_policy_json`, `audio_done`, `lines[]` (`start_s`, `dur_s`, `beat_id`, `speaker_role`), `beats[]`, `shots[]`, `cast[]`, `meta.visual_plan`, `meta.audio_revision` | Full structural ledger + audio timing join. | Required: `video_policy_json` (must be version 2), `audio_done`. Post-audio join via `overlay_audio_timing(strict=True)` raises `PostAudioJoinFailed` if missing. | **Mutates in-memory & disk:** Injects synthetic opening-music beat (`open_music_b000`), stamps top-level `video` section (`shots[]`, `execution_groups[]`, `clip_budget`, `roles_effective`, `routing_env_snapshot`), stamps `meta.video_revision`. | `tests/test_otr_shot_lock.py`, `tests/test_shot_lock_strict_join.py`. | **CONFIRMED** |
| **OTR_MetaBriefImagePromptGen** | `nodes/otr_meta_brief_image_prompt.py:1280-1360` (`generate`) | `script_json` (from ShotLock), `image_policy_json`, `meta.visual_plan`, `meta.source_bank`, `shots[]`, `cast[]`, `scenes[]` | Top-level visual metadata and shot definitions. | Required: `script_json`, `image_policy_json`. | **Read-Only:** Emits `image_prompts_json` (payload containing objects, characters, and scenes). | `tests/test_meta_brief_image_prompt.py`. | **CONFIRMED** |
| **OTR_ImageGenDispatcher** | `nodes/otr_image_gen_dispatcher.py:440-495` (`_reresolve_stills_dir`), `1698-1723` (`dispatch`) | `script_json`, `image_policy_json`, `image_prompts_json`, `episode_id`, `cast[]`, `shots[]`, `meta.paths.stills_dir`, in-flight disk ledger | Reads shot IDs and character IDs to bind stills. | Required: `script_json`, `image_prompts_json`. Re-resolves stills directory if title rename occurred. | **Mutates in-memory & disk:** Stamps top-level `images` dict, updates `shots[i].png_path`, `cast[i].portrait_path`, stamps `meta.image_gen_receipt` via `stamp_durable()`. | `tests/test_image_gen_dispatcher.py`. | **CONFIRMED** |
| **OTR_VideoRenderBatch** | `nodes/otr_video_render_batch.py:175-235`, `nodes/_otr_video_engines/render_driver.py:4550-4650` | `patched_ledger_json`, `master_audio_path`, `video.shots[]`, `video.execution_groups[]`, `clips[]`, `lines[]`, `beats[]`, `meta.paths`, `meta.video.roles_effective` | Reads planned shots, conditioning audio, and still paths. | Required: `patched_ledger_json`, `master_audio_path`. Raises if engine configuration invalid. | **Mutates disk:** Stamps per-clip render telemetry (`humo_render_ms`, `mp4_dur_s`, `mp4_frames`, `warmup_pad_ms`, `audio_fed_to_humo_dur_s`, `oom_recovery_count`), stamps `meta.render_engines` payload via `stamp_durable()`, stamps `audio_motion_profiles`. Emits `clip_manifest_json`. | `tests/test_video_render_batch.py`, `tests/test_audio_motion_foldin.py`. | **CONFIRMED** |
| **OTR_SilentComposite** | `nodes/otr_silent_composite.py:180-260` (`composite`) | `base_video_path`, `clip_manifest_json`, disk ledger | Reads clip timing entries and total duration. | Required: `base_video_path`. | **Mutates disk:** Stamps `meta.phase_ms.silent_composite`, `meta.silent_composite_receipt`. | `tests/test_silent_composite.py`. | **CONFIRMED** |
| **OTR_SceneAwareScopes** | `nodes/otr_scene_aware_scopes.py:120-190` | Audio stream, `clip_manifest_json` | Reads manifest for scene cut boundaries. | Optional audio-visualizer floor. | **Read-Only:** Emits `scopes_mp4_path`. | `tests/test_scene_aware_scopes.py`. | **CONFIRMED** |
| **OTR_PostUpscaleProcgenBlend** | `nodes/otr_post_upscale_procgen_blend.py:200-260` | `source_mp4_path`, `procgen_mp4_path`, `scopes_mp4_path`, disk ledger | Reads disk ledger for phase telemetry. | Optional procgen blend overlay. | **Mutates disk:** Stamps `meta.phase_ms.post_upscale_procgen_blend`. | `tests/test_post_upscale_procgen_blend.py`. | **CONFIRMED** |
| **OTR_CaptionBurn** | `nodes/otr_caption_burn.py:60-130`, `nodes/_otr_captions.py:1-120` (`build_ass_from_ledger`) | `ledger_path` (or disk singleton), `title_card_plan_json`, `lines[]` (`start_s`, `dur_s`, `text`, `speaker_role`, `char_id`), `cast[]` (`char_id`, `name`) | `lines[]` with `speaker_role in ("character", "announcer")` and valid `start_s`/`dur_s`. | Required: `lines[]`. Burns raw `lines[i].text` (including performance directions) per operator ruling 2026-08-05. | **Mutates disk:** Stamps `meta.phase_ms.caption_burn`. | `tests/test_otr_captions.py`, `tests/test_caption_burn.py`. | **CONFIRMED** |
| **OTR_CreditsRoll** | `nodes/otr_credits_roll.py:118-125` (`_require`), `270-380` (`_collect_credits_data`), `560-600` | Disk ledger via `load_ledger_safe`: `cast[]`, `meta.episode_title`, `meta.visual_style`, `meta.render_engines`, `meta.image_engines`, `meta.music_engine`, `meta.source_bank`, `meta.news`, `meta.provenance`, `meta.episode_seed`, `lines[]` (for full transcript scroll) | Full durable ledger singleton. | **Strict No-Fallback:** Missing `episode_title`, `visual_style`, `render_engines`, `image_engines`, `music_engine`, `source_bank`, or `cast` raises `CreditsDataError`. | **Mutates disk:** Stamps `meta.credits_receipt`. Emits `video_with_credits_path` and `declared_credits_tail_s`. | `tests/test_credits_roll.py`, `tests/test_credits_data_error.py`. | **CONFIRMED** |
| **OTR_MasterAudioMux** | `nodes/otr_master_audio_mux.py:320-350` (`_reresolve_master_audio`), `520-570` (`_stamp_terminal_paths`), `550-605` (`mux`) | `silent_video_path`, `master_audio_path`, `declared_credits_tail_s`, disk ledger via `load_ledger_safe` | Video stream, audio stream, credits tail float. | Required: video & audio streams. Re-resolves audio path if title rename moved directory. | **Mutates disk & FS:** Publishes final video to `otr/obs/<episode_id>.mp4`. Stamps `final_audio_path`, `final_video_path`, `meta.obs_final_path`, `meta.paths.obs_final`, `meta.phase_ms.master_audio_mux`. | `tests/test_master_audio_mux.py`, `tests/test_obs_publish.py`. | **CONFIRMED** |
| **OTR_WorkflowValidator** | `nodes/otr_workflow_validator.py:1-200` | `workflow_json_path` | LiteGraph JSON graph structure | Validates node types, links, and widget values. Does not parse episode ledger. | **Non-consumer of episode ledger.** | `tests/test_workflow_validator.py`. | **CHECKED-NOT-A-CONSUMER** |
| **OTR_VideoDirector** | `nodes/otr_video_director.py:1-200` | Direct node widgets (fps, canvas dimensions, model combos) | Node input widgets | Emits `video_policy_json`. Does not read episode ledger. | **Non-consumer of episode ledger.** | `tests/test_video_director.py`. | **CHECKED-NOT-A-CONSUMER** |
| **OTR_ImageDirector** | `nodes/otr_image_director.py:1-200` | Direct node widgets (granularity, fresh_cap, seeds) | Node input widgets | Emits `image_policy_json`. Does not read episode ledger. | **Non-consumer of episode ledger.** | `tests/test_image_director.py`. | **CHECKED-NOT-A-CONSUMER** |

---

## 4. Chronological Mutation Ledger: Construction vs. Post-Freeze Writes

The ledger undergoes two distinct mutation regimes across its lifecycle:

### Phase A: Pre-Freeze Construction & Narrative Seal (Phase 0 -> Phase 10)
All mutations in this phase are owned by the Writer, Story Pack Overlays, and the Freeze Cascade.

1. **Initialization (`nodes/production_ledger.py:590-640`):**
   - Allocates root dictionary: `schema_version = "l4-2026-08-07"`, `episode_id = "pending_<timestamp>"`, empty lists for `cast`, `scenes`, `shots`, `beats`, `lines`, `music`, `clips`, `audio_gates`, `transitions`.
   - Initializes `meta.paths` with per-episode subdirectories (`audio/`, `stills/`, `videos/`, `composited/`, `transcripts/`).
2. **Outline & Beat Initialization (`nodes/production_ledger.py:740-800`):**
   - Populates `beats[]` with `beat_id`, `scene_id`, `goal`, `conflict`, `emotional_shift`, `target_words`, `speaker`.
   - Initializes `lines[]` skeleton rows from outline beats (`init_lines_from_outline`).
3. **Dialogue Composition & Text Metrics (`nodes/_otr_line_composer.py:400`, `nodes/production_ledger.py:1000-1100`):**
   - Writes `lines[i].text`, `lines[i].speaker`, `lines[i].char_id`, `lines[i].speaker_role`.
   - Calculates and stamps `canonical_char_count` and `canonical_word_count` on all lines and totals on `meta.text_metrics`.
4. **Story Pack & Authorship Seal (`nodes/_otr_content_authorship.py:80-140`):**
   - Stamps `meta.source_bank`, `meta.story_contract`, `meta.content_authorship = {"authorship_hash": ..., "mode": ...}`.
5. **Phase 0 Audit (`nodes/_otr_freeze_cascade.py:120`, `nodes/_otr_ledger_freeze.py:700`):**
   - Stamps `meta.gap_audit_pre`.
6. **D3 Role Sweep & Pronunciation Readiness (`nodes/_otr_freeze_cascade.py:450-490`, `nodes/_otr_readiness.py:220-250`):**
   - Under `inline_safety_cleanup` policy, coerces `lines[i].speaker_role = "character"` for real cast members.
   - Stamps `lines[i].text_for_tts` (pronunciation expansions) and `lines[i].compose_flags`.
7. **Phase 8 Video Readiness & Telemetry (`nodes/_otr_readiness.py:380`, `nodes/_otr_word_delivery.py:280`):**
   - Stamps `meta.video_readiness` and `meta.word_delivery_telemetry`.
8. **Phase 10 Gap Audit Post & Structural Seal (`nodes/_otr_ledger_freeze.py:725-850`, `nodes/_otr_freeze_cascade.py:530-580`):**
   - Asserts all narrative invariants.
   - Stamps `meta.cleanup_locked = True`, `meta.freeze_timestamp = ISO-8601`, `meta.freeze_verdict = "frozen_clean" | "frozen_with_warns"`, `meta.gap_audit_post`, `meta.freeze_capability_receipt`.
   - Serializes to wire `script_json` and `v2_ledger_json`. Persists to disk via `_persist_cascade_meta()`.

---

### Phase B: Post-Freeze Execution Writes (The Multi-Writer Downstream Plane)
These mutations occur **after** Phase 10 validation and write directly to the in-flight disk ledger or emit transformed wire dictionaries:

1. **CastLock (`nodes/cast_lock.py:205-316`):**
   - Mutates `cast[]` in-place: stamps `voice_preset`, `presentation_gender`, `tts_model`, `voice_params`, `voice_route_id`, `voice_spec`.
   - Stamps `meta.cast_lock_revision`, `meta.cast_voice_policy`, `meta.delivery_profile_id`, `meta.delivery_profile_version`, `meta.voice_bank_id`, `meta.char_voice_engine`, `meta.announcer_voice_engine`.
   - Calls `production_ledger.stamp_durable(sections={"cast": ...}, source="cast_lock")`.
2. **Audio Engines - Character & Announcer (`nodes/_otr_voice_node_common.py:1060-1165`):**
   - Mutates `lines[]` in-place on disk: stamps `tts_engine`, `voice_preset`, `render_ms`, `generated_dur_s`, `audio_sample_hash`, `sample_rate`, `voice_route_id`, `audio_cache_key`, `audio_sha256`, `provider_model_id`.
   - Flushes via `_persist_ledger_stamps(meta, ledger_stamps)`.
3. **Theme Music Engine (`nodes/stable_audio_theme.py:280-330`):**
   - Mutates `music[]` in-place on disk: stamps `wav_path`, `start_s`, `dur_s`, `cue_spec_sha256`, `music_render_status`.
   - Stamps `meta.music_theme_render_ms`. Saves via `save_ledger_safe()`.
4. **Scene Sequencer (`nodes/scene_sequencer.py:1095-1145`):**
   - Mutates `lines[]` in-place on disk: stamps `start_s`, `dur_s`, `start_s_space = "scene_audio"`.
   - Appends record to `audio_gates[]` (`gate_name = "post_scene_sequencer"`).
   - Stamps `meta.phase_ms.scene_sequencer`, `meta.git_commit`. Saves via `save_ledger_safe()`.
5. **Audio Enhance (`nodes/audio_enhance.py:440-455`):**
   - Appends record to `audio_gates[]` (`gate_name = "post_audio_enhance"`).
   - Stamps `meta.phase_ms.audio_enhance`. Saves via `save_ledger_safe()`.
6. **Episode Assembler (`nodes/scene_sequencer.py:1480-1890`):**
   - Shifts `lines[i].start_s` and `clips[i].start_s` from `scene_audio` space to `master_mix` space.
   - Shifts `music[i].start_s` to `master_mix` space.
   - **Injects synthetic music rows into `lines[]`:** `lines.append({"line_id": "music_<cue>_001", "speaker": "RADIO", "speaker_role": "music_open"|"music_inter"|"music_close", "mirrored_from": "music", ...})`.
   - **Re-sorts entire `lines[]` array chronologically by `start_s`.**
   - Appends crossfade boundaries to `transitions[]`.
   - Appends record to `audio_gates[]` (`gate_name = "post_episode_assembler"`).
   - Stamps `meta.phase_ms.episode_assembler`. Saves via `save_ledger_safe()`.
7. **Signal Lost Video / Episode Renamer (`nodes/production_ledger.py:310-440`, `nodes/video_engine.py`):**
   - **Mutates root `episode_id`:** changes from `pending_<timestamp>` to title slug (e.g. `signal_lost_vances_promise_20260813_120000`).
   - Renames physical folder on filesystem.
   - Traverses entire ledger and **rebases all file paths** (`_rebase_episode_local_paths`).
   - Stamps `final_audio_path`, `final_video_path`, `total_episode_dur_s`, `meta.paths`, `meta.title_card_plan`.
8. **Shot Lock (`nodes/otr_shot_lock.py:1887-1928`):**
   - Rehydrates post-audio timing from disk via `overlay_audio_timing(strict=True)`.
   - Injects opening-music synthetic beat `open_music_b000` into `beats[]`.
   - Creates and populates root `video` section: `video_revision`, `policy_version = 2`, `device_policy`, `dtype_policy`, `max_render_frames`, `canonical_canvas`, `fps`, `execution_groups[]`, `roles`, `roles_effective`, `routing_env_snapshot`, `shots[]`, `clip_budget`.
   - Stamps `meta.video_revision`. Emits `patched_ledger_json`.
9. **Image Gen Dispatcher (`nodes/otr_image_gen_dispatcher.py:1700-1715`):**
   - Creates and populates root `images` dictionary.
   - Stamps `shots[i].png_path` and `cast[i].portrait_path`.
   - Stamps `meta.image_gen_receipt` via `stamp_durable()`.
10. **Video Render Batch (`nodes/otr_video_render_batch.py:175-235`, `render_driver.py:4550-4650`):**
    - Mutates `clips[]` in-place: stamps `humo_render_ms`, `mp4_dur_s`, `mp4_frames`, `warmup_pad_ms`, `audio_fed_to_humo_dur_s`, `oom_recovery_count`.
    - Stamps `meta.render_engines` receipt via `stamp_durable()`.
    - Stamps `meta.audio_motion_profiles`. Saves via `save_ledger_safe()`.
11. **Silent Composite, Procgen Blend & Caption Burn (`nodes/otr_silent_composite.py:240`, `nodes/otr_post_upscale_procgen_blend.py:250`, `nodes/otr_caption_burn.py:120`):**
    - Stamps `meta.phase_ms.silent_composite`, `meta.phase_ms.post_upscale_procgen_blend`, `meta.phase_ms.caption_burn`.
12. **Credits Roll (`nodes/otr_credits_roll.py:380`):**
    - Stamps `meta.credits_receipt`.
13. **Master Audio Mux (`nodes/otr_master_audio_mux.py:530-545`):**
    - Publishes file to `otr/obs/<episode_id>.mp4`.
    - Stamps `final_audio_path`, `final_video_path`, `meta.obs_final_path`, `meta.paths.obs_final`, `meta.phase_ms.master_audio_mux`.
    - Saves via `save_ledger_safe()`.

---

## 5. Field-Level Contract Table

### Root Object (`dict`)
| Field | Type | Owner | Requirement Status | Consumers | Invariants & Schema Constraints | Default Value | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `schema_version` | `str` | Producer (`_otr_ledger.py`) | Required | All consumers, Validators | Must match `^l[1-4]-` or `"l4-2026-08-07"`. Checked in Phase 10 (`_check_schema_version_current`). | `"l4-2026-08-07"` | **CONFIRMED** |
| `episode_id` | `str` | Producer / Renamer | Required | All file resolvers, OBS Publish, Dispatchers | Must be non-empty string. Starts as `pending_<ts>`, renamed to episode title slug. | `"pending_00000000_000000"` | **CONFIRMED** |
| `commit` | `str` | Producer / Phase 10 | Optional / Provenance | CreditsRoll, GapAudit | Git SHA of repo when generated. Stamped in Phase 10. | `""` | **CONFIRMED** |
| `cast` | `list[dict]` | Writer / CastLock | Required | Voice Nodes, Captions, Credits, ShotLock, Image Gen | List of cast member objects. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `scenes` | `list[dict]` | Writer (Outline) | Required | Sequencer, ShotLock, PromptGen | List of scene definitions. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `shots` | `list[dict]` | Writer / ShotLock | Required | ShotLock, Image Gen, Video Render | Planned camera shots. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `beats` | `list[dict]` | Writer (Outline) | Required | Sequencer, ShotLock, Video Render | Narrative beat structure. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `lines` | `list[dict]` | Writer / Sequencer | Required | All Voice Nodes, Sequencer, Assembler, Captions, Credits | Dialogue and narrator lines. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `music` | `list[dict]` | Writer / ThemeMusic | Required | ThemeMusic, Sequencer, Assembler, Credits | Music cues. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `clips` | `list[dict]` | ShotLock / VideoRender | Required | Video Render, Compositor, Credits | Rendered video clip records. Required in `_REQUIRED_TOP_LEVEL_LISTS`. | `[]` | **CONFIRMED** |
| `audio_gates` | `list[dict]` | Audio Nodes / Sequencer | Optional / Diagnostic | Pipeline Audits, Test Suites | Audio tripwire records (SHA256 of first 1024 bytes of audio streams). | `[]` | **CONFIRMED** |
| `transitions` | `list[dict]` | EpisodeAssembler | Optional / Diagnostic | Diagnostic tools | Crossfade boundary timestamps and durations. | `[]` | **CONFIRMED** |
| `video` | `dict` | ShotLock | Post-Audio Required | VideoRenderBatch, RenderDriver | Video execution plan, canonical canvas, execution groups, effective roles. | Absent pre-ShotLock | **CONFIRMED** |
| `images` | `dict` | ImageGenDispatcher | Post-Image Required | VideoRenderBatch, Compositor | Generated image references and manifests. | Absent pre-ImageGen | **CONFIRMED** |
| `final_audio_path` | `str` | SignalLost / MasterMux | Terminal Publish | Terminal publication check | Absolute path to final assembled audio WAV. | `None` / `""` | **CONFIRMED** |
| `final_video_path` | `str` | SignalLost / MasterMux | Terminal Publish | Terminal publication check | Absolute path to final assembled video MP4. | `None` / `""` | **CONFIRMED** |
| `total_episode_dur_s`| `float` | Sequencer / Assembler | Optional / Telemetry | Diagnostics, OBS Publish | Master episode audio duration in seconds. | `0.0` | **CONFIRMED** |
| `meta` | `dict` | Multi-owner | Required | All downstream consumers | Metadata dictionary containing policies, receipts, telemetry, paths. | `{}` | **CONFIRMED** |

---

### Cast Elements (`ledger["cast"][i]`)
| Field | Type | Owner | Requirement Status | Consumers | Invariants & Schema Constraints | Default Value | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `char_id` | `str` | Writer / Casting | Required | CastLock, Voice Nodes, Captions, Credits | Unique identifier (e.g. `"c01"`, `"c02"` or `"announcer"`). Must be unique across `cast[]`. | Required | **CONFIRMED** |
| `name` | `str` | Writer / Casting | Required | Captions, Credits, Reviewer | Character display name. Must be uppercase / title case. Announcer must have name `"ANNOUNCER"`. | `""` | **CONFIRMED** |
| `voice_preset` | `str` | CastLock | Post-CastLock Required | Voice Nodes, Credits | Voice identifier (e.g. Bark `v2/en_speaker_6`, Kokoro `bm_fable`, or clone ID). | `""` pre-lock | **CONFIRMED** |
| `presentation_gender`| `str` | Writer / CastLock | Required | CastLock, Clone Voice Picker | Allowed values: `"male"`, `"female"`, `"neutral"`. Enforced by `_check_per_cast_invariants`. | `"neutral"` | **CONFIRMED** |
| `tts_model` | `str` | CastLock | Optional | Voice Node Dispatcher | Explicit engine override for character (e.g. `"kokoro"`, `"indextts2"`). | `None` | **CONFIRMED** |
| `voice_route_id` | `str` | CastLock | Optional / Proved Route | Voice Node Receipt Verifier | Identifier of qualified route in voice bank. | `None` | **CONFIRMED** |
| `voice_spec` | `dict` | CastLock | Optional | Voice Engines | Full resolved voice specification block. | `None` | **CONFIRMED** |
| `portrait_path` | `str` | ImageGenDispatcher | Optional | Video Engines (HuMo / Still Animators) | Absolute on-disk path to character portrait PNG. | `None` | **CONFIRMED** |

---

### Line Elements (`ledger["lines"][i]`)
| Field | Type | Owner | Requirement Status | Consumers | Invariants & Schema Constraints | Default Value | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `line_id` | `str` | Writer / Outline | Required | All consumers, Sequencer, Patchers | Unique line identifier (`"l001"`, `"b001"`). Must be strictly unique across `lines[]` (G8 check). | Required | **CONFIRMED** |
| `beat_id` | `str` | Writer / Outline | Required | ShotLock, Video Render | Corresponding beat ID from `beats[]`. Must refer to valid beat. | `""` | **CONFIRMED** |
| `scene_id` | `str` | Writer / Outline | Required | Sequencer, ShotLock | Corresponding scene ID from `scenes[]`. | `""` | **CONFIRMED** |
| `shot_id` | `str` | Writer / ShotLock | Optional | ShotLock, Image Gen | Bound shot ID from `shots[]`. | `None` | **CONFIRMED** |
| `speaker` | `str` | Writer | Required | Captions, Script Doctor | Character display name. Must match a character in `cast[]`. | `""` | **CONFIRMED** |
| `char_id` | `str` | Writer / Casting | Required | Voice Nodes, Captions, Sequencer | Character ID. Must resolve to a valid row in `cast[]` or `"announcer"`. | `""` | **CONFIRMED** |
| `speaker_role` | `str` | Writer / Freeze Cascade | Required | Sequencer, Voice Nodes, Captions | Valid values: `"character"`, `"announcer"`, `"music_open"`, `"music_inter"`, `"music_close"`. Legacy `"sfx"` raises! | `"character"` | **CONFIRMED** |
| `text` | `str` | Writer / Script Composer | Required | Captions, Credits, Image Prompt, Motion Clause | Authored dialogue text. Preserves performance directions (e.g. parentheticals) by design! | `""` | **CONFIRMED** |
| `text_for_tts` | `str` | Freeze Cascade (Phase 7) | Required for TTS | Voice Nodes, Audio Engines | Pronunciation-expanded text for TTS engines (numbers spelled out, abbreviations expanded). | Absent -> fallback to `text` | **CONFIRMED** |
| `start_s` | `float` | Sequencer / Assembler | Post-Audio Required | ShotLock, Video Render, Captions | Timestamp in seconds. Begins in `scene_audio` space, shifted to `master_mix` space. | `None` pre-audio | **CONFIRMED** |
| `dur_s` | `float` | Sequencer / Assembler | Post-Audio Required | ShotLock, Video Render, Captions | Audio clip duration in seconds. Must be > 0.0 for rendered lines. | `None` pre-audio | **CONFIRMED** |
| `start_s_space` | `str` | Sequencer / Assembler | Post-Audio Required | Assembler, ShotLock | Coordinate space: `"scene_audio"` (pre-assembler) -> `"master_mix"` (post-assembler). | `None` pre-audio | **CONFIRMED** |
| `tts_engine` | `str` | Voice Nodes | Post-Audio Telemetry | Telemetry Audits | Concrete TTS engine that synthesized line (`"indextts2"`, `"kokoro"`, `"bark"`). | `None` | **CONFIRMED** |
| `render_ms` | `int` | Voice Nodes | Post-Audio Telemetry | Telemetry Audits, Credits | Milliseconds spent in audio engine synthesis (or `0` on cache hit). | `None` | **CONFIRMED** |
| `audio_sample_hash`| `str` | Voice Nodes | Post-Audio Telemetry | Audio Gate Audits | SHA256 hex digest of synthesized audio waveform tensor. | `None` | **CONFIRMED** |
| `mirrored_from` | `str` | EpisodeAssembler | Synthetic Rows Only | Assembler, Video Composite | Set to `"music"` for synthetic music cue rows injected by EpisodeAssembler. | `None` | **CONFIRMED** |

---

### Metadata Object (`ledger["meta"]`)
| Key | Type | Owner | Requirement Status | Consumers | Invariants & Purpose | Default Value | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `episode_title` | `str` | Writer | Required | CreditsRoll, SignalLost, Assembler | Human-readable title of episode. Required by CreditsRoll (raises `CreditsDataError` if missing). | `""` | **CONFIRMED** |
| `source_bank` | `str` | Writer | Required | CreditsRoll, FreezeCascade | Story bank identifier (`"scifi_news"`, `"scifi_fable2"`, `"original_radio"`). Required by CreditsRoll. | `""` | **CONFIRMED** |
| `visual_style` | `str` | Writer | Required | CreditsRoll, ImagePromptGen | Visual style identifier (`"sci_fi_radio"`, `"noir_radio"`). Required by CreditsRoll. | `""` | **CONFIRMED** |
| `cleanup_locked` | `bool` | Freeze Cascade (Phase 10) | Required Seal | Freeze Cascade, Tests | Set to `True` when Phase 10 validation passes. | `False` | **CONFIRMED** |
| `freeze_timestamp`| `str` | Freeze Cascade (Phase 10) | Required Seal | Dispatchers, PostAudioJoin | ISO-8601 timestamp string when freeze passed. Used as proof of run identity. | `None` | **CONFIRMED** |
| `freeze_verdict` | `str` | Freeze Cascade (Phase 10) | Required Seal | CastLock, Freeze Gate | `"frozen_clean"`, `"frozen_with_warns"`, or `"needs_full_rerun"`. CastLock halts on `"needs_full_rerun"`. | `None` | **CONFIRMED** |
| `content_authorship`| `dict` | Story Pack / Writer | Required Seal | Freeze Cascade (Phase 10) | Contains `authorship_hash` and `authorship_policy` (`"content_owned_readonly"`). | `{}` | **CONFIRMED** |
| `render_engines` | `dict` | VideoRenderBatch | Post-Render Required | CreditsRoll | Map of video engines and execution histograms. Required by CreditsRoll. | Absent pre-render | **CONFIRMED** |
| `image_engines` | `dict` | ImageDirector / Gen | Post-Image Required | CreditsRoll | Map of image generation models used. Required by CreditsRoll. | Absent pre-image | **CONFIRMED** |
| `music_engine` | `str` | StableAudioTheme | Post-Music Required | CreditsRoll | Name of music engine (`"stable_audio_3"`). Required by CreditsRoll. | Absent pre-music | **CONFIRMED** |
| `cast_lock_revision`| `int` | CastLock | Post-CastLock Required | Voice Nodes, Diagnostics | Integer counter incremented on each CastLock pass. | `0` | **CONFIRMED** |
| `cast_voice_policy`| `str` | CastLock | Post-CastLock Required | Diagnostics, Telemetry | `"auto_registry"` or `"preserve_ledger"`. | `"preserve_ledger"` | **CONFIRMED** |
| `voice_device` | `str` | CastLock | Post-CastLock Required | Voice Nodes, ThemeMusic | Explicit compute device (`"cuda"`, `"cpu"`, `"mps"`). Replaces legacy waterfalls. | `"cuda"` | **CONFIRMED** |
| `paths` | `dict` | ProductionLedger | Required | All file writers, Dispatchers | Workspace layout paths (`audio_dir`, `stills_dir`, `videos_dir`, `obs_final`). | Initialized in `_build_meta_paths` | **CONFIRMED** |

---

## 6. Schema / Producer / Consumer Contradictions & Lossy Boundaries

1. **The Post-Freeze `lines[]` Cardinality & Ordering Mutation (CONFIRMED):**
   - *Contradiction:* Phase 10 validates `lines[]` as the authoritative narrative contract, verifying exact word counts, line counts, and line ID uniqueness.
   - *Mutation:* `OTR_EpisodeAssembler` (`nodes/scene_sequencer.py:1650-1830`) mutates `lines[]` post-freeze by injecting synthetic rows (`mirrored_from="music"`) chunked <= 22s and **re-sorting `lines[]` chronologically by `start_s`**.
   - *Consequence:* A downstream consumer reading `lines[]` before `EpisodeAssembler` (e.g. `OTR_BatchCharacterVoices`, `OTR_CastLock`) sees only dialogue lines in authoring order. A consumer reading `lines[]` after `EpisodeAssembler` (e.g. `OTR_CaptionBurn`, `OTR_ShotLock`) sees a larger array containing synthetic music lines in chronological audio order.

2. **The In-Flight Singleton vs. ComfyUI Wire Dictionary Divergence (CONFIRMED):**
   - *Lossy Boundary:* ComfyUI passes ledger state across node sockets as serialized JSON strings (`script_json`, `ledger_json`, `patched_ledger_json`). However, nodes writing media assets (`nodes/scene_sequencer.py`, `nodes/_otr_voice_node_common.py`, `nodes/stable_audio_theme.py`) write directly to disk via `in_flight_ledger_path()`.
   - *Hazard:* If a downstream node reads only its wire input (`script_json`) without rehydrating from disk, it receives stale state missing audio durations, sample hashes, and timing offsets.
   - *Mitigation:* `nodes/otr_shot_lock.py:1795` implements `overlay_audio_timing(strict=True)` specifically to bridge this divergence, rehydrating disk timing onto the wire ledger.

3. **Episode Directory Renaming & Path Rebasing (CONFIRMED):**
   - *Boundary:* `OTR_SignalLostVideo` triggers `Ledger.rename_episode()` (`nodes/production_ledger.py:310-440`), which moves `output/otr/episodes/pending_<ts>/` to `output/otr/episodes/<slug>/` and walks all string values in the ledger to rebase paths.
   - *Hazard:* Any downstream node holding a stale in-memory path captured before the rename (e.g. `master_audio_path` in `nodes/otr_master_audio_mux.py:320-350` or `stills_dir` in `nodes/otr_image_gen_dispatcher.py:440-495`) fails to find the file unless it executes an explicit re-resolve probe against the renamed directory.

4. **Speaker Role vs. Cast Member Identity Asymmetry (CONFIRMED):**
   - *Contradiction:* In `_otr_casting.py:948`, the Announcer is often pre-baked into `cast[0]` with `char_id = "c01"` or `char_id = "announcer"`. However, in `_otr_cast_contract.py:260`, character IDs are assigned alphabetically (`c01`, `c02` for real characters).
   - *Enforcement:* `_otr_ledger_freeze.py:515-535` strictly forbids any cast member named `"ANNOUNCER"` from carrying `char_id != "announcer"` or a Bark voice preset. `_otr_ledger_reviewer.py:apply_deterministic_cast_repairs` explicitly refuses to map character lines onto the announcer (BUG-LOCAL-276/271 fix).

5. **Captions Burn vs. TTS Spoken Text Intentional Divergence (CONFIRMED):**
   - *Boundary:* In `nodes/otr_caption_burn.py` / `nodes/_otr_captions.py:19-40`, open SDH captions burn the RAW authored `lines[i].text`, including parenthetical performance directions (e.g. `"(forcefully winding the clock)"`).
   - *Divergence:* TTS engines speak `lines[i].text_for_tts` or run `clean_spoken_text()` (`nodes/_otr_script_prep.py:21`), which strips parentheticals. This divergence is intentional per operator directive 2026-08-05.

6. **Strict No-Fallback Failures in Late Terminal Nodes (CONFIRMED):**
   - *Hazard:* `OTR_CreditsRoll` (`nodes/otr_credits_roll.py:118-125`) strictly requires `meta.episode_title`, `meta.visual_style`, `meta.render_engines`, `meta.image_engines`, `meta.music_engine`, and `meta.source_bank`. If an upstream node (e.g. `OTR_VideoRenderBatch` or `OTR_StableAudioTheme`) fails to stamp its durable receipt, `OTR_CreditsRoll` raises `CreditsDataError` at the very end of the rendering pipeline.

---

## 7. Test Inventory & Uncovered Risks

### Current Test Inventory (10,410 tests in OTR suite / 278 in Bug Bible)
1. **Core Ledger Unit Tests (`tests/test_production_ledger.py`):**
   - Covers: atomic save, directory renaming, path rebasing, text metrics calculation, durable disk merge, and audio identity hashing.
2. **Freeze & Gap Audit Invariant Tests (`tests/test_otr_ledger_freeze.py`, `tests/test_otr_freeze_cascade.py`):**
   - Covers: null rejection, list presence (`_REQUIRED_TOP_LEVEL_LISTS`), G8 line ID uniqueness, G14 provenance block check, G15 scene coherence, and content-owned read-only policy enforcement.
3. **Consumer Helper Tests (`tests/test_otr_ledger_consumers.py`):**
   - Covers: `load_ledger`, `iter_lines` skip filtering, `cast_lookup`, and `audit_post_freeze_writeback`.
4. **Voice & Cast Contract Tests (`tests/test_cast_contract.py`, `tests/test_voice_bank.py`, `tests/test_audio_byte_identical.py`):**
   - Covers: deterministic voice resolution, route verification, and audio sample hashing.
5. **Sequencer & Timeline Tests (`tests/test_sequencer_ledger.py`, `tests/test_scene_sequencer.py`):**
   - Covers: timeline positioning, audio gate calculation, and master mix offset shifting.

### Uncovered Risks & False Confidence Areas (INFERENCE)
1. **The In-Memory Socket vs. Disk Merge Disconnect:** Many unit tests mock `load_ledger_safe` or pass a single in-memory dictionary directly between functions, bypassing the real ComfyUI socket serialization / disk-singleton reload cycle. This provides false confidence regarding race conditions or stale-cache reads during headless runs.
2. **Post-Freeze Line Array Mutations in Downstream Tooling:** Offline audit scripts (e.g. `scripts/audit_otr_full_run.py`) expect `lines[]` to match the exact count from outline composition. Synthetic music mirror injection by `EpisodeAssembler` changes `len(lines)` post-freeze, which can trip external assertions unless filtered by `mirrored_from is None`.
3. **Episode Rename Timing Sensitivity:** If `SignalLostVideo` renames the episode directory while an asynchronous image generation or video batch is holding an open file handle under the old `pending_<ts>` directory, Windows file-locking raises `PermissionError` during `os.replace`.

---

## 8. Recommended Ledger Bible Artifact Set

To bless and document the ledger as the immutable single source of truth, the following artifact set is recommended:

1. **`docs/LEDGER_BIBLE.yaml` (Portable Cross-Repository Contract):**
   - Modeled after `BUG_BIBLE.yaml`.
   - Defines every top-level section, required list, field data type, cardinality, ownership lifecycle phase, permitted mutations, and fail-closed validation rules.
2. **`schemas/otr_ledger_schema_l4.json` (Machine-Readable JSON Schema):**
   - Strict JSON Schema (Draft 2020-12) validating Phase 10 frozen state as well as terminal published state.
   - Enforces pattern matching on IDs (`line_id`, `beat_id`, `scene_id`, `shot_id`, `char_id`), enums on `speaker_role`, and required nested blocks in `meta`.
3. **`nodes/_otr_ledger_contract.py` (Typed Python Models & Validating Wrappers):**
   - Pure Python dataclasses or Pydantic/TypedDict models defining `LedgerRoot`, `CastRow`, `LineRow`, `BeatRow`, `SceneRow`, `ShotRow`, `MusicRow`, `ClipRow`, `MetaBlock`.
   - Replaces loose dict access (`ln.get("text")`) with typed accessors across consumers.
4. **`tests/test_ledger_bible_contract.py` (Executable Contract Test Suite):**
   - Comprehensive test suite validating synthetic and real production ledger fixtures against `LEDGER_BIBLE.yaml` and `otr_ledger_schema_l4.json`.

---

## 9. First Bounded, No-GPU Implementation Chunk

**Objective:** Establish the foundational Ledger Bible definition, schema validation, and test harness without touching GPU workloads, workflow JSON, or altering production behavior.

### Deliverables in Chunk 1:
1. **Create `docs/LEDGER_BIBLE.yaml`:**
   - Author the complete YAML contract documenting root fields, arrays, meta keys, lifecycle phases (Creation -> Phase 10 Freeze -> Media Execution -> Terminal Publish), and producer/consumer ownership.
2. **Create `schemas/otr_ledger_schema_l4.json`:**
   - Author the formal JSON Schema corresponding to `CURRENT_SCHEMA_VERSION = "l4-2026-08-07"`.
3. **Create `tests/test_ledger_bible_contract.py`:**
   - Implement test suite:
     - `test_all_production_fixtures_comply_with_schema`: Loads all existing sample fixtures in `tests/fixtures/` and asserts compliance.
     - `test_phase10_freeze_invariants_match_bible`: Asserts `_otr_ledger_freeze.py` rules strictly reflect `LEDGER_BIBLE.yaml`.
     - `test_post_freeze_writeback_conforms_to_bible`: Asserts post-freeze updates from `cast_lock`, `scene_sequencer`, and `render_driver` obey the declared mutation rules.
4. **Verify Test Suite:**
   - Run via Windows venv: `pytest tests/test_ledger_bible_contract.py -q -p no:cacheprovider`. Ensure 100% pass rate.

---

## 10. Runtime Unknowns (Requiring Focused Probe)

The following items cannot be fully answered by static inspection alone and warrant a non-GPU dry-run or inspection of live episode logs:

1. **Frequency of `overlay_audio_timing` Fallback in Production (`UNVERIFIED`):**
   - *Question:* In live production runs, does `OTR_ShotLock` ever fail to find the in-flight disk singleton when `audio_done` is provided, or is the join 100% reliable across diverse ComfyUI runner configurations?
2. **Actual Peak Memory Overhead of In-Memory Wire Ledgers (`UNVERIFIED`):**
   - *Question:* During 25-minute extended radio dramas, does serializing and deserializing the wire ledger JSON strings across 20+ ComfyUI nodes introduce measurable GC latency or memory fragmentation on Windows?
3. **Edge Cases in Windows File Locking During Mid-Run Episode Rename (`UNVERIFIED`):**
   - *Question:* Under heavy I/O where background file watchers (or audio playback tools) inspect the `pending_<ts>` directory, does `Ledger.rename_episode()` ever experience transient `PermissionError` on Windows `os.replace`?

---

*End of Audit Report.*
