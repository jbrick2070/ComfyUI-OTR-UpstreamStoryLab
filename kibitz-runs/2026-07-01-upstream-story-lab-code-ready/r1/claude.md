VERDICT: yes-with-fixes. Science and media-archive lanes are code-ready. The public-domain lane has a two-layer schema gap and no validated spec-build path. Three claims in the brief contradict the actual code.

---

MUST-FIX BEFORE BUILD

1. [public_domain lane] Public-domain has no end-to-end spec path.
   Defect: preview.py:interpret_fixture_material() line 66 raises ValueError for
   source_bank_id="public_domain_story". _find_source_packet() in nodes.py:120 returns
   None for it. OTR_UpstreamStoryLabValidator.validate() never exercises the PD lane.
   There is no fixtures/source_packets/public_domain_*.json. The plan presents PD as
   a "separate source-folder lane" ready to receive ledger-filling prompt meat next.
   It cannot; the call chain from PD source to LedgerWritingSpec does not exist.
   Fix: either (a) add a fixtures/source_packets/ entry for PD with SourceMaterialPacket
   schema and add the interpret_fixture_material() branch for public_domain_story, or
   (b) explicitly mark the PD lane status="not_implemented" and have both the validator
   and the preview node hard-error when it is selected, instead of silently returning
   raw prompt stages. Do not proceed to "ledger-filling prompt meat for PD lane" until
   one of these is true.

2. [public_domain lane] public_domain_sources manifest schema is incompatible with
   SourceMaterialPacket.
   Defect: fixtures/public_domain_sources/book_chapter_sample/manifest.json has fields
   text_files, image_files, adaptation_mode, required_fidelity that do not exist in
   SourceMaterialPacket. SourceMaterialPacket uses extra="forbid" (contracts.py:13), so
   loading a PD manifest as a SourceMaterialPacket will raise a Pydantic ValidationError.
   No adapter between the two schemas exists anywhere in the codebase. validate_lab.py
   never tries to round-trip a PD manifest through SourceMaterialPacket, so the green
   validation run does not catch this.
   Fix: decide which schema is authoritative for PD source folders and add an explicit
   adapter or loader. Whichever format the pipeline consumes must be covered by a
   validation call in validate_lab.py before PD lane work begins.

3. [nodes.py:83-85] _visual_style_choices() has a hidden fallback that contradicts the
   no-hidden-fallback invariant.
   Defect: only one fixture file exists under fixtures/visual_styles/ (archival_documentary.json).
   The guard "if 'sci_fi_radio' not in styles: styles.append('sci_fi_radio')" silently
   injects the hardcoded string on every startup. The other three in-catalog styles
   (anime, cartoon, paper_origami from catalogs.py:345-366) are never surfaced in the
   dropdown at all. The brief states visual_style is "an equal partner" but the node
   exposes only 2 of 5 catalog styles, with one arriving via undocumented injection.
   Fix: resolve the gap between the in-code VISUAL_STYLES catalog and the fixture files.
   Either (a) add fixture JSON files for all five styles and drop the injection guard,
   or (b) load choices from the in-code catalog (get_visual_style_policy is already
   fail-closed) and remove the fixture-file-scan approach for style discovery. The
   current hybrid is ambiguous and violates the stated invariant.

---

SHOULD-FIX

