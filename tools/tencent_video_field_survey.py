from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.error
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
    parser.add_argument(
        "--http-retries",
        type=int,
        default=2,
        help="How many retries to attempt after the initial HTTP request fails",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.75,
        help="Base sleep in seconds between HTTP retries",
    )
    parser.add_argument(
        "--clip-sample-head",
        type=int,
        default=0,
        help="How many clip IDs to sample from the start of clips_ids (excluding main video_ids)",
    )
    parser.add_argument(
        "--clip-sample-tail",
        type=int,
        default=0,
        help="How many clip IDs to sample from the end of clips_ids (excluding main video_ids)",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.http_retries < 0:
        parser.error("--http-retries must be greater than or equal to 0")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep must be greater than or equal to 0")
    if args.clip_sample_head < 0:
        parser.error("--clip-sample-head must be greater than or equal to 0")
    if args.clip_sample_tail < 0:
        parser.error("--clip-sample-tail must be greater than or equal to 0")
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


def http_get(url: str, timeout: float, retries: int = 0, retry_sleep: float = 0.0) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers=REQUEST_HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, "replace")
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            if retry_sleep > 0:
                time.sleep(retry_sleep * (attempt + 1))
    if last_error is None:
        raise RuntimeError("http_get failed without an exception")
    raise last_error


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


def list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = scalar_value(value, "").strip()
    return [text] if text else []


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


