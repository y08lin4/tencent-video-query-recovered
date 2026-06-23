from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PYTHON_DEMO = ROOT / "examples" / "python" / "tencent_video_api_demo.py"
GO_DEMO_DIR = ROOT / "examples" / "go"
GO_DEMO_BINARY = ROOT / "go.exe"

DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 2
TRANSIENT_ERROR_MARKERS = (
    "deadline exceeded",
    "timeout",
    "timed out",
    "temporary failure",
    "connection reset",
    "connection aborted",
    "eof",
    "awaiting headers",
    "tls handshake timeout",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the repository's Python/Go Tencent Video demo entrypoints "
            "against the highest-value anonymous direct-call validation surfaces."
        )
    )
    parser.add_argument(
        "--surface",
        action="append",
        dest="surfaces",
        help=(
            "Surface id to run; repeatable. "
            "When omitted, run the default full demo surface set."
        ),
    )
    parser.add_argument(
        "--demo",
        choices=("python", "go", "both"),
        default="both",
        help="Limit execution to Python, Go, or both demo families.",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python executable to use for the Python demo.",
    )
    parser.add_argument(
        "--go-bin",
        default="go",
        help="Go executable to use for the Go demo.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Per-command timeout in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Maximum command attempts per surface; transient network failures are retried within this limit.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any selected validation surface fails.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. When omitted, print to stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation.",
    )
    return parser.parse_args()


