from __future__ import annotations

import argparse
from collections import OrderedDict
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


API_1_URL = "https://data.video.qq.com/fcgi-bin/data"
API_2_URL = "https://union.video.qq.com/fcgi-bin/data"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}
DEFAULT_TIDS = ["428", "429", "430", "431", "432", "433", "434", "533", "534", "535", "536", "537", "538", "539", "540"]


def expand_tid_spec(spec: str | None, default: list[str]) -> list[str]:
    if not spec:
        return list(default)
    tids: list[str] = []
    seen: set[str] = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            step = 1 if end >= start else -1
            for value in range(start, end + step, step):
                tid = str(value)
                if tid not in seen:
                    tids.append(tid)
                    seen.add(tid)
            continue
        tid = str(int(part))
        if tid not in seen:
            tids.append(tid)
            seen.add(tid)
    if not tids:
        raise ValueError("tid spec expanded to an empty set")
    return tids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small-band positive tid probe for Tencent Video API1/API2.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    parser.add_argument("--http-retries", type=int, default=2, help="Retry count for transient transport failures.")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation.")
    parser.add_argument(
        "--api1-tids",
        help="Comma-separated tid list and/or inclusive ranges for API1, e.g. 428-434,533-540",
    )
    parser.add_argument(
        "--api2-tids",
        help="Comma-separated tid list and/or inclusive ranges for API2, e.g. 428-434,533-540",
    )
    parser.add_argument(
        "--api1-cid",
        default="mzc00200idzf2m8",
        help="API1 CID sample used to probe positive tid branches",
    )
    parser.add_argument(
        "--api2-vid",
        default="z4102qfi0x4",
        help="API2 VID sample used to probe positive tid branches",
    )
    return parser.parse_args()


def http_fetch(url: str, timeout: float, http_retries: int) -> tuple[int | None, str, str, str]:
    last_transport_error = ""
    for attempt in range(http_retries + 1):
        request = urllib.request.Request(url, headers=REQUEST_HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, "replace")
                return response.status, response.headers.get("Content-Type", ""), body, ""
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset() or "utf-8"
            body = exc.read().decode(charset, "replace")
            return exc.code, exc.headers.get("Content-Type", ""), body, ""
        except Exception as exc:  # pragma: no cover
            last_transport_error = str(exc)
            if attempt >= http_retries:
                break
            time.sleep(0.4 * (attempt + 1))
    return None, "", "", last_transport_error


def build_url(base: str, pairs: list[tuple[str, str]]) -> str:
    return f"{base}?{urllib.parse.urlencode(pairs)}"


def parse_summary(body: str, is_jsonp: bool) -> OrderedDict[str, object]:
    if is_jsonp:
        summary: OrderedDict[str, object] = OrderedDict()
        stripped = body.strip()
        open_paren = stripped.find("(")
        close_paren = stripped.rfind(")")
        prefix = "QZOutputJson="
        root_name = ""
        payload = ""
        if stripped.startswith(prefix):
            root_name = "QZOutputJson"
            payload = stripped[len(prefix):].strip().rstrip(";")
        elif open_paren > 0 and close_paren > open_paren:
            root_name = stripped[:open_paren].strip()
            payload = stripped[open_paren + 1 : close_paren].strip()
        else:
            summary["parse_error"] = "missing JSONP wrapper"
            return summary
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            summary["parse_error"] = f"{exc.msg} at position {exc.pos}"
            return summary
        summary["root"] = root_name
        summary["errorno"] = str(data.get("errorno", ""))
        summary["errormsg"] = str(data.get("errormsg", ""))
        results = data.get("results", [])
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                fields = first.get("fields") or {}
                summary["sample_id"] = str(first.get("id", "")).strip()
                if isinstance(fields, dict):
                    summary["sample_vid"] = str(fields.get("vid", "")).strip()
                    summary["sample_title"] = str(fields.get("title", "")).strip()
        return summary

    summary = OrderedDict()
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        summary["parse_error"] = str(exc)
        return summary
    summary["root_tag"] = root.tag
    summary["errorno"] = (root.findtext(".//errorno") or "").strip()
    summary["errormsg"] = ((root.findtext(".//errormsg") or "") or (root.findtext(".//error") or "")).strip()
    summary["retcode"] = (root.findtext(".//retcode") or "").strip()
    summary["sample_id"] = (root.findtext(".//results/id") or "").strip()
    summary["sample_vid"] = (root.findtext(".//results//vid") or "").strip()
    summary["sample_title"] = (root.findtext(".//results//title") or "").strip()
    return summary


def classify(summary: OrderedDict[str, object], transport_error: str) -> str:
    if transport_error:
        return "transport_error"
    if summary.get("parse_error"):
        return "parse_error"
    errorno = str(summary.get("errorno", "")).strip()
    if errorno == "0" and (
        str(summary.get("sample_vid", "")).strip() or str(summary.get("sample_title", "")).strip()
    ):
        return "positive_tid_branch"
    if errorno == "0" and str(summary.get("sample_id", "")).strip():
        return "success_shell_without_sample"
    if errorno:
        return "error_branch"
    return "no_positive_payload"


def main() -> int:
    args = parse_args()
    api1_tids = expand_tid_spec(args.api1_tids, DEFAULT_TIDS)
    api2_tids = expand_tid_spec(args.api2_tids, DEFAULT_TIDS)
    report: OrderedDict[str, object] = OrderedDict(
        (
            ("generated_at", time.strftime("%Y-%m-%d")),
            ("scope", "Positive tid probe across caller-selected API1/API2 tid sets"),
            ("tested_bands", OrderedDict((
                ("api1", api1_tids),
                ("api2", api2_tids),
            ))),
            ("samples", OrderedDict((
                ("api1_cid", args.api1_cid),
                ("api2_vid", args.api2_vid),
            ))),
            ("api1", OrderedDict()),
            ("api2_xml", OrderedDict()),
            ("api2_jsonp", OrderedDict()),
        )
    )

    for tid in api1_tids:
        pairs = [("tid", tid), ("idlist", args.api1_cid), ("appid", "10001005"), ("appkey", "0d1a9ddd94de871b")]
        url = build_url(API_1_URL, pairs)
        status, content_type, body, transport_error = http_fetch(url, args.timeout, args.http_retries)
        summary = parse_summary(body, is_jsonp=False) if body else OrderedDict()
        report["api1"][tid] = OrderedDict(
            (
                ("url", url),
                ("http_status", status),
                ("content_type", content_type),
                ("transport_error", transport_error),
                ("body_prefix", body[:160] if body else ""),
                ("summary", summary),
                ("classification", classify(summary, transport_error)),
            )
        )

    for tid in api2_tids:
        for bucket, otype, key in (
            ("api2_xml", "xml", "api2_xml"),
            ("api2_jsonp", "json", "api2_jsonp"),
        ):
            pairs = [
                ("otype", otype),
                ("tid", tid),
                ("appid", "20001238"),
                ("appkey", "6c03bbe9658448a4"),
                ("union_platform", "3"),
                ("idlist", args.api2_vid),
            ]
            url = build_url(API_2_URL, pairs)
            status, content_type, body, transport_error = http_fetch(url, args.timeout, args.http_retries)
            summary = parse_summary(body, is_jsonp=(otype == "json")) if body else OrderedDict()
            report[bucket][tid] = OrderedDict(
                (
                    ("url", url),
                    ("http_status", status),
                    ("content_type", content_type),
                    ("transport_error", transport_error),
                    ("body_prefix", body[:160] if body else ""),
                    ("summary", summary),
                    ("classification", classify(summary, transport_error)),
                )
            )

    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=args.indent) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
