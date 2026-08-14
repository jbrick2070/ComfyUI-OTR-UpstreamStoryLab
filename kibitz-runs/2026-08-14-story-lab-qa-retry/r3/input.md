# Story Lab QA - focused scope

Repo `ComfyUI-OTR-UpstreamStoryLab`, main, suite 409 passing. Implemented code.

WRITE YOUR REVIEW FILE FIRST from the four questions below, then verify what
you can in the time you have. Do not attempt a full repo survey; a previous
run spent its whole budget exploring and produced no review. Read at most the
four files named below.

## The laws

1. The sealed ledger holds only announcer speech, character dialogue, music
   cues. Never a stage direction, action row, narration, or delivery note.
2. Code may DETECT a defect and explain it; only a model pass may rewrite
   prose. Every act has an `act_cleanup` model job for that.
3. No word-count authority anywhere. No content guardrails anywhere - a
   source's own violence is carried as the author wrote it.
4. Prompts must work unchanged on a 7B local model and a frontier model. No
   tiering, no per-model variants.

## Four questions. Answer each with a VERDICT and evidence.

**Q1 - Can the source-carried exemption smuggle non-dialogue into a sealed
ledger?** Read `src/upstream_story_lab/spoken_text_policy.py`
(`audit_spoken_text`, `HEURISTIC_FINDING_CODES`, `never_exempt`) and
`src/upstream_story_lab/source_window.py` (`LabSourceSpan.contains`).
On adaptation lanes a line is exempt from three heuristic findings when its
text is literally carried from that act's window, compared whitespace-flattened
and case-folded. Production cues, delimited stage directions, and a row that is
entirely a stage action are never exempt. Attack it: can a short carried
fragment excuse a long invented line? Can carriage from the wrong region count?
Is the flattening too permissive?

**Q2 - Can `act_cleanup` corrupt an act and still be accepted?** Read
`_accept_cleanup` and `_accept_dialogue` in
`src/upstream_story_lab/authoring_executor.py`. Cleanup may reword, convert or
drop a row. Can it drop a beat's last spoken line, orphan an assigned fact,
lose a music cue, or leave act state half-updated when rejected?

**Q3 - Does any prompt contradict what the code enforces?** Read the job
instruction tuples in `src/upstream_story_lab/story_authoring.py` and the
`job_prompts` blocks in `fixtures/story_packs/*/*.json`. A prompt that promises
something acceptance rejects, or omits a rule acceptance enforces, burns
retries or loses a whole run.

**Q4 - Does anything break on a 7B local model?** Prompt length, ambiguity
about JSON output shape, or any instruction a small model would misapply.

## Do not report these - known and already decided

- `presented_gender`/`age_band` not yet sealed on CastMember (queued).
- A leaked speaker prefix (`MACBETH So foul and fair...`) is rejected by no
  acceptance function; defended only by a cleanup instruction.
- Shakespeare is not registered as a bank yet.
- The rendered prompt is barely test-covered.
