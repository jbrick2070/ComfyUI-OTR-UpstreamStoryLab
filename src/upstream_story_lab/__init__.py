"""Isolated upstream story lab package.

This package is intentionally outside ``nodes/`` and is not imported by
production code. It exists to prototype source packets, story models, prompt
profiles, and visual policies before a later transplant.
"""

from .contracts import (
    LedgerWritingSpec,
    PublicDomainSourceManifest,
    SourceMaterialPacket,
    StoryInputPacket,
    StoryModelSpec,
    StoryPack,
    StoryPromptProfile,
    VisualStylePolicy,
)

__all__ = [
    "LedgerWritingSpec",
    "PublicDomainSourceManifest",
    "SourceMaterialPacket",
    "StoryInputPacket",
    "StoryModelSpec",
    "StoryPack",
    "StoryPromptProfile",
    "VisualStylePolicy",
]
