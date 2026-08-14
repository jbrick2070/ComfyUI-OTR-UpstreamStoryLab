# Codex independent Ledger Bible audit

Audit date: 2026-08-13

Model and credit rung: GPT-5.6 Sol, local repo audit/coding rung; no paid
external reviewer spend.

Review routing actually read: operator directive dated 2026-08-11 in the live
OTR `docs/GO_FORWARD_PLAN.md`; the full r1-r4 kibitz gate is suspended. Codex
consult is reserved for a genuine quandary/third attempt and Sonnet 5 for
post-code QA. This audit used read-only parallel code census lanes, with this
Codex window grounding and judging their claims against the Windows checkout.

Production checkout audited:

`C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OldTimeRadio`

Production baseline at audit start: `8c3ed304`, schema
`l4-2026-08-07`, canonical workflow `workflows/otr_canonical.json`.

## Executive verdict

The current production ledger is one mutable JSON dictionary with many legal
writers. It is not wholly frozen at Phase 10, and no authored-core mutation
guard is enforced after Phase 10.

Phase 10 currently does three things:

1. runs selected structural/authorship checks;
2. stamps `meta.cleanup_locked`, `meta.freeze_timestamp`, and
   `meta.freeze_verdict`;
3. returns the same mutable ledger object.

`cleanup_locked` has no production reader. Phase 10 does not deep-copy the
ledger, wrap nested containers, hash the complete authored graph, or make
`Ledger.save()` reject a changed story. Calling it twice refreshes the
timestamp. Evidence:

- `nodes/_otr_ledger_freeze.py:901-954`
- `nodes/_otr_freeze_cascade.py:214-306`
- `nodes/production_ledger.py:705-731,1432-1768`
- zero production reads in the repository-wide `cleanup_locked` census

The correct target is still one ledger JSON file, but with two explicit planes
and two seals:

```text
ledger envelope
├── story_ledger       immutable authored/source/graph/program truth
├── story_seal         canonical SHA-256 over story_ledger
├── production_state   phase-owned append-only attempts and media receipts
└── final_seal         terminal digest after publication and audit
```

The Story Lab emits `story_ledger` plus `story_seal`; the two production fields
are null. OTR may build `production_state`, but every phase must revalidate the
story digest. After `final_seal`, neither plane may change.

This is not a cosmetic rename of the current system. It is the contract needed
to make the operator's “ledger is the Bible” rule executable.

## What the current workflow actually does

The canonical workflow has two visible ledger branches and several hidden disk
joins:

```text
LedgerScriptWriter
  -> LedgerFreezeCascade
       -> CastLock
            -> CharacterVoice
            -> AnnouncerVoice
            -> StableAudioTheme
            -> SceneSequencer -> AudioEnhance -> EpisodeAssembler
       -> ShotLock
            -> MetaBriefImagePrompt
            -> ImageDispatcher -> VideoRenderBatch

VideoRenderBatch -> clip manifest -> SilentComposite -> scopes/blend
durable singleton -> CaptionBurn (read)
durable singleton -> CreditsRoll (read)
active singleton  -> MasterAudioMux (terminal write after publish)
```

Exact canonical link IDs are `230` (writer→freeze), `234`
(freeze→CastLock), `235-237` and `277` (CastLock→voice/music/sequencer), `252`
(freeze→ShotLock), `255-256` (ShotLock→prompt/dispatcher), and `260`
(dispatcher→VideoRenderBatch), all in `workflows/otr_canonical.json:1`.

A repository scan found 59 workflow JSON files: 51 full OTR variants preserve
this ledger-consumer topology, one is writer+freeze story-only, and seven are
stock/native non-OTR graphs. Widget and engine routes vary; the ledger handoff
set does not.

## Chronological mutation finding

The current ledger changes after the claimed freeze by design:

