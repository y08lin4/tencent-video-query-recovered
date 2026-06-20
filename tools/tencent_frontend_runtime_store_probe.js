import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);

const DEFAULT_BROWSER_CANDIDATES = [
  process.env.PLAYWRIGHT_CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
].filter(Boolean);

const COVER_KEYS = [
  "pay_status",
  "pay_status_exchange",
  "show_gift",
  "positive_trailer",
  "positive_content_id",
  "type",
  "type_name",
  "publish_date",
  "downright",
  "F",
  "video_ids",
];

const VIDEO_KEYS = [
  "state",
  "upload_src",
  "targetid",
  "targetId",
  "F",
  "pay_status",
  "positive_trailer",
  "positive_content_id",
  "type",
  "type_name",
  "publish_date",
  "downright",
  "cover_list",
  "c_covers",
];

const SEARCH_KEYS = [
  "pay_status",
  "pay_status_exchange",
  "show_gift",
  "positive_trailer",
  "positive_content_id",
  "state",
  "upload_src",
  "uploadSrc",
  "targetid",
  "targetId",
  "F",
];

function parseArgs(argv) {
  const args = {
    urls: [],
    waitMs: 10000,
    timeoutMs: 45000,
    indent: 2,
    browserPath: "",
  };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--wait-ms") {
      args.waitMs = Number(argv[++i]);
      continue;
    }
    if (token === "--timeout-ms") {
      args.timeoutMs = Number(argv[++i]);
      continue;
    }
    if (token === "--indent") {
      args.indent = Number(argv[++i]);
      continue;
    }
    if (token === "--browser-path") {
      args.browserPath = argv[++i] || "";
      continue;
    }
    if (token.startsWith("--")) {
      throw new Error(`Unknown option: ${token}`);
    }
    args.urls.push(token);
  }
  if (!args.urls.length) {
    throw new Error("At least one Tencent Video URL is required.");
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

async function loadPlaywright() {
  const requireCandidates = [
    process.env.CODEX_NODE_MODULES
      ? path.join(process.env.CODEX_NODE_MODULES, "playwright")
      : "",
    process.env.NODE_REPL_NODE_MODULE_DIRS
      ? path.join(process.env.NODE_REPL_NODE_MODULE_DIRS, "playwright")
      : "",
    process.env.NODE_PATH ? path.join(process.env.NODE_PATH, "playwright") : "",
    "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
    "playwright",
  ].filter(Boolean);
  for (const candidate of requireCandidates) {
    try {
      return require(candidate);
    } catch {}
  }

  const importCandidates = [
    process.env.CODEX_NODE_MODULES
      ? path.join(process.env.CODEX_NODE_MODULES, "playwright", "index.mjs")
      : "",
    process.env.NODE_REPL_NODE_MODULE_DIRS
      ? path.join(process.env.NODE_REPL_NODE_MODULE_DIRS, "playwright", "index.mjs")
      : "",
    process.env.NODE_PATH
      ? path.join(process.env.NODE_PATH, "playwright", "index.mjs")
      : "",
    "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs",
  ].filter(Boolean);
  for (const candidate of importCandidates) {
    try {
      return await import(pathToFileURL(candidate).href);
    } catch {}
  }

  throw new Error(
    "Could not resolve `playwright`. Set CODEX_NODE_MODULES or install playwright in a resolvable node_modules path."
  );
}

async function firstExistingPath(candidates) {
  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {}
  }
  return "";
}

async function resolveBrowserPath(explicitPath) {
  if (explicitPath) {
    await fs.access(explicitPath);
    return explicitPath;
  }
  const resolved = await firstExistingPath(DEFAULT_BROWSER_CANDIDATES);
  if (!resolved) {
    throw new Error(
      "Could not find a local Chrome/Edge executable. Use --browser-path to pass one explicitly."
    );
  }
  return resolved;
}

