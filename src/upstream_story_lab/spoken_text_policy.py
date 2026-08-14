"""Deterministic spoken-only policy for accepted Story Ledger lines.

The ledger stores words that a speech engine may read verbatim.  Planning
intent belongs in beats/scenes; action, delivery notes, quoted novel prose, and
another character's attributed speech do not belong in ``lines[].text``.

This policy is intentionally narrow and evidence-calibrated.  It catches
high-confidence lexical surfaces rather than pretending a regex can judge all
prose.  A future fuzzy or model-assisted policy requires a new policy and
trusted-validator version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Sequence


SPOKEN_TEXT_POLICY_ID = "otr.spoken-text-only.v1"

SpokenFindingCode = Literal[
    "production_cue",
    "delimited_stage_direction",
    "quoted_novel_dialogue",
    "third_person_stage_business",
    "cross_speaker_attribution",
]


@dataclass(frozen=True, slots=True)
class SpokenTextFinding:
    line_id: str
    code: SpokenFindingCode
    detail: str


_PRODUCTION_CUE_RE = re.compile(
    r"^\s*(?:ACTION|SFX|FX|SOUND(?:\s+EFFECT)?|CUE|MUSIC|AUDIO|"
    r"STAGE\s+DIRECTION)\s*:",
    re.IGNORECASE,
)
_DELIMITED_STAGE_RE = re.compile(
    r"(?:\[[^\]\r\n]+\]|\{[^}\r\n]+\}|\*[^*\r\n]+\*|"
    r"\([^()\r\n]*(?:pause|beat|sigh|laugh|whisper|turn|look|walk|"
    r"gesture|nod|shrug|cough|enter|exit|music|sound)[^()\r\n]*\))",
    re.IGNORECASE,
)

_NARRATION_VERBS = (
    "asks",
    "continues",
    "cloud",
    "clouds",
    "drum",
    "drums",
    "enters",
    "exits",
    "frowns",
    "gazes",
    "glances",
    "laughs",
    "leans",
    "leaves",
    "looks",
    "murmurs",
    "nods",
    "pauses",
    "replies",
    "reaches",
    "says",
    "shrugs",
    "sighs",
    "smiles",
    "stands",
    "stares",
    "steps",
    "turns",
    "walks",
    "whispers",
)
_NARRATION_VERB_PATTERN = "|".join(
    re.escape(value) for value in _NARRATION_VERBS
)
_PRONOUN_NARRATION_RE = re.compile(
    rf"\b(?:he|she|they)\s+(?:{_NARRATION_VERB_PATTERN})\b",
    re.IGNORECASE,
)
_PHYSICAL_NOUN_PATTERN = (
    r"eyes?|face|fingers?|hands?|gaze|voice|steps?|head|shoulders?|"
    r"breath|throat|feet|jaw|brow"
)


def _value(row: Any, name: str, default: Any = "") -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _name_variants(name: str) -> tuple[str, ...]:
    words = [word for word in re.findall(r"[\w'-]+", name) if word]
    variants = {name.strip()}
    if words:
        variants.add(words[-1])
        if words[0].casefold() not in {"dr", "doctor", "mr", "mrs", "ms"}:
            variants.add(words[0])
    return tuple(
        sorted(
            (variant for variant in variants if len(variant) > 1),
            key=lambda item: (-len(item), item.casefold()),
        )
    )


def _quote_marker_count(text: str) -> int:
    """Count dialogue quote marks while ignoring apostrophes in words."""

    count = sum(text.count(mark) for mark in ('"', "“", "”", "‘", "’"))
    for index, char in enumerate(text):
        if char != "'":
            continue
        before = text[index - 1] if index else ""
        after = text[index + 1] if index + 1 < len(text) else ""
        if not (before.isalnum() and after.isalnum()):
            count += 1
    return count


def _name_narration_pattern(variants: Iterable[str]) -> re.Pattern[str] | None:
    escaped = [re.escape(value) for value in variants]
    if not escaped:
        return None
    names = "|".join(escaped)
    return re.compile(
        rf"\b(?:{names})(?:'s|’s)?\s+(?:(?:{_PHYSICAL_NOUN_PATTERN})\s+)?"
        rf"(?:{_NARRATION_VERB_PATTERN})\b",
        re.IGNORECASE,
    )


def audit_spoken_text(
    lines: Sequence[Any],
    cast: Sequence[Any],
) -> tuple[SpokenTextFinding, ...]:
    """Return high-confidence spoken-surface defects without mutating input."""

    names_by_id = {
        str(_value(row, "char_id")): str(_value(row, "name"))
        for row in cast
        if str(_value(row, "char_id")) and str(_value(row, "name"))
    }
    variants_by_id = {
        char_id: _name_variants(name) for char_id, name in names_by_id.items()
    }
    findings: list[SpokenTextFinding] = []

    for row in lines:
        line_id = str(_value(row, "line_id"))
        char_id = str(_value(row, "char_id"))
        role = str(_value(row, "speaker_role"))
        text = str(_value(row, "text"))

        if _PRODUCTION_CUE_RE.search(text):
            findings.append(
                SpokenTextFinding(line_id, "production_cue", "cue label in speech")
            )
        if _DELIMITED_STAGE_RE.search(text):
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "delimited_stage_direction",
                    "bracketed/parenthetical action in speech",
                )
            )

        if role != "character":
            continue
        if _quote_marker_count(text) >= 2:
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "quoted_novel_dialogue",
                    "character field contains quoted dialogue plus prose",
                )
            )

        own_pattern = _name_narration_pattern(variants_by_id.get(char_id, ()))
        if _PRONOUN_NARRATION_RE.search(text) or (
            own_pattern is not None and own_pattern.search(text)
        ):
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "third_person_stage_business",
                    "assigned character is narrated rather than speaking",
                )
            )

        for other_id, variants in variants_by_id.items():
            if other_id == char_id:
                continue
            pattern = _name_narration_pattern(variants)
            if pattern is not None and pattern.search(text):
                findings.append(
                    SpokenTextFinding(
                        line_id,
                        "cross_speaker_attribution",
                        f"text attributes action/speech to {names_by_id[other_id]}",
                    )
                )
                break

    unique: dict[tuple[str, str], SpokenTextFinding] = {}
    for finding in findings:
        unique[(finding.line_id, finding.code)] = finding
    return tuple(unique[key] for key in sorted(unique))


def spoken_text_is_clean(lines: Sequence[Any], cast: Sequence[Any]) -> bool:
    return not audit_spoken_text(lines, cast)


__all__ = [
    "SPOKEN_TEXT_POLICY_ID",
    "SpokenTextFinding",
    "audit_spoken_text",
    "spoken_text_is_clean",
]
