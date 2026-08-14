# Driver anchor review (Claude) - r3 wiring / integration

Grounded against the real files at `bbeeb55` before any fan-out. Every claim
below is labelled against what I actually read or ran.

## VERDICT

The wiring is sound and the seam migration is genuinely non-breaking, but the
adaptation lane has a structural hole: two of the four per-act jobs never see
the source they are adapting. Several bank-path gates are now stale rather than
wrong - they still pass, but they are guarding a vocabulary the executor no
longer reads.

## MUST-FIX

**M1. `act_spine` and `act_beats` are planned blind on adaptation lanes.**
CONFIRMED by reading `_job_context` in `authoring_executor.py`: the method
returns early for `act_spine`, and again for `act_beats`, before the branch
that calls `select_act_window` and attaches `source_block`. Only
`act_dialogue` and `act_cleanup` receive the source. This directly contradicts
the premise `build_act_windows` is built on - that act *i* of *n* grounds on
region *i* of *n* - because the acts are *planned* with no knowledge of the
author's text and only *written* against it. On a faithful-adaptation lane the
spine and beats are therefore invented, and the dialogue job is then asked to
carry source words into beats the source never suggested.

**M2. Nothing rejects a leaked speaker prefix in a spoken line.** CONFIRMED by
reading `spoken_text_policy.audit_spoken_text`: for `speaker_role == "announcer"`
the function `continue`s before the name analysis, and on the character lane
`_name_narration_pattern` only fires when a name is followed by an action or
attribution verb. `MACBETH So foul and fair a day I have not seen.` therefore
passes the sanitizer, the act gate, the cleanup gate and the seal. On
adaptation lanes the source block literally prints those prefixes above each
speech, so this is the most likely real-world leak. It is currently defended
only by a cleanup instruction, which is model-owned and unreliable on a 7B.
Known and disclosed in the input document, but it remains the top residual.

## SHOULD-FIX

**S1. `banks.json` `required_seams` guards a retired vocabulary.** CONFIRMED by
running the registry gate over all twelve packs: every pack reports
`missing_seams=0`, because each still carries the full retired `prompt_stages`
block alongside its new `job_prompts`. So the migration is non-breaking today -
but the gate now proves nothing about what the executor actually sends. A pack
could ship all nine retired seams, declare zero `job_prompts`, and pass every
gate while contributing no direction at all.

**S2. `profiles.py` hard-requires `prompt_stages.line_grounding`.** CONFIRMED:
eleven of twelve packs still carry it, and the twelfth
(`simple_4_prompt_experimental`) is exempt because its status is
`experimental`. So this does not block anything today. It will the moment a
pack drops its retired seams, which is the whole point of the migration.

**S3. No gate requires a runnable pack to declare all eight `job_prompts`.**
CONFIRMED by reading `StoryPack._stages_known_and_coda_valid`: unknown job
names and blank values are rejected, but an absent block is legal. All twelve
packs happen to declare all eight, so this is latent.

**S4. `coda_mode` diverges from what the coda validator enforces.** CONFIRMED:
every pack inherits its bank default - `real_news_report` for science news,
`archive_source_note` for media archive, `source_attribution` for public
domain - while `verify_announcer_news_coda` requires, on every lane, that the
coda literally contain the complete claim of a captured fact. The three modes
are therefore descriptive only. The newly installed pack prompts do all
instruct the model to carry the closing claim word for word, so the lanes work;
but nothing enforces that a future pack's coda prompt stays compatible with the
one rule the validator actually applies.

## UNVERIFIABLE / verify-at-build

**U1. Whether the exemption can be abused by quoting a stray fragment.** The
carriage test requires the *whole* row text to appear in the act window, so a
short quotation cannot excuse a long invented line. I read the code and believe
it holds, but I have not proven it adversarially against a hostile provider.
This is the single most valuable thing for a reviewer to attack.

**U2. Small-model behaviour.** Every prompt claim about 7B robustness is a
design judgement; nothing here has been run against an actual local model.

## Invariants a fix must not break

- Code may detect and explain; only a model pass may rewrite prose.
- No word-count authority, no content guardrails, no prompt tiering.
- The sealed ledger holds only announcer speech, character dialogue, music.
- A rejected job retries on its own job; a rejected cleanup restores the draft.
