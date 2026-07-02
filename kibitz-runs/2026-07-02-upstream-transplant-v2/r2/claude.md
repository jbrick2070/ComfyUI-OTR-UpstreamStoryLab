VERDICT: yes-with-fixes. Architecturally sound and grounded against real production code. Five interface gaps must be closed before an implementer can code to this spec without guessing.

---

MUST-FIX BEFORE BUILD

1. [Inherited locks] OutlineRequest.outline_system_prompt does not exist in production.
   The spec says "outline injection via OutlineRequest.outline_system_prompt with empty -> existing resolve_creative_system_prompt path" as a locked decision. But OutlineRequest (production_mirror/nodes/_otr_outline.py:277-352) has no such field. It exists only as a planned seam in production_mirror/docs/2026-07-01-source-bank-visual-style-code-ready/PHASE2_PROMPT_PY_UPDATE_MAP.md:67. The implementer needs to know this field must be ADDED to OutlineRequest at transplant, not that it already exists. Without that distinction, someone coding C5 will grep for it, find nothing, and stall.
   Fix: Change "inherited lock" language to "transplant addition" and cite the PHASE2 doc. Add the planned field signature (outline_system_prompt: str = "") to the C5 patch spec for _otr_outline.py explicitly.

2. [Inherited locks] Style-picker override kwargs do not exist in production.
   The spec locks "style-picker override kwargs (inventor_system_prompt, chooser_system_prompt, chooser_user_template; empty = science default)". The actual pick_style() signature (production_mirror/nodes/_otr_style_picker.py:783-812) has NO such kwargs. The system prompts are module-level constants (_INVENTOR_SYSTEM at :296, _CHOOSER_SYSTEM at :329) and _build_chooser_user_prompt (:393) is a private function, not an overridable parameter. The implementer must know the pick_style signature needs three new optional kwargs wired to override those constants/functions. The spec must declare the exact signature change or the C5 patch will be ambiguous.
   Fix: Add to the C5 patch spec: pick_style gains `inventor_system_prompt: str = ""`, `chooser_system_prompt: str = ""`, `chooser_user_template: str = ""` kwargs; empty = current hardcoded default; non-empty replaces the constant in the messages list.

3. [Seams / C1] interpret_source protocol references five undefined types.
   The protocol declares `SourceMaterialPacket`, `SourceBankSpec`, `LlmFns`, `StoryInputPacket`, `FetchRequest` but none exist anywhere in the codebase. The R1 architecture doc (section 7, C1) says contracts.py will define them, and names SourceMaterialPacket, StoryInputPacket, and SourceBankSpec - but LlmFns and FetchRequest are NOT listed in C1's contracts.py bullet. If the implementer builds contracts.py from the C1 list, the interpreter protocol will reference missing types.
   Fix: Add LlmFns and FetchRequest to the C1 contracts.py type list. At minimum: LlmFns = a protocol/TypedDict with creative_fn and technical_fn callables; FetchRequest = a frozen model with the bank id and any fetch parameters.

4. [Seams] Template variable allowlist is under-specified.
   The spec says "variable allowlist derived from the resolved profile model fields, never a hardcoded Python set." But neither the synthesized spec nor R1 architecture section 4 lists which profile fields become template variables. The R1 architecture (7b.1) says "string.Formatter-parses every template in every pack and fails loudly on an undeclared or misspelled variable at LOAD." But the set of DECLARED variables per seam is never enumerated. The implementer must either (a) infer the allowlist from StoryPromptProfile fields or (b) guess. Without an explicit mapping (seam -> allowed variables), template validation cannot be implemented deterministically.
   Fix: Add a table: seam name -> allowed variable names. Or: declare that the allowlist equals the union of all field names on the resolved StoryPromptProfile plus a small fixed set (e.g. scene_premise for line_grounding). Either way, make it concrete enough to code a validator.

5. [C2 / fixtures] v1 packs "ALREADY RECOVERED" are not in the repo.
   The spec says "12 packs ALREADY RECOVERED from git 41c6512 (extraction verified, 42 files)." No packs/ or fixtures/ directory exists in the current working tree. The git log shows 41c6512 as "v1 snapshot: standalone upstream story lab before clear" and the current HEAD (ccde304) is "clear lab, rebuild as transplant workspace." The recovered packs were in the v1 tree that was then cleared. The implementer must re-extract from git or the spec must include the recovery command.
   Fix: Add a prerequisite step: `git show 41c6512:fixtures/ > ...` or equivalent extraction, with the exact paths. Or commit the recovered fixtures before the C1-C4 build begins.

---

SHOULD-FIX

