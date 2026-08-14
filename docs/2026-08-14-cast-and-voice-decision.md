# Cast identity and voice richness: what the Lab should own

Updated: 2026-08-14. Opus review of production's casting and voice stack,
against the Story Lab's sealed-story/production-state split.

## The question

Does the Story Lab offer voices as rich as production has today?

## The answer: that is two questions, with opposite answers

**Voice stock — the Lab should own none of it, and should not want to.**
Production's honest renderable stock is **42 distinct voices**: 10 bark presets
in `config/cast_pools.py`, 28 kokoro `.pt` files, and 4 clone `.wav` files that
actually exist on disk out of 41 referenced. The remaining 162 rows of
`config/voice_reference_bank.json` are cloud sentinels or missing refs carrying
`ref_sha256="pending"`.

That pool is a production asset with a disk dependency, an engine ladder, and a
staleness problem. Vendoring it would create a second copy the Lab cannot
verify and would put render truth on the story plane. The Lab owns zero voice
IDs. Production already agrees with this by its own behavior:
`cast_one_character` leaves `voice_preset` empty and the freeze gate annotates
that emptiness as "assigned by OTR_CastLock post-freeze".

**Cast identity — this is the real gap, and it is closable.**

The Lab seals `char_id`, `name`, `cast_role`, `character_description`. **Not
one of those four is read by any production voice picker.**
`python_assign_voice_preset` filters on gender first, and
`assign_voice_for_slot` scores gender at 100 of a 170 maximum with a
gender-only unconditional floor. A Lab-sealed cast with no gender therefore
forces every character onto the gender-agnostic fallback, or on the google_tts
lane into a hard `VoiceCastingError` with no fallback at all.

The Lab already has the answer and reads none of it: every vendored Folger
scene ships a provenance sidecar with a `characters` array carrying `gender`
and `gender_source`.

## Decision

The test applied: **a field is a story fact if the audience could contradict it
from the finished episode; it is render truth if only the renderer could.**
"Elizabeth is a woman" is contradicted the moment a bass voice reads her lines
in a script whose other characters call her "she". "Elizabeth is
`v2/en_speaker_7`" is contradicted by nobody.

### Seal (add to `CastMember`)

- `presented_gender`: `male | female | other | unspecified`, default
  `unspecified`. What the drama asserts, not what a larynx does. `unspecified`
  is a real answer, not a gap: a source that named someone and declined to
  gender them has told us something, and the compiler must be able to abstain
  rather than invent.
- `age_band`: `child | teen | adult | elder | unspecified`, default
  `unspecified`. Its own slice so it can be dropped without unwinding anything.

### Deliberately not sealed

- **voice_preset / voice_ref_id / engine_id** — routing, not identity.
- **timbre** — looks like identity, is not. Production assigns it by pure index
  rotation (`_TIMBRE_VOCAB[i % 6]`) with no reference to the character, and it
  is measurably broken in both directions: "bright" and "gravelly" match zero
  bark voices, "sharp" and "dry" match zero reference rows on every engine. A
  third of all slots get a word that constrains nothing. Sealing that would
  make an immutable object carry a known defect forever.
- **dramatic_role** — also `i % 4` rotation. The Lab already seals the real
  version: `StoryAct.speaking_char_ids` in first-speaking order plus per-beat
  line ownership, derived from actual dialogue rather than a slot index.
- **speech_signature** — no consumer in the sealed body.
- **cast_seed** — production needs it because CastLock replays an RNG walk. The
  Lab performs no RNG walk, so its routing can be a pure function of the sealed
  cast facts, the policy version, and the episode ID: strictly more
  reproducible, and immune to the recorded production failure where a missing
  seed folded to one constant and pinned 14 published episodes to the same
  announcer while every unit test stayed green.
- **gender_source** — provenance about a decision, not the decision. Belongs in
  the authoring journal and the routing receipt.

### Production plane

No new phases and no new receipt types: `production_contract.py` already
declares `("cast_routing", "cast_lock")` as phase 2 of 18 with a
`CastRoutingReceipt`.

## Migration cost, measured

Adding the two fields is a **sealed-schema change**: every cast row
serializes them, so every `body_sha256` and `story_sha256` moves. Measured on
2026-08-14: 128 of 404 tests fail on exactly one cause, `validation.body_sha256
does not bind the exact story body`. The work is mechanical but wide -
regenerate the normative envelope, the staged fixture, the per-bank act proofs,
and the generated contract artifacts, then update the hardcoded digests in the
contract tests.

It was reverted rather than half-landed, because an agent was concurrently
rewriting pack fixtures and a partially migrated seal would leave the repo in a
state no gate could describe honestly. It should be done as its own slice, with
nothing else in flight.

## What remains missing afterwards, stated plainly

The Lab will still own no voice pool, no engine profiles, and no bank digest.
It can prove a routing receipt resolves into the sealed cast and that no two
routes share a voice, but it cannot prove a voice ID exists or renders. That
residual is the plane split doing its job, not a defect.
