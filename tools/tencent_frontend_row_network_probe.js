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

const SEARCH_TERMS = [
  "upload_src",
  "uploadSrc",
  "nomal_ids",
  "normal_ids",
  "vip_ids",
  "\"F\":",
  "\"state\":",
  "positive_trailer",
];

const CHAIN_URL_TERMS = ["getCoverInfoBatch", "PageService/getPage", "FillUnionInfo"];

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 12000,
    timeoutMs: 45000,
    clickWaitMs: 2500,
    scrollLoops: 3,
    scrollStep: 900,
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
    if (token === "--scroll-loops") {
      args.scrollLoops = Number(argv[++index]);
      continue;
    }
    if (token === "--scroll-step") {
      args.scrollStep = Number(argv[++index]);
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

async function listTabs(page) {
  return page
    .locator(".tab-node, .tab-node-selected, [role='tab']")
    .evaluateAll((nodes) =>
      nodes
        .map((node) => (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim())
        .filter(Boolean)
    )
    .then((rows) => [...new Set(rows)].slice(0, 8))
    .catch(() => []);
}

function buildTabPlan(tabTexts) {
  const priority = [];
  const rest = [];
  const seen = new Set();
  for (const rawText of tabTexts || []) {
    const text = String(rawText || "").replace(/\s+/g, " ").trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    if (KEYWORDS.some((keyword) => text.includes(keyword))) {
      priority.push(text);
    } else {
      rest.push(text);
    }
  }
  return [...priority, ...rest].slice(0, 8);
}

function shouldReadResponse(resp) {
  const resourceType = resp.request().resourceType();
  const contentType = String(resp.headers()["content-type"] || "").toLowerCase();
  return (
    ["xhr", "fetch", "document", "script"].includes(resourceType) ||
    contentType.includes("json") ||
    contentType.includes("javascript") ||
    contentType.includes("html")
  );
}

function buildSnippets(text, terms) {
  return terms.slice(0, 4).map((term) => {
    const index = text.indexOf(term);
    return {
      term,
      snippet: text
        .slice(Math.max(0, index - 120), Math.min(text.length, index + 260))
        .replace(/\s+/g, " "),
    };
  });
}

async function scrollPage(page, loops, step, clickWaitMs) {
  for (let index = 0; index < loops; index += 1) {
    await page.evaluate((scrollStep) => {
      window.scrollBy(0, scrollStep);
    }, step);
    await page.waitForTimeout(clickWaitMs).catch(() => {});
  }
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const responseHits = [];
  const requestHits = [];
  const requestIndexes = new Map();
  const startedAt = Date.now();
  let phase = "before_navigation";
  const nowMs = () => Date.now() - startedAt;
  page.on("request", async (req) => {
    try {
      const url = req.url();
      const urlHit = CHAIN_URL_TERMS.some((term) => url.includes(term));
      if (!urlHit) {
        return;
      }
      const postData = req.postData() || "";
      requestHits.push({
        phase,
        started_at_ms: nowMs(),
        url,
        method: req.method(),
        resource_type: req.resourceType(),
        post_data_excerpt: postData.slice(0, 500),
      });
      requestIndexes.set(req, requestHits.length - 1);
    } catch {}
  });
  page.on("requestfinished", async (req) => {
    try {
      const index = requestIndexes.get(req);
      if (index === undefined) {
        return;
      }
      const resp = await req.response();
      requestHits[index].finished_at_ms = nowMs();
      requestHits[index].response_status = resp ? resp.status() : null;
    } catch {}
  });
  page.on("response", async (resp) => {
    try {
      if (!shouldReadResponse(resp)) {
        return;
      }
      const text = await resp.text().catch(() => "");
      if (!text || text.length > 2_000_000) {
        return;
      }
      const url = resp.url();
      const urlHit = CHAIN_URL_TERMS.some((term) => url.includes(term));
      const matchedTerms = SEARCH_TERMS.filter((term) => text.includes(term));
      if (!urlHit && !matchedTerms.length) {
        return;
      }
      responseHits.push({
        phase,
        url,
        status: resp.status(),
        resource_type: resp.request().resourceType(),
        content_type: String(resp.headers()["content-type"] || "").toLowerCase(),
        url_hit: urlHit,
        matched_terms: matchedTerms,
        snippets: buildSnippets(text, matchedTerms),
        body_excerpt: urlHit ? text.slice(0, 600).replace(/\s+/g, " ") : "",
      });
    } catch {}
  });
  try {
    phase = "initial_navigation";
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      phase = "after_domcontentloaded_wait";
      await page.waitForTimeout(options.waitMs);
    }
    await clearInterferingPopups(page);
    const tabs = buildTabPlan(await listTabs(page));
    for (const tabText of tabs) {
      const locator = page.locator(".tab-node, .tab-node-selected, [role='tab']").filter({ hasText: tabText }).first();
      if ((await locator.count()) === 0) {
        continue;
      }
      await clearInterferingPopups(page);
      phase = `tab_click:${tabText}`;
      await locator.click({ force: true }).catch(() => {});
      if (options.clickWaitMs > 0) {
        await page.waitForTimeout(options.clickWaitMs);
      }
      phase = `tab_scroll:${tabText}`;
      await scrollPage(page, options.scrollLoops, options.scrollStep, options.clickWaitMs);
    }
    phase = "post_tab_wait";
    await page.waitForTimeout(3000).catch(() => {});
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: page.url(),
      tabs_seen: tabs,
      matching_requests: requestHits.slice(0, 80),
      matching_responses: responseHits.slice(0, 40),
    };
  } finally {
    await page.close();
  }
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const clickWaitMs = Number.isFinite(options.clickWaitMs) ? options.clickWaitMs : 2500;
  const scrollLoops = Number.isFinite(options.scrollLoops) ? options.scrollLoops : 3;
  const scrollStep = Number.isFinite(options.scrollStep) ? options.scrollStep : 900;
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
        results.push(await inspectCase(browser, testCase, { waitMs, timeoutMs, clickWaitMs, scrollLoops, scrollStep }));
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
    scope: "detail/page row-shell followup network probe for F/upload_src frontend semantics",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      click_wait_ms_after_tab_switch: clickWaitMs,
      scroll_loops_after_tab_switch: scrollLoops,
      scroll_step_after_tab_switch: scrollStep,
      cases,
      search_terms: SEARCH_TERMS,
      chain_url_terms: CHAIN_URL_TERMS,
      tab_keywords: KEYWORDS,
    },
    cases: results,
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
