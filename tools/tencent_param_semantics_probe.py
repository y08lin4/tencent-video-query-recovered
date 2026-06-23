from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
import re
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


API_1_URL = "https://data.video.qq.com/fcgi-bin/data"
API_2_URL = "https://union.video.qq.com/fcgi-bin/data"
DEFAULT_API1_TID = "431"
DEFAULT_API1_IDLIST = "mzc00200idzf2m8"
DEFAULT_API1_ALT_VALID_IDLIST = "mzc00200xxpsogl"
DEFAULT_API1_INVALID_IDLIST = "invalidcid123"
DEFAULT_API2_TID = "535"
DEFAULT_API2_IDLIST = "z4102qfi0x4"
DEFAULT_API2_ALT_VALID_IDLIST = "j4101ouc4ve"
DEFAULT_API2_INVALID_IDLIST = "zzzzzzzzzzz"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}
DEFAULT_CALLBACK_CASE_VALUES = OrderedDict(
    (
        ("extra_callback_json", "1"),
        ("extra_callback_cb1_json", "cb1"),
        ("extra_callback_qzoutputjson_json", "QZOutputJson"),
        ("extra_callback_foo_dot_bar_json", "foo.bar"),
        ("extra_callback_empty_json", ""),
        ("extra_callback_a_dash_b_json", "a-b"),
        ("extra_callback_a_bracket_b_json", "a[b]"),
        ("extra_callback_dollar_cb_json", "$cb"),
        ("extra_callback_foo_space_bar_json", "foo bar"),
        ("extra_callback_foo_comma_bar_json", "foo,bar"),
        ("extra_callback_bracket_zero_json", "[0]"),
        ("extra_callback_chinese_json", "中文"),
        ("extra_callback_a_open_paren_json", "a("),
        ("extra_callback_double_open_paren_json", "(("),
        ("extra_callback_close_paren_only_json", ")"),
        ("extra_callback_a_close_paren_json", "a)"),
        ("extra_callback_comment_prefix_json", "/*a"),
        ("extra_callback_a_semicolon_b_json", "a;b"),
        ("extra_callback_a_single_quote_b_json", "a'b"),
        ("extra_callback_a_double_quote_b_json", "a\"b"),
        ("extra_callback_a_slash_json", "a/"),
        ("extra_callback_a_backslash_json", "a\\"),
        ("extra_callback_double_slash_a_json", "//a"),
    )
)
RESERVED_EXTRA_KEY_VALUES = OrderedDict(
    (
        ("format", "json"),
        ("output", "json"),
        ("version", "1"),
        ("v", "1"),
        ("platform", "3"),
        ("source", "1"),
    )
)
AUTHISH_EXTRA_KEY_VALUES = OrderedDict(
    (
        ("token", "deadbeef"),
        ("sign", "deadbeef"),
        ("sig", "deadbeef"),
        ("appver", "1.0.0"),
        ("access_token", "deadbeef"),
        ("authkey", "deadbeef"),
        ("openid", "1"),
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Tencent Video query-key semantics: extra keys and repeated keys."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=2,
        help="Retry count for transient transport failures.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation.",
    )
    parser.add_argument(
        "--extra-env-json",
        help=(
            "Optional JSON file containing replay header environments. "
            "Format: {\"env_name\": {\"Header-Name\": \"value\", ...}, ...}"
        ),
    )
    parser.add_argument(
        "--env-name",
        help="Environment name inside --extra-env-json to load into request headers.",
    )
    parser.add_argument(
        "--api1-tid",
        default=DEFAULT_API1_TID,
        help=f"API1 positive tid anchor. Default: {DEFAULT_API1_TID}",
    )
    parser.add_argument(
        "--api1-idlist",
        default=DEFAULT_API1_IDLIST,
        help=f"API1 idlist anchor. Default: {DEFAULT_API1_IDLIST}",
    )
    parser.add_argument(
        "--api2-tid",
        default=DEFAULT_API2_TID,
        help=f"API2 positive tid anchor. Default: {DEFAULT_API2_TID}",
    )
    parser.add_argument(
        "--api2-idlist",
        default=DEFAULT_API2_IDLIST,
        help=f"API2 idlist anchor. Default: {DEFAULT_API2_IDLIST}",
    )
    parser.add_argument(
        "--case-profile",
        choices=("full", "authish", "callback_contract"),
        default="full",
        help=(
            "Case set to run. `authish` keeps only baselines plus auth-ish extra key cases. "
            "`callback_contract` keeps only the minimal API2 JSONP callback precedence/error-shell cases."
        ),
    )
    parser.add_argument(
        "--extra-callback-value",
        action="append",
        default=[],
        help=(
            "Additional API2 JSONP callback value to probe. "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--extra-callback-file",
        help=(
            "Optional UTF-8 text file containing extra callback values, "
            "one raw value per line."
        ),
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


def callback_case_slug(value: str) -> str:
    normalized = re.sub(r"[^0-9a-z]+", "_", value.lower()).strip("_")
    return normalized or "value"


def callback_case_name(value: str, taken: set[str]) -> str:
    base = f"extra_callback_custom_{callback_case_slug(value)}"
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    candidate = f"{base}_{digest}_json"
    if candidate not in taken:
        return candidate
    index = 2
    while True:
        retry = f"{base}_{digest}_{index}_json"
        if retry not in taken:
            return retry
        index += 1


def load_callback_case_values(
    extra_values: list[str] | None = None,
    extra_file: str | None = None,
) -> OrderedDict[str, str]:
    case_values = OrderedDict(DEFAULT_CALLBACK_CASE_VALUES)
    extras: list[str] = []
    if extra_values:
        extras.extend(extra_values)
    if extra_file:
        extras.extend(Path(extra_file).read_text(encoding="utf-8").splitlines())
    taken = set(case_values.keys())
    for value in extras:
        name = callback_case_name(value, taken)
        taken.add(name)
        case_values[name] = value
    return case_values


def load_replay_headers(extra_env_json: str | None, env_name: str | None) -> dict[str, str]:
    if not extra_env_json and not env_name:
        return {}
    if not extra_env_json or not env_name:
        raise ValueError("--extra-env-json and --env-name must be used together")
    raw = json.loads(Path(extra_env_json).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("--extra-env-json must be a JSON object mapping env names to header objects")
    env = raw.get(env_name)
    if not isinstance(env, dict):
        raise ValueError(f"environment '{env_name}' not found in {extra_env_json}")
    headers: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"environment '{env_name}' contains an invalid header name")
        headers[key] = str(value)
    return headers


def http_fetch(url: str, timeout: float, http_retries: int) -> tuple[int | None, str, str, str]:
    last_transport_error = ""
    for attempt in range(http_retries + 1):
        request = urllib.request.Request(url, headers=REQUEST_HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.status, response.headers.get("Content-Type", ""), response.read().decode(charset, "replace"), ""
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset() or "utf-8"
            body = exc.read().decode(charset, "replace")
            return exc.code, exc.headers.get("Content-Type", ""), body, ""
        except Exception as exc:  # pragma: no cover - runtime reporting path
            last_transport_error = str(exc)
            if attempt >= http_retries:
                break
            time.sleep(0.4 * (attempt + 1))
    return None, "", "", last_transport_error


def build_url(base: str, pairs: list[tuple[str, str]]) -> str:
    return f"{base}?{urllib.parse.urlencode(pairs)}"


def parse_xml_summary(body: str) -> OrderedDict[str, object]:
    summary: OrderedDict[str, object] = OrderedDict()
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        summary["parse_error"] = str(exc)
        return summary

    def text(path: str) -> str:
        return (root.findtext(path) or "").strip()

    summary["root_tag"] = root.tag
    summary["errorno"] = text(".//errorno")
    summary["errormsg"] = text(".//errormsg") or text(".//error")
    summary["retcode"] = text(".//retcode")

    sample_results: list[OrderedDict[str, str]] = []
    for result in root.findall(".//results")[:5]:
        row: OrderedDict[str, str] = OrderedDict()
        row["id"] = (result.findtext("./id") or "").strip()
        row["retcode"] = (result.findtext("./retcode") or "").strip()
        row["vid"] = (result.findtext(".//vid") or "").strip()
        row["cover_id"] = (result.findtext(".//cover_id") or "").strip()
        row["title"] = (result.findtext(".//title") or "").strip()
        row["state"] = (result.findtext(".//state") or "").strip()
        row["upload_src"] = (result.findtext(".//upload_src") or "").strip()
        sample_results.append(row)
    if sample_results:
        summary["sample_results"] = sample_results
    return summary


def parse_jsonp_summary(body: str) -> OrderedDict[str, object]:
    summary: OrderedDict[str, object] = OrderedDict()
    stripped = body.strip()
    root_name = ""
    payload = ""
    prefix = "QZOutputJson="
    if stripped.startswith(prefix):
        root_name = "QZOutputJson"
        payload = stripped[len(prefix):].strip()
    else:
        open_paren = stripped.find("(")
        close_paren = stripped.rfind(")")
        if open_paren < 0 or close_paren <= open_paren:
            summary["parse_error"] = "missing JSONP wrapper"
            return summary
        root_name = stripped[:open_paren].strip()
        payload = stripped[open_paren + 1 : close_paren].strip()
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

    summary["root"] = root_name
    summary["errorno"] = str(data.get("errorno", ""))
    summary["errormsg"] = str(data.get("errormsg", ""))

    sample_results: list[OrderedDict[str, str]] = []
    for result in (data.get("results") or [])[:5]:
        if not isinstance(result, dict):
            continue
        fields = result.get("fields") or {}
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


def summarize_response(body: str, content_type: str) -> OrderedDict[str, object]:
    normalized_type = content_type.lower()
    if "javascript" in normalized_type or body.startswith("QZOutputJson="):
        return parse_jsonp_summary(body)
    return parse_xml_summary(body)


def signature(http_status: int | None, content_type: str, transport_error: str, summary: OrderedDict[str, object]) -> str:
    normalized = OrderedDict(
        (
            ("http_status", http_status),
            ("content_type", content_type.split(";")[0].strip()),
            ("transport_error", transport_error),
            ("summary", summary),
        )
    )
    return json.dumps(normalized, ensure_ascii=False, sort_keys=False)


def api1_pairs(tid: str = DEFAULT_API1_TID, idlist: str = DEFAULT_API1_IDLIST) -> list[tuple[str, str]]:
    return [
        ("tid", tid),
        ("idlist", idlist),
        ("appid", "10001005"),
        ("appkey", "0d1a9ddd94de871b"),
    ]


def api2_pairs(
    tid: str = DEFAULT_API2_TID,
    idlist: str = DEFAULT_API2_IDLIST,
    otype: str = "xml",
) -> list[tuple[str, str]]:
    return [
        ("otype", otype),
        ("tid", tid),
        ("appid", "20001238"),
        ("appkey", "6c03bbe9658448a4"),
        ("union_platform", "3"),
        ("idlist", idlist),
    ]


def choose_alt_value(primary: str, preferred_alt: str, fallback: str) -> str:
    return fallback if primary == preferred_alt else preferred_alt


def make_cases(
    api1_tid: str = DEFAULT_API1_TID,
    api1_idlist: str = DEFAULT_API1_IDLIST,
    api2_tid: str = DEFAULT_API2_TID,
    api2_idlist: str = DEFAULT_API2_IDLIST,
    case_profile: str = "full",
    callback_case_values: OrderedDict[str, str] | None = None,
) -> OrderedDict[str, list[tuple[str, str, list[tuple[str, str]]]]]:
    callback_case_values = callback_case_values or OrderedDict(DEFAULT_CALLBACK_CASE_VALUES)
    api1_base = api1_pairs(api1_tid, api1_idlist)
    api2_base = api2_pairs(api2_tid, api2_idlist, "xml")
    api2_json_base = api2_pairs(api2_tid, api2_idlist, "json")
    api1_alt_valid_idlist = choose_alt_value(
        api1_idlist, DEFAULT_API1_ALT_VALID_IDLIST, DEFAULT_API1_IDLIST
    )
    api2_alt_valid_idlist = choose_alt_value(
        api2_idlist, DEFAULT_API2_ALT_VALID_IDLIST, DEFAULT_API2_IDLIST
    )
    api1_reserved_extra_cases = [
        (f"extra_{key}", API_1_URL, api1_base + [(key, value)])
        for key, value in RESERVED_EXTRA_KEY_VALUES.items()
    ]
    api2_reserved_extra_xml_cases = [
        (f"extra_{key}_xml", API_2_URL, api2_base + [(key, value)])
        for key, value in RESERVED_EXTRA_KEY_VALUES.items()
    ]
    api2_reserved_extra_json_cases = [
        (f"extra_{key}_json", API_2_URL, api2_json_base + [(key, value)])
        for key, value in RESERVED_EXTRA_KEY_VALUES.items()
    ]
    api1_authish_extra_cases = [
        (f"extra_{key}", API_1_URL, api1_base + [(key, value)])
        for key, value in AUTHISH_EXTRA_KEY_VALUES.items()
    ]
    api2_authish_extra_xml_cases = [
        (f"extra_{key}_xml", API_2_URL, api2_base + [(key, value)])
        for key, value in AUTHISH_EXTRA_KEY_VALUES.items()
    ]
    api2_authish_extra_json_cases = [
        (f"extra_{key}_json", API_2_URL, api2_json_base + [(key, value)])
        for key, value in AUTHISH_EXTRA_KEY_VALUES.items()
    ]
    api2_callback_cases = [
        (case_name, API_2_URL, api2_json_base + [("callback", value)])
        for case_name, value in callback_case_values.items()
    ]
    api2_json_wrong_appkey = [
        ("otype", "json"),
        ("tid", api2_tid),
        ("appid", "20001238"),
        ("appkey", "deadbeef"),
        ("union_platform", "3"),
        ("idlist", api2_idlist),
    ]
    api2_callback_contract_cases = [
        ("repeat_callback_cb1_then_empty_json", API_2_URL, api2_json_base + [("callback", "cb1"), ("callback", "")]),
        ("repeat_callback_empty_then_cb1_json", API_2_URL, api2_json_base + [("callback", ""), ("callback", "cb1")]),
        ("repeat_callback_cb1_then_a_open_paren_json", API_2_URL, api2_json_base + [("callback", "cb1"), ("callback", "a(")]),
        ("repeat_callback_a_open_paren_then_cb1_json", API_2_URL, api2_json_base + [("callback", "a("), ("callback", "cb1")]),
        ("branch_canonical_wrong_appkey_json", API_2_URL, api2_json_wrong_appkey),
        ("error_callback_cb1_wrong_appkey_json", API_2_URL, api2_json_wrong_appkey + [("callback", "cb1")]),
        ("error_callback_a_open_paren_wrong_appkey_json", API_2_URL, api2_json_wrong_appkey + [("callback", "a(")]),
    ]
    if case_profile == "authish":
        return OrderedDict(
            (
                (
                    "api1",
                    [
                        ("baseline", API_1_URL, api1_base),
                        *api1_authish_extra_cases,
                    ],
                ),
                (
                    "api2",
                    [
                        ("baseline_xml", API_2_URL, api2_base),
                        ("baseline_json", API_2_URL, api2_json_base),
                        *api2_authish_extra_xml_cases,
                        *api2_authish_extra_json_cases,
                    ],
                ),
            )
        )
    if case_profile == "callback_contract":
        return OrderedDict(
            (
                (
                    "api2",
                    [
                        ("baseline_json", API_2_URL, api2_json_base),
                        ("extra_callback_cb1_json", API_2_URL, api2_json_base + [("callback", "cb1")]),
                        ("extra_callback_empty_json", API_2_URL, api2_json_base + [("callback", "")]),
                        ("extra_callback_a_open_paren_json", API_2_URL, api2_json_base + [("callback", "a(")]),
                        *api2_callback_contract_cases,
                    ],
                ),
            )
        )

    return OrderedDict(
        (
            (
                "api1",
                [
                    ("baseline", API_1_URL, api1_base),
                    ("extra_foo", API_1_URL, api1_base + [("foo", "1")]),
                    ("extra_callback", API_1_URL, api1_base + [("callback", "1")]),
                    ("extra_underscore", API_1_URL, api1_base + [("_", "1782000000")]),
                    *api1_reserved_extra_cases,
                    *api1_authish_extra_cases,
                    ("branch_text_appid_wrong_appkey", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "notanumber"), ("appkey", "deadbeef")]),
                    ("branch_canonical_wrong_appkey", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "deadbeef")]),
                    ("repeat_idlist_valid_then_valid", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("idlist", api1_alt_valid_idlist), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_idlist_invalid_then_valid", API_1_URL, [("tid", api1_tid), ("idlist", DEFAULT_API1_INVALID_IDLIST), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_idlist_valid_then_invalid", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("idlist", DEFAULT_API1_INVALID_IDLIST), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_tid_good_then_bad", API_1_URL, [("tid", api1_tid), ("tid", "0"), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_tid_bad_then_good", API_1_URL, [("tid", "0"), ("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_appid_good_then_text", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appid", "notanumber"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_appid_text_then_good", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "notanumber"), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]),
                    ("repeat_appid_canonical_then_text_wrong_appkey", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appid", "notanumber"), ("appkey", "deadbeef")]),
                    ("repeat_appid_text_then_canonical_wrong_appkey", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "notanumber"), ("appid", "10001005"), ("appkey", "deadbeef")]),
                    ("repeat_appkey_good_then_wrong", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b"), ("appkey", "deadbeef")]),
                    ("repeat_appkey_wrong_then_good", API_1_URL, [("tid", api1_tid), ("idlist", api1_idlist), ("appid", "10001005"), ("appkey", "deadbeef"), ("appkey", "0d1a9ddd94de871b")]),
                ],
            ),
            (
                "api2",
                [
                    ("baseline_xml", API_2_URL, api2_base),
                    ("baseline_json", API_2_URL, api2_json_base),
                    ("extra_foo_xml", API_2_URL, api2_base + [("foo", "1")]),
                    ("extra_callback_xml", API_2_URL, api2_base + [("callback", "1")]),
                    ("extra_underscore_xml", API_2_URL, api2_base + [("_", "1782000000")]),
                    ("extra_foo_json", API_2_URL, api2_json_base + [("foo", "1")]),
                    *api2_callback_cases,
                    ("extra_underscore_json", API_2_URL, api2_json_base + [("_", "1782000000")]),
                    *api2_reserved_extra_xml_cases,
                    *api2_reserved_extra_json_cases,
                    *api2_authish_extra_xml_cases,
                    *api2_authish_extra_json_cases,
                    ("branch_text_appid_wrong_appkey", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "notanumber"), ("appkey", "deadbeef"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("branch_canonical_wrong_appkey", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "deadbeef"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_idlist_valid_then_valid", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist), ("idlist", api2_alt_valid_idlist)]),
                    ("repeat_idlist_invalid_then_valid", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", DEFAULT_API2_INVALID_IDLIST), ("idlist", api2_idlist)]),
                    ("repeat_idlist_valid_then_invalid", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist), ("idlist", DEFAULT_API2_INVALID_IDLIST)]),
                    ("repeat_otype_xml_then_json", API_2_URL, [("otype", "xml"), ("otype", "json"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_otype_json_then_xml", API_2_URL, [("otype", "json"), ("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_tid_good_then_536", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("tid", "536"), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_tid_536_then_good", API_2_URL, [("otype", "xml"), ("tid", "536"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_union_platform_good_then_999", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("union_platform", "999"), ("idlist", api2_idlist)]),
                    ("repeat_union_platform_999_then_good", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "999"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_appid_canonical_then_text_wrong_appkey", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appid", "notanumber"), ("appkey", "deadbeef"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_appid_text_then_canonical_wrong_appkey", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "notanumber"), ("appid", "20001238"), ("appkey", "deadbeef"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_appkey_good_then_wrong", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "6c03bbe9658448a4"), ("appkey", "deadbeef"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                    ("repeat_appkey_wrong_then_good", API_2_URL, [("otype", "xml"), ("tid", api2_tid), ("appid", "20001238"), ("appkey", "deadbeef"), ("appkey", "6c03bbe9658448a4"), ("union_platform", "3"), ("idlist", api2_idlist)]),
                ],
            ),
        )
    )


def baseline_key_for(api_name: str, case_name: str) -> str:
    if api_name != "api2":
        if case_name == "repeat_appid_canonical_then_text_wrong_appkey":
            return "branch_canonical_wrong_appkey"
        if case_name == "repeat_appid_text_then_canonical_wrong_appkey":
            return "branch_text_appid_wrong_appkey"
        if case_name == "repeat_appkey_good_then_wrong":
            return "baseline"
        if case_name == "repeat_appkey_wrong_then_good":
            return "branch_canonical_wrong_appkey"
        return "baseline"
    if case_name in {"baseline_xml", "baseline_json"}:
        return case_name
    if (case_name.startswith("extra_callback_") and case_name.endswith("_json")) or case_name == "extra_underscore_json":
        return "baseline_json"
    if case_name == "repeat_appid_canonical_then_text_wrong_appkey":
        return "branch_canonical_wrong_appkey"
    if case_name == "repeat_appid_text_then_canonical_wrong_appkey":
        return "branch_text_appid_wrong_appkey"
    if case_name == "repeat_appkey_good_then_wrong":
        return "baseline_xml"
    if case_name == "repeat_appkey_wrong_then_good":
        return "branch_canonical_wrong_appkey"
    if case_name == "repeat_otype_json_then_xml":
        return "baseline_json"
    if case_name == "repeat_otype_xml_then_json":
        return "baseline_xml"
    if case_name == "repeat_callback_cb1_then_empty_json":
        return "extra_callback_cb1_json"
    if case_name == "repeat_callback_empty_then_cb1_json":
        return "extra_callback_empty_json"
    if case_name == "repeat_callback_cb1_then_a_open_paren_json":
        return "extra_callback_cb1_json"
    if case_name == "repeat_callback_a_open_paren_then_cb1_json":
        return "extra_callback_a_open_paren_json"
    if case_name == "branch_canonical_wrong_appkey_json":
        return "branch_canonical_wrong_appkey_json"
    if case_name == "error_callback_cb1_wrong_appkey_json":
        return "branch_canonical_wrong_appkey_json"
    if case_name == "error_callback_a_open_paren_wrong_appkey_json":
        return "branch_canonical_wrong_appkey_json"
    if case_name.endswith("_json"):
        return "baseline_json"
    return "baseline_xml"


def secondary_control_key_for(api_name: str, case_name: str) -> str | None:
    if case_name == "repeat_appid_canonical_then_text_wrong_appkey":
        return "branch_text_appid_wrong_appkey"
    if case_name == "repeat_appid_text_then_canonical_wrong_appkey":
        return "branch_canonical_wrong_appkey"
    if api_name == "api1" and case_name == "repeat_appkey_good_then_wrong":
        return "branch_canonical_wrong_appkey"
    if api_name == "api2" and case_name == "repeat_appkey_good_then_wrong":
        return "branch_canonical_wrong_appkey"
    if api_name == "api1" and case_name == "repeat_appkey_wrong_then_good":
        return "baseline"
    if api_name == "api2" and case_name == "repeat_appkey_wrong_then_good":
        return "baseline_xml"
    if case_name == "repeat_callback_cb1_then_empty_json":
        return "extra_callback_empty_json"
    if case_name == "repeat_callback_empty_then_cb1_json":
        return "extra_callback_cb1_json"
    if case_name == "repeat_callback_cb1_then_a_open_paren_json":
        return "extra_callback_a_open_paren_json"
    if case_name == "repeat_callback_a_open_paren_then_cb1_json":
        return "extra_callback_cb1_json"
    if case_name == "error_callback_cb1_wrong_appkey_json":
        return "extra_callback_cb1_json"
    if case_name == "error_callback_a_open_paren_wrong_appkey_json":
        return "extra_callback_a_open_paren_json"
    return None


def infer_judgment(
    api_name: str,
    case_name: str,
    control_sig: str,
    secondary_control_sig: str,
    sig: str,
    summary: OrderedDict[str, object],
) -> str:
    if case_name.startswith("branch_"):
        return "control_case"
    if sig == control_sig:
        if case_name.startswith("extra_callback_") and case_name.endswith("_json"):
            return "jsonp_callback_value_changes_wrapper_branch"
        if case_name.startswith("repeat_callback_"):
            return "repeated_callback_first_value_wins_in_tested_branch"
        if case_name.startswith("extra_"):
            return "extra_key_ignored_in_tested_branch"
        if "repeat_tid_" in case_name or "repeat_idlist_" in case_name or "repeat_otype_" in case_name:
            return "repeated_key_first_value_wins_in_tested_branch"
        if "repeat_union_platform_" in case_name:
            return "union_platform_ignored_or_repeated_key_no_observed_change"
        if "repeat_appid_" in case_name:
            return "repeated_appid_first_value_wins_in_tested_branch"
        if "repeat_appkey_" in case_name:
            return "repeated_appkey_first_value_wins_in_tested_branch"
        return "repeated_key_no_observed_change_vs_control"
    if secondary_control_sig and sig == secondary_control_sig:
        if case_name.startswith("repeat_callback_"):
            return "repeated_callback_second_value_wins_or_later_wrapper_selected"
        if "repeat_appid_" in case_name:
            return "repeated_appid_second_value_wins_or_later_branch_selected"
        if "repeat_appkey_" in case_name:
            return "repeated_appkey_second_value_wins_or_later_branch_selected"
    if case_name == "repeat_idlist_invalid_then_valid":
        return "repeated_idlist_first_value_wins_in_tested_branch"
    if case_name == "repeat_tid_bad_then_good":
        return "repeated_tid_first_value_wins_in_tested_branch"
    if case_name == "repeat_otype_json_then_xml":
        return "repeated_otype_second_value_or_transport_change"
    if case_name == "baseline_json" and api_name == "api2" and summary.get("root") == "QZOutputJson":
        return "baseline_jsonp_wrapper"
    if case_name.startswith("extra_callback_") and case_name.endswith("_json"):
        return "jsonp_callback_value_changes_wrapper_branch"
    if case_name == "branch_canonical_wrong_appkey_json":
        return "control_case"
    if case_name == "error_callback_cb1_wrong_appkey_json":
        return "jsonp_error_branch_callback_changes_wrapper_branch"
    if case_name == "error_callback_a_open_paren_wrong_appkey_json":
        return "jsonp_error_branch_callback_parse_breaking_wrapper"
    if case_name.startswith("repeat_callback_"):
        return "repeated_callback_changes_wrapper_or_parseability"
    if "repeat_idlist_" in case_name:
        return "repeated_idlist_changes_effective_item_selection"
    if "repeat_tid_" in case_name:
        return "repeated_tid_changes_routing_branch"
    if "repeat_otype_" in case_name:
        return "repeated_otype_changes_wrapper_branch"
    if "repeat_union_platform_" in case_name:
        return "repeated_union_platform_changes_effective_branch"
    if "repeat_appid_" in case_name:
        return "repeated_appid_changes_selected_auth_branch"
    if "repeat_appkey_" in case_name:
        return "repeated_appkey_changes_selected_auth_branch"
    return "changed_vs_baseline"


def callback_wrapper_family(
    case_name: str,
    body: str,
    transport_error: str,
    summary: OrderedDict[str, object],
    callback_case_values: OrderedDict[str, str],
) -> str:
    expected = callback_case_values.get(case_name)
    if expected is None:
        return ""
    if transport_error or not body:
        return "unparseable_or_error"
    stripped = body.strip()
    if stripped.startswith("QZOutputJson="):
        return "fallback_default"
    if stripped.startswith("<"):
        return "unparseable_or_error"
    if summary.get("parse_error"):
        return "unparseable_or_error"
    root = str(summary.get("root", ""))
    if root == expected:
        return "raw_passthrough"
    if root or expected:
        return "normalized"
    return "unparseable_or_error"


def main() -> int:
    args = parse_args()
    replay_headers = load_replay_headers(args.extra_env_json, args.env_name)
    callback_case_values = load_callback_case_values(
        extra_values=args.extra_callback_value,
        extra_file=args.extra_callback_file,
    )
    original_headers = REQUEST_HEADERS.copy()
    if replay_headers:
        REQUEST_HEADERS.clear()
        REQUEST_HEADERS.update(replay_headers)
    cases = make_cases(
        api1_tid=args.api1_tid,
        api1_idlist=args.api1_idlist,
        api2_tid=args.api2_tid,
        api2_idlist=args.api2_idlist,
        case_profile=args.case_profile,
        callback_case_values=callback_case_values,
    )
    report: OrderedDict[str, object] = OrderedDict()
    report["generated_at"] = time.strftime("%Y-%m-%d")
    report["scope"] = "Tencent Video main-interface query-key semantics: extra keys and repeated keys"
    report["anchors"] = OrderedDict(
        (
            ("api1_tid", args.api1_tid),
            ("api1_idlist", args.api1_idlist),
            ("api2_tid", args.api2_tid),
            ("api2_idlist", args.api2_idlist),
            ("case_profile", args.case_profile),
            ("callback_case_values", callback_case_values),
        )
    )
    report["environment"] = OrderedDict(
        (
            ("extra_env_json", args.extra_env_json or ""),
            ("env_name", args.env_name or ""),
            ("request_headers", OrderedDict((key, REQUEST_HEADERS[key]) for key in REQUEST_HEADERS)),
        )
    )
    report["cases"] = OrderedDict()

    try:
        for api_name, api_cases in cases.items():
            api_report: OrderedDict[str, object] = OrderedDict()
            api_report["endpoint"] = API_1_URL if api_name == "api1" else API_2_URL
            api_report["results"] = OrderedDict()
            baseline_signatures: dict[str, str] = {}

            for case_name, base, pairs in api_cases:
                url = build_url(base, pairs)
                http_status, content_type, body, transport_error = http_fetch(
                    url, timeout=args.timeout, http_retries=args.http_retries
                )
                summary = summarize_response(body, content_type) if body else OrderedDict()
                sig = signature(http_status, content_type, transport_error, summary)
                if case_name.startswith("baseline"):
                    baseline_signatures[case_name] = sig
                    judgment = "baseline"
                else:
                    control_key = baseline_key_for(api_name, case_name)
                    control_sig = baseline_signatures.get(control_key, "")
                    secondary_key = secondary_control_key_for(api_name, case_name)
                    secondary_control_sig = baseline_signatures.get(secondary_key, "") if secondary_key else ""
                    judgment = infer_judgment(api_name, case_name, control_sig, secondary_control_sig, sig, summary)

                row: OrderedDict[str, object] = OrderedDict()
                row["pairs"] = pairs
                row["url"] = url
                row["http_status"] = http_status
                row["content_type"] = content_type
                row["transport_error"] = transport_error
                row["body_prefix"] = body[:120] if body else ""
                row["summary"] = summary
                if case_name in callback_case_values:
                    row["callback_value"] = callback_case_values[case_name]
                    row["wrapper_family"] = callback_wrapper_family(
                        case_name,
                        body,
                        transport_error,
                        summary,
                        callback_case_values,
                    )
                row["judgment"] = judgment
                api_report["results"][case_name] = row
                baseline_signatures[case_name] = sig

            report["cases"][api_name] = api_report
    finally:
        REQUEST_HEADERS.clear()
        REQUEST_HEADERS.update(original_headers)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=args.indent)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
