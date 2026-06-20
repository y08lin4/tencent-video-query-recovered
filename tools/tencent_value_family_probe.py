from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import datetime as dt
import json
from pathlib import Path
import sys

import tencent_cover_graph_probe as graph
import tencent_video_field_survey as survey


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a rare-value family by combining cover-graph traversal "
            "with per-cover field surveys."
        )
    )
    parser.add_argument(
        "seeds",
        nargs="+",
        help="Seed cover URLs or raw CIDs",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="How many related-cover hops to follow",
    )
    parser.add_argument(
        "--max-covers",
        type=int,
        default=60,
        help="Maximum number of covers to fetch in the graph pass",
    )
    parser.add_argument(
        "--related-video-sample",
        type=int,
        default=3,
        help="How many main video_ids to use per cover when collecting related covers",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="API2 batch size when reading video details",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
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
        "--clip-sample-head",
        type=int,
        default=0,
        help="How many clip IDs to sample from the start of clips_ids",
    )
    parser.add_argument(
        "--clip-sample-tail",
        type=int,
        default=0,
        help="How many clip IDs to sample from the end of clips_ids",
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
    if args.depth < 0:
        parser.error("--depth must be greater than or equal to 0")
    if args.max_covers <= 0:
        parser.error("--max-covers must be greater than 0")
    if args.related_video_sample <= 0:
        parser.error("--related-video-sample must be greater than 0")
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


def seed_to_cover_url(seed: str) -> str:
    cid = graph.normalize_seed(seed)
    return f"https://v.qq.com/x/cover/{cid}.html"


def compact_sample(sample: OrderedDict[str, object]) -> OrderedDict[str, object]:
    cover = sample.get("cover", {})
    if not isinstance(cover, dict):
        cover = {}
    cover_fields = cover.get("fields", {})
    if not isinstance(cover_fields, dict):
        cover_fields = {}
    derived = sample.get("derived", {})
    if not isinstance(derived, dict):
        derived = {}
    derived_cover = derived.get("cover", {})
    if not isinstance(derived_cover, dict):
        derived_cover = {}
    derived_videos = derived.get("videos", {})
    if not isinstance(derived_videos, dict):
        derived_videos = {}
    return OrderedDict(
        (
            ("cid", sample.get("cid", "")),
            ("status", sample.get("status", "")),
            ("title", survey.scalar_value(cover_fields.get("title", ""))),
            ("type", survey.scalar_value(cover_fields.get("type", ""))),
            ("type_name", survey.scalar_value(cover_fields.get("type_name", ""))),
            ("pay_status", survey.scalar_value(cover_fields.get("pay_status", ""))),
            (
                "positive_trailer",
                survey.scalar_value(cover_fields.get("positive_trailer", "")),
            ),
            (
                "positive_content_id",
                survey.scalar_value(cover_fields.get("positive_content_id", "")),
            ),
            ("video_ids_count", derived_cover.get("video_ids_count", 0)),
            ("clips_ids_count", derived_cover.get("clips_ids_count", 0)),
            ("downright_count", derived_cover.get("downright_count", 0)),
            ("nomal_f_counts", derived_cover.get("nomal_f_counts", {})),
            ("vip_f_counts", derived_cover.get("vip_f_counts", {})),
            ("state_counts", derived_videos.get("state_counts", {})),
            ("upload_src_counts", derived_videos.get("upload_src_counts", {})),
            (
                "publish_date_nonempty_count",
                derived_videos.get("publish_date_nonempty_count", 0),
            ),
            (
                "targetid_nonempty_count",
                derived_videos.get("targetid_nonempty_count", 0),
            ),
        )
    )


def build_field_union(
    compact_samples: list[OrderedDict[str, object]]
) -> OrderedDict[str, object]:
    nomal_f_union: Counter[str] = Counter()
    vip_f_union: Counter[str] = Counter()
    state_union: Counter[str] = Counter()
    upload_src_union: Counter[str] = Counter()
    publish_date_nonempty_count = 0
    targetid_nonempty_count = 0
    for sample in compact_samples:
        nomal_f_counts = sample.get("nomal_f_counts", {})
        vip_f_counts = sample.get("vip_f_counts", {})
        state_counts = sample.get("state_counts", {})
        upload_src_counts = sample.get("upload_src_counts", {})
        if isinstance(nomal_f_counts, dict):
            nomal_f_union.update({str(key): int(value) for key, value in nomal_f_counts.items()})
        if isinstance(vip_f_counts, dict):
            vip_f_union.update({str(key): int(value) for key, value in vip_f_counts.items()})
        if isinstance(state_counts, dict):
            state_union.update({str(key): int(value) for key, value in state_counts.items()})
        if isinstance(upload_src_counts, dict):
            upload_src_union.update(
                {str(key): int(value) for key, value in upload_src_counts.items()}
            )
        publish_date_nonempty_count += int(sample.get("publish_date_nonempty_count", 0))
        targetid_nonempty_count += int(sample.get("targetid_nonempty_count", 0))
    return OrderedDict(
        (
            ("nomal_f_union", OrderedDict(sorted(nomal_f_union.items()))),
            ("vip_f_union", OrderedDict(sorted(vip_f_union.items()))),
            ("state_union", OrderedDict(sorted(state_union.items()))),
            ("upload_src_union", OrderedDict(sorted(upload_src_union.items()))),
            ("publish_date_nonempty_count", publish_date_nonempty_count),
            ("targetid_nonempty_count", targetid_nonempty_count),
        )
    )


def main() -> int:
    args = parse_args()
    normalized_seeds = [graph.normalize_seed(seed) for seed in args.seeds]

    graph_args = argparse.Namespace(
        seeds=list(normalized_seeds),
        depth=args.depth,
        max_covers=args.max_covers,
        related_video_sample=args.related_video_sample,
        batch_size=args.batch_size,
        timeout=args.timeout,
        http_retries=args.http_retries,
        retry_sleep=args.retry_sleep,
        indent=args.indent,
    )
    graph_report = graph.run_probe(graph_args)

    survey_report = survey.build_report(
        [seed_to_cover_url(seed) for seed in normalized_seeds],
        timeout=args.timeout,
        batch_size=args.batch_size,
        http_retries=args.http_retries,
        retry_sleep=args.retry_sleep,
        clip_sample_head=args.clip_sample_head,
        clip_sample_tail=args.clip_sample_tail,
    )
    compact_samples = [
        compact_sample(sample)
        for sample in survey_report.get("samples", [])
        if isinstance(sample, OrderedDict)
    ]

    report = OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("tool", "tencent_value_family_probe"),
                        (
                            "generated_at",
                            dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                        ),
                        ("seed_count", len(normalized_seeds)),
                        ("depth", args.depth),
                        ("max_covers", args.max_covers),
                        ("related_video_sample", args.related_video_sample),
                        ("batch_size", args.batch_size),
                        ("timeout_seconds", args.timeout),
                        ("http_retries", args.http_retries),
                        ("retry_sleep_seconds", args.retry_sleep),
                        ("clip_sample_head", args.clip_sample_head),
                        ("clip_sample_tail", args.clip_sample_tail),
                    )
                ),
            ),
            ("seeds", normalized_seeds),
            ("graph_summary", graph_report.get("summary", OrderedDict())),
            ("graph_covers", graph_report.get("covers", [])),
            ("graph_errors", graph_report.get("errors", [])),
            ("survey_compact", compact_samples),
            ("survey_field_union", build_field_union(compact_samples)),
        )
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=args.indent)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
