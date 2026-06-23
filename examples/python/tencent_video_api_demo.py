from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_1_URL = "https://data.video.qq.com/fcgi-bin/data"
API_2_URL = "https://union.video.qq.com/fcgi-bin/data"

API_1_DEFAULT_PARAMS = {
    "tid": "431",
    "appid": "10001005",
    "appkey": "0d1a9ddd94de871b",
}

API_2_DEFAULT_PARAMS = {
    "otype": "xml",
    "tid": "535",
    "appid": "20001238",
    "appkey": "6c03bbe9658448a4",
    "union_platform": "3",
}

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}


def build_pair_guidance_for_api(
    api_label: str,
    params: dict[str, str],
    canonical_params: dict[str, str],
) -> dict[str, object]:
    appid = str(params.get("appid") or "").strip()
    appkey = str(params.get("appkey") or "").strip()
    canonical_appid = str(canonical_params.get("appid") or "").strip()
    canonical_appkey = str(canonical_params.get("appkey") or "").strip()

    appid_matches = appid == canonical_appid
    appkey_matches = appkey == canonical_appkey
    using_canonical_pair = appid_matches and appkey_matches
    if using_canonical_pair:
        override_shape = "canonical_pair"
        advisories: list[str] = []
    elif appid_matches != appkey_matches:
        override_shape = "partial_override"
        advisories = [
            (
                f"{api_label}: current appid/appkey is a partial override relative to the canonical pair "
                f"{canonical_appid}+{canonical_appkey}; treat them as one branch-gating pair unless you are deliberately probing."
            )
        ]
    else:
        override_shape = "noncanonical_pair"
        advisories = [
            (
                f"{api_label}: current appid/appkey is off the canonical pair "
                f"{canonical_appid}+{canonical_appkey}; in the current tested anonymous scope, keep the pair together unless you are deliberately probing numeric appid families."
            )
        ]

    return {
        "api": api_label,
        "canonical_pair": {
            "appid": canonical_appid,
            "appkey": canonical_appkey,
        },
        "current_pair": {
            "appid": appid,
            "appkey": appkey,
        },
        "using_canonical_pair": using_canonical_pair,
        "override_shape": override_shape,
        "advisories": advisories,
    }


def build_pair_guidance(
    api1_params: dict[str, str],
    api2_params: dict[str, str],
) -> list[dict[str, object]]:
    return [
        build_pair_guidance_for_api("api1", api1_params, API_1_DEFAULT_PARAMS),
        build_pair_guidance_for_api("api2", api2_params, API_2_DEFAULT_PARAMS),
    ]


def has_meaningful_value(value: object) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return str(value or "").strip() != ""


def split_csv_values(values: list[str] | tuple[str, ...] | None) -> list[str]:
    output: list[str] = []
    for value in values or []:
        for part in str(value or "").split(","):
            part = part.strip()
            if part:
                output.append(part)
    return output


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