| Stage | Current mutation | Durable truth |
|---|---|---|
| Freeze wrapper | adds `freeze_unload_ok` after the last cascade save | wire/live memory only |
| CastLock | voice identities and receipts; can locally reroute announcer role | cast/meta durable; reroute wire-only |
| Voice render | TTS engine, cache, hash, duration, provider fields per `line_id` | durable line patches |
| Theme | engine receipt; cue manifest returned | meta durable; manifest wire |
| Sequencer | line timing, music reconciliation, audio gates | durable, but save result ignored |
| AudioEnhance | phase/gate receipt | best effort |
| EpisodeAssembler | master hash, timing shifts, music rows, mirror lines, line reorder, transitions | best effort; may still emit `audio_done` |
| SignalLostVideo | pending→final rename, path rebase, procgen/final paths | best effort |
| ShotLock | post-audio overlay and `video.shots` plan | wire only |
| ImageDispatcher | images and engine receipts | images/meta durable; some local corrections wire-only |
| VideoRenderBatch | render engines and audio-motion receipt | those receipts durable; shots wire; clips filesystem+manifest |
| Post-blend | final path and blend forensics | best effort |
| CaptionBurn | reads timed ledger | no ledger write |
| CreditsRoll | reads live singleton | no ledger write |
| MasterMux | publishes, then stamps final pointers | publish survives stamp failure |
| Full-run audit | audit verdict | best effort |

The complete code-cited matrix is machine-readable at
`contracts/ledger_consumer_matrix_l4.json`.

## Hard contract gaps established

### 1. Freeze is a status, not enforcement

`meta.cleanup_locked` is written but never read by production. The capability
receipt hashes ordered `line_id` plus text and the content-authorship receipt;
it does not bind cast, scenes, shots, beats, speaker ownership, facts, authored
music, or the full object. It proves a narrow cascade interval, not future
immutability (`nodes/_otr_freeze_cascade.py:214-306`).

### 2. The accepted story can still change shape

CastLock may rewrite a mis-stamped announcer line's `speaker_role` after Phase
10 (`nodes/cast_lock.py:448-534`). EpisodeAssembler removes/recreates music
mirror rows and chronologically reorders `lines[]`
(`nodes/scene_sequencer.py:1698-1830`). These are incompatible with a claim
that the complete line array is an immutable authored surface.

### 3. Source-fact lineage is lost at the durable adapter

SciFi's typed score and script artifacts carry `fact_ids`, and P5 receives them.
`_assemble_ledger()` constructs durable line rows without them, then
`production_ledger.set_lines()` has no `fact_ids` field. Evidence:

- `nodes/_otr_scifi_codex.py:467-524,1988,2067`
- `nodes/_otr_scifi_codex.py:3188-3221`
- `nodes/production_ledger.py:1252-1309`

Therefore the current durable ledger cannot prove that the final announcer
coda speaks a captured source fact. This is a direct blocker for the five-outcome
Story Lab contract.

### 4. Speaker routing and program meaning are conflated

Current media routing recognizes `character`, `announcer`, `music_open`,
`music_inter`, and `music_close`. The target story program needs semantic roles
such as `announcer_open` and `announcer_news_coda`. Those are different axes:

- `speaker_role` answers which speech engine receives a spoken line;
- `sequence_role` answers what that row means in the episode program.

Both announcer semantic roles route through `speaker_role=announcer`.
`character_dialogue` routes through `character`. Music items reference cues,
not a synthetic speaking character.

### 5. Wire, disk, manifest, and filesystem truth diverge

The Phase-10 wire is intentionally pre-audio. Later nodes frequently discover
the singleton out of band. ShotLock performs a strict post-audio overlay to
repair this split (`nodes/otr_shot_lock.py:170-540`). Video plans live on the
wire, rendered clips live in the episode filesystem and clip manifest, while
only selected render receipts reach the durable ledger. Any Bible that labels
all of these “ledger writes” without stating durability is false.

### 6. Save/version policy is not unified

`save_ledger_safe()` preserves a foreign nonempty schema version, while
`Ledger.save()` promotes merged data to the current version. There is no
registered migration graph:

- `nodes/_otr_ledger.py:335-418`
- `nodes/production_ledger.py:1432-1501`

The target rejects unknown versions and permits only a named, tested migration
edge with before/after digests.

### 7. Current failure policies are inconsistent

Some `stamp_durable()` calls fail loudly. Sequencer, assembler, enhance,
post-blend, audit, and terminal stamps are wholly or partly best effort.
MasterMux publishes before it stamps the ledger and deliberately keeps the
published result successful if the stamp fails
(`nodes/otr_master_audio_mux.py:500-569`). A final seal therefore cannot occur
until ownership and required-phase failure policy are explicit.

