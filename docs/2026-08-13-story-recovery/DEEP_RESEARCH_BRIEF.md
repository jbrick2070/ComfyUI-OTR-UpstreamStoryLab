# Deep-research brief — scalable component structure for chunked stories

Updated: 2026-08-13

This is a paste-ready brief for ChatGPT Deep Research, Gemini Deep Research,
or another research system with web access. It asks research to challenge the
lab architecture; it does not delegate the five locked product outcomes.

## Research task

Research and recommend a model-agnostic component architecture for generating
variable-length, source-grounded radio-drama **ledgers** in bounded chunks.
Ground the recommendation in primary academic/technical sources on
hierarchical narrative planning, long-form generation, discourse coherence,
state tracking, constrained structured generation, and evaluation. Prefer
peer-reviewed papers and original project/paper pages; clearly label
inferences that combine multiple sources.

The system must work across changing local and hosted LLMs. It must not depend
on one model understanding labels such as “medium story,” and it must scale by
adding bounded semantic units rather than by asking for more words or allowing
one response/string to grow without bound.

## Fixed product constraints

The Story Lab emits exactly one validated ledger JSON. It does not synthesize
speech or render/publish media.

Every acceptable news-story ledger must prove:

1. ledger schema/graph/cast/speaker/fact/music integrity;
2. captured source/news provenance and usable factual claims;
3. first spoken row is an announcer introduction of story, setting, and
   characters;
4. last spoken row is an announcer summary of the real news grounded in the
   captured facts;
5. opening music is first and closing music is last.

The only visible length control is:

```text
episode_length_tier = ultra_short | medium | long | extra_long
```

Words and eventual audio duration are telemetry, not acceptance gates. The
four tier-to-structure mappings are deliberately unknown and may differ by
media bank.

## Working hypothesis to challenge

Do not accept this hierarchy merely because it is supplied. Compare it with
credible alternatives and identify where terms collapse or need separation:

```text
episode
  fixed opening music
  announcer introduction
  body
    movement / sequence
      scene
        beat
          speaker-owned turn
            spoken line(s)
  announcer factual news coda
  fixed closing music
```

The tentative scaling unit is a **movement**: a bounded story component with a
declared entry state, dramatic job, evidence/character obligations, and exit
state. A generation call receives only a bounded movement or movement slice,
the immutable source/cast/topology authority, and a compact prior-state
summary. It may fill assigned spoken rows but cannot add/drop/reorder rows or
change speaker/fact ownership.

## Questions the research must answer

1. What hierarchy is best supported by the literature for coherent scalable
   story generation: acts, sequences/movements, scenes, beats, turns, events,
   goals, or another representation?
2. Which unit should `episode_length_tier` scale, and which structures should
   remain fixed overhead?
3. Should the complete topology be planned once, planned recursively, or
   expanded one movement at a time? Compare coherence, adaptability, error
   recovery, and context cost.
4. What immutable state and mutable state should cross a chunk boundary?
   Address source facts, cast, character goals/knowledge, unresolved causal
   threads, setting/time, promises/payoffs, prior utterances, and style.
5. How can the compiler prevent a later chunk from contradicting or silently
   rewriting earlier accepted ledger rows?
6. How should news-derived fiction keep factual evidence distinct from
   fictional invention, especially in the terminal announcer coda?
7. How should public-domain prose, plays, original fiction, news, and media
   archives map the same four tiers without pretending their semantic units
   are identical?
8. Which automatic checks measure structural coherence and source fidelity
   without becoming subjective prose-quality vetoes?
9. Which failures require local row repair, movement regeneration, topology
   replanning, or complete candidate retirement?
10. How should experiments compare different LLMs and future versions without
    making one model's behavior part of the contract?

## Required output

Return:

1. a concise evidence synthesis with direct links and citations to primary
   sources;
2. a terminology table mapping the sources' units to this project;
3. two or three genuinely different candidate component architectures;
4. a comparison table covering coherence, scalability, boundedness,
   inspectability, source grounding, model dependence, and implementation
   complexity;
5. one recommended smallest viable architecture and why;
6. a typed pseudo-schema for the episode plan, movement/chunk contract,
   carried story state, and final ledger receipt;
7. a bank-by-bank account of what a scalable unit means;
8. an experiment matrix starting at `ultra_short` and testing at least three
   materially different LLMs before extrapolating upward;
9. falsification criteria: observations that would disprove the recommended
   hierarchy or tier mapping;
10. unresolved questions that genuinely require operator judgment.

## Evidence and reasoning rules

- Search current literature as well as foundational work.
- Prefer primary papers/project documentation over summaries and blogs.
- Do not cite a source for a stronger claim than it actually makes.
- Separate reported evidence, project-specific inference, and recommendation.
- Do not assume word count is a semantic length control.
- Do not propose unbounded whole-story generation as the baseline.
- Do not make a prompt responsible for ledger integrity or fixed bookends.
- Do not prescribe one universal scene/beat count across media banks without
  empirical justification.
- Treat LLM and provider behavior as unstable experimental variables.

## Local evidence available to the researcher

- `fixtures/story_recovery/science_news_good_20260716.json`: clean legacy
  control with source-consistent announcer opening/closing.
- `fixtures/story_recovery/scifi_news_bad_20260813.json`: current compiled
  challenger with render success but lost bookends, narration, and speaker
  ownership.
- `fixtures/story_recovery/ledger_requirements_v1.json`: machine-readable hard
  requirements and four-tier enum.
- `docs/2026-08-13-story-recovery/PROBLEM_STATEMENT.md`: grounded regression
  statement.
- `docs/2026-08-13-story-recovery/RECOVERY_MATRIX.md`: mechanisms available to
  restore or port.
- `docs/2026-08-13-story-recovery/LENGTH_TIER_EXPERIMENT.md`: current process
  hypothesis and experiment boundaries.

The researcher should recommend a ledger architecture, not production OTR
wiring and not a video/render architecture.
