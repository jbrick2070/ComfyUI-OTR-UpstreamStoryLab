VERDICT: yes-with-fixes. The vision is coherent and well-grounded against the real production code, but several structural gaps and one contradiction need closing before build.

---

MUST-FIX BEFORE BUILD

1. [Section 5] NEWS_SEED_KEYS claim lists 7 keys but production code shows the dict also carries no `body_chars` as an int in the docstring at `_otr_legacy_to_stage1_adapter.py:73` -- verify: does the ACTUAL news_seed dict emitted by the live NewsFetcher always include `body_chars` as an int, or is it sometimes absent? The compat mirror pins this shape; if the real emitter ever omits `body_chars`, the drift-proof test will false-positive on every run. The fix: the pinned shape must document which keys are required vs optional, or the drift-proof test must allow subset matching for optional keys.

2. [Section 4] The seam list claims `casting_brief_seam` is a prompt seam site ("source/casting brief text path; craft stays shared"), but the production `news_interpreter.py` (`build_news_briefs`) generates `casting_brief` as an LLM-authored field stamped on NewsBriefs -- it is not a prompt template site the way `outline_system` or `pitch_room_system` are. Conflating a generated brief field with a parameterizable prompt seam will confuse the pack author about what they can override. Fix: either split the seam list into "prompt template seams" vs "generated content fields" or remove `casting_brief_seam` from the seam vocabulary and document that casting briefs flow through the interpreter, not through pack overrides.

3. [Section 7, C5] The transplant_work chunk says `_otr_source_interpreter.py` is a "facade; science delegates to news_interpreter unchanged," but the plan never specifies what the facade's PUBLIC INTERFACE is. The production `news_interpreter.py` exposes `build_news_briefs(technical_fn, ...)` with 12+ kwargs. The facade needs a contract: does it re-export `build_news_briefs` verbatim, wrap it with bank-specific defaults, or define a new protocol? Without this, two implementors will build incompatible facades. Fix: declare the facade's call signature in the plan -- at minimum `interpret(source_packet, generate_fn, bank_spec) -> StoryInputPacket` or equivalent.

4. [Section 7, C2] "12 story packs (recovered from git v1 and extended to seam-complete)" -- but the v1 lab was cleared in commit ccde304 ("clear lab, rebuild as transplant workspace"). The v1 snapshot is at git 41c6512. Verify: can the build session actually `git show 41c6512:...` to recover those packs? If the v1 tree did not contain 12 JSON pack files (it may have had Python-embedded content), the "recovered from git v1" claim is aspirational, not factual. Fix: either confirm the exact git paths of the 12 packs in the v1 tree, or state that packs will be AUTHORED fresh from the seam list and the v1 Python prose.

5. [Section 1 + Section 7] The architecture diagram shows `production adapter (tomorrow's transplant chunk)` as a separate phase, but Section 7 C5 puts `transplant_work/` patch specs and new production-ready modules in TONIGHT's build scope. This is a scope/phasing contradiction: is the transplant coded tonight or tomorrow? Fix: either move C5 explicitly to a "staged but not applied" non-goal (like the workflow JSON), or acknowledge that tonight's session writes production-shaped code that is tested in the lab but not deployed.

---

SHOULD-FIX

1. [Section 5] The compat mirror cites `production_mirror/nodes/_otr_story_brief_helpers.py` for the four tail constants. Confirmed correct against the real file (lines 229, 232, 243, 251). However, the plan names this grouping `SCI_FI_TAILS` -- but these constants are NOT sci-fi-specific. `STYLE_TAIL_DEFAULT` is "cinematic, 35mm film look..." which is genre-neutral. `ERA_TAIL_DEFAULT` is "timeless cinematic aesthetic." Naming them `SCI_FI_TAILS` will mislead implementors into thinking they only apply to the science bank. Fix: rename to `VISUAL_TAIL_CONSTANTS` or similar, and clarify that `sci_fi_radio` is one visual style policy that REPRODUCES these constants, not that the constants ARE sci-fi.