def key_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def dict_get(mapping: Any, *candidates: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    indexed = {key_id(str(key)): value for key, value in mapping.items()}
    for candidate in candidates:
        found = indexed.get(key_id(candidate))
        if found is not None:
            return found
    return None


def normalize_str(value: Any) -> str:
    return str(value or "").strip()


def split_csv_text(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def has_value(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return normalize_str(value) != ""


def payload_cover_info(payload: dict[str, Any]) -> dict[str, Any]:
    cover = dict_get(payload, "cover_info", "coverinfo")
    return cover if isinstance(cover, dict) else {}


def payload_cover_infos(payload: dict[str, Any]) -> list[dict[str, Any]]:
    covers = dict_get(payload, "cover_infos", "coverinfos")
    if not isinstance(covers, list):
        return []
    return [cover for cover in covers if isinstance(cover, dict)]


def payload_api1_params(payload: dict[str, Any]) -> dict[str, Any]:
    params = dict_get(payload, "api1_params", "api1params")
    return params if isinstance(params, dict) else {}


def payload_api2_params(payload: dict[str, Any]) -> dict[str, Any]:
    params = dict_get(payload, "api2_params", "api2params")
    return params if isinstance(params, dict) else {}


def payload_video_details(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = dict_get(payload, "video_details", "videodetails")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def payload_batch_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    diag = dict_get(payload, "api2_batch_diagnostics", "api2batchdiagnostics")
    return diag if isinstance(diag, dict) else {}


def payload_api1_batch_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    diag = dict_get(payload, "api1_batch_diagnostics", "api1batchdiagnostics")
    return diag if isinstance(diag, dict) else {}


def first_row(payload: dict[str, Any]) -> dict[str, Any]:
    details = payload_video_details(payload)
    return details[0] if details else {}


def row_has_fuller_detail(row: dict[str, Any]) -> bool:
    return any(
        has_value(dict_get(row, candidate))
        for candidate in ("duration_seconds", "state", "upload_src", "defn", "category_map")
    )


def row_has_positive_shell(row: dict[str, Any]) -> bool:
    return any(
        has_value(dict_get(row, candidate))
        for candidate in ("retcode", "vid", "title", "url")
    )


def row_cover_list_count(row: dict[str, Any]) -> int:
    covers = dict_get(row, "cover_list", "coverlist")
    return len(covers) if isinstance(covers, list) else 0


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cover = payload_cover_info(payload)
    covers = payload_cover_infos(payload)
    api1_params = payload_api1_params(payload)
    api2_params = payload_api2_params(payload)
    rows = payload_video_details(payload)
    row = rows[0] if rows else {}
    api1_diagnostics = payload_api1_batch_diagnostics(payload)
    diagnostics = payload_batch_diagnostics(payload)
    return OrderedDict(
        (
            ("cid", normalize_str(dict_get(payload, "cid"))),
            ("cover_title", normalize_str(dict_get(cover, "title"))),
            ("cover_video_ids_count", len(dict_get(cover, "video_ids") or [])),
            ("cover_infos_count", len(covers)),
            ("api1_requested_cid_count", int(dict_get(api1_diagnostics, "requested_cid_count") or 0)),
            ("api1_returned_cover_count", int(dict_get(api1_diagnostics, "returned_cover_count") or 0)),
            ("api1_returned_cids", dict_get(api1_diagnostics, "returned_cids") or []),
            ("api1_aggregated_video_ids_count", int(dict_get(api1_diagnostics, "aggregated_video_ids_count") or 0)),
            ("api1_tid", normalize_str(dict_get(api1_params, "tid"))),
            ("api2_tid", normalize_str(dict_get(api2_params, "tid"))),
            ("api2_otype", normalize_str(dict_get(api2_params, "otype"))),
            ("api2_union_platform", normalize_str(dict_get(api2_params, "union_platform"))),
            ("api2_callback", normalize_str(dict_get(api2_params, "callback"))),
            ("results_count", len(rows)),
            ("first_result_vid", normalize_str(dict_get(row, "vid"))),
            ("first_result_retcode", normalize_str(dict_get(row, "retcode"))),
            ("first_result_title", normalize_str(dict_get(row, "title"))),
            ("first_result_empty_shell", bool(dict_get(row, "empty_shell"))),
            ("first_result_has_url", has_value(dict_get(row, "url"))),
            ("first_result_has_vid", has_value(dict_get(row, "vid"))),
            ("first_result_has_duration", has_value(dict_get(row, "duration_seconds"))),
            ("first_result_has_state", has_value(dict_get(row, "state"))),
            ("first_result_has_upload_src", has_value(dict_get(row, "upload_src"))),
            ("first_result_has_create_time", has_value(dict_get(row, "create_time"))),
            ("first_result_cover_list_count", row_cover_list_count(row)),
            ("first_result_has_defn", has_value(dict_get(row, "defn"))),
            (
                "batch_all_results_empty_shell",
                bool(dict_get(diagnostics, "all_results_empty_shell")),
            ),
        )
    )


def validate_canonical_chain(payload: dict[str, Any]) -> tuple[bool, str, list[str]]:
    cover = payload_cover_info(payload)
    row = first_row(payload)
    checks = [
        has_value(dict_get(cover, "title")),
        has_value(dict_get(cover, "video_ids")),
        normalize_str(dict_get(row, "retcode")) == "0",
        not bool(dict_get(row, "empty_shell")),
        row_has_fuller_detail(row),
    ]
    highlights = [
        f"API1 cover title={normalize_str(dict_get(cover, 'title')) or '-'}",
        f"API1 video_ids_count={len(dict_get(cover, 'video_ids') or [])}",
        f"API2 first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        (
            "API2 canonical row includes fuller detail fields"
            if row_has_fuller_detail(row)
            else "API2 canonical row is missing fuller detail fields"
        ),
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def validate_url_chain(
    payload: dict[str, Any], expected_cid: str
) -> tuple[bool, str, list[str]]:
    ok, result, highlights = validate_canonical_chain(payload)
    actual_cid = normalize_str(dict_get(payload, "cid"))
    cid_ok = actual_cid == expected_cid
    highlights.insert(0, f"extracted cid={actual_cid or '-'}")
    return ok and cid_ok, result if ok and cid_ok else "failure", highlights


def validate_api1_tid537_probe(
    payload: dict[str, Any], expected_cid: str
) -> tuple[bool, str, list[str]]:
    cover = payload_cover_info(payload)
    covers = payload_cover_infos(payload)
    api1_params = payload_api1_params(payload)
    api1_diagnostics = payload_api1_batch_diagnostics(payload)
    actual_cid = normalize_str(dict_get(payload, "cid"))
    actual_tid = normalize_str(dict_get(api1_params, "tid"))
    video_ids_count = len(dict_get(cover, "video_ids") or [])
    aggregated_video_ids_count = int(dict_get(api1_diagnostics, "aggregated_video_ids_count") or 0)
    checks = [
        actual_cid == expected_cid,
        actual_tid == "537",
        len(covers) > 0,
        video_ids_count == 0,
        aggregated_video_ids_count == 0,
    ]
    highlights = [
        f"cid={actual_cid or '-'}",
        f"api1 tid={actual_tid or '-'}",
        f"cover_infos_count={len(covers)}",
        f"cover_video_ids_count={video_ids_count}",
        f"aggregated_video_ids_count={aggregated_video_ids_count}",
    ]
    return all(checks), "success_with_shell_only_probe" if all(checks) else "failure", highlights


def validate_api1_tid453_cover_shell(
    payload: dict[str, Any], expected_cid: str
) -> tuple[bool, str, list[str]]:
    cover = payload_cover_info(payload)
    covers = payload_cover_infos(payload)
    api1_params = payload_api1_params(payload)
    api1_diagnostics = payload_api1_batch_diagnostics(payload)
    rows = payload_video_details(payload)
    actual_cid = normalize_str(dict_get(payload, "cid"))
    actual_tid = normalize_str(dict_get(api1_params, "tid"))
    cover_title = normalize_str(dict_get(cover, "title"))
    video_ids_count = len(dict_get(cover, "video_ids") or [])
    aggregated_video_ids_count = int(dict_get(api1_diagnostics, "aggregated_video_ids_count") or 0)
    checks = [
        actual_cid == expected_cid,
        actual_tid == "453",
        len(covers) > 0,
        has_value(cover_title),
        video_ids_count == 0,
        aggregated_video_ids_count == 0,
        len(rows) == 0,
    ]
    highlights = [
        f"cid={actual_cid or '-'}",
        f"api1 tid={actual_tid or '-'}",
        f"cover_title={cover_title or '-'}",
        f"cover_infos_count={len(covers)}",
        f"cover_video_ids_count={video_ids_count}",
        f"aggregated_video_ids_count={aggregated_video_ids_count}",
        f"video_details_count={len(rows)}",
    ]
    return all(checks), "success_with_cover_shell_only_branch" if all(checks) else "failure", highlights


def validate_jsonp_callback(payload: dict[str, Any], callback: str) -> tuple[bool, str, list[str]]:
    row = first_row(payload)
    api2_params = payload_api2_params(payload)
    diagnostics = payload_batch_diagnostics(payload)
    otype = normalize_str(dict_get(api2_params, "otype"))
    seen_callback = normalize_str(dict_get(api2_params, "callback"))
    checks = [
        otype == "json",
        seen_callback == callback,
        normalize_str(dict_get(row, "retcode")) == "0",
        row_has_positive_shell(row),
        not bool(dict_get(diagnostics, "all_results_empty_shell")),
    ]
    highlights = [
        f"api2 otype={otype or '-'}",
        f"api2 callback={seen_callback or '-'}",
        f"first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        (
            "JSONP path returned a non-empty positive row"
            if row_has_positive_shell(row)
            else "JSONP path did not return a usable positive row"
        ),
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def validate_alt_positive_tid(
    payload: dict[str, Any], expected_tid: str
) -> tuple[bool, str, list[str]]:
    row = first_row(payload)
    api2_params = payload_api2_params(payload)
    actual_tid = normalize_str(dict_get(api2_params, "tid"))
    sparse = row_has_positive_shell(row) and not row_has_fuller_detail(row)
    checks = [
        actual_tid == expected_tid,
        normalize_str(dict_get(row, "retcode")) == "0",
        row_has_positive_shell(row),
    ]
    highlights = [
        f"api2 tid={actual_tid or '-'}",
        f"first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        (
            "alternate positive shell is sparse on this sample"
            if sparse
            else "alternate positive shell is not sparse on this sample"
        ),
    ]
    result = "success_with_thin_positive_shell" if all(checks) and sparse else "success"
    if not all(checks):
        result = "failure"
    return all(checks), result, highlights


def validate_api2_tid488_thin_positive_shell(payload: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(payload)
    api2_params = payload_api2_params(payload)
    actual_tid = normalize_str(dict_get(api2_params, "tid"))
    checks = [
        actual_tid == "488",
        normalize_str(dict_get(row, "retcode")) == "0",
        has_value(dict_get(row, "title")),
        has_value(dict_get(row, "url")),
        not has_value(dict_get(row, "vid")),
        not has_value(dict_get(row, "duration_seconds")),
        row_cover_list_count(row) == 0,
        not has_value(dict_get(row, "create_time")),
        not has_value(dict_get(row, "state")),
        not has_value(dict_get(row, "upload_src")),
    ]
    highlights = [
        f"api2 tid={actual_tid or '-'}",
        f"first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        f"has_title={has_value(dict_get(row, 'title'))}",
        f"has_url={has_value(dict_get(row, 'url'))}",
        f"has_vid={has_value(dict_get(row, 'vid'))}",
        f"has_duration={has_value(dict_get(row, 'duration_seconds'))}",
        f"cover_list_count={row_cover_list_count(row)}",
        f"has_create_time={has_value(dict_get(row, 'create_time'))}",
    ]
    return all(checks), "success_with_thin_positive_shell" if all(checks) else "failure", highlights


def validate_api2_tid502_richer_positive_shell(payload: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(payload)
    api2_params = payload_api2_params(payload)
    actual_tid = normalize_str(dict_get(api2_params, "tid"))
    checks = [
        actual_tid == "502",
        normalize_str(dict_get(row, "retcode")) == "0",
        has_value(dict_get(row, "title")),
        has_value(dict_get(row, "url")),
        has_value(dict_get(row, "vid")),
        has_value(dict_get(row, "duration_seconds")),
        row_cover_list_count(row) >= 1,
        has_value(dict_get(row, "create_time")),
        not has_value(dict_get(row, "state")),
        not has_value(dict_get(row, "upload_src")),
        not has_value(dict_get(row, "defn")),
    ]
    highlights = [
        f"api2 tid={actual_tid or '-'}",
        f"first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        f"has_title={has_value(dict_get(row, 'title'))}",
        f"has_url={has_value(dict_get(row, 'url'))}",
        f"has_vid={has_value(dict_get(row, 'vid'))}",
        f"has_duration={has_value(dict_get(row, 'duration_seconds'))}",
        f"cover_list_count={row_cover_list_count(row)}",
        f"has_create_time={has_value(dict_get(row, 'create_time'))}",
    ]
    return all(checks), "success_with_richer_alt_positive_shell" if all(checks) else "failure", highlights


def validate_alt_positive_tid_union_platform(
    payload: dict[str, Any], expected_tid: str, expected_union_platform: str
) -> tuple[bool, str, list[str]]:
    ok, result, highlights = validate_alt_positive_tid(payload, expected_tid)
    api2_params = payload_api2_params(payload)
    actual_union_platform = normalize_str(dict_get(api2_params, "union_platform", "UnionPlatform"))
    union_ok = actual_union_platform == expected_union_platform
    highlights.insert(1, f"api2 union_platform={actual_union_platform or '-'}")
    return ok and union_ok, result if ok and union_ok else "failure", highlights


def validate_batch_lookup(
    payload: dict[str, Any], expected_vids: list[str]
) -> tuple[bool, str, list[str]]:
    rows = payload_video_details(payload)
    seen_vids = [normalize_str(dict_get(row, "vid")) for row in rows]
    diagnostics = payload_batch_diagnostics(payload)
    checks = [
        len(rows) == len(expected_vids),
        all(vid in seen_vids for vid in expected_vids),
        not bool(dict_get(diagnostics, "all_results_empty_shell")),
    ]
    highlights = [
        f"results_count={len(rows)}",
        f"seen_vids={seen_vids}",
        (
            "batch returned at least one non-empty result"
            if not bool(dict_get(diagnostics, "all_results_empty_shell"))
            else "batch collapsed into all-empty-shell results"
        ),
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def validate_multi_cid_direct_batch(
    payload: dict[str, Any], expected_cids: list[str], minimum_rows: int
) -> tuple[bool, str, list[str]]:
    cover = payload_cover_info(payload)
    covers = payload_cover_infos(payload)
    api1_diagnostics = payload_api1_batch_diagnostics(payload)
    rows = payload_video_details(payload)
    diagnostics = payload_batch_diagnostics(payload)
    actual_cid = normalize_str(dict_get(payload, "cid"))
    actual_cids = dict_get(payload, "cids")
    if not isinstance(actual_cids, list):
        actual_cids = split_csv_text(actual_cid)
    cover_video_ids = dict_get(cover, "video_ids") or []
    cover_level_video_ids = [
        vid
        for item in covers
        for vid in (dict_get(item, "video_ids") or [])
        if normalize_str(vid)
    ]
    returned_cover_count = int(dict_get(api1_diagnostics, "returned_cover_count") or 0)
    requested_cid_count = int(dict_get(api1_diagnostics, "requested_cid_count") or 0)
    aggregated_video_ids_count = int(dict_get(api1_diagnostics, "aggregated_video_ids_count") or 0)
    returned_cids = dict_get(api1_diagnostics, "returned_cids") or []
    checks = [
        actual_cids == expected_cids,
        has_value(dict_get(cover, "title")),
        requested_cid_count == len(expected_cids),
        len(covers) == len(expected_cids),
        returned_cover_count == len(covers),
        sorted(normalize_str(cid) for cid in returned_cids if normalize_str(cid)) == sorted(expected_cids),
        all(has_value(dict_get(item, "cid")) and has_value(dict_get(item, "title")) for item in covers),
        len(cover_level_video_ids) >= minimum_rows,
        len(rows) >= minimum_rows,
        len(rows) == len(cover_level_video_ids),
        aggregated_video_ids_count == len(cover_level_video_ids),
        not bool(dict_get(diagnostics, "all_results_empty_shell")),
    ]
    highlights = [
        f"cid={actual_cid or '-'}",
        f"cids={actual_cids}",
        f"cover_title={normalize_str(dict_get(cover, 'title')) or '-'}",
        f"requested_cid_count={requested_cid_count}",
        f"cover_infos_count={len(covers)}",
        f"returned_cover_count={returned_cover_count}",
        f"returned_cids={returned_cids}",
        f"cover_video_ids_count={len(cover_video_ids) if isinstance(cover_video_ids, list) else 0}",
        f"aggregated_video_ids_count={aggregated_video_ids_count}",
        f"results_count={len(rows)}",
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def validate_union_platform_override(
    payload: dict[str, Any], expected_union_platform: str
) -> tuple[bool, str, list[str]]:
    row = first_row(payload)
    api2_params = payload_api2_params(payload)
    actual_union_platform = normalize_str(dict_get(api2_params, "union_platform", "UnionPlatform"))
    checks = [
        actual_union_platform == expected_union_platform,
        normalize_str(dict_get(row, "retcode")) == "0",
        not bool(dict_get(row, "empty_shell")),
        row_has_fuller_detail(row),
    ]
    highlights = [
        f"api2 union_platform={actual_union_platform or '-'}",
        f"first retcode={normalize_str(dict_get(row, 'retcode')) or '-'}",
        (
            "explicit union_platform override still returned a fuller canonical row"
            if row_has_fuller_detail(row)
            else "explicit union_platform override did not return a fuller canonical row"
        ),
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def validate_all_invalid_jsonp(payload: dict[str, Any]) -> tuple[bool, str, list[str]]:
    diagnostics = payload_batch_diagnostics(payload)
    rows = payload_video_details(payload)
    checks = [
        len(rows) >= 1,
        bool(dict_get(diagnostics, "all_results_empty_shell")),
        int(dict_get(diagnostics, "empty_shell_count") or 0) == len(rows),
    ]
    highlights = [
        f"results_count={len(rows)}",
        f"empty_shell_count={int(dict_get(diagnostics, 'empty_shell_count') or 0)}",
        (
            "caller-side diagnostics recognized top-level success + all-empty-shell batch"
            if bool(dict_get(diagnostics, "all_results_empty_shell"))
            else "caller-side diagnostics did not recognize the all-empty-shell batch"
        ),
    ]
    return all(checks), "success" if all(checks) else "failure", highlights


def python_command(*args: str, python_bin: str) -> list[str]:
    return [python_bin, str(PYTHON_DEMO), *args]


def powershell_quote(arg: str) -> str:
    return "'" + str(arg).replace("'", "''") + "'"


def go_command(*args: str, go_bin: str) -> list[str]:
    if go_bin == "go":
        ps_command = " ".join(
            [
                "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;",
                "go",
                "run",
                ".\\examples\\go\\main.go",
                *(powershell_quote(arg) for arg in args),
            ]
        )
        return ["powershell", "-NoProfile", "-Command", ps_command]
    return [go_bin, *args]


def build_surface_specs(args: argparse.Namespace) -> OrderedDict[str, dict[str, Any]]:
    return OrderedDict(
        (
            (
                "python_url_canonical_chain",
                {
                    "demo": "python",
                    "command": python_command(
                        "--url",
                        "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_url_chain(payload, "mzc00200idzf2m8"),
                    "intent": "Canonical URL -> CID -> API1 -> API2 XML fuller-detail path.",
                },
            ),
            (
                "go_url_canonical_chain",
                {
                    "demo": "go",
                    "command": go_command(
                        "-url",
                        "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_url_chain(payload, "mzc00200idzf2m8"),
                    "intent": "Canonical URL -> CID -> API1 -> API2 XML fuller-detail path.",
                },
            ),
            (
                "python_canonical_cid_chain_xml",
                {
                    "demo": "python",
                    "command": python_command("--cid", "mzc00200idzf2m8", "--json", python_bin=args.python_bin),
                    "validator": validate_canonical_chain,
                    "intent": "Canonical API1 CID -> API2 XML fuller-detail path.",
                },
            ),
            (
                "go_canonical_cid_chain_xml",
                {
                    "demo": "go",
                    "command": go_command("-cid", "mzc00200idzf2m8", "-json", go_bin=args.go_bin),
                    "validator": validate_canonical_chain,
                    "intent": "Canonical API1 CID -> API2 XML fuller-detail path.",
                },
            ),
            (
                "python_api1_multi_cid_direct_batch",
                {
                    "demo": "python",
                    "command": python_command(
                        "--cid",
                        "mzc00200idzf2m8,mzc00200xxpsogl",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_multi_cid_direct_batch(
                        payload, ["mzc00200idzf2m8", "mzc00200xxpsogl"], 2
                    ),
                    "intent": "Direct multi-CID demo path that expands into a multi-cover API2 batch.",
                },
            ),
            (
                "go_api1_multi_cid_direct_batch",
                {
                    "demo": "go",
                    "command": go_command(
                        "-cid",
                        "mzc00200idzf2m8,mzc00200xxpsogl",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_multi_cid_direct_batch(
                        payload, ["mzc00200idzf2m8", "mzc00200xxpsogl"], 2
                    ),
                    "intent": "Direct multi-CID demo path that expands into a multi-cover API2 batch.",
                },
            ),
            (
                "python_api1_tid537_probe_shell",
                {
                    "demo": "python",
                    "command": python_command(
                        "--cid",
                        "mzc00200idzf2m8",
                        "--api1-tid",
                        "537",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_api1_tid537_probe(payload, "mzc00200idzf2m8"),
                    "intent": "API1 tid=537 success-shell probe on a public CID.",
                },
            ),
            (
                "python_api1_tid453_cover_shell_only",
                {
                    "demo": "python",
                    "command": python_command(
                        "--cid",
                        "mzc00200idzf2m8",
                        "--api1-tid",
                        "453",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_api1_tid453_cover_shell(payload, "mzc00200idzf2m8"),
                    "intent": "API1 tid=453 positive cover-shell-only branch on a public CID.",
                },
            ),
            (
                "go_api1_tid537_probe_shell",
                {
                    "demo": "go",
                    "command": go_command(
                        "-cid",
                        "mzc00200idzf2m8",
                        "-api1-tid",
                        "537",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_api1_tid537_probe(payload, "mzc00200idzf2m8"),
                    "intent": "API1 tid=537 success-shell probe on a public CID.",
                },
            ),
            (
                "go_api1_tid453_cover_shell_only",
                {
                    "demo": "go",
                    "command": go_command(
                        "-cid",
                        "mzc00200idzf2m8",
                        "-api1-tid",
                        "453",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_api1_tid453_cover_shell(payload, "mzc00200idzf2m8"),
                    "intent": "API1 tid=453 positive cover-shell-only branch on a public CID.",
                },
            ),
            (
                "python_jsonp_callback_override",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--api2-otype",
                        "json",
                        "--api2-callback",
                        "cb1",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_jsonp_callback(payload, "cb1"),
                    "intent": "JSONP wrapper override path with a known public video.",
                },
            ),
            (
                "go_jsonp_callback_override",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4",
                        "-api2-otype",
                        "json",
                        "-api2-callback",
                        "cb1",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_jsonp_callback(payload, "cb1"),
                    "intent": "JSONP wrapper override path with a known public video.",
                },
            ),
            (
                "python_api2_alt_positive_tid_488",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--api2-tid",
                        "488",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": validate_api2_tid488_thin_positive_shell,
                    "intent": "Alternate positive tid 488 thin shell on a public sample.",
                },
            ),
            (
                "go_api2_alt_positive_tid_488",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4",
                        "-api2-tid",
                        "488",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": validate_api2_tid488_thin_positive_shell,
                    "intent": "Alternate positive tid 488 thin shell on a public sample.",
                },
            ),
            (
                "python_api2_alt_positive_tid_502",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "j4101ouc4ve",
                        "--api2-tid",
                        "502",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": validate_api2_tid502_richer_positive_shell,
                    "intent": "Alternate positive tid 502 richer shell on a public sample.",
                },
            ),
            (
                "go_api2_alt_positive_tid_502",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "j4101ouc4ve",
                        "-api2-tid",
                        "502",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": validate_api2_tid502_richer_positive_shell,
                    "intent": "Alternate positive tid 502 richer shell on a public sample.",
                },
            ),
            (
                "python_api2_alt_positive_tid_540",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--api2-tid",
                        "540",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid(payload, "540"),
                    "intent": "Alternate positive tid 540 shell on a public sample.",
                },
            ),
            (
                "go_api2_alt_positive_tid_540",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4",
                        "-api2-tid",
                        "540",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid(payload, "540"),
                    "intent": "Alternate positive tid 540 shell on a public sample.",
                },
            ),
            (
                "python_api2_alt_positive_tid_541",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "j4101ouc4ve",
                        "--api2-tid",
                        "541",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid(payload, "541"),
                    "intent": "Alternate positive tid 541 shell on a public sample.",
                },
            ),
            (
                "go_api2_alt_positive_tid_541",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "j4101ouc4ve",
                        "-api2-tid",
                        "541",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid(payload, "541"),
                    "intent": "Alternate positive tid 541 shell on a public sample.",
                },
            ),
            (
                "python_api2_tid541_union0003_spotcheck",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--api2-tid",
                        "541",
                        "--api2-union-platform",
                        "0003",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid_union_platform(
                        payload, "541", "0003"
                    ),
                    "intent": "Alternate tid=541 positive shell with explicit union_platform=0003.",
                },
            ),
            (
                "go_api2_tid541_union0003_spotcheck",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4",
                        "-api2-tid",
                        "541",
                        "-api2-union-platform",
                        "0003",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_alt_positive_tid_union_platform(
                        payload, "541", "0003"
                    ),
                    "intent": "Alternate tid=541 positive shell with explicit union_platform=0003.",
                },
            ),
            (
                "python_api2_batch_lookup_xml",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--vid",
                        "j4101ouc4ve",
                        "--api2-batch-size",
                        "2",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_batch_lookup(
                        payload, ["z4102qfi0x4", "j4101ouc4ve"]
                    ),
                    "intent": "Canonical XML batch lookup on two public videos.",
                },
            ),
            (
                "go_api2_batch_lookup_xml",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4,j4101ouc4ve",
                        "-api2-batch-size",
                        "2",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_batch_lookup(
                        payload, ["z4102qfi0x4", "j4101ouc4ve"]
                    ),
                    "intent": "Canonical XML batch lookup on two public videos.",
                },
            ),
            (
                "python_api2_batch_size_override",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--vid",
                        "j4101ouc4ve",
                        "--api2-batch-size",
                        "1",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_batch_lookup(
                        payload, ["z4102qfi0x4", "j4101ouc4ve"]
                    ),
                    "intent": "Canonical API2 path with explicit batch-size=1 on a two-VID input.",
                },
            ),
            (
                "go_api2_batch_size_override",
                {
                    "demo": "go",
                    "command": go_command(
                        "-cid",
                        "mzc00200idzf2m8,mzc00200xxpsogl",
                        "-api2-batch-size",
                        "1",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_multi_cid_direct_batch(
                        payload, ["mzc00200idzf2m8", "mzc00200xxpsogl"], 2
                    ),
                    "intent": "Direct multi-CID path with explicit API2 batch-size=1 and non-empty multi-row output.",
                },
            ),
            (
                "python_api2_union_platform_override",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "z4102qfi0x4",
                        "--api2-union-platform",
                        "999",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": lambda payload: validate_union_platform_override(payload, "999"),
                    "intent": "Canonical API2 path with explicit union_platform override on a public sample.",
                },
            ),
            (
                "go_api2_union_platform_override",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "z4102qfi0x4",
                        "-api2-union-platform",
                        "999",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": lambda payload: validate_union_platform_override(payload, "999"),
                    "intent": "Canonical API2 path with explicit union_platform override on a public sample.",
                },
            ),
            (
                "python_api2_all_invalid_jsonp_batch",
                {
                    "demo": "python",
                    "command": python_command(
                        "--vid",
                        "zzzzzzzzzzz",
                        "--vid",
                        "yyyyyyyyyyy",
                        "--api2-otype",
                        "json",
                        "--api2-batch-size",
                        "2",
                        "--json",
                        python_bin=args.python_bin,
                    ),
                    "validator": validate_all_invalid_jsonp,
                    "intent": "All-invalid JSONP batch consumer-rule path.",
                },
            ),
            (
                "go_api2_all_invalid_jsonp_batch",
                {
                    "demo": "go",
                    "command": go_command(
                        "-vids",
                        "zzzzzzzzzzz,yyyyyyyyyyy",
                        "-api2-otype",
                        "json",
                        "-api2-batch-size",
                        "2",
                        "-json",
                        go_bin=args.go_bin,
                    ),
                    "validator": validate_all_invalid_jsonp,
                    "intent": "All-invalid JSONP batch consumer-rule path.",
                },
            ),
        )
    )


