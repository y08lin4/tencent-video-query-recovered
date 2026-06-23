from __future__ import annotations

import argparse
from collections import OrderedDict
import json
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

API_1_DEFAULTS = OrderedDict(
    (
        ("tid", "431"),
        ("idlist", "mzc00200idzf2m8"),
        ("appid", "10001005"),
        ("appkey", "0d1a9ddd94de871b"),
    )
)

API_2_DEFAULTS = OrderedDict(
    (
        ("otype", "xml"),
        ("tid", "535"),
        ("appid", "20001238"),
        ("appkey", "6c03bbe9658448a4"),
        ("union_platform", "3"),
        ("idlist", "z4102qfi0x4"),
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Tencent Video API parameter validation and response shape."
    )
    parser.add_argument("api", choices=("api1", "api2"), help="Which API to probe")
    parser.add_argument(
        "--case-profile",
        choices=("baseline", "appid_numeric_focus", "appid_numeric_band"),
        default="baseline",
        help="Which case set to run. `baseline` keeps the original contract matrix; `appid_numeric_focus` zooms in on representative numeric appid branches; `appid_numeric_band` sweeps a contiguous numeric appid band.",
    )
    parser.add_argument(
        "--appid-start",
        type=int,
        default=None,
        help="Start of the numeric appid band when --case-profile=appid_numeric_band.",
    )
    parser.add_argument(
        "--appid-end",
        type=int,
        default=None,
        help="End of the numeric appid band when --case-profile=appid_numeric_band.",
    )
    parser.add_argument(
        "--sample-id",
        default="",
        help="CID for api1 or VID/idlist for api2. Defaults to a known working sample.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Retry count for transient transport failures.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation.",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.retries < 0:
        parser.error("--retries must be >= 0")
    return args


def build_url(base: str, params: OrderedDict[str, str | None]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        pairs.append((key, value))
    return f"{base}?{urllib.parse.urlencode(pairs)}"


def http_fetch(url: str, timeout: float, retries: int) -> tuple[int | None, str, str]:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    last_error = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.status, response.read().decode(charset, "replace"), ""
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset() or "utf-8"
            body = exc.read().decode(charset, "replace")
            return exc.code, body, ""
        except Exception as exc:  # pragma: no cover - runtime reporting path
            last_error = str(exc)
            if attempt < retries:
                time.sleep(1)
                continue
    return None, "", last_error


def parse_xml_summary(xml_text: str, api: str) -> OrderedDict[str, object]:
    summary: OrderedDict[str, object] = OrderedDict()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        summary["parse_error"] = str(exc)
        return summary

    def text(path: str) -> str:
        return (root.findtext(path) or "").strip()

    summary["root_tag"] = root.tag
    summary["errorno"] = text(".//errorno")
    summary["errormsg"] = text(".//errormsg") or text(".//error")
    summary["retcode"] = text(".//retcode")

    per_result: list[OrderedDict[str, str]] = []
    for result in root.findall(".//results")[:5]:
        row: OrderedDict[str, str] = OrderedDict()
        row["id"] = (result.findtext("./id") or "").strip()
        row["retcode"] = (result.findtext("./retcode") or "").strip()
        row["vid"] = (result.findtext(".//vid") or "").strip()
        row["cover_id"] = (result.findtext(".//cover_id") or "").strip()
        row["title"] = (result.findtext(".//title") or "").strip()
        per_result.append(row)
    if per_result:
        summary["sample_results"] = per_result

    if api == "api1":
        summary["cover_results_count"] = len(root.findall(".//results"))
        summary["video_ids_count"] = len(root.findall(".//video_ids"))
        summary["clips_ids_count"] = len(root.findall(".//clips_ids"))
        summary["title"] = text(".//title")
        summary["cover_id"] = text(".//cover_id")
        summary["pay_status"] = text(".//pay_status")
        summary["type"] = text(".//type")
        summary["type_name"] = text(".//type_name")
    else:
        results = root.findall(".//results")
        summary["results_count"] = len(results)
        vids: list[str] = []
        titles: list[str] = []
        for result in results[:5]:
            vids.append((result.findtext(".//vid") or "").strip())
            titles.append((result.findtext(".//title") or "").strip())
        summary["sample_vids"] = vids
        summary["sample_titles"] = titles
    return summary


def make_baseline_cases(
    api: str, sample_id: str
) -> list[tuple[str, OrderedDict[str, str | None]]]:
    if api == "api1":
        params = API_1_DEFAULTS.copy()
        if sample_id:
            params["idlist"] = sample_id
        cases = [
            ("baseline", params.copy()),
            ("missing_tid", override(params, tid=None)),
            ("zero_tid", override(params, tid="0")),
            ("alpha_tid", override(params, tid="abc")),
            ("missing_appid", override(params, appid=None)),
            ("missing_appid_and_appkey", override(params, appid=None, appkey=None)),
            ("appid_1", override(params, appid="1")),
            ("appid_99999", override(params, appid="99999")),
            ("appid_text", override(params, appid="notanumber")),
            ("appid_text_no_appkey", override(params, appid="notanumber", appkey=None)),
            ("missing_appkey", override(params, appkey=None)),
            ("wrong_appkey", override(params, appkey="deadbeef")),
            ("missing_idlist", override(params, idlist=None)),
            ("empty_idlist", override(params, idlist="")),
            ("spaces_idlist", override(params, idlist="  ")),
            ("comma_idlist", override(params, idlist=",")),
            ("double_comma_idlist", override(params, idlist=",,")),
            ("illegal_cid", override(params, idlist="invalidcid123")),
            ("empty_shape_cid", override(params, idlist="mzc00000zzzzzzz")),
            ("duplicate_cid", override(params, idlist=f"{params['idlist']},{params['idlist']}")),
            ("mixed_valid_illegal_cid", override(params, idlist=f"invalidcid123,{params['idlist']}")),
            ("mixed_valid_empty_shape_cid", override(params, idlist=f"mzc00000zzzzzzz,{params['idlist']}")),
        ]
        return cases

    params = API_2_DEFAULTS.copy()
    if sample_id:
        params["idlist"] = sample_id
    cases = [
        ("baseline", params.copy()),
        ("missing_otype", override(params, otype=None)),
        ("wrong_otype_json", override(params, otype="json")),
        ("wrong_otype_text", override(params, otype="text")),
        ("missing_tid", override(params, tid=None)),
        ("zero_tid", override(params, tid="0")),
        ("alpha_tid", override(params, tid="abc")),
        ("missing_appid", override(params, appid=None)),
        ("missing_appid_and_appkey", override(params, appid=None, appkey=None)),
        ("appid_1", override(params, appid="1")),
        ("appid_99999", override(params, appid="99999")),
        ("appid_text", override(params, appid="notanumber")),
        ("appid_text_no_appkey", override(params, appid="notanumber", appkey=None)),
        ("missing_appkey", override(params, appkey=None)),
        ("wrong_appkey", override(params, appkey="deadbeef")),
        ("missing_union_platform", override(params, union_platform=None)),
        ("wrong_union_platform", override(params, union_platform="999")),
        ("missing_idlist", override(params, idlist=None)),
        ("empty_idlist", override(params, idlist="")),
        ("spaces_idlist", override(params, idlist="  ")),
        ("comma_idlist", override(params, idlist=",")),
        ("double_comma_idlist", override(params, idlist=",,")),
        ("invalid_vid", override(params, idlist="zzzzzzzzzzz")),
        ("mixed_valid_invalid_vid", override(params, idlist=f"{params['idlist']},zzzzzzzzzzz")),
    ]
    return cases


def make_appid_numeric_focus_cases(
    api: str, sample_id: str
) -> list[tuple[str, OrderedDict[str, str | None]]]:
    if api == "api1":
        params = API_1_DEFAULTS.copy()
        if sample_id:
            params["idlist"] = sample_id
        cases: list[tuple[str, OrderedDict[str, str | None]]] = [
            ("baseline", params.copy()),
            ("appid_1", override(params, appid="1")),
            ("appid_2", override(params, appid="2")),
            ("appid_3", override(params, appid="3")),
            ("appid_10", override(params, appid="10")),
            ("appid_100", override(params, appid="100")),
            ("appid_1000", override(params, appid="1000")),
            ("appid_99999", override(params, appid="99999")),
        ]
        for value in range(10001000, 10001011):
            cases.append((f"appid_{value}", override(params, appid=str(value))))
        cases.extend(
            [
                (
                    "appid_10001004_missing_appkey",
                    override(params, appid="10001004", appkey=None),
                ),
                (
                    "appid_10001004_wrong_appkey",
                    override(params, appid="10001004", appkey="deadbeef"),
                ),
            ]
        )
        return cases

    params = API_2_DEFAULTS.copy()
    if sample_id:
        params["idlist"] = sample_id
    cases = [
        ("baseline", params.copy()),
        ("appid_1", override(params, appid="1")),
        ("appid_2", override(params, appid="2")),
        ("appid_3", override(params, appid="3")),
        ("appid_10", override(params, appid="10")),
        ("appid_100", override(params, appid="100")),
        ("appid_1000", override(params, appid="1000")),
        ("appid_99999", override(params, appid="99999")),
    ]
    for value in range(20001233, 20001244):
        cases.append((f"appid_{value}", override(params, appid=str(value))))
    cases.extend(
        [
            (
                "appid_20001237_missing_appkey",
                override(params, appid="20001237", appkey=None),
            ),
            (
                "appid_20001237_wrong_appkey",
                override(params, appid="20001237", appkey="deadbeef"),
            ),
        ]
    )
    return cases


def make_appid_numeric_band_cases(
    api: str, sample_id: str, appid_start: int | None, appid_end: int | None
) -> list[tuple[str, OrderedDict[str, str | None]]]:
    if api == "api1":
        params = API_1_DEFAULTS.copy()
        if sample_id:
            params["idlist"] = sample_id
        start = 10000995 if appid_start is None else appid_start
        end = 10001015 if appid_end is None else appid_end
    else:
        params = API_2_DEFAULTS.copy()
        if sample_id:
            params["idlist"] = sample_id
        start = 20001228 if appid_start is None else appid_start
        end = 20001248 if appid_end is None else appid_end
    if start > end:
        raise ValueError("appid_start must be <= appid_end")
    cases: list[tuple[str, OrderedDict[str, str | None]]] = [
        ("baseline", params.copy()),
        ("appid_1", override(params, appid="1")),
    ]
    for value in range(start, end + 1):
        cases.append((f"appid_{value}", override(params, appid=str(value))))
    return cases


def make_cases(
    api: str,
    sample_id: str,
    case_profile: str,
    appid_start: int | None,
    appid_end: int | None,
) -> list[tuple[str, OrderedDict[str, str | None]]]:
    if case_profile == "appid_numeric_focus":
        return make_appid_numeric_focus_cases(api, sample_id)
    if case_profile == "appid_numeric_band":
        return make_appid_numeric_band_cases(api, sample_id, appid_start, appid_end)
    return make_baseline_cases(api, sample_id)


def override(
    params: OrderedDict[str, str | None], **updates: str | None
) -> OrderedDict[str, str | None]:
    next_params = params.copy()
    for key, value in updates.items():
        next_params[key] = value
    return next_params


def main() -> int:
    args = parse_args()
    base_url = API_1_URL if args.api == "api1" else API_2_URL
    cases = make_cases(
        args.api,
        args.sample_id.strip(),
        args.case_profile,
        args.appid_start,
        args.appid_end,
    )

    results: list[OrderedDict[str, object]] = []
    for name, params in cases:
        url = build_url(base_url, params)
        status, body, transport_error = http_fetch(
            url, timeout=args.timeout, retries=args.retries
        )
        row: OrderedDict[str, object] = OrderedDict()
        row["case"] = name
        row["url"] = url
        row["http_status"] = status
        if transport_error:
            row["transport_error"] = transport_error
        row["body_prefix"] = body[:200]
        row["xml_summary"] = parse_xml_summary(body, args.api) if body else OrderedDict()
        results.append(row)

    report = OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("api", args.api),
                        ("case_profile", args.case_profile),
                        ("appid_start", args.appid_start),
                        ("appid_end", args.appid_end),
                        ("timeout_seconds", args.timeout),
                        ("retries", args.retries),
                    )
                ),
            ),
            ("results", results),
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=args.indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
