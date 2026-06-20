import { createRequire } from "node:module";
import path from "node:path";
import { runProbe as runCommentInfoScan } from "./tencent_frontend_targetid_commentinfo_scan.js";

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
    bucket: "sports_collection_shell",
    url: "https://v.qq.com/x/cover/mzc002003fh665c.html",
  },
  {
    bucket: "variety_topic_pay15_targetid_uploadsrc",
    url: "https://v.qq.com/x/cover/mzc002001u873es/k004768pj4j.html",
  },
];

const IDENTITY_KEY_RE = /(targetid|commentid|feed[_-]?id|father[_-]?feed[_-]?id|cp[_-]?id|dokiid|ftid)/i;

const INIT_PROBE_SCRIPT = `
(() => {
  const state = {
    open_calls: [],
    iframe_src_sets: [],
    post_message_calls: [],
  };
  const render = (value) => {
    if (value === null || value === undefined) {
      return value;
    }
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return value;
    }
    try {
      return JSON.stringify(value).slice(0, 240);
    } catch {
      try {
        return String(value).slice(0, 240);
      } catch {
        return "[unrenderable]";
      }
    }
  };

  try {
    const originalOpen = window.open;
    window.open = function patchedOpen(...args) {
      if (state.open_calls.length < 20) {
        state.open_calls.push(args.slice(0, 4).map((value) => render(value)));
      }
      return typeof originalOpen === "function" ? originalOpen.apply(this, args) : null;
    };
  } catch {}

  try {
    const originalPostMessage = window.postMessage;
    window.postMessage = function patchedPostMessage(...args) {
      if (state.post_message_calls.length < 40) {
        state.post_message_calls.push(args.slice(0, 2).map((value) => render(value)));
      }
      return originalPostMessage.apply(this, args);
    };
  } catch {}

  try {
    const proto = window.HTMLIFrameElement && window.HTMLIFrameElement.prototype;
    const descriptor = proto ? Object.getOwnPropertyDescriptor(proto, "src") : null;
    if (proto && descriptor && typeof descriptor.set === "function") {
      Object.defineProperty(proto, "src", {
        configurable: descriptor.configurable !== false,
        enumerable: descriptor.enumerable !== false,
        get: descriptor.get,
        set(value) {
          if (state.iframe_src_sets.length < 40) {
            state.iframe_src_sets.push(String(value));
          }
          return descriptor.set.call(this, value);
        },
      });
    }
  } catch {}

  window.__TV_TARGETID_REPORT_IDENTITY__ = state;
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

function parseNumericSet(values) {
  const set = new Set();
  for (const value of values || []) {
    const text = String(value || "");
    const matches = text.match(/\d{4,}/g) || [];
    for (const match of matches) {
      set.add(match);
    }
  }
  return [...set];
}

function intersect(a, b) {
  const right = new Set(b || []);
  return [...new Set(a || [])].filter((value) => right.has(value));
}

function collectScalarValues(value, sink = [], limit = 120) {
  if (sink.length >= limit || value === null || value === undefined) {
    return sink;
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    sink.push(String(value));
    return sink;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      if (sink.length >= limit) {
        break;
      }
      collectScalarValues(item, sink, limit);
    }
    return sink;
  }
  if (typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      if (sink.length >= limit) {
        break;
      }
      sink.push(String(key));
      collectScalarValues(child, sink, limit);
    }
  }
  return sink;
}

async function inspectReportButtons(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const requestHits = [];
  page.on("request", (request) => {
    const url = request.url();
    if (
      requestHits.length < 40 &&
      /feedback|report|tipoff|complain|universalReport|danmaku|comment/i.test(url)
    ) {
      requestHits.push({
        method: request.method(),
        url,
      });
    }
  });

  try {
    await page.addInitScript({ content: INIT_PROBE_SCRIPT });
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }

    const dom = await page.evaluate(() => {
      const parseParams = (raw) => {
        const params = {};
        try {
          for (const [key, value] of new URLSearchParams(raw || "")) {
            params[key] = value;
          }
        } catch {}
        return params;
      };
      const visible = (node) => {
        if (!node) {
          return false;
        }
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const textOf = (node) => (node?.innerText || node?.textContent || "").replace(/\s+/g, " ").trim();
      const identityKeyRe = /(targetid|commentid|feed[_-]?id|father[_-]?feed[_-]?id|cp[_-]?id|dokiid|ftid)/i;
      const ownerPropRe = /^(?:__reactProps\$|__reactFiber\$|__vue)/;
      const previewValue = (value) => {
        if (value === null || value === undefined) {
          return value;
        }
        if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
          return value;
        }
        if (Array.isArray(value)) {
          return value.slice(0, 6).map((item) => previewValue(item));
        }
        if (typeof value === "object") {
          const out = {};
          for (const key of Object.getOwnPropertyNames(value).slice(0, 8)) {
            let child;
            try {
              child = value[key];
            } catch {
              continue;
            }
            if (
              child === null ||
              child === undefined ||
              typeof child === "string" ||
              typeof child === "number" ||
              typeof child === "boolean"
            ) {
              out[key] = child;
            }
          }
          if (Object.keys(out).length > 0) {
            return out;
          }
          return `[object ${value.constructor?.name || "Object"}]`;
        }
        try {
          return String(value).slice(0, 120);
        } catch {
          return "[unrenderable]";
        }
      };
      const collectInterestingEntries = (source, basePath = "", depth = 0, sink = [], seen = new WeakSet()) => {
        if (!source || typeof source !== "object" || depth > 2 || sink.length >= 20) {
          return sink;
        }
        if (seen.has(source)) {
          return sink;
        }
        seen.add(source);
        const keys = Object.getOwnPropertyNames(source).slice(0, 40);
        for (const key of keys) {
          if (sink.length >= 20) {
            break;
          }
          let child;
          try {
            child = source[key];
          } catch {
            continue;
          }
          const nextPath = basePath ? `${basePath}.${key}` : key;
          if (identityKeyRe.test(key)) {
            sink.push({
              path: nextPath,
              value: previewValue(child),
            });
          }
          if (depth < 2 && child && typeof child === "object") {
            collectInterestingEntries(child, nextPath, depth + 1, sink, seen);
          }
        }
        return sink;
      };
      const scanOwnerBridgeNode = (node, label) => {
        if (!node) {
          return null;
        }
        const dataset = {};
        try {
          for (const [key, value] of Object.entries(node.dataset || {})) {
            if (identityKeyRe.test(key)) {
              dataset[key] = value;
            }
          }
        } catch {}
        const ownerProps = [];
        try {
          for (const prop of Object.getOwnPropertyNames(node)) {
            if (!ownerPropRe.test(prop)) {
              continue;
            }
            let raw;
            try {
              raw = node[prop];
            } catch {
              continue;
            }
            const interestingEntries = collectInterestingEntries(raw);
            if (interestingEntries.length > 0) {
              ownerProps.push({
                prop,
                interesting_entries: interestingEntries.slice(0, 12),
              });
            }
          }
        } catch {}
        if (Object.keys(dataset).length === 0 && ownerProps.length === 0) {
          return null;
        }
        return {
          label,
          tag: node.tagName ? node.tagName.toLowerCase() : null,
          className: String(node.className || "").slice(0, 200),
          dataset,
          owner_props: ownerProps.slice(0, 4),
        };
      };
      const scanOwnerBridgeContext = (node) => {
        const candidates = [
          ["self", node],
          ["feed", node?.closest?.(".at-feed") || null],
          ["report", node?.closest?.('[class*="report"]') || null],
          ["comment", node?.closest?.('[class*="comment"], [data-targetid], [data-commentid]') || null],
          ["parent", node?.parentElement || null],
        ];
        const seen = new Set();
        const results = [];
        for (const [label, candidate] of candidates) {
          if (!candidate || seen.has(candidate)) {
            continue;
          }
          seen.add(candidate);
          const snapshot = scanOwnerBridgeNode(candidate, label);
          if (snapshot) {
            results.push(snapshot);
          }
        }
        return results;
      };

      const buttons = Array.from(document.querySelectorAll(".at-feed__action-report"));
      const samples = buttons.slice(0, 8).map((node, index) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        const raw = node.getAttribute("dt-params") || "";
        return {
          index,
          text: textOf(node),
          visibility: style.visibility,
          display: style.display,
          opacity: style.opacity,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          dt_params_raw: raw,
          dt_params: parseParams(raw),
          owner_bridge_scan: scanOwnerBridgeContext(node),
          feed_excerpt: textOf(node.closest(".at-feed")).slice(0, 160),
        };
      });

      return {
        report_button_count: buttons.length,
        visible_report_button_count: buttons.filter((node) => visible(node)).length,
        report_button_samples: samples,
      };
    });

    const forcedClick = await page.evaluate(async () => {
      const node = document.querySelector(".at-feed__action-report");
      if (!node) {
        return { error: "no report button found" };
      }
      const parent = node.closest(".at-feed");
      const before = {
        text: (node.textContent || "").trim(),
        className: String(node.className || ""),
        visibility: getComputedStyle(node).visibility,
        display: getComputedStyle(node).display,
      };
      if (parent) {
        parent.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true, cancelable: true, view: window }));
        parent.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, cancelable: true, view: window }));
      }
      node.style.visibility = "visible";
      node.style.display = "inline-flex";
      node.style.opacity = "1";
      node.style.pointerEvents = "auto";
      try {
        node.click();
      } catch {}
      try {
        node.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      } catch {}
      await new Promise((resolve) => setTimeout(resolve, 1800));
      const after = {
        visibility: getComputedStyle(node).visibility,
        display: getComputedStyle(node).display,
      };
      return {
        before,
        after,
      };
    });

    const finalState = await page.evaluate(() => {
      const state = window.__TV_TARGETID_REPORT_IDENTITY__ || {
        open_calls: [],
        iframe_src_sets: [],
        post_message_calls: [],
      };
      const interestingIframes = Array.from(document.querySelectorAll("iframe"))
        .map((node) => {
          try {
            return node.getAttribute("src") || node.src || "";
          } catch {
            return "";
          }
        })
        .filter((value) => /feedback|report|tipoff|complain|universalReport/i.test(value));
      return {
        open_calls: state.open_calls,
        iframe_src_sets: state.iframe_src_sets,
        post_message_calls: state.post_message_calls,
        interesting_iframes: interestingIframes,
      };
    });

    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      dom,
      forced_click: forcedClick,
      final_state: finalState,
      request_hits: requestHits,
    };
  } finally {
    await page.close();
  }
}

function mergeIdentityAudit(caseScan, domAudit) {
  const reportButtonSamples = domAudit.dom?.report_button_samples || [];
  const dtParamsNumeric = parseNumericSet(
    reportButtonSamples.flatMap((entry) => Object.values(entry.dt_params || {}))
  );
  const ownerBridgeNumeric = parseNumericSet(
    reportButtonSamples.flatMap((entry) => collectScalarValues(entry.owner_bridge_scan || []))
  );
  const commentTargetIds = caseScan.targetid_decoded_values || [];
  const commentCommentIds = caseScan.commentid_decoded_values || [];
  const dokiValues = [
    ...(caseScan.pg_dokiid_values || []),
    ...(caseScan.relate_doki_decoded_values || []),
    ...(caseScan.request_dokiid_values || []),
    ...(caseScan.response_ftid_values || []),
  ];
  return {
    bucket: domAudit.bucket,
    input_url: domAudit.input_url,
    title: caseScan.title || null,
    classification: caseScan.classification,
    commentinfo_container_present: caseScan.commentinfo_container_present,
    nonempty_commentinfo_hits: caseScan.nonempty_commentinfo_hits,
    targetid_decoded_values: commentTargetIds,
    commentid_decoded_values: commentCommentIds,
    pg_dokiid_values: caseScan.pg_dokiid_values || [],
    relate_doki_decoded_values: caseScan.relate_doki_decoded_values || [],
    report_button_count: domAudit.dom?.report_button_count || 0,
    visible_report_button_count: domAudit.dom?.visible_report_button_count || 0,
    report_button_samples: reportButtonSamples,
    dt_params_numeric_values: dtParamsNumeric,
    owner_bridge_numeric_values: ownerBridgeNumeric,
    intersections: {
      targetid_vs_dt_params: intersect(commentTargetIds, dtParamsNumeric),
      commentid_vs_dt_params: intersect(commentCommentIds, dtParamsNumeric),
      dokiid_ftid_vs_dt_params: intersect(dokiValues, dtParamsNumeric),
      targetid_vs_owner_bridge: intersect(commentTargetIds, ownerBridgeNumeric),
      commentid_vs_owner_bridge: intersect(commentCommentIds, ownerBridgeNumeric),
      dokiid_ftid_vs_owner_bridge: intersect(dokiValues, ownerBridgeNumeric),
    },
    forced_click: domAudit.forced_click,
    final_state: {
      open_call_count: (domAudit.final_state?.open_calls || []).length,
      interesting_iframe_count: (domAudit.final_state?.interesting_iframes || []).length,
      post_message_count: (domAudit.final_state?.post_message_calls || []).length,
      open_calls: domAudit.final_state?.open_calls || [],
      interesting_iframes: domAudit.final_state?.interesting_iframes || [],
    },
    request_hits: domAudit.request_hits || [],
  };
}

function buildTakeaways(cases) {
  const takeaways = [];
  const positiveCases = cases.filter((entry) => entry.nonempty_commentinfo_hits > 0);
  if (
    positiveCases.length > 0 &&
    positiveCases.every(
      (entry) =>
        entry.intersections.targetid_vs_owner_bridge.length === 0 &&
        entry.intersections.commentid_vs_owner_bridge.length === 0
    )
  ) {
    takeaways.push(
      "Even the added dataset / owner-prop bridge scan around anonymous report/comment nodes still did not surface the same targetid/commentid values from the positive commentInfo family."
    );
  }
  if (
    positiveCases.length > 0 &&
    positiveCases.every(
      (entry) =>
        entry.intersections.targetid_vs_dt_params.length === 0 &&
        entry.intersections.commentid_vs_dt_params.length === 0
    )
  ) {
    takeaways.push(
      "On pages where root.base.commentInfo.targetid/commentid is non-empty, the sampled comment report buttons still expose a different identity family (`feed_id` / `cp_id` / counters) rather than the decoded commentInfo targetid/commentid values."
    );
  }
  if (
    cases.every(
      (entry) =>
        entry.final_state.open_call_count === 0 &&
        entry.final_state.interesting_iframe_count === 0 &&
        entry.final_state.post_message_count === 0
    )
  ) {
    takeaways.push(
      "Even after force-revealing and clicking the first sampled report button, this audit still did not produce a natural report popup / iframe / postMessage handoff carrying targetid."
    );
  }
  if (positiveCases.some((entry) => entry.intersections.dokiid_ftid_vs_dt_params.length === 0)) {
    takeaways.push(
      "The anonymous comment-report DOM identity tags also stay disjoint from the currently observed dokiid/ftid discussion chain on the sampled positive pages."
    );
  }
  takeaways.push(
    "This narrows the natural-producer gap: in the tested anonymous DOM path, commentInfo targetid/commentid survives as a neighboring payload family, but the sampled report-button producer surface still does not expose or consume those same IDs directly."
  );
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const browserPath = await resolveBrowserPath(options.browserPath || "");

  const commentInfoScan = await runCommentInfoScan({
    cases,
    waitMs,
    timeoutMs,
    browserPath,
  });
  const commentInfoMap = new Map((commentInfoScan.cases || []).map((entry) => [entry.bucket, entry]));

  const playwright = await loadPlaywright();
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath,
  });
  const domAudits = [];
  try {
    for (const testCase of cases) {
      try {
        domAudits.push(await inspectReportButtons(browser, testCase, { waitMs, timeoutMs }));
      } catch (error) {
        domAudits.push({
          bucket: testCase.bucket,
          input_url: testCase.url,
          error: String(error),
          dom: {
            report_button_count: 0,
            visible_report_button_count: 0,
            report_button_samples: [],
          },
          forced_click: {},
          final_state: {
            open_calls: [],
            iframe_src_sets: [],
            post_message_calls: [],
            interesting_iframes: [],
          },
          request_hits: [],
        });
      }
    }
  } finally {
    await browser.close();
  }

  const mergedCases = domAudits.map((entry) => {
    const scan = commentInfoMap.get(entry.bucket) || {};
    return mergeIdentityAudit(scan, entry);
  });

  return {
    generated_at: new Date().toISOString(),
    scope: "anonymous report-button identity audit against commentInfo targetid/commentid families",
    source_tool: "tools/tencent_frontend_targetid_report_identity_audit.js",
    commentinfo_source_tool: "tools/tencent_frontend_targetid_commentinfo_scan.js",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      actions: [
        "scan parse-layer commentInfo targetid/commentid families",
        "inspect hidden comment report button dt-params",
        "force-reveal and click the first sampled report button",
        "compare report-button numeric ids with commentInfo targetid/commentid and dokiid/ftid families",
      ],
      cases,
    },
    cases: mergedCases,
    takeaways: buildTakeaways(mergedCases),
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