def select_surfaces(
    args: argparse.Namespace, specs: OrderedDict[str, dict[str, Any]]
) -> OrderedDict[str, dict[str, Any]]:
    selected_ids = list(specs.keys())
    if args.demo != "both":
        selected_ids = [surface_id for surface_id in selected_ids if surface_id.startswith(args.demo)]
    if args.surfaces:
        requested = []
        for raw in args.surfaces:
            requested.extend([part.strip() for part in raw.split(",") if part.strip()])
        unknown = [surface_id for surface_id in requested if surface_id not in specs]
        if unknown:
            raise SystemExit(f"unknown surface ids: {', '.join(unknown)}")
        selected_ids = [surface_id for surface_id in requested if surface_id in selected_ids]
    return OrderedDict((surface_id, specs[surface_id]) for surface_id in selected_ids)


def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=env,
    )


def looks_transient_failure(result_kind: str, stderr_text: str, stdout_text: str) -> bool:
    if result_kind == "timeout":
        return True
    haystack = f"{stderr_text}\n{stdout_text}".lower()
    return any(marker in haystack for marker in TRANSIENT_ERROR_MARKERS)


def evaluate_attempt(
    command: list[str], timeout: int
) -> tuple[str, OrderedDict[str, Any], dict[str, Any] | None]:
    try:
        completed = run_command(command, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        entry = OrderedDict(
            (
                ("result", "timeout"),
                ("timeout_seconds", timeout),
                ("stdout_excerpt", (exc.stdout or "")[:600]),
                ("stderr_excerpt", (exc.stderr or "")[:600]),
            )
        )
        return "timeout", entry, None

    entry = OrderedDict(
        (
            ("exit_code", completed.returncode),
            ("stderr_excerpt", completed.stderr[:600]),
        )
    )
    if completed.returncode != 0:
        entry["result"] = "command_failed"
        entry["stdout_excerpt"] = completed.stdout[:600]
        return "command_failed", entry, None

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        entry["result"] = "invalid_json_output"
        entry["stdout_excerpt"] = completed.stdout[:600]
        entry["json_error"] = str(exc)
        return "invalid_json_output", entry, None

    return "success", entry, payload


def evaluate_surface(
    surface_id: str, spec: dict[str, Any], timeout: int, retries: int
) -> OrderedDict[str, Any]:
    command = [str(part) for part in spec["command"]]
    entry = OrderedDict(
        (
            ("surface", surface_id),
            ("demo", spec["demo"]),
            ("intent", spec["intent"]),
            ("command", command),
        )
    )
    attempts: list[OrderedDict[str, Any]] = []
    max_attempts = max(1, retries)
    payload: dict[str, Any] | None = None
    final_kind = "failure"
    for attempt_index in range(1, max_attempts + 1):
        attempt_kind, attempt_entry, payload = evaluate_attempt(command, timeout)
        attempt_entry["attempt"] = attempt_index
        attempts.append(attempt_entry)
        final_kind = attempt_kind
        if attempt_kind == "success":
            break
        if attempt_kind in ("invalid_json_output",):
            break
        stderr_text = normalize_str(attempt_entry.get("stderr_excerpt"))
        stdout_text = normalize_str(attempt_entry.get("stdout_excerpt"))
        if attempt_index >= max_attempts or not looks_transient_failure(attempt_kind, stderr_text, stdout_text):
            break

    entry["attempt_count"] = len(attempts)
    entry["attempts"] = attempts
    final_attempt = attempts[-1]
    for key, value in final_attempt.items():
        if key == "attempt":
            continue
        entry[key] = value
    if payload is None:
        return entry

    entry["payload_summary"] = summarize_payload(payload)
    ok, result, highlights = spec["validator"](payload)
    entry["result"] = result
    entry["ok"] = ok
    entry["highlights"] = highlights
    return entry


def build_report(
    args: argparse.Namespace, selected: OrderedDict[str, dict[str, Any]]
) -> OrderedDict[str, Any]:
    results = [
        evaluate_surface(surface_id, spec, args.timeout, args.retries)
        for surface_id, spec in selected.items()
    ]
    failures = [
        result["surface"]
        for result in results
        if result.get("ok") is False or result["result"] in ("command_failed", "invalid_json_output", "timeout")
    ]
    report = OrderedDict(
        (
            ("generated_at", datetime.now().isoformat(timespec="seconds")),
            ("runner_script", str(Path(__file__).resolve())),
            ("runner_go_execution_mode", "powershell_wrapped_toolchain_go_run_when_go_bin_is_go"),
            (
                "scope",
                "Rerunnable validation summary for the repository's Python and Go direct-call demo surfaces.",
            ),
            (
                "runner_inputs",
                OrderedDict(
                    (
                        ("selected_surfaces", list(selected.keys())),
                        ("demo_filter", args.demo),
                        ("python_bin", args.python_bin),
                        ("go_bin", args.go_bin),
                        ("timeout_seconds", args.timeout),
                        ("retries", args.retries),
                    )
                ),
            ),
            ("results", results),
            ("failed_surfaces", failures),
            (
                "current_reading",
                [
                    "This runner is scoped to anonymous direct-call demo surfaces that already have documented evidence in the repository.",
                    "A passing rerun strengthens example replayability, but it does not close aged-cookie or login-state gaps by itself.",
                    "Alternate positive tid 488/502/540/541 should still be read as positive shells, not as field-equivalent replacements for canonical tid=535.",
                    "Within that alternate family, tid=502 currently sits on a richer shell than tid=488/540/541, but still below canonical 535 detail fullness.",
                ],
            ),
        )
    )
    return report


def write_output(report: OrderedDict[str, Any], output: str | None, indent: int) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=indent) + "\n"
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


def main() -> None:
    args = parse_args()
    specs = build_surface_specs(args)
    selected = select_surfaces(args, specs)
    report = build_report(args, selected)
    write_output(report, args.output, args.indent)
    if args.strict and report["failed_surfaces"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
