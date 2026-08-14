# OTR Ledger Bible v2

Status: enshrined Story Lab constitution; not yet transplanted into production
OTR. The story plane, story seal, typed append-only production journal,
terminal final seal, and strict atomic persistence path are executable.

Machine authority:

- `contracts/ledger_bible_v2.json`
- `contracts/ledger_envelope_v2.schema.json`
- `contracts/ledger_field_laws_v2.json`
- `docs/LEDGER_FIELD_REFERENCE.md`
- `src/upstream_story_lab/ledger_contract.py`
- `contracts/ledger_consumer_matrix_l4.json` (current-production
  characterization, not the target schema)

This document explains those artifacts. Current parity tests cover the core
versions, roles, outcomes, evidence rules, and current-production corrections.
Generated full-schema/document parity is a required pre-transplant chunk.

## One file, two kinds of truth

An episode still has one ledger JSON. The file is an envelope with two planes:

```text
otr.ledger_envelope.v2
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
`final_seal=null`. The explicit `otr.story-lab.production-adapter` v1 can later
attach and append the strict typed production journal without changing the
canonical story, body, or StorySeal bytes. After the terminal final seal is
minted, no ordinary story or production mutation is legal.

This distinction matters because “the story is accepted” and “the episode has
finished rendering” occur at different times. Pretending the entire file is
immutable at story acceptance would make truthful audio, image, video, path,
and publication receipts impossible.

Version vocabulary is exact:

| Surface | Version |
|---|---|
| envelope | `otr.ledger_envelope.v2` |
| story plane | `otr.story_ledger.v2` |
| story seal | `otr.story_seal.v1` |
| captured source packet | `otr.captured_source_packet.v1` |
| production plane | `otr.production_state.v2` |
| final seal | `otr.final_seal.v1` |
| minimum outcomes | `otr.minimum_ship.v2` |
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

- context: episode title, story seed, setting, and strict integer `act_count`
  from 1 through 8;
- source packet: bank ID, captured-packet artifact digest, sources, facts, and
  evidence locators; the trusted news-capture validator verifies that external
  packet digest because it is not a recursive hash of the embedded projection;
- cast: immutable character IDs, exact names, role, and description;
- one story arc whose ordered act IDs exactly match `act_count`;
- one ordered act row per act, with planning-only spine, entry state, exit
  state, final speaking-character IDs, and ordered beat IDs;
- scenes and shots as a separate render axis, plus beats and spoken lines as a
  closed graph;
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
delivery-note rows. Story seed, arc summary, act spines/states, scene/shot
descriptions, and beat intent are planning metadata; they never pass to a
speech consumer as dialogue.

The centralized pre-seal compiler serves every source bank. It may drop
standalone forbidden draft rows and remove characters that own no accepted
dialogue. It never invents filler dialogue to justify a cast row. If narration
or stage business is embedded ambiguously inside a proposed speech row, the
compiler returns that act to its dialogue job. Trusted admission never mutates
the proposed `StoryBody`.

That shape rule is not enough by itself: the August 13 challenger put novel
prose such as `Ada turns to Leo` inside a nominal character line. Trusted
ledger-integrity admission therefore runs `otr.spoken-text-only.v1`. It rejects
production cues and delimited directions in every speech row, plus quoted novel
dialogue, third-person stage business, and cross-speaker attribution in a
character row. It never rewrites prose during admission; the draft returns to
the owning act-dialogue job.

## One centralized authoring compiler, many creative banks

Science news, media archive, public-domain story, and custom-source banks keep
authority over source selection, tone, story seeds, and bank-specific prompt
content. They all feed one compiler and one admission boundary:

```text
bank packet
  -> story seed
  -> X-act story arc
  -> for each act: spine -> beats -> dialogue
  -> cast sweep
  -> announcer opening
  -> announcer factual coda
  -> compiler music bookends
  -> trusted admission and story seal
