# Adaptation admission: measured conflict and the v2 spoken-text decision

Updated: 2026-08-14. Evidence-first record for the fidelity transplant.

## What was measured

The 14 vendored Folger scenes now live at
`fixtures/source_banks/shakespeare/sources/`. Every speech in them was
extracted and run through the Story Lab's live admission policy
(`otr.spoken-text-only.v1`, `src/upstream_story_lab/spoken_text_policy.py`).

| Corpus | Speeches | Policy findings | Rate |
|---|---|---|---|
| Raw Folger text, inline `[directions]` intact | 944 | 186 | 19.7% |
| Same text, inline `[directions]` removed | 944 | 9 | 1.0% |

The 154-finding gap is `delimited_stage_direction` firing on Folger's own
inline `[Aside.]` and `[to ORLANDO]` markers. That is **correct behavior**: a
bracketed direction is not spoken, and it must never reach TTS. It tells us
about source *preprocessing*, not about the policy.

The residual 9 are the real signal. Eight are genuine spoken Shakespeare that
the policy rejects; one is an artifact of the extraction probe. Examples,
verbatim from the source:

- `Sir, there she stands.` — Lear, speaking aloud about someone present.
- `The jewels of our father, with washed eyes Cordelia leaves you.` —
  Cordelia, speaking aloud of herself in the third person.
- `They stand at the door, master. Bid them welcome hither.`
- `Bless thee, Bottom, bless thee! Thou art translated!`

Separately, the decode-runaway guard added earlier today produced **zero**
false positives across all 944 speeches. Shakespeare's deliberate repetition
(`I'll do, I'll do, and I'll do`, `munched and munched and munched`) passes,
because the consecutive-repeat threshold scales with phrase length. That guard
needs no change.

## The conflict, stated exactly

The same detector code fires on faithful classical text and on the defect the
policy exists to stop:

| Line | Verdict |
|---|---|
| `Sir, there she stands.` (faithful Lear) | rejected `third_person_stage_business` |
| `Ada turns to Leo, her voice tightening...` (the August challenger defect) | rejected `third_person_stage_business` |

No lexical rule separates them, because lexically they are the same shape. This
is the same class of failure production recorded when its safety gate
discouraged `Is this a dagger which I see before me` while adapting Macbeth —
a shape heuristic destroying fidelity.

Weakening or deleting the heuristic is not acceptable: it is the only thing
standing between the ledger and the exact novel-prose narration that produced
"The Light of Possibility".

## Decision — `otr.spoken-text-only.v2`, source-carried exemption

The heuristic's premise is *"a model invented narrative prose instead of
writing dialogue."* When the words provably come from the vendored source
text, that premise is false, and the heuristic no longer applies.

On adaptation lanes only, a spoken line is exempt from the three **heuristic**
detectors — `third_person_stage_business`, `cross_speaker_attribution`,
`quoted_novel_dialogue` — when its text is provably carried from the act's
frozen source window. The check is deterministic: normalized comparison of the
line text against the vendored source bytes, not a similarity score and not a
model judgment.

Two rules are absolute and never exempt, on any lane:

- `production_cue` (`SFX:`, `MUSIC:`, `ACTION:`) — never spoken;
- `delimited_stage_direction` (`[Aside.]`, `{...}`, `*...*`) — never spoken,
  even when the source itself prints it. Folger's inline directions must be
  stripped by the compiler before a line is proposed, never carried.

This is a new validator version, exactly as the Bible requires: *"A fuzzy or
model-assisted policy requires a new validator version; it is never a silent
implementation change."* Concretely:

- `spoken_text_policy` gains v2 with an explicit optional carried-source
  argument; v1 behavior is unchanged when no source is supplied.
- `otr.story_validator.ledger_integrity` goes to validator version `4`.
- The exemption must be *evidenced*, not asserted: an admitted adaptation line
  carries the source digest and offset span it was carried from, so a later
  reader can re-verify the claim against the vendored bytes.
- Non-adaptation lanes (`science_news`, `media_archive` original drama) are
  unaffected and keep full heuristic strictness.

## What this does not change

- The spoken-only law itself. No action rows, stage directions, narration, or
  delivery notes are ever sealed or sent to TTS.
- Admission never rewrites accepted prose; a rejected act returns to its
  dialogue job.
- No word-count authority of any kind is introduced.
- No content filtering of any kind is introduced. The source's own violence is
  carried as the author staged it.
