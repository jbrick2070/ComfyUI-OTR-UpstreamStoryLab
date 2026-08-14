"""Pure renderers for the checked-in Ledger Constitution artifacts.

The executable Pydantic models are the authority.  This module performs no
filesystem I/O and deliberately emits no timestamps, host paths, or other
ambient state, so identical models always produce byte-identical artifacts.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .ledger_contract import LedgerEnvelope
from .production_contract import PRODUCTION_PHASE_OWNERS


ENVELOPE_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
ENVELOPE_SCHEMA_ID = "urn:otr:schema:ledger-envelope:v2"
ENVELOPE_SCHEMA_COMMENT = (
    "Generated from upstream_story_lab.ledger_contract.LedgerEnvelope; "
    "do not edit by hand."
)
FIELD_LAWS_SCHEMA_VERSION = "otr.ledger_field_laws.v2"


def _pretty_json(value: object) -> str:
    """Return the repository's deterministic UTF-8 JSON text form."""

    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def envelope_schema_document() -> dict[str, Any]:
    """Build the complete Draft 2020-12 schema for ``LedgerEnvelope``."""

    schema = LedgerEnvelope.model_json_schema(
        mode="validation",
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = ENVELOPE_SCHEMA_DIALECT
    schema["$id"] = ENVELOPE_SCHEMA_ID
    schema["$comment"] = ENVELOPE_SCHEMA_COMMENT
    return schema


def render_envelope_schema() -> str:
    """Render the full envelope JSON Schema as stable pretty JSON."""

    return _pretty_json(envelope_schema_document())


def _ref_name(ref: str) -> str:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        raise ValueError(f"unsupported JSON Schema reference: {ref!r}")
    return ref[len(prefix) :]


def _resolve_ref(
    schema: Mapping[str, Any], definitions: Mapping[str, Any]
) -> Mapping[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    name = _ref_name(ref)
    resolved = definitions.get(name)
    if not isinstance(resolved, Mapping):
        raise ValueError(f"unresolved JSON Schema reference: {ref!r}")
    return resolved


def _schema_type(
    schema: Mapping[str, Any], definitions: Mapping[str, Any]
) -> str:
    """Return a compact, deterministic human type for one schema property."""

    ref = schema.get("$ref")
    if isinstance(ref, str):
        resolved = _resolve_ref(schema, definitions)
        resolved_type = str(resolved.get("type", "value"))
        return f"{resolved_type}<{_ref_name(ref)}>"

    const = schema.get("const")
    if "const" in schema:
        return f"literal[{json.dumps(const, ensure_ascii=False)}]"

    enum = schema.get("enum")
    if isinstance(enum, list):
        values = ",".join(
            json.dumps(value, ensure_ascii=False, sort_keys=True)
            for value in enum
        )
        return f"enum[{values}]"

    alternatives = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(alternatives, list):
        names: list[str] = []
        mapping = schema.get("discriminator", {}).get("mapping", {})
        if isinstance(mapping, Mapping) and mapping:
            names.extend(str(key) for key in sorted(mapping))
        else:
            for alternative in alternatives:
                if not isinstance(alternative, Mapping):
                    continue
                candidate = _schema_type(alternative, definitions)
                if candidate not in names:
                    names.append(candidate)
        return " | ".join(names) if names else "union"

    schema_type = schema.get("type", "value")
    if schema_type == "array":
        items = schema.get("items")
        item_type = (
            _schema_type(items, definitions)
            if isinstance(items, Mapping)
            else "value"
        )
        return f"array[{item_type}]"
    return str(schema_type)


def _default_law(schema: Mapping[str, Any], *, required: bool) -> str:
    if "default" in schema:
        rendered = json.dumps(
            schema["default"], ensure_ascii=False, sort_keys=True
        )
        return f"literal {rendered}"
    if required:
        return "required; no default"
    if schema.get("type") == "array":
        return "factory []"
    return "model default"


def _lifecycle_law(
    path: str, phase_id: str | None
) -> dict[str, str]:
    if phase_id is not None:
        return {
            "owner": PRODUCTION_PHASE_OWNERS[phase_id],
            "mutation": phase_id,
            "durability": "append-only run journal",
            "failure": (
                f"reject invalid {phase_id} append; preserve prior journal"
            ),
        }

    if path.startswith(
        "ledger_envelope.production_state.journal[]<acceptance>"
    ):
        return {
            "owner": "acceptance_validator",
            "mutation": "phase_acceptance",
            "durability": "append-only run journal",
            "failure": (
                "reject invalid acceptance append; preserve active acceptance"
            ),
        }

    if path == "ledger_envelope.production_state.journal" or path.startswith(
        "ledger_envelope.production_state.journal[]"
    ):
        return {
            "owner": "production_journal",
            "mutation": "production_extension",
            "durability": "append-only run journal",
            "failure": "reject invalid append; preserve prior journal",
        }

    if path.startswith("ledger_envelope.production_state"):
        return {
            "owner": "production_journal",
            "mutation": "production_initialization",
            "durability": "immutable run root; journal append-only",
            "failure": "reject production-state initialization",
        }
    if path.startswith("ledger_envelope.story_seal"):
        return {
            "owner": "story_seal_builder",
            "mutation": "story_acceptance",
            "durability": "write once; immutable during production",
            "failure": "reject seal minting; preserve unaccepted draft",
        }
    if path.startswith("ledger_envelope.story_ledger.validation"):
        return {
            "owner": "trusted_story_validators",
            "mutation": "story_acceptance",
            "durability": "sealed with story_ledger",
            "failure": "reject story atomically; retain draft for owning job",
        }
    if path.startswith("ledger_envelope.story_ledger.body.source_packet"):
        return {
            "owner": "source_capture",
            "mutation": "pre_acceptance_capture",
            "durability": "sealed with story_ledger",
            "failure": "reject missing, stale, or unverified captured evidence",
        }
    if path.startswith("ledger_envelope.story_ledger"):
        return {
            "owner": "central_story_compiler",
            "mutation": "pre_acceptance_authoring",
            "durability": "sealed story; immutable during production",
            "failure": "reject story atomically; return to owning authoring job",
        }
    if path.startswith("ledger_envelope.final_seal"):
        return {
            "owner": "terminal_audit",
            "mutation": "terminal_finalization",
            "durability": "null-only until final-seal contract lands",
            "failure": "reject non-null final seal",
        }
    return {
        "owner": "ledger_envelope_compiler",
        "mutation": "envelope_creation",
        "durability": "schema identity is immutable",
        "failure": "reject invalid envelope",
    }


def _branch_labels(schema: Mapping[str, Any]) -> dict[str, str]:
    """Map a union branch's local ``$ref`` to its discriminator value."""

    discriminator = schema.get("discriminator")
    if not isinstance(discriminator, Mapping):
        return {}
    mapping = discriminator.get("mapping")
    if not isinstance(mapping, Mapping):
        return {}
    return {
        str(ref): str(label)
        for label, ref in mapping.items()
        if isinstance(ref, str)
    }


def _walk_schema_fields(
    schema: Mapping[str, Any],
    *,
    definitions: Mapping[str, Any],
    path: str,
    phase_id: str | None,
    rows: list[dict[str, str]],
) -> None:
    """Walk reachable object fields, preserving discriminated branch paths."""

    ref = schema.get("$ref")
    if isinstance(ref, str):
        _walk_schema_fields(
            _resolve_ref(schema, definitions),
            definitions=definitions,
            path=path,
            phase_id=phase_id,
            rows=rows,
        )
        return

    alternatives = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(alternatives, list):
        labels = _branch_labels(schema)
        non_null = [
            branch
            for branch in alternatives
            if isinstance(branch, Mapping) and branch.get("type") != "null"
        ]
        for index, branch in enumerate(non_null):
            branch_ref = branch.get("$ref")
            label = labels.get(str(branch_ref)) if branch_ref else None
            branch_path = path
            branch_phase = phase_id
            if label is not None:
                branch_path = f"{path}<{label}>"
                discriminator = schema.get("discriminator", {})
                if (
                    isinstance(discriminator, Mapping)
                    and discriminator.get("propertyName") == "phase_id"
                    and label in PRODUCTION_PHASE_OWNERS
                ):
                    branch_phase = label
            elif len(non_null) > 1:
                branch_path = f"{path}<option-{index + 1}>"
            _walk_schema_fields(
                branch,
                definitions=definitions,
                path=branch_path,
                phase_id=branch_phase,
                rows=rows,
            )
        return

    if schema.get("type") == "array":
        items = schema.get("items")
        if isinstance(items, Mapping):
            _walk_schema_fields(
                items,
                definitions=definitions,
                path=f"{path}[]",
                phase_id=phase_id,
                rows=rows,
            )
        return

    resolved = _resolve_ref(schema, definitions)
    properties = resolved.get("properties")
    if not isinstance(properties, Mapping):
        return
    required_fields = set(resolved.get("required", []))
    for field_name in sorted(properties):
        field_schema = properties[field_name]
        if not isinstance(field_schema, Mapping):
            continue
        field_path = f"{path}.{field_name}"
        row = {
            "path": field_path,
            "type": _schema_type(field_schema, definitions),
            "default": _default_law(
                field_schema, required=field_name in required_fields
            ),
        }
        row.update(_lifecycle_law(field_path, phase_id))
        rows.append(row)
        _walk_schema_fields(
            field_schema,
            definitions=definitions,
            path=field_path,
            phase_id=phase_id,
            rows=rows,
        )


def lifecycle_catalog_document() -> dict[str, Any]:
    """Build lifecycle laws for every reachable envelope field path."""

    envelope_schema = envelope_schema_document()
    definitions = envelope_schema.get("$defs", {})
    if not isinstance(definitions, Mapping):
        raise ValueError("LedgerEnvelope JSON Schema has no $defs object")
    root_row = {
        "path": "ledger_envelope",
        "type": "object<LedgerEnvelope>",
        "default": "required; no default",
    }
    root_row.update(_lifecycle_law("ledger_envelope", None))
    rows: list[dict[str, str]] = [root_row]
    _walk_schema_fields(
        envelope_schema,
        definitions=definitions,
        path="ledger_envelope",
        phase_id=None,
        rows=rows,
    )
    rows.sort(key=lambda row: row["path"])
    paths = [row["path"] for row in rows]
    if len(paths) != len(set(paths)):
        duplicates = sorted(
            {path for path in paths if paths.count(path) > 1}
        )
        raise ValueError(f"duplicate lifecycle paths: {duplicates}")

    return {
        "schema_version": FIELD_LAWS_SCHEMA_VERSION,
        "source_schema_id": ENVELOPE_SCHEMA_ID,
        "scope": "ledger_envelope",
        "field_count": len(rows),
        "fields": rows,
    }


def render_lifecycle_catalog() -> str:
    """Render production lifecycle laws as stable pretty JSON."""

    return _pretty_json(lifecycle_catalog_document())


def _markdown_code(value: str) -> str:
    escaped = value.replace("|", r"\|")
    return "`" + escaped + "`"


def _markdown_text(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


def render_lifecycle_markdown() -> str:
    """Render the human reference from the exact machine catalog rows."""

    catalog = lifecycle_catalog_document()
    lines = [
        "# Ledger Field Reference",
        "",
        (
            "Generated from the executable `LedgerEnvelope` and "
            "story, seal, and `ProductionState` models. Do not edit this "
            "file by hand."
        ),
        "",
        f"Schema: `{catalog['source_schema_id']}`",
        f"Lifecycle catalog: `{catalog['schema_version']}`",
        f"Covered field paths: **{catalog['field_count']}**",
        "",
        (
            "Each discriminated attempt branch is expanded separately so its "
            "fields name the registered phase owner rather than a generic "
            "producer."
        ),
        "",
        (
            "| Path | Type | Default law | Lifecycle owner | Mutation phase | "
            "Durability | Failure policy |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for row in catalog["fields"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_code(row["path"]),
                    _markdown_code(row["type"]),
                    _markdown_text(row["default"]),
                    _markdown_code(row["owner"]),
                    _markdown_code(row["mutation"]),
                    _markdown_text(row["durability"]),
                    _markdown_text(row["failure"]),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_contract_artifacts() -> dict[str, str]:
    """Return every checked-in generated artifact keyed by POSIX repo path."""

    return {
        "contracts/ledger_envelope_v2.schema.json": render_envelope_schema(),
        "contracts/ledger_field_laws_v2.json": render_lifecycle_catalog(),
        "docs/LEDGER_FIELD_REFERENCE.md": render_lifecycle_markdown(),
    }


__all__ = [
    "ENVELOPE_SCHEMA_COMMENT",
    "ENVELOPE_SCHEMA_DIALECT",
    "ENVELOPE_SCHEMA_ID",
    "FIELD_LAWS_SCHEMA_VERSION",
    "envelope_schema_document",
    "lifecycle_catalog_document",
    "render_contract_artifacts",
    "render_envelope_schema",
    "render_lifecycle_catalog",
    "render_lifecycle_markdown",
]
