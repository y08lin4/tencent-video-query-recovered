from __future__ import annotations

import argparse
from collections import OrderedDict
import datetime as dt
import json
from pathlib import Path
import sys


STATUS_SCALE = [
    "stable_value",
    "small_family",
    "anomaly_value",
    "shape_confirmed_semantics_unknown",
]

FIELD_ALIASES = OrderedDict(
    (
        ("type_name", "paired_1_to_1_with_type_in_current_samples"),
    )
)

FIELD_ORDER = (
    "pay_status",
    "type",
    "type_name",
    "positive_trailer",
    "positive_content_id",
    "state",
    "upload_src",
    "F",
    "downright",
)

CORE_CARD_KEYS = (
    "status",
    "sample_count",
    "representative_samples",
    "types",
    "page_shapes",
    "strong_correlations",
    "counterexamples",
    "current_blackbox_explanation",
    "unconfirmed_items",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Synthesize Tencent Video enum indexes and enum cards from the "
            "current analysis JSON files."
        )
    )
    parser.add_argument(
        "--analysis-dir",
        default="analysis",
        help="Directory containing current analysis JSON files",
    )
    parser.add_argument(
        "--artifact",
        choices=("both", "index", "cards"),
        default="both",
        help="Which artifact to emit to stdout",
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
    return parser.parse_args()


def load_json(path: Path) -> OrderedDict[str, object]:
    text: str | None = None
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = path.read_text(encoding="utf-8", errors="replace")
    return json.loads(text, object_pairs_hook=OrderedDict)


def load_optional_json(path: Path) -> OrderedDict[str, object]:
    if not path.exists():
        return OrderedDict()
    return load_json(path)


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def add_unique(target: list[str], value: object) -> None:
    text = clean_text(value)
    if text and text not in target:
        target.append(text)


def union_str_lists(left: object, right: object) -> list[str]:
    merged: list[str] = []
    for source in (left, right):
        if isinstance(source, list):
            for value in source:
                add_unique(merged, value)
    return merged


def list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]
    text = clean_text(value)
    return [text] if text else []


def to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sort_value_key(value: str) -> tuple[int, int, str]:
    text = clean_text(value)
    if text.isdigit():
        return (0, to_int(text), text)
    if "/" in text:
        left, _ = text.split("/", 1)
        if left.isdigit():
            return (0, to_int(left), text)
    return (1, 0, text)


def iter_index_values(value: object) -> list[str]:
    if isinstance(value, dict):
        return sorted(
            [clean_text(item) for item in as_list(value.get("values")) if clean_text(item)],
            key=sort_value_key,
        )
    if isinstance(value, list):
        return sorted([clean_text(item) for item in value if clean_text(item)], key=sort_value_key)
    return []


def default_status(field_name: str, value: str, sample_count: int) -> str:
    if field_name == "pay_status":
        if not value:
            return "anomaly_value"
        if sample_count >= 5:
            return "stable_value"
        if sample_count >= 2:
            return "small_family"
        return "anomaly_value"
    if field_name == "type":
        if sample_count >= 2:
            return "stable_value"
        if sample_count == 1:
            return "small_family"
        return "shape_confirmed_semantics_unknown"
    if field_name == "type_name":
        if sample_count >= 2:
            return "stable_value"
        if sample_count == 1:
            return "small_family"
        return "shape_confirmed_semantics_unknown"
    if field_name == "positive_trailer":
        return "small_family" if value == "2" else "stable_value"
    if field_name == "positive_content_id":
        return "shape_confirmed_semantics_unknown"
    if field_name == "state":
        return "stable_value" if value == "4" else "small_family"
    if field_name == "upload_src":
        return "small_family" if sample_count >= 2 else "shape_confirmed_semantics_unknown"
    if field_name == "F":
        return "stable_value" if value in {"2", "7"} else "small_family"
    return "shape_confirmed_semantics_unknown"


def reconcile_status(field_name: str, value: str, sample_count: int, status: str) -> str:
    normalized = clean_text(status)
    default = default_status(field_name, value, sample_count)
    if not normalized:
        return default
    if field_name in {"pay_status", "upload_src"}:
        return default
    if field_name in {"type", "type_name"}:
        if sample_count <= 0:
            return "shape_confirmed_semantics_unknown"
        if sample_count == 1 and normalized == "stable_value":
            return "small_family"
    return normalized


def default_explanation(field_name: str, value: str) -> str:
    if field_name == "pay_status":
        return "derived from current pay_status probes"
    if field_name == "type":
        return "derived from current type distribution"
    if field_name == "type_name":
        return "current samples keep a 1-to-1 mapping between `type` and `type_name`"
    if field_name == "positive_trailer":
        return "derived from current cover-family evidence"
    if field_name == "positive_content_id":
        return "derived from current cover-family evidence"
    if field_name == "state":
        return "derived from current state field matrix"
    if field_name == "upload_src":
        return "derived from current upload_src field matrix"
    if field_name == "F":
        return "derived from current F field matrix"
    if field_name == "downright":
        return "derived from current downright code index"
    return f"derived from current {field_name} evidence"


def normalize_explanation(
    field_name: str,
    value: str,
    status: str,
    sample_count: int,
    explanation: str,
) -> str:
    text = clean_text(explanation)
    if field_name == "type":
        if status == "stable_value":
            return f"当前可稳定当作 `{value}` 对应的黑盒类目桶使用。"
        if status == "small_family":
            return f"当前已观测到 `{value}` 这支类目，但仍属于 small_family 占位，暂不升级成广义稳定类目桶。"
        if status == "shape_confirmed_semantics_unknown":
            return f"当前只确认 `{value}` 这支类目形态存在，语义仍待命名。"
        if status == "anomaly_value":
            return f"当前只见到 `{value}` 的异常单点，暂不提升为稳定类目桶。"
    if field_name == "type_name":
        if sample_count <= 0 or status == "shape_confirmed_semantics_unknown":
            return "当前仅沿用 type 层镜像占位，尚无独立 type_name 样本，不写成展示名层稳定值。"
        if status == "stable_value":
            return "当前样本里 `type_name` 与 `type` 保持 1:1 配对，可暂作展示名层稳定映射。"
        if status == "small_family":
            return "当前样本里 `type_name` 与 `type` 仍保持 1:1 配对，但当前只够 small_family 占位，暂不升级成展示名层稳定值。"
        if status == "anomaly_value":
            return "当前只见到零散 type_name 线索，仍不足以写成展示名层稳定值。"
    return text or default_explanation(field_name, value)


