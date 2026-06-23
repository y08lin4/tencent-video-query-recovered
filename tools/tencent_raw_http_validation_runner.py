from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
import html
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 2
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}
TRANSIENT_ERROR_MARKERS = (
    "deadline exceeded",
    "timeout",
    "timed out",
    "temporary failure",
    "connection reset",
    "connection aborted",
    "awaiting headers",
    "tls handshake timeout",
    "eof",
)

API1 = "https://data.video.qq.com/fcgi-bin/data"
API2 = "https://union.video.qq.com/fcgi-bin/data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run raw HTTP validation for the highest-value Tencent Video "
            "direct-call capability rows in the current anonymous scope."
        )
    )
    parser.add_argument(
        "--surface",
        action="append",
        dest="surfaces",
        help="Surface id to run; repeatable. When omitted, run the default surface set.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Maximum request attempts per surface.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any selected surface fails.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path; when omitted, write to stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation.",
    )
    return parser.parse_args()


def normalize_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def has_value(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return normalize_str(value) != ""


def parse_jsonp_payload(body: str) -> dict[str, Any]:
    stripped = body.strip()
    if stripped.startswith("QZOutputJson="):
        payload = stripped[len("QZOutputJson=") :].strip()
    else:
        open_paren = stripped.find("(")
        close_paren = stripped.rfind(")")
        if open_paren < 0 or close_paren <= open_paren:
            raise ValueError("unparseable JSONP wrapper")
        payload = stripped[open_paren + 1 : close_paren].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("JSONP payload is not an object")
    return data


def is_empty_shell(row: dict[str, Any]) -> bool:
    meaningful_fields = [
        row.get("vid"),
        row.get("title"),
        row.get("duration_seconds"),
        row.get("state"),
        row.get("upload_src"),
        row.get("create_time"),
        row.get("modify_time"),
        row.get("cover_list"),
        row.get("category_map"),
        row.get("vwh"),
        row.get("defn"),
    ]
    return not any(has_value(value) for value in meaningful_fields)


def normalize_multi_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_str(item) for item in value if normalize_str(item)]
    text = normalize_str(value)
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_xml_row(item: ET.Element) -> dict[str, Any]:
    field = item.find("./fields")
    if field is None:
        return {}
    row = OrderedDict()
    row["result_id"] = normalize_str(item.findtext("./id"))
    row["retcode"] = normalize_str(item.findtext("./retcode"))
    row["vid"] = normalize_str(field.findtext("./vid"))
    row["title"] = normalize_str(field.findtext("./title"))
    row["duration_seconds"] = normalize_str(field.findtext("./duration"))
    row["url"] = normalize_str(field.findtext("./url"))
    row["cover_list"] = [
        normalize_str(node.text) for node in field.findall("./cover_list") if normalize_str(node.text)
    ]
    row["category_map"] = [
        normalize_str(node.text) for node in field.findall("./category_map") if normalize_str(node.text)
    ]
    row["state"] = normalize_str(field.findtext("./state"))
    row["upload_src"] = normalize_str(field.findtext("./upload_src"))
    row["create_time"] = normalize_str(field.findtext("./create_time"))
    row["modify_time"] = normalize_str(field.findtext("./modify_time"))
    row["vwh"] = [normalize_str(node.text) for node in field.findall("./vWH") if normalize_str(node.text)]
    if not row["vwh"]:
        row["vwh"] = [normalize_str(node.text) for node in field.findall("./vwh") if normalize_str(node.text)]
    row["defn"] = {}
    defn_raw = html.unescape(normalize_str(field.findtext("./defn")))
    if defn_raw:
        try:
            parsed = json.loads(defn_raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            row["defn"] = parsed
    row["empty_shell"] = is_empty_shell(row)
    return row


def parse_json_row(item: dict[str, Any]) -> dict[str, Any]:
    field = item.get("fields") or {}
    if not isinstance(field, dict):
        field = {}
    row = OrderedDict()
    row["result_id"] = normalize_str(item.get("id"))
    row["retcode"] = normalize_str(item.get("retcode"))
    row["vid"] = normalize_str(field.get("vid"))
    row["title"] = normalize_str(field.get("title"))
    row["duration_seconds"] = normalize_str(field.get("duration"))
    row["url"] = normalize_str(field.get("url"))
    row["cover_list"] = normalize_multi_value(field.get("cover_list"))
    row["category_map"] = normalize_multi_value(field.get("category_map"))
    row["state"] = normalize_str(field.get("state"))
    row["upload_src"] = normalize_str(field.get("upload_src"))
    row["create_time"] = normalize_str(field.get("create_time"))
    row["modify_time"] = normalize_str(field.get("modify_time"))
    row["vwh"] = normalize_multi_value(field.get("vWH") or field.get("vwh"))
    row["defn"] = {}
    raw_defn = field.get("defn")
    if isinstance(raw_defn, dict):
        row["defn"] = raw_defn
    else:
        defn_raw = html.unescape(normalize_str(raw_defn))
        if defn_raw:
            try:
                parsed = json.loads(defn_raw)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict):
                row["defn"] = parsed
    row["empty_shell"] = is_empty_shell(row)
    return row


