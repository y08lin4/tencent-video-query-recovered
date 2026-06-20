from __future__ import annotations

import argparse
from collections import OrderedDict
import datetime as dt
import json
import sys
from typing import Any

import tencent_environment_matrix_probe as env_probe
import tencent_video_field_survey as survey


DEFAULT_BUCKETS: OrderedDict[str, str] = OrderedDict(
    (
        ("film_single_second", "https://v.qq.com/x/cover/mzc002009qyd7nv/m4102tgsa8d.html"),
        ("anime_season_second", "https://v.qq.com/x/cover/mzc00200fobieel/u41010ju5vc.html"),
        ("tv_season_second", "https://v.qq.com/x/cover/mzc00200dfbfsrw.html"),
        ("variety_season_second", "https://v.qq.com/x/cover/mzc00200c2gydkd.html"),
        ("kids_regular_season", "https://v.qq.com/x/cover/mzc00200lyd87zd.html"),
        ("kids_free_pack_second", "https://v.qq.com/x/cover/mzc002002cxp3uh.html"),
        ("topic_page_second", "https://v.qq.com/x/cover/mzc00200apbfiqs.html"),
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Tencent Video same-day environment field-drift matrix on second "
            "representative pages for the main page-shape buckets."
        )
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="API2 batch size for representative field surveys",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=1,
        help="Retries for representative field surveys",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.5,
        help="Base sleep between survey retries",
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
    parser.add_argument(
        "--bucket",
        action="append",
        default=[],
        help="Optional extra bucket in the form name=https://v.qq.com/...",
    )
    parser.add_argument(
        "--no-default-buckets",
        action="store_true",
        help="Only run explicitly provided --bucket items",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.batch_size <= 0 or args.batch_size > 32:
        parser.error("--batch-size must be between 1 and 32")
    if args.http_retries < 0:
        parser.error("--http-retries must be greater than or equal to 0")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep must be greater than or equal to 0")
    return args


def build_bucket_map(extra_items: list[str], include_defaults: bool = True) -> OrderedDict[str, str]:
    buckets = OrderedDict(DEFAULT_BUCKETS) if include_defaults else OrderedDict()
    for raw in extra_items:
        if "=" not in raw:
            raise ValueError(f"Invalid --bucket value: {raw!r}")
        name, url = raw.split("=", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            raise ValueError(f"Invalid --bucket value: {raw!r}")
        buckets[name] = url
    return buckets


def bucket_has_probe_error(payload: dict[str, Any]) -> bool:
    environments = payload.get("environments", {})
    if not isinstance(environments, dict):
        return False
    for env_payload in environments.values():
        row = env_payload if isinstance(env_payload, dict) else {}
        sample_status = str(row.get("sample_status", "")).strip()
        if sample_status and sample_status != "ok":
            return True
    return False


def run_bucket_matrix(
    bucket_urls: OrderedDict[str, str],
    args: argparse.Namespace,
) -> OrderedDict[str, Any]:
    original_headers = survey.REQUEST_HEADERS.copy()
    try:
        report: OrderedDict[str, Any] = OrderedDict()
        for bucket, url in bucket_urls.items():
            per_env: OrderedDict[str, Any] = OrderedDict()
            signatures: list[str] = []
            for env_name, headers in env_probe.ENVIRONMENTS.items():
                survey.REQUEST_HEADERS.clear()
                survey.REQUEST_HEADERS.update(headers)
                sample = survey.survey_sample(
                    url,
                    timeout=args.timeout,
                    batch_size=args.batch_size,
                    http_retries=args.http_retries,
                    retry_sleep=args.retry_sleep,
                    clip_sample_head=0,
                    clip_sample_tail=0,
                )
                summary = env_probe.extract_field_drift_summary(sample)
                signatures.append(json.dumps(summary, ensure_ascii=False, sort_keys=False))
                per_env[env_name] = summary
            report[bucket] = OrderedDict(
                (
                    ("url", url),
                    ("unique_signature_count", len(set(signatures))),
                    ("environments", per_env),
                )
            )
        return report
    finally:
        survey.REQUEST_HEADERS.clear()
        survey.REQUEST_HEADERS.update(original_headers)


def summarize_takeaways(report: OrderedDict[str, Any]) -> list[str]:
    takeaways: list[str] = []
    stable_buckets: list[str] = []
    unstable_buckets: list[str] = []
    probe_error_buckets: list[str] = []
    for bucket, payload in report.items():
        row = payload if isinstance(payload, dict) else {}
        unique_count = int(row.get("unique_signature_count", 0) or 0)
        has_probe_error = bucket_has_probe_error(row)
        if unique_count == 1 and not has_probe_error:
            stable_buckets.append(bucket)
        elif has_probe_error:
            probe_error_buckets.append(bucket)
        else:
            unstable_buckets.append(bucket)
    if stable_buckets:
        takeaways.append(
            "Same-day second-representative rechecks stayed environment-stable for: "
            + ", ".join(stable_buckets)
            + "."
        )
    if unstable_buckets:
        takeaways.append(
            "Same-day field-shape drift still needs attention for: "
            + ", ".join(unstable_buckets)
            + "."
        )
    if probe_error_buckets:
        takeaways.append(
            "Some environments hit survey/probe errors rather than clean field drift for: "
            + ", ".join(probe_error_buckets)
            + "."
        )
    if "sports_replay_second" in report and int(as_dict(report["sports_replay_second"]).get("unique_signature_count", 0) or 0) == 1 and not bucket_has_probe_error(as_dict(report["sports_replay_second"])):
        takeaways.append(
            "This extension now includes a high-confidence sports replay second representative under the base four request environments."
        )
    elif "sports_replay_second" in report:
        takeaways.append(
            "This extension closes part of the 'second representative page' gap for film/anime/tv/variety/kids/topic buckets, but sports replay still needs a curated second representative page."
        )
    return takeaways


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_open_items(report: OrderedDict[str, Any]) -> list[str]:
    open_items = [
        "cross-day retest is still pending",
        "browser-like sec-ch-ua / sec-fetch-* / synthetic-cookie requests have been covered separately, but real-session cookie / login-state / aged-cookie environments are still outside the current matrix",
    ]
    error_buckets = [
        bucket
        for bucket, payload in report.items()
        if bucket_has_probe_error(as_dict(payload))
    ]
    if error_buckets:
        open_items.append(
            "inspect probe-level failures before classifying them as field drift: "
            + ", ".join(error_buckets)
        )
    if "sports_replay_second" in report:
        replay_row = as_dict(report.get("sports_replay_second"))
        if int(replay_row.get("unique_signature_count", 0) or 0) != 1 or bucket_has_probe_error(replay_row):
            open_items.append("sports_replay still needs a curated second representative page")
    if "variety_viewangle_second" in report:
        variety_row = as_dict(report.get("variety_viewangle_second"))
        if int(variety_row.get("unique_signature_count", 0) or 0) != 1 or bucket_has_probe_error(variety_row):
            open_items.append("variety_viewangle second representative still needs a stable same-day multi-environment closure")
    return open_items


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - older Python compatibility
        pass

    args = parse_args()
    bucket_urls = build_bucket_map(args.bucket, include_defaults=not args.no_default_buckets)
    if not bucket_urls:
        raise SystemExit("No buckets configured. Provide --bucket or omit --no-default-buckets.")
    report = run_bucket_matrix(bucket_urls, args)
    output = OrderedDict(
        (
            ("generated_at", dt.date.today().isoformat()),
            (
                "scope",
                "same-day second-representative environment matrix for main page-shape buckets",
            ),
            ("environments_tested", list(env_probe.ENVIRONMENTS.keys())),
            ("bucket_urls", bucket_urls),
            ("buckets", report),
            ("current_takeaways", summarize_takeaways(report)),
            ("still_open", build_open_items(report)),
        )
    )
    rendered = json.dumps(output, ensure_ascii=False, indent=args.indent)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
