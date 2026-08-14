# Story Lab QA - a sequence of narrow agy passes

One broad pass already failed: agy explored 116 steps and timed out before
writing anything. So this is five SMALL passes, each scoped to a couple of
files. Run one, I fix what it finds, then run the next.

Every pass gets the same PREAMBLE, then one STEP block. Paste
`PREAMBLE + STEP n` as the prompt.

Run each from the repo:

```bash
cd C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab
```

---

## PREAMBLE (paste this above every step)

You are QA-ing the Story Lab at
C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab

WRITE YOUR FINDINGS FIRST, then verify in whatever budget is left. Read ONLY
the files this step names. Do not survey the repo - a previous pass died doing
that.

Give every finding a VERDICT, a file:line, and a concrete fix. Say plainly when
you could not verify something rather than guessing.

What the system is: one source packet becomes one sealed radio-drama ledger.
The only length control is a strict integer act_count 1..8. The schedule is
4*act_count+7 jobs. Acts are authored ONE AT A TIME:
story_seed -> story_arc -> per act (act_spine -> act_beats -> act_dialogue ->
act_cleanup) -> cast_sweep -> announcer_open -> announcer_news_coda ->
music_bookends -> final_admission.

Every sealed episode has the same shape on every bank:
music -> announcer opening -> character dialogue (optional music beats inside)
-> announcer coda stating the real source truthfully -> music.

The laws:
1. The sealed ledger holds ONLY announcer speech, character dialogue and music
   cues. Never a stage direction, action row, narration or delivery note.
2. Code may DETECT a defect and explain it; only a model pass may rewrite
   prose. `act_cleanup` is that pass.
3. No word-count authority anywhere - no target, budget, cap or gate.
4. No content guardrails anywhere. A source's own violence is carried as the
   author wrote it.
5. One prompt per job must serve a 7B local model and a frontier model alike.
   No tiering, no per-model variants, no conditional branches.
6. Runaway guards (decode-loop and repetition detection) are code-side and
   STAY. They are not length limits and must never appear as prompt rules.

Already known - do NOT report these:
- presented_gender/age_band are not yet sealed on CastMember (queued).
- A leaked speaker prefix ("MACBETH So foul and fair...") is rejected by no
  acceptance function; defended only by a cleanup instruction.
- The whole-line stage detector misses verbs outside its whitelist ("They
  weep."). Widening it is a policy-version decision.
- coda_mode values are descriptive; only the verbatim fact claim is enforced.
- The rendered prompt is barely test-covered.

---

## STEP 1 - the carriage exemption

Read ONLY `src/upstream_story_lab/spoken_text_policy.py` and
`src/upstream_story_lab/source_window.py`.

On adaptation lanes a spoken line is exempt from three heuristic findings
(third_person_stage_business, cross_speaker_attribution, quoted_novel_dialogue)
when its text is literally carried from that act's source window, compared
whitespace-flattened and case-folded. Production cues, delimited stage
directions, and a row that is entirely a stage action are NEVER exempt.

Attack it. Can a short carried fragment excuse a long invented line? Can text
carried from one act excuse a line in another? Is the flattening too
permissive? Can a crafted line defeat `_is_whole_line_stage_action`? Does
`LabSourceSpan.contains` differ from `LabSourceDocument.contains` in a way that
matters?

## STEP 2 - the cleanup pass

Read ONLY `_accept_dialogue` and `_accept_cleanup` in
`src/upstream_story_lab/authoring_executor.py`.

Cleanup may reword, convert or drop a row; it may not re-assign one. Can it
lose a beat's last spoken line, orphan an assigned fact, reassign a speaker or
beat, drop a music cue, or leave act state half-updated when rejected? Does
every rejection reach the model as feedback it can act on? Can a rejected
cleanup corrupt the act it was repairing?

## STEP 3 - prompts against enforced rules

Read ONLY the instruction tuples in `src/upstream_story_lab/story_authoring.py`
and the `job_prompts` blocks in `fixtures/story_packs/*/*.json`.

For each of the eight jobs, does the prompt promise anything the acceptance
code rejects, or omit anything it rejects on? Name the acceptance function for
each finding. A mismatch here burns retries or loses a whole run after every
act has been paid for.

## STEP 4 - do the banks actually differ

Read ONLY `fixtures/banks.json` and the `job_prompts` blocks across
`fixtures/story_packs/*/*.json`.

Do the lanes have genuinely different creative voices, or have they collapsed
into one voice with different nouns? Does any bank's direction contradict
another bank's `forbidden_leakage_terms`? Does any prompt smuggle in a length
rule or a content guardrail? Is any prompt tiered or conditional?

## STEP 5 - the sealed contract

Read ONLY `src/upstream_story_lab/ledger_contract.py` and
`src/upstream_story_lab/ledger_verifiers.py`.

Can a story be sealed that violates the program shape - a missing bookend, a
music cue outside the character body, a coda that is not the last spoken row,
an orphaned fact, a cast row that owns no dialogue? Can a receipt be trusted
without its verifier actually running? Is the v4 adaptation verifier reachable
without the source bodies it needs?
