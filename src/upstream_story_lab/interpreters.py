"""Source interpreter bindings: named, allowlisted, declared in banks.json.

Protocol (kibitz r1):

    interpret_source(packet, bank, llm_fns) -> StoryInputPacket

Fixture interpreters are DETERMINISTIC PLUMBING: they validate and assemble
content that lives in the source packet JSON (fixture_* fields). They never
author prose. At transplant, the science bank's production interpreter wraps
news_interpreter.build_news_briefs verbatim and maps NewsBriefs ->
StoryInputPacket; that binding is registered production-side, not here.
"""

from __future__ import annotations

from typing import Any, Callable

from .contracts import SourceBankSpec, SourceMaterialPacket, StoryInputPacket


class InterpreterError(ValueError):
    """Fail-loud interpreter problem (missing content, wrong bank)."""


#: Optional LLM callables a production interpreter may use. Fixture
#: interpreters ignore them (network/model-free by design).
LlmFns = dict[str, Callable[..., Any]]


def _require(packet: SourceMaterialPacket, field: str) -> str:
    value = str(getattr(packet, field, "")).strip()
    if not value:
        raise InterpreterError(
            f"source packet for bank {packet.source_bank_id!r} is missing "
            f"required fixture content field {field!r} - author it in the "
            "packet JSON (JSON owns content; no prose is invented here)."
        )
    return value


def _base_kwargs(packet: SourceMaterialPacket, story_model_id: str) -> dict[str, Any]:
    return {
        "source_bank_id": packet.source_bank_id,
        "story_model_id": story_model_id,
        "source_label": packet.source_label,
        "casting_brief": _require(packet, "fixture_casting_brief"),
        "script_brief": (
            packet.fixture_script_brief.strip()
            or packet.source_summary.strip()
            or _require(packet, "fixture_script_brief")
        ),
        "close_brief": _require(packet, "fixture_close_brief"),
        "key_terms": list(packet.fixture_key_terms),
        "source_fidelity_rules": list(packet.fixture_fidelity_rules),
        "source_material": packet,
    }


def interpret_fixture_scifi_news(packet: SourceMaterialPacket,
                                 bank: SourceBankSpec,
                                 llm_fns: LlmFns | None = None,
                                 *, story_model_id: str) -> StoryInputPacket:
    """Science-article lane. Serves every sci-fi news bank (scifi_news and the
    quality lane scifi_news_pro): the packet is checked against the bank it was
    resolved for, not against one hardcoded id."""

    if packet.source_bank_id != bank.source_bank_id:
        raise InterpreterError(
            f"sci-fi news interpreter for bank {bank.source_bank_id!r} got a "
            f"packet declaring {packet.source_bank_id!r}"
        )
    kwargs = _base_kwargs(packet, story_model_id)
    if not kwargs["key_terms"]:
        raise InterpreterError(
            "science fixture packet must carry fixture_key_terms (>=1); the "
            "production lane guarantees key_terms via NewsBriefs"
        )
    kwargs["adaptation_trace"] = {"fixture": True, "story_model_id": story_model_id}
    return StoryInputPacket(**kwargs)


def interpret_fixture_media_archive(packet: SourceMaterialPacket,
                                    bank: SourceBankSpec,
                                    llm_fns: LlmFns | None = None,
                                    *, story_model_id: str) -> StoryInputPacket:
    if packet.source_bank_id != "media_archive":
        raise InterpreterError(
            f"media_archive interpreter got bank {packet.source_bank_id!r}"
        )
    kwargs = _base_kwargs(packet, story_model_id)
    kwargs["adaptation_trace"] = {"fixture": True, "story_model_id": story_model_id}
    return StoryInputPacket(**kwargs)