def row_cover_list_count(row: dict[str, Any]) -> int:
    covers = row.get("cover_list")
    return len(covers) if isinstance(covers, list) else 0


def parse_api1_summary(body: str) -> dict[str, Any]:
    root = ET.fromstring(body)
    errorno = normalize_str(root.findtext(".//errorno"))
    errormsg = normalize_str(root.findtext(".//errormsg") or root.findtext(".//error"))
    cover_title = normalize_str(root.findtext(".//title"))
    cover_type = normalize_str(root.findtext(".//type"))
    pay_status = normalize_str(root.findtext(".//pay_status"))
    raw_video_ids: list[str] = []
    for node in root.findall(".//video_ids"):
        raw_video_ids.extend(normalize_multi_value(node.text))
    field_names: list[str] = []
    extra_field_keys: list[str] = []
    extra_nonempty_fields: OrderedDict[str, str] = OrderedDict()
    core_field_tags = {
        "cover_id",
        "title",
        "type",
        "type_name",
        "video_ids",
        "pay_status",
        "new_pic_hz",
        "new_pic_vt",
    }
    fields_node = root.find(".//results/fields")
    if fields_node is not None:
        for child in list(fields_node):
            tag = normalize_str(child.tag)
            if not tag:
                continue
            field_names.append(tag)
            if tag in core_field_tags:
                continue
            extra_field_keys.append(tag)
            value = normalize_str(child.text)
            if value:
                extra_nonempty_fields[tag] = value
    return OrderedDict(
        (
            ("errorno", errorno),
            ("errormsg", errormsg),
            ("cover_title", cover_title),
            ("cover_type", cover_type),
            ("pay_status", pay_status),
            ("video_ids_count", len(raw_video_ids)),
            ("video_ids_head", raw_video_ids[:5]),
            ("field_count", len(field_names)),
            ("field_names", field_names),
            ("extra_field_keys", extra_field_keys),
            ("extra_nonempty_fields", extra_nonempty_fields),
        )
    )


def parse_api2_xml_summary(body: str) -> dict[str, Any]:
    root = ET.fromstring(body)
    errorno = normalize_str(root.findtext(".//errorno"))
    rows = [row for row in (parse_xml_row(item) for item in root.findall(".//results")) if row]
    empty_count = sum(1 for row in rows if row.get("empty_shell"))
    return OrderedDict(
        (
            ("errorno", errorno),
            ("rows", rows),
            ("results_count", len(rows)),
            ("empty_shell_count", empty_count),
            ("all_results_empty_shell", bool(rows) and empty_count == len(rows)),
        )
    )


def parse_api2_json_summary(body: str) -> dict[str, Any]:
    payload = parse_jsonp_payload(body)
    errorno = normalize_str(payload.get("errorno"))
    rows = [parse_json_row(item) for item in payload.get("results", []) if isinstance(item, dict)]
    empty_count = sum(1 for row in rows if row.get("empty_shell"))
    return OrderedDict(
        (
            ("errorno", errorno),
            ("rows", rows),
            ("results_count", len(rows)),
            ("empty_shell_count", empty_count),
            ("all_results_empty_shell", bool(rows) and empty_count == len(rows)),
            ("wrapper_prefix", body[:40]),
        )
    )


