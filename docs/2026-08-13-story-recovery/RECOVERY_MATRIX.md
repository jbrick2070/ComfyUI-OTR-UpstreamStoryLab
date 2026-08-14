# Recovery matrix — what is worth saving

Updated: 2026-08-13

The current Story Lab `main` (`7df7c80`) is the clean experiment workspace.
Its `production_mirror` is frozen at OTR `d48a9d76` and is a historical
reference only: most mirrored files have drifted or disappeared in live OTR.
`mirror_drift=none` means the mirror still matches its own July manifest, not
that it matches production today.

## Restore from the old `science_news` behavior

| Mechanism | Evidence seam | Decision |
|---|---|---|
| Physical announcer bookends | `production_mirror/nodes/_otr_outline.py` assembled the first and last announcer beats and validated two bookends | Restore the behavior as explicit typed row purposes, not as prompt advice |
| Place/time/who opening | `_otr_line_composer.SafeOpenBrief`, `compose_announcer_intro`, and its safe fallback | Restore and add a source-backed news-premise field; keep fictional outcome starved from the opener |
| Real-news coda | `compose_news_coda` authored a fictional-to-real bridge, then deterministically appended `news_close_brief` | Restore the source-grounded guarantee using typed fact IDs; do not let the model rewrite the factual payload |
| Pre-owned speaker rows | old ledger initialization stamped speaker/character identity before prose was authored | Restore this authority boundary in the compact score/writer design |
| Spoken correctness corpus | recover high-confidence helpers/tests from `314dd481^:nodes/_otr_line_hygiene.py` | Restore only narration, stage-business, and cross-speaker correctness classes; use authored repair then reject residual defects |

## Port from current OTR

| Mechanism | Current seam | Decision |
|---|---|---|
| Fail-loud bank/pack routing | `_otr_story_pack.py`, `_otr_story_routing.py`, story-pack registries | Port the typed ownership and refusal behavior; no cross-bank fallback |
| Typed source payload | `_otr_source_payload.py` | Port the exact fetch/interpreter contract and provenance |
| Evidence graph | `_otr_scifi_codex.py` P0 fact/entity/source-span types and validation | Port source facts and exact references |
| Compact typed compiler | P3/P5 draft types, graph compiler, bijection checks | Port the mechanical compiler; add typed bookend roles and speaker authority |
| Attempt/provenance receipts | `_otr_content_authorship.py`, call journal, resolved-model receipts | Port accepted-attempt-only receipts and hashes |
| Finite retries | structured-call/candidate ladder | Port bounded fresh attempts; no recursive repair |
| Decode liveness | commits `832eaf6b`, `9af0f7e2`, `b37e095b` and `_otr_decode_guard.py` | Port later as one dependency cluster, only when the lab has a real model adapter; preserve both `verbatim_cycle` and `open_string` |
| Media duration truth | audio samples/sample rate drive final duration; `_otr_word_delivery.py` is telemetry | Keep audio authoritative and words observational |

## Compare in the lab before deciding

| Question | Control | Challenger |
|---|---|---|
| Story shape | frozen legacy `science_news` fixture | compiled current `scifi_news` P3/P5 fixture |
| Writer topology | dedicated intro/body/coda paths | compact whole-script text pass |
| Chunk size | old per-line/many-pass behavior | current bounded whole-artifact drafts |
| Bank-specific length mapping | historical word-derived budget | new four-tier semantic plan |
| Spoken correction | historical narrow detectors plus too many later global gates | current very narrow explicit-markup check |

The goal is not to declare one whole architecture the winner. It is to measure
which authority boundaries survive small and long stories across media banks.

## Exclude

- The retired `legacy_many_pass` pipeline as a whole. It is descriptive-only in
  this lab and `run_pipeline()` correctly refuses to execute it.
- Subjective story-quality vetoes and deterministic Python-authored prose.
- Word-fit rerolls, word clamps, and target-word acceptance.
- Current speakerless P5 context.
- Current “announcer appears somewhere” topology.
- Any one-signal or token-ceiling substitute for the final liveness guard.
- The stale production workflow/bridge as shipping code.
- A prompt-only instruction to add an introduction or coda; topology must make
  those rows unavoidable.

## Unsafe shortcuts

- Reverting the July `science_news` retirement would revive incompatible
  routing, prompts, tests, and deleted behavior.
- Cherry-picking only `_otr_decode_guard.py` would stage dead code: the guard
  depends on real generation routes, failure classification, rerolls, and
  completion evidence.
- Adding only `speaker` prose to a prompt leaves no authoritative cast mapping.
- Expanding a text-field ceiling to make a long episode confuses liveness with
  length. Longer stories must add bounded semantic units.
- Treating the legacy control as proof of music topology would fabricate data;
  its ledger contains no structured music rows.

## Safe build order after this evidence chunk

1. Pure fixture adapters and semantic receipts.
2. Four-tier bank plan schema/resolver, without changing prompts.
3. Explicit music/announcer/body/coda topology and P5 speaker projection.
4. Narrow spoken correctness audit and one bounded authored repair.
5. Executable lab A/B adapters.
6. Integrate the complete liveness cluster into those real model call paths.
7. Start with `ultra_short`; calibrate upward only from measured audio/story
   receipts.
8. Transplant proven pieces into OTR in small independently green chunks.
