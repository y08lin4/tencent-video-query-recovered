from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, deque
import datetime as dt
import json
import sys

import tencent_video_field_survey as survey


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Traverse related Tencent Video covers and summarize cover-level fields."
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
        help="Maximum number of covers to fetch",
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
        default=20,
        help="API2 batch size when reading related videos",
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
        help="How many retries to attempt after the initial HTTP request fails",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.75,
        help="Base sleep in seconds between HTTP retries",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation",
    )
    args = parser.parse_args()
    if args.depth < 0:
        parser.error("--depth must be greater than or equal to 0")
    if args.max_covers <= 0:
        parser.error("--max-covers must be greater than 0")
    if args.related_video_sample <= 0:
        parser.error("--related-video-sample must be greater than 0")
    if args.batch_size <= 0 or args.batch_size > 32:
        parser.error("--batch-size must be between 1 and 32")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.http_retries < 0:
        parser.error("--http-retries must be greater than or equal to 0")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep must be greater than or equal to 0")
    return args


def normalize_seed(value: str) -> str:
    cid = survey.extract_cid_from_url(value)
    if cid:
        return cid
    text = value.strip()
    if not text:
        raise ValueError("empty seed")
    return text


def fetch_cover(
    cid: str,
    timeout: float,
    http_retries: int,
    retry_sleep: float,
) -> dict[str, object]:
    return survey.parse_cover_document(
        survey.http_get(
            survey.build_api_1_url(cid),
            timeout,
            retries=http_retries,
            retry_sleep=retry_sleep,
        )
    )


def fetch_videos(
    vids: list[str],
    batch_size: int,
    timeout: float,
    http_retries: int,
    retry_sleep: float,
) -> list[dict[str, object]]:
    videos: list[dict[str, object]] = []
    for batch in survey.chunked(vids, batch_size):
        videos.extend(
            survey.parse_video_document(
                survey.http_get(
                    survey.build_api_2_url(batch),
                    timeout,
                    retries=http_retries,
                    retry_sleep=retry_sleep,
                )
            )
        )
    return videos


def collect_related_cids(videos: list[dict[str, object]]) -> list[str]:
    related: list[str] = []
    for video in videos:
        fields = video.get("fields", {})
        if not isinstance(fields, dict):
            continue
        related.extend(survey.list_value(fields.get("cover_list")))
        compact = survey.scalar_value(fields.get("c_covers", "")).strip()
        if compact:
            related.extend(part.strip() for part in compact.split("+") if part.strip())
    return survey.unique_strings(related)


def build_cover_row(
    cid: str,
    depth: int,
    source_cid: str | None,
    cover: dict[str, object],
) -> OrderedDict[str, object]:
    fields = cover["fields"]
    assert isinstance(fields, dict)
    downright_values = survey.list_value(fields.get("downright"))
    return OrderedDict(
        (
            ("cid", cid),
            ("depth", depth),
            ("source_cid", source_cid or ""),
            ("title", survey.scalar_value(fields.get("title", ""))),
            ("type", survey.scalar_value(fields.get("type", ""))),
            ("type_name", survey.scalar_value(fields.get("type_name", ""))),
            ("pay_status", survey.scalar_value(fields.get("pay_status", ""))),
            ("positive_trailer", survey.scalar_value(fields.get("positive_trailer", ""))),
            ("positive_content_id", survey.scalar_value(fields.get("positive_content_id", ""))),
            ("video_ids_count", len(cover["video_ids"])),
            ("clips_ids_count", len(survey.list_value(fields.get("clips_ids")))),
            ("downright_count", len(downright_values)),
            ("downright_unique", downright_values),
        )
    )


def build_summary(covers: list[OrderedDict[str, object]]) -> OrderedDict[str, object]:
    pay_counts: Counter[str] = Counter()
    pos_counts: Counter[str] = Counter()
    pcid_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    downright_count_counts: Counter[str] = Counter()
    zero_downright: list[OrderedDict[str, object]] = []
    noncanonical: list[OrderedDict[str, object]] = []

    for cover in covers:
        pay_counts.update([str(cover["pay_status"])])
        pos_counts.update([str(cover["positive_trailer"])])
        pcid_counts.update([str(cover["positive_content_id"])])
        type_counts.update([f'{cover["type"]}/{cover["type_name"]}'])
        downright_count_counts.update([str(cover["downright_count"])])
        if int(cover["downright_count"]) == 0:
            zero_downright.append(cover)
        if str(cover["positive_trailer"]) == "0":
            noncanonical.append(cover)

    return OrderedDict(
        (
            ("cover_count", len(covers)),
            ("pay_status_counts", OrderedDict(sorted(pay_counts.items()))),
            ("positive_trailer_counts", OrderedDict(sorted(pos_counts.items()))),
            ("positive_content_id_counts", OrderedDict(sorted(pcid_counts.items()))),
            ("type_counts", OrderedDict(sorted(type_counts.items()))),
            ("downright_count_counts", OrderedDict(sorted(downright_count_counts.items()))),
            ("zero_downright_count", len(zero_downright)),
            ("zero_downright_covers", zero_downright),
            ("positive_trailer_zero_count", len(noncanonical)),
            ("positive_trailer_zero_covers", noncanonical),
        )
    )


def run_probe(args: argparse.Namespace) -> OrderedDict[str, object]:
    normalized_seeds = [normalize_seed(seed) for seed in args.seeds]
    queue: deque[tuple[str, int, str | None]] = deque(
        (cid, 0, None) for cid in survey.unique_strings(normalized_seeds)
    )
    seen: set[str] = set()
    covers: list[OrderedDict[str, object]] = []
    errors: list[OrderedDict[str, object]] = []

    while queue and len(covers) < args.max_covers:
        cid, depth, source_cid = queue.popleft()
        if cid in seen:
            continue
        seen.add(cid)

        try:
            cover = fetch_cover(
                cid,
                timeout=args.timeout,
                http_retries=args.http_retries,
                retry_sleep=args.retry_sleep,
            )
        except Exception as exc:  # pragma: no cover - runtime reporting path
            errors.append(
                OrderedDict(
                    (
                        ("cid", cid),
                        ("depth", depth),
                        ("source_cid", source_cid or ""),
                        ("stage", "api1"),
                        ("error", str(exc)),
                    )
                )
            )
            continue

        covers.append(build_cover_row(cid, depth, source_cid, cover))

        if depth >= args.depth:
            continue

        sample_vids = cover["video_ids"][: args.related_video_sample]
        if not sample_vids:
            continue

        try:
            videos = fetch_videos(
                sample_vids,
                batch_size=args.batch_size,
                timeout=args.timeout,
                http_retries=args.http_retries,
                retry_sleep=args.retry_sleep,
            )
        except Exception as exc:  # pragma: no cover - runtime reporting path
            errors.append(
                OrderedDict(
                    (
                        ("cid", cid),
                        ("depth", depth),
                        ("source_cid", source_cid or ""),
                        ("stage", "api2"),
                        ("error", str(exc)),
                    )
                )
            )
            continue

        for related_cid in collect_related_cids(videos):
            if related_cid and related_cid not in seen:
                queue.append((related_cid, depth + 1, cid))

    report = OrderedDict(
        (
            (
                "meta",
                OrderedDict(
                    (
                        ("tool", "tencent_cover_graph_probe"),
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
                    )
                ),
            ),
            ("seeds", normalized_seeds),
            ("covers", covers),
            ("summary", build_summary(covers)),
            ("errors", errors),
        )
    )
    return report


def main() -> int:
    args = parse_args()
    report = run_probe(args)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=args.indent))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
