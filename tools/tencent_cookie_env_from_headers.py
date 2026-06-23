from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path


DESKTOP_HEADERS = OrderedDict(
    (
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"),
        ("Accept", "*/*"),
        ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        ("Referer", "https://v.qq.com/"),
        ("Origin", "https://v.qq.com"),
    )
)

MOBILE_HEADERS = OrderedDict(
    (
        ("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"),
        ("Accept", "*/*"),
        ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        ("Referer", "https://m.v.qq.com/"),
        ("Origin", "https://m.v.qq.com"),
    )
)

MODE_TO_KEYS = {
    "real": ("pc_web_real_cookie_replay", "mobile_h5_real_cookie_replay"),
    "aged": ("pc_web_aged_cookie_replay", "mobile_h5_aged_cookie_replay"),
    "login": ("pc_web_login_state_replay", "mobile_h5_login_state_replay"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Tencent Video replay environment JSON from raw Cookie headers."
    )
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_TO_KEYS.keys()),
        required=True,
        help="Replay environment family to build.",
    )
    parser.add_argument(
        "--desktop-cookie-header",
        help="Desktop Cookie header text.",
    )
    parser.add_argument(
        "--desktop-cookie-file",
        help="Text file containing the desktop Cookie header.",
    )
    parser.add_argument(
        "--mobile-cookie-header",
        help="Mobile Cookie header text.",
    )
    parser.add_argument(
        "--mobile-cookie-file",
        help="Text file containing the mobile Cookie header.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation.",
    )
    args = parser.parse_args()
    if not args.desktop_cookie_header and not args.desktop_cookie_file:
        parser.error("one of --desktop-cookie-header or --desktop-cookie-file is required")
    return args


def read_cookie_value(inline_value: str | None, file_path: str | None) -> str:
    if inline_value:
        return inline_value.strip()
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()
    return ""


def build_env(headers_template: OrderedDict[str, str], cookie_header: str) -> OrderedDict[str, str]:
    env = OrderedDict(headers_template)
    env["Cookie"] = cookie_header
    return env


def main() -> int:
    args = parse_args()
    desktop_cookie = read_cookie_value(args.desktop_cookie_header, args.desktop_cookie_file)
    mobile_cookie = read_cookie_value(args.mobile_cookie_header, args.mobile_cookie_file)
    desktop_key, mobile_key = MODE_TO_KEYS[args.mode]

    payload: OrderedDict[str, OrderedDict[str, str]] = OrderedDict()
    payload[desktop_key] = build_env(DESKTOP_HEADERS, desktop_cookie)
    if mobile_cookie:
        payload[mobile_key] = build_env(MOBILE_HEADERS, mobile_cookie)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=args.indent) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
