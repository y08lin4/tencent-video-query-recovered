from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PYTHON_DEMO = ROOT / "examples" / "python" / "tencent_video_api_demo.py"
GO_DEMO = ROOT / "go.exe"

API1_CIDS = [
    "mzc00200idzf2m8",
    "mzc00200xxpsogl",
    "mzc002009qyd7nv",
]
API2_VIDS = [
    "z4102qfi0x4",
    "j4101ouc4ve",
    "m4102tgsa8d",
]

API1_TIDS = ["431", "537"]
API2_TIDS = ["535", "540", "541"]


def parse_csv_arg(raw: str | None, default: list[str]) -> list[str]:
    if not raw:
        return list(default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a multi-sample tid richness matrix from the repository's Python/Go demos."
    )
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-command timeout in seconds.")
    parser.add_argument("--python-bin", default=sys.executable, help="Python executable for the Python demo.")
    parser.add_argument(
        "--api1-tids",
        help="Comma-separated API1 tid list to include in the Python matrix. Defaults to the built-in 431/537 set.",
    )
    parser.add_argument(
        "--api2-tids",
        help="Comma-separated API2 tid list to include in the Python matrix. Defaults to the built-in 535/540/541 set.",
    )
    parser.add_argument(
        "--skip-go",
        action="store_true",
        help="Skip Go spot-checks and only run the Python matrix.",
    )
    return parser.parse_args()


def normalize_str(value: Any) -> str:
    return str(value or "").strip()


