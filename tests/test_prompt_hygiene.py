"""Style contract for every pack's bank direction.

`job_prompts` is the ONLY channel a pack has to the model, so the rules that
govern what may be said there are enforced here rather than left to reviewer
attention:

- every authoring job gets direction, so no model call runs voiceless;
- plain ASCII, because these strings cross PowerShell and JSON on Windows and
  smart quotes arrive as mojibake;
- no length authority - `act_count` is the only length control the lab has,
  and a word budget in a prompt quietly becomes one;
- no content guardrails. The operator directive is explicit: generated episode
  content is not filtered. A pack that forbids the source's own violence turns
  a Macbeth adaptation into a fidelity defect, which is what this roster
  migration exists to remove.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from upstream_story_lab.contracts import AUTHORING_JOB_SEAMS

ROOT = Path(__file__).resolve().parents[1]
PACK_PATHS = sorted((ROOT / "fixtures" / "story_packs").rglob("*.json"))

#: Length/budget authority in any form. `act_count` is the only length control.
FORBIDDEN_LENGTH_AUTHORITY = (
    "word count",
    "word_count",
    "wordcount",
    "target words",
    "target_words",
    "max_words",
    "min_words",
    "word budget",
    "word_budget",
    "recommended_word_budget",
    "words long",
    "words or fewer",
    "words or less",
    "no more than",
    "at most",
    "character limit",
    "runtime of",
)

#: Content filtering, softeners, and family-friendly clauses. Phrases, not bare
#: words: a pack may legitimately instruct that the source's own violence be
#: carried as the author staged it, and that is the opposite of a guardrail.
FORBIDDEN_CONTENT_GUARDRAILS = (
    "sfw",
    "family-friendly",
    "family friendly",
    "keep it clean",
    "profanity",
    "graphic violence",
    "avoid blood",
    "no weapons",
    "no guns",
    "no knives",
    "keep harm low",
    "never cruel",
    "avoid violence",
    "gore",
    "tasteful",
)

#: One prompt per job serves small, medium, and frontier models alike.
FORBIDDEN_MODEL_TIERING = (
    "if you are a",
    "smaller model",
    "larger model",
    "frontier model",
    "7b",
    "70b",
    "gpt-",
    "claude",
    "llama",
)


def _packs() -> list[tuple[str, dict]]:
    out = []
    for path in PACK_PATHS:
        out.append((str(path.relative_to(ROOT)), json.loads(
            path.read_text(encoding="utf-8"))))
    return out


PACKS = _packs()


def test_packs_were_discovered() -> None:
    assert PACKS, "no story packs found to check"


@pytest.mark.parametrize("rel,pack", PACKS, ids=[p[0] for p in PACKS])
def test_pack_declares_every_authoring_job(rel: str, pack: dict) -> None:
    assert set(pack.get("job_prompts", {})) == set(AUTHORING_JOB_SEAMS), rel


@pytest.mark.parametrize("rel,pack", PACKS, ids=[p[0] for p in PACKS])
def test_pack_prompt_text_is_plain_ascii(rel: str, pack: dict) -> None:
    for job, text in pack.get("job_prompts", {}).items():
        bad = sorted({c for c in text if ord(c) > 127})
        assert not bad, f"{rel}:{job} carries non-ASCII {bad}"


@pytest.mark.parametrize("rel,pack", PACKS, ids=[p[0] for p in PACKS])
def test_pack_prompts_carry_no_forbidden_vocabulary(rel: str, pack: dict) -> None:
    for job, text in pack.get("job_prompts", {}).items():
        low = text.lower()
        for token in FORBIDDEN_LENGTH_AUTHORITY:
            assert token not in low, f"{rel}:{job} carries length authority {token!r}"
        for token in FORBIDDEN_CONTENT_GUARDRAILS:
            assert token not in low, f"{rel}:{job} carries a content guardrail {token!r}"
        for token in FORBIDDEN_MODEL_TIERING:
            assert token not in low, f"{rel}:{job} tiers by model {token!r}"


@pytest.mark.parametrize("rel,pack", PACKS, ids=[p[0] for p in PACKS])
def test_pack_metadata_carries_no_forbidden_vocabulary(rel: str, pack: dict) -> None:
    """tone_guardrails and outline_rules_extra reach the resolved profile too."""

    fields = list(pack.get("tone_guardrails", []))
    fields.append(pack.get("outline_rules_extra", ""))
    for text in fields:
        low = str(text).lower()
        for token in FORBIDDEN_LENGTH_AUTHORITY:
            assert token not in low, f"{rel} metadata carries length authority {token!r}"
        for token in FORBIDDEN_CONTENT_GUARDRAILS:
            assert token not in low, f"{rel} metadata carries a guardrail {token!r}"
