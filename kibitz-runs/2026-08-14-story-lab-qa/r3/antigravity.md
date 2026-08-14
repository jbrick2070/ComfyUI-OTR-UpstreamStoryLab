I will read the kibitz skill documentation to understand the review guidelines and rules.
I will read the document to review located at `C:/Users/jeffr/Documents/ComfyUI/custom_nodes/ComfyUI-OTR-UpstreamStoryLab/kibitz-runs/2026-08-14-story-lab-qa/r3/input.md`.
I will list the contents of the repository directory to understand the structure of the codebase.
I will list the contents of the `src/upstream_story_lab` directory to find the source code files mentioned in the prompt.
I will run the tests in the repository using `pytest` to see if there are any failures or check the current status of the implementation.
I will run the tests using `python -m pytest` to ensure the current directory is added to python's import path (`sys.path`).
I will list the running background tasks to see if the pytest execution has finished.
I will view the `src/upstream_story_lab/story_authoring.py` file to understand the schedule, job structures, and sanitization.
I will list the contents of the `fixtures` directory to see banks.json and any other metadata files.
I will view `fixtures/banks.json` to inspect the source-bank configurations and their required seams or flags.
I will search the codebase for references to `required_seams` to see how it is validated.
I will view `src/upstream_story_lab/registry.py` around line 169 to see the seam validation logic.
I will search `src/upstream_story_lab/contracts.py` for the definition of `StoryPack`.
I will view `src/upstream_story_lab/contracts.py` to inspect the structure of `StoryPack` and other related contract classes.
I will search for `AUTHORING_JOB_SEAMS` and `TEMPLATE_SEAMS` in the codebase.
I will view the beginning of `src/upstream_story_lab/contracts.py` to see the definitions of `TEMPLATE_SEAMS` and `AUTHORING_JOB_SEAMS`.
I will search for references to `job_prompts` in the python source files to understand how the executor reads them.
I will list the files in the `fixtures/story_packs` directory to inspect the actual pack JSON files.
I will list the files in `fixtures/story_packs/science_news`.
I will view `fixtures/story_packs/science_news/science_news_default.json` to see its schema and prompt definitions.
I will list the files in `fixtures/story_packs/media_archive` to see the packs for that bank.
I will view `fixtures/story_packs/media_archive/broadcast_history_comedy.json` to inspect its contents.
I will view `src/upstream_story_lab/ledger_verifiers.py` to see how the announcer news coda is validated and check if there is a mismatch with the packs' coda modes.
I will search the `authoring_executor.py` file to see where ledger validators/verifiers are invoked.
I will view `src/upstream_story_lab/authoring_executor.py` to see the acceptance and validation flow for the announcer coda and other jobs.
I will view `src/upstream_story_lab/authoring_executor.py` from line 1120 to 1200 to inspect the `_accept_open` and `_accept_coda` methods.
I will view the next block of lines in `src/upstream_story_lab/authoring_executor.py` (lines 1201 to 1300) to find the acceptance logic for announcer open and coda.
I will view `src/upstream_story_lab/authoring_executor.py` lines 1301 to 1420.
I will view `src/upstream_story_lab/authoring_executor.py` lines 1421 to 1500.
I will search the `authoring_executor.py` file for references to `closing_fact_id` to see how it is selected.
I will view the `assign_story_facts` and related setup in `src/upstream_story_lab/authoring_executor.py` from line 600 to 710.
I will list the files in `fixtures/story_packs/public_domain` to see the packs for the public domain story bank.
I will list the files in the `fixtures/story_packs/experimental` directory.
I will view `fixtures/story_packs/experimental/simple_4_prompt_experimental.json` to inspect its contents.
I will view `fixtures/pipelines.json` to see how pipelines are configured.
I will view `src/upstream_story_lab/profiles.py` to check the prompt profile validation logic.
I will search `src/upstream_story_lab/authoring_executor.py` for references to `resolve_profile` to see if and how the executor uses it.
I will search the codebase for references to `resolve_profile` to see where the Resolved Prompt Profile is constructed.
I will view `src/upstream_story_lab/bridge.py` to understand the bridge layer and how it interfaces between ComfyUI/production and the executor.
I will view the contents of `nodes.py` to see how the ComfyUI nodes wire up the executor and the bridge.
I will view `src/upstream_story_lab/source_window.py` to inspect the tiling, excerpt bounds, collapse floor, and check for any off-by-one bugs.
I will search for `_job_context` in `src/upstream_story_lab/authoring_executor.py` to see where the source block is attached to the prompt context.
I will view `src/upstream_story_lab/authoring_executor.py` from line 860 to 980 to inspect the job context assembly and the prompt rendering logic.
I will search for `_act_window` in `src/upstream_story_lab/authoring_executor.py` to verify how it behaves.
I will view the `_act_window` method implementation in `src/upstream_story_lab/authoring_executor.py`.
I will search for `self.source_document` in `src/upstream_story_lab/authoring_executor.py` to see where it gets initialized.
I will view `src/upstream_story_lab/spoken_text_policy.py` to understand how the spoken text policy and its heuristic checks/exemptions work.
I will search the codebase for `build_trusted_receipt_verifiers` to see what is passed as `carried_sources` during validation or execution.
I will view lines 1800 to 1830 of `src/upstream_story_lab/authoring_executor.py` to see what is passed to `build_trusted_receipt_verifiers` when building receipt verifiers in the executor.
I will view `src/upstream_story_lab/authoring_executor.py` lines 1100 to 1120 to see what carriage context is passed during the dialogue job validation.
I will view `fixtures/story_packs/public_domain/faithful_radio_adaptation.json` to inspect its prompt structures.
I will list the files in `fixtures/source_banks/shakespeare` to inspect the Shakespeare bank files.
I will search for `SourceBankSpec` in `src/upstream_story_lab/contracts.py` to see the structure a registered bank must follow.
I will view `contracts.py` around line 177 to check the model definition of `SourceBankSpec`.
I will view `src/upstream_story_lab/interpreters.py` to inspect the registered source interpreters.
I will view the first 100 lines of `fixtures/source_banks/shakespeare/curated_scenes.json` to understand the Shakespeare bank data structure.
I will view the beginning of `src/upstream_story_lab/registry.py` to see how the banks and source packets are loaded and registered.
I will view lines 101 to 142 of `src/upstream_story_lab/registry.py` to see the pack loading and validation logic.
I will search for `allowed_seam_variables` in `src/upstream_story_lab/contracts.py` to see what variables are allowed in templates.
I will view `contracts.py` lines 85 to 169 to understand the template variable validation.
I will search for `LABEL_TEMPLATE_VARIABLES` and `SEAM_RUNTIME_VARIABLES` definitions in `src/upstream_story_lab/contracts.py`.
I will view `contracts.py` lines 60 to 90.
I will search for `render_` or `format(` or prompt rendering logic in `src/upstream_story_lab/authoring_executor.py`.
I will view `src/upstream_story_lab/authoring_executor.py` lines 530 to 600 to inspect the `render_job_prompt` function.
I will search `src/upstream_story_lab/authoring_executor.py` for references to `line_grounding` to see if it is used in the staged authoring executor.
I will run a python command to check if all story packs declare all eight job prompts.
I will run a python command to output the `announcer_news_coda` prompt for each story pack to check if they all correctly instruct the model to return the fact_id and mention the fact claim.
I will search for the definition of `AnnouncerCodaPayload` in `src/upstream_story_lab/authoring_executor.py`.
I will view the `AnnouncerCodaPayload` model definition in `src/upstream_story_lab/authoring_executor.py`.
I will list the directories and files in `fixtures/public_domain_sources` to see how the public domain stories and their packets are structured.
I will list the files in `fixtures/source_packets` to see the source packets.
I will view `fixtures/source_packets/public_domain_story.json` to see how its facts are defined.
I will search for `source_packet_bytes` in `src/upstream_story_lab/authoring_executor.py` to see where it comes from.
I will view the `AuthoringBrief` model definition in `src/upstream_story_lab/authoring_executor.py` to see its fields.
I will search the tests for `source_packet_bytes` to see how it is constructed and passed to the brief.
I will search the entire codebase for references to `source_packet_bytes`.
I will search for references to `AuthoringBrief` in `tests/test_bank_act_proofs.py`.
I will search the `tests` directory for references to `AuthoringBrief` to see where the test briefs are defined.
I will search the entire repository for references to `AuthoringBrief` to find how briefs are instantiated.
I will view `scripts/generate_bank_act_proofs.py` to understand how the test proofs for each bank are generated and structured.
I will view `fixtures/story_recovery/v2/source_packets/public_domain_tell_tale_heart_20260814.json` to see how its facts are structured.
I will view `src/upstream_story_lab/compat.py` to check the compatibility fields and constants.
I will search for `author_story_ledger` in `src/upstream_story_lab/authoring_executor.py` to see how it sequences the execution of the story authoring jobs.
I will view the `author_story_ledger` function implementation at the end of `src/upstream_story_lab/authoring_executor.py`.
I will search for `def run` in `src/upstream_story_lab/authoring_executor.py` to inspect the main execution loop.
I will view `src/upstream_story_lab/authoring_executor.py` lines 725 to 810 to inspect `_StagedRun.run()`.
I will search for `StagedModelProvider` in `src/upstream_story_lab/authoring_executor.py`.
I will view the `StagedModelProvider` protocol definition in `src/upstream_story_lab/authoring_executor.py`.
I will view `src/upstream_story_lab/runner.py` to see what model provider implementations are defined.
I will view `src/upstream_story_lab/scripted_provider.py` to see how the scripted story provider works.
I will view `CUSTOM_SOURCE_BANK_GUIDE.md` to see the instructions for registering a custom bank.
I will list the contents of `fixtures/source_banks/shakespeare/sources` to inspect the Shakespeare text source files.
I will view `fixtures/source_banks/shakespeare/sources/macbeth__act1_scene3.provenance.json` to inspect the structure of the Shakespeare provenance records.
I will view the rest of `src/upstream_story_lab/registry.py` to see how public domain manifests and source packets are loaded.
I will view the rest of `src/upstream_story_lab/registry.py`.
I will view `fixtures/source_banks/shakespeare/roster_gender_supplement.json` to understand the supplementary gender records.
I will search the codebase for references to `gender` or `roster_gender_supplement` to see how Shakespeare's gender roster is used.
I will search the `src/` directory for references to `gender` to see how gender validation or schema properties are handled.
I will search the `tests/` directory for references to `gender` to see how the tests use the gender roster or supplement.
I will search the `tests` directory for references to `shakespeare` to see if there are any tests that touch the Shakespeare files.
I will view `tests/test_spoken_text_policy_v2.py` to see how it uses the Shakespeare scenes and tests the exemption policy.
I will view `src/upstream_story_lab/preview.py` to see how story leakage is scanned and validated.
I will search for `_AcceptedSpeechRow` in `src/upstream_story_lab/authoring_executor.py` to check their structure.
I will view lines 420 to 450 of `src/upstream_story_lab/authoring_executor.py`.
I will search for references to `self.final_cast` in `src/upstream_story_lab/authoring_executor.py` to see how it is managed.
I will view `_common_context` implementation in `src/upstream_story_lab/authoring_executor.py` lines 835 to 865.
I will search for the definition of `_compile_story_ledger` in `src/upstream_story_lab/authoring_executor.py` to see how the final story ledger is constructed.
I will view `src/upstream_story_lab/authoring_executor.py` lines 1530 to 1600.
I will view lines 1710 to 1750 of `src/upstream_story_lab/authoring_executor.py`.
I will search for `build_story_seal` in `src/upstream_story_lab/ledger_contract.py`.
I will view `src/upstream_story_lab/ledger_contract.py` lines 1050 to 1100 to see how the story seal and outcome receipts are built.
I will search for `verify_story_acceptance` in `src/upstream_story_lab/ledger_contract.py`.
I will view lines 980 to 1050 of `src/upstream_story_lab/ledger_contract.py` to check how the verifier registry is selected and used in `verify_story_acceptance`.
I will search for `class StoryLedger` in `src/upstream_story_lab/ledger_contract.py`.
I will view `src/upstream_story_lab/ledger_contract.py` lines 565 to 600.