def build_surface_specs() -> OrderedDict[str, dict[str, Any]]:
    return OrderedDict(
        (
            (
                "api1_single_cover_lookup",
                {
                    "url": f"{API1}?tid=431&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_single_cover_lookup,
                    "intent": "Single CID canonical API1 raw lookup.",
                },
            ),
            (
                "api1_batch_cover_lookup",
                {
                    "url": f"{API1}?tid=431&idlist=mzc00200idzf2m8,mzc00200xxpsogl&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_batch_cover_lookup,
                    "intent": "Direct multi-CID API1 raw lookup.",
                },
            ),
            (
                "api1_tid537_probe_shell",
                {
                    "url": f"{API1}?tid=537&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_tid537_probe_shell,
                    "intent": "Direct API1 tid=537 shell probe on a public CID.",
                },
            ),
            (
                "api1_tid453_cover_shell_only",
                {
                    "url": f"{API1}?tid=453&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_tid453_cover_shell_only,
                    "intent": "Direct API1 tid=453 positive cover-shell-only branch on a public CID.",
                },
            ),
            (
                "api1_tid476_imgtag_ultra_thin_shell",
                {
                    "url": f"{API1}?tid=476&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_tid476_imgtag_ultra_thin_shell,
                    "intent": "Direct API1 tid=476 imgtag-family ultra-thin success shell on a public CID.",
                },
            ),
            (
                "api1_tid506_empty_valued_field_shell",
                {
                    "url": f"{API1}?tid=506&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_tid506_empty_valued_field_shell,
                    "intent": "Direct API1 tid=506 empty-valued field shell on a public CID.",
                },
            ),
            (
                "api1_tid483_video_ids_led_thin_shell",
                {
                    "url": f"{API1}?tid=483&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b",
                    "parser": parse_api1_summary,
                    "validator": validate_api1_tid483_video_ids_led_thin_shell,
                    "intent": "Direct API1 tid=483 video_ids-led thin success shell on a public CID.",
                },
            ),
            (
                "api2_single_detail_xml_canonical",
                {
                    "url": f"{API2}?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_single_detail_xml_canonical,
                    "intent": "Canonical API2 XML single-row lookup.",
                },
            ),
            (
                "api2_single_detail_xml_tid488_alt_positive_shell",
                {
                    "url": f"{API2}?otype=xml&tid=488&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid488_alt_positive_shell,
                    "intent": "Alternate positive API2 tid=488 thin shell.",
                },
            ),
            (
                "api2_single_detail_xml_tid502_alt_positive_shell",
                {
                    "url": f"{API2}?otype=xml&tid=502&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=j4101ouc4ve",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid502_alt_positive_shell,
                    "intent": "Alternate positive API2 tid=502 richer shell.",
                },
            ),
            (
                "api2_single_detail_xml_tid506_near_empty_success_shell",
                {
                    "url": f"{API2}?otype=xml&tid=506&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid506_near_empty_success_shell,
                    "intent": "API2 tid=506 near-empty success shell.",
                },
            ),
            (
                "api2_single_detail_xml_tid540_alt_positive_shell",
                {
                    "url": f"{API2}?otype=xml&tid=540&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid540_alt_positive_shell,
                    "intent": "Alternate positive API2 tid=540 shell.",
                },
            ),
            (
                "api2_single_detail_xml_tid541_alt_positive_shell",
                {
                    "url": f"{API2}?otype=xml&tid=541&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=j4101ouc4ve",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid541_alt_positive_shell,
                    "intent": "Alternate positive API2 tid=541 shell.",
                },
            ),
            (
                "api2_tid541_union0003_thin_shell_spotcheck",
                {
                    "url": f"{API2}?otype=xml&tid=541&appid=20001238&appkey=6c03bbe9658448a4&union_platform=0003&idlist=z4102qfi0x4",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_tid541_union0003_thin_shell_spotcheck,
                    "intent": "Alternate positive API2 tid=541 with union_platform=0003.",
                },
            ),
            (
                "api2_single_detail_jsonp",
                {
                    "url": f"{API2}?otype=json&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4&callback=cb1",
                    "parser": parse_api2_json_summary,
                    "validator": validate_api2_single_detail_jsonp,
                    "intent": "Canonical API2 JSONP callback override row.",
                },
            ),
            (
                "api2_batch_lookup_up_to_32_nonempty_vids",
                {
                    "url": f"{API2}?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4,j4101ouc4ve",
                    "parser": parse_api2_xml_summary,
                    "validator": validate_api2_batch_lookup_up_to_32_nonempty_vids,
                    "intent": "Canonical API2 XML multi-VID batch lookup.",
                },
            ),
            (
                "api2_all_invalid_jsonp_batch_consumer_rule",
                {
                    "url": f"{API2}?otype=json&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=zzzzzzzzzzz,yyyyyyyyyyy",
                    "parser": parse_api2_json_summary,
                    "validator": validate_api2_all_invalid_jsonp_batch_consumer_rule,
                    "intent": "All-invalid JSONP batch consumer-rule path.",
                },
            ),
        )
    )