def card_template(field_name: str, value: str, sample_count: int = 0) -> OrderedDict[str, object]:
    return OrderedDict(
        (
            ("status", default_status(field_name, value, sample_count)),
            ("sample_count", sample_count),
            ("representative_samples", []),
            ("types", []),
            ("page_shapes", []),
            ("strong_correlations", []),
            ("counterexamples", []),
            ("current_blackbox_explanation", default_explanation(field_name, value)),
            ("unconfirmed_items", ["official backend naming"]),
        )
    )


def make_observation_map() -> OrderedDict[str, OrderedDict[str, OrderedDict[str, object]]]:
    return OrderedDict((field_name, OrderedDict()) for field_name in FIELD_ORDER)


def observe(
    observations: OrderedDict[str, OrderedDict[str, OrderedDict[str, object]]],
    field_name: str,
    value: object,
    *,
    sample_count: int = 0,
    representative_sample: object = "",
    type_value: object = "",
) -> None:
    text = clean_text(value)
    if not text:
        return
    field_obs = observations[field_name]
    slot = field_obs.setdefault(
        text,
        OrderedDict(
            (
                ("sample_count", 0),
                ("representative_samples", []),
                ("types", []),
            )
        ),
    )
    slot["sample_count"] = max(to_int(slot.get("sample_count")), sample_count)
    reps = slot["representative_samples"]
    types = slot["types"]
    assert isinstance(reps, list)
    assert isinstance(types, list)
    add_unique(reps, representative_sample)
    add_unique(types, type_value)


def merge_seed_card(base_card: dict[str, object], seed_card: dict[str, object]) -> OrderedDict[str, object]:
    merged = OrderedDict(base_card)
    for key, seed_value in seed_card.items():
        if key in {"representative_samples", "types", "page_shapes", "strong_correlations", "counterexamples", "unconfirmed_items"}:
            merged[key] = union_str_lists(merged.get(key), seed_value)
            continue
        if key == "sample_count":
            merged[key] = max(to_int(merged.get(key)), to_int(seed_value))
            continue
        if key == "sample_count_hint":
            if "sample_count_hint" not in merged and seed_value:
                merged[key] = seed_value
            continue
        if seed_value not in (None, "", [], {}):
            merged[key] = seed_value
    return merged


