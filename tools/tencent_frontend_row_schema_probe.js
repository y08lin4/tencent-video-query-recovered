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

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 15000,
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

function normalizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function buildFieldPresence(item) {
  return {
    has_vid: item.vid !== undefined,
    has_title_new: item.title_new !== undefined,
    has_c_title_detail: item.c_title_detail !== undefined,
    has_positive_trailer: item.positive_trailer !== undefined,
    has_targetid: item.targetid !== undefined || item.targetId !== undefined,
    has_state: item.state !== undefined,
    has_upload_src: item.upload_src !== undefined || item.uploadSrc !== undefined,
    has_F: item.F !== undefined,
  };
}

function extractFieldValues(item) {
  return {
    vid: item.vid,
    title_new: item.title_new,
    c_title_detail: item.c_title_detail,
    positive_trailer: item.positive_trailer,
    targetid: item.targetId !== undefined ? item.targetId : item.targetid,
    state: item.state,
    upload_src: item.uploadSrc !== undefined ? item.uploadSrc : item.upload_src,
    F: item.F,
    type: item.type,
  };
}

async function collectVisibleCardTexts(page) {
  return page.evaluate(() => {
    const visible = (node) => {
      if (!node) {
        return false;
      }
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    };
    const textOf = (node) => (node?.innerText || node?.textContent || "").replace(/\s+/g, " ").trim();
    const candidates = [];
    for (const node of Array.from(
      document.querySelectorAll(".video-item, .video-item-wrapper, .card-wrap, .feed-card, [class*='video-item'], [class*='card']")
    )) {
      if (!visible(node)) {
        continue;
      }
      const text = textOf(node);
      if (!text) {
        continue;
      }
      candidates.push(text.slice(0, 220));
      if (candidates.length >= 30) {
        break;
      }
    }
    return candidates;
  });
}

function extractResponseRows(payload, visibleCardTexts) {
  const normalizedVisible = visibleCardTexts.map((text) => normalizeText(text)).filter(Boolean);
  const hits = [];
  const seen = new WeakSet();
  const signatures = new Set();

  const matchesVisibleText = (candidate) => {
    const text = normalizeText(candidate);
    if (!text) {
      return [];
    }
    const matched = [];
    for (const visibleText of normalizedVisible) {
      if (
        visibleText.includes(text) ||
        text.includes(visibleText) ||
        (text.length >= 6 && visibleText.includes(text.slice(0, Math.min(text.length, 20)))) ||
        (visibleText.length >= 6 && text.includes(visibleText.slice(0, Math.min(visibleText.length, 20))))
      ) {
        matched.push(visibleText);
      }
      if (matched.length >= 4) {
        break;
      }
    }
    return matched;
  };

  const walk = (node, path, depth = 0) => {
    if (!node || typeof node !== "object" || seen.has(node) || depth > 10 || hits.length >= 120) {
      return;
    }
    seen.add(node);
    if (Array.isArray(node)) {
      node.slice(0, 400).forEach((item, index) => walk(item, `${path}[${index}]`, depth + 1));
      return;
    }
    const titleCandidates = [node.title_new, node.c_title_detail, node.title, node.name];
    const matchedVisible = titleCandidates.flatMap(matchesVisibleText);
    if (matchedVisible.length) {
      const signature = JSON.stringify([
        path,
        node.vid || "",
        normalizeText(node.title_new || node.c_title_detail || node.title || node.name || ""),
      ]);
      if (!signatures.has(signature)) {
        signatures.add(signature);
        hits.push({
          path,
          matched_visible_texts: [...new Set(matchedVisible)].slice(0, 4),
          field_presence: buildFieldPresence(node),
          field_values: extractFieldValues(node),
        });
      }
    }
    for (const [key, value] of Object.entries(node).slice(0, 400)) {
      walk(value, `${path}.${key}`, depth + 1);
    }
  };

  walk(payload, "payload", 0);
  return hits;
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const pageResponses = [];
  page.on("response", async (resp) => {
    if (!/PageService\/getPage/.test(resp.url())) {
      return;
    }
    try {
      const text = await resp.text();
      pageResponses.push({
        url: resp.url(),
        payload: JSON.parse(text),
      });
    } catch {}
  });
  try {
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }
    await clearInterferingPopups(page);
    const visibleCardTexts = await collectVisibleCardTexts(page);
    const responseHits = [];
    for (const entry of pageResponses) {
      const matchedRows = extractResponseRows(entry.payload, visibleCardTexts);
      if (matchedRows.length) {
        responseHits.push({
          url: entry.url,
          matched_rows: matchedRows.slice(0, 40),
        });
      }
    }

    const presenceUnion = {
      has_positive_trailer: false,
      has_targetid: false,
      has_state: false,
      has_upload_src: false,
      has_F: false,
    };
    for (const responseHit of responseHits) {
      for (const row of responseHit.matched_rows || []) {
        for (const key of Object.keys(presenceUnion)) {
          presenceUnion[key] = presenceUnion[key] || !!row.field_presence?.[key];
        }
      }
    }

    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: page.url(),
      visible_card_texts: visibleCardTexts.slice(0, 16),
      matched_response_count: responseHits.length,
      response_hits: responseHits.slice(0, 12),
      matched_row_field_presence_union: presenceUnion,
    };
  } finally {
    await page.close();
  }
}

function buildTakeaways(cases) {
  const takeaways = [];
  for (const entry of cases) {
    const presence = entry.matched_row_field_presence_union || {};
    takeaways.push(
      `${entry.bucket}: matched visible card rows in getPage responses with presence union ${JSON.stringify(presence)}.`
    );
  }
  if (
    cases.length &&
    cases.every(
      (entry) =>
        entry.matched_row_field_presence_union &&
        !entry.matched_row_field_presence_union.has_upload_src &&
        !entry.matched_row_field_presence_union.has_F
    )
  ) {
    takeaways.push(
      "Across the current representative detail pages, the matched getPage row schema for visible cards still omitted both `upload_src` and `F`."
    );
  }
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 15000;
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
    scope: "vector-layout getPage row schema probe for visible detail-page cards",
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
