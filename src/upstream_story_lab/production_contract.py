"""Strict append-only production-plane contract for Ledger Bible v1.

The production plane records completed attempts and explicit acceptance events.
It never owns authored story content.  This module is deliberately independent
from :mod:`ledger_contract` so the envelope may import these types without a
circular dependency.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timedelta
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


PRODUCTION_STATE_SCHEMA_VERSION = "otr.production_state.v1"
HEX64_PATTERN = r"^[0-9a-f]{64}$"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"

PRODUCTION_PHASE_REGISTRY = (
    ("workspace_identity", "episode_workspace"),
    ("cast_routing", "cast_lock"),
    ("voice_render", "voice_renderers"),
    ("music_render", "music_renderer"),
    ("speech_timeline", "scene_sequencer"),
    ("audio_enhance", "audio_enhance"),
    ("master_audio", "episode_assembler"),
    ("procgen_video", "signal_lost_video"),
    ("visual_plan", "shot_lock"),
    ("image_render", "image_dispatcher"),
    ("video_render", "video_render_batch"),
    ("silent_composite", "silent_composite"),
    ("scopes", "scene_aware_scopes"),
    ("post_blend", "post_upscale_procgen_blend"),
    ("captions", "caption_burn"),
    ("credits", "credits_roll"),
    ("publication", "master_audio_mux"),
    ("audit", "full_run_audit"),
)
PRODUCTION_PHASE_IDS = tuple(phase_id for phase_id, _ in PRODUCTION_PHASE_REGISTRY)
PRODUCTION_PHASE_OWNERS = dict(PRODUCTION_PHASE_REGISTRY)

PhaseId = Literal[
    "workspace_identity",
    "cast_routing",
    "voice_render",
    "music_render",
    "speech_timeline",
    "audio_enhance",
    "master_audio",
    "procgen_video",
    "visual_plan",
    "image_render",
    "video_render",
    "silent_composite",
    "scopes",
    "post_blend",
    "captions",
    "credits",
    "publication",
    "audit",
]
StoryRefKind = Literal[
    "source_packet",
    "source",
    "fact",
    "cast",
    "scene",
    "shot",
    "beat",
    "line",
    "music_cue",
    "sequence",
]
ArtifactKind = Literal[
    "workspace_manifest",
    "cast_route_manifest",
    "line_audio",
    "music_audio",
    "cue_manifest",
    "speech_timeline",
    "enhanced_audio",
    "master_audio",
    "procgen_video",
    "visual_plan",
    "image",
    "video_clip",
    "clip_manifest",
    "silent_video",
    "scopes_video",
    "post_blend_video",
    "captions",
    "captioned_video",
    "credits_manifest",
    "credits_video",
    "publication_audio",
    "publication_video",
    "obs_scene_collection",
    "audit_report",
]


class ProductionContractError(ValueError):
    """The proposed production journal violates Ledger Bible v1."""


class StrictProductionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        revalidate_instances="always",
        validate_assignment=True,
    )


def _canonical_text(value: str) -> str:
    if not value.strip():
        raise ProductionContractError("required production text cannot be blank")
    if unicodedata.normalize("NFC", value) != value:
        raise ProductionContractError("production text must already be NFC")
    return value


CanonicalText = Annotated[str, AfterValidator(_canonical_text)]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProductionContractError("production timestamps must be UTC")
    return value


UtcDatetime = Annotated[datetime, AfterValidator(_utc)]


def _relative_posix_path(value: str) -> str:
    value = _canonical_text(value)
    if value.startswith("/") or "\\" in value:
        raise ProductionContractError("artifact paths must be relative POSIX paths")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ProductionContractError("artifact paths cannot contain empty/dot segments")
    return value


RelativePosixPath = Annotated[str, AfterValidator(_relative_posix_path)]


def _unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ProductionContractError(f"{label} must be unique")


def _production_plain(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _assert_production_canonical(value: object, path: str = "$") -> None:
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ProductionContractError(f"non-NFC string at {path}")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        raise ProductionContractError(f"floating point is forbidden at {path}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_production_canonical(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProductionContractError(f"non-string object key at {path}")
            _assert_production_canonical(key, f"{path}.<key>")
            _assert_production_canonical(item, f"{path}.{key}")
        return
    raise ProductionContractError(
        f"unsupported canonical value {type(value).__name__} at {path}"
    )


def production_canonical_bytes(value: object) -> bytes:
    plain = _production_plain(value)
    _assert_production_canonical(plain)
    return json.dumps(
        plain,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def production_sha256(value: object) -> str:
    return hashlib.sha256(production_canonical_bytes(value)).hexdigest()


class StoryRef(StrictProductionModel):
    kind: StoryRefKind
    ref_id: str = Field(pattern=ID_PATTERN)


class ArtifactReceipt(StrictProductionModel):
    artifact_id: str = Field(pattern=ID_PATTERN)
    artifact_kind: ArtifactKind
    media_type: CanonicalText
    storage_root_id: str = Field(pattern=ID_PATTERN)
    relative_path: RelativePosixPath
    content_sha256: str = Field(pattern=HEX64_PATTERN)
    size_bytes: int = Field(ge=0)
    durability: Literal["run_local", "episode_local", "published"]
    story_refs: list[StoryRef] = Field(default_factory=list)
    duration_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_story_refs(self) -> "ArtifactReceipt":
        keys = [f"{ref.kind}:{ref.ref_id}" for ref in self.story_refs]
        _unique(keys, "artifact story references")
        return self


class ArtifactRef(StrictProductionModel):
    phase_id: PhaseId
    acceptance_id: str = Field(pattern=ID_PATTERN)
    accepted_attempt_id: str = Field(pattern=ID_PATTERN)
    artifact_id: str = Field(pattern=ID_PATTERN)
    content_sha256: str = Field(pattern=HEX64_PATTERN)


class DependencyRef(StrictProductionModel):
    phase_id: PhaseId
    acceptance_id: str = Field(pattern=ID_PATTERN)
    accepted_attempt_id: str = Field(pattern=ID_PATTERN)
    acceptance_sha256: str = Field(pattern=HEX64_PATTERN)


class ProducerIdentity(StrictProductionModel):
    component_id: str = Field(pattern=ID_PATTERN)
    component_version: CanonicalText
    source_revision: CanonicalText
    config_sha256: str = Field(pattern=HEX64_PATTERN)


class FailureReceipt(StrictProductionModel):
    code: str = Field(pattern=ID_PATTERN)
    message: CanonicalText
    retriable: bool
    diagnostic_artifact_ids: list[str] = Field(default_factory=list)

    @field_validator("diagnostic_artifact_ids")
    @classmethod
    def validate_diagnostic_ids(cls, value: list[str]) -> list[str]:
        _unique(value, "diagnostic artifact IDs")
        return value


class RationalFps(StrictProductionModel):
    numerator: int = Field(gt=0)
    denominator: int = Field(gt=0)


class ProcessorStep(StrictProductionModel):
    processor_id: str = Field(pattern=ID_PATTERN)
    processor_version: CanonicalText
    config_sha256: str = Field(pattern=HEX64_PATTERN)


class PhaseReceiptBase(StrictProductionModel):
    input_artifact_ids: list[str] = Field(default_factory=list)
    output_artifact_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_artifact_ids(self) -> "PhaseReceiptBase":
        _unique(self.input_artifact_ids, "receipt input artifact IDs")
        _unique(self.output_artifact_ids, "receipt output artifact IDs")
        return self


class WorkspaceIdentityReceipt(PhaseReceiptBase):
    phase_id: Literal["workspace_identity"] = "workspace_identity"
    operation: Literal["initialize", "rename", "rebase"]
    workspace_id: str = Field(pattern=ID_PATTERN)
    prior_workspace_id: str | None = Field(default=None, pattern=ID_PATTERN)
    storage_root_id: str = Field(pattern=ID_PATTERN)
    relative_workspace_path: RelativePosixPath
    requesting_phase: PhaseId | None = None
    rebased_artifact_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_operation(self) -> "WorkspaceIdentityReceipt":
        if self.operation == "initialize" and self.prior_workspace_id is not None:
            raise ProductionContractError(
                "workspace initialization cannot name a prior workspace"
            )
        if self.operation != "initialize" and self.prior_workspace_id is None:
            raise ProductionContractError(
                "workspace rename/rebase requires prior_workspace_id"
            )
        _unique(self.rebased_artifact_ids, "rebased artifact IDs")
        return self


class CastRoute(StrictProductionModel):
    cast_ref: StoryRef
    engine_id: str = Field(pattern=ID_PATTERN)
    voice_ref_id: str = Field(pattern=ID_PATTERN)
    provider_voice_id: CanonicalText
    preset_id: CanonicalText
    presentation: CanonicalText
    route_id: str = Field(pattern=ID_PATTERN)
    fallback_route_id: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def validate_cast_ref(self) -> "CastRoute":
        if self.cast_ref.kind != "cast":
            raise ProductionContractError("cast route must reference a cast row")
        return self


class CastRoutingReceipt(PhaseReceiptBase):
    phase_id: Literal["cast_routing"] = "cast_routing"
    policy_id: str = Field(pattern=ID_PATTERN)
    policy_version: CanonicalText
    routes: list[CastRoute] = Field(min_length=1)


class LineAudioItem(StrictProductionModel):
    line_ref: StoryRef
    artifact_id: str = Field(pattern=ID_PATTERN)
    engine_id: str = Field(pattern=ID_PATTERN)
    model_id: CanonicalText
    voice_ref_id: str = Field(pattern=ID_PATTERN)
    preset_id: CanonicalText
    provider_id: CanonicalText
    route_id: str = Field(pattern=ID_PATTERN)
    cache_key: CanonicalText
    cache_hit: bool
    duration_ms: int = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(ge=1, le=32)

    @model_validator(mode="after")
    def validate_line_ref(self) -> "LineAudioItem":
        if self.line_ref.kind != "line":
            raise ProductionContractError("line audio must reference a spoken line")
        return self


class VoiceRenderReceipt(PhaseReceiptBase):
    phase_id: Literal["voice_render"] = "voice_render"
    lines: list[LineAudioItem] = Field(min_length=1)


class CueAudioItem(StrictProductionModel):
    cue_ref: StoryRef
    artifact_id: str = Field(pattern=ID_PATTERN)
    engine_id: str = Field(pattern=ID_PATTERN)
    model_id: CanonicalText
    duration_ms: int = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(ge=1, le=32)

    @model_validator(mode="after")
    def validate_cue_ref(self) -> "CueAudioItem":
        if self.cue_ref.kind != "music_cue":
            raise ProductionContractError("music audio must reference a music cue")
        return self


class MusicRenderReceipt(PhaseReceiptBase):
    phase_id: Literal["music_render"] = "music_render"
    cues: list[CueAudioItem] = Field(min_length=1)
    cue_manifest_artifact_id: str = Field(pattern=ID_PATTERN)


class TimelineItem(StrictProductionModel):
    sequence_ref: StoryRef
    content_ref: StoryRef
    input_artifact_id: str = Field(pattern=ID_PATTERN)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_refs(self) -> "TimelineItem":
        if self.sequence_ref.kind != "sequence":
            raise ProductionContractError("timeline item must name a sequence row")
        if self.content_ref.kind not in {"line", "music_cue"}:
            raise ProductionContractError(
                "timeline content must reference a line or music cue"
            )
        return self


class SpeechTimelineReceipt(PhaseReceiptBase):
    phase_id: Literal["speech_timeline"] = "speech_timeline"
    items: list[TimelineItem] = Field(min_length=1)
    timeline_artifact_id: str = Field(pattern=ID_PATTERN)
    total_duration_ms: int = Field(gt=0)


class AudioEnhanceReceipt(PhaseReceiptBase):
    phase_id: Literal["audio_enhance"] = "audio_enhance"
    processor_chain: list[ProcessorStep] = Field(min_length=1)
    enhanced_audio_artifact_id: str = Field(pattern=ID_PATTERN)
    duration_ms: int = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(ge=1, le=32)


class MasterTimingItem(StrictProductionModel):
    content_ref: StoryRef
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_content_ref(self) -> "MasterTimingItem":
        if self.content_ref.kind not in {"line", "music_cue"}:
            raise ProductionContractError(
                "master timing must reference a line or music cue"
            )
        return self


class TransitionReceipt(StrictProductionModel):
    transition_id: str = Field(pattern=ID_PATTERN)
    kind: Literal["fade_in", "fade_out", "crossfade", "mix"]
    at_ms: int = Field(ge=0)
    duration_ms: int = Field(ge=0)


class MasterAudioReceipt(PhaseReceiptBase):
    phase_id: Literal["master_audio"] = "master_audio"
    master_audio_artifact_id: str = Field(pattern=ID_PATTERN)
    timing: list[MasterTimingItem] = Field(min_length=1)
    transitions: list[TransitionReceipt] = Field(default_factory=list)
    total_duration_ms: int = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(ge=1, le=32)


class ProcgenVideoReceipt(PhaseReceiptBase):
    phase_id: Literal["procgen_video"] = "procgen_video"
    base_video_artifact_id: str = Field(pattern=ID_PATTERN)
    engine_id: str = Field(pattern=ID_PATTERN)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    fps: RationalFps
    frame_count: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    workspace_rename_requested: bool = False


class VisualRequest(StrictProductionModel):
    request_id: str = Field(pattern=ID_PATTERN)
    shot_ref: StoryRef
    beat_refs: list[StoryRef] = Field(min_length=1)
    line_refs: list[StoryRef] = Field(default_factory=list)
    cast_refs: list[StoryRef] = Field(default_factory=list)
    prompt_sha256: str = Field(pattern=HEX64_PATTERN)
    route_id: str = Field(pattern=ID_PATTERN)

    @model_validator(mode="after")
    def validate_ref_kinds(self) -> "VisualRequest":
        if self.shot_ref.kind != "shot":
            raise ProductionContractError("visual request must reference a shot")
        if any(ref.kind != "beat" for ref in self.beat_refs):
            raise ProductionContractError("visual beat_refs must reference beats")
        if any(ref.kind != "line" for ref in self.line_refs):
            raise ProductionContractError("visual line_refs must reference lines")
        if any(ref.kind != "cast" for ref in self.cast_refs):
            raise ProductionContractError("visual cast_refs must reference cast rows")
        return self


class VisualPlanReceipt(PhaseReceiptBase):
    phase_id: Literal["visual_plan"] = "visual_plan"
    policy_id: str = Field(pattern=ID_PATTERN)
    policy_version: CanonicalText
    plan_revision: int = Field(ge=1)
    plan_artifact_id: str = Field(pattern=ID_PATTERN)
    requests: list[VisualRequest] = Field(min_length=1)


class ImageRenderItem(StrictProductionModel):
    request_id: str = Field(pattern=ID_PATTERN)
    artifact_id: str = Field(pattern=ID_PATTERN)
    story_refs: list[StoryRef] = Field(min_length=1)
    engine_id: str = Field(pattern=ID_PATTERN)
    model_id: CanonicalText
    prompt_sha256: str = Field(pattern=HEX64_PATTERN)
    seed: int = Field(ge=0)
    provenance: CanonicalText


class ImageRenderReceipt(PhaseReceiptBase):
    phase_id: Literal["image_render"] = "image_render"
    images: list[ImageRenderItem] = Field(min_length=1)


class VideoClipItem(StrictProductionModel):
    request_id: str = Field(pattern=ID_PATTERN)
    artifact_id: str = Field(pattern=ID_PATTERN)
    story_refs: list[StoryRef] = Field(min_length=1)
    init_image_artifact_ids: list[str] = Field(default_factory=list)
    engine_id: str = Field(pattern=ID_PATTERN)
    route_id: str = Field(pattern=ID_PATTERN)
    duration_ms: int = Field(gt=0)
    frame_count: int = Field(gt=0)
    fps: RationalFps
    audio_motion_receipt: CanonicalText | None = None


class VideoRenderReceipt(PhaseReceiptBase):
    phase_id: Literal["video_render"] = "video_render"
    clips: list[VideoClipItem] = Field(min_length=1)
    clip_manifest_artifact_id: str = Field(pattern=ID_PATTERN)


class SilentCompositeReceipt(PhaseReceiptBase):
    phase_id: Literal["silent_composite"] = "silent_composite"
    clip_manifest_artifact_id: str = Field(pattern=ID_PATTERN)
    base_video_artifact_id: str | None = Field(default=None, pattern=ID_PATTERN)
    silent_video_artifact_id: str = Field(pattern=ID_PATTERN)
    engine_id: str = Field(pattern=ID_PATTERN)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    fps: RationalFps
    duration_ms: int = Field(gt=0)


class ScopesReceipt(PhaseReceiptBase):
    phase_id: Literal["scopes"] = "scopes"
    clip_manifest_artifact_id: str = Field(pattern=ID_PATTERN)
    audio_artifact_id: str | None = Field(default=None, pattern=ID_PATTERN)
    scopes_artifact_id: str = Field(pattern=ID_PATTERN)
    processor: ProcessorStep


class PostBlendReceipt(PhaseReceiptBase):
    phase_id: Literal["post_blend"] = "post_blend"
    foreground_artifact_id: str = Field(pattern=ID_PATTERN)
    base_artifact_id: str | None = Field(default=None, pattern=ID_PATTERN)
    scopes_artifact_id: str | None = Field(default=None, pattern=ID_PATTERN)
    final_silent_video_artifact_id: str = Field(pattern=ID_PATTERN)
    processor_chain: list[ProcessorStep] = Field(min_length=1)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)


class CaptionsReceipt(PhaseReceiptBase):
    phase_id: Literal["captions"] = "captions"
    input_video_artifact_id: str = Field(pattern=ID_PATTERN)
    timeline_artifact_id: str = Field(pattern=ID_PATTERN)
    captions_artifact_id: str = Field(pattern=ID_PATTERN)
    captioned_video_artifact_id: str = Field(pattern=ID_PATTERN)
    policy_id: str = Field(pattern=ID_PATTERN)
    policy_version: CanonicalText
    line_refs: list[StoryRef] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_line_refs(self) -> "CaptionsReceipt":
        if any(ref.kind != "line" for ref in self.line_refs):
            raise ProductionContractError("captions must reference spoken lines")
        return self


class CreditsReceipt(PhaseReceiptBase):
    phase_id: Literal["credits"] = "credits"
    input_video_artifact_id: str = Field(pattern=ID_PATTERN)
    credits_manifest_artifact_id: str = Field(pattern=ID_PATTERN)
    credits_video_artifact_id: str = Field(pattern=ID_PATTERN)
    policy_id: str = Field(pattern=ID_PATTERN)
    policy_version: CanonicalText
    credited_refs: list[StoryRef] = Field(min_length=1)


class PublicationDestination(StrictProductionModel):
    destination_id: str = Field(pattern=ID_PATTERN)
    locator: CanonicalText
    published_artifact_ids: list[str] = Field(min_length=1)


class PublicationReceipt(PhaseReceiptBase):
    phase_id: Literal["publication"] = "publication"
    master_audio_artifact_id: str = Field(pattern=ID_PATTERN)
    terminal_video_artifact_id: str = Field(pattern=ID_PATTERN)
    final_audio_artifact_id: str = Field(pattern=ID_PATTERN)
    final_video_artifact_id: str = Field(pattern=ID_PATTERN)
    obs_scene_collection_artifact_id: str = Field(pattern=ID_PATTERN)
    destinations: list[PublicationDestination] = Field(min_length=1)


class AuditCheck(StrictProductionModel):
    check_id: str = Field(pattern=ID_PATTERN)
    status: Literal["pass", "fail"]
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    message: CanonicalText


class AuditReceipt(PhaseReceiptBase):
    phase_id: Literal["audit"] = "audit"
    verdict: Literal["pass"] = "pass"
    policy_id: str = Field(pattern=ID_PATTERN)
    policy_version: CanonicalText
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    pre_audit_production_sha256: str = Field(pattern=HEX64_PATTERN)
    publication_acceptance_id: str = Field(pattern=ID_PATTERN)
    checks: list[AuditCheck] = Field(min_length=1)
    report_artifact_id: str = Field(pattern=ID_PATTERN)


ReceiptT = TypeVar("ReceiptT", bound=PhaseReceiptBase)


class SucceededResult(StrictProductionModel, Generic[ReceiptT]):
    status: Literal["succeeded"] = "succeeded"
    receipt: ReceiptT


class FailedResult(StrictProductionModel):
    status: Literal["failed"] = "failed"
    failure: FailureReceipt


class ProductionAttemptBase(StrictProductionModel):
    attempt_id: str = Field(pattern=ID_PATTERN)
    attempt_number: int = Field(ge=1)
    episode_id: str = Field(pattern=ID_PATTERN)
    run_id: str = Field(pattern=ID_PATTERN)
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    started_at: UtcDatetime
    completed_at: UtcDatetime
    producer: ProducerIdentity
    dependencies: list[DependencyRef] = Field(default_factory=list)
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    produced_artifacts: list[ArtifactReceipt] = Field(default_factory=list)
    story_refs: list[StoryRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_common_attempt(self) -> "ProductionAttemptBase":
        if self.completed_at < self.started_at:
            raise ProductionContractError("attempt completion precedes start")
        _unique(
            [dependency.phase_id for dependency in self.dependencies],
            "attempt dependency phases",
        )
        _unique(
            [artifact.artifact_id for artifact in self.input_artifacts],
            "attempt input artifact IDs",
        )
        _unique(
            [artifact.artifact_id for artifact in self.produced_artifacts],
            "attempt produced artifact IDs",
        )
        _unique(
            [f"{ref.kind}:{ref.ref_id}" for ref in self.story_refs],
            "attempt story references",
        )
        production_canonical_bytes(self)
        return self


def _validate_attempt_result(attempt: ProductionAttemptBase, result: object) -> None:
    produced = {artifact.artifact_id for artifact in attempt.produced_artifacts}
    inputs = {artifact.artifact_id for artifact in attempt.input_artifacts}
    if isinstance(result, FailedResult):
        missing = set(result.failure.diagnostic_artifact_ids) - produced
        if missing:
            raise ProductionContractError(
                f"failure references unknown diagnostic artifacts: {sorted(missing)}"
            )
        return
    if not isinstance(result, SucceededResult):
        raise ProductionContractError("attempt result has no known status")
    receipt = result.receipt
    receipt_inputs = set(receipt.input_artifact_ids)
    receipt_outputs = set(receipt.output_artifact_ids)
    if receipt_inputs != inputs:
        raise ProductionContractError(
            "receipt input_artifact_ids must exactly cover attempt inputs"
        )
    if receipt_outputs != produced:
        raise ProductionContractError(
            "receipt output_artifact_ids must exactly cover produced artifacts"
        )
    undeclared = _nested_artifact_ids(receipt) - receipt_inputs - receipt_outputs
    if undeclared:
        raise ProductionContractError(
            f"receipt uses undeclared artifact IDs: {sorted(undeclared)}"
        )


def _nested_artifact_ids(value: object, field_name: str = "") -> set[str]:
    """Collect typed ``*_artifact_id(s)`` fields below a phase receipt."""

    if isinstance(value, BaseModel):
        found: set[str] = set()
        for name in type(value).model_fields:
            if name in {"input_artifact_ids", "output_artifact_ids"}:
                continue
            item = getattr(value, name)
            if name.endswith("_artifact_id") and isinstance(item, str):
                found.add(item)
                continue
            if name.endswith("_artifact_ids") and isinstance(item, list):
                found.update(entry for entry in item if isinstance(entry, str))
                continue
            found.update(_nested_artifact_ids(item, name))
        return found
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value:
            found.update(_nested_artifact_ids(item, field_name))
        return found
    return set()


class WorkspaceIdentityAttempt(ProductionAttemptBase):
    phase_id: Literal["workspace_identity"] = "workspace_identity"
    owner: Literal["episode_workspace"] = "episode_workspace"
    result: Annotated[
        SucceededResult[WorkspaceIdentityReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "WorkspaceIdentityAttempt":
        _validate_attempt_result(self, self.result)
        return self


class CastRoutingAttempt(ProductionAttemptBase):
    phase_id: Literal["cast_routing"] = "cast_routing"
    owner: Literal["cast_lock"] = "cast_lock"
    result: Annotated[
        SucceededResult[CastRoutingReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "CastRoutingAttempt":
        _validate_attempt_result(self, self.result)
        return self


class VoiceRenderAttempt(ProductionAttemptBase):
    phase_id: Literal["voice_render"] = "voice_render"
    owner: Literal["voice_renderers"] = "voice_renderers"
    result: Annotated[
        SucceededResult[VoiceRenderReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "VoiceRenderAttempt":
        _validate_attempt_result(self, self.result)
        return self


class MusicRenderAttempt(ProductionAttemptBase):
    phase_id: Literal["music_render"] = "music_render"
    owner: Literal["music_renderer"] = "music_renderer"
    result: Annotated[
        SucceededResult[MusicRenderReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "MusicRenderAttempt":
        _validate_attempt_result(self, self.result)
        return self


class SpeechTimelineAttempt(ProductionAttemptBase):
    phase_id: Literal["speech_timeline"] = "speech_timeline"
    owner: Literal["scene_sequencer"] = "scene_sequencer"
    result: Annotated[
        SucceededResult[SpeechTimelineReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "SpeechTimelineAttempt":
        _validate_attempt_result(self, self.result)
        return self


class AudioEnhanceAttempt(ProductionAttemptBase):
    phase_id: Literal["audio_enhance"] = "audio_enhance"
    owner: Literal["audio_enhance"] = "audio_enhance"
    result: Annotated[
        SucceededResult[AudioEnhanceReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "AudioEnhanceAttempt":
        _validate_attempt_result(self, self.result)
        return self


class MasterAudioAttempt(ProductionAttemptBase):
    phase_id: Literal["master_audio"] = "master_audio"
    owner: Literal["episode_assembler"] = "episode_assembler"
    result: Annotated[
        SucceededResult[MasterAudioReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "MasterAudioAttempt":
        _validate_attempt_result(self, self.result)
        return self


class ProcgenVideoAttempt(ProductionAttemptBase):
    phase_id: Literal["procgen_video"] = "procgen_video"
    owner: Literal["signal_lost_video"] = "signal_lost_video"
    result: Annotated[
        SucceededResult[ProcgenVideoReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "ProcgenVideoAttempt":
        _validate_attempt_result(self, self.result)
        return self


class VisualPlanAttempt(ProductionAttemptBase):
    phase_id: Literal["visual_plan"] = "visual_plan"
    owner: Literal["shot_lock"] = "shot_lock"
    result: Annotated[
        SucceededResult[VisualPlanReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "VisualPlanAttempt":
        _validate_attempt_result(self, self.result)
        return self


class ImageRenderAttempt(ProductionAttemptBase):
    phase_id: Literal["image_render"] = "image_render"
    owner: Literal["image_dispatcher"] = "image_dispatcher"
    result: Annotated[
        SucceededResult[ImageRenderReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "ImageRenderAttempt":
        _validate_attempt_result(self, self.result)
        return self


class VideoRenderAttempt(ProductionAttemptBase):
    phase_id: Literal["video_render"] = "video_render"
    owner: Literal["video_render_batch"] = "video_render_batch"
    result: Annotated[
        SucceededResult[VideoRenderReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "VideoRenderAttempt":
        _validate_attempt_result(self, self.result)
        return self


class SilentCompositeAttempt(ProductionAttemptBase):
    phase_id: Literal["silent_composite"] = "silent_composite"
    owner: Literal["silent_composite"] = "silent_composite"
    result: Annotated[
        SucceededResult[SilentCompositeReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "SilentCompositeAttempt":
        _validate_attempt_result(self, self.result)
        return self


class ScopesAttempt(ProductionAttemptBase):
    phase_id: Literal["scopes"] = "scopes"
    owner: Literal["scene_aware_scopes"] = "scene_aware_scopes"
    result: Annotated[
        SucceededResult[ScopesReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "ScopesAttempt":
        _validate_attempt_result(self, self.result)
        return self


class PostBlendAttempt(ProductionAttemptBase):
    phase_id: Literal["post_blend"] = "post_blend"
    owner: Literal["post_upscale_procgen_blend"] = "post_upscale_procgen_blend"
    result: Annotated[
        SucceededResult[PostBlendReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "PostBlendAttempt":
        _validate_attempt_result(self, self.result)
        return self


class CaptionsAttempt(ProductionAttemptBase):
    phase_id: Literal["captions"] = "captions"
    owner: Literal["caption_burn"] = "caption_burn"
    result: Annotated[
        SucceededResult[CaptionsReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "CaptionsAttempt":
        _validate_attempt_result(self, self.result)
        return self


class CreditsAttempt(ProductionAttemptBase):
    phase_id: Literal["credits"] = "credits"
    owner: Literal["credits_roll"] = "credits_roll"
    result: Annotated[
        SucceededResult[CreditsReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "CreditsAttempt":
        _validate_attempt_result(self, self.result)
        return self


class PublicationAttempt(ProductionAttemptBase):
    phase_id: Literal["publication"] = "publication"
    owner: Literal["master_audio_mux"] = "master_audio_mux"
    result: Annotated[
        SucceededResult[PublicationReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "PublicationAttempt":
        _validate_attempt_result(self, self.result)
        return self


class AuditAttempt(ProductionAttemptBase):
    phase_id: Literal["audit"] = "audit"
    owner: Literal["full_run_audit"] = "full_run_audit"
    result: Annotated[
        SucceededResult[AuditReceipt] | FailedResult,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def validate_result(self) -> "AuditAttempt":
        _validate_attempt_result(self, self.result)
        return self


PhaseAttempt = Annotated[
    WorkspaceIdentityAttempt
    | CastRoutingAttempt
    | VoiceRenderAttempt
    | MusicRenderAttempt
    | SpeechTimelineAttempt
    | AudioEnhanceAttempt
    | MasterAudioAttempt
    | ProcgenVideoAttempt
    | VisualPlanAttempt
    | ImageRenderAttempt
    | VideoRenderAttempt
    | SilentCompositeAttempt
    | ScopesAttempt
    | PostBlendAttempt
    | CaptionsAttempt
    | CreditsAttempt
    | PublicationAttempt
    | AuditAttempt,
    Field(discriminator="phase_id"),
]

PHASE_ATTEMPT_TYPES = (
    WorkspaceIdentityAttempt,
    CastRoutingAttempt,
    VoiceRenderAttempt,
    MusicRenderAttempt,
    SpeechTimelineAttempt,
    AudioEnhanceAttempt,
    MasterAudioAttempt,
    ProcgenVideoAttempt,
    VisualPlanAttempt,
    ImageRenderAttempt,
    VideoRenderAttempt,
    SilentCompositeAttempt,
    ScopesAttempt,
    PostBlendAttempt,
    CaptionsAttempt,
    CreditsAttempt,
    PublicationAttempt,
    AuditAttempt,
)


class PhaseAcceptance(StrictProductionModel):
    acceptance_id: str = Field(pattern=ID_PATTERN)
    phase_id: PhaseId
    owner: CanonicalText
    episode_id: str = Field(pattern=ID_PATTERN)
    run_id: str = Field(pattern=ID_PATTERN)
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    accepted_attempt_id: str = Field(pattern=ID_PATTERN)
    accepted_attempt_sha256: str = Field(pattern=HEX64_PATTERN)
    validator_id: str = Field(pattern=ID_PATTERN)
    validator_version: CanonicalText
    accepted_at: UtcDatetime
    supersedes_acceptance_id: str | None = Field(default=None, pattern=ID_PATTERN)


class AttemptEvent(StrictProductionModel):
    event_type: Literal["attempt"] = "attempt"
    attempt: PhaseAttempt


class AcceptanceEvent(StrictProductionModel):
    event_type: Literal["acceptance"] = "acceptance"
    acceptance: PhaseAcceptance


ProductionEvent = Annotated[
    AttemptEvent | AcceptanceEvent,
    Field(discriminator="event_type"),
]


class RunPhase(StrictProductionModel):
    phase_id: PhaseId
    owner: CanonicalText
    disposition: Literal["required", "optional", "omitted"]
    omission_reason: CanonicalText | None = None
    depends_on: list[PhaseId] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_omission(self) -> "RunPhase":
        if self.disposition == "omitted" and self.omission_reason is None:
            raise ProductionContractError("omitted phase requires an omission reason")
        if self.disposition != "omitted" and self.omission_reason is not None:
            raise ProductionContractError(
                "only an omitted phase may carry an omission reason"
            )
        _unique(self.depends_on, "run-phase dependencies")
        return self


def default_run_plan() -> list[RunPhase]:
    """Return an explicit neutral plan; route-specific DAGs replace dependencies."""

    return [
        RunPhase(
            phase_id=phase_id,
            owner=owner,
            disposition="required",
            depends_on=[],
        )
        for phase_id, owner in PRODUCTION_PHASE_REGISTRY
    ]


def _result_succeeded(attempt: PhaseAttempt) -> bool:
    return isinstance(attempt.result, SucceededResult)


def _iter_attempt_artifacts(attempt: PhaseAttempt) -> dict[str, ArtifactReceipt]:
    return {artifact.artifact_id: artifact for artifact in attempt.produced_artifacts}


class ProductionState(StrictProductionModel):
    schema_version: Literal[PRODUCTION_STATE_SCHEMA_VERSION] = (
        PRODUCTION_STATE_SCHEMA_VERSION
    )
    episode_id: str = Field(pattern=ID_PATTERN)
    run_id: str = Field(pattern=ID_PATTERN)
    story_sha256: str = Field(pattern=HEX64_PATTERN)
    created_at: UtcDatetime
    run_plan: list[RunPhase] = Field(min_length=18, max_length=18)
    journal: list[ProductionEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> "ProductionState":
        self._validate_plan()
        self._validate_journal()
        production_canonical_bytes(self)
        return self

    def _validate_plan(self) -> None:
        phase_ids = [row.phase_id for row in self.run_plan]
        if tuple(phase_ids) != PRODUCTION_PHASE_IDS:
            raise ProductionContractError(
                "run_plan must contain all registered phases in canonical order"
            )
        positions = {phase_id: index for index, phase_id in enumerate(phase_ids)}
        omitted = {
            row.phase_id for row in self.run_plan if row.disposition == "omitted"
        }
        for row in self.run_plan:
            if row.owner != PRODUCTION_PHASE_OWNERS[row.phase_id]:
                raise ProductionContractError(
                    f"phase {row.phase_id!r} has the wrong lifecycle owner"
                )
            for dependency in row.depends_on:
                if positions[dependency] >= positions[row.phase_id]:
                    raise ProductionContractError(
                        f"phase {row.phase_id!r} dependency is not earlier"
                    )
                if dependency in omitted:
                    raise ProductionContractError(
                        f"phase {row.phase_id!r} depends on an omitted phase"
                    )
            if row.depends_on != sorted(
                row.depends_on, key=lambda phase_id: positions[phase_id]
            ):
                raise ProductionContractError(
                    f"phase {row.phase_id!r} dependencies must use registry order"
                )

    def _validate_journal(self) -> None:
        plan = {row.phase_id: row for row in self.run_plan}
        attempts: dict[str, PhaseAttempt] = {}
        phase_attempts: dict[str, list[PhaseAttempt]] = {
            phase_id: [] for phase_id in PRODUCTION_PHASE_IDS
        }
        acceptances: dict[str, PhaseAcceptance] = {}
        latest: dict[str, PhaseAcceptance] = {}
        active: dict[str, PhaseAcceptance] = {}

        for event in self.journal:
            if isinstance(event, AttemptEvent):
                attempt = event.attempt
                if plan[attempt.phase_id].disposition == "omitted":
                    raise ProductionContractError(
                        f"omitted phase {attempt.phase_id!r} cannot have attempts"
                    )
                if attempt.attempt_id in attempts:
                    raise ProductionContractError("attempt IDs must be globally unique")
                if (
                    attempt.episode_id != self.episode_id
                    or attempt.run_id != self.run_id
                    or attempt.story_sha256 != self.story_sha256
                ):
                    raise ProductionContractError(
                        "attempt identity does not bind the production root"
                    )
                expected_number = len(phase_attempts[attempt.phase_id]) + 1
                if attempt.attempt_number != expected_number:
                    raise ProductionContractError(
                        f"phase {attempt.phase_id!r} attempt numbers must be contiguous"
                    )
                expected_dependencies = plan[attempt.phase_id].depends_on
                actual_dependencies = [item.phase_id for item in attempt.dependencies]
                if actual_dependencies != expected_dependencies:
                    raise ProductionContractError(
                        f"phase {attempt.phase_id!r} must bind its declared dependencies"
                    )
                for dependency in attempt.dependencies:
                    accepted = active.get(dependency.phase_id)
                    if accepted is None:
                        raise ProductionContractError(
                            f"dependency phase {dependency.phase_id!r} is not accepted"
                        )
                    if (
                        dependency.acceptance_id != accepted.acceptance_id
                        or dependency.accepted_attempt_id
                        != accepted.accepted_attempt_id
                        or dependency.acceptance_sha256
                        != production_sha256(accepted)
                    ):
                        raise ProductionContractError(
                            f"dependency phase {dependency.phase_id!r} is stale"
                        )
                dependency_phases = set(actual_dependencies)
                for artifact_ref in attempt.input_artifacts:
                    if artifact_ref.phase_id not in dependency_phases:
                        raise ProductionContractError(
                            "input artifact is not from a declared dependency"
                        )
                    accepted = active[artifact_ref.phase_id]
                    if (
                        artifact_ref.acceptance_id != accepted.acceptance_id
                        or artifact_ref.accepted_attempt_id
                        != accepted.accepted_attempt_id
                    ):
                        raise ProductionContractError(
                            "input artifact does not bind the active acceptance"
                        )
                    dependency_attempt = attempts[accepted.accepted_attempt_id]
                    artifact = _iter_attempt_artifacts(dependency_attempt).get(
                        artifact_ref.artifact_id
                    )
                    if artifact is None or (
                        artifact.content_sha256 != artifact_ref.content_sha256
                    ):
                        raise ProductionContractError(
                            "input artifact does not resolve by ID and digest"
                        )
                attempts[attempt.attempt_id] = attempt
                phase_attempts[attempt.phase_id].append(attempt)
                continue

            acceptance = event.acceptance
            if acceptance.acceptance_id in acceptances:
                raise ProductionContractError("acceptance IDs must be globally unique")
            if plan[acceptance.phase_id].disposition == "omitted":
                raise ProductionContractError(
                    f"omitted phase {acceptance.phase_id!r} cannot be accepted"
                )
            if acceptance.owner != PRODUCTION_PHASE_OWNERS[acceptance.phase_id]:
                raise ProductionContractError("acceptance has the wrong phase owner")
            if (
                acceptance.episode_id != self.episode_id
                or acceptance.run_id != self.run_id
                or acceptance.story_sha256 != self.story_sha256
            ):
                raise ProductionContractError(
                    "acceptance identity does not bind the production root"
                )
            attempt = attempts.get(acceptance.accepted_attempt_id)
            if attempt is None or attempt.phase_id != acceptance.phase_id:
                raise ProductionContractError(
                    "acceptance must reference an existing same-phase attempt"
                )
            if not _result_succeeded(attempt):
                raise ProductionContractError("failed attempt cannot be accepted")
            if acceptance.accepted_attempt_sha256 != production_sha256(attempt):
                raise ProductionContractError("acceptance attempt digest mismatch")
            for dependency in attempt.dependencies:
                current_dependency = active.get(dependency.phase_id)
                if (
                    current_dependency is None
                    or current_dependency.acceptance_id
                    != dependency.acceptance_id
                ):
                    raise ProductionContractError(
                        "acceptance cannot activate an attempt with stale dependencies"
                    )
            current = latest.get(acceptance.phase_id)
            expected_supersedes = current.acceptance_id if current else None
            if acceptance.supersedes_acceptance_id != expected_supersedes:
                raise ProductionContractError(
                    "acceptance supersession must name the current acceptance"
                )
            if current:
                current_attempt = attempts[current.accepted_attempt_id]
                if attempt.attempt_number <= current_attempt.attempt_number:
                    raise ProductionContractError(
                        "acceptance supersession must select a newer attempt"
                    )
            if current and current.accepted_attempt_id == attempt.attempt_id:
                raise ProductionContractError(
                    "acceptance cannot re-accept the same attempt"
                )
            acceptances[acceptance.acceptance_id] = acceptance
            latest[acceptance.phase_id] = acceptance
            active[acceptance.phase_id] = acceptance
            _invalidate_stale_active_acceptances(active, attempts)


def active_acceptance(
    state: ProductionState, phase_id: PhaseId
) -> PhaseAcceptance | None:
    attempts: dict[str, PhaseAttempt] = {}
    active: dict[str, PhaseAcceptance] = {}
    for event in state.journal:
        if isinstance(event, AttemptEvent):
            attempts[event.attempt.attempt_id] = event.attempt
        else:
            active[event.acceptance.phase_id] = event.acceptance
            _invalidate_stale_active_acceptances(active, attempts)
    return active.get(phase_id)


def _invalidate_stale_active_acceptances(
    active: dict[str, PhaseAcceptance],
    attempts: dict[str, PhaseAttempt],
) -> None:
    """Drop downstream acceptances whose bound dependency was superseded."""

    changed = True
    while changed:
        changed = False
        for phase_id, acceptance in list(active.items()):
            attempt = attempts[acceptance.accepted_attempt_id]
            if any(
                dependency.phase_id not in active
                or active[dependency.phase_id].acceptance_id
                != dependency.acceptance_id
                for dependency in attempt.dependencies
            ):
                del active[phase_id]
                changed = True


def iter_story_refs(value: object):
    """Yield every typed story reference nested in a production value."""

    if isinstance(value, StoryRef):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from iter_story_refs(getattr(value, field_name))
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_story_refs(item)


__all__ = [
    "AcceptanceEvent",
    "ArtifactReceipt",
    "ArtifactRef",
    "AttemptEvent",
    "DependencyRef",
    "PHASE_ATTEMPT_TYPES",
    "PRODUCTION_PHASE_IDS",
    "PRODUCTION_PHASE_OWNERS",
    "PRODUCTION_PHASE_REGISTRY",
    "PRODUCTION_STATE_SCHEMA_VERSION",
    "PhaseAcceptance",
    "PhaseAttempt",
    "PhaseId",
    "ProductionContractError",
    "ProductionEvent",
    "ProductionState",
    "RunPhase",
    "StoryRef",
    "active_acceptance",
    "default_run_plan",
    "iter_story_refs",
    "production_canonical_bytes",
    "production_sha256",
]
