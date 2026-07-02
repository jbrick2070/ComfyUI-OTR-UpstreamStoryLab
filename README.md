# Upstream Story Lab

Status: live standalone ComfyUI custom-node lab. This folder registers preview
and validation nodes under `OTR/Upstream Story Lab`, but it is not imported by
the production OldTimeRadio node package and is not wired into the canonical
workflow.

Purpose:

```text
source_bank -> source material -> story_model -> story_pipeline -> story pack
story pack -> ledger_writing_spec -> existing production ledger
visual_style -> visual policy -> ledger visual directives
```

This folder exists so the upstream story architecture can be built, previewed,
reviewed, and validated separately before transplanting into the live OTR
workflow.

Hard rules:

- Do not import this folder from production nodes until the transplant chunk.
- Do not edit `workflows/otr_scifi_16gb_full.json` from this lab.
- Do not add compatibility fallbacks here.
- The live preview nodes must fail loudly on bad source/story/style selections.
- Unknown source banks, story models, or visual styles should be treated as
  hard errors in the eventual code.
- Fixtures should be network-free and safe to run in tests.

Suggested layout:

- `fixtures/source_packets/`: sample source material packets.
- `fixtures/story_packs/`: cloneable prompt/content packs by source/model.
- `fixtures/public_domain_sources/`: sample source folders for books, comics,
  plays, stories, etc.
- `fixtures/source_bank_schemas/`: custom source-bank schema templates.
- `fixtures/visual_styles/`: sample visual style policy JSON.
- `CUSTOM_SOURCE_BANK_GUIDE.md`: guide for making a new source bank.
- `TRANSPLANT_MANIFEST.md`: checklist for moving proven pieces into production.

The core design distinction:

- `source_bank` decides where the material comes from.
- `story_model` decides the dramatic/tonal writing shape.
- `story_pipeline` decides the LLM pass structure.
- `visual_style` decides still/video rendering language.

Treat source lanes as separate models/pipelines from the start:

- science RSS/news
- media RSS/archive
- public-domain source folders
- custom source-bank schemas
- simple 4-prompt experimental

The first build may clone the current many-pass scaffold for each lane, but the
lanes should stay separate so later experiments can change one model's LLM
scaffolding without hurting the others.

Future source-bank dropdown:

- `science_news` / "Sci-Fi Science News"
- `media_archive` / "Media RSS / Archive"
- `public_domain_story` / "Public Domain"
- `custom_source_bank` / "+ Add Your Own"

`custom_source_bank` is not a fallback. It is a guided extension lane. Until a
valid schema/profile is supplied, selecting it should fail with a clear message
that points to `CUSTOM_SOURCE_BANK_GUIDE.md`.

Media archive note:

The media-archive source bank must not become sci-fi anthology plotting with
archive nouns swapped in. Its initial story models are restoration adventure,
cinematic humorous, happy archive mystery, gentle thriller, and broadcast
history comedy.

Experimental pipeline note:

`simple_4_prompt_experimental` is exposed as a visible experiment, not a hidden
fallback. It tests whether a stronger LLM can produce a clean ledger through:

1. creative story pass
2. creative ledger-fill pass
3. technical schema cleanup pass
4. final technical ledger consistency audit

If it fails, it fails loudly; it must never fall back to the legacy story
builder.

An optional adaptive cleanup experiment may ask the technical model whether one
more cleanup pass is needed and which approved local technical model should run
it. Python still owns the stop condition: deterministic validators pass, or the
hard `max_cleanup_passes` cap is reached and the run fails loudly.