1. [Compatibility mirrors] close_brief vs news_close_brief naming ambiguity.
   "GENERATED CONTENT FIELDS" lists `close_brief` but the actual NewsBriefs field is `news_close_brief` (production_mirror/nodes/news_interpreter.py:167). These are semantically related but have different names. The interpreter must map news_close_brief -> close_brief on StoryInputPacket. This mapping is not stated. An implementer could name the StoryInputPacket field either way and break the seam reference chain.
   Fix: State the mapping explicitly: NewsBriefs.news_close_brief maps to StoryInputPacket.close_brief. Or use consistent names throughout.

2. [C5] compose_source_coda does not exist in production.
   The spec references "compose_source_coda returns LineResult" as an inherited lock. This function does not exist anywhere in production_mirror. It appears only in PHASE2_PROMPT_PY_UPDATE_MAP.md:628 as a planned facade. The implementer must know they are writing this from scratch in _otr_line_composer.py, not modifying an existing function. The return type LineResult is confirmed real (production_mirror/nodes/_otr_line_composer.py:937).
   Fix: Label compose_source_coda as "new facade to be added" rather than an inherited behavior.

3. [Fallback taxonomy] FALLBACK_INVENTORY table is referenced but never provided.
   The spec says "each site enters a FALLBACK_INVENTORY table in the plan with a per-lane decision and a test at transplant time." No such table exists in this document or in R1_ARCHITECTURE_AND_CODING_PLAN_V2.md. The three grandfathered sites are described (style-picker padding, title regen, announcer outro) but the per-lane decision (fail-loud for non-science) is prose, not a structured table a test can consume.
   Fix: Add the table. Three rows minimum: site (file:line), science_news behavior, non-science behavior, test assertion. This is what makes the "fail loud" policy testable.

4. [R1 architecture section 5 vs synthesized spec] SCI_FI_TAILS vs PRODUCTION_VISUAL_TAILS.
   R1_ARCHITECTURE_AND_CODING_PLAN_V2.md section 5 line 129 still says `SCI_FI_TAILS`. The synthesized spec renames it to `PRODUCTION_VISUAL_TAILS`. The implementer who reads both documents will see a contradiction. One name must win everywhere.
   Fix: Update R1_ARCHITECTURE section 5 to use PRODUCTION_VISUAL_TAILS, or add a note that the synthesized spec supersedes.

5. [C3] "~60 combos" test budget is vague.
   The spec says "valid pack pairs x styles, ~60 combos + one negative per axis, <10s budget." With 12 packs, 5 visual styles, and at least 2 pipelines, the naive cross-product is 120. If scoped to valid (bank, model) pairs only, the count depends on how many packs belong to each bank - information not in the spec. The implementer cannot verify "~60" without the fixture data.
   Fix: Either commit the fixture data first (MUST-FIX 5) so the count is derivable, or enumerate the valid (bank, model, pipeline) triples explicitly.

---

OPTIONAL / NICE-TO-HAVE

1. The fetcher protocol (fetch_source) is declared but explicitly scoped out for v1 (only science_news fetches at runtime). Consider omitting the FetchRequest type from C1 entirely and adding it when a second fetcher ships. Less dead code to maintain.

2. Provenance hashing (sha256 over canonical JSON) is well-defined, but the spec does not say when hashes are computed - at registry load time, at bridge emit time, or both. A one-line statement ("computed at bridge emit; cached at registry load") prevents a performance question later.

3. The PD manifest shape (source_text_ref + text_files/image_files + rights_status=public_domain) would benefit from three lines of example JSON so the implementer does not have to reverse-engineer the shape from prose.

---

CUT THESE (over-engineering)

1. [R1 architecture 7b.3] Provenance stamping with 8 separate hashes (pack_sha256, style_sha256, banks_sha256, pipelines_sha256, lab_state_digest, production_baseline, plus bank/model/pipeline/style ids). For a one-operator local pipeline with < 30 packs, the four id stamps (bank, model, pipeline, style) plus a single lab_state_digest are sufficient for reproducibility. The per-file sha256 hashes add complexity to every fixture edit without a real consumer. Safe to cut because: the exact JSON bytes are in git; git commit hash IS the provenance hash.
   If kept: at least defer per-file hashes to a follow-up. Ship with ids + lab_state_digest only.

2. [R1 architecture 7b.5] Pipeline simulation with failure injection (FakeLLM runner). The synthesized spec correctly narrows this to simple_4_prompt_experimental only. Confirm the R1 doc's broader "any declared pipeline" language is dead - legacy_many_pass is descriptive-only and must NOT get a FakeLLM runner (the writer owns that sequence). The broader language in 7b.5 could mislead.

3. [R1 architecture 7b.2] Auditable Resolution record ("requested ids, resolved ids, which defaults applied, source file of every decision"). For tonight's build this is a dataclass with six fields that no consumer reads until transplant. Consider shipping resolve() returning a flat tuple of resolved ids tonight, upgrading to the Resolution record when the bridge actually consumes it.
