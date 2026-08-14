# OTR Ledger Bible v1

Status: blessed Story Lab story-plane contract; not yet transplanted into
production OTR. The executable model is deliberately unable to accept a
non-null production plane or final seal until their strict schemas land.

Machine authority:

- `contracts/ledger_bible_v1.json`
- `src/upstream_story_lab/ledger_contract.py`
- `contracts/ledger_consumer_matrix_l4.json` (current-production
  characterization, not the target schema)

This document explains those artifacts. Current parity tests cover the core
versions, roles, outcomes, evidence rules, and current-production corrections.
Generated full-schema/document parity is a required pre-transplant chunk.

## One file, two kinds of truth

An episode still has one ledger JSON. The file is an envelope with two planes:

```text
otr.ledger_envelope.v1
├── story_ledger
│   ├── immutable authored/source/graph/program truth
│   └── five acceptance receipts bound to body_sha256
├── story_seal
│   └── SHA-256 of the complete story_ledger
├── production_state
│   └── phase-owned attempts, media artifacts, timings and delivery receipts
└── final_seal
    └── terminal identity after required production phases, publish and audit
```

The Story Lab returns this one file with `production_state=null` and
`final_seal=null`. The current executable class rejects either field when
non-null rather than accepting an untyped future journal. OTR will fill the
production plane without changing one byte of the story plane only after its
strict receipt schemas and adapter exist. After the final seal, no ordinary
mutation is legal.

This distinction matters because “the story is accepted” and “the episode has
finished rendering” occur at different times. Pretending the entire file is
immutable at story acceptance would make truthful audio, image, video, path,
and publication receipts impossible.

Version vocabulary is exact:

| Surface | Version |
|---|---|
| envelope | `otr.ledger_envelope.v1` |
| story plane | `otr.story_ledger.v1` |
| story seal | `otr.story_seal.v1` |
| captured source packet | `otr.captured_source_packet.v1` |
| production plane | `otr.production_state.v1` |
| final seal | `otr.final_seal.v1` |
| minimum outcomes | `otr.minimum_ship.v1` |
| canonicalization | `otr.canonical-json.v1` |

## Identity

- `episode_id` identifies one accepted story edition. It never changes.
- `run_id` identifies one production execution of that story.
- `workspace_id` is the renameable directory/slug identity used by production.
- Resume retains `run_id` and appends a phase attempt.
- Rerender creates a new `run_id` for the same `episode_id` and story digest.
- Changing accepted story content creates a new sealed story and a new
  `episode_id`.

A pending directory name is not story identity. A filesystem rename must never
change the story digest.

## The immutable story plane

`story_ledger.body` owns:

- context: episode title, premise, setting, and `episode_length_tier`;
- source packet: bank ID, captured-packet artifact digest, sources, facts, and
  evidence locators; the trusted news-capture validator verifies that external
  packet digest because it is not a recursive hash of the embedded projection;
- cast: immutable character IDs, exact names, role, and description;
- scenes, shots, beats, and spoken lines as a closed graph;
- music cues as authored program requests, separate from speech, with exact
  `request_authority` (`compiler_bookend` for open/close, `script` for an
  interstitial);
- one ordered sequence referencing every line and cue exactly once.

Every spoken line contains:

- `line_id`, `scene_id`, `shot_id`, and `beat_id`;
- `char_id` and exact score-owned `speaker`;
- routing `speaker_role` (`announcer` or `character`);
- spoken `text`;
- `fact_ids`, present even when empty.

There are no action rows, stage-direction rows, narrator-prose rows, or
delivery-note rows. Visual intent and dramatic intent may live in typed graph
metadata; they are never passed to a speech consumer as dialogue.

## Routing role and sequence role are different

`speaker_role` chooses a voice route:

```text
announcer
character
```

`sequence_role` defines program meaning and order:

```text
music_open
announcer_open
character_dialogue
music_inter
announcer_news_coda
music_close
```

Thus both `announcer_open` and `announcer_news_coda` point to lines whose
`speaker_role` is `announcer`. `character_dialogue` points to a line whose
speaker route is `character`. Music roles point to `music_cue` objects, never
to a pretend speaking character.

## Required program topology

The sequence is ordered authority:

