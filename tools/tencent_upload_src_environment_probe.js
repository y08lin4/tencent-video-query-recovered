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
    cid: "mzc00200s6oqemg",
    label: "pure_2048_positive_a",
    expected_type: "111",
    expected_pay_status: "7",
    expected_positive_trailer: "0",
    expected_upload_src_counts: { "2048": 7 },
    expected_state_counts: { "4": 7 },
    expected_targetid_nonempty_count: 7,
  },
  {
    cid: "mzc00200ua6uec2",
    label: "pure_2048_positive_b",
    expected_type: "111",
    expected_pay_status: "7",
    expected_positive_trailer: "0",
    expected_upload_src_counts: { "2048": 7 },
    expected_state_counts: { "4": 7 },
    expected_targetid_nonempty_count: 7,
  },
  {
    cid: "mzc002008tghx9y",
    label: "mixed_2048_108_cover",
    expected_type: "111",
    expected_upload_src_counts: { "108": 2, "2048": 21 },
  },
  {
    cid: "mzc00200rcuv1sy",
    label: "same_type_negative_control_a",
    expected_type: "111",
    expected_upload_src_counts: { "0": 7 },
  },
  {
    cid: "mzc00200l0svlgo",
    label: "same_type_negative_control_b",
    expected_type: "111",
    expected_upload_src_counts: { "0": 7 },
  },
  {
    cid: "mzc00200q9c4iok",
    label: "same_type_negative_control_c",
    expected_type: "111",
    expected_upload_src_counts: { "0": 7 },
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
      const response = await fetch(url, { headers, signal: controller.signal });
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

function summarizeRows(rows) {
  const stateCounts = {};
  const uploadSrcCounts = {};
  let targetidNonemptyCount = 0;
  let publishDateNonemptyCount = 0;
  const unusualUploadExamples = [];
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
    if (uploadSrc && unusualUploadExamples.length < 12) {
      unusualUploadExamples.push({ vid, title, upload_src: uploadSrc, state, targetid });
    }
  }
  return {
    video_count: rows.length,
    state_counts: orderedCounter(stateCounts),
    upload_src_counts: orderedCounter(uploadSrcCounts),
    targetid_nonempty_count: targetidNonemptyCount,
    publish_date_nonempty_count: publishDateNonemptyCount,
    unusual_upload_examples: unusualUploadExamples,
  };
}

function matchBaseline(summary, config) {
  const pieces = [];
  if (config.expected_upload_src_counts) {
    pieces.push(
      JSON.stringify(summary.upload_src_counts || {}) ===
        JSON.stringify(config.expected_upload_src_counts)
    );
  }
  if (config.expected_state_counts) {
    pieces.push(
      JSON.stringify(summary.state_counts || {}) ===
        JSON.stringify(config.expected_state_counts)
    );
  }
  if (typeof config.expected_targetid_nonempty_count === "number") {
    pieces.push(summary.targetid_nonempty_count === config.expected_targetid_nonempty_count);
  }
  return pieces.length ? pieces.every(Boolean) : null;
}

async function fetchCoverSummary(config, headers, options) {
  const api1Url = buildUrl(API1_URL, { ...API1_DEFAULTS, idlist: config.cid });
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
  if (cover.errormsg || (cover.errorno && cover.errorno !== "0")) {
    return {
      status: "error",
      api1_http_status: api1.http_status,
      api1_content_type: api1.content_type,
      api1_errorno: cover.errorno,
      api1_errormsg: cover.errormsg,
    };
  }
  if (!cover.video_ids.length) {
    return {
      status: "error",
      api1_http_status: api1.http_status,
      api1_content_type: api1.content_type,
      error: "API1 returned no video_ids",
    };
  }

  const rows = [];
  for (const batch of chunk(cover.video_ids, options.batchSize)) {
    const api2Url = buildUrl(API2_URL, { ...API2_DEFAULTS, idlist: batch.join(",") });
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
    for (const result of results) {
      if (result && typeof result === "object") {
        rows.push(result);
      }
    }
  }

  return {
    status: "ok",
    api1_http_status: api1.http_status,
    title: cover.title,
    type: cover.type,
    type_name: cover.type_name,
    pay_status: cover.pay_status,
    positive_trailer: cover.positive_trailer,
    video_ids_count: cover.video_ids.length,
    ...summarizeRows(rows),
  };
}

function buildTakeaways(report) {
  const out = [];
  for (const [cid, bucket] of Object.entries(report.covers)) {
    if (bucket.unique_signature_count === 1) {
      out.push(`${cid} stayed environment-stable across ${report.environments_tested.length} tested environments.`);
    } else {
      out.push(`${cid} produced ${bucket.unique_signature_count} distinct environment signatures.`);
    }
    if (bucket.baseline_match === true) {
      out.push(`${cid} matched its expected upload/state baseline under the canonical environment.`);
    }
  }
  return out;
}

export async function runUploadSrcEnvironmentProbe(config = {}) {
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
    scope: "upload_src=2048 environment matrix for pure positive, mixed, and same-type negative covers",
    environments_tested: Object.keys(environments),
    covers: {},
  };

  for (const coverConfig of coverConfigs) {
    const envResults = {};
    const signatures = [];
    for (const [envName, headers] of Object.entries(environments)) {
      const summary = await fetchCoverSummary(coverConfig, headers, options);
      envResults[envName] = summary;
      signatures.push(JSON.stringify(summary));
    }
    const canonical = envResults.pc_web_ua || Object.values(envResults)[0];
    report.covers[coverConfig.cid] = {
      label: coverConfig.label,
      expected_baseline: {
        expected_type: coverConfig.expected_type || "",
        expected_pay_status: coverConfig.expected_pay_status || "",
        expected_positive_trailer: coverConfig.expected_positive_trailer || "",
        expected_upload_src_counts: coverConfig.expected_upload_src_counts || null,
        expected_state_counts: coverConfig.expected_state_counts || null,
        expected_targetid_nonempty_count:
          typeof coverConfig.expected_targetid_nonempty_count === "number"
            ? coverConfig.expected_targetid_nonempty_count
            : null,
      },
      unique_signature_count: new Set(signatures).size,
      baseline_match:
        canonical && canonical.status === "ok" ? matchBaseline(canonical, coverConfig) : null,
      environments: envResults,
    };
  }

  report.current_takeaways = buildTakeaways(report);
  return report;
}

export async function writeUploadSrcEnvironmentReport(outputPath, config = {}) {
  const report = await runUploadSrcEnvironmentProbe(config);
  await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  return report;
}
