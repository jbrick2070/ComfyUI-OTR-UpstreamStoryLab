"""Upstream story lab v2 - transplant workspace package.

Not imported by production. Prototypes the multi-source story architecture
(banks/packs/pipelines/styles as JSON; Python validates, routes, executes,
fails loudly) and emits the bridge artifact production will consume at the
explicit transplant chunk.
"""

from .contracts import (
    BridgeArtifact,
    LedgerWritingSpec,
    MetaMirrors,
    PipelineSpec,
    PublicDomainSourceManifest,
    Resolution,
    SourceBankSpec,
    SourceMaterialPacket,
    StoryInputPacket,
    StoryPack,
    StoryPromptProfile,
    VisualStylePolicy,
)
from .registry import Registry, RegistryError, UnknownIdError
from .ledger_contract import (
    LedgerContractError,
    LedgerEnvelope,
    StoryBody,
    StoryLedger,
    StorySeal,
    assert_story_unchanged,
    build_story_seal,
    canonical_bytes,
    canonical_sha256,
    verify_story_acceptance,
    verify_story_envelope,
)

__all__ = [
    "BridgeArtifact",
    "LedgerWritingSpec",
    "LedgerContractError",
    "LedgerEnvelope",
    "MetaMirrors",
    "PipelineSpec",
    "PublicDomainSourceManifest",
    "Registry",
    "RegistryError",
    "Resolution",
    "SourceBankSpec",
    "SourceMaterialPacket",
    "StoryInputPacket",
    "StoryBody",
    "StoryLedger",
    "StoryPack",
    "StoryPromptProfile",
    "StorySeal",
    "UnknownIdError",
    "VisualStylePolicy",
    "assert_story_unchanged",
    "build_story_seal",
    "canonical_bytes",
    "canonical_sha256",
    "verify_story_acceptance",
    "verify_story_envelope",
]