def load_request_headers(
    env_json_path: str | None,
    env_name: str | None,
) -> tuple[dict[str, str], str | None]:
    if not env_json_path:
        return {}, None

    payload = json.loads(Path(env_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("env json root must be an object")

    resolved_env_name = env_name
    selected: object
    if env_name:
        if env_name not in payload:
            available = ", ".join(sorted(str(key) for key in payload))
            raise RuntimeError(f"env name {env_name!r} not found in env json; available: {available}")
        selected = payload[env_name]
    elif all(isinstance(value, str) for value in payload.values()):
        selected = payload
    elif len(payload) == 1:
        resolved_env_name, selected = next(iter(payload.items()))
    else:
        available = ", ".join(sorted(str(key) for key in payload))
        raise RuntimeError(
            "env json contains multiple named environments; pass --env-name from: "
            f"{available}"
        )

    if not isinstance(selected, dict):
        raise RuntimeError("selected env payload must be an object of request headers")

    headers = {}
    for key, value in selected.items():
        header_name = str(key).strip()
        header_value = str(value or "").strip()
        if header_name and header_value:
            headers[header_name] = header_value
    return headers, str(resolved_env_name) if resolved_env_name else None


def http_get(url: str, timeout: int = 10, extra_headers: dict[str, str] | None = None) -> str:
    headers = dict(DEFAULT_REQUEST_HEADERS)
    headers.update(extra_headers or {})
    req = urllib.request.Request(
        url,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def apply_overrides(base: dict[str, str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(base)
    for key, value in (overrides or {}).items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def build_api_1_url(cid: str, overrides: dict[str, str] | None = None) -> str:
    params = apply_overrides(API_1_DEFAULT_PARAMS, overrides)
    params["idlist"] = cid
    return f"{API_1_URL}?{urllib.parse.urlencode(params)}"


def build_api_2_url(vids: list[str], overrides: dict[str, str] | None = None) -> str:
    params = apply_overrides(API_2_DEFAULT_PARAMS, overrides)
    params["idlist"] = ",".join(vids)
    return f"{API_2_URL}?{urllib.parse.urlencode(params)}"


def parse_api1_cover_result(result_node: ET.Element) -> dict:
    field = result_node.find("./fields")
    if field is None:
        return {}

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
    video_ids = [
        part.strip()
        for node in field.findall("./video_ids")
        for part in (node.text or "").split(",")
        if part.strip()
    ]
    extra_field_keys: list[str] = []
    extra_nonempty_fields: dict[str, str] = {}
    for child in list(field):
        tag = str(child.tag or "").strip()
        if not tag or tag in core_field_tags:
            continue
        extra_field_keys.append(tag)
        value = (child.text or "").strip()
        if value:
            extra_nonempty_fields[tag] = value
    cid = (field.findtext("./cover_id") or result_node.findtext("./id") or "").strip()
    return {
        "cid": cid,
        "title": (field.findtext("./title") or "").strip(),
        "type": (field.findtext("./type") or "").strip(),
        "type_name": (field.findtext("./type_name") or "").strip(),
        "video_ids": video_ids,
        "pay_status": (field.findtext("./pay_status") or "").strip(),
        "cover_pic_hz": (field.findtext("./new_pic_hz") or "").strip(),
        "cover_pic_vt": (field.findtext("./new_pic_vt") or "").strip(),
        "extra_field_keys": extra_field_keys,
        "extra_nonempty_fields": extra_nonempty_fields,
    }


def summarize_api1_batch(requested_cids: list[str], cover_infos: list[dict]) -> dict:
    aggregated_video_ids = [
        vid
        for cover in cover_infos
        for vid in (cover.get("video_ids") or [])
        if str(vid or "").strip()
    ]
    return {
        "requested_cids": requested_cids,
        "requested_cid_count": len(requested_cids),
        "returned_cover_count": len(cover_infos),
        "returned_cids": [str(cover.get("cid") or "").strip() for cover in cover_infos if str(cover.get("cid") or "").strip()],
        "aggregated_video_ids_count": len(aggregated_video_ids),
        "aggregated_video_ids_head": aggregated_video_ids[:10],
    }


def fetch_cover_infos(
    cids: list[str],
    api1_params: dict[str, str] | None = None,
    request_headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict]:
    root = ET.fromstring(
        http_get(
            build_api_1_url(",".join(cids), overrides=api1_params),
            timeout=timeout,
            extra_headers=request_headers,
        )
    )
    error_text = (root.findtext(".//errormsg") or root.findtext(".//error") or "").strip()
    error_no = (root.findtext(".//errorno") or "").strip()
    if error_text or (error_no and error_no != "0"):
        raise RuntimeError(error_text or f"API1 errorno={error_no}")
    return [cover for node in root.findall("./results") if (cover := parse_api1_cover_result(node))]


def parse_defn(defn_raw: str) -> dict:
    if isinstance(defn_raw, dict):
        return defn_raw
    if not defn_raw:
        return {}
    try:
        return json.loads(defn_raw)
    except json.JSONDecodeError:
        return {}


def parse_jsonp_payload(body: str) -> dict:
    prefix = "QZOutputJson="
    stripped = body.strip()
    if stripped.startswith(prefix):
        payload = stripped[len(prefix) :].strip()
    else:
        open_paren = stripped.find("(")
        close_paren = stripped.rfind(")")
        if open_paren < 0 or close_paren <= open_paren:
            raise RuntimeError("API2 JSONP wrapper missing or unparseable")
        payload = stripped[open_paren + 1 : close_paren].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise RuntimeError("API2 JSONP payload is not an object")
    return data


def is_api2_empty_shell_row(row: dict) -> bool:
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
    return not any(has_meaningful_value(value) for value in meaningful_fields)


def summarize_api2_batch(rows: list[dict]) -> dict:
    empty_shell_count = sum(1 for row in rows if row.get("empty_shell"))
    return {
        "results_count": len(rows),
        "empty_shell_count": empty_shell_count,
        "nonempty_result_count": len(rows) - empty_shell_count,
        "all_results_empty_shell": bool(rows) and empty_shell_count == len(rows),
        "caller_rule": (
            "Treat top-level API2 success plus all results empty_shell=true as an all-invalid/empty-shell batch; "
            "do not rely on top-level errorno or per-result retcode alone."
        ),
    }


def normalize_multi_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    text = str(value).strip()
    return [text] if text else []


def fetch_video_details(
    vids: list[str],
    batch_size: int = 10,
    api2_params: dict[str, str] | None = None,
    request_headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict]:
    results: list[dict] = []
    merged_api2_params = apply_overrides(API_2_DEFAULT_PARAMS, api2_params)
    otype = merged_api2_params.get("otype", "xml")
    for start in range(0, len(vids), batch_size):
        batch = vids[start : start + batch_size]
        body = http_get(
            build_api_2_url(batch, overrides=merged_api2_params),
            timeout=timeout,
            extra_headers=request_headers,
        )

        if otype == "json":
            data = parse_jsonp_payload(body)
            error_text = str(data.get("errormsg", "")).strip()
            error_no = str(data.get("errorno", "")).strip()
            if error_text or (error_no and error_no != "0"):
                raise RuntimeError(error_text or f"API2 errorno={error_no}")

            for result_node in data.get("results", []):
                if not isinstance(result_node, dict):
                    continue
                field = result_node.get("fields") or {}
                if not isinstance(field, dict):
                    continue

                defn = parse_defn(field.get("defn", {}))
                row = {
                    "result_id": str(result_node.get("id") or "").strip(),
                    "retcode": str(result_node.get("retcode") or "").strip(),
                    "vid": str(field.get("vid") or "").strip(),
                    "title": str(field.get("title") or "").strip(),
                    "duration_seconds": str(field.get("duration") or "").strip(),
                    "duration": format_duration(field.get("duration")),
                    "url": str(field.get("url") or "").strip(),
                    "cover_list": normalize_multi_value(field.get("cover_list")),
                    "category_map": normalize_multi_value(field.get("category_map")),
                    "vwh": normalize_multi_value(field.get("vWH")),
                    "defn": defn,
                    "state": str(field.get("state") or "").strip(),
                    "upload_src": str(field.get("upload_src") or "").strip(),
                    "create_time": str(field.get("create_time") or "").strip(),
                    "modify_time": str(field.get("modify_time") or "").strip(),
                    "audio": format_size(defn.get("audio")),
                    "sd": format_size(defn.get("sd")),
                    "hd": format_size(defn.get("hd")),
                    "shd": format_size(defn.get("shd")),
                    "fhd": format_size(defn.get("fhd")),
                    "uhd": format_size(defn.get("uhd")),
                    "source": format_size(defn.get("source")),
                }
                row["empty_shell"] = is_api2_empty_shell_row(row)
                results.append(row)
            continue

        root = ET.fromstring(body)
        error_text = (root.findtext(".//errormsg") or root.findtext(".//error") or "").strip()
        error_no = (root.findtext(".//errorno") or "").strip()
        if error_text or (error_no and error_no != "0"):
            raise RuntimeError(error_text or f"API2 errorno={error_no}")

        for result_node in root.findall(".//results"):
            field = result_node.find("./fields")
            if field is None:
                continue

            defn_raw = html.unescape((field.findtext("./defn") or "").strip())
            defn = parse_defn(defn_raw)
            cover_list = [(node.text or "").strip() for node in field.findall("./cover_list") if (node.text or "").strip()]
            category_map = [(node.text or "").strip() for node in field.findall("./category_map") if (node.text or "").strip()]
            vwh = [(node.text or "").strip() for node in field.findall("./vWH") if (node.text or "").strip()]

            row = {
                "result_id": (result_node.findtext("./id") or "").strip(),
                "retcode": (result_node.findtext("./retcode") or "").strip(),
                "vid": (field.findtext("./vid") or "").strip(),
                "title": (field.findtext("./title") or "").strip(),
                "duration_seconds": (field.findtext("./duration") or "").strip(),
                "duration": format_duration(field.findtext("./duration")),
                "url": (field.findtext("./url") or "").strip(),
                "cover_list": cover_list,
                "category_map": category_map,
                "vwh": vwh,
                "defn": defn,
                "state": (field.findtext("./state") or "").strip(),
                "upload_src": (field.findtext("./upload_src") or "").strip(),
                "create_time": (field.findtext("./create_time") or "").strip(),
                "modify_time": (field.findtext("./modify_time") or "").strip(),
                "audio": format_size(defn.get("audio")),
                "sd": format_size(defn.get("sd")),
                "hd": format_size(defn.get("hd")),
                "shd": format_size(defn.get("shd")),
                "fhd": format_size(defn.get("fhd")),
                "uhd": format_size(defn.get("uhd")),
                "source": format_size(defn.get("source")),
            }
            row["empty_shell"] = is_api2_empty_shell_row(row)
            results.append(row)
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
    parser.add_argument("--cid", action="append", dest="cids", help="Cover ID, repeatable or comma-separated")
    parser.add_argument("--vid", action="append", dest="vids", help="Video ID, repeatable")
    parser.add_argument("--api1-tid", default=API_1_DEFAULT_PARAMS["tid"], help="API1 tid")
    parser.add_argument("--api1-appid", default=API_1_DEFAULT_PARAMS["appid"], help="API1 appid")
    parser.add_argument("--api1-appkey", default=API_1_DEFAULT_PARAMS["appkey"], help="API1 appkey")
    parser.add_argument("--api2-otype", choices=("xml", "json"), default=API_2_DEFAULT_PARAMS["otype"], help="API2 wrapper mode")
    parser.add_argument("--api2-tid", default=API_2_DEFAULT_PARAMS["tid"], help="API2 tid")
    parser.add_argument("--api2-appid", default=API_2_DEFAULT_PARAMS["appid"], help="API2 appid")
    parser.add_argument("--api2-appkey", default=API_2_DEFAULT_PARAMS["appkey"], help="API2 appkey")
    parser.add_argument("--api2-union-platform", default=API_2_DEFAULT_PARAMS["union_platform"], help="API2 union_platform")
    parser.add_argument("--api2-callback", default=None, help="API2 JSONP callback override; only applies when --api2-otype json")
    parser.add_argument("--api2-batch-size", type=int, default=10, help="API2 batch size for demo requests")
    parser.add_argument("--env-json", help="Path to a replay environment JSON file")
    parser.add_argument("--env-name", help="Environment name inside --env-json, such as pc_web_real_cookie_replay")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    cids = split_csv_values(args.cids)
    if not cids and args.url:
        cid_from_url = extract_cid_from_url(args.url)
        if cid_from_url:
            cids = [cid_from_url]
    if not cids and not args.vids:
        raise SystemExit("Provide --url, --cid, or at least one --vid")

    if args.api2_batch_size <= 0 or args.api2_batch_size > 32:
        raise SystemExit("--api2-batch-size must be between 1 and 32")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be > 0")

    api1_params = {
        "tid": args.api1_tid,
        "appid": args.api1_appid,
        "appkey": args.api1_appkey,
    }
    api2_params = {
        "otype": args.api2_otype,
        "tid": args.api2_tid,
        "appid": args.api2_appid,
        "appkey": args.api2_appkey,
        "union_platform": args.api2_union_platform,
    }
    if args.api2_callback is not None:
        api2_params["callback"] = args.api2_callback
    request_headers, resolved_env_name = load_request_headers(args.env_json, args.env_name)

    cover_info = None
    cover_infos: list[dict] = []
    vids = list(args.vids or [])
    if cids:
        cover_infos = fetch_cover_infos(
            cids,
            api1_params=api1_params,
            request_headers=request_headers,
            timeout=args.timeout,
        )
        cover_info = cover_infos[0] if cover_infos else None
        if not vids:
            vids = [
                vid
                for cover in cover_infos
                for vid in (cover.get("video_ids") or [])
                if str(vid or "").strip()
            ]

    details = (
        fetch_video_details(
            vids,
            batch_size=args.api2_batch_size,
            api2_params=api2_params,
            request_headers=request_headers,
            timeout=args.timeout,
        )
        if vids
        else []
    )
    payload = {
        "cid": ",".join(cids) if cids else None,
        "cids": cids,
        "api1_params": api1_params,
        "api2_params": api2_params,
        "pair_guidance": build_pair_guidance(api1_params, api2_params),
        "request_environment": {
            "env_json": args.env_json,
            "env_name": resolved_env_name,
            "timeout_seconds": args.timeout,
            "header_keys": sorted(request_headers),
        },
        "cover_info": cover_info,
        "cover_infos": cover_infos,
        "api1_batch_diagnostics": summarize_api1_batch(cids, cover_infos) if cids else None,
        "api2_batch_diagnostics": summarize_api2_batch(details) if vids else None,
        "video_details": details,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    pair_guidance = payload["pair_guidance"]
    pair_advisories = [
        advisory
        for item in pair_guidance
        for advisory in (item.get("advisories") or [])
    ]
    if pair_advisories:
        print("参数提示:")
        for advisory in pair_advisories:
            print(f"- {advisory}")
        print()

    if cover_infos:
        if len(cover_infos) == 1:
            print(f"CID: {cover_info['cid']}")
            print(f"标题: {cover_info['title']}")
            print(f"类型: {cover_info['type_name']} ({cover_info['type']})")
            print(f"VIDs: {', '.join(cover_info['video_ids']) or '-'}")
            extra_field_keys = cover_info.get("extra_field_keys") or []
            extra_nonempty_fields = cover_info.get("extra_nonempty_fields") or {}
            if extra_field_keys:
                print(f"额外字段键数: {len(extra_field_keys)}")
            if extra_nonempty_fields:
                extra_preview = ", ".join(
                    f"{key}={value}" for key, value in extra_nonempty_fields.items()
                )
                print(f"额外非空字段: {extra_preview}")
        else:
            diagnostics = summarize_api1_batch(cids, cover_infos)
            print(f"CIDs: {', '.join(cids)}")
            print(f"返回 cover 数: {diagnostics['returned_cover_count']}")
            print(f"聚合 VIDs: {diagnostics['aggregated_video_ids_count']}")
            print()
            for index, cover in enumerate(cover_infos, start=1):
                print(f"[{index}] CID: {cover['cid']}")
                print(f"    标题: {cover['title']}")
                print(f"    类型: {cover['type_name']} ({cover['type']})")
                print(f"    VIDs: {', '.join(cover['video_ids']) or '-'}")
                extra_field_keys = cover.get("extra_field_keys") or []
                extra_nonempty_fields = cover.get("extra_nonempty_fields") or {}
                if extra_field_keys:
                    print(f"    额外字段键数: {len(extra_field_keys)}")
                if extra_nonempty_fields:
                    extra_preview = ", ".join(
                        f"{key}={value}" for key, value in extra_nonempty_fields.items()
                    )
                    print(f"    额外非空字段: {extra_preview}")
        print()

    if details:
        diagnostics = summarize_api2_batch(details)
        if diagnostics["all_results_empty_shell"]:
            print("注意: 当前 API2 批量结果为 top-level success + 全部 empty-shell，调用方应按全坏/全空批量处理。")
            print()
        print_text_table(details)


if __name__ == "__main__":
    main()
