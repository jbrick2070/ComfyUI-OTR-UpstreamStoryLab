"""Verify the transplanted source-bank data stays intact and budget-free.

The Story Lab vendors real source texts so adaptation fidelity can be proven
against actual prose rather than synthetic fixtures.  Those bytes are
evidence: every Folger scene must still hash to the digest its provenance
sidecar recorded when it was fetched, every manifest unit must resolve to a
real file, and no source row may reacquire a word budget.

Non-commercial license labels are carried so downstream credits can honor
them.  They are metadata for the credits roll, never spoken text.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BANKS = ROOT / "fixtures" / "source_banks"
PUBLIC_DOMAIN = SOURCE_BANKS / "public_domain_story"
SHAKESPEARE = SOURCE_BANKS / "shakespeare"

MANIFEST_SCHEMA_VERSION = "otr_story_lab.source_manifest.v1"
CURATED_SCHEMA_VERSION = "otr_story_lab.curated_scenes.v1"
FORBIDDEN_KEYS = ("recommended_word_budget", "target_words", "word_budget")

SOURCE_REQUIRED_KEYS = (
    "source_id",
    "title",
    "author",
    "year",
    "license_status",
    "license_url",
    "source_url",
    "source_label",
    "adapter_type",
    "search_tags",
    "cast_hints",
    "units",
)
UNIT_REQUIRED_KEYS = ("unit_id", "label", "synopsis", "text_path")
SCENE_REQUIRED_KEYS = (
    "source_ref",
    "play_code",
    "play_title",
    "act",
    "scene",
    "scene_label",
    "synopsis",
    "source_label",
    "source_url",
    "license_label",
    "license_url",
    "commercial_use_allowed",
    "text_path",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_public_domain(failures: list[str]) -> int:
    manifest = _load(PUBLIC_DOMAIN / "manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        failures.append(
            f"public-domain manifest schema is {manifest.get('schema_version')!r}"
        )
    sources = manifest.get("sources", [])
    if not sources:
        failures.append("public-domain manifest declares no sources")
    seen_ids: set[str] = set()
    for source in sources:
        source_id = source.get("source_id", "<missing>")
        missing = [key for key in SOURCE_REQUIRED_KEYS if key not in source]
        if missing:
            failures.append(f"source {source_id} missing keys {missing}")
        if source_id in seen_ids:
            failures.append(f"duplicate source_id {source_id}")
        seen_ids.add(source_id)
        for unit in source.get("units", []):
            unit_missing = [key for key in UNIT_REQUIRED_KEYS if key not in unit]
            if unit_missing:
                failures.append(
                    f"source {source_id} unit missing keys {unit_missing}"
                )
            text_path = PUBLIC_DOMAIN / unit.get("text_path", "")
            if not text_path.is_file():
                failures.append(
                    f"source {source_id} unit text is missing: "
                    f"{unit.get('text_path')}"
                )
            elif not text_path.read_text(encoding="utf-8").strip():
                failures.append(f"source {source_id} unit text is empty")
    return len(sources)


def _check_shakespeare(failures: list[str]) -> tuple[int, int]:
    curated = _load(SHAKESPEARE / "curated_scenes.json")
    if curated.get("schema_version") != CURATED_SCHEMA_VERSION:
        failures.append(
            f"curated-scenes schema is {curated.get('schema_version')!r}"
        )
    scenes = curated.get("scenes", [])
    if not scenes:
        failures.append("curated scenes declares no scenes")
    for scene in scenes:
        ref = scene.get("source_ref", "<missing>")
        missing = [key for key in SCENE_REQUIRED_KEYS if key not in scene]
        if missing:
            failures.append(f"scene {ref} missing keys {missing}")
        if not (SHAKESPEARE / scene.get("text_path", "")).is_file():
            failures.append(f"scene {ref} text is missing")
        # Non-commercial source text must keep the label credits will show.
        if scene.get("commercial_use_allowed") is False and not scene.get(
            "license_label"
        ):
            failures.append(
                f"scene {ref} is non-commercial but carries no license label"
            )

    verified = 0
    for prov_path in sorted((SHAKESPEARE / "sources").glob("*.provenance.json")):
        provenance = _load(prov_path)
        body_path = prov_path.parent / prov_path.name.replace(
            ".provenance.json", ".txt"
        )
        if not body_path.is_file():
            failures.append(f"provenance {prov_path.stem} has no source text")
            continue
        body = body_path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != provenance.get("body_sha256"):
            failures.append(
                f"provenance {prov_path.stem} digest drifted: source text no "
                "longer matches the bytes that were fetched"
            )
        elif len(body) != provenance.get("body_bytes"):
            failures.append(f"provenance {prov_path.stem} byte count drifted")
        else:
            verified += 1
        if not provenance.get("speakers"):
            failures.append(f"provenance {prov_path.stem} lists no speakers")
    return len(scenes), verified


def _check_no_budgets(failures: list[str]) -> None:
    for path in sorted(SOURCE_BANKS.rglob("*.json")):
        payload = path.read_text(encoding="utf-8")
        for key in FORBIDDEN_KEYS:
            if f'"{key}"' in payload:
                failures.append(
                    f"{path.relative_to(ROOT)} carries forbidden {key!r}; the "
                    "Story Lab has no word-count authority"
                )


def main() -> int:
    if not SOURCE_BANKS.is_dir():
        print("FAIL source bank data is missing")
        return 1
    failures: list[str] = []
    source_count = _check_public_domain(failures)
    scene_count, verified = _check_shakespeare(failures)
    _check_no_budgets(failures)

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"source banks failed: {len(failures)} problem(s)")
        return 1
    print(
        f"source banks OK: {source_count} public-domain sources, "
        f"{scene_count} curated scenes, {verified} provenance digests verified, "
        "no word budgets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
