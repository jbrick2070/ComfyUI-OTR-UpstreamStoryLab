# Kickoff prompt for the next window

Paste everything below the line.

---

Work in `C:\Users\jeffr\Documents\ComfyUI\custom_nodes\ComfyUI-OTR-UpstreamStoryLab`
(main @ ca4c6df, 450 tests green). Read `docs/GO_FORWARD_PLAN.md` first — it
opens with a HANDOFF section. Do not touch production OTR.

The goal this session is to get a REAL story written and judged, methodically.
Everything so far was written by a scripted stand-in that cycles eight fixed
lines, so the ledger machinery is proven and the writing is not.

Do it in this order, and stop at each checkpoint to show me the result:

**1. Slice 1 of `docs/2026-08-14-prod-to-lab-transplant-plan.md` — the close.**
Prompt-only, all six live packs, zero code risk. Fold production's coda
contract into `job_prompts.announcer_news_coda`: the one-line spoken shape, the
enumerated stock-opener ban, a worked tale-to-clause example in each lane's own
vocabulary, "reference the tale by its subject or setting, not how it ended",
and the concrete-final-image menu including "a changed silence". Scope
production's "state no fact, date or outcome" to the BRIDGE only — the lab
requires the closing claim verbatim, so unscoped it contradicts itself.

**2. Slice 2 — give the announcer surfaces their context.** Small executor
change in `_job_context`: the coda job currently receives the arc, cast and
closing fact but nothing about how the story ended, so the host writes an
epilogue for a story it has not seen. Add the final act's exit state, the final
spoken line, and the accepted opening. Then add the clauses that depend on
them: lightly echo the opening's tone, agree with the produced ending, no
hedging. Regenerate the sealed proofs — never hand-edit a digest.

**CHECKPOINT: run the gates and show me a story.**
`python -m pytest -q && python scripts/validate_lab.py && python scripts/generate_bank_act_proofs.py --check`
then `python scripts/read_story.py fixtures/story_recovery/v2/bank_act_proofs/shakespeare_three_act.json --plan`

**3. Run a real story.** ComfyUI hosts the model; the seam exists.
`GenerateFnProvider` in `src/upstream_story_lab/generate_fn_provider.py` adapts
production's `generate_fn(messages, *, temperature, max_new_tokens, stop)` so
the lab loads no second model. Wire it to whatever model the workflow has, run
`scifi_news` at `--acts 1` first (cheapest smoke), then 3 acts. Save the
transcript.

**CHECKPOINT: read it aloud to me.** `python scripts/read_story.py <ledger>
--plan --facts`. Tell me honestly whether it is any good, where it sags, and
which job's prompt caused each weakness. Do not tell me the tests pass and call
that success — the tests never judged the writing.

**4. Iterate methodically.** One prompt change at a time, re-run, re-read,
compare. Keep a short log of what changed and what it did to the story.

Standing rules — these were learned the hard way, do not relearn them:

- The sealed ledger holds only announcer speech, character dialogue and music
  cues. Never a stage direction, action row, narration or delivery note. Every
  line becomes TTS audio.
- Before the seal a draft may be rewritten freely; after it, nothing. The
  rewriting is done by MODEL passes, never by code — `act_cleanup` is that
  pass. Code detects and explains; it never edits prose. No Python shims.
- No word-count authority anywhere: no target, budget, cap or gate.
- No content guardrails anywhere. A source's own violence is carried as the
  author wrote it.
- One prompt for every model tier, small local through frontier. No tiering,
  no per-model variants, no conditional branches.
- Runaway guards (decode-loop, repetition) are code-side and stay. They are not
  length limits and never appear as prompt rules.
- No bare `assert` in shipped code — `python -O` strips it.
- Seven banks, one pack each, all peers. Licence and non-commercial notices
  ride the credits roll, never the audio.
- Regenerate sealed fixtures with their generators; never hand-edit a digest.

Ask me before: retiring the legacy many-pass runner, sealing
`presented_gender` (a 128-test digest migration), or transplanting anything
into production OTR.
