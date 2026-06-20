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
    bucket: "kids_dualfull_targetid",
    url: "https://v.qq.com/x/cover/jynqzy9n3wfrsfp/l0020z7maus.html",
  },
  {
    bucket: "tv_season_second",
    url: "https://v.qq.com/x/cover/mzc00200dfbfsrw.html",
  },
  {
    bucket: "tv_season_qyn2",
    url: "https://v.qq.com/x/cover/mzc002002kqssyu/q4100dpkd26.html",
  },
  {
    bucket: "sports_collection_shell",
    url: "https://v.qq.com/x/cover/mzc002003fh665c.html",
  },
  {
    bucket: "show_perspective_pay15",
    url: "https://v.qq.com/x/cover/mzc0020081c19hy.html",
  },
  {
    bucket: "topic_page_second",
    url: "https://v.qq.com/x/cover/mzc00200apbfiqs.html",
  },
];

const INIT_SCAN_SCRIPT = `
(() => {
  const MAX_HITS = 96;
  const MAX_DEPTH = 6;
  const MAX_CHILDREN = 20;
  const seen = new WeakSet();

  const state = {
    hits: [],
    key_nodes: [],
    errors: [],
  };

  const scalar = (value) => {
    if (value === null || value === undefined) {
      return value;
    }
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return value;
    }
    if (Array.isArray(value)) {
      return { type: "array", length: value.length, head: value.slice(0, 4) };
    }
    return { type: "object", keys: Object.keys(value).slice(0, 10) };
  };

  const recordKeyNode = (value, path) => {
    if (!value || typeof value !== "object" || state.key_nodes.length >= MAX_HITS) {
      return;
    }
    const summary = {};
    for (const key of ["targetid", "targetId", "commentid", "commentId", "pg_dokiid", "dokiId"]) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        summary[key] = scalar(value[key]);
      }
    }
    const summaryKeys = Object.keys(summary);
    if (!summaryKeys.length) {
      return;
    }
    const signature = JSON.stringify({ path, summary });
    if (state.key_nodes.some((entry) => JSON.stringify(entry) === signature)) {
      return;
    }
    state.key_nodes.push({
      path,
      keys: summaryKeys,
      summary,
    });
  };

  const recordCommentInfo = (owner, path) => {
    if (!owner || typeof owner !== "object" || !owner.commentInfo || typeof owner.commentInfo !== "object") {
      return;
    }
    const commentInfo = owner.commentInfo;
    const row = {
      path,
      owner_keys: Object.keys(owner).slice(0, 12),
      commentInfo_keys_head: Object.keys(commentInfo).slice(0, 12),
      targetid_raw: commentInfo.targetid ?? commentInfo.targetId ?? null,
      commentid_raw: commentInfo.commentid ?? commentInfo.commentId ?? null,
    };
    const signature = JSON.stringify(row);
    if (state.hits.some((entry) => JSON.stringify(entry) === signature)) {
      return;
    }
    if (state.hits.length < MAX_HITS) {
      state.hits.push(row);
    }
  };

  const walk = (value, path, depth) => {
    if (!value || typeof value !== "object" || seen.has(value) || depth > MAX_DEPTH) {
      return;
    }
    seen.add(value);
    if (Object.prototype.hasOwnProperty.call(value, "commentInfo")) {
      recordCommentInfo(value, path || "root");
    }
    recordKeyNode(value, path || "root");
    const keys = Object.keys(value).slice(0, MAX_CHILDREN);
    for (const key of keys) {
      let nextValue;
      try {
        nextValue = value[key];
      } catch {
        continue;
      }
      walk(nextValue, path ? path + "." + key : key, depth + 1);
    }
  };

  const originalParse = JSON.parse.bind(JSON);
  JSON.parse = function patchedParse(...args) {
    const result = originalParse(...args);
    try {
      walk(result, "root", 0);
    } catch (error) {
      if (state.errors.length < 12) {
        state.errors.push(String(error));
      }
    }
    return result;
  };

  window.__TV_COMMENTINFO_SCAN__ = state;
})();
`;

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
  if (!Number.isFinite(args.waitMs) || args.waitMs < 0) {
    throw new Error("--wait-ms must be a non-negative number.");
  }
  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs <= 0) {
    throw new Error("--timeout-ms must be greater than 0.");
  }
  if (!Number.isFinite(args.indent) || args.indent < 0) {
    throw new Error("--indent must be a non-negative number.");
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

function decodeNumericBase64(value) {
  if (typeof value !== "string" || !value || !/^[A-Za-z0-9+/=]+$/.test(value) || value.length % 4 !== 0) {
    return null;
  }
  try {
    const decoded = Buffer.from(value, "base64").toString("utf8");
    return /^\d{6,}$/.test(decoded) ? decoded : null;
  } catch {
    return null;
  }
}

function decodeMaybeNumeric(value) {
  if (typeof value !== "string" || !value) {
    return null;
  }
  if (/^\d{6,}$/.test(value)) {
    return value;
  }
  return decodeNumericBase64(value);
}

function uniqueStrings(values) {
  return [...new Set(values.filter((value) => typeof value === "string" && value))];
}

function normalizeVariant(row) {
  const targetidRaw = typeof row?.targetid_raw === "string" ? row.targetid_raw : null;
  const commentidRaw = typeof row?.commentid_raw === "string" ? row.commentid_raw : null;
  return {
    path: typeof row?.path === "string" ? row.path : "root",
    owner_keys: Array.isArray(row?.owner_keys) ? row.owner_keys : [],
    commentInfo_keys_head: Array.isArray(row?.commentInfo_keys_head) ? row.commentInfo_keys_head : [],
    targetid_raw: targetidRaw,
    targetid_decoded: decodeMaybeNumeric(targetidRaw),
    commentid_raw: commentidRaw,
    commentid_decoded: decodeMaybeNumeric(commentidRaw),
  };
}

function classifyResult(variants) {
  if (!variants.length) {
    return {
      classification: "negative",
      reason_code: "container_missing",
      nonemptyHits: [],
    };
  }
  const nonemptyHits = variants.filter((row) => row.targetid_raw || row.commentid_raw);
  if (nonemptyHits.length) {
    return {
      classification: "positive",
      reason_code: "ids_found",
      nonemptyHits,
    };
  }
  return {
    classification: "negative",
    reason_code: "container_empty",
    nonemptyHits,
  };
}

function summarizeKeyNodes(keyNodes) {
  const pgDokiidValues = [];
  const relateDokiDecodedValues = [];
  for (const node of keyNodes) {
    const summary = node?.summary || {};
    if (typeof summary.pg_dokiid === "string" && summary.pg_dokiid) {
      pgDokiidValues.push(summary.pg_dokiid);
    }
    if (typeof summary.dokiId === "string") {
      const decoded = decodeMaybeNumeric(summary.dokiId);
      if (decoded) {
        relateDokiDecodedValues.push(decoded);
      }
    }
  }
  return {
    pg_dokiid_values: uniqueStrings(pgDokiidValues),
    relate_doki_decoded_values: uniqueStrings(relateDokiDecodedValues),
  };
}

function buildCaseTakeaway(result) {
  if (result.error) {
    return `${result.bucket}: probe error ${JSON.stringify(result.error)}`;
  }
  if (result.classification === "positive") {
    const decodedTarget = result.targetid_decoded_values.length
      ? `targetid decoded sample ${result.targetid_decoded_values.slice(0, 3).join(", ")}`
      : "non-empty commentInfo.targetid raw values";
    const decodedComment = result.commentid_decoded_values.length
      ? `commentid decoded sample ${result.commentid_decoded_values.slice(0, 2).join(", ")}`
      : "no decoded commentid yet";
    return `${result.bucket}: positive via root.base.commentInfo (${result.nonempty_commentinfo_hits} non-empty hits; ${decodedTarget}; ${decodedComment})`;
  }
  if (result.reason_code === "container_empty") {
    return `${result.bucket}: root.base.commentInfo container exists but stayed empty in this probe`;
  }
  return `${result.bucket}: no commentInfo container found in the scanned parse payloads`;
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  try {
    await page.addInitScript({ content: INIT_SCAN_SCRIPT });
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }
    const pageData = await page.evaluate(() => {
      const state = window.__TV_COMMENTINFO_SCAN__ || { hits: [], key_nodes: [], errors: [] };
      return {
        final_url: location.href,
        title: document.title,
        hits: Array.isArray(state.hits) ? state.hits : [],
        key_nodes: Array.isArray(state.key_nodes) ? state.key_nodes : [],
        errors: Array.isArray(state.errors) ? state.errors : [],
      };
    });
    const variants = pageData.hits.map(normalizeVariant);
    const dedupedVariants = [];
    const seenVariantSignatures = new Set();
    for (const variant of variants) {
      const signature = JSON.stringify(variant);
      if (seenVariantSignatures.has(signature)) {
        continue;
      }
      seenVariantSignatures.add(signature);
      dedupedVariants.push(variant);
    }
    const classification = classifyResult(dedupedVariants);
    const ownerShape = uniqueStrings(
      dedupedVariants.map((row) => JSON.stringify(Array.isArray(row.owner_keys) ? row.owner_keys : []))
    ).map((value) => JSON.parse(value));
    const keyNodes = Array.isArray(pageData.key_nodes) ? pageData.key_nodes.slice(0, 16) : [];
    const keyNodeSummary = summarizeKeyNodes(keyNodes);
    const { cid, vid } = extractCidVid(pageData.final_url || testCase.url);
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: pageData.final_url || null,
      title: pageData.title || null,
      cid,
      vid,
      classification: classification.classification,
      reason_code: classification.reason_code,
      commentinfo_container_present: dedupedVariants.length > 0,
      nonempty_commentinfo_hits: classification.nonemptyHits.length,
      commentinfo_owner_shape: ownerShape,
      commentinfo_variant_samples: dedupedVariants.slice(0, 10),
      targetid_decoded_values: uniqueStrings(
        classification.nonemptyHits.map((row) => row.targetid_decoded).filter(Boolean)
      ),
      commentid_decoded_values: uniqueStrings(
        classification.nonemptyHits.map((row) => row.commentid_decoded).filter(Boolean)
      ),
      pg_dokiid_values: keyNodeSummary.pg_dokiid_values,
      relate_doki_decoded_values: keyNodeSummary.relate_doki_decoded_values,
      key_nodes: keyNodes,
      errors: pageData.errors || [],
    };
  } finally {
    await page.close();
  }
}