## Live episode classification

The August 13 `wan_ti2v` episode remains a real render success:

- 13/13 clips and 30/30 render segments;
- `RESULT SUCCESS`;
- `obs_publish OK`;
- ffprobe-valid 193.040-second H.264/AAC OBS asset;
- exact engine `wan_ti2v` delivered.

Its story content is separately failed: no announcer bookends, no factual
coda, narration/action prose in voiced rows, and cross-speaker ownership. The
decode liveness guard never fired on its accepted P3/P5. This is why the target
contract keeps `render_pass` and `content_pass` separate.

The two production evidence projections remain hash-pinned under
`fixtures/story_recovery/`. They admit the observed story defect; broader
freeze/schema observations remain contract debt and are not new PBUG/Bug Bible
entries merely because static code found them.

## Independent review of AGY's report

The raw Antigravity report correctly found the multi-writer lifecycle and the
need for separate narrative and media concerns. Five claims required
correction:

| AGY claim | Grounded verdict | Correction |
|---|---|---|
| Narrative plane is “strictly frozen at Phase 10” | Disagree | It is validated/stamped, not guarded after save. |
| Current system already has a coherent dual-plane contract | Partial | The concerns are visible, but remain mixed in one mutable dict. Two planes are the target. |
| SilentComposite stamps ledger phase metadata | Disagree | No ledger input; manifest/media only. |
| CaptionBurn stamps ledger phase metadata | Disagree | Timed-ledger read; ASS/video write only. |
| CreditsRoll stamps `meta.credits_receipt` | Disagree | Reads `get_ledger().data`; produces credits media only. |
| Video render durably writes ledger clips/shots | Disagree | Shots are wire/state-capture; clips are files+manifest; selected meta receipts alone are durable. |

AGY's raw report is preserved unedited at
`AGY_LEDGER_BIBLE_AUDIT.md`. Corrections are represented in
`contracts/ledger_consumer_matrix_l4.json`; the audit is evidence, not erased
history.

## Adopted Ledger Bible v1 boundary

The machine contract is `contracts/ledger_bible_v1.json`; the executable story
model and seal are `src/upstream_story_lab/ledger_contract.py`.

The story plane contains:

- stable accepted `episode_id`;
- title, premise, setting, and the four-value length tier;
- complete source packet, source digests, facts, and evidence references;
- cast authority with exactly one announcer;
- closed scene→shot→beat→line graph;
- every spoken line's exact speaker, route role, text, and `fact_ids`;
- music cues separate from spoken lines;
- one ordered sequence referencing every line/cue exactly once;
- five body-digest-bound outcome receipts.

The exact program is:

```text
music_open
announcer_open
character_dialogue+
music_inter*        (only when script-requested; inside the story body)
announcer_news_coda (at least one source fact)
music_close
```

No word target, duration target, scene count, movement count, prompt, provider,
model, or pass count is part of story acceptance. The fixed UI length labels
remain, but their bank-specific process mapping is deliberately postponed.

## First bounded implementation result

The Story Lab now has a pure CPU contract boundary that:

- uses strict unknown-field rejection;
- validates IDs, references, ownership, exact sequence coverage, music
  bookends, first/last announcer roles, and factual-coda linkage;
- keeps `speaker_role` separate from `sequence_role`;
- binds five semantic outcome receipts to the exact story-body digest;
- canonicalizes NFC, float-free story JSON and seals it with SHA-256;
- detects nested story changes while permitting a correctly bound production
  plane to grow.

The contract does not yet migrate or alter production OTR. Production-state
receipt schemas, the l4 adapter, save guards, workflow wiring, and final seal
belong to later transplant chunks, each with consumer characterization tests.

## Runtime unknowns left honest

- The exact production-state receipt schema for every phase has not yet been
  implemented.
- A lossless migration from existing l4 is impossible when required facts or
  semantic roles were never stored; historical records need explicit loss
  accounting and remain read-only by default.
- A current production episode satisfying all five target outcomes plus music
  topology has not yet been generated by Story Lab v1.
- The target final seal cannot be wired until terminal audit/write ordering and
  required phase failures are made explicit.

None of those unknowns requires a GPU to close at the contract stage.