def first_row(summary: dict[str, Any]) -> dict[str, Any]:
    rows = summary.get("rows") if isinstance(summary, dict) else None
    return rows[0] if isinstance(rows, list) and rows else {}


def validate_api1_single_cover_lookup(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and has_value(summary.get("cover_title"))
        and int(summary.get("video_ids_count") or 0) >= 1
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"video_ids_count={int(summary.get('video_ids_count') or 0)}",
    ]
    return ok, "success" if ok else "failure", highlights


def validate_api1_batch_cover_lookup(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    count = int(summary.get("video_ids_count") or 0)
    ok = normalize_str(summary.get("errorno")) == "0" and count >= 2
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"video_ids_count={count}",
    ]
    return ok, "success" if ok else "failure", highlights


def validate_api1_tid537_probe_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    video_ids_count = int(summary.get("video_ids_count") or 0)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and not has_value(summary.get("cover_title"))
        and video_ids_count == 0
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"video_ids_count={video_ids_count}",
    ]
    return ok, "success_with_shell_only_probe" if ok else "failure", highlights


def validate_api1_tid453_cover_shell_only(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    video_ids_count = int(summary.get("video_ids_count") or 0)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and has_value(summary.get("cover_title"))
        and video_ids_count == 0
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"video_ids_count={video_ids_count}",
    ]
    return ok, "success_with_cover_shell_only_branch" if ok else "failure", highlights


def validate_api1_tid476_imgtag_ultra_thin_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    video_ids_count = int(summary.get("video_ids_count") or 0)
    field_count = int(summary.get("field_count") or 0)
    extra_field_keys = summary.get("extra_field_keys") or []
    if not isinstance(extra_field_keys, list):
        extra_field_keys = []
    extra_nonempty_fields = summary.get("extra_nonempty_fields") or {}
    if not isinstance(extra_nonempty_fields, dict):
        extra_nonempty_fields = {}
    qbox_imgtag = normalize_str(extra_nonempty_fields.get("qbox_imgtag"))
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and not has_value(summary.get("cover_title"))
        and not has_value(summary.get("cover_type"))
        and not has_value(summary.get("pay_status"))
        and video_ids_count == 0
        and "apad_imgtag" in extra_field_keys
        and "qbox_imgtag" in extra_field_keys
        and qbox_imgtag == "{}"
        and field_count >= 20
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"cover_type={normalize_str(summary.get('cover_type')) or '-'}",
        f"pay_status={normalize_str(summary.get('pay_status')) or '-'}",
        f"video_ids_count={video_ids_count}",
        f"field_count={field_count}",
        f"extra_field_key_count={len(extra_field_keys)}",
        f"qbox_imgtag={qbox_imgtag or '-'}",
    ]
    return ok, "success_with_imgtag_family_ultra_thin_shell" if ok else "failure", highlights


