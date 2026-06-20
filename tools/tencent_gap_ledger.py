from __future__ import annotations

import argparse
from collections import OrderedDict
import datetime as dt
import json
from pathlib import Path
import sys


COMPLETION_MODEL = "black_box_closure_plus_frontend_semantics_plus_environment_matrix_plus_enum_cards"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a machine-readable gap ledger from current Tencent API analysis files."
    )
    parser.add_argument(
        "--analysis-dir",
        default="analysis",
        help="Directory containing the current analysis JSON files",
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
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def clean_text(value: object) -> str:
    return str(value).strip()


def find_frontend_field(frontend: dict[str, object], field_name: str) -> dict[str, object]:
    for item in as_list(frontend.get("fields")):
        row = as_dict(item)
        if clean_text(row.get("field")) == field_name:
            return row
    return {}


def find_card(cards_doc: dict[str, object], field_name: str, value: str) -> dict[str, object]:
    cards = as_dict(cards_doc.get("cards"))
    field_cards = as_dict(cards.get(field_name))
    return as_dict(field_cards.get(value))


def union_str_lists(*sources: object) -> list[str]:
    merged: list[str] = []
    for source in sources:
        if isinstance(source, list):
            for value in source:
                text = clean_text(value)
                if text and text not in merged:
                    merged.append(text)
    return merged


def build_api_contract_confirmed(
    api_contract: dict[str, object],
    environment_matrix: dict[str, object],
) -> list[str]:
    api2 = as_dict(api_contract.get("api2"))
    idlist_limit = as_dict(api2.get("idlist_limit"))
    limit = clean_text(idlist_limit.get("max_nonempty_items")) or "32"
    return [
        f"API1 and API2 both have a {limit} non-empty item limit; 33 returns -111001.",
        "Headers and UA did not change the tested API1/API2 contract branches across the current same-day plus next-day retest matrix, including the browser-like header and synthetic-cookie followup.",
        "API2 only switches to JSONP on exact lowercase `otype=json`.",
    ]


def build_frontend_confirmed(frontend: dict[str, object]) -> list[str]:
    return [
        "`pay_status` participates in VIP-related frontend reporting and adjacent gift gating.",
        "Dynamic hook evidence shows raw-like `pay_status` values still survive at `JSON.parse` layer, while the first exposed `union.coverInfoMap.pay_status` slot is already `0` on tested PC Web detail pages.",
        "Focused runtime followup now captures parse-layer raw `6/8/15` on selected pages, while the exposed `union.coverInfoMap.pay_status` slot still stays `0` across those same cases.",
        "Focused runtime followup also shows `pay_status=6` does not imply one frontend branch by itself: the movie sample keeps `pay_status_exchange=true`, while the TV-season sample keeps `pay_status_exchange=false` even though both pages expose `cover_pay_status=0`.",
        "Focused branch runtime followup now also covers normalized `positive_trailer=0/1/2`, and the 2026-06-20 same-type control groups extend that into visible first-screen divergence: type=10 splits `pt=0/1/2` across `选集/SVIP/纯享`, short-video-forward, and preview-badge surfaces; type=106 and type=4 also reproduce pt-dependent divergence. This is still correlation, not sole-cause proof.",
        "`state` is normalized into the `union` store and directly drives unavailable/offline/deleted/not-playable validation branches.",
        "`downright` gates download-related toolbar behavior.",
        "`cover_list / c_covers / topic_id_list` are merged before the next frontend request chain.",
        "`publish_date` is reformatted and gated before display.",
        "`targetid` now has a static player/danmaku sink, runtime getter hits, stronger comment/community-side evidence, and a partially closed runtime consumer path: non-empty `root.base.commentInfo.targetid/commentid` samples are no longer kids-only, their decoded values stay disjoint from the observed `dokiid/ftid` request chain, and the current live magic-danmaku REPORT-click producer still only emits `{id}` while the downstream sink expects `b.data.targetId`; a synthetic runtime probe proves that raw `DANMAKU_REPORT` payloads on the real `Dte` listener bus do map through to popup `targetid=` query values, while nested payloads collapse to `id=undefined&targetid=undefined`. A separate report-identity audit narrows the natural-producer gap further: tested anonymous comment-report buttons on positive pages expose disjoint `feed_id/cp_id` identities rather than `commentInfo.targetid/commentid` or `dokiid/ftid`, and still do not open a targetid-bearing popup. The remaining open question is the natural producer, not the downstream consumer mapping.",
        "`positive_trailer` is normalized into frontend state and now has repeatable same-type surface correlation, but it is not yet isolated as the sole branch switch.",
        "`F` is present in tested startup / SSR payloads, but current tested detail startup/main/runtime slices still do not expose a named consumer.",
        "`upload_src` is still absent from current tested detail startup/main/runtime slices and may only surface later in a secondary bundle or non-detail path.",
    ]


def build_enum_progress(cards_doc: dict[str, object], index_doc: dict[str, object]) -> list[str]:
    type_count = len(as_list(as_dict(index_doc.get("fields")).get("type")))
    return [
        "pay_status=5 remains a stable_value within a narrow movie branch",
        "pay_status=6 can no longer be summarized as one single kids regular-season shape; the current type=106 family already splits into at least a double-zero branch, a clean season-style dual-full branch, and a narrower hybrid/aggregation neighborhood, while `jynqzy9n3wfrsfp` now reinforces that not every theme/travel-looking kids page belongs to hybrid",
        "pay_status=9 is now a broader small_family and is no longer explainable as anime-only or upload_src=149-only",
        "pay_status=15 and 16 both remain variety-bounded small_family values, but both have already expanded well beyond the first over-narrow explanations",
        "upload_src=2048 is now replicated on a second independent cover and should be treated as a type=111 small family rather than a single-point anomaly",
        f"type universe expanded to {type_count} observed values including 28/29/111",
    ]


def build_open_gaps(
    cards_doc: dict[str, object],
    frontend: dict[str, object],
    environment_matrix: dict[str, object],
) -> list[OrderedDict[str, object]]:
    def gap(field: str, needs: list[str]) -> OrderedDict[str, object]:
        return OrderedDict((("field", field), ("needs", needs)))

    gaps = [
        gap(
            "pay_status=15",
            [
                "confirm whether it can stably escape the current variety-bounded family",
                "official naming still unknown",
            ],
        ),
        gap(
            "pay_status=16",
            [
                "confirm whether it can cross out of variety",
                "official naming still unknown",
            ],
        ),
        gap(
            "pay_status=9",
            [
                "backfill cleaner type/page-shape labels for the new dance/long-tail samples",
                "determine whether it should stay small_family or eventually upgrade",
            ],
        ),
        gap(
            "upload_src=2048",
            [
                "determine whether the family is stable beyond current type=111 knowledge pages",
                "official naming still unknown",
            ],
        ),
        gap(
            "frontend_upload_src_trace",
            [
                "confirm whether `upload_src` is omitted from the current tested detail startup/main/runtime slice or consumed later in a secondary bundle / non-detail runtime path",
            ],
        ),
        gap(
            "frontend_F_trace",
            [
                "confirm whether startup-payload `F` only shapes generic rows or is consumed downstream in player/runtime code after the currently negative tested detail startup/main/runtime scan",
            ],
        ),
        gap(
            "frontend_positive_trailer_branch",
            [
                "separate positive_trailer effect from type/page-shell carry-over; current same-type controls prove correlation, not sole causality",
                "expand representatives until `pt=0/1/2` maps cleanly to stable first-screen modules across major type buckets",
            ],
        ),
        gap(
            "frontend_targetid_runtime_callsite",
            [
                "find the real live producer that bridges into the already-closed popup sink; the tested anonymous report-button DOM path only exposes disjoint `feed_id/cp_id` identities",
                "confirm whether `commentInfo.targetid/commentid` ever converges with either `dokiid/ftid` or `feed_id/cp_id` in a later lazy/login path",
                "retest login / hover-reveal / menu-open paths to see whether any natural report entry upgrades into a non-empty targetid popup",
            ],
        ),
        gap(
            "state=8_family",
            [
                "explain why some sibling covers only have sparse `state=8` rows while others are `state=8`-heavy",
                "decide whether the current `type=106` and `type=113` branches are enough to promote a more stable family model",
            ],
        ),
        gap(
            "environment_matrix_closure",
            [
                "real-session cookie / login-state / aged-cookie environments are still outside the current matrix; the current browser-like cookie check is synthetic only",
                "representative field-drift cross-day closure is now available for the five canonical pages, but it is not yet expanded to every page-shape bucket or every second representative",
                "type=4 sports pages now split across replay, person/info shell, feature-doc, and a stronger match-highlights/collection shell family; the remaining sports gap is whether mixed event hubs like `mzc0020069a6anp` should be modeled as sibling to the cleaner `mzc002003fh665c` bucket",
                "type=106 kids pages now include at least a double-zero branch, a clean season-style dual-full branch, and a narrower hybrid/aggregation neighborhood; `jynqzy9n3wfrsfp` no longer looks like hybrid and instead reinforces clean dual-full",
            ],
        ),
        gap(
            "downright_full_index",
            [
                "extract the complete code universe instead of only high-signal rare codes",
                "reconcile current representative samples for 31/41/44/62/184",
            ],
        ),
    ]
    return gaps


def build_stop_condition_upgrade() -> OrderedDict[str, object]:
    return OrderedDict(
        (
            (
                "rule",
                "Require two consecutive six-agent rounds with no new contract branch, no new non-empty enum value, no stable counterexample, and no new page-shape explanation branch.",
            ),
            (
                "extra_requirements",
                [
                    "main type buckets covered",
                    "main page-shape buckets covered",
                    "every non-empty pay_status classified",
                    "every new upload_src either replicated or marked anomaly",
                ],
            ),
        )
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover - older Python compatibility
        pass

    args = parse_args()
    analysis_dir = Path(args.analysis_dir)
    api_contract = load_json(analysis_dir / "api_contract_summary_20260619.json")
    frontend = load_json(analysis_dir / "frontend_field_consumption_20260619.json")
    environment_matrix = load_json(analysis_dir / "environment_matrix_20260619.json")
    enum_cards = load_json(analysis_dir / "enum_cards_20260619.json")
    enum_index = load_json(analysis_dir / "enum_index_20260619.json")

    report = OrderedDict(
        (
            ("generated_at", dt.date.today().isoformat()),
            ("completion_model", COMPLETION_MODEL),
            (
                "confirmed_now",
                OrderedDict(
                    (
                        ("api_contract", build_api_contract_confirmed(api_contract, environment_matrix)),
                        ("frontend_semantics", build_frontend_confirmed(frontend)),
                        ("enum_progress", build_enum_progress(enum_cards, enum_index)),
                    )
                ),
            ),
            ("open_gaps", build_open_gaps(enum_cards, frontend, environment_matrix)),
            ("stop_condition_upgrade", build_stop_condition_upgrade()),
        )
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=args.indent)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
