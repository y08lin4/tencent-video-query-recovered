from __future__ import annotations

import argparse
from collections import OrderedDict
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

import tencent_api_contract_probe as contract
import tencent_video_field_survey as survey


BASE_ENVIRONMENTS: OrderedDict[str, dict[str, str]] = OrderedDict(
    (
        (
            "pc_web_ua",
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
            },
        ),
        (
            "mobile_h5_ua",
            {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept": "*/*",
            },
        ),
        (
            "minimal_headers",
            {},
        ),
        (
            "referer_origin",
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Referer": "https://v.qq.com/",
                "Origin": "https://v.qq.com",
            },
        ),
    )
)
BROWSER_LIKE_ENVIRONMENTS: OrderedDict[str, dict[str, str]] = OrderedDict(
    (
        (
            "pc_web_browser_like",
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://v.qq.com/",
                "Sec-CH-UA": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            },
        ),
        (
            "pc_web_browser_like_cookie",
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": (
                    "pgv_pvid=blackboxprobe123456; "
                    "video_guid=blackboxprobe123456; "
                    "_qpsvr_localtk=0.123456789"
                ),
                "Referer": "https://v.qq.com/",
                "Sec-CH-UA": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            },
        ),
        (
            "mobile_h5_browser_like",
            {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://v.qq.com/",
                "Sec-CH-UA": '"Mobile Safari";v="18", "Safari";v="18", "Not/A)Brand";v="24"',
                "Sec-CH-UA-Mobile": "?1",
                "Sec-CH-UA-Platform": '"iOS"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            },
        ),
        (
            "mobile_h5_browser_like_cookie",
            {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": (
                    "pgv_pvid=blackboxprobe654321; "
                    "video_guid=blackboxprobe654321; "
                    "_qpsvr_localtk=0.987654321"
                ),
                "Referer": "https://v.qq.com/",
                "Sec-CH-UA": '"Mobile Safari";v="18", "Safari";v="18", "Not/A)Brand";v="24"',
                "Sec-CH-UA-Mobile": "?1",
                "Sec-CH-UA-Platform": '"iOS"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            },
        ),
    )
)
# Backward-compatible alias for callers that still import the original name.
ENVIRONMENTS = BASE_ENVIRONMENTS
VID_PATTERN = re.compile(r"/cover/[^/]+/([^/]+)\.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a same-day Tencent Video environment matrix across API1/API2 "
            "contract cases and representative page field shapes."
        )
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="API2 batch size for representative field surveys",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=1,
        help="Retries for representative field surveys",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.5,
        help="Base sleep between survey retries",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation",
    )
    parser.add_argument(
        "--include-browser-like",
        action="store_true",
        help="Include sec-ch-ua / sec-fetch-* / synthetic-cookie browser-like environments",
    )
    parser.add_argument(
        "--extra-env-json",
        help=(
            "Optional JSON file containing additional replay environments. "
            "Format: {\"env_name\": {\"Header-Name\": \"value\", ...}, ...}"
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional output file path; when omitted, write JSON to stdout",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.batch_size <= 0 or args.batch_size > 32:
        parser.error("--batch-size must be between 1 and 32")
    if args.http_retries < 0:
        parser.error("--http-retries must be greater than or equal to 0")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep must be greater than or equal to 0")
    return args


def load_extra_environments(path: str | None) -> OrderedDict[str, dict[str, str]]:
    extra: OrderedDict[str, dict[str, str]] = OrderedDict()
    if not path:
        return extra
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("--extra-env-json must be a JSON object mapping env names to header objects")
    for env_name, headers in raw.items():
        if not isinstance(env_name, str) or not env_name.strip():
            raise ValueError("extra environment names must be non-empty strings")
        if not isinstance(headers, dict):
            raise ValueError(f"extra environment '{env_name}' must map to a JSON object of headers")
        normalized_headers: dict[str, str] = {}
        for key, value in headers.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"extra environment '{env_name}' contains an invalid header name")
            normalized_headers[key] = str(value)
        extra[env_name] = normalized_headers
    return extra


def build_environments(
    include_browser_like: bool,
    extra_env_json: str | None = None,
    extra_environments: OrderedDict[str, dict[str, str]] | None = None,
) -> OrderedDict[str, dict[str, str]]:
    environments = OrderedDict(BASE_ENVIRONMENTS)
    if include_browser_like:
        environments.update(BROWSER_LIKE_ENVIRONMENTS)
    environments.update(extra_environments if extra_environments is not None else load_extra_environments(extra_env_json))
    return environments


def build_duplicate_list(value: str, count: int) -> str:
    return ",".join(value for _ in range(count))


def build_case_sets() -> tuple[list[tuple[str, OrderedDict[str, str | None]]], list[tuple[str, OrderedDict[str, str | None]]]]:
    api1 = contract.API_1_DEFAULTS.copy()
    api2 = contract.API_2_DEFAULTS.copy()
    api1_cases = [
        ("baseline_single_valid", api1.copy()),
        ("missing_tid", contract.override(api1, tid=None)),
        ("missing_appid", contract.override(api1, appid=None)),
        ("appid_99999", contract.override(api1, appid="99999")),
        ("canonical_appid_missing_appkey", contract.override(api1, appkey=None)),
        ("empty_shape_plus_valid", contract.override(api1, idlist=f"mzc00000zzzzzzz,{api1['idlist']}")),
        ("mixed_valid_illegal_cid", contract.override(api1, idlist=f"invalidcid123,{api1['idlist']}")),
        ("duplicate_and_empty_slots", contract.override(api1, idlist=f",{api1['idlist']},,{api1['idlist']},mzc00200xxpsogl,")),
        ("dup32", contract.override(api1, idlist=build_duplicate_list(str(api1["idlist"]), 32))),
        ("dup33", contract.override(api1, idlist=build_duplicate_list(str(api1["idlist"]), 33))),
    ]
    api2_cases = [
        ("baseline_xml_single", api2.copy()),
        ("otype_json_single", contract.override(api2, otype="json")),
        ("otype_json_upper", contract.override(api2, otype="JSON")),
        ("otype_missing", contract.override(api2, otype=None)),
        ("otype_text", contract.override(api2, otype="text")),
        ("missing_tid", contract.override(api2, tid=None)),
        ("tid_536", contract.override(api2, tid="536")),
        ("tid_431", contract.override(api2, tid="431")),
        ("missing_appid", contract.override(api2, appid=None)),
        ("appid_99999", contract.override(api2, appid="99999")),
        ("canonical_appid_missing_appkey", contract.override(api2, appkey=None)),
        ("union_platform_missing", contract.override(api2, union_platform=None)),
        ("union_platform_999", contract.override(api2, union_platform="999")),
        ("mixed_valid_invalid_vid", contract.override(api2, idlist=f"{api2['idlist']},zzzzzzzzzzz,j4101ouc4ve")),
        ("mixed_valid_invalid_vid_json", contract.override(api2, otype="json", idlist=f"{api2['idlist']},zzzzzzzzzzz,j4101ouc4ve")),
        ("all_invalid_jsonp_batch", contract.override(api2, otype="json", idlist="zzzzzzzzzzz,yyyyyyyyyyy")),
        ("duplicate_and_empty_slots", contract.override(api2, idlist=f",{api2['idlist']},,{api2['idlist']},j4101ouc4ve,")),
        ("duplicate_and_empty_slots_json", contract.override(api2, otype="json", idlist=f",{api2['idlist']},,{api2['idlist']},j4101ouc4ve,")),
        ("dup32", contract.override(api2, idlist=build_duplicate_list(str(api2["idlist"]), 32))),
        ("dup32_json", contract.override(api2, otype="json", idlist=build_duplicate_list(str(api2["idlist"]), 32))),
        ("dup33", contract.override(api2, idlist=build_duplicate_list(str(api2["idlist"]), 33))),
        ("dup33_json", contract.override(api2, otype="json", idlist=build_duplicate_list(str(api2["idlist"]), 33))),
    ]
    return api1_cases, api2_cases


def fetch_with_headers(
    url: str,
    headers: dict[str, str],
    timeout: float,
    http_retries: int,
    retry_sleep: float,
) -> tuple[int | None, str, str, str]:
    last_transport_error = ""
    for attempt in range(http_retries + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, "replace")
                return response.status, response.headers.get("Content-Type", ""), body, ""
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset() or "utf-8"
            body = exc.read().decode(charset, "replace")
            return exc.code, exc.headers.get("Content-Type", ""), body, ""
        except Exception as exc:  # pragma: no cover - network reporting path
            last_transport_error = str(exc)
            if attempt >= http_retries:
                break
            if retry_sleep > 0:
                time.sleep(retry_sleep * (attempt + 1))
    return None, "", "", last_transport_error


def parse_jsonp_summary(body: str) -> OrderedDict[str, Any]:
    summary: OrderedDict[str, Any] = OrderedDict()
    prefix = "QZOutputJson="
    if not body.startswith(prefix):
        summary["parse_error"] = "missing JSONP wrapper"
        return summary
    payload = body[len(prefix):].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        summary["parse_error"] = f"{exc.msg} at position {exc.pos}"
        return summary

    if not isinstance(data, dict):
        summary["parse_error"] = "payload is not a JSON object"
        return summary

    summary["root"] = "QZOutputJson"
    summary["errorno"] = str(data.get("errorno", ""))
    summary["errormsg"] = str(data.get("errormsg", ""))
    results = data.get("results", [])
    if isinstance(results, list):
        summary["results_count"] = len(results)
        sample_results: list[OrderedDict[str, str]] = []
        for result in results[:5]:
            if not isinstance(result, dict):
                continue
            fields = result.get("fields", {})
            row: OrderedDict[str, str] = OrderedDict()
            row["id"] = str(result.get("id", "")).strip()
            row["retcode"] = str(result.get("retcode", "")).strip()
            if isinstance(fields, dict):
                row["vid"] = str(fields.get("vid", "")).strip()
                row["title"] = str(fields.get("title", "")).strip()
                row["state"] = str(fields.get("state", "")).strip()
                row["upload_src"] = str(fields.get("upload_src", "")).strip()
            sample_results.append(row)
        if sample_results:
            summary["sample_results"] = sample_results
    return summary


def build_signature(http_status: int | None, content_type: str, transport_error: str, summary: OrderedDict[str, Any]) -> str:
    normalized = OrderedDict(
        (
            ("http_status", http_status),
            ("content_type", content_type.split(";")[0].strip()),
            ("transport_error", transport_error),
            ("summary", summary),
        )
    )
    return json.dumps(normalized, ensure_ascii=False, sort_keys=False)


def run_case_set(
    api: str,
    cases: list[tuple[str, OrderedDict[str, str | None]]],
    timeout: float,
    environments: OrderedDict[str, dict[str, str]],
    http_retries: int,
    retry_sleep: float,
) -> OrderedDict[str, Any]:
    base_url = contract.API_1_URL if api == "api1" else contract.API_2_URL
    grouped: OrderedDict[str, Any] = OrderedDict()
    for case_name, params in cases:
        per_env: OrderedDict[str, Any] = OrderedDict()
        signatures: list[str] = []
        for env_name, headers in environments.items():
            url = contract.build_url(base_url, params)
            status, content_type, body, transport_error = fetch_with_headers(
                url,
                headers,
                timeout,
                http_retries=http_retries,
                retry_sleep=retry_sleep,
            )
            if body.startswith("QZOutputJson="):
                summary = parse_jsonp_summary(body)
            else:
                summary = contract.parse_xml_summary(body, api) if body else OrderedDict()
            signature = build_signature(status, content_type, transport_error, summary)
            signatures.append(signature)
            per_env[env_name] = OrderedDict(
                (
                    ("http_status", status),
                    ("content_type", content_type),
                    ("transport_error", transport_error),
                    ("summary", summary),
                )
            )

        grouped[case_name] = OrderedDict(
            (
                ("params", params),
                ("unique_signature_count", len(set(signatures))),
                ("environments", per_env),
            )
        )
    return grouped


def extract_field_drift_summary(sample: OrderedDict[str, Any]) -> OrderedDict[str, Any]:
    derived = sample.get("derived", {})
    cover = derived.get("cover", {}) if isinstance(derived, dict) else {}
    videos = derived.get("videos", {}) if isinstance(derived, dict) else {}
    selection = select_representative_video_row(sample)
    fields = selection["fields"]
    sample_status = str(sample.get("status", "")).strip() or "unknown"
    sample_error = str(sample.get("error", "")).strip()
    return OrderedDict(
        (
            ("sample_status", sample_status),
            ("sample_error", sample_error),
            ("cover_video_ids_count", cover.get("video_ids_count")),
            ("cover_downright_count", cover.get("downright_count")),
            ("state_counts", videos.get("state_counts", {})),
            ("upload_src_counts", videos.get("upload_src_counts", {})),
            ("publish_date_nonempty_count", videos.get("publish_date_nonempty_count")),
            ("targetid_nonempty_count", videos.get("targetid_nonempty_count")),
            ("selected_row_vid", selection["selected_row_vid"]),
            ("selected_row_source", selection["selected_row_source"]),
            ("selected_row_cover_list", fields.get("cover_list", [])),
            ("selected_row_category_map", fields.get("category_map", [])),
        )
    )


def extract_vid_from_url(url: str) -> str:
    match = VID_PATTERN.search(url)
    return match.group(1) if match else ""


def row_vid(video_row: dict[str, Any]) -> str:
    vid = str(video_row.get("vid", "")).strip()
    if vid:
        return vid
    fields = video_row.get("fields", {})
    if isinstance(fields, dict):
        return str(fields.get("vid", "")).strip()
    return ""


def normalize_row_fields(video_row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(video_row, dict):
        return {}
    fields = video_row.get("fields", {})
    return fields if isinstance(fields, dict) else {}


def select_representative_video_row(sample: OrderedDict[str, Any]) -> dict[str, Any]:
    video_rows = sample.get("videos", [])
    rows = [row for row in video_rows if isinstance(row, dict)] if isinstance(video_rows, list) else []
    requested_vid = extract_vid_from_url(str(sample.get("input_url", "")))
    video_ids = sample.get("video_ids", [])
    preferred_vid = ""
    selection_source = ""
    if requested_vid:
        preferred_vid = requested_vid
        selection_source = "url_vid"
    elif isinstance(video_ids, list) and video_ids:
        preferred_vid = str(video_ids[0]).strip()
        selection_source = "cover_video_ids_first"

    if preferred_vid:
        for row in rows:
            if row_vid(row) == preferred_vid:
                return {
                    "selected_row_vid": preferred_vid,
                    "selected_row_source": selection_source,
                    "fields": normalize_row_fields(row),
                }

    if rows:
        sorted_rows = sorted(rows, key=lambda row: row_vid(row) or "\uffff")
        fallback = sorted_rows[0]
        fallback_vid = row_vid(fallback)
        return {
            "selected_row_vid": fallback_vid,
            "selected_row_source": "sorted_vid_fallback",
            "fields": normalize_row_fields(fallback),
        }

    return {
        "selected_row_vid": "",
        "selected_row_source": "no_video_rows",
        "fields": {},
    }


def run_representative_field_diff(args: argparse.Namespace) -> OrderedDict[str, Any]:
    urls = OrderedDict(
        (
            ("film_single", "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html"),
            ("anime_season", "https://v.qq.com/x/cover/mzc00200xxpsogl/j4101ouc4ve.html"),
            ("variety_topic", "https://v.qq.com/x/cover/mzc002001u873es.html"),
            ("sports_replay", "https://v.qq.com/x/cover/mzc002003u0t3rl.html"),
            ("kids_free_pack", "https://v.qq.com/x/cover/mzc00200tuupfc2.html"),
        )
    )

    extra_environments = load_extra_environments(args.extra_env_json)
    environments = build_environments(
        args.include_browser_like,
        args.extra_env_json,
        extra_environments=extra_environments,
    )
    original_headers = survey.REQUEST_HEADERS.copy()
    try:
        report: OrderedDict[str, Any] = OrderedDict()
        for bucket, url in urls.items():
            per_env: OrderedDict[str, Any] = OrderedDict()
            signatures: list[str] = []
            for env_name, headers in environments.items():
                survey.REQUEST_HEADERS.clear()
                survey.REQUEST_HEADERS.update(headers)
                sample = survey.survey_sample(
                    url,
                    timeout=args.timeout,
                    batch_size=args.batch_size,
                    http_retries=args.http_retries,
                    retry_sleep=args.retry_sleep,
                    clip_sample_head=0,
                    clip_sample_tail=0,
                )
                summary = extract_field_drift_summary(sample)
                signatures.append(json.dumps(summary, ensure_ascii=False, sort_keys=False))
                per_env[env_name] = summary
            report[bucket] = OrderedDict(
                (
                    ("url", url),
                    ("unique_signature_count", len(set(signatures))),
                    ("environments", per_env),
                )
            )
        return report
    finally:
        survey.REQUEST_HEADERS.clear()
        survey.REQUEST_HEADERS.update(original_headers)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - older Python compatibility
        pass
    args = parse_args()
    extra_environments = load_extra_environments(args.extra_env_json)
    environments = build_environments(
        args.include_browser_like,
        args.extra_env_json,
        extra_environments=extra_environments,
    )
    api1_cases, api2_cases = build_case_sets()
    report = OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("tool", "tencent_environment_matrix_probe"),
                        ("timeout_seconds", args.timeout),
                        ("http_retries", args.http_retries),
                        ("retry_sleep_seconds", args.retry_sleep),
                        ("environments", list(environments.keys())),
                        ("include_browser_like", args.include_browser_like),
                        ("extra_env_json", args.extra_env_json or ""),
                        ("extra_environment_names", list(extra_environments.keys())),
                    )
                ),
            ),
            (
                "api1_contract_matrix",
                run_case_set(
                    "api1",
                    api1_cases,
                    timeout=args.timeout,
                    environments=environments,
                    http_retries=args.http_retries,
                    retry_sleep=args.retry_sleep,
                ),
            ),
            (
                "api2_contract_matrix",
                run_case_set(
                    "api2",
                    api2_cases,
                    timeout=args.timeout,
                    environments=environments,
                    http_retries=args.http_retries,
                    retry_sleep=args.retry_sleep,
                ),
            ),
            ("representative_field_diff", run_representative_field_diff(args)),
        )
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=args.indent)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
