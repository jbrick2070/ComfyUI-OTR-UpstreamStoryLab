from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from upstream_story_lab.ledger_artifacts import (
    ENVELOPE_SCHEMA_COMMENT,
    ENVELOPE_SCHEMA_DIALECT,
    ENVELOPE_SCHEMA_ID,
    FIELD_LAWS_SCHEMA_VERSION,
    envelope_schema_document,
    lifecycle_catalog_document,
    render_contract_artifacts,
    render_envelope_schema,
    render_lifecycle_catalog,
    render_lifecycle_markdown,
)
from upstream_story_lab.production_contract import (
    PHASE_ATTEMPT_TYPES,
    PRODUCTION_PHASE_OWNERS,
    ProductionState,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_ledger_contract_artifacts.py"
NORMATIVE = (
    ROOT
    / "fixtures"
    / "story_recovery"
    / "v2"
    / "normative_ledger_envelope.json"
)


def _canonical_pretty_json(value: object) -> str:
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


def _load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "ledger_contract_artifact_generator", GENERATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_envelope_schema_is_full_draft_2020_12_and_deterministic() -> None:
    rendered = render_envelope_schema()
    schema = json.loads(rendered)

    assert rendered.endswith("\n")
    assert rendered == render_envelope_schema()
    assert rendered == _canonical_pretty_json(schema)
    assert schema["$schema"] == ENVELOPE_SCHEMA_DIALECT
    assert schema["$id"] == ENVELOPE_SCHEMA_ID
    assert schema["$comment"] == ENVELOPE_SCHEMA_COMMENT
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "schema_version",
        "story_ledger",
        "story_seal",
        "production_state",
        "final_seal",
    }
    assert "ProductionState" in schema["$defs"]
    for attempt_type in PHASE_ATTEMPT_TYPES:
        assert attempt_type.__name__ in schema["$defs"]
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(
        json.loads(NORMATIVE.read_text(encoding="utf-8"))
    )
    assert schema == envelope_schema_document()


def test_lifecycle_catalog_covers_roots_and_each_phase_attempt_owner() -> None:
    catalog = lifecycle_catalog_document()
    rows = catalog["fields"]
    paths = [row["path"] for row in rows]

    assert catalog["schema_version"] == FIELD_LAWS_SCHEMA_VERSION
    assert catalog["source_schema_id"] == ENVELOPE_SCHEMA_ID
    assert catalog["scope"] == "ledger_envelope"
    assert catalog["field_count"] == len(rows)
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert set(rows[0]) == {
        "path",
        "type",
        "default",
        "owner",
        "mutation",
        "durability",
        "failure",
    }
    assert all(all(str(value).strip() for value in row.values()) for row in rows)

    path_set = set(paths)
    for field_name in ProductionState.model_fields:
        assert f"ledger_envelope.production_state.{field_name}" in path_set

    assert {
        "ledger_envelope.story_ledger.body.context.act_count",
        "ledger_envelope.story_ledger.body.context.story_seed",
        "ledger_envelope.story_ledger.body.story_arc.summary",
        "ledger_envelope.story_ledger.body.acts[].spine",
        "ledger_envelope.story_ledger.body.beats[].act_id",
        "ledger_envelope.story_ledger.body.lines[].text",
        "ledger_envelope.story_seal.story_sha256",
        "ledger_envelope.final_seal",
    } <= path_set
    story_rows = [
        row
        for row in rows
        if row["path"].startswith("ledger_envelope.story_ledger.body.acts")
    ]
    assert story_rows
    assert {row["owner"] for row in story_rows} == {
        "central_story_compiler"
    }

    attempt_base = (
        "ledger_envelope.production_state.journal[]<attempt>.attempt"
    )
    for attempt_type in PHASE_ATTEMPT_TYPES:
        phase_id = attempt_type.model_fields["phase_id"].default
        owner = PRODUCTION_PHASE_OWNERS[phase_id]
        prefix = f"{attempt_base}<{phase_id}>"
        phase_rows = [row for row in rows if row["path"].startswith(prefix + ".")]
        assert phase_rows, phase_id
        assert {row["owner"] for row in phase_rows} == {owner}
        assert {row["mutation"] for row in phase_rows} == {phase_id}
        for field_name in attempt_type.model_fields:
            assert f"{prefix}.{field_name}" in path_set
        assert any(
            row["path"].startswith(f"{prefix}.result<succeeded>.receipt.")
            for row in phase_rows
        )
        assert any(
            row["path"].startswith(f"{prefix}.result<failed>.failure.")
            for row in phase_rows
        )


