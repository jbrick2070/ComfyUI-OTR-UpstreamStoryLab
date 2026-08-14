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
#: Selected only when a caller supplies a source document; see
#: ``audit_spoken_text``.  Same detectors, plus a literal-carriage exemption
#: for the heuristic findings on adaptation lanes.
SPOKEN_TEXT_POLICY_V2_ID = "otr.spoken-text-only.v2"

SpokenFindingCode = Literal[
    "production_cue",
    "delimited_stage_direction",
    "quoted_novel_dialogue",
    "third_person_stage_business",
    "cross_speaker_attribution",
]


#: Findings that infer authorship from prose shape.  Only these may be
#: excused by literal carriage from a source; a production cue or a delimited
#: direction is never speakable, whoever wrote it.
HEURISTIC_FINDING_CODES: frozenset[str] = frozenset(
    {
        "quoted_novel_dialogue",
        "third_person_stage_business",
        "cross_speaker_attribution",
    }
)


def _carried_predicate(carried_source: Any | None):
    """Adapt a source document into a ``text -> bool`` carriage test."""

    if carried_source is None:
        return None
    contains = getattr(carried_source, "contains", None)
    if callable(contains):
        return lambda text: bool(text.strip()) and bool(contains(text))
    if callable(carried_source):
        return lambda text: bool(text.strip()) and bool(carried_source(text))
    raise TypeError(
        "carried_source must expose contains(text) or be callable"
    )


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

_PHYSICAL_ACTION_VERBS = (
    "adjusts",
    "cloud",
    "clouds",
    "contemplates",
    "dances",
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
    "moves",
    "nods",
    "pauses",
    "paces",
    "reaches",
    "shrugs",
    "sighs",
    "sits",
    "smiles",
    "stands",
    "stares",
    "steps",
    "stops",
    "taps",
    "tightens",
    "turns",
    "walks",
    "watches",
)
_ATTRIBUTION_VERBS = (
    "asks",
    "asked",
    "continues",
    "continued",
    "murmurs",
    "murmured",
    "replies",
    "replied",
    "says",
    "said",
    "shouts",
    "shouted",
    "whispers",
    "whispered",
)
_NAME_ACTION_VERBS = tuple(
    dict.fromkeys((*_PHYSICAL_ACTION_VERBS, *_ATTRIBUTION_VERBS))
)
_PHYSICAL_ACTION_VERB_PATTERN = "|".join(
    re.escape(value) for value in _PHYSICAL_ACTION_VERBS
)
_NAME_ACTION_VERB_PATTERN = "|".join(
    re.escape(value) for value in _NAME_ACTION_VERBS
)
_PRONOUN_NARRATION_RE = re.compile(
    rf"\b(?:he|she|they)\s+(?:{_PHYSICAL_ACTION_VERB_PATTERN})\b",
    re.IGNORECASE,
)
_PRONOUN_ATTRIBUTION_RE = re.compile(
    r"\b(?:he|she|they)\s+"
    r"(?:asks|asked|continues|continued|murmurs|murmured|replies|replied|"
    r"says|said|shouts|shouted|whispers|whispered)\b",
    re.IGNORECASE,
)
_PHYSICAL_NOUN_PATTERN = (
    r"eyes?|face|fingers?|hands?|gaze|voice|steps?|head|shoulders?|"
    r"breath|throat|feet|jaw|brow"
)
_SCENE_NARRATION_RE = re.compile(
    r"\b(?:the\s+board(?:['’]s\s+chair)?|the\s+room|"
    r"(?:his|her|their)\s+(?:voice|words|gaze|eyes?|steps?))\s+"
    r"(?:clears|echoes|exchanges|exhales|falls|holds|presses|returns|"
    r"trails|trembles)\b",
    re.IGNORECASE,
)
_THIRD_PERSON_REFERENCE_RE = re.compile(
    r"\b(?:he|she|they|her|his|their|hers|him|them)\b",
    re.IGNORECASE,
)

_BARE_STAGE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"(?:pause|beat|silence|laughs?|sighs?|gasps?|coughs?|sobs?|groans?)"
    r"|(?:he|she|they|[A-Z][a-z]+)\s+"
    r"(?:laughs?|sighs?|gasps?|coughs?|sobs?|groans?)"
    r"|(?:the\s+)?(?:door|window|telephone|phone|bell|alarm|buzzer|clock|"
    r"radio|static|music|footsteps?)\s+"
    r"(?:slams?|creaks?|rings?|opens?|closes?|knocks?|buzzes?|chimes?|"
    r"ticks?|rumbles?|crashes?|swells?|fades?|plays?|starts?|stops?|"
    r"crackles?|approach(?:es)?|recedes?)"
    r"|(?:thunder|wind|rain)\s+"
    r"(?:rolls?|rumbles?|howls?|rises?|falls?|pounds?)"
    r"|(?:a|the)\s+(?:knock|bang|crash|ring)\s+"
    r"(?:at|on|from|inside|outside)\s+(?:the\s+)?"
    r"(?:door|window|wall|hall|room|radio)"
    r"|(?:the\s+)?sound\s+of\s+"
    r"(?:thunder|rain|wind|static|footsteps?|a\s+door|a\s+bell)"
    r")\s*[.!?]*\s*$",
    re.IGNORECASE,
)

