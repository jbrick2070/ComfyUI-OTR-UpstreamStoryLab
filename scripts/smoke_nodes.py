"""ComfyUI import smoke: node mappings load and dropdown choices discover
from the registry (no ComfyUI required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nodes  # noqa: E402


class SmokeError(RuntimeError):
    """A gate failed.  Raised, not asserted, so ``python -O`` cannot skip it."""


def require(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


mappings = sorted(nodes.NODE_CLASS_MAPPINGS)
banks = nodes._bank_choices()
models = nodes._model_choices()
styles = nodes._style_choices()
pipelines = nodes._pipeline_choices()

require(
    mappings
    == [
        "OTR_BridgeArtifactEmit",
        "OTR_StoryPackPreview",
        "OTR_UpstreamStoryLabValidator",
    ],
    f"unexpected node mappings: {mappings}",
)
EXPECTED_BANKS = [
    "custom_source_bank",
    "media_archive",
    "original",
    "public_domain",
    "scifi_news",
    "scifi_news_pro",
    "shakespeare",
]
# The full roster, not a spot check: a bank lost from the dropdown must fail
# the smoke rather than pass silently. _bank_choices returns sorted ids.
require(
    banks == EXPECTED_BANKS,
    f"bank dropdown roster drifted: {banks} != {EXPECTED_BANKS}",
)
require(
    "simple_4_prompt_experimental" not in [m for m in models if m != "auto"],
    "experimental pack must not appear in narrative model choices",
)
require(
    "archival_documentary" in styles and "auto" in styles,
    f"style choices are incomplete: {styles}",
)
require("legacy_many_pass" in pipelines, f"pipeline choices: {pipelines}")

for node_class in (
    nodes.OTR_StoryPackPreview,
    nodes.OTR_BridgeArtifactEmit,
):
    act_type, act_meta = node_class.INPUT_TYPES()["required"]["act_count"]
    require(act_type == "INT", f"act_count widget type is {act_type!r}")
    require(
        act_meta == {"default": 3, "min": 1, "max": 8, "step": 1},
        f"act_count widget metadata drifted: {act_meta}",
    )

report = nodes.OTR_UpstreamStoryLabValidator().validate()[0]
require(
    report.startswith("OK Upstream Story Lab v2"),
    f"validator report did not start with OK: {report[:80]}",
)

print("smoke OK")
print("nodes:", mappings)
print("banks:", banks)
print("styles:", styles)
