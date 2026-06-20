from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import datetime as dt
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

import tencent_video_field_survey as survey


SEARCH_URL = (
    "https://pbaccess.video.qq.com/"
    "trpc.videosearch.mobile_search.MultiTerminalSearch/"
    "MbSearch?vversion_platform=2"
)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://v.qq.com",
    "Origin": "https://v.qq.com",
}
DEFAULT_FEATURE_LIST = [
    "DEFAULT_FEFEATURE",
    "PC_SHORT_VIDEOS_WATERFALL",
    "PC_WANT_EPISODE_V2",
    "PC_WANT_EPISODE",
]
CID_PATTERN = re.compile(r"/x/cover/([A-Za-z0-9]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query the Tencent Video search backend, extract cover CIDs, "
            "and optionally resolve them through API1."
        )
    )
    parser.add_argument("queries", nargs="+", help="Search queries to submit")
    parser.add_argument(
        "--pagesize",
        type=int,
        default=20,
        help="Requested search backend page size",
    )
    parser.add_argument(
        "--max-resolve",
        type=int,
        default=120,
        help="Maximum number of unique CIDs to resolve through API1",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=2,
        help="How many retries to attempt after the initial request fails",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.75,
        help="Base sleep in seconds between HTTP retries",
    )
    parser.add_argument(
        "--front-version",
        default="26060108",
        help="frontVersion to send in extraInfo",
    )
    parser.add_argument(
        "--version",
        default="26022601",
        help="version to send in the main body",
    )
    parser.add_argument(
        "--client-type",
        type=int,
        default=1,
        help="clientType to send in the main body",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path; when omitted, write JSON to stdout",
    )
    args = parser.parse_args()
    if args.pagesize <= 0:
        parser.error("--pagesize must be greater than 0")
    if args.max_resolve < 0:
        parser.error("--max-resolve must be greater than or equal to 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.http_retries < 0:
        parser.error("--http-retries must be greater than or equal to 0")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep must be greater than or equal to 0")
    return args


def build_payload(
    query: str,
    pagesize: int,
    version: str,
    client_type: int,
    front_version: str,
) -> OrderedDict[str, object]:
    return OrderedDict(
        (
            ("version", version),
            ("clientType", client_type),
            ("filterValue", ""),
            ("uuid", f"debug-{query}"),
            ("retry", 0),
            ("query", query),
            ("pagenum", 0),
            ("pagesize", pagesize),
            ("queryFrom", 0),
            ("sceneId", 0),
            ("searchDatakey", ""),
            ("transInfo", ""),
            ("isneedQc", True),
            ("preQid", ""),
            ("adClientInfo", ""),
            (
                "extraInfo",
                OrderedDict(
                    (
                        ("isNewMarkLabel", "1"),
                        ("multi_terminal_pc", "1"),
                        ("themeType", "0"),
                        ("sugRelatedIds", "{}"),
                        ("appVersion", ""),
                        ("frontVersion", front_version),
                    )
                ),
            ),
            ("featureList", list(DEFAULT_FEATURE_LIST)),
        )
    )


def http_post_json(
    url: str,
    payload: OrderedDict[str, object],
    timeout: float,
    retries: int = 0,
    retry_sleep: float = 0.0,
) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            data=data,
            headers=REQUEST_HEADERS,
            method="POST",
        )
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
        raise RuntimeError("http_post_json failed without an exception")
    raise last_error


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


def extract_cids(response_text: str) -> list[str]:
    normalized = response_text.replace("\\/", "/")
    return unique_strings(match.group(1) for match in CID_PATTERN.finditer(normalized))


def resolve_cid(
    cid: str,
    timeout: float,
    http_retries: int,
    retry_sleep: float,
) -> OrderedDict[str, str]:
    cover = survey.parse_cover_document(
        survey.http_get(
            survey.build_api_1_url(cid),
            timeout,
            retries=http_retries,
            retry_sleep=retry_sleep,
        )
    )
    fields = cover["fields"]
    assert isinstance(fields, dict)
    return OrderedDict(
        (
            ("cid", cid),
            ("title", survey.scalar_value(fields.get("title", ""))),
            ("type", survey.scalar_value(fields.get("type", ""))),
            ("type_name", survey.scalar_value(fields.get("type_name", ""))),
            ("pay_status", survey.scalar_value(fields.get("pay_status", ""))),
            (
                "positive_trailer",
                survey.scalar_value(fields.get("positive_trailer", "")),
            ),
            (
                "positive_content_id",
                survey.scalar_value(fields.get("positive_content_id", "")),
            ),
        )
    )