async function inspectPage(page, inputUrl, waitMs, timeoutMs) {
  await page.goto(inputUrl, {
    waitUntil: "domcontentloaded",
    timeout: timeoutMs,
  });
  if (waitMs > 0) {
    await page.waitForTimeout(waitMs);
  }
  return page.evaluate(
    ({ coverKeys, videoKeys, searchKeys }) => {
      const ssr = window.__vikor__context__?.ssrPayloads || {};
      const pinia = ssr._piniaState || {};
      const union = pinia.union || {};
      const coverMap = union.coverInfoMap || {};
      const videoMap = union.videoInfoMap || {};
      const cid = union.initialCid || Object.keys(coverMap)[0] || "";
      const vid = union.initialVid || Object.keys(videoMap)[0] || "";
      const cover = coverMap[cid] || {};
      const video = videoMap[vid] || {};

      const pick = (obj, keys) =>
        Object.fromEntries(
          keys.map((key) => [key, obj[key]]).filter(([, value]) => value !== undefined)
        );

      const roots = {
        pinia: pinia,
        asyncData: ssr._async_data,
        ctx: window.__vikor__context__,
      };
      const hits = [];
      const seen = new WeakSet();
      const walk = (obj, basePath, depth = 0) => {
        if (!obj || typeof obj !== "object" || seen.has(obj) || depth > 8 || hits.length >= 120) {
          return;
        }
        seen.add(obj);
        for (const key of Object.keys(obj)) {
          const nextPath = basePath ? `${basePath}.${key}` : key;
          let value;
          try {
            value = obj[key];
          } catch {
            continue;
          }
          if (searchKeys.includes(key)) {
            hits.push({
              path: nextPath,
              value: value,
              value_type: typeof value,
            });
          }
          walk(value, nextPath, depth + 1);
        }
      };
      for (const [name, root] of Object.entries(roots)) {
        walk(root, name, 0);
      }

      return {
        final_url: location.href,
        title: document.title,
        cid,
        vid,
        union_keys: Object.keys(union),
        cover_key_count: Object.keys(cover).length,
        video_key_count: Object.keys(video).length,
        store_cover_fields: pick(cover, coverKeys),
        store_video_fields: pick(video, videoKeys),
        runtime_key_hits: hits,
      };
    },
    { coverKeys: COVER_KEYS, videoKeys: VIDEO_KEYS, searchKeys: SEARCH_KEYS }
  );
}

function buildSummary(pages) {
  const payStatusValues = [];
  const positiveTrailerValues = [];
  const absentEverywhere = {
    F: true,
    upload_src: true,
    targetid: true,
  };

  for (const page of pages) {
    const cover = page.store_cover_fields || {};
    const video = page.store_video_fields || {};
    if (cover.pay_status !== undefined && !payStatusValues.includes(String(cover.pay_status))) {
      payStatusValues.push(String(cover.pay_status));
    }
    if (
      cover.positive_trailer !== undefined &&
      !positiveTrailerValues.includes(String(cover.positive_trailer))
    ) {
      positiveTrailerValues.push(String(cover.positive_trailer));
    }
    if (cover.F !== undefined || video.F !== undefined) {
      absentEverywhere.F = false;
    }
    if (video.upload_src !== undefined) {
      absentEverywhere.upload_src = false;
    }
    if (video.targetid !== undefined || video.targetId !== undefined) {
      absentEverywhere.targetid = false;
    }
  }

  return {
    normalized_cover_pay_status_values: payStatusValues,
    normalized_cover_positive_trailer_values: positiveTrailerValues,
    absent_from_sampled_union_store: Object.entries(absentEverywhere)
      .filter(([, absent]) => absent)
      .map(([field]) => field),
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const playwright = await loadPlaywright();
  const browserPath = await resolveBrowserPath(args.browserPath);
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath,
  });

  const pages = [];
  try {
    for (const inputUrl of args.urls) {
      const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
      try {
        const result = await inspectPage(page, inputUrl, args.waitMs, args.timeoutMs);
        pages.push({
          input_url: inputUrl,
          ...result,
        });
      } catch (error) {
        pages.push({
          input_url: inputUrl,
          error: String(error),
        });
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }

  const report = {
    tool: "tencent_frontend_runtime_store_probe",
    browser_executable: browserPath,
    wait_ms: args.waitMs,
    timeout_ms: args.timeoutMs,
    pages,
    summary: buildSummary(pages.filter((page) => !page.error)),
  };
  process.stdout.write(JSON.stringify(report, null, args.indent));
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack || error.message : String(error)}\n`);
  process.exitCode = 1;
});
