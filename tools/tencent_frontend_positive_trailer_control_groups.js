import { runProbe as runVisibleProbe } from "./tencent_frontend_positive_trailer_branch_probe.js";

const DEFAULT_CASES = [
  {
    bucket: "type10_variety_pt0_pay15",
    url: "https://v.qq.com/x/cover/mzc002001u873es.html",
  },
  {
    bucket: "type10_variety_pt1_pay15",
    url: "https://v.qq.com/x/cover/mzc00200k1tze71.html",
  },
  {
    bucket: "type10_variety_pt1_pay16",
    url: "https://v.qq.com/x/cover/mzc00200u2ay1kj.html",
  },
  {
    bucket: "type10_variety_pt2_pay16",
    url: "https://v.qq.com/x/cover/mzc00200tzs7ig5.html",
  },
  {
    bucket: "type106_kids_pt0_pay8",
    url: "https://v.qq.com/x/cover/mzc00200j7l2u0p.html",
  },
  {
    bucket: "type106_kids_pt1_pay6",
    url: "https://v.qq.com/x/cover/jynqzy9n3wfrsfp.html",
  },
  {
    bucket: "type4_sports_pt0_pay6",
    url: "https://v.qq.com/x/cover/mzc00383lw807hq.html",
  },
  {
    bucket: "type4_sports_pt1_pay8",
    url: "https://v.qq.com/x/cover/mzc0020069a6anp.html",
  },
];

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 12000,
    timeoutMs: 45000,
    indent: 2,
    browserPath: "",
  };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--wait-ms") {
      args.waitMs = Number(argv[++index]);
      continue;
    }
    if (token === "--timeout-ms") {
      args.timeoutMs = Number(argv[++index]);
      continue;
    }
    if (token === "--indent") {
      args.indent = Number(argv[++index]);
      continue;
    }
    if (token === "--browser-path") {
      args.browserPath = argv[++index] || "";
      continue;
    }
    if (token === "--case") {
      const raw = argv[++index] || "";
      const pivot = raw.indexOf("=");
      if (pivot <= 0) {
        throw new Error(`Invalid --case value: ${raw}`);
      }
      args.cases.push({
        bucket: raw.slice(0, pivot),
        url: raw.slice(pivot + 1),
      });
      continue;
    }
    throw new Error(`Unknown option: ${token}`);
  }
  return args;
}

