from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

import tencent_video_field_survey as survey


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
FIELD_KEYS = (
    "pay_status",
    "positive_trailer",
    "state",
    "upload_src",
    "targetid",
    "F",
    "downright",
    "publish_date",
    "cover_list",
    "c_covers",
    "category_map",
)
SEMANTIC_KEYS = (
    "report_cover_pay_status",
    "report_vid_pay_status",
    "pay_status_exchange",
    "showGive",
    "attachIframe",
    "usePublishDate",
    "publishDate",
    "LINK_REPLACED",
    "VIDEO_CAN_NOT_PLAY_IN_COVER",
    "OFFLINE",
    "DELETED",
    "getCoverInfoBatch",
    "FillUnionInfo",
)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=\"([^\"]+\.js[^\"]*)\"')
SCRIPT_TAG_RE = re.compile(
    r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
SCRIPT_SRC_ATTR_RE = re.compile(r'src=\"([^\"]+)\"', re.IGNORECASE)
VID_PATTERN = re.compile(r"/cover/[^/]+/([^/]+)\.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Tencent Video HTML plus current detail/player bundles, then "
            "extract SSR / inline-script / bundle snippets and an API-side snapshot "
            "for key frontend-semantic fields."
        )
    )
    parser.add_argument("urls", nargs="+", help="Tencent Video page URLs")
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


def http_fetch(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_script_url(value: str) -> str:
    if value.startswith("//"):
        return f"https:{value}"
    return value


def find_snippet(text: str, needle: str, radius: int = 180) -> str | None:
    index = text.find(needle)
    if index < 0:
        return None
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return text[start:end]


def collect_script_urls(html: str) -> list[str]:
    urls: list[str] = []
    for match in SCRIPT_SRC_RE.finditer(html):
        url = normalize_script_url(match.group(1))
        if url not in urls:
            urls.append(url)
    return urls


def collect_script_blocks(html: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in SCRIPT_TAG_RE.finditer(html):
        attrs = match.group("attrs") or ""
        body = match.group("body") or ""
        src_match = SCRIPT_SRC_ATTR_RE.search(attrs)
        src = normalize_script_url(src_match.group(1)) if src_match else ""
        blocks.append({"src": src, "body": body})
    return blocks


def choose_main_bundle(script_urls: list[str]) -> str | None:
    for url in script_urls:
        if "video-detail-vue/assets/index-" in url and "legacy" not in url:
            return url
    for url in script_urls:
        if "video-detail-vue/assets/index-" in url:
            return url
    return script_urls[0] if script_urls else None


def choose_secondary_bundles(script_urls: list[str], main_bundle_url: str | None) -> list[str]:
    selected: list[str] = []
    for url in script_urls:
        if url == main_bundle_url:
            continue
        if "txv.core.js" in url or "superplayer" in url:
            selected.append(url)
    return selected


def extract_vid_from_url(url: str) -> str:
    match = VID_PATTERN.search(url)
    return match.group(1) if match else ""


def build_api_snapshot(url: str, timeout: float) -> dict[str, object]:
    cid = survey.extract_cid_from_url(url)
    if not cid:
        return {"error": "could not extract CID"}

    cover = survey.parse_cover_document(survey.http_get(survey.build_api_1_url(cid), timeout))
    video_ids = list(cover["video_ids"])
    requested_vid = extract_vid_from_url(url)
    selected_vid = requested_vid if requested_vid in video_ids else (video_ids[0] if video_ids else "")
    video_snapshot: dict[str, object] = {}
    if selected_vid:
        videos = survey.parse_video_document(
            survey.http_get(survey.build_api_2_url([selected_vid]), timeout)
        )
        if videos:
            fields = videos[0].get("fields", {})
            if isinstance(fields, dict):
                video_snapshot = {
                    key: fields.get(key)
                    for key in (
                        "vid",
                        "title",
                        "state",
                        "F",
                        "upload_src",
                        "publish_date",
                        "targetid",
                        "cover_list",
                        "c_covers",
                        "category_map",
                    )
                }

    cover_fields = cover.get("fields", {})
    if not isinstance(cover_fields, dict):
        cover_fields = {}
    return {
        "cid": cid,
        "requested_vid": requested_vid,
        "selected_vid": selected_vid,
        "cover_fields": {
            key: cover_fields.get(key)
            for key in (
                "title",
                "type",
                "type_name",
                "pay_status",
                "positive_trailer",
                "positive_content_id",
                "publish_date",
                "video_ids",
                "downright",
            )
        },
        "video_fields": video_snapshot,
    }


def build_hit_map(text: str, needles: tuple[str, ...]) -> dict[str, str | None]:
    return {key: find_snippet(text, key) for key in needles}


def inspect_page(url: str, timeout: float) -> dict[str, object]:
    html = http_fetch(url, timeout)
    script_blocks = collect_script_blocks(html)
    script_urls = collect_script_urls(html)
    main_bundle_url = choose_main_bundle(script_urls)
    secondary_bundle_urls = choose_secondary_bundles(script_urls, main_bundle_url)
    inline_script_text = "\n".join(
        block["body"] for block in script_blocks if block["body"] and not block["src"]
    )

    bundle_urls = [bundle for bundle in [main_bundle_url, *secondary_bundle_urls] if bundle]
    bundle_hits: dict[str, dict[str, str | None]] = {}
    semantic_hits: dict[str, dict[str, str | None]] = {}
    for bundle_url in bundle_urls:
        bundle_text = http_fetch(bundle_url, timeout)
        bundle_hits[bundle_url] = build_hit_map(bundle_text, FIELD_KEYS)
        semantic_hits[bundle_url] = build_hit_map(bundle_text, SEMANTIC_KEYS)

    return {
        "url": url,
        "has_vikor_context": "window.__vikor__context__" in html,
        "has_ssr_payloads": "window.__vikor__context__.ssrPayloads" in html,
        "script_count": len(script_urls),
        "main_bundle_url": main_bundle_url,
        "secondary_bundle_urls": secondary_bundle_urls,
        "api_snapshot": build_api_snapshot(url, timeout),
        "html_hits": build_hit_map(html, FIELD_KEYS),
        "inline_script_hits": build_hit_map(inline_script_text, FIELD_KEYS),
        "bundle_hits": bundle_hits,
        "semantic_hits": semantic_hits,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - older Python compatibility
        pass
    args = parse_args()
    results = []
    for url in args.urls:
        try:
            results.append(inspect_page(url, args.timeout))
        except urllib.error.URLError as exc:
            results.append(
                {
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    print(
        json.dumps(
            {
                "tool": "tencent_frontend_semantic_probe",
                "field_keys": list(FIELD_KEYS),
                "semantic_keys": list(SEMANTIC_KEYS),
                "pages": results,
            },
            ensure_ascii=False,
            indent=args.indent,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