_DIALOGUE_OPENER_ALLOW = (
    "looks like",
    "sounds like",
    "seems like",
    "seems ",
    "seem ",
    "feels like",
    "smells like",
    "looks ",
)
_FIRST_SECOND_PERSON_ROOTS = frozenset(
    {"i", "we", "you", "me", "us", "my", "your", "our"}
)
_THIRD_PERSON_SUBJECTS = frozenset({"he", "she", "they"})
_THIRD_PERSON_PHYSICAL_ACTION_VERBS = frozenset(
    {
        "open",
        "opens",
        "opening",
        "close",
        "closes",
        "closing",
        "cross",
        "crosses",
        "crossing",
        "switch",
        "switches",
        "switching",
        "flip",
        "flips",
        "flipping",
        "enter",
        "enters",
        "entering",
        "exit",
        "exits",
        "exiting",
        "turn",
        "walk",
        "step",
        "move",
        "reach",
        "stand",
        "sit",
    }
)
_COPULA_MODAL = frozenset(
    {
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "am",
        "can",
        "could",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "must",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
    }
)
_DIALOGUE_STARTER = frozenset(
    {
        "yes",
        "no",
        "well",
        "oh",
        "maybe",
        "please",
        "now",
        "listen",
        "look",
        "hey",
        "okay",
        "fine",
        "sure",
    }
)
_HONORIFICS = frozenset(
    {
        "dr",
        "doctor",
        "mr",
        "mrs",
        "ms",
        "prof",
        "professor",
        "capt",
        "captain",
    }
)


@dataclass(frozen=True, slots=True)
class _QuoteSpan:
    start: int
    end: int


def _value(row: Any, name: str, default: Any = "") -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _candidate_name_variants(name: str) -> tuple[str, ...]:
    compact = " ".join(name.split())
    if not compact:
        return ()
    words = re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", compact, re.UNICODE)
    variants = {compact}
    if len(words) > 1 and words[0].casefold() in _HONORIFICS:
        variants.add(" ".join(words[1:]))
    return tuple(sorted(variants, key=lambda item: (-len(item), item.casefold())))


def _unique_name_variants(names_by_id: dict[str, str]) -> dict[str, tuple[str, ...]]:
    candidates = {
        char_id: _candidate_name_variants(name)
        for char_id, name in names_by_id.items()
    }
    owners: dict[str, set[str]] = {}
    for char_id, variants in candidates.items():
        for variant in variants:
            owners.setdefault(variant.casefold(), set()).add(char_id)
    return {
        char_id: tuple(
            variant
            for variant in variants
            if owners[variant.casefold()] == {char_id}
        )
        for char_id, variants in candidates.items()
    }


def _is_word_apostrophe(text: str, index: int) -> bool:
    before = text[index - 1] if index else ""
    after = text[index + 1] if index + 1 < len(text) else ""
    return before.isalnum() and after.isalnum()


def _dialogue_quote_spans(text: str) -> tuple[_QuoteSpan, ...]:
    """Pair dialogue wrappers while treating straight/curly apostrophes as words."""

    spans: list[_QuoteSpan] = []
    active_kind: Literal["single", "double"] | None = None
    active_start = -1
    for index, char in enumerate(text):
        if char in {"'", "’"} and _is_word_apostrophe(text, index):
            continue

        if active_kind == "single":
            if char in {"'", "’"}:
                spans.append(_QuoteSpan(active_start, index))
                active_kind = None
            continue
        if active_kind == "double":
            if char in {'"', "”"}:
                spans.append(_QuoteSpan(active_start, index))
                active_kind = None
            continue

        if char in {"‘"} or (
            char == "'"
            and index + 1 < len(text)
            and text[index + 1].isalnum()
        ):
            active_kind = "single"
            active_start = index
        elif char in {'"', "“"}:
            active_kind = "double"
            active_start = index
    return tuple(spans)


def _outside_quote_spans(
    text: str,
    quote_spans: Sequence[_QuoteSpan],
) -> tuple[tuple[str, bool], ...]:
    """Return outside-dialogue text and whether each span touches a line edge."""

    if not quote_spans:
        return ((text, True),)
    outside: list[tuple[str, bool]] = []
    cursor = 0
    last_index = len(quote_spans) - 1
    for index, span in enumerate(quote_spans):
        outside.append((text[cursor : span.start], index == 0))
        cursor = span.end + 1
        if index == last_index:
            outside.append((text[cursor:], True))
    return tuple(outside)