def parse_json_array_field(value: object) -> list[dict[str, object]]:
    text = scalar_value(value, "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def summarize_videos(videos: list[dict[str, object]]) -> OrderedDict[str, object]:
    state_counts: Counter[str] = Counter()
    upload_src_counts: Counter[str] = Counter()
    defn_key_counts: Counter[str] = Counter()
    targetid_nonempty = 0
    publish_date_nonempty = 0
    publish_date_examples: list[OrderedDict[str, str]] = []
    targetid_examples: list[OrderedDict[str, str]] = []
    unusual_upload_examples: list[OrderedDict[str, str]] = []

    for video in videos:
        fields = video.get("fields", {})
        if not isinstance(fields, dict):
            continue
        vid = scalar_value(fields.get("vid", ""))
        title = scalar_value(fields.get("title", ""))
        state = scalar_value(fields.get("state", ""))
        upload_src = scalar_value(fields.get("upload_src", ""))
        publish_date = scalar_value(fields.get("publish_date", "")).strip()
        targetid = scalar_value(fields.get("targetid", "")).strip()

        state_counts.update([state])
        upload_src_counts.update([upload_src])

        defn_expanded = video.get("defn_expanded", {})
        if isinstance(defn_expanded, dict):
            defn_key_counts.update(defn_expanded.keys())

        if publish_date:
            publish_date_nonempty += 1
            if len(publish_date_examples) < 12:
                publish_date_examples.append(
                    OrderedDict((("vid", vid), ("title", title), ("publish_date", publish_date)))
                )
        if targetid:
            targetid_nonempty += 1
            if len(targetid_examples) < 12:
                targetid_examples.append(
                    OrderedDict((("vid", vid), ("title", title), ("targetid", targetid)))
                )
        if upload_src and upload_src not in {"20"} and len(unusual_upload_examples) < 16:
            unusual_upload_examples.append(
                OrderedDict((("vid", vid), ("title", title), ("upload_src", upload_src)))
            )

    return OrderedDict(
        (
            ("video_count", len(videos)),
            ("state_counts", OrderedDict(sorted(state_counts.items()))),
            ("upload_src_counts", OrderedDict(sorted(upload_src_counts.items()))),
            ("defn_key_counts", OrderedDict(sorted(defn_key_counts.items()))),
            ("targetid_nonempty_count", targetid_nonempty),
            ("publish_date_nonempty_count", publish_date_nonempty),
            ("publish_date_examples", publish_date_examples),
            ("targetid_examples", targetid_examples),
            ("unusual_upload_examples", unusual_upload_examples),
        )
    )


def select_clip_probe_ids(
    cover_fields: dict[str, object],
    video_ids: list[str],
    clip_sample_head: int,
    clip_sample_tail: int,
) -> list[str]:
    clip_ids = unique_strings(list_value(cover_fields.get("clips_ids")))
    if not clip_ids or (clip_sample_head <= 0 and clip_sample_tail <= 0):
        return []

    main_video_set = set(video_ids)
    extra_clip_ids = [clip_id for clip_id in clip_ids if clip_id not in main_video_set]
    sampled: list[str] = []
    if clip_sample_head > 0:
        sampled.extend(extra_clip_ids[:clip_sample_head])
    if clip_sample_tail > 0:
        sampled.extend(extra_clip_ids[-clip_sample_tail:])
    return unique_strings(sampled)


def build_derived_summary(
    cover_fields: dict[str, object],
    video_ids: list[str],
    videos: list[dict[str, object]],
) -> OrderedDict[str, object]:
    nomal_items = parse_json_array_field(cover_fields.get("nomal_ids"))
    vip_items = parse_json_array_field(cover_fields.get("vip_ids"))
    return OrderedDict(
        (
            (
                "cover",
                OrderedDict(
                    (
                        ("video_ids_count", len(video_ids)),
                        ("clips_ids_count", len(list_value(cover_fields.get("clips_ids")))),
                        ("downright_count", len(list_value(cover_fields.get("downright")))),
                        (
                            "downright_unique",
                            sorted(set(list_value(cover_fields.get("downright")))),
                        ),
                        (
                            "nomal_f_counts",
                            OrderedDict(sorted(Counter(str(item.get("F")) for item in nomal_items).items())),
                        ),
                        (
                            "vip_f_counts",
                            OrderedDict(sorted(Counter(str(item.get("F")) for item in vip_items).items())),
                        ),
                    )
                ),
            ),
            ("videos", summarize_videos(videos)),
        )
    )


def survey_sample(
    url: str,
    timeout: float,
    batch_size: int,
    http_retries: int,
    retry_sleep: float,
    clip_sample_head: int,
    clip_sample_tail: int,
) -> OrderedDict[str, object]:
    sample: OrderedDict[str, object] = OrderedDict()
    sample["input_url"] = url

    try:
        cid = extract_cid_from_url(url)
        if not cid:
            raise RuntimeError("could not extract CID from URL")

        sample["cid"] = cid
        cover_request_url = build_api_1_url(cid)
        sample["cover_request"] = {"url": cover_request_url}

        cover = parse_cover_document(
            http_get(
                cover_request_url,
                timeout,
                retries=http_retries,
                retry_sleep=retry_sleep,
            )
        )
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
            videos.extend(
                parse_video_document(
                    http_get(
                        api_2_url,
                        timeout,
                        retries=http_retries,
                        retry_sleep=retry_sleep,
                    )
                )
            )

        if not videos:
            raise RuntimeError("API2 returned no video field records")

        sample["video_request_batches"] = video_batches
        sample["videos"] = videos
        sample["video_field_names"] = sorted(
            {field_name for video in videos for field_name in video["field_names"]}
        )
        sample["derived"] = build_derived_summary(cover["fields"], video_ids, videos)

        clip_probe_ids = select_clip_probe_ids(
            cover["fields"],
            video_ids,
            clip_sample_head=clip_sample_head,
            clip_sample_tail=clip_sample_tail,
        )
        if clip_probe_ids:
            clip_probe_videos: list[dict[str, object]] = []
            clip_request_batches: list[dict[str, object]] = []
            for batch in chunked(clip_probe_ids, batch_size):
                api_2_url = build_api_2_url(batch)
                clip_request_batches.append({"vids": batch, "url": api_2_url})
                clip_probe_videos.extend(
                    parse_video_document(
                        http_get(
                            api_2_url,
                            timeout,
                            retries=http_retries,
                            retry_sleep=retry_sleep,
                        )
                    )
                )
            sample["clip_probe"] = OrderedDict(
                (
                    ("clip_ids", clip_probe_ids),
                    ("request_batches", clip_request_batches),
                    ("videos", clip_probe_videos),
                    ("video_field_names", sorted(
                        {field_name for video in clip_probe_videos for field_name in video["field_names"]}
                    )),
                    ("derived", summarize_videos(clip_probe_videos)),
                )
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
    clip_video_counts: Counter[str] = Counter()
    defn_counts: Counter[str] = Counter()
    successful_sample_count = 0
    total_video_count = 0
    videos_with_defn_count = 0
    total_clip_video_count = 0

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

        clip_probe = sample.get("clip_probe", {})
        if isinstance(clip_probe, dict):
            for video in clip_probe.get("videos", []):
                if not isinstance(video, dict):
                    continue
                total_clip_video_count += 1
                clip_video_counts.update(video.get("field_names", []))

    return OrderedDict(
        (
            ("sample_count", len(samples)),
            ("successful_sample_count", successful_sample_count),
            ("failed_sample_count", len(samples) - successful_sample_count),
            ("video_count", total_video_count),
            ("clip_video_count", total_clip_video_count),
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
                "clip_video_field_frequency",
                build_frequency_report(clip_video_counts, total_clip_video_count, "clip_videos"),
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


def build_report(
    urls: list[str],
    timeout: float,
    batch_size: int,
    http_retries: int = 0,
    retry_sleep: float = 0.0,
    clip_sample_head: int = 0,
    clip_sample_tail: int = 0,
) -> OrderedDict[str, object]:
    samples = [
        survey_sample(
            url,
            timeout=timeout,
            batch_size=batch_size,
            http_retries=http_retries,
            retry_sleep=retry_sleep,
            clip_sample_head=clip_sample_head,
            clip_sample_tail=clip_sample_tail,
        )
        for url in urls
    ]
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
                        ("http_retries", http_retries),
                        ("retry_sleep_seconds", retry_sleep),
                        ("clip_sample_head", clip_sample_head),
                        ("clip_sample_tail", clip_sample_tail),
                    )
                ),
            ),
            ("samples", samples),
            ("summary", build_summary(samples)),
        )
    )


def main() -> int:
    args = parse_args()
    report = build_report(
        args.urls,
        timeout=args.timeout,
        batch_size=args.batch_size,
        http_retries=args.http_retries,
        retry_sleep=args.retry_sleep,
        clip_sample_head=args.clip_sample_head,
        clip_sample_tail=args.clip_sample_tail,
    )
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=args.indent))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