1. exactly one `music_open`, first;
2. exactly one `announcer_open`, the first spoken row;
3. one or more `character_dialogue` rows;
4. zero or more `music_inter` cues, each explicitly requested by the script and
   located inside the character-story body;
5. exactly one `announcer_news_coda`, the last spoken row;
6. exactly one `music_close`, last.

The opening introduces the story, place/time, and characters. The coda
summarizes captured real news and references at least one valid source fact.
Those semantic claims need explicit validator receipts; a JSON shape alone
cannot honestly prove what prose means.

## Five minimum outcomes

All five receipts are required and must say `pass`:

1. `ledger_integrity`
2. `news_capture`
3. `announcer_open`
4. `announcer_news_coda`
5. `music_bookends`

Each receipt names its validator/version and typed `{kind, ref_id}` evidence.
`news_capture`
must name the packet plus a fact; the opening receipt names the exact opening
line; the coda receipt names the exact coda plus one of its facts; and the
music receipt names the exact opening and closing cues. `ledger_integrity` may
use the bound body hash alone. All five are bound to the same `body_sha256`. A
receipt cannot survive a changed line, fact, speaker, cue, or order.

The trusted v1 registry is code-owned and contains exactly five identities at
validator version `1`: `otr.story_validator.ledger_integrity`,
`otr.story_validator.news_capture`, `otr.story_validator.announcer_open`,
`otr.story_validator.announcer_news_coda`, and
`otr.story_validator.music_bookends`. The prose policy is deliberately
conservative and deterministic. After Unicode normalization and case folding,
the opening must literally contain the premise, setting, opening-scene time,
and every character name. The coda must literally contain the complete claim
of at least one receipt-named fact cited by that line. A fuzzy or
model-assisted policy requires a new validator version; it is never a silent
implementation change.

The news validator is constructed with caller-supplied captured-packet bytes
keyed by their declared SHA-256. It hashes the exact raw bytes, parses the
strict `otr.captured_source_packet.v1` artifact, and requires its complete
source/fact projection to equal the accepted story projection. It performs no
network lookup. The historical recovery control and challenger calibrate the
positive and negative semantics; neither is itself promoted into v1.

## Referential integrity

The v1 graph fails closed unless:

- every ID is nonempty and unique in its table;
- every fact source reference resolves;
- every scene owns its declared shots;
- every shot owns its declared beats;
- every beat owns its declared lines;
- line scene/shot/beat joins agree;
- every line's `char_id`, `speaker`, and `speaker_role` agree with cast;
- every line fact reference resolves;
- every sequence item points to the correct line/cue table;
- every line and cue appears exactly once in sequence;
- line/cue table order matches its sequence projection, and scene/shot/beat
  child order matches the corresponding table order;
- no scene, shot, beat, line, cue, fact, source, or cast row is orphaned.

Array order is meaningful and sealed. Reordering accepted story rows is a
story change, not a harmless cleanup.

## Story seal

Story v1 canonicalization is deliberately small:

- UTF-8 output;
- every string must already be NFC;
- no floating-point values in the story plane;
- object keys sorted;
- compact separators;
- NaN and Infinity forbidden;
- strict models reject unknown properties.

The canonicalization ID is `otr.canonical-json.v1`. Structural parsing is not
acceptance: the seal builder first revalidates a fresh serialization and runs
every receipt through a caller-owned trusted verifier registry. Unknown or
failed verifier identities fail closed. The production-independent semantic
registry lives in `src/upstream_story_lab/ledger_verifiers.py`; low-level trust
plumbing tests may still inject explicitly synthetic verifiers, while the
normative v1 fixture is admitted only through the code-owned registry.

The complete accepted `story_ledger` is hashed with SHA-256 into
`story_seal.story_sha256`. The whole seal receipt, including its one-time UTC
`sealed_at`, is immutable during production extension. Changing the algorithm
is a schema migration, never a silent implementation detail.

## The production plane (normative target; executable schema pending)

`production_state` is not a second story. It is an append-only execution
journal whose phase artifacts reference immutable story IDs.

The versioned registry includes:

- workspace identity and rename/rebase;
- cast routing;
- voice render;
- music render;
- positioned speech timeline;
- audio enhancement;
- master audio;
- procedural base video (workspace rename requests still route through the
  workspace-identity owner);