def _escape_name(value: str) -> str:
    return r"\s+".join(re.escape(part) for part in value.split())


def _name_narration_pattern(
    variants: Iterable[str],
    *,
    verb_pattern: str = _NAME_ACTION_VERB_PATTERN,
) -> re.Pattern[str] | None:
    escaped = [_escape_name(value) for value in variants]
    if not escaped:
        return None
    names = "|".join(escaped)
    return re.compile(
        rf"(?<![\w'])"
        rf"(?:{names})"
        rf"(?=\s|['’])"
        rf"(?:\s+(?:{verb_pattern})\b|"
        rf"(?:['’]s)\s+(?:{_PHYSICAL_NOUN_PATTERN})\s+"
        rf"(?:{verb_pattern})\b)",
        re.IGNORECASE,
    )


def _matches(pattern: re.Pattern[str] | None, text: str) -> bool:
    return pattern is not None and pattern.search(text) is not None


def _has_stage_signal(
    text: str,
    name_patterns: Iterable[re.Pattern[str]],
    *,
    include_pronoun_attribution: bool = False,
) -> bool:
    if not text.strip():
        return False
    return bool(
        _PRONOUN_NARRATION_RE.search(text)
        or (
            include_pronoun_attribution
            and _PRONOUN_ATTRIBUTION_RE.search(text)
        )
        or _SCENE_NARRATION_RE.search(text)
        or any(pattern.search(text) for pattern in name_patterns)
    )


def _has_third_person_density(text: str) -> bool:
    return len(_THIRD_PERSON_REFERENCE_RE.findall(text)) >= 2


def _is_whole_line_stage_action(text: str, *, max_words: int = 32) -> bool:
    """Recover the bounded action-chain detector without mutating dialogue."""

    value = " ".join(text.split())
    if not value or _dialogue_quote_spans(value):
        return False
    lower = value.casefold()
    if any(lower.startswith(opener) for opener in _DIALOGUE_OPENER_ALLOW):
        return False
    words = re.findall(r"[a-z]+(?:['’][a-z]+)?", lower)
    if not words or len(words) > max_words:
        return False
    for word in words:
        root = re.split(r"['’]", word)[0]
        if word in _FIRST_SECOND_PERSON_ROOTS or root in _FIRST_SECOND_PERSON_ROOTS:
            return False

    lead = words[0]
    if lead in _DIALOGUE_STARTER:
        return False
    third_person_subject = False
    verb = lead
    if lead in _THIRD_PERSON_SUBJECTS and len(words) > 1:
        third_person_subject = True
        verb = words[1]
    if verb in _COPULA_MODAL or verb in _DIALOGUE_STARTER:
        return False

    whitelisted = verb in _PHYSICAL_ACTION_VERBS
    subject_action = (
        third_person_subject and verb in _THIRD_PERSON_PHYSICAL_ACTION_VERBS
    )
    verbish = bool(verb) and "'" not in verb and "’" not in verb and (
        verb.endswith("ing")
        or verb.endswith("ed")
        or (verb.endswith("s") and len(verb) > 2)
    )
    if not (whitelisted or subject_action or verbish):
        return False
    if not whitelisted and not subject_action and "," not in value:
        return False
    return True