2. [Section 6] `motion_prompts` keyed by MOTION_ROLE_KEYS -- confirmed against `render_driver.py:546-561` (announcer, music_open, music_close, music_inter). The plan says "scene_broll/background_abstract/sfx are dead roles and must stay dead." Verify: grep the full render_driver.py for these strings to confirm they are truly absent. [ASSUMPTION] I could not read the full render_driver.py (41k tokens). If any of these dead roles are still referenced in fallback paths, the validator that rejects them will break production.

3. [Section 7b, item 4] "Cross-product invariant tests assert over ALL combos: resolution succeeds or raises a typed error." With 4 axes (banks x models x pipelines x styles), the cross-product can explode if fixture counts grow. With the stated "12 story packs, 5 visual styles" and even 3 banks x 3 pipelines, that is 12 x 5 x 3 x 3 = 540 combos. Each combo runs template formatting + validation. This is fine at this scale, but the plan should state the expected combo count and set a test-time budget (e.g., "must complete in <10s") so future fixture additions do not silently balloon CI time.

4. [Section 4] The seam `interpret` is described as "(source brain -> briefs; science keeps news_interpreter)" but Section 3 says bank bindings are `"interpreter": "fixture_media_archive"` style strings resolved through an allowlist. The `interpret` seam is a PROMPT seam (template text), while the interpreter binding is a PYTHON behavior binding. These are two different extension mechanisms for the same concept. The plan does not make clear which one a new bank author uses to customize interpretation. Fix: clarify that the `interpret` seam is the prompt template the interpreter uses internally, while the binding selects WHICH interpreter runs. Or collapse them into one mechanism.

5. [Section 7, C1] `contracts.py` lists `SourceMaterialPacket` and `PublicDomainSourceManifest` but the plan never describes what public-domain source material LOOKS like or how PD sources differ from news sources at the packet level. The manifest "safety (absolute/.. paths)" test in C3 implies PD sources reference local files. Fix: add a one-line description of the PD packet shape and how it differs from a news packet.

---

OPTIONAL / NICE-TO-HAVE

1. [Section 7b, item 3] Content hashes (pack_sha256 etc.) in provenance are good for reproducibility but the plan does not specify whether hashes are computed over raw file bytes or normalized JSON. If two sessions produce semantically identical JSON with different whitespace, the hashes diverge. Recommend: hash the canonical `json.dumps(sort_keys=True, separators=(',',':'))` output, and state this in the contract.

2. [Section 8] Gates reference `FABLE_FINAL_REVIEW_2026-07-02.md` but do not inline the gate list. A reader of this plan alone cannot verify gate coverage without opening a second document. Consider inlining the gate checklist or at minimum listing the gate count.

---

CUT THESE (scope / over-engineering)

1. [Section 7, C5] `transplant_work/` patch specs with "exact before/after hunks, file+line cited against production_mirror." Writing exact diff hunks against a moving production codebase tonight, when the transplant is explicitly deferred to tomorrow, is premature. The production code may receive hotfixes overnight that invalidate every line number. Cut the line-cited hunks; keep only the module-level change descriptions and the new standalone files. The hunks can be generated fresh at transplant time when the actual production HEAD is known.

2. [Section 7b, item 5] "Pipeline simulation with failure injection" + FakeLLM runner. This is a test infrastructure investment that is valuable but not required for the lab to be build-ready. The core contract ("no hidden fallback") is already covered by cross-product invariant tests (item 4) and registry fail-loud tests (C3). Cut or defer the FakeLLM runner to a follow-up; it can be added after the registry and contracts are stable. If kept, it risks becoming a maintenance drag if pipeline specs change shape.

3. [Section 7, C4] `scripts/validate_lab.py` CLI runner. The lab is a ComfyUI custom node. If the tests (C3) pass and the node (C4 `nodes.py`) loads, a separate CLI runner adds marginal value. Cut unless there is a specific non-ComfyUI validation workflow (e.g., CI without ComfyUI installed). If CI is the use case, say so.
