import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);

const DEFAULT_BROWSER_CANDIDATES = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
];

const DEFAULT_CASES = [
  {
    bucket: "tv_topic_positive_trailer_2_pay8",
    url: "https://v.qq.com/x/cover/mzc00200nkzol5n.html",
  },
  {
    bucket: "tv_season_positive_trailer_2_pay6",
    url: "https://v.qq.com/x/cover/mzc002001w361jz.html",
  },
  {
    bucket: "variety_topic_positive_trailer_0",
    url: "https://v.qq.com/x/cover/mzc002001u873es/k004768pj4j.html",
  },
  {
    bucket: "kids_positive_trailer_1",
    url: "https://v.qq.com/x/cover/jynqzy9n3wfrsfp/l0020z7maus.html",
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

async function resolveBrowserPath(explicitPath = "") {
  if (explicitPath) {
    const fs = await import("node:fs/promises");
    await fs.access(explicitPath);
    return explicitPath;
  }
  const fs = await import("node:fs/promises");
  for (const candidate of DEFAULT_BROWSER_CANDIDATES) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {}
  }
  throw new Error("Could not find a local Chrome/Edge executable.");
}

async function loadPlaywright() {
  const runtimeNodeModules = "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
  try {
    const moduleBuiltin = require("node:module");
    const nodePath = process.env.NODE_PATH ? process.env.NODE_PATH.split(path.delimiter) : [];
    if (!nodePath.includes(runtimeNodeModules)) {
      process.env.NODE_PATH = [runtimeNodeModules, ...nodePath].filter(Boolean).join(path.delimiter);
      if (typeof moduleBuiltin.Module?._initPaths === "function") {
        moduleBuiltin.Module._initPaths();
      }
    }
  } catch {}
  const requireCandidates = [
    "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
    "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.js",
    "playwright",
  ];
  for (const candidate of requireCandidates) {
    try {
      return require(candidate);
    } catch {}
  }
  const importCandidates = [
    "playwright",
    "file:///C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs",
  ];
  for (const candidate of importCandidates) {
    try {
      return await import(candidate);
    } catch {}
  }
  throw new Error("Could not resolve `playwright`.");
}

function extractCidVid(url) {
  const coverMatch = /\/cover\/([^/.?#]+)(?:\/([^/.?#]+))?/.exec(url || "");
  return {
    cid: coverMatch?.[1] || null,
    vid: coverMatch?.[2] || null,
  };
}

function collectKeywordCounts(items, key) {
  const counts = {};
  for (const item of items) {
    const value = String(item?.[key] || "");
    for (const keyword of ["预告", "片花", "纯享", "正片", "SVIP", "更多短视频", "精彩预告", "精彩片花", "选集"]) {
      if (value.includes(keyword)) {
        counts[keyword] = (counts[keyword] || 0) + 1;
      }
    }
  }
  return counts;
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  try {
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }
    const data = await page.evaluate(() => {
      const visible = (node) => {
        if (!node) {
          return false;
        }
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };

      const textOf = (node) => (node?.innerText || node?.textContent || "").replace(/\s+/g, " ").trim();
      const pickVisibleTexts = (selector, limit = 20) =>
        Array.from(document.querySelectorAll(selector))
          .filter((node) => visible(node))
          .map((node) => textOf(node))
          .filter((text) => text && text.length <= 80)
          .slice(0, limit);

      const moduleTitles = Array.from(document.querySelectorAll(".module-title"))
        .filter((node) => visible(node))
        .map((node) => textOf(node))
        .filter(Boolean)
        .slice(0, 20);

      const tabNodes = Array.from(document.querySelectorAll(".tab-node, .tab-node-selected, [role='tab']"))
        .filter((node) => visible(node))
        .map((node) => ({
          text: textOf(node),
          className: String(node.className || "").slice(0, 120),
          selected:
            String(node.className || "").includes("selected") ||
            node.getAttribute("aria-selected") === "true",
        }))
        .filter((node) => node.text)
        .slice(0, 20);

      const cards = Array.from(document.querySelectorAll(".video-item, .video-item-wrapper"))
        .filter((node) => visible(node))
        .map((node) => {
          const badgeNode =
            node.querySelector(".corner-wrap .text") ||
            node.querySelector(".corner-wrap") ||
            node.querySelector(".video-item-left");
          const titleNode =
            node.querySelector(".video-item-right-main") ||
            node.querySelector(".video-item-right") ||
            node;
          return {
            badge: textOf(badgeNode).slice(0, 40),
            title: textOf(titleNode).slice(0, 120),
          };
        })
        .filter((row) => row.badge || row.title)
        .slice(0, 12);

      const ssr = window.__vikor__context__?.ssrPayloads?._piniaState?.union || {};
      const coverMap = ssr.coverInfoMap || {};
      const videoMap = ssr.videoInfoMap || {};
      const cid = ssr.initialCid || Object.keys(coverMap)[0] || "";
      const vid = ssr.initialVid || Object.keys(videoMap)[0] || "";
      const cover = coverMap[cid] || {};
      const video = videoMap[vid] || {};

      return {
        final_url: location.href,
        title: document.title,
        union_snapshot: {
          cid,
          vid,
          cover_positive_trailer: cover.positive_trailer,
          cover_positive_content_id: cover.positive_content_id,
          cover_pay_status: cover.pay_status,
          cover_type: cover.type,
          cover_type_name: cover.type_name,
          video_state: video.state,
        },
        module_titles: moduleTitles,
        tab_nodes: tabNodes,
        intro_titles: pickVisibleTexts(".intro-title, .module-title-container, .module-title", 20),
        visible_keyword_texts: pickVisibleTexts("button, a, span, div", 80).filter((text) =>
          /(正片|预告|片花|花絮|看点|抢先看|纯享|番外|选集|节目单|更多短视频|精彩预告|精彩片花)/.test(text)
        ).slice(0, 40),
        card_samples: cards,
      };
    });
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: data.final_url,
      title: data.title,
      cid: extractCidVid(data.final_url || testCase.url).cid,
      vid: extractCidVid(data.final_url || testCase.url).vid,
      union_snapshot: data.union_snapshot,
      module_titles: data.module_titles,
      tab_nodes: data.tab_nodes,
      intro_titles: data.intro_titles,
      visible_keyword_texts: data.visible_keyword_texts,
      card_samples: data.card_samples,
      module_keyword_counts: collectKeywordCounts(
        data.module_titles.map((text) => ({ text })),
        "text"
      ),
      tab_keyword_counts: collectKeywordCounts(data.tab_nodes, "text"),
      card_badge_keyword_counts: collectKeywordCounts(data.card_samples, "badge"),
      card_title_keyword_counts: collectKeywordCounts(data.card_samples, "title"),
    };
  } finally {
    await page.close();
  }
}

function buildTakeaways(cases) {
  const takeaways = [];
  const pt2 = cases.filter((entry) => entry.union_snapshot?.cover_positive_trailer === 2);
  const pt1 = cases.filter((entry) => entry.union_snapshot?.cover_positive_trailer === 1);
  const pt0 = cases.filter((entry) => entry.union_snapshot?.cover_positive_trailer === 0);

  if (
    pt2.some((entry) => entry.module_titles.includes("精彩预告")) &&
    pt2.some((entry) => (entry.card_badge_keyword_counts["预告"] || 0) > 0)
  ) {
    takeaways.push(
      "positive_trailer=2 representative pages now show a concrete UI-side pattern: the adjacent content module headline becomes `精彩预告`, and the first sampled cards carry explicit `预告` badges."
    );
  }
  if (
    pt1.some((entry) => entry.module_titles.includes("精彩片花")) ||
    pt1.some((entry) => (entry.module_keyword_counts["精彩片花"] || 0) > 0) ||
    pt1.some((entry) => (entry.tab_keyword_counts["精彩片花"] || 0) > 0)
  ) {
    takeaways.push(
      "positive_trailer=1 representative kids page surfaces a `精彩片花` branch instead of a `精彩预告` headline."
    );
  }
  if (
    pt0.some((entry) => entry.module_titles.includes("选集")) &&
    pt0.some((entry) => (entry.card_badge_keyword_counts["SVIP"] || 0) > 0)
  ) {
    takeaways.push(
      "positive_trailer=0 representative variety topic page stays on an `选集` / program-list surface, and the first sampled cards are dominated by `SVIP` pay badges rather than `预告` badges."
    );
  }
  takeaways.push(
    "This remains page-shape-correlated evidence rather than a strict same-layout causal proof: the current probe closes the first visible module/card pattern, not the final backend enum naming."
  );
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const browserPath = await resolveBrowserPath(options.browserPath || "");
  const playwright = await loadPlaywright();
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath,
  });
  const results = [];
  try {
    for (const testCase of cases) {
      try {
        results.push(await inspectCase(browser, testCase, { waitMs, timeoutMs }));
      } catch (error) {
        results.push({
          bucket: testCase.bucket,
          input_url: testCase.url,
          error: String(error),
        });
      }
    }
  } finally {
    await browser.close();
  }
  return {
    generated_at: new Date().toISOString(),
    scope: "detail-page visible module / tab / card-surface probe for positive_trailer frontend semantics",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      cases,
    },
    cases: results,
    takeaways: buildTakeaways(results.filter((entry) => !entry.error)),
  };
}

async function cliMain(argv) {
  const args = parseArgs(argv);
  const report = await runProbe(args);
  const proc = globalThis.process;
  if (proc && proc.stdout) {
    proc.stdout.write(JSON.stringify(report, null, args.indent));
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