def test_lifecycle_json_and_markdown_share_one_catalog() -> None:
    catalog = lifecycle_catalog_document()
    rendered_json = render_lifecycle_catalog()
    rendered_markdown = render_lifecycle_markdown()

    assert rendered_json == _canonical_pretty_json(catalog)
    assert json.loads(rendered_json) == catalog
    assert rendered_markdown.endswith("\n")
    assert (
        f"Covered field paths: **{catalog['field_count']}**"
        in rendered_markdown
    )
    assert "| Path | Type | Default law | Lifecycle owner |" in rendered_markdown
    for row in catalog["fields"]:
        assert f"`{row['path']}`" in rendered_markdown


def test_render_contract_artifacts_has_only_pinned_paths() -> None:
    artifacts = render_contract_artifacts()
    assert list(artifacts) == [
        "contracts/ledger_envelope_v2.schema.json",
        "contracts/ledger_field_laws_v2.json",
        "docs/LEDGER_FIELD_REFERENCE.md",
    ]
    assert all(text.endswith("\n") for text in artifacts.values())


def test_checked_in_artifacts_are_byte_exact_fresh_renderings() -> None:
    artifacts = render_contract_artifacts()

    for relative_path, rendered in artifacts.items():
        assert (ROOT / relative_path).read_bytes() == rendered.encode("utf-8")


def test_cli_write_and_read_only_check(tmp_path: Path, capsys) -> None:
    generator = _load_generator_module()
    expected = render_contract_artifacts()

    assert generator.main(["--check"], root=tmp_path) == 1
    missing_output = capsys.readouterr().out
    assert missing_output.count("MISSING ") == len(expected)
    assert not any(tmp_path.rglob("*"))

    assert generator.main(["--write"], root=tmp_path) == 0
    capsys.readouterr()
    for relative_path, rendered in expected.items():
        assert (tmp_path / relative_path).read_bytes() == rendered.encode("utf-8")

    assert generator.main(["--check"], root=tmp_path) == 0
    assert "artifacts are current" in capsys.readouterr().out

    stale_path = tmp_path / "contracts" / "ledger_field_laws_v2.json"
    stale_path.write_bytes(b"{}\n")
    before = stale_path.read_bytes()
    assert generator.main(["--check"], root=tmp_path) == 1
    stale_output = capsys.readouterr().out
    assert "STALE contracts/ledger_field_laws_v2.json" in stale_output
    assert stale_path.read_bytes() == before


def test_cli_check_is_read_only_and_green_on_repository(capsys) -> None:
    generator = _load_generator_module()
    paths = [ROOT / path for path in render_contract_artifacts()]
    before = {path: path.read_bytes() for path in paths}

    assert generator.main(["--check"], root=ROOT) == 0
    assert "artifacts are current" in capsys.readouterr().out
    assert {path: path.read_bytes() for path in paths} == before


def test_cli_requires_exactly_one_mode(tmp_path: Path) -> None:
    generator = _load_generator_module()
    with pytest.raises(SystemExit) as no_mode:
        generator.main([], root=tmp_path)
    assert no_mode.value.code == 2
    with pytest.raises(SystemExit) as both_modes:
        generator.main(["--write", "--check"], root=tmp_path)
    assert both_modes.value.code == 2