def validate_api1_tid506_empty_valued_field_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    video_ids_count = int(summary.get("video_ids_count") or 0)
    field_count = int(summary.get("field_count") or 0)
    extra_field_keys = summary.get("extra_field_keys") or []
    if not isinstance(extra_field_keys, list):
        extra_field_keys = []
    extra_nonempty_fields = summary.get("extra_nonempty_fields") or {}
    if not isinstance(extra_nonempty_fields, dict):
        extra_nonempty_fields = {}
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and not has_value(summary.get("cover_title"))
        and not has_value(summary.get("cover_type"))
        and not has_value(summary.get("pay_status"))
        and video_ids_count == 0
        and field_count == 10
        and len(extra_field_keys) == 9
        and "description" in extra_field_keys
        and "playing_status" in extra_field_keys
        and "user_id" in extra_field_keys
        and "qbox_imgtag" not in extra_field_keys
        and not extra_nonempty_fields
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"cover_type={normalize_str(summary.get('cover_type')) or '-'}",
        f"pay_status={normalize_str(summary.get('pay_status')) or '-'}",
        f"video_ids_count={video_ids_count}",
        f"field_count={field_count}",
        f"extra_field_key_count={len(extra_field_keys)}",
        f"extra_nonempty_field_count={len(extra_nonempty_fields)}",
    ]
    return ok, "success_with_empty_valued_field_shell" if ok else "failure", highlights


def validate_api1_tid483_video_ids_led_thin_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    video_ids_count = int(summary.get("video_ids_count") or 0)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and not has_value(summary.get("cover_title"))
        and not has_value(summary.get("cover_type"))
        and not has_value(summary.get("pay_status"))
        and video_ids_count >= 1
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"cover_title={normalize_str(summary.get('cover_title')) or '-'}",
        f"cover_type={normalize_str(summary.get('cover_type')) or '-'}",
        f"pay_status={normalize_str(summary.get('pay_status')) or '-'}",
        f"video_ids_count={video_ids_count}",
    ]
    return ok, "success_with_video_ids_led_shell" if ok else "failure", highlights


def validate_api2_single_detail_xml_canonical(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("duration_seconds"))
        and has_value(row.get("state"))
        and has_value(row.get("upload_src"))
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"has_state={has_value(row.get('state'))}",
        f"has_upload_src={has_value(row.get('upload_src'))}",
    ]
    return ok, "success" if ok else "failure", highlights


