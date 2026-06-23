#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_DESKTOP_URL =
  "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html";
const DEFAULT_WAIT_MS = 10000;
const DEFAULT_OUTPUT = path.join(
  process.cwd(),
  "analysis",
  "anonymous_real_cookie_env.json",
);
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
].filter(Boolean);
const PLAYWRIGHT_CORE_CANDIDATES = [
  process.env.PLAYWRIGHT_CORE_PATH,
  "C:/Users/lin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/node_modules/playwright-core",
].filter(Boolean);
const API_HOSTS = ["data.video.qq.com", "union.video.qq.com"];

function parseArgs(argv) {
  const options = {
    output: DEFAULT_OUTPUT,
    desktopUrl: DEFAULT_DESKTOP_URL,
    waitMs: DEFAULT_WAIT_MS,
    executablePath: "",
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--output") {
      options.output = argv[++i];
    } else if (arg === "--desktop-url") {
      options.desktopUrl = argv[++i];
    } else if (arg === "--wait-ms") {
      options.waitMs = Number(argv[++i]);
    } else if (arg === "--executable-path") {
      options.executablePath = argv[++i];
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!Number.isFinite(options.waitMs) || options.waitMs < 0) {
    throw new Error("--wait-ms must be a non-negative number");
  }
  return options;
}

function printHelp() {
  process.stdout.write(
    [
      "Usage: node tools/tencent_anonymous_cookie_replay_env_capture.js [options]",
      "",
      "Options:",
      "  --output <path>            Output JSON path",
      "  --desktop-url <url>        Seed page to open before reading cookies",
      "  --wait-ms <ms>             Wait time after navigation (default 10000)",
      "  --executable-path <path>   Explicit Chrome/Edge executable path",
      "  -h, --help                 Show this help",
      "",
    ].join("\n"),
  );
}

function findExecutable(explicitPath) {
  const candidates = explicitPath ? [explicitPath] : CHROME_CANDIDATES;
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error(
    "No Chrome/Edge executable found. Pass --executable-path or set CHROME_PATH.",
  );
}

function loadPlaywright() {
  const attempts = ["playwright-core", "playwright", ...PLAYWRIGHT_CORE_CANDIDATES];
  const errors = [];
  for (const candidate of attempts) {
    try {
      return require(candidate);
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }
  throw new Error(`Unable to load Playwright. Attempts: ${errors.join(" | ")}`);
}

function cookieMatchesHost(cookieDomain, host) {
  const normalized = String(cookieDomain || "").replace(/^\./, "").toLowerCase();
  const hostLower = host.toLowerCase();
  return hostLower === normalized || hostLower.endsWith(`.${normalized}`);
}

function buildCookieHeader(cookies, hosts) {
  const selected = [];
  const seen = new Set();
  for (const cookie of cookies) {
    const name = String(cookie.name || "");
    if (!name || seen.has(name)) {
      continue;
    }
    if (hosts.some((host) => cookieMatchesHost(cookie.domain, host))) {
      selected.push(`${name}=${cookie.value || ""}`);
      seen.add(name);
    }
  }
  return selected.join("; ");
}

function buildDesktopHeaders(cookieHeader) {
  return {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: "https://v.qq.com/",
    Origin: "https://v.qq.com",
    Cookie: cookieHeader,
  };
}

function buildMobileHeaders(cookieHeader) {
  return {
    "User-Agent":
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) " +
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: "https://m.v.qq.com/",
    Origin: "https://m.v.qq.com",
    Cookie: cookieHeader,
  };
}

async function captureReplayEnvironments(options) {
  const playwright = loadPlaywright();
  const executablePath = findExecutable(options.executablePath);
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath,
  });
  try {
    const desktopContext = await browser.newContext({
      userAgent:
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
      viewport: { width: 1440, height: 900 },
      locale: "zh-CN",
      extraHTTPHeaders: { "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8" },
    });
    const desktopPage = await desktopContext.newPage();
    await desktopPage.goto(options.desktopUrl, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await desktopPage.waitForTimeout(options.waitMs);
    const desktopCookies = await desktopContext.cookies();
    await desktopContext.close();

    const mobileContext = await browser.newContext({
      ...playwright.devices["iPhone 13"],
      locale: "zh-CN",
      extraHTTPHeaders: { "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8" },
    });
    const mobilePage = await mobileContext.newPage();
    await mobilePage.goto(options.desktopUrl, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await mobilePage.waitForTimeout(options.waitMs);
    const mobileCookies = await mobileContext.cookies();
    await mobileContext.close();

    const desktopCookieHeader = buildCookieHeader(desktopCookies, API_HOSTS);
    const mobileCookieHeader = buildCookieHeader(mobileCookies, API_HOSTS);
    if (!desktopCookieHeader) {
      throw new Error("Desktop capture produced an empty API cookie header");
    }
    if (!mobileCookieHeader) {
      throw new Error("Mobile capture produced an empty API cookie header");
    }

    return {
      pc_web_real_cookie_replay: buildDesktopHeaders(desktopCookieHeader),
      mobile_h5_real_cookie_replay: buildMobileHeaders(mobileCookieHeader),
    };
  } finally {
    await browser.close();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const envJson = await captureReplayEnvironments(options);
  fs.mkdirSync(path.dirname(options.output), { recursive: true });
  fs.writeFileSync(options.output, `${JSON.stringify(envJson, null, 2)}\n`, "utf8");
  process.stdout.write(`${options.output}\n`);
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