def interpret_fixture_public_domain(packet: SourceMaterialPacket,
                                    bank: SourceBankSpec,
                                    llm_fns: LlmFns | None = None,
                                    *, story_model_id: str) -> StoryInputPacket:
    if packet.source_bank_id != "public_domain":
        raise InterpreterError(
            f"public_domain interpreter got bank {packet.source_bank_id!r}"
        )
    if packet.rights_status != "public_domain":
        raise InterpreterError(
            f"public_domain packet has rights_status {packet.rights_status!r}; "
            "only 'public_domain' is allowed in this lane"
        )
    kwargs = _base_kwargs(packet, story_model_id)
    if not (packet.raw_text.strip() or packet.source_text_ref.strip()):
        raise InterpreterError(
            "public_domain packet must carry raw_text or source_text_ref"
        )
    kwargs["script_brief"] = packet.raw_text.strip() or kwargs["script_brief"]
    kwargs["adaptation_trace"] = {
        "fixture": True,
        "story_model_id": story_model_id,
        "source_kind": packet.source_kind,
    }
    return StoryInputPacket(**kwargs)


def interpret_fixture_shakespeare(packet: SourceMaterialPacket,
                                  bank: SourceBankSpec,
                                  llm_fns: LlmFns | None = None,
                                  *, story_model_id: str) -> StoryInputPacket:
    """Curated-scene adaptation lane. The Folger scenes are vendored under
    fixtures/source_banks/shakespeare/ with provenance digests and a
    non-commercial license label, so the packet must point at a scene rather
    than carry an invented one."""

    if packet.source_bank_id != "shakespeare":
        raise InterpreterError(
            f"shakespeare interpreter got bank {packet.source_bank_id!r}"
        )
    if packet.rights_status not in ("public_domain", "licensed"):
        raise InterpreterError(
            f"shakespeare packet has rights_status {packet.rights_status!r}; "
            "a curated scene is either 'public_domain' or 'licensed' (the "
            "Folger editions carry a non-commercial license)"
        )
    kwargs = _base_kwargs(packet, story_model_id)
    if not (packet.raw_text.strip() or packet.source_text_ref.strip()):
        raise InterpreterError(
            "shakespeare packet must carry raw_text or source_text_ref naming "
            "the curated scene this lane adapts"
        )
    kwargs["script_brief"] = packet.raw_text.strip() or kwargs["script_brief"]
    kwargs["adaptation_trace"] = {
        "fixture": True,
        "story_model_id": story_model_id,
        "source_kind": packet.source_kind,
    }
    return StoryInputPacket(**kwargs)


def interpret_fixture_original(packet: SourceMaterialPacket,
                               bank: SourceBankSpec,
                               llm_fns: LlmFns | None = None,
                               *, story_model_id: str) -> StoryInputPacket:
    """No-source lane. Nothing is being adapted, so a packet that points at
    external source material is a lane error rather than extra grounding: the
    premise in source_summary IS the material."""

    if packet.source_bank_id != "original":
        raise InterpreterError(
            f"original interpreter got bank {packet.source_bank_id!r}"
        )
    if packet.source_text_ref.strip() or packet.source_url.strip():
        raise InterpreterError(
            "original packet references external source material "
            f"(source_text_ref={packet.source_text_ref!r}, "
            f"source_url={packet.source_url!r}); this lane invents its premise "
            "and declares it in source_summary"
        )
    if not packet.source_summary.strip():
        raise InterpreterError(
            "original packet must carry source_summary - the concept premise "
            "stands in for source text in this lane"
        )
    kwargs = _base_kwargs(packet, story_model_id)
    kwargs["adaptation_trace"] = {
        "fixture": True,
        "story_model_id": story_model_id,
        "adapts_a_source": False,
    }
    return StoryInputPacket(**kwargs)


#: The explicit binding allowlist. banks.json names one of these; an unknown
#: binding is a hard error naming the bank (no hidden engines).
INTERPRETER_BINDINGS: dict[str, Callable[..., StoryInputPacket]] = {
    "fixture_scifi_news": interpret_fixture_scifi_news,
    "fixture_media_archive": interpret_fixture_media_archive,
    "fixture_public_domain": interpret_fixture_public_domain,
    "fixture_shakespeare": interpret_fixture_shakespeare,
    "fixture_original": interpret_fixture_original,
}


def resolve_interpreter(bank: SourceBankSpec) -> Callable[..., StoryInputPacket]:
    binding = (bank.interpreter or "").strip()
    try:
        return INTERPRETER_BINDINGS[binding]
    except KeyError as exc:
        raise InterpreterError(
            f"bank {bank.source_bank_id!r} declares unknown interpreter binding "
            f"{binding!r}; allowlist: {sorted(INTERPRETER_BINDINGS)}"
        ) from exc
