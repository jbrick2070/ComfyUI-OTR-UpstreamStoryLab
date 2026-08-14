# Ledger Bible audit plan

Updated: 2026-08-13

## Audited boundary decision

The accepted story is the Bible for every downstream stage. Story generation
may revise drafts, but acceptance is one atomic story boundary. Production then
records measured media truth in a separate plane inside the same JSON envelope:

```text
mutable draft
  -> full structural + semantic validation
  -> canonical story serialization + SHA-256
  -> immutable story_ledger + story_seal
  -> phase-owned production_state receipts
  -> publish + audit
  -> final_seal over the completed envelope
```

No cleanup, TTS, music, image, video, caption, credit, assembler, or publisher
stage may change `story_ledger` after acceptance. Those stages may write only
their declared `production_state` phase receipt. A contract change requires a
new schema version and an explicit migration; it never edits an accepted story
in place. The Story Lab emits one envelope containing `story_ledger` plus
`story_seal`; `production_state` and `final_seal` are null at that boundary.

This is a correction to the initial whole-object-freeze hypothesis. Live OTR
cannot freeze its entire JSON at Phase 10 because it intentionally adds voice,
timing, image, video, path, publication, and audit truth afterward. Its current
`meta.cleanup_locked` stamp has no production reader and is not an immutability
guard. The target therefore separates authored truth from production truth
instead of calling the current mutable dict frozen.

## Why audit consumers first

A ledger schema invented only from writer output is incomplete. The actual
contract is the reconciled set of guarantees that real downstream consumers
depend on. The first recovery task is therefore to audit code, not redesign
prompts.

For every producer, mutator, and reader, record:

| Field | Meaning |
|---|---|
| component | Node/module/script name |
| file and function | Exact implementation seam |
| lifecycle phase | draft, pre-freeze, freeze, or post-freeze |
| operation | create, read, derive, mutate, serialize, or publish |
| JSON path(s) | Exact root/nested fields touched |
| requiredness | required, conditional, optional, or defaulted |
| type/shape | Actual expected type and constraints |
| order assumption | Sequence/first/last/adjacency behavior |
| identity assumption | IDs, foreign keys, cast/speaker/fact references |
| fallback behavior | Fail loud, skip, default, or silently derive |
| mutation | Exact before/after write, if any |
| evidence | File/line and executable test |

Static search is only discovery. Every claimed requirement must be confirmed at
the function that consumes it and, where practical, by an executable consumer
contract test.

## Canonical row surface to test

The first contract permits only these ordered sequence roles:

```text
music_open
announcer_open
character_dialogue
music_inter            # optional; only when requested by the story ledger
announcer_news_coda
music_close
```

Spoken rows are only announcer or character dialogue. `action`,
`stage_direction`, third-person narration, and delivery notes are forbidden in
the spoken surface. Story movement, intent, setting, continuity, and visual
ideas may exist as typed metadata, but no speech consumer may treat them as a
line to read aloud.

## Audit phases

### A. Inventory and classify

1. Find every ledger constructor and serializer.
2. Find every direct or indirect dict/list/object write.
3. Find every consumer entry point, including conditional engine routes.
4. Classify each touch as pre-freeze or post-freeze.
5. Find all schema/version checks, adapters, defaults, fallbacks, and legacy
   aliases.

Search by both symbols and field names. A consumer that treats the ledger as an
untyped dict may not import the ledger class at all.

### B. Reconcile the contract

For each JSON path:

1. identify its authoritative producer;
2. identify every reader and their strongest assumption;
3. resolve conflicting types/names/order expectations;
4. mark derived fields and prohibit consumers from treating them as authority;
5. remove dead fields only after proving no consumer reads them;
6. define referential-integrity and cardinality rules;
7. assign the field to one schema version.

Unknown, conflicting, or silently defaulted requirements remain visible audit
findings. They are not guessed into the Bible.

### C. Prove both seal boundaries

Use a canonical JSON digest of the complete `story_ledger` immediately after
acceptance. For every downstream consumer test:

1. load a fresh sealed story fixture;
2. record its canonical bytes and SHA-256;
3. invoke the consumer with media/model calls stubbed only at external
   boundaries;
4. assert the story bytes and digest are unchanged;
5. assert writes touch only the component's declared production phase;
6. fail with the exact unauthorized JSON path when a change occurs.

Also add mutation-negative tests: direct story assignment, list append, nested
dict write, and in-place normalization must be rejected after the story seal.
A shallow read-only wrapper is insufficient if nested containers remain
mutable. After publication and audit, compute the final seal and reject changes
to either plane.

### D. Publish one source of truth

The finished Ledger Bible artifact set is:

```text
contracts/ledger_bible_v1.json          machine lifecycle/invariants/ownership
contracts/ledger_consumer_matrix_l4.json current live-code characterization
src/upstream_story_lab/ledger_contract.py executable story model + seal
docs/LEDGER_BIBLE.md                    human contract and migration boundary
fixtures/story_recovery/*.json          hash-pinned production evidence
tests/test_ledger_bible_contract.py     graph/role/order/seal/parity rules
```

Later production-state receipt schemas and migration adapters must be generated
from the same machine source. The Markdown Bible is parity-checked against the
machine contract; it must not become a separately maintained description that
can drift.

## First no-GPU chunk

1. Complete the producer/mutator/consumer matrix from live OTR. **DONE.**
2. Reconcile the raw AGY report with an independent code audit. **DONE; AGY's
   strict-Phase-10 claim and three late-node write claims were corrected.**
3. Define the story/production split, canonical story seal, exact role axes,
   graph closure, and five outcome receipts. **DONE in the machine contract.**
4. Add pure CPU graph/seal/parity tests. **IN THIS CHUNK.**
5. Add production-state receipt schemas and one consumer adapter test at a
   time, beginning with CastLock, in the transplant chunk.
6. Add the final seal only after publication/audit write ordering is explicit.

No story prompt or length-tier implementation belongs in this first chunk.

## Exit criteria

- Every downstream consumer is present in the matrix with code evidence.
- Every required field has one authoritative producer and versioned type.
- Sequence roles and first/last constraints are executable.
- Source facts, cast/speaker IDs, line IDs, music IDs, and references are
  closed and validated.
- The story plane is deeply immutable, not merely top-level read-only.
- Every production consumer preserves the story digest and writes only its
  declared phase receipt.
- The completed envelope becomes fully immutable only at the final seal.
- The human Ledger Bible and machine schema cannot disagree unnoticed.
- The two recovery fixtures remain reproducible and hash-pinned.

Only after these gates should the lab choose a scalable chunk architecture or
ask an LLM to fill ledger drafts.
