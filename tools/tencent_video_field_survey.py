from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_1_URL = "https://data.video.qq.com/fcgi-bin/data"
API_2_URL = "https://union.video.qq.com/fcgi-bin/data"
CID_PATTERNS = (
    re.compile(r"/cover/([^/]+)/[^/]+\.html"),
    re.compile(r"/cover/([^/]+)\.html"),
)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Survey Tencent video cover/video fields across multiple URLs."
    )
    parser.add_argument("urls", nargs="+", help="Tencent video page URLs")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="How many VIDs to request per API2 batch",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


def extract_cid_from_url(url: str) -> str | None:
    text = url.strip()
    for pattern in CID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)

    parsed = urllib.parse.urlparse(text)
    cid_values = urllib.parse.parse_qs(parsed.query).get("cid", [])
    for cid in cid_values:
        cid = cid.strip()
        if cid:
            return cid
    return None


def build_api_1_url(cid: str) -> str:
    params = {
        "tid": "431",
        "idlist": cid,
        "appid": "10001005",
        "appkey": "0d1a9ddd94de871b",
    }
    return f"{API_1_URL}?{urllib.parse.urlencode(params)}"


def build_api_2_url(vids: list[str]) -> str:
    params = {
        "otype": "xml",
        "tid": "535",
        "appid": "20001238",
        "appkey": "6c03bbe9658448a4",
        "union_platform": "3",
        "idlist": ",".join(vids),
    }
    return f"{API_2_URL}?{urllib.parse.urlencode(params)}"


def http_get(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, "replace")


def parse_xml(xml_text: str, label: str) -> ET.Element:
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise RuntimeError(f"{label} XML parse failed: {exc}") from exc


def find_error(root: ET.Element, label: str) -> None:
    error_text = (root.findtext(".//errormsg") or root.findtext(".//error") or "").strip()
    error_no = (root.findtext(".//errorno") or "").strip()
    if error_text or (error_no and error_no != "0"):
        raise RuntimeError(error_text or f"{label} errorno={error_no}")


def collect_leaf_fields(node: ET.Element) -> tuple[OrderedDict[str, object], list[str]]:
    field_values: OrderedDict[str, list[str]] = OrderedDict()

    def visit(current: ET.Element) -> None:
        children = list(current)
        if children:
            for child in children:
                visit(child)
            return
        field_values.setdefault(current.tag, []).append((current.text or "").strip())

    visit(node)

    normalized: OrderedDict[str, object] = OrderedDict()
    for name, values in field_values.items():
        normalized[name] = values[0] if len(values) == 1 else values
    return normalized, sorted(field_values)


def split_csv_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def scalar_value(value: object, default: str = "") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else default
    if value is None:
        return default
    return str(value)


def parse_cover_document(xml_text: str) -> dict[str, object]:
    root = parse_xml(xml_text, "API1")
    find_error(root, "API1")

    fields, field_names = collect_leaf_fields(root)
    video_ids: list[str] = []
    for node in root.findall(".//video_ids"):
        text = (node.text or "").strip()
        if text:
            video_ids.extend(split_csv_values(text))

    return {
        "field_names": field_names,
        "fields": fields,
        "video_ids": unique_strings(video_ids),
    }


def parse_defn(defn_raw: str) -> tuple[dict[str, object], str | None]:
    text = defn_raw.strip()
    if not text:
        return {}, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, f"{exc.msg} at position {exc.pos}"
    if isinstance(data, dict):
        return data, None
    return {"_value": data}, None


def parse_video_document(xml_text: str) -> list[dict[str, object]]:
    root = parse_xml(xml_text, "API2")
    find_error(root, "API2")

    videos: list[dict[str, object]] = []
    for result_node in root.findall(".//results"):
        field_node = result_node.find("./fields")
        if field_node is None:
            continue

        fields, field_names = collect_leaf_fields(field_node)
        defn_raw = html.unescape(scalar_value(fields.get("defn", "")))
        defn_expanded, defn_error = parse_defn(defn_raw)

        video: OrderedDict[str, object] = OrderedDict()
        vid = scalar_value(fields.get("vid", "")) or scalar_value(result_node.findtext("./id"), "")
        if vid:
            video["vid"] = vid
        video["field_names"] = field_names
        video["fields"] = fields
        video["defn_raw"] = defn_raw
        video["defn_expanded"] = defn_expanded
        if defn_error:
            video["defn_parse_error"] = defn_error
        videos.append(video)

    return videos


