import fs from "node:fs/promises";
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
    bucket: "variety_pay15_topic_shell",
    url: "https://v.qq.com/x/cover/mzc002001u873es.html",
  },
  {
    bucket: "sports_collection_shell",
    url: "https://v.qq.com/x/cover/mzc002003fh665c.html",
  },
  {
    bucket: "kids_free_pack_shell",
    url: "https://v.qq.com/x/cover/mzc00200q00mv2h.html",
  },
];

const SEARCH_TERMS = [
  "upload_src",
  "uploadSrc",
  "\"F\":",
  "\"state\":",
  "positive_trailer",
  "cover_list",
  "c_covers",
  "topic_id_list",
];

const CHAIN_PATTERNS = [
  { tag: "PageService/getPage", matches: ["PageService/getPage"] },
  { tag: "getCoverInfoBatch", matches: ["getCoverInfoBatch"] },
  { tag: "FillUnionInfo", matches: ["FillUnionInfo"] },
  { tag: "coverInfoMap", matches: ["coverInfoMap"] },
  { tag: "videoInfoMap", matches: ["videoInfoMap"] },
  { tag: "commentInfo", matches: ["commentInfo"] },
  { tag: "pc_sv_mixed_feeds", matches: ["pc_sv_mixed_feeds"] },
  { tag: "topic_id_list", matches: ["topic_id_list"] },
  { tag: "cover_list", matches: ["cover_list"] },
  { tag: "c_covers", matches: ["c_covers"] },
  { tag: "normal_ids", matches: ["normal_ids", "nomal_ids"] },
  { tag: "vip_ids", matches: ["vip_ids"] },
];

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 14000,
    timeoutMs: 50000,
    clickWaitMs: 2500,
    scrollStep: 1200,
    scrollLoops: 4,
    indent: 2,
    browserPath: "",
    output: "",
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
    if (token === "--scroll-step") {
      args.scrollStep = Number(argv[++index]);
      continue;
    }
    if (token === "--scroll-loops") {
      args.scrollLoops = Number(argv[++index]);
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
    if (token === "--output") {
      args.output = argv[++index] || "";
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
    await fs.access(explicitPath);
    return explicitPath;
  }
  for (const candidate of DEFAULT_BROWSER_CANDIDATES) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {}
  }
  throw new Error("Could not find a local Chrome/Edge executable.");
}

