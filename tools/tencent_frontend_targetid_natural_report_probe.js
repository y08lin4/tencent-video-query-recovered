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
    bucket: "variety_topic_pay15_targetid_uploadsrc",
    url: "https://v.qq.com/x/cover/mzc002001u873es/k004768pj4j.html",
  },
];

const INIT_PROBE_SCRIPT = `
(() => {
  const state = {
    open_calls: [],
    post_message_calls: [],
    iframe_src_sets: [],
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

  window.__TV_NATURAL_REPORT_PROBE__ = state;
})();
`;

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 12000,
    timeoutMs: 45000,
    hoverLimit: 8,
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
    if (token === "--hover-limit") {
      args.hoverLimit = Number(argv[++i]);
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
    if (token === "--case") {
      const raw = argv[++i] || "";
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
  if (!Number.isFinite(args.hoverLimit) || args.hoverLimit <= 0) {
    throw new Error("--hover-limit must be greater than 0.");
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

function matchesInterestingUrl(url) {
  return /feedback|report|tipoff|complain|universalReport|danmaku|comment/i.test(url);
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const requestHits = [];
  const popupHits = [];
  const frameHits = [];
  page.on("request", (request) => {
    const url = request.url();
    if (requestHits.length < 60 && matchesInterestingUrl(url)) {
      requestHits.push({ method: request.method(), url });
    }
  });
  page.on("popup", (popup) => {
    if (popupHits.length < 20) {
      popupHits.push({ url: popup.url() });
    }
  });
  page.on("frameattached", (frame) => {
    if (frameHits.length < 40) {
      frameHits.push({ name: frame.name(), url: frame.url() });
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

    const initial = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll(".at-feed__action-report"));
      const samples = buttons.slice(0, 12).map((node, index) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return {
          index,
          text: (node.textContent || "").trim(),
          visibility: style.visibility,
          display: style.display,
          opacity: style.opacity,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          dt_params: node.getAttribute("dt-params") || "",
        };
      });
      return {
        report_button_count: buttons.length,
        report_button_samples: samples,
      };
    });

    const hoverSweep = [];
    const feedCount = await page.locator(".at-feed").count();
    for (let i = 0; i < Math.min(feedCount, options.hoverLimit); i += 1) {
      const locator = page.locator(".at-feed").nth(i);
      try {
        await locator.scrollIntoViewIfNeeded();
        await locator.hover({ force: true, timeout: 5000 });
        await page.waitForTimeout(600);
        const state = await page.evaluate((index) => {
          const feed = document.querySelectorAll(".at-feed")[index];
          const report = feed ? feed.querySelector(".at-feed__action-report") : null;
          if (!report) {
            return null;
          }
          const style = getComputedStyle(report);
          const rect = report.getBoundingClientRect();
          return {
            index,
            visibility: style.visibility,
            display: style.display,
            opacity: style.opacity,
            pointer_events: style.pointerEvents,
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        }, i);
        hoverSweep.push({ index: i, state });
      } catch (error) {
        hoverSweep.push({ index: i, error: String(error) });
      }
    }

    const programmaticClick = await page.evaluate(async () => {
      const node = document.querySelector(".at-feed__action-report");
      if (!node) {
        return { error: "no report button found" };
      }
      const style = getComputedStyle(node);
      const result = {
        text: (node.textContent || "").trim(),
        visibility: style.visibility,
        display: style.display,
      };
      try {
        node.click();
        result.click_called = true;
      } catch (error) {
        result.click_error = String(error);
      }
      try {
        node.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
        result.dispatch_click = true;
      } catch (error) {
        result.dispatch_click_error = String(error);
      }
      await new Promise((resolve) => setTimeout(resolve, 1800));
      return result;
    });

    const playerContextMenu = await (async () => {
      try {
        const player = page.locator(".main-player-container").first();
        await player.click({ button: "right", force: true, position: { x: 300, y: 180 }, timeout: 5000 });
      } catch {
        try {
          await page.mouse.click(360, 240, { button: "right" });
        } catch {}
      }
      await page.waitForTimeout(1200);
      return page.evaluate(() => {
        const menu = document.querySelector(".txp_contextmenu");
        const itemNodes = Array.from(document.querySelectorAll(".txp_menuitem"));
        const menuVisible =
          !!menu &&
          getComputedStyle(menu).display !== "none" &&
          getComputedStyle(menu).visibility !== "hidden" &&
          menu.getBoundingClientRect().width > 0;
        const items = itemNodes.map((node) => ({
          text: (node.textContent || "").trim(),
          visible:
            getComputedStyle(node).display !== "none" &&
            getComputedStyle(node).visibility !== "hidden" &&
            node.getBoundingClientRect().width > 0,
        }));
        return {
          menu_class: menu ? menu.className : null,
          menu_visible: menuVisible,
          items,
        };
      });
    })();

    const finalState = await page.evaluate(() => {
      const interestingRe = /feedback|report|tipoff|complain|universalReport|danmaku|comment/i;
      const probe = window.__TV_NATURAL_REPORT_PROBE__ || {
        open_calls: [],
        post_message_calls: [],
        iframe_src_sets: [],
      };
      return {
        probe,
        interesting_iframes: Array.from(document.querySelectorAll("iframe"))
          .map((node) => {
            try {
              return node.getAttribute("src") || node.src || "";
            } catch {
              return "";
            }
          })
          .filter((value) => typeof value === "string" && interestingRe.test(value)),
      };
    });

    const takeaways = [];
    const visibleHover = hoverSweep.find((entry) => entry.state && entry.state.visibility !== "hidden");
    if (!visibleHover) {
      takeaways.push("No sampled comment/report button became visible after direct hover on `.at-feed` cards.");
    }
    if ((finalState.probe.open_calls || []).length === 0) {
      takeaways.push("No `window.open(...)` report/feedback popup was triggered during the natural-path attempts.");
    }
    if ((finalState.interesting_iframes || []).length === 0) {
      takeaways.push("No feedback/report iframe URL was created during the natural-path attempts.");
    }
    if (!playerContextMenu.menu_visible) {
      takeaways.push("The player context menu stayed hidden in the tested anonymous PC-Web path.");
    }

    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      initial,
      hover_sweep: hoverSweep,
      programmatic_click: programmaticClick,
      player_context_menu: playerContextMenu,
      final_state: finalState,
      request_hits: requestHits,
      popup_hits: popupHits,
      frame_hits: frameHits,
      takeaways,
    };
  } finally {
    await page.close();
  }
}

export async function runProbe(options = {}) {
  const playwright = await loadPlaywright();
  const browserPath = await resolveBrowserPath(options.browserPath || "");
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath,
  });
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const hoverLimit = Number.isFinite(options.hoverLimit) ? options.hoverLimit : 8;
  const pages = [];
  try {
    for (const testCase of cases) {
      try {
        pages.push(await inspectCase(browser, testCase, { waitMs, timeoutMs, hoverLimit }));
      } catch (error) {
        pages.push({
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
    scope: "natural anonymous PC-Web report/feedback path probe for targetid-related popup handoff",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      hover_limit: hoverLimit,
      natural_actions: [
        "inspect hidden comment report buttons",
        "hover sampled .at-feed cards",
        "programmatic click on the first hidden comment report button",
        "right-click the player container and inspect the context menu",
      ],
      cases,
    },
    pages,
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