```

`act_count=X` is a scheduler input, not a request hidden in prose. It creates
exactly X ordered act paths, where X is a strict integer from 1 through 8.
Each path has separate spine, beat-plan, and actual-dialogue jobs. A retry is
another attempt on the same job; it never creates another act. Open, coda,
music, cast sweep, and admission are outside the act loop.

The stable schedule contains `3 * act_count + 7` jobs. Of those,
`3 * act_count + 4` are base model jobs: 7 model jobs for one act through 28
for eight acts, before retries. This is a compute/cost receipt, not a story
length guarantee.

Every dialogue job repeats the same output law: fill the exact beat IDs with
actual words spoken aloud by the assigned character, and emit no narration,
stage business, delivery notes, or another character's words. The accepted act
row then records its spine and exact beat projection, and its
`speaking_char_ids` must match final dialogue in first-speaking order.

There is no global word-count knob or word-count acceptance gate. A dialogue
job may receive soft local guidance such as exchanges or approximate duration
when useful. A 3060, 5090, or cloud route may change model choice, batching,
latency, and retry cost; it never changes the ledger shape or the chosen act
count.

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
3. one or more `character_dialogue` rows for every accepted act;
4. zero or more `music_inter` cues, each explicitly requested by the script and
   located inside the character-story body;
5. exactly one `announcer_news_coda`, the last spoken row;
6. exactly one `music_close`, last.

No other sequence role is legal. The opening introduces the story,
place/time, and final speaking characters. The coda
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

The trusted v2 registry is code-owned and contains exactly five identities.
`otr.story_validator.ledger_integrity` is validator version `3`, covering the
v2 graph plus `otr.spoken-text-only.v1`.
`otr.story_validator.announcer_open` is version `2`: after Unicode
normalization and case folding, the opener must literally contain the story
title, setting, opening-scene time, and every final speaking character name.
It does not require the planning seed, spine, or beat intent to be copied into
spoken prose. `otr.story_validator.news_capture`,
`otr.story_validator.announcer_news_coda`, and
`otr.story_validator.music_bookends` remain version `1`. The coda must
literally contain the complete claim of at least one receipt-named fact cited
by that line. A fuzzy or
model-assisted policy requires a new validator version; it is never a silent
implementation change. Opening admission and spoken-only admission are
independent: a clean dialogue body cannot compensate for a missing introduction,
and a correct announcer opening cannot compensate for narrated character rows.

The news validator is constructed with caller-supplied captured-packet bytes
keyed by their declared SHA-256. It hashes the exact raw bytes, parses the
strict `otr.captured_source_packet.v1` artifact, and requires its complete
source/fact projection to equal the accepted story projection. It performs no
network lookup. The historical recovery control and challenger calibrate the
positive and negative semantics; neither is itself promoted into v2.

## Referential integrity

The v2 graph fails closed unless:

- every ID is nonempty and unique in its table;
- every fact source reference resolves;
- `act_count`, ordered story-arc IDs, and ordered act rows agree exactly;
- every act owns its exact ordered beat projection and final dialogue cast;
- compiler announcer beats remain outside the act partition;
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
- no act, scene, shot, beat, line, cue, fact, source, or cast row is orphaned;
- every retained character owns at least one accepted dialogue row.

Array order is meaningful and sealed. Reordering accepted story rows is a
story change, not a harmless cleanup.

## Story seal

Story v2 canonicalization is deliberately small:

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
normative v2 fixture is admitted only through the code-owned registry.

The complete accepted `story_ledger` is hashed with SHA-256 into
`story_seal.story_sha256`. The whole seal receipt, including its one-time UTC
`sealed_at`, is immutable during production extension. Changing the algorithm
is a schema migration, never a silent implementation detail.

## The production plane (typed append-only schema)

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
attempt. Required phases cannot silently skip. Typed story references cover
source packets, sources, facts, cast, acts, scenes, shots, beats, lines, cues,
and sequence rows; every reference must resolve into the sealed story.

Media stages may add timings, hashes, cache keys, paths, model/engine receipts,
and measured duration. They may not alter story text, speaker ownership, facts,
graph topology, or program order.

## Final seal

The final seal occurs only after:

- every required run-plan phase has an accepted successful attempt;
- final audio/video/OBS artifacts exist and have byte identities;
- terminal audit is recorded.

It binds the story digest, complete production-state digest, episode/run
identities, UTC seal time, and a non-recursive digest of the complete terminal
envelope. Its own `final_payload_sha256` field is the only field omitted from
that digest preimage. The active publication must precede a successful audit;
the audit binds the exact pre-audit production prefix and its acceptance is the
last journal event. Afterward both planes are immutable. A later rerender is a
new `run_id`; a later story edit is a new story edition. Operational
annotations after the final seal are sidecar records referencing its digest,
not edits to the sealed ledger.

## Adapter and durable JSON

The Story Lab includes one explicit adapter and one strict persistence path.
They accept only the exact current v2 envelope; v1 evidence and current-l4
objects are never repaired or promoted. Before production initialization, the
adapter freshly verifies all five story receipts. It then proves that canonical
`story_ledger` bytes, canonical `StoryBody` bytes, every StorySeal field, and
`story_sha256` remain exact.

Save and load use deterministic canonical UTF-8 JSON with an LF final newline
and no BOM. Duplicate keys, malformed UTF-8, CR line endings, unknown schemas,
non-finite numbers, stale story or production digests, and invalid final seals
fail closed. Save validates and roundtrips before touching the destination,
writes and verifies a same-directory temporary file, and only then atomically
replaces the target. A failed save preserves the prior target bytes.

## What is deliberately not a story acceptance rule

The Bible does not accept or reject a story based on:

- word count;
- measured minutes;
- scene, beat, line, exchange, or turn count beyond each act's nonempty graph;
- model/provider choice;
- prompt wording;
- subjective style or quality scores.

The visible length input is exactly one strict integer:

```text
act_count = 1..8
```

It determines how many act paths the centralized compiler schedules. It does
not prescribe words, minutes, beats per act, or exchanges. Words and downstream
duration are receipts, not acceptance authority.

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

There is no automatic `l4 -> v2` migration. Existing ledgers remain historical
evidence unless a named migration can account for every missing semantic field.
The proven Story Lab adapter preserves the story bytes/digest and writes all
later media truth into `production_state`. Production OTR does not call it yet;
that wiring remains the next explicit transplant rather than a silent l4
migration.

The July `science_news` control is intentionally historical evidence rather
than a normative v2 object. For example, its cast row identifies ANNOUNCER as
`c01` while its spoken rows use `char_id="announcer"`. A migration must resolve
that identity explicitly; the fixture is never silently admitted because its
prose happens to demonstrate the desired bookends. Reusing an ID literal in
different typed tables (for example legacy `line_id="b001"` and
`beat_id="b001"`) is not itself a v2 collision: uniqueness is per table and
references carry their kind.

## Executable evidence

- Current consumer characterization:
  `contracts/ledger_consumer_matrix_l4.json`
- Target machine contract: `contracts/ledger_bible_v2.json`
- Generated Draft 2020-12 envelope schema:
  `contracts/ledger_envelope_v2.schema.json`
- Generated lifecycle/default/owner/failure catalog for all 1,322 expanded
  field paths: `contracts/ledger_field_laws_v2.json`
- Human field reference rendered from the same catalog:
  `docs/LEDGER_FIELD_REFERENCE.md`
- Strict models, graph validator, canonicalization and story guard:
  `src/upstream_story_lab/ledger_contract.py`
- Five trusted semantic validators and immutable registry:
  `src/upstream_story_lab/ledger_verifiers.py`
- Centralized act scheduler, draft filter, and cast sweep:
  `src/upstream_story_lab/story_authoring.py`
- Provider-neutral staged authoring executor and prompt layer:
  `src/upstream_story_lab/authoring_executor.py`
- Deterministic scripted provider (fake model for tests/fixtures only):
  `src/upstream_story_lab/scripted_provider.py`
- Staged-executor proof fixture (three acts, sealed and reloadable):
  `fixtures/story_recovery/v2/staged_authoring_three_act.json` via
  `scripts/generate_staged_authoring_fixture.py`
- Strict production adapter and atomic save/load guard:
  `src/upstream_story_lab/ledger_io.py`
- Complete normative envelope and external captured packet:
  `fixtures/story_recovery/v2/`
- Rejected mutation corpus with one replayed case per machine invariant:
  `fixtures/story_recovery/v2/rejected_mutations_v2.json`
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

The production workflow remains unchanged. A later transplant must wire the
proven adapter, save guards, centralized source-bank routing, act scheduler,
spoken-only draft cleanup, and final seal into current OTR in small tested
chunks; then recreate the seven-leg render runner so no post-change proof uses
stale code.