async function loadPlaywright() {
  const runtimeNodeModules =
    "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
  const playwrightNodeModules = `${runtimeNodeModules}/playwright/node_modules`;
  try {
    const moduleBuiltin = require("node:module");
    const nodePath = globalThis.process?.env?.NODE_PATH
      ? globalThis.process.env.NODE_PATH.split(path.delimiter)
      : [];
    const mergedNodePath = [runtimeNodeModules, playwrightNodeModules, ...nodePath];
    if (
      !nodePath.includes(runtimeNodeModules) ||
      !nodePath.includes(playwrightNodeModules)
    ) {
      globalThis.process.env.NODE_PATH = mergedNodePath
        .filter(Boolean)
        .join(path.delimiter);
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
  await page
    .evaluate(() => {
      for (const selector of [
        ".txv-client-service-popup__container",
        ".txv-client-service-popup__mask",
        ".txv-client-service-popup",
      ]) {
        for (const node of Array.from(document.querySelectorAll(selector))) {
          node.remove();
        }
      }
    })
    .catch(() => {});
}

async function listTabs(page) {
  return page
    .locator(".tab-node, .tab-node-selected, [role='tab']")
    .evaluateAll((nodes) =>
      nodes
        .map((node) => (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim())
        .filter(Boolean)
    )
    .then((rows) => [...new Set(rows)].slice(0, 10))
    .catch(() => []);
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

function classifyChainTags(url, text) {
  const tags = [];
  for (const pattern of CHAIN_PATTERNS) {
    if (pattern.matches.some((token) => url.includes(token) || text.includes(token))) {
      tags.push(pattern.tag);
    }
  }
  return tags;
}

function classifyUrlChainTags(url) {
  return classifyChainTags(url, "");
}

function classifyTextChainTags(text) {
  return classifyChainTags("", text);
}

function parseStructuredPayload(text) {
  const trimmed = text.trim();
  let candidate = trimmed;
  if (candidate.startsWith("QZOutputJson=")) {
    candidate = candidate.slice("QZOutputJson=".length).trim();
    if (candidate.endsWith(";")) {
      candidate = candidate.slice(0, -1);
    }
  }
  if (
    (candidate.startsWith("{") && candidate.endsWith("}")) ||
    (candidate.startsWith("[") && candidate.endsWith("]"))
  ) {
    try {
      return JSON.parse(candidate);
    } catch {}
  }
  return null;
}

function sampleIdsFromText(text, pattern, limit) {
  const results = [];
  const seen = new Set();
  for (const match of text.matchAll(pattern)) {
    const value = String(match[0] || "").trim();
    if (!value || seen.has(value)) {
      continue;
    }
    seen.add(value);
    results.push(value);
    if (results.length >= limit) {
      break;
    }
  }
  return results;
}

function buildResponseShape(text) {
  const parsed = parseStructuredPayload(text);
  const topKeys =
    parsed && typeof parsed === "object" && !Array.isArray(parsed) ? Object.keys(parsed).slice(0, 12) : [];
  return {
    json_top_keys: topKeys,
    contains_coverInfoMap: text.includes("coverInfoMap"),
    contains_videoInfoMap: text.includes("videoInfoMap"),
    contains_commentInfo: text.includes("commentInfo"),
    contains_cover_list: text.includes("cover_list"),
    contains_c_covers: text.includes("c_covers"),
    contains_topic_id_list: text.includes("topic_id_list"),
    contains_normal_ids: text.includes("normal_ids") || text.includes("nomal_ids"),
    contains_vip_ids: text.includes("vip_ids"),
    contains_F: text.includes("\"F\":"),
    contains_upload_src: text.includes("upload_src") || text.includes("uploadSrc"),
    contains_state: text.includes("\"state\":"),
    contains_positive_trailer: text.includes("positive_trailer"),
    contains_targetid: text.includes("targetid"),
    sample_cids: sampleIdsFromText(text, /mzc[0-9a-z]{11}/gi, 5),
    sample_vids: sampleIdsFromText(text, /\b[a-z0-9]{11}\b/gi, 5),
  };
}

function guessPageFamily(inputUrl, finalUrl) {
  const coverOnlyPattern = /\/cover\/[^/]+\.html(?:[?#].*)?$/i;
  const detailPattern = /\/cover\/[^/]+\/[^/]+\.html(?:[?#].*)?$/i;
  if (detailPattern.test(finalUrl)) {
    return "detail";
  }
  if (coverOnlyPattern.test(finalUrl) && finalUrl === inputUrl) {
    return "cover_only";
  }
  if (coverOnlyPattern.test(finalUrl)) {
    return "cover_shell";
  }
  if (finalUrl.includes("/page/")) {
    return "topic";
  }
  return "unknown";
}

function summarizeResponses(responses) {
  const summary = {
    getPage_response_count: 0,
    getCoverInfoBatch_response_count: 0,
    FillUnionInfo_response_count: 0,
    any_response_with_F: false,
    any_response_with_upload_src: false,
    any_response_with_state: false,
    any_response_with_positive_trailer: false,
    getPage_with_F: false,
    getPage_with_upload_src: false,
    getCoverInfoBatch_with_F: false,
    getCoverInfoBatch_with_upload_src: false,
  };
  for (const row of responses) {
    const tags = new Set(row.url_chain_tags || []);
    const terms = new Set(row.matched_terms || []);
    if (tags.has("PageService/getPage")) {
      summary.getPage_response_count += 1;
      if (terms.has("\"F\":")) {
        summary.getPage_with_F = true;
      }
      if (terms.has("upload_src") || terms.has("uploadSrc")) {
        summary.getPage_with_upload_src = true;
      }
    }
    if (tags.has("getCoverInfoBatch")) {
      summary.getCoverInfoBatch_response_count += 1;
      if (terms.has("\"F\":")) {
        summary.getCoverInfoBatch_with_F = true;
      }
      if (terms.has("upload_src") || terms.has("uploadSrc")) {
        summary.getCoverInfoBatch_with_upload_src = true;
      }
    }
    if (tags.has("FillUnionInfo")) {
      summary.FillUnionInfo_response_count += 1;
    }
    if (terms.has("\"F\":")) {
      summary.any_response_with_F = true;
    }
    if (terms.has("upload_src") || terms.has("uploadSrc")) {
      summary.any_response_with_upload_src = true;
    }
    if (terms.has("\"state\":")) {
      summary.any_response_with_state = true;
    }
    if (terms.has("positive_trailer")) {
      summary.any_response_with_positive_trailer = true;
    }
  }
  return summary;
}

async function clickTabs(page, tabs, clickWaitMs) {
  for (const tabText of tabs) {
    const locator = page
      .locator(".tab-node, .tab-node-selected, [role='tab']")
      .filter({ hasText: tabText })
      .first();
    if ((await locator.count()) === 0) {
      continue;
    }
    await clearInterferingPopups(page);
    await locator.click({ force: true }).catch(() => {});
    if (clickWaitMs > 0) {
      await page.waitForTimeout(clickWaitMs);
    }
  }
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
      const postData = req.postData() || "";
      const tags = classifyUrlChainTags(req.url());
      if (!tags.length && !req.url().includes("v.qq.com") && !req.url().includes("video.qq.com")) {
        return;
      }
      const row = {
        phase,
        started_at_ms: nowMs(),
        url: req.url(),
        method: req.method(),
        resource_type: req.resourceType(),
        chain_tags: tags,
        post_data_excerpt: postData.slice(0, 400),
      };
      requestHits.push(row);
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
      if (!text || text.length > 8_000_000) {
        return;
      }
      const matchedTerms = SEARCH_TERMS.filter((term) => text.includes(term));
      const urlChainTags = classifyUrlChainTags(resp.url());
      const textChainTags = classifyTextChainTags(text);
      const chainTags = [...new Set([...urlChainTags, ...textChainTags])];
      if (!matchedTerms.length && !chainTags.length) {
        return;
      }
      const shape = buildResponseShape(text);
      responseHits.push({
        phase,
        seen_at_ms: nowMs(),
        url: resp.url(),
        status: resp.status(),
        resource_type: resp.request().resourceType(),
        content_type: String(resp.headers()["content-type"] || "").toLowerCase(),
        url_chain_tags: urlChainTags,
        text_chain_tags: textChainTags,
        chain_tags: chainTags,
        matched_terms: matchedTerms,
        shape,
        snippets: buildSnippets(
          text,
          chainTags.length ? [...chainTags.slice(0, 2), ...matchedTerms] : matchedTerms
        ),
      });
    } catch {}
  });

  try {
    phase = "navigation";
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }
    phase = "after_popup_clear";
    await clearInterferingPopups(page);
    const tabs = await listTabs(page);
    for (const tabText of tabs) {
      phase = `after_tab_click:${tabText}`;
      await clickTabs(page, [tabText], options.clickWaitMs);
    }
    for (let index = 0; index < options.scrollLoops; index += 1) {
      phase = `after_scroll:${index + 1}`;
      await scrollPage(page, 1, options.scrollStep, options.clickWaitMs);
    }
    await page.waitForTimeout(2500).catch(() => {});

    const sampleTitle = await page.title().catch(() => "");
    const matchingResponses = responseHits.slice(0, 60);
    const matchingRequests = requestHits.slice(0, 80);
    const finalUrl = page.url();
    const finalPageFamilyGuess = guessPageFamily(testCase.url, finalUrl);
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: finalUrl,
      redirected_to_detail:
        finalUrl !== testCase.url && finalPageFamilyGuess === "detail",
      final_page_family_guess: finalPageFamilyGuess,
      title: sampleTitle,
      tabs_seen: tabs,
      response_summary: summarizeResponses(matchingResponses),
      matching_requests: matchingRequests,
      matching_responses: matchingResponses,
    };
  } finally {
    await page.close();
  }
}

export async function runProbe(options = {}) {
  const cases =
    Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 14000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 50000;
  const clickWaitMs = Number.isFinite(options.clickWaitMs) ? options.clickWaitMs : 2500;
  const scrollStep = Number.isFinite(options.scrollStep) ? options.scrollStep : 1200;
  const scrollLoops = Number.isFinite(options.scrollLoops) ? options.scrollLoops : 4;
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
        results.push(
          await inspectCase(browser, testCase, {
            waitMs,
            timeoutMs,
            clickWaitMs,
            scrollStep,
            scrollLoops,
          })
        );
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
    scope: "non-detail frontend chain probe for getPage/getCoverInfoBatch and F/upload_src evidence",
      method: {
        browser: "system Chrome via Playwright",
        browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      click_wait_ms_after_tab_switch: clickWaitMs,
      scroll_step: scrollStep,
        scroll_loops: scrollLoops,
        cases,
        search_terms: SEARCH_TERMS,
        chain_patterns: CHAIN_PATTERNS.map((row) => row.tag),
      },
      cases: results,
    };
}

async function cliMain(argv) {
  const args = parseArgs(argv);
  const report = await runProbe(args);
  const rendered = JSON.stringify(report, null, args.indent);
  if (args.output) {
    const outputPath = path.resolve(args.output);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, `${rendered}\n`, "utf8");
    return;
  }
  const proc = globalThis.process;
  if (proc && proc.stdout) {
    proc.stdout.write(rendered);
  }
}

const proc = globalThis.process;
const argv = proc && Array.isArray(proc.argv) ? proc.argv.slice(2) : [];
if (proc && argv[0] === "--cli") {
  cliMain(argv.slice(1)).catch((error) => {
    const message = JSON.stringify(
      {
        error: String(error),
        stack:
          error && typeof error.stack === "string"
            ? error.stack.split("\n").slice(0, 8)
            : [],
      },
      null,
      2
    );
    proc.stderr.write(message);
    proc.exitCode = 1;
  });
}