def survey_sample(url: str, timeout: float, batch_size: int) -> OrderedDict[str, object]:
    sample: OrderedDict[str, object] = OrderedDict()
    sample["input_url"] = url

    try:
        cid = extract_cid_from_url(url)
        if not cid:
            raise RuntimeError("could not extract CID from URL")

        sample["cid"] = cid
        cover_request_url = build_api_1_url(cid)
        sample["cover_request"] = {"url": cover_request_url}

        cover = parse_cover_document(http_get(cover_request_url, timeout))
        sample["cover"] = {
            "field_names": cover["field_names"],
            "fields": cover["fields"],
        }
        video_ids = list(cover["video_ids"])
        sample["video_ids"] = video_ids
        if not video_ids:
            raise RuntimeError("API1 returned no video_ids")

        videos: list[dict[str, object]] = []
        video_batches: list[dict[str, object]] = []
        for batch in chunked(video_ids, batch_size):
            api_2_url = build_api_2_url(batch)
            video_batches.append({"vids": batch, "url": api_2_url})
            videos.extend(parse_video_document(http_get(api_2_url, timeout)))

        if not videos:
            raise RuntimeError("API2 returned no video field records")

        sample["video_request_batches"] = video_batches
        sample["videos"] = videos
        sample["video_field_names"] = sorted(
            {field_name for video in videos for field_name in video["field_names"]}
        )
        sample["status"] = "ok"
    except Exception as exc:
        sample["status"] = "error"
        sample["error"] = str(exc)

    return sample


def build_frequency_report(
    counts: Counter[str], total: int, denominator: str
) -> OrderedDict[str, object]:
    fields: OrderedDict[str, object] = OrderedDict()
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        fields[name] = {
            "count": count,
            "ratio": round(count / total, 6) if total else 0.0,
        }
    return OrderedDict(
        (
            ("denominator", denominator),
            ("total", total),
            ("fields", fields),
        )
    )


def build_summary(samples: list[OrderedDict[str, object]]) -> OrderedDict[str, object]:
    cover_counts: Counter[str] = Counter()
    video_counts: Counter[str] = Counter()
    defn_counts: Counter[str] = Counter()
    successful_sample_count = 0
    total_video_count = 0
    videos_with_defn_count = 0

    for sample in samples:
        if sample.get("status") != "ok":
            continue

        successful_sample_count += 1
        cover = sample.get("cover", {})
        if isinstance(cover, dict):
            cover_counts.update(cover.get("field_names", []))

        for video in sample.get("videos", []):
            if not isinstance(video, dict):
                continue
            total_video_count += 1
            video_counts.update(video.get("field_names", []))

            defn_expanded = video.get("defn_expanded", {})
            if isinstance(defn_expanded, dict) and defn_expanded:
                videos_with_defn_count += 1
                defn_counts.update(defn_expanded.keys())

    return OrderedDict(
        (
            ("sample_count", len(samples)),
            ("successful_sample_count", successful_sample_count),
            ("failed_sample_count", len(samples) - successful_sample_count),
            ("video_count", total_video_count),
            ("videos_with_defn_count", videos_with_defn_count),
            (
                "cover_field_frequency",
                build_frequency_report(
                    cover_counts,
                    successful_sample_count,
                    "successful_samples",
                ),
            ),
            (
                "video_field_frequency",
                build_frequency_report(video_counts, total_video_count, "videos"),
            ),
            (
                "defn_field_frequency",
                build_frequency_report(
                    defn_counts,
                    videos_with_defn_count,
                    "videos_with_defn",
                ),
            ),
        )
    )


def build_report(urls: list[str], timeout: float, batch_size: int) -> OrderedDict[str, object]:
    samples = [survey_sample(url, timeout=timeout, batch_size=batch_size) for url in urls]
    return OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("tool", "tencent_video_field_survey"),
                        (
                            "generated_at",
                            dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                        ),
                        ("input_count", len(urls)),
                        ("timeout_seconds", timeout),
                        ("batch_size", batch_size),
                    )
                ),
            ),
            ("samples", samples),
            ("summary", build_summary(samples)),
        )
    )


def main() -> int:
    args = parse_args()
    report = build_report(args.urls, timeout=args.timeout, batch_size=args.batch_size)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=args.indent))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
