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
    bucket: "tv_season_f_mixed",
    url: "https://v.qq.com/x/cover/mzc00200whxf2zp.html",
  },
  {
    bucket: "variety_topic_uploadsrc_mixed",
    url: "https://v.qq.com/x/cover/mzc00200iy331ds.html",
  },
];

const KEYWORDS = ["选集", "预告", "片花", "花絮", "看点", "正片", "纯享", "更多短视频"];

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 12000,
    timeoutMs: 45000,
    clickWaitMs: 1500,
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
    if (token === "--click-wait-ms") {
      args.clickWaitMs = Number(argv[++index]);
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
    const nodePath = globalThis.process?.env?.NODE_PATH ? globalThis.process.env.NODE_PATH.split(path.delimiter) : [];
    if (!nodePath.includes(runtimeNodeModules)) {
      globalThis.process.env.NODE_PATH = [runtimeNodeModules, ...nodePath].filter(Boolean).join(path.delimiter);
      if (typeof moduleBuiltin.Module?._initPaths === "function") {
        moduleBuiltin.Module._initPaths();
      }
    }
  } catch {}
  const requireCandidates = [
    `${runtimeNodeModules}/playwright`,
    `${runtimeNodeModules}/playwright/index.js`,
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

function parseVidFromHref(href) {
  const match = /\/cover\/[^/]+\/([^/.?#]+)\.html/.exec(href || "");
  return match?.[1] || "";
}

function countValues(items, key) {
  const counts = {};
  for (const item of items || []) {
    const text = String(item?.[key] || "");
    if (!text) {
      continue;
    }
    counts[text] = (counts[text] || 0) + 1;
  }
  return counts;
}

function summarizeKeywordCounts(items, keys) {
  const counts = {};
  for (const item of items || []) {
    for (const key of keys) {
      const text = String(item?.[key] || "");
      for (const keyword of KEYWORDS) {
        if (text.includes(keyword)) {
          counts[keyword] = (counts[keyword] || 0) + 1;
        }
      }
    }
  }
  return counts;
}

async function collectSnapshot(page, label) {
  return page.evaluate((snapshotLabel) => {
    const visible = (node) => {
      if (!node) {
        return false;
      }
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    };

    const textOf = (node) => (node?.innerText || node?.textContent || "").replace(/\s+/g, " ").trim();

    const parseJsonArray = (value) => {
      if (typeof value !== "string" || !value.trim()) {
        return [];
      }
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    };

    const ssr = window.__vikor__context__?.ssrPayloads || {};
    const pinia = ssr._piniaState || {};
    const union = pinia.union || {};
    const coverMap = union.coverInfoMap || {};
    const videoMap = union.videoInfoMap || {};
    const cid = union.initialCid || Object.keys(coverMap)[0] || "";
    const vid = union.initialVid || Object.keys(videoMap)[0] || "";
    const cover = coverMap[cid] || {};
    const video = videoMap[vid] || {};
    const roots = {
      pinia,
      asyncData: ssr._async_data,
      ctx: window.__vikor__context__,
    };

    const coverShellHits = [];
    const seenCoverNodes = new WeakSet();
    const currentCid = String(cid || "");
    const collectCoverShells = (node, path, depth = 0) => {
      if (!node || typeof node !== "object" || seenCoverNodes.has(node) || depth > 8 || coverShellHits.length >= 60) {
        return;
      }
      seenCoverNodes.add(node);
      if (Array.isArray(node)) {
        node.slice(0, 200).forEach((item, index) => collectCoverShells(item, `${path}[${index}]`, depth + 1));
        return;
      }
      const candidateCid = String(node.cover_id || node.cid || node.id || "");
      const nomalIds = parseJsonArray(node.nomal_ids);
      const vipIds = parseJsonArray(node.vip_ids);
      if (
        nomalIds.length ||
        vipIds.length ||
        (currentCid && candidateCid && candidateCid === currentCid)
      ) {
        coverShellHits.push({
          path,
          candidate_cid: candidateCid,
          title: String(node.title || ""),
          type: node.type,
          type_name: node.type_name,
          pay_status: node.pay_status,
          positive_trailer: node.positive_trailer,
          nomal_ids_count: nomalIds.length,
          vip_ids_count: vipIds.length,
          nomal_ids: nomalIds.slice(0, 80).map((row) => ({ F: row?.F, V: row?.V })),
          vip_ids: vipIds.slice(0, 80).map((row) => ({ F: row?.F, V: row?.V })),
        });
      }
      for (const [key, value] of Object.entries(node).slice(0, 400)) {
        collectCoverShells(value, `${path}.${key}`, depth + 1);
      }
    };
    collectCoverShells(roots, "roots", 0);

    const bestCoverShell =
      coverShellHits
        .slice()
        .sort(
          (left, right) =>
            (right.nomal_ids_count + right.vip_ids_count) - (left.nomal_ids_count + left.vip_ids_count)
        )[0] || null;

    const nomalIds = bestCoverShell?.nomal_ids?.length ? bestCoverShell.nomal_ids : parseJsonArray(cover.nomal_ids);
    const vipIds = bestCoverShell?.vip_ids?.length ? bestCoverShell.vip_ids : parseJsonArray(cover.vip_ids);

    const tabNodes = Array.from(document.querySelectorAll(".tab-node, .tab-node-selected, [role='tab']"))
      .filter((node) => visible(node))
      .map((node) => ({
        text: textOf(node),
        className: String(node.className || "").slice(0, 160),
        selected:
          String(node.className || "").includes("selected") ||
          node.getAttribute("aria-selected") === "true",
      }))
      .filter((row) => row.text)
      .slice(0, 20);

    const moduleTitles = Array.from(document.querySelectorAll(".module-title, .module-title-container, .intro-title"))
      .filter((node) => visible(node))
      .map((node) => textOf(node))
      .filter(Boolean)
      .slice(0, 20);

    const cardRows = [];
    const seenCardKey = new Set();
    const candidateNodes = Array.from(
      document.querySelectorAll(
        ".video-item, .video-item-wrapper, .card-wrap, .feed-card, [class*='video-item'], [class*='card']"
      )
    );
    for (const node of candidateNodes) {
      if (!visible(node)) {
        continue;
      }
      const anchor = node.matches("a[href*='/cover/']") ? node : node.querySelector("a[href*='/cover/']");
      const href = String(anchor?.href || "");
      const text = textOf(anchor) || textOf(node);
      if (!text || text.length > 200) {
        continue;
      }
      const badges = Array.from(
        node.querySelectorAll(
          ".corner-wrap, .video-item-left, .tag, .badge, [class*='badge'], [class*='tag'], [class*='mark']"
        )
      )
        .map((node) => textOf(node))
        .filter(Boolean)
        .slice(0, 6);
      const cardKey = `${href}|${text.slice(0, 80)}`;
      if (seenCardKey.has(cardKey)) {
        continue;
      }
      seenCardKey.add(cardKey);
      cardRows.push({
        href,
        text: text.slice(0, 160),
        badges,
      });
      if (cardRows.length >= 20) {
        break;
      }
    }

    return {
      snapshot_label: snapshotLabel,
      final_url: location.href,
      title: document.title,
      union_snapshot: {
        cid,
        vid,
        cover_type: cover.type,
        cover_type_name: cover.type_name,
        cover_pay_status: cover.pay_status,
        cover_positive_trailer: cover.positive_trailer,
        cover_positive_content_id: cover.positive_content_id,
        cover_nomal_ids_count: nomalIds.length,
        cover_vip_ids_count: vipIds.length,
        video_state: video.state,
        video_upload_src: video.upload_src ?? video.uploadSrc,
        video_F: video.F,
      },
      nomal_ids: nomalIds.map((row) => ({
        F: row?.F,
        V: row?.V,
      })),
      vip_ids: vipIds.map((row) => ({
        F: row?.F,
        V: row?.V,
      })),
      cover_shell_hits: coverShellHits.slice(0, 12),
      tab_nodes: tabNodes,
      module_titles: moduleTitles,
      card_samples: cardRows,
      roots,
    };
  }, label);
}

function annotateSnapshot(rawSnapshot) {
  const nomalMap = new Map();
  const vipMap = new Map();
  for (const row of rawSnapshot.nomal_ids || []) {
    if (row && row.V) {
      nomalMap.set(String(row.V), String(row.F));
    }
  }
  for (const row of rawSnapshot.vip_ids || []) {
    if (row && row.V) {
      vipMap.set(String(row.V), String(row.F));
    }
  }

  const targetVids = new Set();
  const cards = (rawSnapshot.card_samples || []).map((row) => {
    const vid = parseVidFromHref(row.href || "");
    if (vid) {
      targetVids.add(vid);
    }
    return {
      ...row,
      vid,
      nomal_F: vid ? nomalMap.get(vid) || "" : "",
      vip_F: vid ? vipMap.get(vid) || "" : "",
    };
  });

  const relevantKeys = [
    "vid",
    "id",
    "V",
    "video_id",
    "upload_src",
    "uploadSrc",
    "state",
    "F",
    "pay_status",
    "positive_trailer",
    "positive_content_id",
    "category_map",
    "title",
  ];

  const hits = [];
  const seenObjects = new WeakSet();
  const targets = targetVids;

  function pickFields(obj) {
    const picked = {};
    for (const key of relevantKeys) {
      if (obj[key] !== undefined) {
        picked[key] = obj[key];
      }
    }
    return picked;
  }

  function walk(node, path, depth = 0) {
    if (!node || typeof node !== "object" || seenObjects.has(node) || depth > 8 || hits.length >= 160) {
      return;
    }
    seenObjects.add(node);
    if (Array.isArray(node)) {
      node.slice(0, 200).forEach((item, index) => walk(item, `${path}[${index}]`, depth + 1));
      return;
    }
    const directMatch = [node.vid, node.id, node.V, node.video_id].find((value) => targets.has(String(value || "")));
    if (directMatch) {
      hits.push({
        path,
        matched_vid: String(directMatch),
        fields: pickFields(node),
      });
    }
    const entries = Object.entries(node).slice(0, 400);
    for (const [key, value] of entries) {
      if (targets.has(String(key)) && value && typeof value === "object" && !Array.isArray(value)) {
        hits.push({
          path: `${path}.${key}`,
          matched_vid: String(key),
          fields: pickFields(value),
        });
      }
      walk(value, `${path}.${key}`, depth + 1);
    }
  }

  walk(rawSnapshot.roots, "roots", 0);

  const hitsByVid = {};
  for (const hit of hits) {
    const vid = hit.matched_vid;
    hitsByVid[vid] = hitsByVid[vid] || [];
    if (hitsByVid[vid].length < 6) {
      hitsByVid[vid].push(hit);
    }
  }

  const annotatedCards = cards.map((row) => ({
    ...row,
    frontend_hits: row.vid ? hitsByVid[row.vid] || [] : [],
  }));

  return {
    snapshot_label: rawSnapshot.snapshot_label,
    final_url: rawSnapshot.final_url,
    title: rawSnapshot.title,
    union_snapshot: rawSnapshot.union_snapshot,
    cover_shell_hits: rawSnapshot.cover_shell_hits,
    tab_nodes: rawSnapshot.tab_nodes,
    module_titles: rawSnapshot.module_titles,
    card_samples: annotatedCards,
    nomal_f_counts: countValues(rawSnapshot.nomal_ids, "F"),
    vip_f_counts: countValues(rawSnapshot.vip_ids, "F"),
    visible_nomal_f_counts: countValues(annotatedCards.filter((row) => row.nomal_F), "nomal_F"),
    visible_vip_f_counts: countValues(annotatedCards.filter((row) => row.vip_F), "vip_F"),
    frontend_upload_src_counts: countValues(
      annotatedCards.flatMap((row) => row.frontend_hits || []).map((hit) => ({
        upload_src: hit?.fields?.upload_src ?? hit?.fields?.uploadSrc,
      })),
      "upload_src"
    ),
    frontend_state_counts: countValues(
      annotatedCards.flatMap((row) => row.frontend_hits || []).map((hit) => ({
        state: hit?.fields?.state,
      })),
      "state"
    ),
    keyword_counts: {
      modules: summarizeKeywordCounts(rawSnapshot.module_titles.map((text) => ({ text })), ["text"]),
      tabs: summarizeKeywordCounts(rawSnapshot.tab_nodes, ["text"]),
      cards: summarizeKeywordCounts(annotatedCards, ["text", "badges"]),
    },
  };
}

async function clearInterferingPopups(page) {
  await page.evaluate(() => {
    for (const selector of [
      ".txv-client-service-popup__container",
      ".txv-client-service-popup__mask",
      ".txv-client-service-popup",
    ]) {
      for (const node of Array.from(document.querySelectorAll(selector))) {
        node.remove();
      }
    }
  }).catch(() => {});
}

function buildTabPlan(snapshot) {
  const candidates = [];
  const seen = new Set();
  for (const node of snapshot.tab_nodes || []) {
    const text = String(node.text || "").replace(/\s+/g, " ").trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    if (KEYWORDS.some((keyword) => text.includes(keyword))) {
      candidates.push(text);
    }
  }
  return candidates.slice(0, 8);
}

async function clickTabAndSnapshot(page, tabText, clickWaitMs) {
  await clearInterferingPopups(page);
  const locator = page
    .locator(".tab-node, .tab-node-selected, [role='tab']")
    .filter({ hasText: tabText })
    .first();
  if ((await locator.count()) === 0) {
    throw new Error(`tab not found: ${tabText}`);
  }
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  await locator.click({ timeout: 6000, force: true });
  if (clickWaitMs > 0) {
    await page.waitForTimeout(clickWaitMs);
  }
  await clearInterferingPopups(page);
  return collectSnapshot(page, `tab:${tabText}`);
}

function buildCaseTakeaways(caseReport) {
  const takeaways = [];
  const initial = caseReport.initial_snapshot || {};
  if (Object.keys(initial.nomal_f_counts || {}).length) {
    takeaways.push(
      `${caseReport.bucket}: cover-level nomal_ids already split into F buckets ${JSON.stringify(initial.nomal_f_counts)}.`
    );
  }
  for (const tabRun of caseReport.tab_runs || []) {
    const visibleF = tabRun.snapshot?.visible_nomal_f_counts || {};
    const uploadCounts = tabRun.snapshot?.frontend_upload_src_counts || {};
    if (Object.keys(visibleF).length) {
      takeaways.push(`${caseReport.bucket} / ${tabRun.tab_text}: visible cards map back to nomal F buckets ${JSON.stringify(visibleF)}.`);
    }
    if (Object.keys(uploadCounts).length) {
      takeaways.push(
        `${caseReport.bucket} / ${tabRun.tab_text}: frontend-side row objects expose upload_src counts ${JSON.stringify(uploadCounts)}.`
      );
    }
  }
  return takeaways;
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
    await clearInterferingPopups(page);
    await page.mouse.wheel(0, 1200).catch(() => {});
    await page.waitForTimeout(800).catch(() => {});
    await clearInterferingPopups(page);
    const initialRaw = await collectSnapshot(page, "initial");
    const initialSnapshot = annotateSnapshot(initialRaw);
    const tabPlan = buildTabPlan(initialSnapshot);
    const tabRuns = [];
    for (const tabText of tabPlan) {
      try {
        const raw = await clickTabAndSnapshot(page, tabText, options.clickWaitMs);
        tabRuns.push({
          tab_text: tabText,
          snapshot: annotateSnapshot(raw),
        });
      } catch (error) {
        tabRuns.push({
          tab_text: tabText,
          error: String(error),
        });
      }
    }
    const finalUrl = initialSnapshot.final_url || testCase.url;
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: finalUrl,
      cid: extractCidVid(finalUrl).cid,
      vid: extractCidVid(finalUrl).vid,
      title: initialSnapshot.title,
      initial_snapshot: initialSnapshot,
      tab_plan: tabPlan,
      tab_runs: tabRuns,
      takeaways: buildCaseTakeaways({
        bucket: testCase.bucket,
        initial_snapshot: initialSnapshot,
        tab_runs: tabRuns,
      }),
    };
  } finally {
    await page.close();
  }
}

function buildTakeaways(results) {
  const takeaways = [];
  for (const result of results) {
    for (const line of result.takeaways || []) {
      if (!takeaways.includes(line)) {
        takeaways.push(line);
      }
    }
  }
  if (
    results.some((entry) => Object.keys(entry.initial_snapshot?.nomal_f_counts || {}).length > 1) &&
    results.some((entry) => entry.tab_runs?.some((run) => Object.keys(run.snapshot?.visible_nomal_f_counts || {}).length > 0))
  ) {
    takeaways.push(
      "Current evidence favors a row-shell / tab-surface explanation for `F`: mixed F codes already exist in cover-level nomal_ids, and visible tab/card rows can map back to those F buckets without the field surfacing in the main union hero row."
    );
  }
  if (
    results.some((entry) => entry.tab_runs?.some((run) => Object.keys(run.snapshot?.frontend_upload_src_counts || {}).length > 0))
  ) {
    takeaways.push(
      "Current evidence also suggests `upload_src` is more likely to survive in row-level / lazy-loaded frontend objects than in the first exposed union hero row, especially on mixed aggregation pages."
    );
  }
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const clickWaitMs = Number.isFinite(options.clickWaitMs) ? options.clickWaitMs : 1500;
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
        results.push(await inspectCase(browser, testCase, { waitMs, timeoutMs, clickWaitMs }));
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
    scope: "detail/page row-shell probe for F/upload_src frontend semantics",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      click_wait_ms_after_tab_switch: clickWaitMs,
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