- visual plan;
- image render;
- video render;
- silent composite;
- scene-aware scopes;
- post-upscale/procgen blend;
- captions;
- credits;
- publication;
- terminal audit.

Each phase has one declared owner. Attempts are append-only and bind the story
digest plus dependency receipts. An accepted attempt must reference a succeeded
attempt. Required phases cannot silently skip. Artifact references to lines,
cues, beats, shots, or cast must resolve into the sealed story.

Media stages may add timings, hashes, cache keys, paths, model/engine receipts,
and measured duration. They may not alter story text, speaker ownership, facts,
graph topology, or program order.

## Final seal

The final seal occurs only after:

- every required run-plan phase has an accepted successful attempt;
- final audio/video/OBS artifacts exist and have byte identities;
- terminal audit is recorded.

It binds the story digest, production-state digest, episode/run identities, and
seal time. Afterward both planes are immutable. A later rerender is a new
`run_id`; a later story edit is a new story edition. Operational annotations
after the final seal are sidecar records referencing its digest, not edits to
the sealed ledger.

## What is deliberately not a story acceptance rule

The Bible does not accept or reject a story based on:

- word count;
- measured minutes;
- scene, movement, beat, or turn count beyond graph integrity;
- model/provider choice;
- number of authoring passes;
- prompt wording;
- subjective style or quality scores.

The visible length input remains exactly:

```text
ultra_short
medium
long
extra_long
```

Each source bank will later map that label to a versioned generation process.
Words and downstream duration are receipts, not acceptance authority. That
length experiment begins only after the Ledger Bible boundary is stable.

## Current l4 compatibility warning

Production OTR schema `l4-2026-08-07` is not this contract:

- it mixes authored and production fields in one mutable dictionary;
- `cleanup_locked` has no enforcing reader;
- Phase 10 does not seal the whole authored graph;
- CastLock can alter line routing after Phase 10;
- EpisodeAssembler can add/reorder line rows;
- SciFi `fact_ids` can disappear before durable storage;
- wire, disk, manifest, and filesystem representations diverge;
- save paths disagree about unknown schema-version handling.

There is no automatic `l4 -> v1` migration. Existing ledgers remain historical
evidence unless a named migration can account for every missing semantic field.
New Story Lab output will need an explicit production adapter that preserves
the story bytes/digest and writes all media truth into `production_state`.

The July `science_news` control is intentionally historical evidence rather
than a normative v1 object. For example, its cast row identifies ANNOUNCER as
`c01` while its spoken rows use `char_id="announcer"`. A migration must resolve
that identity explicitly; the fixture is never silently admitted because its
prose happens to demonstrate the desired bookends. Reusing an ID literal in
different typed tables (for example legacy `line_id="b001"` and
`beat_id="b001"`) is not itself a v1 collision: uniqueness is per table and
references carry their kind.

## Executable evidence

- Current consumer characterization:
  `contracts/ledger_consumer_matrix_l4.json`
- Target machine contract: `contracts/ledger_bible_v1.json`
- Strict models, graph validator, canonicalization and story guard:
  `src/upstream_story_lab/ledger_contract.py`
- Five trusted semantic validators and immutable registry:
  `src/upstream_story_lab/ledger_verifiers.py`
- Complete normative envelope and external captured packet:
  `fixtures/story_recovery/v1/`
- Rejected mutation corpus with one replayed case per machine invariant:
  `fixtures/story_recovery/v1/rejected_mutations_v1.json`
- Contract tests: `tests/test_ledger_bible_contract.py`
- Semantic and mutation-corpus tests:
  `tests/test_ledger_semantic_verifiers.py` and
  `tests/test_ledger_mutation_corpus.py`
- Live good/bad evidence projections: `fixtures/story_recovery/`
- Independent audit and reviewer reconciliation:
  `docs/2026-08-13-story-recovery/`

That directory preserves the raw Antigravity and Sonnet reports separately
from the grounded Codex audit and synthesis. Raw reviewer confidence is not a
contract authority.

The production workflow remains unchanged. A later transplant must add its
adapter, production receipt schemas, save guards, workflow wiring, and final
seal in small tested chunks; then recreate the seven-leg render runner so no
post-change proof uses stale code.
