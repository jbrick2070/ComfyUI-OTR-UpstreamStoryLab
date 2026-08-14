"""Extract immutable Story Lab recovery cases from real OTR ledgers.

This script does not diagnose or repair a story.  It copies the smallest
authoritative objects needed to reproduce the 2026-08-13 comparison and pins
each source/object with SHA-256.  The checked-in JSON files are therefore
evidence, not hand-authored examples.

Usage (PowerShell paths shown only as argument names):

    python scripts/extract_story_recovery_cases.py \
      --bad-ledger <current-scifi-news-ledger> \
      --bad-render-result <w45-result-json> \
      --bad-obs-asset <published-mp4> \
      --good-ledger <legacy-science-news-ledger> \
      --good-final-video <legacy-final-mp4>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "otr_story_recovery_case.v1"

BAD_LEDGER_SHA256 = (
    "a1146b22dcf0e122348e901070969089c5bfc92604f7b41395dca092212546fe"
)
BAD_RENDER_RESULT_SHA256 = (
    "65b81d6d7c11262f71bdf82568b7e9ba8f380f51ee188dbefe98ce3d3706f2f5"
)
BAD_OBS_ASSET_SHA256 = (
    "ef35bada7cca3e35b0c338d6825c7b0ab5ff502ef50d53a2005a321d1b9d1d4c"
)
GOOD_LEDGER_SHA256 = (
    "ad5285a08a88d7682ad707baf44dea2e8c094b9c08e153f466a7233d8af2ee8f"
)
GOOD_FINAL_VIDEO_SHA256 = (
    "45738f2a8e0c2de2e52e15352010d40698729bfcf8f877930da6fd2f089b2ca7"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file_hash(path: Path, expected: str, label: str) -> None:
    actual = _file_sha256(path)
    if actual != expected:
        raise SystemExit(
            f"{label} hash mismatch: expected {expected}, got {actual}: {path}"
        )


def _portable_hint(path: Path) -> str:
    parts = list(path.resolve().parts)
    lowered = [part.lower() for part in parts]
    if "output" in lowered:
        index = lowered.index("output")
        return "/".join(parts[index:])
    return path.name


def _last_accepted_call(ledger: dict[str, Any], pass_id: str) -> dict[str, Any]:
    calls = ledger["meta"]["scifi_codex"]["call_journal"]["calls"]
    matches = [
        call
        for call in calls
        if call.get("pass_id") == pass_id and call.get("status") == "accepted"
    ]
    if not matches:
        raise SystemExit(f"accepted {pass_id} call is absent")
    return matches[-1]


def _accepted_attempt_sha(call: dict[str, Any]) -> str:
    matches = [
        attempt
        for attempt in call.get("attempts", [])
        if attempt.get("status") == "accepted"
    ]
    if not matches or not matches[-1].get("raw_sha256"):
        raise SystemExit(f"accepted attempt receipt is absent for {call.get('pass_id')}")
    return str(matches[-1]["raw_sha256"])


def _object_hashes(objects: dict[str, Any]) -> dict[str, str]:
    return {name: _canonical_sha256(value) for name, value in objects.items()}


def _extract_bad_case(
    ledger_path: Path,
    render_result_path: Path,
    obs_asset_path: Path,
) -> dict[str, Any]:
    _require_file_hash(ledger_path, BAD_LEDGER_SHA256, "bad ledger")
    _require_file_hash(
        render_result_path,
        BAD_RENDER_RESULT_SHA256,
        "bad render result",
    )
    _require_file_hash(obs_asset_path, BAD_OBS_ASSET_SHA256, "bad OBS asset")

    ledger = _read_json(ledger_path)
    render_result = _read_json(render_result_path)
    p2 = _last_accepted_call(ledger, "P2")
    p3 = _last_accepted_call(ledger, "P3")
    p5 = _last_accepted_call(ledger, "P5")
    fact_index = ledger["meta"]["scifi_codex"]["fact_index"]

    evidence_objects = {
        "cast_plan": p2["accepted"],
        "fact_index": fact_index,
        "p3_compiled": p3["accepted"],
        "p5_compiled": p5["accepted"],
        "p3_request_receipt": ledger["meta"]["scifi_codex"]["call_journal"][
            "radio_score_draft_surface"
        ],
        "p5_request_receipt": ledger["meta"]["scifi_codex"]["call_journal"][
            "script_transport"
        ],
        "word_budget_telemetry": ledger["meta"]["word_budget"],
        "render_result": render_result,
    }
    scifi = ledger["meta"]["scifi_codex"]
    authorship = ledger["meta"]["content_authorship"]
    final_script_receipt = next(
        row
        for row in authorship["accepted_artifacts"]
        if row.get("artifact_id") == "final_script"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": "scifi_news_bad_20260813_light_of_possibility",
        "arm": "challenger",
        "case_kind": "current_scifi_codex_v4",
        "capabilities": {
            "p3_compiled": True,
            "p5_compiled": True,
            "raw_transport": False,
            "source_facts": True,
            "music_topology": True,
        },
        "provenance": {
            "episode_id": ledger["episode_id"],
            "otr_commit": ledger["commit"],
            "source_bank": ledger["meta"]["source_bank"],
            "source_ledger_path_hint": _portable_hint(ledger_path),
            "source_ledger_sha256": BAD_LEDGER_SHA256,
            "source_digest": fact_index["payload_sha256"],
        },
        "render_receipt": {
            "render_pass": True,
            "result_path_hint": render_result_path.name,
            "result_sha256": BAD_RENDER_RESULT_SHA256,
            "result": render_result,
            "published_asset_path_hint": _portable_hint(obs_asset_path),
            "published_asset_sha256": BAD_OBS_ASSET_SHA256,
            "published_asset_bytes": obs_asset_path.stat().st_size,
        },
        "object_sha256": _object_hashes(evidence_objects),
        "projection_sha256": _canonical_sha256(evidence_objects),
        "authorities": {
            "cast_plan": p2["accepted"],
            "fact_index": fact_index,
        },
        "artifacts": {
            "p3": {
                "compiled": p3["accepted"],
                "accepted_transport_receipt": p3["accepted_transport"],
                "accepted_attempt_raw_sha256": _accepted_attempt_sha(p3),
            },
            "p5": {
                "compiled": p5["accepted"],
                "accepted_transport_receipt": p5["accepted_transport"],
                "accepted_attempt_raw_sha256": _accepted_attempt_sha(p5),
                "script_digest": scifi["script_digest"],
                "authorship_receipt_sha256": final_script_receipt["sha256"],
            },
            "word_budget_telemetry": ledger["meta"]["word_budget"],
        },
        "request_receipts": {
            "radio_score_draft_surface": scifi["call_journal"][
                "radio_score_draft_surface"
            ],
            "script_transport": scifi["call_journal"]["script_transport"],
        },
        "expected": {
            "story_content_pass": False,
            "presentation_topology_pass": False,
            "finding_codes": [
                "ANNOUNCER_OPEN_MISSING",
                "ANNOUNCER_CODA_MISSING",
                "ANNOUNCER_INTERIOR_ONLY",
                "FACTUAL_CODA_MISSING",
                "P5_SPEAKER_AUTHORITY_MISSING",
                "SPOKEN_NARRATION_OR_STAGE_BUSINESS",
                "CROSS_SPEAKER_TEXT",
                "MUSIC_OPEN_ANCHOR_NOT_ANNOUNCER",
                "MUSIC_CLOSE_ANCHOR_NOT_ANNOUNCER",
            ],
            "narration_or_stage_line_ids": [
                "l001",
                "l002",
                "l004",
                "l005",
                "l007",
                "l008",
                "l009",
                "l010",
                "l011",
            ],
            "cross_speaker_line_ids": ["l005", "l006", "l011"],
        },
        "evidence_limits": [
            "The compact raw P3/P5 JSON text was not persisted; only its byte/character receipt and SHA-256 survive.",
            "The compiled accepted objects are exact ledger evidence and must not be described as raw transport replay.",
        ],
    }


def _extract_good_case(ledger_path: Path, final_video_path: Path) -> dict[str, Any]:
    _require_file_hash(ledger_path, GOOD_LEDGER_SHA256, "good ledger")
    _require_file_hash(
        final_video_path,
        GOOD_FINAL_VIDEO_SHA256,
        "good final video",
    )
    ledger = _read_json(ledger_path)
    evidence_objects = {
        "cast": ledger["cast"],
        "lines": ledger["lines"],
        "news": ledger["meta"]["news"],
        "news_seed": ledger["meta"]["news_seed"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": "science_news_good_20260716_folder_of_red_stamps",
        "arm": "control",
        "case_kind": "legacy_science_news_control",
        "capabilities": {
            "p3_compiled": False,
            "p5_compiled": False,
            "raw_transport": False,
            "source_facts": True,
            "music_topology": False,
        },
        "provenance": {
            "episode_id": ledger["episode_id"],
            "otr_commit": ledger["commit"],
            "source_bank": ledger["meta"]["source_bank"],
            "source_ledger_path_hint": _portable_hint(ledger_path),
            "source_ledger_sha256": GOOD_LEDGER_SHA256,
            "source_digest": ledger["meta"]["news"]["source_hash"],
        },
        "render_receipt": {
            "render_pass": True,
            "published_asset_path_hint": _portable_hint(final_video_path),
            "published_asset_sha256": GOOD_FINAL_VIDEO_SHA256,
            "published_asset_bytes": final_video_path.stat().st_size,
            "audio_duration_seconds": ledger["total_episode_dur_s"],
            "spoken_word_count_telemetry": ledger["total_word_count"],
        },
        "object_sha256": _object_hashes(evidence_objects),
        "projection_sha256": _canonical_sha256(evidence_objects),
        "artifacts": evidence_objects,
        "expected": {
            "story_content_pass": True,
            "presentation_topology_pass": "not_evaluated",
            "first_spoken_role": "announcer",
            "last_spoken_role": "announcer",
            "closing_line_contains_exact_news_close_brief": True,
            "character_rows_are_direct_dialogue": True,
        },
        "evidence_limits": [
            "This legacy ledger has no structured music cue rows.",
            "Opening/closing music topology is not evaluated for this control and must never be inferred as a pass.",
            "The fixture is a clean semantic control, not a claim that the retired many-pass pipeline should return.",
        ],
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bad-ledger", type=Path, required=True)
    parser.add_argument("--bad-render-result", type=Path, required=True)
    parser.add_argument("--bad-obs-asset", type=Path, required=True)
    parser.add_argument("--good-ledger", type=Path, required=True)
    parser.add_argument("--good-final-video", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "fixtures" / "story_recovery",
    )
    args = parser.parse_args()

    bad = _extract_bad_case(
        args.bad_ledger,
        args.bad_render_result,
        args.bad_obs_asset,
    )
    good = _extract_good_case(args.good_ledger, args.good_final_video)
    _write(args.output_dir / "scifi_news_bad_20260813.json", bad)
    _write(args.output_dir / "science_news_good_20260716.json", good)
    print(f"wrote {args.output_dir / 'scifi_news_bad_20260813.json'}")
    print(f"wrote {args.output_dir / 'science_news_good_20260716.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
