import fs from "node:fs/promises";

const API1_URL = "https://data.video.qq.com/fcgi-bin/data";
const API2_URL = "https://union.video.qq.com/fcgi-bin/data";

export const BASE_ENVIRONMENTS = {
  pc_web_ua: {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    Accept: "*/*",
  },
  mobile_h5_ua: {
    "User-Agent":
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    Accept: "*/*",
  },
  minimal_headers: {},
  referer_origin: {
    "User-Agent": "Mozilla/5.0",
    Accept: "*/*",
    Referer: "https://v.qq.com/",
    Origin: "https://v.qq.com",
  },
};

export const BROWSER_LIKE_ENVIRONMENTS = {
  pc_web_browser_like: {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: "https://v.qq.com/",
    "Sec-CH-UA":
      '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
  },
  pc_web_browser_like_cookie: {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Cookie:
      "pgv_pvid=blackboxprobe123456; video_guid=blackboxprobe123456; _qpsvr_localtk=0.123456789",
    Referer: "https://v.qq.com/",
    "Sec-CH-UA":
      '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
  },
  mobile_h5_browser_like: {
    "User-Agent":
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Referer: "https://v.qq.com/",
    "Sec-CH-UA":
      '"Mobile Safari";v="18", "Safari";v="18", "Not/A)Brand";v="24"',
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": '"iOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
  },
  mobile_h5_browser_like_cookie: {
    "User-Agent":
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    Accept: "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    Cookie:
      "pgv_pvid=blackboxprobe654321; video_guid=blackboxprobe654321; _qpsvr_localtk=0.987654321",
    Referer: "https://v.qq.com/",
    "Sec-CH-UA":
      '"Mobile Safari";v="18", "Safari";v="18", "Not/A)Brand";v="24"',
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": '"iOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
  },
};

const API1_DEFAULTS = {
  tid: "431",
  appid: "10001005",
  appkey: "0d1a9ddd94de871b",
};

const API2_DEFAULTS = {
  otype: "json",
  tid: "535",
  appid: "20001238",
  appkey: "6c03bbe9658448a4",
  union_platform: "3",
};

const DEFAULT_COVER_CONFIGS = [
  {
    cid: "482396nuyaelv0e",
    expected_type: "106/少儿",
    expected_pay_status: "8",
    expected_positive_trailer: "1",
    expected_state_counts: { "4": 8, "8": 73 },
    expected_upload_src_counts: { "20": 3, "108": 78 },
  },
  {
    cid: "mzc002006tgfqvp",
    expected_type: "106/少儿",
    expected_pay_status: "8",
    expected_positive_trailer: "0",
    expected_state_counts: { "4": 238, "8": 3 },
    expected_upload_src_counts: { "108": 240, "141": 1 },
    pinned_positive_vid: "n3122jif99n",
  },
];