function toCount(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function deriveSurfaceFlags(entry) {
  const moduleCounts = entry.module_keyword_counts || {};
  const tabCounts = entry.tab_keyword_counts || {};
  const badgeCounts = entry.card_badge_keyword_counts || {};
  const titleCounts = entry.card_title_keyword_counts || {};
  return {
    has_trailer_module: toCount(moduleCounts["精彩预告"]) > 0,
    has_preview_badge: toCount(badgeCounts["预告"]) > 0,
    has_clip_tab: toCount(tabCounts["精彩片花"]) > 0,
    has_episode_surface: toCount(moduleCounts["选集"]) > 0,
    has_short_video_surface:
      toCount(moduleCounts["更多短视频"]) > 0 || toCount(tabCounts["更多短视频"]) > 0,
    has_svip_badges: toCount(badgeCounts.SVIP) > 0,
    has_chunxiang_titles: toCount(titleCounts["纯享"]) > 0,
  };
}

function buildPatternSummary(entries) {
  const summary = {
    case_count: entries.length,
    buckets: entries.map((entry) => entry.bucket),
    representative_titles: entries.map((entry) => entry.title).filter(Boolean).slice(0, 4),
    trailer_module_hits: 0,
    preview_badge_hits: 0,
    clip_tab_hits: 0,
    episode_surface_hits: 0,
    short_video_surface_hits: 0,
    svip_badge_hits: 0,
    chunxiang_title_hits: 0,
  };
  for (const entry of entries) {
    const flags = entry.surface_flags || {};
    summary.trailer_module_hits += flags.has_trailer_module ? 1 : 0;
    summary.preview_badge_hits += flags.has_preview_badge ? 1 : 0;
    summary.clip_tab_hits += flags.has_clip_tab ? 1 : 0;
    summary.episode_surface_hits += flags.has_episode_surface ? 1 : 0;
    summary.short_video_surface_hits += flags.has_short_video_surface ? 1 : 0;
    summary.svip_badge_hits += flags.has_svip_badges ? 1 : 0;
    summary.chunxiang_title_hits += flags.has_chunxiang_titles ? 1 : 0;
  }
  return summary;
}

function buildGroupSummaries(entries) {
  const groups = new Map();
  for (const entry of entries) {
    const type = String(entry.union_snapshot?.cover_type ?? "");
    const typeName = String(entry.union_snapshot?.cover_type_name ?? "");
    const positiveTrailer = String(entry.union_snapshot?.cover_positive_trailer ?? "");
    const key = `${type}/${typeName}`;
    if (!groups.has(key)) {
      groups.set(key, {
        cover_type: type,
        cover_type_name: typeName,
        by_positive_trailer: {},
      });
    }
    const slot = groups.get(key);
    slot.by_positive_trailer[positiveTrailer] = slot.by_positive_trailer[positiveTrailer] || [];
    slot.by_positive_trailer[positiveTrailer].push(entry);
  }

  const summaries = [];
  for (const group of groups.values()) {
    const byPositiveTrailer = {};
    for (const [positiveTrailer, groupEntries] of Object.entries(group.by_positive_trailer)) {
      byPositiveTrailer[positiveTrailer] = buildPatternSummary(groupEntries);
    }
    summaries.push({
      cover_type: group.cover_type,
      cover_type_name: group.cover_type_name,
      by_positive_trailer: byPositiveTrailer,
    });
  }
  return summaries;
}

function buildTakeaways(cases, groupSummaries) {
  const takeaways = [];

  const type10 = groupSummaries.find(
    (entry) => entry.cover_type === "10" || entry.cover_type_name === "综艺"
  );
  if (type10) {
    const pt0 = type10.by_positive_trailer["0"];
    const pt1 = type10.by_positive_trailer["1"];
    const pt2 = type10.by_positive_trailer["2"];
    if (pt0 && pt1 && pt2) {
      takeaways.push(
        "Within the same type=10 / variety control group, positive_trailer now splits into visibly different frontend surfaces: pt=0 stays closer to `选集` / `SVIP` / `纯享`, pt=1 keeps the same variety family but does not collapse into the same exact episode-list signature, and pt=2 becomes the strongest candidate for a preview-like branch."
      );
    }
  }

  const type106 = groupSummaries.find(
    (entry) => entry.cover_type === "106" || entry.cover_type_name === "少儿"
  );
  if (type106 && type106.by_positive_trailer["0"] && type106.by_positive_trailer["1"]) {
    takeaways.push(
      "The same type=106 / kids control group reproduces a positive_trailer split as well: pt=1 keeps the previously seen `精彩片花`-style branch, while pt=0 moves away from that tab signature and into a more collection-like surface."
    );
  }

  const type4 = groupSummaries.find(
    (entry) => entry.cover_type === "4" || entry.cover_type_name === "体育"
  );
  if (type4 && type4.by_positive_trailer["0"] && type4.by_positive_trailer["1"]) {
    takeaways.push(
      "The type=4 / sports control group still shows page-shape carry-over, but positive_trailer=0 and 1 do not collapse into an identical first-screen pattern there either."
    );
  }

  const pt2Cases = cases.filter((entry) => String(entry.union_snapshot?.cover_positive_trailer) === "2");
  if (
    pt2Cases.length >= 2 &&
    pt2Cases.every((entry) => entry.surface_flags?.has_trailer_module && entry.surface_flags?.has_preview_badge)
  ) {
    takeaways.push(
      "Across both the earlier pt=2 representative pages and the new same-type control groups, positive_trailer=2 remains the strongest visible candidate for a preview-oriented frontend surface."
    );
  }

  takeaways.push(
    "These control groups strengthen the frontend-semantic evidence, but they still do not prove a strict same-layout causal rerender from positive_trailer alone; type-specific page shape and operating shell are still part of the explanation."
  );
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const baseReport = await runVisibleProbe({
    ...options,
    cases,
  });
  const enrichedCases = (baseReport.cases || []).map((entry) => ({
    ...entry,
    surface_flags: deriveSurfaceFlags(entry),
  }));
  const groupSummaries = buildGroupSummaries(enrichedCases);
  return {
    generated_at: new Date().toISOString(),
    scope: "same-type control-group probe for positive_trailer frontend semantics",
    source_tool: "tools/tencent_frontend_positive_trailer_control_groups.js",
    base_probe: "tools/tencent_frontend_positive_trailer_branch_probe.js",
    method: {
      ...baseReport.method,
      control_goal:
        "reduce cross-type ambiguity by comparing positive_trailer splits inside the same type buckets",
    },
    cases: enrichedCases,
    group_summaries: groupSummaries,
    takeaways: buildTakeaways(enrichedCases, groupSummaries),
  };
}

async function cliMain(argv) {
  const args = parseArgs(argv);
  const report = await runProbe(args);
  const indent = Number.isFinite(args.indent) ? args.indent : 2;
  const proc = globalThis.process;
  if (proc && proc.stdout) {
    proc.stdout.write(JSON.stringify(report, null, indent));
  }
}

const proc = globalThis.process;
const argv = proc && Array.isArray(proc.argv) ? proc.argv.slice(2) : [];
if (proc && argv[0] === "--cli") {
  cliMain(argv.slice(1)).catch((error) => {
    const message = JSON.stringify(
      {
        error: String(error),
        stack: error && typeof error.stack === "string" ? error.stack.split("\n").slice(0, 8) : [],
      },
      null,
      2
    );
    proc.stderr.write(message);
    proc.exitCode = 1;
  });
}
