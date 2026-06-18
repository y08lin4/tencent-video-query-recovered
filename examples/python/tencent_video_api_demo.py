from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_1_URL = "https://data.video.qq.com/fcgi-bin/data"
API_2_URL = "https://union.video.qq.com/fcgi-bin/data"


def extract_cid_from_url(url: str) -> str | None:
    patterns = [
        r"/cover/([^/]+)/[^/]+\.html",
        r"/cover/([^/]+)\.html",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None


def format_duration(seconds: int | str | None) -> str:
    if seconds in (None, ""):
        return "-"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_size(value: int | float | str | None) -> str:
    if value in (None, ""):
        return "-"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size:.0f} {unit}"
        size /= 1024
    return "-"


def http_get(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


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


def fetch_cover_info(cid: str) -> dict:
    root = ET.fromstring(http_get(build_api_1_url(cid)))
    error_node = root.find(".//error")
    if error_node is not None and error_node.text:
        raise RuntimeError(error_node.text.strip())

    video_ids: list[str] = []
    for node in root.findall(".//video_ids"):
        text = (node.text or "").strip()
        if text:
            video_ids.extend([part.strip() for part in text.split(",") if part.strip()])

    return {
        "cid": cid,
        "title": (root.findtext(".//title") or "").strip(),
        "type": (root.findtext(".//type") or "").strip(),
        "type_name": (root.findtext(".//type_name") or "").strip(),
        "video_ids": video_ids,
        "pay_status": (root.findtext(".//pay_status") or "").strip(),
        "cover_pic_hz": (root.findtext(".//new_pic_hz") or "").strip(),
        "cover_pic_vt": (root.findtext(".//new_pic_vt") or "").strip(),
    }


def parse_defn(defn_raw: str) -> dict:
    if not defn_raw:
        return {}
    try:
        return json.loads(defn_raw)
    except json.JSONDecodeError:
        return {}


def fetch_video_details(vids: list[str], batch_size: int = 10) -> list[dict]:
    results: list[dict] = []
    for start in range(0, len(vids), batch_size):
        batch = vids[start : start + batch_size]
        root = ET.fromstring(http_get(build_api_2_url(batch)))
        error_node = root.find(".//error")
        if error_node is not None and error_node.text:
            raise RuntimeError(error_node.text.strip())

        for field in root.findall(".//field"):
            defn = parse_defn((field.findtext(".//defn") or "").strip())
            results.append(
                {
                    "vid": (field.findtext(".//vid") or "").strip(),
                    "title": (field.findtext(".//title") or "").strip(),
                    "duration_seconds": (field.findtext(".//duration") or "").strip(),
                    "duration": format_duration(field.findtext(".//duration")),
                    "url": (field.findtext(".//url") or "").strip(),
                    "cover_list": (field.findtext(".//cover_list") or "").strip(),
                    "defn": defn,
                    "audio": format_size(defn.get("audio")),
                    "sd": format_size(defn.get("sd")),
                    "hd": format_size(defn.get("hd")),
                    "shd": format_size(defn.get("shd")),
                    "fhd": format_size(defn.get("fhd")),
                    "uhd": format_size(defn.get("uhd")),
                    "source": format_size(defn.get("source")),
                }
            )
    return results


def print_text_table(items: list[dict]) -> None:
    headers = ["title", "vid", "duration", "audio", "sd", "hd", "shd", "fhd", "uhd"]
    widths = {header: len(header) for header in headers}
    for item in items:
        for header in headers:
            widths[header] = max(widths[header], len(str(item.get(header, ""))))

    line = " | ".join(header.ljust(widths[header]) for header in headers)
    sep = "-+-".join("-" * widths[header] for header in headers)
    print(line)
    print(sep)
    for item in items:
        print(" | ".join(str(item.get(header, "")).ljust(widths[header]) for header in headers))


def main() -> None:
    parser = argparse.ArgumentParser(description="Tencent video dual-API demo")
    parser.add_argument("--url", help="Tencent video page URL")
    parser.add_argument("--cid", help="Cover ID")
    parser.add_argument("--vid", action="append", dest="vids", help="Video ID, repeatable")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    cid = args.cid
    if not cid and args.url:
        cid = extract_cid_from_url(args.url)
    if not cid and not args.vids:
        raise SystemExit("Provide --url, --cid, or at least one --vid")

    cover_info = None
    vids = list(args.vids or [])
    if cid:
        cover_info = fetch_cover_info(cid)
        if not vids:
            vids = cover_info["video_ids"]

    details = fetch_video_details(vids) if vids else []
    payload = {
        "cid": cid,
        "cover_info": cover_info,
        "video_details": details,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if cover_info:
        print(f"CID: {cover_info['cid']}")
        print(f"标题: {cover_info['title']}")
        print(f"类型: {cover_info['type_name']} ({cover_info['type']})")
        print(f"VIDs: {', '.join(cover_info['video_ids']) or '-'}")
        print()

    if details:
        print_text_table(details)


if __name__ == "__main__":
    main()