def validate_api2_tid540_alt_positive_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("url"))
        and has_value(row.get("duration_seconds"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_url={has_value(row.get('url'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"has_state={has_value(row.get('state'))}",
        f"has_upload_src={has_value(row.get('upload_src'))}",
    ]
    return ok, "success_with_thin_positive_shell" if ok else "failure", highlights


def validate_api2_tid488_alt_positive_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("url"))
        and not has_value(row.get("vid"))
        and not has_value(row.get("duration_seconds"))
        and row_cover_list_count(row) == 0
        and not has_value(row.get("create_time"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_url={has_value(row.get('url'))}",
        f"has_vid={has_value(row.get('vid'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"cover_list_count={row_cover_list_count(row)}",
        f"has_create_time={has_value(row.get('create_time'))}",
    ]
    return ok, "success_with_thin_positive_shell" if ok else "failure", highlights


def validate_api2_tid502_alt_positive_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("url"))
        and has_value(row.get("vid"))
        and has_value(row.get("duration_seconds"))
        and row_cover_list_count(row) >= 1
        and has_value(row.get("create_time"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
        and not has_value(row.get("defn"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_url={has_value(row.get('url'))}",
        f"has_vid={has_value(row.get('vid'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"cover_list_count={row_cover_list_count(row)}",
        f"has_create_time={has_value(row.get('create_time'))}",
    ]
    return ok, "success_with_richer_alt_positive_shell" if ok else "failure", highlights


def validate_api2_tid506_near_empty_success_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and bool(row.get("empty_shell"))
        and not has_value(row.get("title"))
        and not has_value(row.get("url"))
        and not has_value(row.get("vid"))
        and not has_value(row.get("duration_seconds"))
        and row_cover_list_count(row) == 0
        and not has_value(row.get("create_time"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
        and not has_value(row.get("defn"))
        and bool(summary.get("all_results_empty_shell"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"empty_shell={bool(row.get('empty_shell'))}",
        f"has_title={has_value(row.get('title'))}",
        f"has_url={has_value(row.get('url'))}",
        f"has_vid={has_value(row.get('vid'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"cover_list_count={row_cover_list_count(row)}",
        f"all_results_empty_shell={bool(summary.get('all_results_empty_shell'))}",
    ]
    return ok, "success_with_near_empty_shell" if ok else "failure", highlights


def validate_api2_tid541_alt_positive_shell(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("url"))
        and not has_value(row.get("duration_seconds"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_url={has_value(row.get('url'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"has_state={has_value(row.get('state'))}",
        f"has_upload_src={has_value(row.get('upload_src'))}",
    ]
    return ok, "success_with_thin_positive_shell" if ok else "failure", highlights


def validate_api2_tid541_union0003_thin_shell_spotcheck(
    summary: dict[str, Any]
) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
        and has_value(row.get("url"))
        and not has_value(row.get("duration_seconds"))
        and not has_value(row.get("state"))
        and not has_value(row.get("upload_src"))
    )
    highlights = [
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
        f"has_url={has_value(row.get('url'))}",
        f"has_duration={has_value(row.get('duration_seconds'))}",
        f"has_state={has_value(row.get('state'))}",
        f"has_upload_src={has_value(row.get('upload_src'))}",
    ]
    return ok, "success_with_thin_positive_shell" if ok else "failure", highlights


def validate_api2_single_detail_jsonp(summary: dict[str, Any]) -> tuple[bool, str, list[str]]:
    row = first_row(summary)
    wrapper = normalize_str(summary.get("wrapper_prefix"))
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and wrapper.startswith("cb1(")
        and normalize_str(row.get("retcode")) == "0"
        and has_value(row.get("title"))
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"wrapper_prefix={wrapper[:16] or '-'}",
        f"retcode={normalize_str(row.get('retcode')) or '-'}",
        f"title={normalize_str(row.get('title')) or '-'}",
    ]
    return ok, "success" if ok else "failure", highlights


def validate_api2_batch_lookup_up_to_32_nonempty_vids(
    summary: dict[str, Any]
) -> tuple[bool, str, list[str]]:
    rows = summary.get("rows") if isinstance(summary, dict) else []
    vids = [normalize_str(row.get("vid")) for row in rows if isinstance(row, dict)]
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and int(summary.get("results_count") or 0) == 2
        and "z4102qfi0x4" in vids
        and "j4101ouc4ve" in vids
        and not bool(summary.get("all_results_empty_shell"))
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"results_count={int(summary.get('results_count') or 0)}",
        f"vids={vids}",
        f"all_results_empty_shell={bool(summary.get('all_results_empty_shell'))}",
    ]
    return ok, "success" if ok else "failure", highlights


def validate_api2_all_invalid_jsonp_batch_consumer_rule(
    summary: dict[str, Any]
) -> tuple[bool, str, list[str]]:
    count = int(summary.get("results_count") or 0)
    empty_count = int(summary.get("empty_shell_count") or 0)
    ok = (
        normalize_str(summary.get("errorno")) == "0"
        and count >= 1
        and bool(summary.get("all_results_empty_shell"))
        and empty_count == count
    )
    highlights = [
        f"errorno={normalize_str(summary.get('errorno')) or '-'}",
        f"results_count={count}",
        f"empty_shell_count={empty_count}",
        f"all_results_empty_shell={bool(summary.get('all_results_empty_shell'))}",
    ]
    return ok, "success" if ok else "failure", highlights


def looks_transient_error(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in TRANSIENT_ERROR_MARKERS)


def http_get(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def run_surface(surface_id: str, spec: dict[str, Any], timeout: int, retries: int) -> OrderedDict[str, Any]:
    entry = OrderedDict(
        (
            ("surface", surface_id),
            ("intent", spec["intent"]),
            ("url", spec["url"]),
        )
    )
    attempts: list[OrderedDict[str, Any]] = []
    max_attempts = max(1, retries)
    body = ""
    final_error = ""
    for attempt in range(1, max_attempts + 1):
        attempt_entry = OrderedDict((("attempt", attempt),))
        try:
            body = http_get(spec["url"], timeout)
            attempt_entry["result"] = "http_success"
            attempt_entry["body_prefix"] = body[:120]
            attempts.append(attempt_entry)
            break
        except urllib.error.HTTPError as exc:
            final_error = f"HTTP {exc.code}: {exc.reason}"
            attempt_entry["result"] = "http_error"
            attempt_entry["error"] = final_error
            attempts.append(attempt_entry)
            break
        except Exception as exc:  # noqa: BLE001
            final_error = str(exc)
            attempt_entry["result"] = "transport_error"
            attempt_entry["error"] = final_error
            attempts.append(attempt_entry)
            if attempt >= max_attempts:
                break
            if not looks_transient_error(final_error) and "WinError" not in final_error:
                break
            time.sleep(1.0)
    entry["attempt_count"] = len(attempts)
    entry["attempts"] = attempts
    if not body:
        entry["result"] = "request_failed"
        entry["ok"] = False
        entry["error"] = final_error
        return entry
    try:
        summary = spec["parser"](body)
    except Exception as exc:  # noqa: BLE001
        entry["result"] = "parse_failed"
        entry["ok"] = False
        entry["error"] = str(exc)
        entry["body_prefix"] = body[:240]
        return entry
    entry["summary"] = summary
    ok, result, highlights = spec["validator"](summary)
    entry["result"] = result
    entry["ok"] = ok
    entry["highlights"] = highlights
    return entry


def build_report(args: argparse.Namespace, specs: OrderedDict[str, dict[str, Any]]) -> OrderedDict[str, Any]:
    selected_ids = list(specs.keys())
    if args.surfaces:
        requested: list[str] = []
        for raw in args.surfaces:
            requested.extend([part.strip() for part in raw.split(",") if part.strip()])
        unknown = [surface_id for surface_id in requested if surface_id not in specs]
        if unknown:
            raise SystemExit(f"unknown surface ids: {', '.join(unknown)}")
        selected_ids = requested
    rows = [run_surface(surface_id, specs[surface_id], args.timeout, args.retries) for surface_id in selected_ids]
    failures = [row["surface"] for row in rows if not row.get("ok")]
    return OrderedDict(
        (
            ("generated_at", datetime.now().strftime("%Y-%m-%d")),
            (
                "scope",
                "Live raw HTTP validation summary for the highest-value Tencent Video direct-call rows in the current anonymous scope.",
            ),
            (
                "runner_inputs",
                OrderedDict(
                    (
                        ("selected_surfaces", selected_ids),
                        ("timeout_seconds", args.timeout),
                        ("retries", args.retries),
                    )
                ),
            ),
            ("results", rows),
            ("failed_surfaces", failures),
            (
                "current_reading",
                [
                    "This runner validates raw HTTP behavior only in the current anonymous direct-call scope.",
                    "API1 tid=476 should now be read as an imgtag-family ultra-thin success shell: on the dedicated raw sample it returns 25 imgtag-oriented fields with qbox_imgtag={}, but still no cover title and no video_ids.",
                    "API1 tid=506 should now be read as an empty-valued field shell: on the dedicated raw sample it returns 10 empty-valued fields with a 9-key extra-field family (description/end_time/live_vid/.../user_id), but no qbox_imgtag and no video_ids.",
                    "API1 tid=483 should still be read as a video_ids-led thin shell: errorno=0 plus non-empty video_ids_count does not mean canonical 431 cover richness.",
                    "API2 tid=506 should still be read as a near-empty success shell: top-level success plus retcode=0 does not currently rise into caller-facing detail fields on the dedicated raw XML validation sample.",
                    "Alternate tid 488/502/540/541 rows are expected to succeed as positive shells rather than canonical-full detail rows.",
                    "Within that alternate family, tid=502 currently sits on a richer shell than tid=488/540/541, but still below canonical 535 detail fullness.",
                    "The all-invalid JSONP row is a consumer-rule validation, not a content-extraction success row.",
                    "The current batch row is a canonical multi-VID spot-check on the known batch-capable branch, not a fresh 32-slot saturation replay.",
                ],
            ),
        )
    )


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
    report = build_report(args, build_surface_specs())
    write_output(report, args.output, args.indent)
    if args.strict and report["failed_surfaces"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