def build_type_pair_lookup(seed_index_fields: dict[str, object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for value in iter_index_values(seed_index_fields.get("type")):
        if "/" not in value:
            continue
        type_id, _ = value.split("/", 1)
        lookup[type_id] = value
    return lookup


def resolve_type_value(raw_type: object, raw_type_name: object, type_pair_lookup: dict[str, str]) -> str:
    type_text = clean_text(raw_type)
    if not type_text:
        return ""
    if "/" in type_text:
        return type_text
    mapped = clean_text(type_pair_lookup.get(type_text))
    if mapped:
        return mapped
    type_name_text = clean_text(raw_type_name)
    if type_name_text and "�" not in type_name_text:
        return f"{type_text}/{type_name_text}"
    return type_text


def iter_followup_samples(
    report: dict[str, object],
) -> list[tuple[dict[str, object], dict[str, object], dict[str, object], str]]:
    rows: list[tuple[dict[str, object], dict[str, object], dict[str, object], str]] = []
    for sample in as_list(report.get("samples")):
        row = as_dict(sample)
        cover = as_dict(row.get("cover"))
        fields = as_dict(cover.get("fields"))
        derived = as_dict(as_dict(row.get("derived")).get("videos"))
        cid = clean_text(row.get("cid"))
        rows.append((row, fields, derived, cid))
    return rows


def load_followup_reports(analysis_dir: Path) -> list[OrderedDict[str, object]]:
    reports: list[OrderedDict[str, object]] = []
    seen: set[Path] = set()
    fixed_names = [
        "pay_status_manual_followup_20260619.json",
        "upload_src_2048_followup_20260619.json",
        "kids_regular_candidate_mzc00200qrzj493_20260619.json",
        "kids_regular_candidate_zkbp0mrqhy0x1hl_20260619.json",
        "kids_pay6_branch_followup_20260619.json",
        "kids_cross_ip_field_followup_20260619.json",
    ]
    for name in fixed_names:
        path = analysis_dir / name
        if path.exists():
            reports.append(load_json(path))
            seen.add(path.resolve())
    for path in sorted(analysis_dir.glob("enum_followup_*.json")):
        resolved = path.resolve()
        if resolved in seen:
            continue
        reports.append(load_json(path))
        seen.add(resolved)
    return reports


def parse_cover_video_slot_counts(value: object) -> OrderedDict[str, int]:
    text = clean_text(value)
    if not text:
        return OrderedDict()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return OrderedDict()
    if not isinstance(data, list):
        return OrderedDict()
    counts: OrderedDict[str, int] = OrderedDict()
    for item in data:
        row = as_dict(item)
        f_value = clean_text(row.get("F"))
        if not f_value:
            continue
        counts[f_value] = counts.get(f_value, 0) + 1
    return counts


def iter_followup_cover_rows(
    reports: list[dict[str, object]],
    type_pair_lookup: dict[str, str],
) -> list[tuple[str, str, dict[str, object], dict[str, object]]]:
    rows: list[tuple[str, str, dict[str, object], dict[str, object]]] = []
    for report in reports:
        for _, fields, derived, cid in iter_followup_samples(report):
            type_value = resolve_type_value(fields.get("type"), fields.get("type_name"), type_pair_lookup)
            rows.append((cid, type_value, fields, derived))
    return rows


def collect_index(
    search_probe: dict[str, object],
    state_upload: dict[str, object],
    f_matrix: dict[str, object],
    cover_families: dict[str, object],
    state8_followup: dict[str, object],
    followup_reports: list[dict[str, object]],
    seed_index_fields: dict[str, object],
    seed_cards: dict[str, object],
) -> OrderedDict[str, object]:
    values = OrderedDict((field_name, []) for field_name in FIELD_ORDER)
    type_name_values: list[str] = values["type_name"]  # type: ignore[assignment]
    type_pair_lookup = build_type_pair_lookup(seed_index_fields)

    def add_type_pair(type_value: object) -> None:
        text = clean_text(type_value)
        if not text:
            return
        add_unique(values["type"], text)
        if "/" in text:
            _, type_name = text.split("/", 1)
            add_unique(type_name_values, type_name)

    broad_probe = as_dict(search_probe.get("broad_probe"))
    for value in as_dict(broad_probe.get("pay_status_counts")).keys():
        add_unique(values["pay_status"], value)
    for value in as_dict(broad_probe.get("type_counts")).keys():
        add_type_pair(value)
    for sample in as_list(broad_probe.get("representative_samples")):
        row = as_dict(sample)
        add_type_pair(row.get("type"))
        add_unique(values["pay_status"], row.get("pay_status"))
        add_unique(values["positive_trailer"], row.get("positive_trailer"))
        add_unique(values["positive_content_id"], row.get("positive_content_id"))

    targeted_followups = as_dict(search_probe.get("targeted_followups"))
    for family_name in ("pay_status_5_family", "pay_status_9_family", "pay_status_15_family"):
        family = as_dict(targeted_followups.get(family_name))
        for sample in as_list(family.get("samples")):
            row = as_dict(sample)
            add_type_pair(row.get("type"))
            add_unique(values["pay_status"], row.get("pay_status"))
            add_unique(values["positive_trailer"], row.get("positive_trailer"))
            add_unique(values["positive_content_id"], row.get("positive_content_id"))

    state_buckets = (
        as_list(state_upload.get("pages"))
        + as_list(state_upload.get("new_type_subset"))
        + as_list(state_upload.get("pay_status_5_and_9_field_shapes"))
        + as_list(as_dict(state_upload.get("sports_subset")).get("covers"))
    )
    for sample in state_buckets:
        row = as_dict(sample)
        add_type_pair(row.get("type"))
        add_unique(values["pay_status"], row.get("pay_status"))
        for state_value in as_dict(row.get("state_counts")).keys():
            add_unique(values["state"], state_value)
        upload_counts = as_dict(row.get("upload_counts")) or as_dict(row.get("upload_src_counts"))
        for upload_value in upload_counts.keys():
            add_unique(values["upload_src"], upload_value)

    f_buckets = (
        as_list(f_matrix.get("covers"))
        + as_list(f_matrix.get("new_type_subset"))
        + as_list(f_matrix.get("pay_status_5_and_9_samples"))
        + as_list(as_dict(f_matrix.get("sports_subset")).get("covers"))
    )
    for sample in f_buckets:
        row = as_dict(sample)
        add_type_pair(row.get("type"))
        add_unique(values["pay_status"], row.get("pay_status"))
        for field_name in ("nomal_f_counts", "vip_f_counts"):
            for f_value in as_dict(row.get(field_name)).keys():
                add_unique(values["F"], f_value)

    pay16 = as_dict(cover_families.get("pay_status_16_chain"))
    main_cover = as_dict(pay16.get("main_cover"))
    add_type_pair(main_cover.get("type"))
    add_unique(values["pay_status"], main_cover.get("pay_status"))
    add_unique(values["positive_trailer"], main_cover.get("positive_trailer"))
    add_unique(values["positive_content_id"], main_cover.get("positive_content_id"))

    state8_rows = [as_dict(state8_followup.get("seed_cover"))]
    state8_rows.extend(as_dict(row) for row in as_list(state8_followup.get("confirmed_positive_covers")))
    state8_rows.extend(as_dict(row) for row in as_list(state8_followup.get("contrast_covers")))
    for row in state8_rows:
        add_type_pair(row.get("type"))
        add_unique(values["pay_status"], row.get("pay_status"))
        add_unique(values["positive_trailer"], row.get("positive_trailer"))
        for state_value in as_dict(row.get("state_counts")).keys():
            add_unique(values["state"], state_value)
        upload_counts = as_dict(row.get("upload_src_counts"))
        for upload_value in upload_counts.keys():
            add_unique(values["upload_src"], upload_value)

    for _, type_value, fields, derived in iter_followup_cover_rows(followup_reports, type_pair_lookup):
        add_type_pair(type_value)
        add_unique(values["pay_status"], fields.get("pay_status"))
        add_unique(values["positive_trailer"], fields.get("positive_trailer"))
        add_unique(values["positive_content_id"], fields.get("positive_content_id"))
        for state_value in as_dict(derived.get("state_counts")).keys():
            add_unique(values["state"], state_value)
        for upload_value in as_dict(derived.get("upload_src_counts")).keys():
            add_unique(values["upload_src"], upload_value)
        for f_counts in (
            parse_cover_video_slot_counts(fields.get("nomal_ids")),
            parse_cover_video_slot_counts(fields.get("vip_ids")),
        ):
            for f_value in f_counts.keys():
                add_unique(values["F"], f_value)
        for downright_value in list_value(fields.get("downright")):
            add_unique(values["downright"], downright_value)

    result = OrderedDict()
    for field_name in FIELD_ORDER:
        if field_name == "downright":
            coverage = "highlighted_codes_from_current_round_plus_doc_backfill"
            seed_downright = as_dict(seed_index_fields.get("downright"))
            if clean_text(seed_downright.get("coverage")):
                coverage = clean_text(seed_downright.get("coverage"))
            downright_values = iter_index_values(values.get("downright"))
            for seed_value in iter_index_values(seed_index_fields.get("downright")):
                if seed_value not in downright_values:
                    downright_values.append(seed_value)
            if not downright_values:
                downright_values = sorted(
                    [clean_text(value) for value in as_dict(seed_cards.get("downright")).keys() if clean_text(value)],
                    key=sort_value_key,
                )
            result[field_name] = OrderedDict((("coverage", coverage), ("values", downright_values)))
            continue

        merged_values = iter_index_values(values.get(field_name))
        seed_values = iter_index_values(seed_index_fields.get(field_name))
        if field_name == "type_name" and seed_values:
            ordered_values = [clean_text(value) for value in as_list(seed_index_fields.get(field_name)) if clean_text(value)]
            for generated_value in merged_values:
                if generated_value not in ordered_values:
                    ordered_values.append(generated_value)
            result[field_name] = ordered_values
            continue

        for seed_value in seed_values:
            if seed_value not in merged_values:
                merged_values.append(seed_value)
        merged_values.sort(key=sort_value_key)
        result[field_name] = merged_values
    return result


def build_observations(
    search_probe: dict[str, object],
    state_upload: dict[str, object],
    f_matrix: dict[str, object],
    cover_families: dict[str, object],
    state8_followup: dict[str, object],
    followup_reports: list[dict[str, object]],
    type_pair_lookup: dict[str, str],
) -> OrderedDict[str, OrderedDict[str, OrderedDict[str, object]]]:
    observations = make_observation_map()

    broad_probe = as_dict(search_probe.get("broad_probe"))
    for value, count in as_dict(broad_probe.get("pay_status_counts")).items():
        observe(observations, "pay_status", value, sample_count=to_int(count))
    for value, count in as_dict(broad_probe.get("type_counts")).items():
        observe(observations, "type", value, sample_count=to_int(count))
        if "/" in clean_text(value):
            _, type_name = clean_text(value).split("/", 1)
            observe(observations, "type_name", type_name, sample_count=to_int(count))
    for sample in as_list(broad_probe.get("representative_samples")):
        row = as_dict(sample)
        cid = clean_text(row.get("cid"))
        type_value = clean_text(row.get("type"))
        pay_status = clean_text(row.get("pay_status"))
        observe(observations, "pay_status", pay_status, representative_sample=cid, type_value=type_value)
        observe(observations, "positive_trailer", row.get("positive_trailer"), representative_sample=cid, type_value=type_value)
        observe(observations, "positive_content_id", row.get("positive_content_id"), representative_sample=cid, type_value=type_value)

    targeted_followups = as_dict(search_probe.get("targeted_followups"))
    for family_name in ("pay_status_5_family", "pay_status_9_family", "pay_status_15_family"):
        family = as_dict(targeted_followups.get(family_name))
        for sample in as_list(family.get("samples")):
            row = as_dict(sample)
            cid = clean_text(row.get("cid"))
            type_value = clean_text(row.get("type"))
            observe(observations, "pay_status", row.get("pay_status"), representative_sample=cid, type_value=type_value)
            observe(observations, "positive_trailer", row.get("positive_trailer"), representative_sample=cid, type_value=type_value)
            observe(observations, "positive_content_id", row.get("positive_content_id"), representative_sample=cid, type_value=type_value)

    state_rows = (
        as_list(state_upload.get("pages"))
        + as_list(state_upload.get("new_type_subset"))
        + as_list(state_upload.get("pay_status_5_and_9_field_shapes"))
        + as_list(as_dict(state_upload.get("sports_subset")).get("covers"))
    )
    for sample in state_rows:
        row = as_dict(sample)
        cid = clean_text(row.get("cid")) or clean_text(row.get("title"))
        type_value = clean_text(row.get("type"))
        observe(observations, "type", type_value, representative_sample=cid, type_value=type_value)
        if "/" in type_value:
            _, type_name = type_value.split("/", 1)
            observe(observations, "type_name", type_name, representative_sample=cid, sample_count=1)
        observe(observations, "pay_status", row.get("pay_status"), representative_sample=cid, type_value=type_value)
        for state_value, count in as_dict(row.get("state_counts")).items():
            observe(observations, "state", state_value, sample_count=to_int(count), representative_sample=cid, type_value=type_value)
        upload_counts = as_dict(row.get("upload_counts")) or as_dict(row.get("upload_src_counts"))
        for upload_value, count in upload_counts.items():
            observe(observations, "upload_src", upload_value, sample_count=to_int(count), representative_sample=cid, type_value=type_value)

    f_rows = (
        as_list(f_matrix.get("covers"))
        + as_list(f_matrix.get("new_type_subset"))
        + as_list(f_matrix.get("pay_status_5_and_9_samples"))
        + as_list(as_dict(f_matrix.get("sports_subset")).get("covers"))
    )
    for sample in f_rows:
        row = as_dict(sample)
        cid = clean_text(row.get("cid")) or clean_text(row.get("title"))
        type_value = clean_text(row.get("type"))
        observe(observations, "type", type_value, representative_sample=cid, type_value=type_value)
        observe(observations, "pay_status", row.get("pay_status"), representative_sample=cid, type_value=type_value)
        for field_name in ("nomal_f_counts", "vip_f_counts"):
            for f_value, count in as_dict(row.get(field_name)).items():
                observe(observations, "F", f_value, sample_count=to_int(count), representative_sample=cid, type_value=type_value)

    pay16 = as_dict(cover_families.get("pay_status_16_chain"))
    main_cover = as_dict(pay16.get("main_cover"))
    observe(
        observations,
        "pay_status",
        main_cover.get("pay_status"),
        representative_sample=main_cover.get("cid"),
        type_value=main_cover.get("type"),
    )

    state8_rows = [as_dict(state8_followup.get("seed_cover"))]
    state8_rows.extend(as_dict(row) for row in as_list(state8_followup.get("confirmed_positive_covers")))
    state8_rows.extend(as_dict(row) for row in as_list(state8_followup.get("contrast_covers")))
    for row in state8_rows:
        cid = clean_text(row.get("cid"))
        type_value = clean_text(row.get("type"))
        observe(observations, "pay_status", row.get("pay_status"), representative_sample=cid, type_value=type_value)
        observe(observations, "positive_trailer", row.get("positive_trailer"), representative_sample=cid, type_value=type_value)
        for state_value, count in as_dict(row.get("state_counts")).items():
            observe(observations, "state", state_value, sample_count=to_int(count), representative_sample=cid, type_value=type_value)
        for upload_value, count in as_dict(row.get("upload_src_counts")).items():
            observe(observations, "upload_src", upload_value, sample_count=to_int(count), representative_sample=cid, type_value=type_value)

    for cid, type_value, fields, derived in iter_followup_cover_rows(followup_reports, type_pair_lookup):
        observe(observations, "type", type_value, representative_sample=cid, type_value=type_value)
        if "/" in type_value:
            _, type_name = type_value.split("/", 1)
            observe(observations, "type_name", type_name, representative_sample=cid, sample_count=1)
        observe(observations, "pay_status", fields.get("pay_status"), representative_sample=cid, type_value=type_value)
        observe(
            observations,
            "positive_trailer",
            fields.get("positive_trailer"),
            representative_sample=cid,
            type_value=type_value,
        )
        observe(
            observations,
            "positive_content_id",
            fields.get("positive_content_id"),
            representative_sample=cid,
            type_value=type_value,
        )
        for state_value, count in as_dict(derived.get("state_counts")).items():
            observe(
                observations,
                "state",
                state_value,
                sample_count=to_int(count),
                representative_sample=cid,
                type_value=type_value,
            )
        for upload_value, count in as_dict(derived.get("upload_src_counts")).items():
            observe(
                observations,
                "upload_src",
                upload_value,
                sample_count=to_int(count),
                representative_sample=cid,
                type_value=type_value,
            )
        merged_f_counts = parse_cover_video_slot_counts(fields.get("nomal_ids"))
        for f_value, count in parse_cover_video_slot_counts(fields.get("vip_ids")).items():
            merged_f_counts[f_value] = max(merged_f_counts.get(f_value, 0), count)
        for f_value, count in merged_f_counts.items():
            observe(
                observations,
                "F",
                f_value,
                sample_count=to_int(count),
                representative_sample=cid,
                type_value=type_value,
            )
        for downright_value in list_value(fields.get("downright")):
            observe(
                observations,
                "downright",
                downright_value,
                sample_count=1,
                representative_sample=cid,
                type_value=type_value,
            )

    return observations


def build_cards(
    index_fields: OrderedDict[str, object],
    observations: OrderedDict[str, OrderedDict[str, OrderedDict[str, object]]],
    seed_cards: dict[str, object],
) -> OrderedDict[str, object]:
    cards = OrderedDict()
    for field_name in FIELD_ORDER:
        field_cards = OrderedDict()
        seed_field = as_dict(seed_cards.get(field_name))
        values = iter_index_values(index_fields.get(field_name))
        for seed_value in seed_field.keys():
            text = clean_text(seed_value)
            if text and text not in values:
                values.append(text)
        values.sort(key=sort_value_key)
        for value in values:
            obs = as_dict(as_dict(observations.get(field_name)).get(value))
            card = card_template(field_name, value, to_int(obs.get("sample_count")))
            card["representative_samples"] = union_str_lists(card.get("representative_samples"), obs.get("representative_samples"))
            card["types"] = union_str_lists(card.get("types"), obs.get("types"))
            seed_card = as_dict(seed_field.get(value))
            if seed_card:
                card = merge_seed_card(card, seed_card)
            field_cards[value] = card
        cards[field_name] = field_cards
    return cards


def apply_state8_followup(cards: OrderedDict[str, object], state8_followup: dict[str, object]) -> None:
    state_cards = as_dict(cards.setdefault("state", OrderedDict()))
    slot = as_dict(state_cards.setdefault("8", card_template("state", "8", 0)))
    seed_cover = as_dict(state8_followup.get("seed_cover"))
    positive_covers = [as_dict(row) for row in as_list(state8_followup.get("confirmed_positive_covers"))]
    representative_samples = union_str_lists(
        [seed_cover.get("cid")] + [row.get("cid") for row in positive_covers],
        [],
    )
    types = union_str_lists(
        [seed_cover.get("type")] + [row.get("type") for row in positive_covers],
        [],
    )
    slot["status"] = "small_family"
    slot["sample_count"] = len(representative_samples)
    slot["representative_samples"] = representative_samples
    slot["types"] = types
    slot["page_shapes"] = ["少儿聚合页", "表演演出聚合页"]
    slot["strong_correlations"] = [
        "当前常和 pay_status=8 共现，但不是充要条件",
        "当前已覆盖 positive_trailer=0/1",
    ]
    slot["counterexamples"] = [
        "state=8 不是空字段代理；在表演演出大聚合页里 targetid 仍是全满",
        "pay_status=8 不推出 state=8；mzc002000xmvpgy / mzc00200nlxxm5m 仍是纯 state=4",
        "state=8 也不推出 pay_status=8；mzc00200axsj6bx / pay_status=6 仍能打出少量 state=8 行",
    ]
    slot["current_blackbox_explanation"] = (
        "当前更像行级 small-family signal；已跨多个 cover，至少覆盖 type=106/113，不是单一 cover 级壳标签。"
    )
    slot["unconfirmed_items"] = [
        "为什么有些 sibling cover 只有稀疏 state=8 行，而有些 cover 会变成 state=8-heavy family",
        "官方后台命名",
    ]


def apply_manual_value_overlays(cards: OrderedDict[str, object]) -> None:
    pay_status_cards = as_dict(cards.setdefault("pay_status", OrderedDict()))
    slot6 = as_dict(pay_status_cards.setdefault("6", card_template("pay_status", "6", 0)))
    slot6["strong_correlations"] = union_str_lists(
        slot6.get("strong_correlations"),
        [
            "在当前 `type=106 + positive_trailer=1 + positive_content_id=1543606` 少儿样本里，至少已拆出 `double-zero` 与 `dual-full` 两支。",
            "kids 分支已跨 `小猪佩奇 / 汪汪队立大功 / 超级飞侠` 复现，不再是单一 IP 内部规律。",
            "`jynqzy9n3wfrsfp` 这类主题/旅行味道更强的少儿页，最新 field retest 仍是 strict `publish_date=20/20 + targetid=20/20`，说明它更靠近 clean dual-full，不应被标题风格直接推成 hybrid。",
        ],
    )
    slot6["counterexamples"] = union_str_lists(
        slot6.get("counterexamples"),
        [
            "`type=106 + pay_status=6` 不只对应单一少儿常规季页；`mzc00200qrzj493` 是 `publish_date=0/26 + targetid=0/26`，`zkbp0mrqhy0x1hl` 是 `publish_date=26/26 + targetid=26/26`。",
            "`double-zero` 也不推出 `upload_src=129`；`mzc00200qrzj493` 证明同样形态也可以是 `upload_src=20`。",
            "`第N季` 标题也不自动推出 `dual-full`；`mzc002006huuuiu / 小猪佩奇第10季[普通话版]` 与 `mzc00200syo2994 / 汪汪队大救援第五季` 都是 `double-zero`。",
            "`主题/旅行` 味道也不自动推出 hybrid/aggregation；`jynqzy9n3wfrsfp` 最新补测仍是 clean dual-full，而 `bzfkv5se8qaqel2 / mzc00200yokeal4` 才更像邻近 hybrid。",
            "前端当前也不直接按 raw `pay_status=6` 分支；focused runtime probe 里 `movie_single_pay6_exchange_true` 与 `tv_season_pay6_exchange_false` 都先暴露 `cover_pay_status=0`，但 `pay_status_exchange` 一真一假。",
        ],
    )
    slot6["current_blackbox_explanation"] = (
        "当前已是跨体育/电视剧/动漫/纪录片等多桶稳定值；但在 `type=106` 少儿 + `positive_trailer=1` 家族里，至少已分成 double-zero、clean season-style dual-full，以及更窄的 hybrid/aggregation 邻近分支。`jynqzy9n3wfrsfp` 现在更像 clean dual-full，而不是 hybrid。"
    )
    slot6["unconfirmed_items"] = [
        "kids aggregation/hybrid branch 是否应单列、以及它和 clean dual-full 的边界",
        "官方后台命名",
    ]

    slot8 = as_dict(pay_status_cards.setdefault("8", card_template("pay_status", "8", 0)))
    slot8["strong_correlations"] = union_str_lists(
        slot8.get("strong_correlations"),
        [
            "focused runtime probe 已在 `kids_free_pack_pay8` 抓到 parse-layer raw `8`，但 exposed `union.coverInfoMap.pay_status` 仍是 `0`。",
        ],
    )
    slot8["counterexamples"] = union_str_lists(
        slot8.get("counterexamples"),
        [
            "raw `8` 的前端可见性是页依赖的；同轮 focused runtime probe 里 `sports_replay_pay8` 与 `education_coveronly_pay8` 只看到 parse-layer `0`。",
        ],
    )
    slot8["unconfirmed_items"] = union_str_lists(
        slot8.get("unconfirmed_items"),
        [
            "前端为何只在部分 pay8 页面保留 raw 8",
        ],
    )

    slot15 = as_dict(pay_status_cards.setdefault("15", card_template("pay_status", "15", 0)))
    slot15["strong_correlations"] = union_str_lists(
        slot15.get("strong_correlations"),
        [
            "focused runtime probe 已在 `variety_topic_pay15` 抓到 parse-layer raw `15`，但 exposed `union.coverInfoMap.pay_status` 仍是 `0`，`pay_status_exchange=false`。",
        ],
    )
    slot15["unconfirmed_items"] = union_str_lists(
        slot15.get("unconfirmed_items"),
        [
            "raw 15 是否会在别的综艺页型上稳定保留到 parse layer",
        ],
    )

    positive_trailer_cards = as_dict(cards.setdefault("positive_trailer", OrderedDict()))
    slot_pt2 = as_dict(positive_trailer_cards.setdefault("2", card_template("positive_trailer", "2", 0)))
    slot_pt2["representative_samples"] = union_str_lists(
        slot_pt2.get("representative_samples"),
        [
            "mzc00200nkzol5n",
            "mzc002001w361jz",
            "mzc00200tzs7ig5",
        ],
    )
    slot_pt2["types"] = union_str_lists(
        slot_pt2.get("types"),
        [
            "2/电视剧",
            "10/综艺",
        ],
    )
    slot_pt2["strong_correlations"] = union_str_lists(
        slot_pt2.get("strong_correlations"),
        [
            "focused branch runtime followup 已直接覆盖 `mzc00200nkzol5n / mzc002001w361jz`，exposed `union.coverInfoMap.positive_trailer` 仍保持 `2`，且 getter 会重复命中。",
            "2026-06-20 同类 control-group followup 里，`type=10 / 综艺` 的 `mzc00200tzs7ig5` 也命中 `positive_trailer=2`，而且是该组里唯一稳定打出 `preview_badge / 预告` 卡面的分支。",
        ],
    )
    slot_pt2["counterexamples"] = union_str_lists(
        slot_pt2.get("counterexamples"),
        [
            "`positive_trailer=2` 不推出 pay_status=8；`mzc002001w361jz` 仍是 pay_status=6。",
            "`positive_trailer=2` 还不能直接推出独立 `trailer_module` / try-watch / gift 分支；它已经能在部分 page shell 上推出 `preview_badge / 预告` 卡面，但外显仍受 type / page shell 共同影响。",
        ],
    )
    slot_pt2["current_blackbox_explanation"] = (
        "当前它更像一个至少跨 `电视剧 + 综艺` 复现的 preview-like signal 候选；前端会把它归一化后保留进状态层，但外显仍受 type / page shell 共同影响，还不能把它直接命名成某个官方 UI 开关。"
    )
    slot_pt2["unconfirmed_items"] = union_str_lists(
        slot_pt2.get("unconfirmed_items"),
        [
            "它是否会在更多非电视剧 type 上稳定打出 preview-like 外显",
            "它是否会触发当前 probe 尚未命中的次级模块 / 请求链",
        ],
    )

    slot7 = as_dict(pay_status_cards.setdefault("7", card_template("pay_status", "7", 0)))
    slot7["strong_correlations"] = union_str_lists(
        slot7.get("strong_correlations"),
        ["当前已跨 `22/音乐`、`31/生活`、`111/文化历史` 复现，不再是单点异常"],
    )
    slot7["current_blackbox_explanation"] = (
        "当前已不再是单页单类目异常值；至少已跨音乐、生活、文化历史三支复现，但官方后台命名仍未确认。"
    )

    f_cards = as_dict(cards.setdefault("F", OrderedDict()))
    slot_f0 = as_dict(f_cards.setdefault("0", card_template("F", "0", 0)))
    slot_f0["strong_correlations"] = union_str_lists(
        slot_f0.get("strong_correlations"),
        ["当前强相关于预告 / 抢先看类条目"],
    )
    slot_f0["current_blackbox_explanation"] = (
        "当前更像预告 / 抢先看桶；已跨综艺、电视剧、动漫样本复现，但还不能直接命名成后台正式状态。"
    )

    slot_f4 = as_dict(f_cards.setdefault("4", card_template("F", "4", 0)))
    slot_f4["strong_correlations"] = union_str_lists(
        slot_f4.get("strong_correlations"),
        ["当前 live followup 里仍只落在预告类条目"],
    )
    slot_f4["current_blackbox_explanation"] = (
        "当前仍像更窄的预告类桶；这轮 live followup 已在《问心2》预告片样本上直接复现。"
    )

    type_cards = as_dict(cards.setdefault("type", OrderedDict()))
    type106 = as_dict(type_cards.setdefault("106/少儿", card_template("type", "106/少儿", 0)))
    type106["representative_samples"] = union_str_lists(
        type106.get("representative_samples"),
        [
            "mzc00200qrzj493",
            "zkbp0mrqhy0x1hl",
            "ca1k6ja4k81h8ov",
            "ob6ak6eq2wp5qui",
            "mzc00200syo2994",
            "1ftxhqhqz7choul",
            "jynqzy9n3wfrsfp",
            "bzfkv5se8qaqel2",
            "mzc00200yokeal4",
        ],
    )
    type106["strong_correlations"] = union_str_lists(
        type106.get("strong_correlations"),
        [
            "当前 kids 样本里同时包含 pay_status=6 的 double-zero / clean season-style dual-full 两支，以及 pay_status=8 的免费/精华聚合支。",
            "double-zero 与 clean season-style dual-full 已跨 `小猪佩奇 / 汪汪队立大功 / 超级飞侠` 复现。",
            "latest same-day base-4 followup 里，`bzfkv5se8qaqel2` / `mzc00200yokeal4` 继续保持 hybrid/aggregation-like 轮廓，而 `jynqzy9n3wfrsfp` 仍是 clean dual-full。",
        ],
    )
    type106["counterexamples"] = union_str_lists(
        type106.get("counterexamples"),
        [
            "`type=106` 不能只绑定到单一少儿常规季页；同一 type 下至少已有 double-zero、clean dual-full、free/aggregation-like 多种形态。",
            "`第N季` 标题不推出统一页型；`ca1k6ja4k81h8ov` 与 `ob6ak6eq2wp5qui` 是 dual-full，但 `mzc002006huuuiu` 与 `mzc00200syo2994` 仍是 double-zero。",
            "`主题/旅行` 标题也不自动推出 hybrid；`jynqzy9n3wfrsfp` 的最新补测仍是 `publish_date=20/20 + targetid=20/20`。",
        ],
    )
    type106["current_blackbox_explanation"] = (
        "当前可稳定当作 `106/少儿` 的黑盒类目桶使用；但这个桶内部已明显分叉，至少包含 pay_status=6 的 double-zero、clean season-style dual-full，以及更窄的 hybrid/aggregation 邻近分支，再加上 pay_status=8 的 free/aggregation-like 分支。"
    )
    type106["unconfirmed_items"] = union_str_lists(
        type106.get("unconfirmed_items"),
        [
            "kids aggregation/hybrid branch 的稳定边界",
            "官方后台命名",
        ],
    )

    downright_cards = as_dict(cards.setdefault("downright", OrderedDict()))
    overlays = {
        "31": {
            "counterexamples": [
                "`31` 已不是《一人之下 第6季》专属；电影单片 `mzc00200sq680j2` 也命中该码",
            ],
            "current_blackbox_explanation": "当前已确认跨动漫季页与电影单片复现，但边界仍偏高熵，暂不升级成稳定语义码。",
        },
        "41": {
            "strong_correlations": [
                "当前 live followup 里集中出现在 `庆余年第二季 / 长安诺` 这对电视剧季页样本",
            ],
            "current_blackbox_explanation": "当前是相对干净的电视剧季页差异码簇之一，但具体业务码义仍待命名。",
        },
        "44": {
            "counterexamples": [
                "`44` 不只落在单一电视剧季页；电影单片 `mzc002003r5yq45` 也直接命中",
            ],
            "current_blackbox_explanation": "当前已确认跨电视剧季页与电影单片复现，不能再写成单样本差异码。",
        },
        "62": {
            "counterexamples": [
                "`62` 不是单类目专属；体育人物 `mzc00383lw807hq` 与电影单片 `mzc00200sq680j2` 都命中",
            ],
            "current_blackbox_explanation": "当前已确认跨体育与电影流动，不能写成窄专题专属码。",
        },
        "184": {
            "counterexamples": [
                "`184` 不只落在少儿 / 纪录片；电影单片 `mzc00200sq680j2` 也是正例",
            ],
            "current_blackbox_explanation": "当前最强样本仍在纪录片 / 少儿邻域，但电影反例已经说明它不是窄类目专属码。",
        },
    }
    for value, patch in overlays.items():
        slot = as_dict(downright_cards.setdefault(value, card_template("downright", value, 0)))
        for key in ("strong_correlations", "counterexamples"):
            if key in patch:
                slot[key] = union_str_lists(slot.get(key), patch[key])
        if patch.get("current_blackbox_explanation"):
            slot["current_blackbox_explanation"] = patch["current_blackbox_explanation"]


def normalize_card(field_name: str, value: str, card: dict[str, object]) -> OrderedDict[str, object]:
    representative_samples = union_str_lists(card.get("representative_samples"), [])
    types = union_str_lists(card.get("types"), [])
    page_shapes = union_str_lists(card.get("page_shapes"), [])
    strong_correlations = union_str_lists(card.get("strong_correlations"), [])
    counterexamples = union_str_lists(card.get("counterexamples"), [])
    unconfirmed_items = union_str_lists(card.get("unconfirmed_items"), [])
    if "官方后台命名" in unconfirmed_items and "official backend naming" in unconfirmed_items:
        unconfirmed_items = [item for item in unconfirmed_items if item != "official backend naming"]

    sample_count = to_int(card.get("sample_count"))
    if sample_count <= 0 and clean_text(card.get("sample_count_hint")) == "high":
        sample_count = max(5, len(representative_samples))
    sample_count = max(sample_count, len(representative_samples))

    status = reconcile_status(
        field_name,
        value,
        sample_count,
        clean_text(card.get("status")),
    )
    explanation = normalize_explanation(
        field_name,
        value,
        status,
        sample_count,
        clean_text(card.get("current_blackbox_explanation")),
    )

    normalized = OrderedDict(
        (
            ("status", status),
            ("sample_count", sample_count),
            ("representative_samples", representative_samples),
            ("types", types),
            ("page_shapes", page_shapes),
            ("strong_correlations", strong_correlations),
            ("counterexamples", counterexamples),
            ("current_blackbox_explanation", explanation),
            ("unconfirmed_items", unconfirmed_items or ["official backend naming"]),
        )
    )
    index_scope = clean_text(card.get("index_scope"))
    if index_scope:
        normalized["index_scope"] = index_scope
    return normalized


def normalize_cards(
    cards: OrderedDict[str, object],
    index_fields: OrderedDict[str, object],
) -> OrderedDict[str, object]:
    normalized = OrderedDict()
    for field_name in FIELD_ORDER:
        field_cards = as_dict(cards.get(field_name))
        values = iter_index_values(index_fields.get(field_name))
        for existing_value in field_cards.keys():
            text = clean_text(existing_value)
            if text and text not in values:
                values.append(text)
        values.sort(key=sort_value_key)
        normalized[field_name] = OrderedDict(
            (value, normalize_card(field_name, value, as_dict(field_cards.get(value)))) for value in values
        )
    return normalized


def build_index_doc(seed_index_doc: dict[str, object], fields: OrderedDict[str, object]) -> OrderedDict[str, object]:
    field_aliases = OrderedDict(FIELD_ALIASES)
    for key, value in as_dict(seed_index_doc.get("field_aliases")).items():
        field_aliases[clean_text(key)] = value
    return OrderedDict(
        (
            ("generated_at", dt.date.today().isoformat()),
            ("field_aliases", field_aliases),
            ("fields", fields),
        )
    )


def build_cards_doc(seed_cards_doc: dict[str, object], cards: OrderedDict[str, object]) -> OrderedDict[str, object]:
    field_aliases = OrderedDict(FIELD_ALIASES)
    for key, value in as_dict(seed_cards_doc.get("field_aliases")).items():
        field_aliases[clean_text(key)] = value
    open_items = union_str_lists(
        seed_cards_doc.get("open_items"),
        [
            "downright 目前仍只覆盖高信号差异码，完整 code universe 需要继续抽取",
            "type_name 当前按 1:1 展示名层复用，若后续出现同 type 不同展示名再拆卡",
            "部分 upload_src / downright 代表样本仍有标题已知但 CID 待回填的情况",
        ],
    )
    return OrderedDict(
        (
            ("generated_at", dt.date.today().isoformat()),
            ("status_scale", STATUS_SCALE),
            ("field_aliases", field_aliases),
            ("cards", cards),
            ("open_items", open_items),
        )
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - older Python compatibility
        pass

    args = parse_args()
    analysis_dir = Path(args.analysis_dir)
    search_probe = load_json(analysis_dir / "search_backend_seed_probe_20260619.json")
    state_upload = load_json(analysis_dir / "state_upload_dirty_pages_20260619.json")
    f_matrix = load_json(analysis_dir / "f_matrix_extra_categories_20260619.json")
    cover_families = load_json(analysis_dir / "cover_family_boundaries_20260619.json")
    state8_followup = load_optional_json(analysis_dir / "state8_family_followup_20260619.json")
    followup_reports = load_followup_reports(analysis_dir)
    seed_index_doc = load_optional_json(analysis_dir / "enum_index_20260619.json")
    seed_cards_doc = load_optional_json(analysis_dir / "enum_cards_20260619.json")
    seed_index_fields = as_dict(seed_index_doc.get("fields"))
    seed_cards = as_dict(seed_cards_doc.get("cards"))
    type_pair_lookup = build_type_pair_lookup(seed_index_fields)

    index_fields = collect_index(
        search_probe,
        state_upload,
        f_matrix,
        cover_families,
        state8_followup,
        followup_reports,
        seed_index_fields,
        seed_cards,
    )
    observations = build_observations(
        search_probe,
        state_upload,
        f_matrix,
        cover_families,
        state8_followup,
        followup_reports,
        type_pair_lookup,
    )
    cards = build_cards(index_fields, observations, seed_cards)
    apply_state8_followup(cards, state8_followup)
    apply_manual_value_overlays(cards)
    normalized_cards = normalize_cards(cards, index_fields)

    index_doc = build_index_doc(seed_index_doc, index_fields)
    cards_doc = build_cards_doc(seed_cards_doc, normalized_cards)

    if args.artifact == "index":
        output = index_doc
    elif args.artifact == "cards":
        output = cards_doc
    else:
        output = OrderedDict((("enum_index", index_doc), ("enum_cards", cards_doc)))

    rendered = json.dumps(output, ensure_ascii=False, indent=args.indent)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