function buildTakeaways(cases) {
  const positives = cases.filter((entry) => entry.classification === "positive");
  const emptyContainers = cases.filter((entry) => entry.reason_code === "container_empty");
  const missingContainers = cases.filter((entry) => entry.reason_code === "container_missing");
  const takeaways = [];
  if (positives.length) {
    takeaways.push(
      `positive commentInfo targetid/commentid evidence now spans ${positives.length} scanned page(s): ${positives
        .map((entry) => entry.bucket)
        .join(", ")}`
    );
  }
  if (emptyContainers.length) {
    takeaways.push(
      `empty commentInfo containers were reproduced on: ${emptyContainers.map((entry) => entry.bucket).join(", ")}`
    );
  }
  if (missingContainers.length) {
    takeaways.push(
      `no commentInfo container was found on: ${missingContainers.map((entry) => entry.bucket).join(", ")}`
    );
  }
  return takeaways.concat(cases.map(buildCaseTakeaway));
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
          classification: "negative",
          reason_code: "error",
          error: String(error),
        });
      }
    }
  } finally {
    await browser.close();
  }
  return {
    generated_at: new Date().toISOString(),
    scope: "browser-level commentInfo/targetid scan focused on parse-layer root.base.commentInfo payloads",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      cases,
    },
    cases: results,
    takeaways: buildTakeaways(results),
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
        stack: error && typeof error.stack === "string" ? error.stack.split("\\n").slice(0, 8) : [],
      },
      null,
      2
    );
    proc.stderr.write(message);
    proc.exitCode = 1;
  });
}