4. [nodes.py:283-289 / simple_4_prompt_experimental] Experimental pipeline is
   structurally coupled to custom_source_bank, not a free pipeline dimension.
   The brief says "the experimental simple_4_prompt_experimental pipeline must stay
   visible" as if it is orthogonal to source bank selection. In practice the fixture
   key is ("custom_source_bank", "simple_4_prompt_experimental",
   "simple_4_prompt_experimental") (validate_lab.py:97). It cannot be selected for
   science_news, media_archive, or public_domain_story without adding new story pack
   fixtures. The plan does not name this constraint anywhere. If the intent is that
   any source bank can eventually run the 4-pass pipeline, the current architecture
   does not support it.
   Fix: document this as an explicit current constraint ("experimental pipeline is
   only available via custom_source_bank until per-lane packs are added"), or add
   a story pack fixture for at least one real lane to demonstrate the pipeline is
   truly portable.

5. [nodes.py:309-313] custom_source_bank preview path is not a loud failure.
   Defect: when source_bank_id is "custom_source_bank", the preview node skips
   get_story_model() and returns raw prompt stages from the fixture pack without
   checking whether a real custom schema, source packet, or story pack has been
   provided. The brief requires custom_source_bank to "fail loudly until a valid
   schema, source packet, and story pack exist." It does not. It silently succeeds
   by returning the experimental pack's prompt stages. There is no schema
   validation, no source packet check, no guard distinguishing the experimental
   fixture from a real user-provided custom bank.
   Fix: the custom_source_bank branch should either (a) check for a custom schema
   file and raise with a pointer to CUSTOM_SOURCE_BANK_GUIDE.md if none is found,
   or (b) be documented as "experimental fixture path only" with a visible note
   in the output that this is not a validated custom bank run.

6. [OTR_UpstreamStoryLabValidator.validate()] Validator does not exercise the
   public-domain lane at all.
   Defect: the validator (nodes.py:178-225) validates science and media-archive
   source packets and builds specs for both. It validates story packs only by key
   membership and leakage-term scan. No PD SourceMaterialPacket is instantiated,
   no PD spec is built, no PD prompt preview is generated or checked for forbidden
   terms. A green validator run does not mean the PD lane is working; it means the
   PD lane was not tested. The brief lists this node's output as evidence the lab
   is ready.
   Fix: after defect 1 is resolved, add PD fixture packet instantiation and a
   build_spec_from_material call (or a hard error if PD status is not_implemented)
   inside validate() so the validator's green output is a meaningful signal.

7. [nodes.py / visual style selection] No compatibility enforcement between visual
   style and source bank.
   Defect: the preview node accepts any (source_bank_id, visual_style_id) combination
   without checking for forbidden-term overlap. Selecting sci_fi_radio visual style
   with media_archive source bank would produce a LedgerWritingSpec with
   visual_policy.allow_radio_tails=True, while the archival_documentary style that
   the media-archive lane was designed for sets allow_radio_tails=False. The
   leakage check (nodes.py:195-199) only runs the archival_documentary+media_archive
   combination inside the validator, not at preview time for arbitrary user selections.
   Fix: at minimum, document which visual styles are compatible with which source banks
   in the fixture or catalog, and run a forbidden-term check in preview() when a
   non-default visual style is selected for a lane that has documented forbidden terms.

---

OPTIONAL / NICE-TO-HAVE

- The _story_pack_choice_map() key format "source_bank / story_model / pipeline"
  (nodes.py:59-61) uses a space-slash-space separator. All current ids use underscores,
  so no collision today. Worth noting for future custom bank ids that might contain
  spaces or slashes.

- IS_CHANGED in both nodes hashes all of fixtures/ + src/ + nodes.py. This is correct
  and conservative. It does mean every fixture edit (including adding new story packs
  for other lanes) will invalidate both nodes' cache simultaneously. Acceptable for a
  lab; note before scaling fixture count.

- StoryPromptProfile.style_picker_chooser_user_template (contracts.py:77) is empty
  string by default and is never populated for media_archive or public_domain_story
  profiles (catalogs.py:248-314). If any downstream prompt builder reads this field,
  it silently gets an empty string. Verify: confirm no production prompt module reads
  this field before transplant.

---

CUT THESE (scope / over-engineering)

1. [simple_4_prompt_experimental / fixture] The experimental 4-pass pack (fixtures/
   story_packs/experimental/simple_4_prompt_experimental.json) contains no actual
   prompt language beyond placeholders describing what each pass should do. Registering
   it in validate_lab.py:97 as a required key adds a test assertion that guarantees
   the presence of a mostly-empty fixture. The fixture is not load-bearing at this
   stage. Keeping it is harmless, but requiring it in the validator inflates the
   "story_packs=12" count with a non-functional entry that could mislead a reader
   about lab completeness. Safe to defer the experimental pack assertion to the round
   where the 4-pass pipeline is actually being implemented.

2. [PROMPT_SURGERY_CHECKLIST.md] The checklist documents future R3+ production-node
   edits (nodes/news_interpreter.py, nodes/_otr_outline.py, etc.) that are explicitly
   out of scope for this round. Listing it as a "file to inspect" in the brief adds
   review surface without adding signal about the current code-ready state. Safe to
   leave unreviewed until the transplant planning round.

---

[ASSUMPTION] The brief claims "Import smoke already run" and "Validation already run"
and shows clean output. This review treats those outputs as accurate. The green
validation is not a contradiction because validate_lab.py does not test the PD lane;
it is consistent with the defects found here.

[ASSUMPTION] The production OTR workflow (ComfyUI-OldTimeRadio/workflows/
otr_scifi_16gb_full.json) was not inspected for this round. Claims about the
"existing production ledger contract" and "meta.news.*" compatibility mirror shape
(preview.py:91-105) are taken from the code and not cross-checked against the
production workflow schema.

[ASSUMPTION] The claim that pydantic is available in the ComfyUI Python environment
is taken on faith from the validation run output. No requirements file or pyproject
is present in this repo to verify it. verify: confirm pydantic is listed in the
ComfyUI custom node dependency manifest or installed environment.