function buildUrl(base, params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) {
      continue;
    }
    search.set(key, String(value));
  }
  return `${base}?${search.toString()}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchText(url, headers, options) {
  let lastError = "";
  for (let attempt = 0; attempt <= options.httpRetries; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs);
    try {
      const response = await fetch(url, {
        headers,
        signal: controller.signal,
      });
      const text = await response.text();
      clearTimeout(timer);
      return {
        http_status: response.status,
        content_type: response.headers.get("content-type") || "",
        body: text,
        transport_error: "",
      };
    } catch (error) {
      clearTimeout(timer);
      lastError = error instanceof Error ? error.message : String(error);
      if (attempt >= options.httpRetries) {
        break;
      }
      if (options.retrySleepMs > 0) {
        await sleep(options.retrySleepMs * (attempt + 1));
      }
    }
  }
  return {
    http_status: null,
    content_type: "",
    body: "",
    transport_error: lastError,
  };
}

function decodeXmlText(text) {
  return text
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function extractTagValues(xml, tag) {
  const pattern = new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, "g");
  const values = [];
  for (const match of xml.matchAll(pattern)) {
    values.push(decodeXmlText(match[1]).trim());
  }
  return values;
}

function extractFirstTag(xml, tag) {
  const values = extractTagValues(xml, tag);
  return values.length ? values[0] : "";
}

function splitCsvUnique(values) {
  const seen = new Set();
  const ordered = [];
  for (const value of values) {
    for (const part of String(value).split(",")) {
      const text = part.trim();
      if (!text || seen.has(text)) {
        continue;
      }
      seen.add(text);
      ordered.push(text);
    }
  }
  return ordered;
}

function parseApi1Cover(xml) {
  const errorno = extractFirstTag(xml, "errorno");
  const errormsg = extractFirstTag(xml, "errormsg") || extractFirstTag(xml, "error");
  return {
    errorno,
    errormsg,
    title: extractFirstTag(xml, "title"),
    type: extractFirstTag(xml, "type"),
    type_name: extractFirstTag(xml, "type_name"),
    pay_status: extractFirstTag(xml, "pay_status"),
    positive_trailer: extractFirstTag(xml, "positive_trailer"),
    video_ids: splitCsvUnique(extractTagValues(xml, "video_ids")),
  };
}

function parseJsonpBody(body) {
  const prefix = "QZOutputJson=";
  if (!body.startsWith(prefix)) {
    throw new Error("missing JSONP wrapper");
  }
  let payload = body.slice(prefix.length).trim();
  if (payload.endsWith(";")) {
    payload = payload.slice(0, -1);
  }
  return JSON.parse(payload);
}

function chunk(values, size) {
  const out = [];
  for (let index = 0; index < values.length; index += size) {
    out.push(values.slice(index, index + size));
  }
  return out;
}

function increment(counter, key) {
  const text = String(key ?? "").trim();
  counter[text] = (counter[text] || 0) + 1;
}

function orderedCounter(counter) {
  return Object.fromEntries(
    Object.entries(counter).sort(([a], [b]) => a.localeCompare(b, "en"))
  );
}

function summarizeRows(rows, pinnedPositiveVid) {
  const stateCounts = {};
  const uploadSrcCounts = {};
  let targetidNonemptyCount = 0;
  let publishDateNonemptyCount = 0;
  let firstPositiveRow = null;
  let pinnedPositiveRow = null;
  for (const row of rows) {
    const fields = row.fields && typeof row.fields === "object" ? row.fields : {};
    const vid = String(fields.vid || row.id || "").trim();
    const title = String(fields.title || "").trim();
    const state = String(fields.state || "").trim();
    const uploadSrc = String(fields.upload_src || "").trim();
    const targetid = String(fields.targetid || "").trim();
    const publishDate = String(fields.publish_date || "").trim();

    increment(stateCounts, state);
    increment(uploadSrcCounts, uploadSrc);

    if (targetid) {
      targetidNonemptyCount += 1;
    }
    if (publishDate) {
      publishDateNonemptyCount += 1;
    }

    if (!firstPositiveRow && state === "8") {
      firstPositiveRow = {
        vid,
        title,
        state,
        upload_src: uploadSrc,
        targetid,
        publish_date: publishDate,
      };
    }

    if (pinnedPositiveVid && vid === pinnedPositiveVid) {
      pinnedPositiveRow = {
        vid,
        title,
        state,
        upload_src: uploadSrc,
        targetid,
        publish_date: publishDate,
      };
    }
  }

  return {
    video_count: rows.length,
    state_counts: orderedCounter(stateCounts),
    upload_src_counts: orderedCounter(uploadSrcCounts),
    targetid_nonempty_count: targetidNonemptyCount,
    publish_date_nonempty_count: publishDateNonemptyCount,
    first_state8_row: firstPositiveRow,
    pinned_positive_row: pinnedPositiveRow,
  };
}

function buildSignature(summary) {
  return JSON.stringify(summary);
}

async function fetchCoverSummary(config, headers, options) {
  const api1Url = buildUrl(API1_URL, {
    ...API1_DEFAULTS,
    idlist: config.cid,
  });
  const api1 = await fetchText(api1Url, headers, options);
  if (!api1.body) {
    return {
      status: "error",
      transport_error: api1.transport_error,
      api1_http_status: api1.http_status,
      api1_content_type: api1.content_type,
    };
  }

  const cover = parseApi1Cover(api1.body);
  const videoIds = cover.video_ids;
  if (cover.errormsg || (cover.errorno && cover.errorno !== "0")) {
    return {
      status: "error",
      api1_http_status: api1.http_status,
      api1_content_type: api1.content_type,
      api1_errorno: cover.errorno,
      api1_errormsg: cover.errormsg,
    };
  }
  if (!videoIds.length) {
    return {
      status: "error",
      api1_http_status: api1.http_status,
      api1_content_type: api1.content_type,
      error: "API1 returned no video_ids",
    };
  }

  const rows = [];
  const batchSummaries = [];
  for (const batch of chunk(videoIds, options.batchSize)) {
    const api2Url = buildUrl(API2_URL, {
      ...API2_DEFAULTS,
      idlist: batch.join(","),
    });
    const api2 = await fetchText(api2Url, headers, options);
    if (!api2.body) {
      return {
        status: "error",
        api1_http_status: api1.http_status,
        api2_http_status: api2.http_status,
        api2_content_type: api2.content_type,
        transport_error: api2.transport_error,
      };
    }
    const payload = parseJsonpBody(api2.body);
    const results = Array.isArray(payload.results) ? payload.results : [];
    batchSummaries.push({
      request_vid_count: batch.length,
      results_count: results.length,
      errorno: String(payload.errorno ?? "").trim(),
      errormsg: String(payload.errormsg ?? "").trim(),
    });
    for (const result of results) {
      if (result && typeof result === "object") {
        rows.push(result);
      }
    }
  }

  const summary = summarizeRows(rows, config.pinned_positive_vid || "");
  return {
    status: "ok",
    api1_http_status: api1.http_status,
    api1_content_type: api1.content_type,
    title: cover.title,
    type: cover.type,
    type_name: cover.type_name,
    pay_status: cover.pay_status,
    positive_trailer: cover.positive_trailer,
    video_ids_count: videoIds.length,
    batch_count: batchSummaries.length,
    batch_summaries: batchSummaries,
    ...summary,
  };
}

function buildTakeaways(report) {
  const takeaways = [];
  for (const [cid, bucket] of Object.entries(report.covers)) {
    if (bucket.unique_signature_count === 1) {
      takeaways.push(
        `${cid} stayed environment-stable across ${report.environments_tested.length} tested environments for state/upload counts.`
      );
    } else {
      takeaways.push(
        `${cid} produced ${bucket.unique_signature_count} distinct environment signatures and still needs closer drift/error review.`
      );
    }
    if (bucket.cross_day_match_20260619 === true) {
      takeaways.push(
        `${cid} also matches the 2026-06-19 baseline state/upload distribution, so this probe adds a cross-day consistency check.`
      );
    }
  }
  return takeaways;
}

function matchBaseline(summary, baseline) {
  if (!baseline) {
    return null;
  }
  const sameState =
    JSON.stringify(summary.state_counts || {}) ===
    JSON.stringify(baseline.expected_state_counts || {});
  const sameUpload =
    JSON.stringify(summary.upload_src_counts || {}) ===
    JSON.stringify(baseline.expected_upload_src_counts || {});
  return sameState && sameUpload;
}

export async function runState8EnvironmentProbe(config = {}) {
  const options = {
    batchSize: config.batchSize || 32,
    timeoutMs: config.timeoutMs || 12000,
    httpRetries: config.httpRetries ?? 1,
    retrySleepMs: config.retrySleepMs || 500,
    includeBrowserLike: Boolean(config.includeBrowserLike),
  };

  const environments = {
    ...BASE_ENVIRONMENTS,
    ...(options.includeBrowserLike ? BROWSER_LIKE_ENVIRONMENTS : {}),
  };
  const coverConfigs = config.coverConfigs || DEFAULT_COVER_CONFIGS;

  const report = {
    generated_at: new Date().toISOString(),
    scope: "positive state=8 environment matrix for selected covers",
    environments_tested: Object.keys(environments),
    covers: {},
  };

  for (const coverConfig of coverConfigs) {
    const envResults = {};
    const signatures = [];
    for (const [envName, headers] of Object.entries(environments)) {
      const summary = await fetchCoverSummary(coverConfig, headers, options);
      envResults[envName] = summary;
      signatures.push(buildSignature(summary));
    }
    const canonicalSummary =
      envResults.pc_web_ua || envResults.mobile_h5_ua || Object.values(envResults)[0];
    report.covers[coverConfig.cid] = {
      expected_baseline_20260619: {
        expected_type: coverConfig.expected_type,
        expected_pay_status: coverConfig.expected_pay_status,
        expected_positive_trailer: coverConfig.expected_positive_trailer,
        expected_state_counts: coverConfig.expected_state_counts,
        expected_upload_src_counts: coverConfig.expected_upload_src_counts,
        pinned_positive_vid: coverConfig.pinned_positive_vid || "",
      },
      unique_signature_count: new Set(signatures).size,
      cross_day_match_20260619:
        canonicalSummary && canonicalSummary.status === "ok"
          ? matchBaseline(canonicalSummary, coverConfig)
          : null,
      environments: envResults,
    };
  }

  report.current_takeaways = buildTakeaways(report);
  return report;
}

export async function writeState8EnvironmentReport(outputPath, config = {}) {
  const report = await runState8EnvironmentProbe(config);
  await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  return report;
}