def has_nonempty(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return normalize_str(value) != ""


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    entry: dict[str, Any] = {
        "command": command,
        "exit_code": completed.returncode,
        "stderr_excerpt": completed.stderr[:600],
    }
    if completed.returncode != 0:
        entry["result"] = "command_failed"
        entry["stdout_excerpt"] = completed.stdout[:600]
        return entry
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        entry["result"] = "invalid_json_output"
        entry["stdout_excerpt"] = completed.stdout[:600]
        entry["json_error"] = str(exc)
        return entry
    entry["result"] = "success"
    entry["payload"] = payload
    return entry


def summarize_api1(payload: dict[str, Any]) -> OrderedDict[str, Any]:
    cover = payload.get("cover_info") or {}
    diagnostics = payload.get("api1_batch_diagnostics") or {}
    cover_infos = payload.get("cover_infos") or []
    video_ids = cover.get("video_ids") or []
    has_title = has_nonempty(cover.get("title"))
    has_type = has_nonempty(cover.get("type"))
    has_type_name = has_nonempty(cover.get("type_name"))
    has_pay_status = has_nonempty(cover.get("pay_status"))
    summary = OrderedDict(
        (
            ("cover_title", normalize_str(cover.get("title"))),
            ("type", normalize_str(cover.get("type"))),
            ("type_name", normalize_str(cover.get("type_name"))),
            ("pay_status", normalize_str(cover.get("pay_status"))),
            ("video_ids_count", len(video_ids)),
            ("cover_infos_count", len(cover_infos) if isinstance(cover_infos, list) else 0),
            ("aggregated_video_ids_count", int(diagnostics.get("aggregated_video_ids_count") or 0)),
            ("has_cover_pic_hz", has_nonempty(cover.get("cover_pic_hz"))),
        )
    )
    if summary["video_ids_count"] > 0 and (has_title or has_type or has_type_name or has_pay_status):
        summary["shape"] = "positive_cover_branch"
    elif summary["video_ids_count"] > 0:
        summary["shape"] = "video_ids_only_shell"
    elif has_title or has_type or has_type_name or has_pay_status:
        summary["shape"] = "cover_only_positive_shell"
    elif summary["cover_infos_count"] > 0 or summary["has_cover_pic_hz"]:
        summary["shape"] = "success_shell_without_sample"
    else:
        summary["shape"] = "empty_or_failure_shell"
    return summary


def summarize_api2(payload: dict[str, Any]) -> OrderedDict[str, Any]:
    rows = payload.get("video_details") or []
    row = rows[0] if rows else {}
    has_pic = has_nonempty(row.get("pic160x90")) or has_nonempty(row.get("pic_640_360")) or has_nonempty(row.get("pic496x280")) or has_nonempty(row.get("pic_228_128"))
    has_type = has_nonempty(row.get("type"))
    has_vid = has_nonempty(row.get("vid"))
    has_create_time = has_nonempty(row.get("create_time"))
    summary = OrderedDict(
        (
            ("retcode", normalize_str(row.get("retcode"))),
            ("title", normalize_str(row.get("title"))),
            ("duration_seconds", normalize_str(row.get("duration_seconds"))),
            ("url", normalize_str(row.get("url"))),
            ("has_title", has_nonempty(row.get("title"))),
            ("has_duration", has_nonempty(row.get("duration_seconds"))),
            ("has_url", has_nonempty(row.get("url"))),
            ("has_defn", has_nonempty(row.get("defn"))),
            ("has_state", has_nonempty(row.get("state"))),
            ("has_upload_src", has_nonempty(row.get("upload_src"))),
            ("has_category_map", has_nonempty(row.get("category_map"))),
            ("has_cover_list", has_nonempty(row.get("cover_list"))),
            ("has_vwh", has_nonempty(row.get("vwh"))),
            ("has_pic", has_pic),
            ("has_type", has_type),
            ("has_vid", has_vid),
            ("has_create_time", has_create_time),
            ("empty_shell", bool(row.get("empty_shell"))),
        )
    )
    richness_fields = [
        "has_title",
        "has_duration",
        "has_url",
        "has_defn",
        "has_state",
        "has_upload_src",
        "has_category_map",
        "has_cover_list",
        "has_vwh",
        "has_pic",
        "has_type",
        "has_vid",
        "has_create_time",
    ]
    summary["richness_score"] = sum(1 for name in richness_fields if summary[name])
    if summary["has_title"] and summary["has_duration"] and summary["has_defn"]:
        summary["shape"] = "fuller_detail_row"
    elif (
        summary["has_title"]
        and summary["has_duration"]
        and summary["has_url"]
        and summary["has_cover_list"]
        and summary["has_type"]
        and summary["has_vid"]
    ):
        summary["shape"] = "richer_alternate_positive_shell"
    elif summary["has_title"] and summary["has_url"] and summary["has_pic"] and not summary["has_duration"]:
        summary["shape"] = "title_url_pic_shell"
    elif summary["has_title"] and summary["has_url"] and summary["has_pic"]:
        summary["shape"] = "title_url_pic_shell"
    elif summary["empty_shell"] or summary["richness_score"] == 0:
        summary["shape"] = "success_shell_without_sample"
    elif summary["has_title"] or summary["has_url"]:
        summary["shape"] = "thin_positive_shell"
    else:
        summary["shape"] = "empty_or_failure_shell"
    return summary


def python_api1_command(python_bin: str, cid: str, tid: str) -> list[str]:
    return [python_bin, str(PYTHON_DEMO), "--cid", cid, "--api1-tid", tid, "--json"]


def python_api2_command(python_bin: str, vid: str, tid: str) -> list[str]:
    return [python_bin, str(PYTHON_DEMO), "--vid", vid, "--api2-tid", tid, "--json"]


def go_api1_command(cid: str, tid: str) -> list[str]:
    return [str(GO_DEMO), "-cid", cid, "-api1-tid", tid, "-json"]


def go_api2_command(vid: str, tid: str) -> list[str]:
    return [str(GO_DEMO), "-vids", vid, "-api2-tid", tid, "-json"]


def build_report(args: argparse.Namespace) -> OrderedDict[str, Any]:
    api1_tids = parse_csv_arg(args.api1_tids, API1_TIDS)
    api2_tids = parse_csv_arg(args.api2_tids, API2_TIDS)
    report = OrderedDict(
        (
            ("generated_at", datetime.now().isoformat(timespec="seconds")),
            (
                "scope",
                f"Multi-sample tid field-richness matrix for API1 {','.join(api1_tids)} and API2 {','.join(api2_tids)} using the repository demos",
            ),
            ("python_matrix", OrderedDict()),
            ("go_spotchecks", OrderedDict()),
        )
    )

    api1_rows = OrderedDict()
    for tid in api1_tids:
        tid_rows = OrderedDict()
        for cid in API1_CIDS:
            result = run_command(python_api1_command(args.python_bin, cid, tid), args.timeout)
            entry = OrderedDict((("demo_result", result["result"]),))
            if result["result"] == "success":
                entry["summary"] = summarize_api1(result["payload"])
            else:
                entry["command"] = result["command"]
                entry["stderr_excerpt"] = result.get("stderr_excerpt", "")
                entry["stdout_excerpt"] = result.get("stdout_excerpt", "")
            tid_rows[cid] = entry
        api1_rows[tid] = tid_rows
    report["python_matrix"]["api1"] = api1_rows

    api2_rows = OrderedDict()
    for tid in api2_tids:
        tid_rows = OrderedDict()
        for vid in API2_VIDS:
            result = run_command(python_api2_command(args.python_bin, vid, tid), args.timeout)
            entry = OrderedDict((("demo_result", result["result"]),))
            if result["result"] == "success":
                entry["summary"] = summarize_api2(result["payload"])
            else:
                entry["command"] = result["command"]
                entry["stderr_excerpt"] = result.get("stderr_excerpt", "")
                entry["stdout_excerpt"] = result.get("stdout_excerpt", "")
            tid_rows[vid] = entry
        api2_rows[tid] = tid_rows
    report["python_matrix"]["api2"] = api2_rows

    go_checks = OrderedDict()
    if not args.skip_go:
        for label, command, summarizer in (
            ("api1_tid431_primary", go_api1_command(API1_CIDS[0], "431"), summarize_api1),
            ("api1_tid537_primary", go_api1_command(API1_CIDS[0], "537"), summarize_api1),
            ("api2_tid535_primary", go_api2_command(API2_VIDS[0], "535"), summarize_api2),
            ("api2_tid540_primary", go_api2_command(API2_VIDS[0], "540"), summarize_api2),
            ("api2_tid541_secondary", go_api2_command(API2_VIDS[1], "541"), summarize_api2),
        ):
            result = run_command(command, args.timeout)
            entry = OrderedDict((("demo_result", result["result"]),))
            if result["result"] == "success":
                entry["summary"] = summarizer(result["payload"])
            else:
                entry["command"] = result["command"]
                entry["stderr_excerpt"] = result.get("stderr_excerpt", "")
                entry["stdout_excerpt"] = result.get("stdout_excerpt", "")
            go_checks[label] = entry
    report["go_spotchecks"] = go_checks

    report["verdict"] = [
        "This matrix is caller-facing evidence about output richness, not a proof that aged-cookie or login-state behave the same.",
        "Different positive or top-level-success tid branches can still expose very different shell thickness; do not collapse them into one capability family without checking the row-level shape.",
        "Canonical fuller-detail rows should stay the default for callers unless a thinner shell branch is being probed deliberately."
    ]
    return report


def main() -> int:
    args = parse_args()
    report = build_report(args)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