def build_summary(resolved: list[OrderedDict[str, str]]) -> OrderedDict[str, object]:
    type_counts: Counter[str] = Counter()
    pay_status_counts: Counter[str] = Counter()
    positive_trailer_counts: Counter[str] = Counter()
    positive_content_id_counts: Counter[str] = Counter()
    for row in resolved:
        type_counts.update([f'{row["type"]}/{row["type_name"]}'])
        pay_status_counts.update([row["pay_status"]])
        positive_trailer_counts.update([row["positive_trailer"]])
        positive_content_id_counts.update([row["positive_content_id"]])
    return OrderedDict(
        (
            ("resolved_count", len(resolved)),
            ("type_counts", OrderedDict(sorted(type_counts.items()))),
            ("pay_status_counts", OrderedDict(sorted(pay_status_counts.items()))),
            (
                "positive_trailer_counts",
                OrderedDict(sorted(positive_trailer_counts.items())),
            ),
            (
                "positive_content_id_counts",
                OrderedDict(sorted(positive_content_id_counts.items())),
            ),
        )
    )


def main() -> int:
    args = parse_args()
    per_query: list[OrderedDict[str, object]] = []
    all_cids: list[str] = []
    errors: list[OrderedDict[str, str]] = []

    for query in args.queries:
        payload = build_payload(
            query=query,
            pagesize=args.pagesize,
            version=args.version,
            client_type=args.client_type,
            front_version=args.front_version,
        )
        try:
            response_text = http_post_json(
                SEARCH_URL,
                payload,
                timeout=args.timeout,
                retries=args.http_retries,
                retry_sleep=args.retry_sleep,
            )
        except Exception as exc:  # pragma: no cover - runtime reporting path
            errors.append(
                OrderedDict(
                    (
                        ("stage", "search"),
                        ("query", query),
                        ("error", str(exc)),
                    )
                )
            )
            continue

        query_cids = extract_cids(response_text)
        all_cids.extend(query_cids)
        per_query.append(
            OrderedDict(
                (
                    ("query", query),
                    ("cid_count", len(query_cids)),
                    ("sample_cids", query_cids[:12]),
                    (
                        "sample_urls",
                        [f"https://v.qq.com/x/cover/{cid}.html" for cid in query_cids[:8]],
                    ),
                )
            )
        )

    unique_cids = unique_strings(all_cids)
    resolved: list[OrderedDict[str, str]] = []
    for cid in unique_cids[: args.max_resolve]:
        try:
            resolved.append(
                resolve_cid(
                    cid,
                    timeout=args.timeout,
                    http_retries=args.http_retries,
                    retry_sleep=args.retry_sleep,
                )
            )
        except Exception as exc:  # pragma: no cover - runtime reporting path
            errors.append(
                OrderedDict(
                    (
                        ("stage", "api1"),
                        ("cid", cid),
                        ("error", str(exc)),
                    )
                )
            )

    report = OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("tool", "tencent_search_seed_probe"),
                        (
                            "generated_at",
                            dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                        ),
                        ("query_count", len(args.queries)),
                        ("pagesize", args.pagesize),
                        ("max_resolve", args.max_resolve),
                        ("timeout_seconds", args.timeout),
                        ("http_retries", args.http_retries),
                        ("retry_sleep_seconds", args.retry_sleep),
                        ("version", args.version),
                        ("client_type", args.client_type),
                        ("front_version", args.front_version),
                    )
                ),
            ),
            ("queries", per_query),
            ("unique_cid_count", len(unique_cids)),
            ("resolved", resolved),
            ("summary", build_summary(resolved)),
            ("errors", errors),
        )
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=args.indent)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