def audit_spoken_text(
    lines: Sequence[Any],
    cast: Sequence[Any],
    *,
    carried_source: Any | None = None,
) -> tuple[SpokenTextFinding, ...]:
    """Return high-confidence spoken-surface defects without mutating input.

    With no ``carried_source`` this is exactly ``otr.spoken-text-only.v1``.

    Supplying a source document selects ``otr.spoken-text-only.v2``, which
    exempts the three *heuristic* findings for a line whose words are literally
    carried from that source.  Those heuristics exist to catch a model writing
    narrative prose instead of dialogue; when the words provably come from the
    author, that premise is false.  Measured need: `Sir, there she stands.` and
    `with washed eyes Cordelia leaves you.` are genuine spoken Shakespeare that
    v1 rejects.

    The exemption is deliberately narrow.  It requires literal carriage, so a
    paraphrase stays subject to the heuristics.  Production cues, delimited
    stage directions, and a row that is *entirely* a stage cue are never
    exempt: the source printing a direction does not make it speakable.
    """

    carried = _carried_predicate(carried_source)

    names_by_id = {
        str(_value(row, "char_id")): str(_value(row, "name"))
        for row in cast
        if str(_value(row, "char_id")) and str(_value(row, "name"))
    }
    variants_by_id = _unique_name_variants(names_by_id)
    patterns_by_id = {
        char_id: _name_narration_pattern(variants)
        for char_id, variants in variants_by_id.items()
    }
    physical_patterns_by_id = {
        char_id: _name_narration_pattern(
            variants,
            verb_pattern=_PHYSICAL_ACTION_VERB_PATTERN,
        )
        for char_id, variants in variants_by_id.items()
    }
    all_name_patterns = tuple(
        pattern for pattern in patterns_by_id.values() if pattern is not None
    )
    findings: list[SpokenTextFinding] = []
    #: Findings no source may excuse, keyed by (line_id, code).
    never_exempt: set[tuple[str, str]] = set()
    text_by_line: dict[str, str] = {}

    for row in lines:
        line_id = str(_value(row, "line_id"))
        char_id = str(_value(row, "char_id"))
        role = str(_value(row, "speaker_role"))
        text = str(_value(row, "text"))
        text_by_line[line_id] = text

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
        if _BARE_STAGE_LINE_RE.fullmatch(text):
            # A row that is nothing but a stage cue stays forbidden even when
            # the source prints it: a direction is never speakable.
            never_exempt.add((line_id, "third_person_stage_business"))
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "third_person_stage_business",
                    "whole speech row is a production action or sound cue",
                )
            )

        if role != "character":
            continue

        quote_spans = _dialogue_quote_spans(text)
        outside_spans = _outside_quote_spans(text, quote_spans)
        edge_spans = [value for value, is_edge in outside_spans if is_edge]
        interior_spans = [value for value, is_edge in outside_spans if not is_edge]

        if quote_spans and any(
            _has_stage_signal(
                value,
                all_name_patterns,
                include_pronoun_attribution=True,
            )
            for value in edge_spans
        ):
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "quoted_novel_dialogue",
                    "quoted speech has narrator prose at a line edge",
                )
            )

        own_pattern = patterns_by_id.get(char_id)
        cross_speaker_id: str | None = None
        for other_id, pattern in patterns_by_id.items():
            if other_id == char_id or pattern is None:
                continue
            if quote_spans:
                cross_match = any(
                    pattern.search(value) for value, _is_edge in outside_spans
                )
            else:
                physical_pattern = physical_patterns_by_id.get(other_id)
                cross_match = bool(
                    physical_pattern is not None
                    and physical_pattern.search(text)
                    and _has_third_person_density(text)
                )
            if cross_match:
                cross_speaker_id = other_id
                break

        whole_line_action = _is_whole_line_stage_action(text)
        if whole_line_action:
            # A row that is nothing but stage action is never speakable, and
            # carriage cannot excuse it.  Sources print directions - "[He
            # exits.]" - so a bracket-stripped direction is quotable from the
            # source and would otherwise ride the exemption straight into the
            # sealed ledger.
            never_exempt.add((line_id, "third_person_stage_business"))
        if not quote_spans:
            narrated = bool(
                whole_line_action
                or _PRONOUN_NARRATION_RE.search(text)
                or _SCENE_NARRATION_RE.search(text)
                or _matches(own_pattern, text)
                or (
                    cross_speaker_id is not None
                    and _has_third_person_density(text)
                )
            )
        else:
            narrated = whole_line_action or any(
                _has_stage_signal(
                    value,
                    (own_pattern,) if own_pattern is not None else (),
                    include_pronoun_attribution=True,
                )
                for value in interior_spans
            )
        if narrated:
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "third_person_stage_business",
                    "assigned character is narrated rather than speaking",
                )
            )

        if cross_speaker_id is not None:
            findings.append(
                SpokenTextFinding(
                    line_id,
                    "cross_speaker_attribution",
                    "text attributes action/speech to "
                    f"{names_by_id[cross_speaker_id]}",
                )
            )

    unique: dict[tuple[str, str], SpokenTextFinding] = {}
    for finding in findings:
        unique[(finding.line_id, finding.code)] = finding

    if carried is not None:
        for key in list(unique):
            line_id, code = key
            if (
                code in HEURISTIC_FINDING_CODES
                and key not in never_exempt
                and carried(text_by_line.get(line_id, ""))
            ):
                del unique[key]
    return tuple(unique[key] for key in sorted(unique))


def spoken_text_is_clean(
    lines: Sequence[Any],
    cast: Sequence[Any],
    *,
    carried_source: Any | None = None,
) -> bool:
    return not audit_spoken_text(lines, cast, carried_source=carried_source)


__all__ = [
    "HEURISTIC_FINDING_CODES",
    "SPOKEN_TEXT_POLICY_ID",
    "SPOKEN_TEXT_POLICY_V2_ID",
    "SpokenTextFinding",
    "audit_spoken_text",
    "spoken_text_is_clean",
]
