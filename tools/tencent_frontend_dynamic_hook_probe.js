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
    bucket: "movie_single_pay6_exchange_true",
    url: "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html",
  },
  {
    bucket: "tv_season_pay6_exchange_false",
    url: "https://v.qq.com/x/cover/mzc00200whxf2zp.html",
  },
  {
    bucket: "variety_topic_pay15_targetid_uploadsrc",
    url: "https://v.qq.com/x/cover/mzc002001u873es.html",
  },
  {
    bucket: "education_coveronly_pay8_targetid_uploadsrc",
    url: "https://v.qq.com/x/cover/mzc00200bhj36oq.html",
  },
];

const DEFAULT_SYNTHETIC_TARGET_ID = "7652145698";

const INIT_HOOK_SCRIPT = `
(() => {
  const TARGET_KEYS = ["pay_status", "pay_status_exchange", "show_gift", "positive_trailer", "positive_content_id", "state", "upload_src", "uploadSrc", "targetid", "targetId", "F", "downright"];
  const TARGET_SET = new Set(TARGET_KEYS);
  const EVENT_BUS_EMIT_KEYS = ["emit", "trigger", "$emit"];
  const EVENT_BUS_LISTENER_KEYS = ["on", "once", "addListener"];
  const MAX_EVENTS = 180;
  const MAX_HITS = 160;
  const MAX_ERRORS = 20;
  const MAX_DEPTH = 5;
  const MAX_CHILDREN = 24;
  const MAX_FUNCTION_CALLS = 60;
  const MAX_RUNTIME_SCAN_DEPTH = 3;
  const MAX_RUNTIME_SCAN_CHILDREN = 80;
  const MAX_TARGETID_HINTS = 10;
  const MAX_EVENT_BUS_CALLS = 60;
  const ATTACH_IFRAME_RE = /attachIframe/i;
  const TARGETID_TEXT_RE = /targetid|targetId/i;
  const REPORT_EVENT_RE = /REQUEST_REPORT|DANMAKU_REPORT|danmaku:requestReport|danmaku:report/i;

  const state = {
    started_at_ms: 0,
    json_hits: [],
    access_events: [],
    union_snapshots: [],
    function_calls: [],
    event_bus_calls: [],
    report_listener_regs: [],
    iframe_events: [],
    synthetic_report_runs: [],
    targetid_flow_samples: [],
    errors: [],
    wrap_count: 0,
    wrapped_labels: [],
    function_wrap_count: 0,
    wrapped_function_labels: [],
    event_bus_wrap_count: 0,
    wrapped_event_bus_labels: [],
    _seen: new WeakSet(),
    _wrapped: new WeakMap(),
    _wrappedFunctions: new WeakMap(),
    _wrappedEventBusFunctions: new WeakMap(),
    _reportBusRefs: [],
    _reportBusRefIndex: new WeakMap(),
    _last_union_signature: "",
    _event_signatures: new Set(),
    _iframePatched: false,
    _runtimeScanCount: 0,
  };

  const scalar = (value) => {
    if (value === null || value === undefined) {
      return value;
    }
    if (Array.isArray(value)) {
      return { type: "array", length: value.length, head: value.slice(0, 5) };
    }
    if (typeof value === "object") {
      return { type: "object", keys: Object.keys(value).slice(0, 8) };
    }
    if (typeof value === "string" && value.length > 120) {
      return value.slice(0, 120);
    }
    return value;
  };

  const elapsed = () => {
    try {
      return Math.round(performance.now());
    } catch {
      return 0;
    }
  };

  const record = (bucket, payload, limit) => {
    const target = state[bucket];
    if (!Array.isArray(target) || target.length >= limit) {
      return;
    }
    target.push({ elapsed_ms: elapsed(), ...payload });
  };

  const recordUnique = (bucket, signature, payload, limit) => {
    if (!signature) {
      record(bucket, payload, limit);
      return;
    }
    const dedupeKey = bucket + ":" + signature;
    if (state._event_signatures.has(dedupeKey)) {
      return;
    }
    state._event_signatures.add(dedupeKey);
    record(bucket, payload, limit);
  };

  const captureStack = () => {
    try {
      throw new Error("tv_dynamic_hook_trace");
    } catch (error) {
      if (!error || typeof error.stack !== "string") {
        return [];
      }
      return error.stack
        .split("\\n")
        .slice(2, 7)
        .map((line) => line.trim())
        .filter(Boolean);
    }
  };

  const renderPreview = (value, limit = 320) => {
    try {
      const rendered = JSON.stringify(value);
      return typeof rendered === "string" ? rendered.slice(0, limit) : String(rendered).slice(0, limit);
    } catch {
      try {
        return String(value).slice(0, limit);
      } catch {
        return "[unrenderable]";
      }
    }
  };

  const rememberReportBusRef = (bus) => {
    if (!bus || (typeof bus !== "object" && typeof bus !== "function")) {
      return -1;
    }
    const existingIndex = state._reportBusRefIndex.get(bus);
    if (Number.isInteger(existingIndex)) {
      return existingIndex;
    }
    const nextIndex = state._reportBusRefs.length;
    state._reportBusRefs.push(bus);
    state._reportBusRefIndex.set(bus, nextIndex);
    return nextIndex;
  };

  const recordReportListenerReg = (bus, payload) => {
    const refIndex = rememberReportBusRef(bus);
    const eventName = String(payload && payload.event_name ? payload.event_name : "");
    const ctorName = String(payload && payload.ctor_name ? payload.ctor_name : "");
    recordUnique(
      "report_listener_regs",
      [refIndex, eventName, ctorName, payload && payload.label, payload && payload.key].join("|"),
      { ref_index: refIndex, ...payload },
      MAX_HITS
    );
    return refIndex;
  };

  const collectTargetIdHints = (value, path, depth, hints) => {
    if (!Array.isArray(hints) || hints.length >= MAX_TARGETID_HINTS || depth > 3) {
      return;
    }
    if (value === null || value === undefined) {
      return;
    }
    if (typeof value === "string") {
      if (TARGETID_TEXT_RE.test(value)) {
        hints.push({ path, value: scalar(value) });
      }
      return;
    }
    if (typeof value !== "object") {
      return;
    }
    if (Array.isArray(value)) {
      for (let index = 0; index < value.length && index < 4; index += 1) {
        collectTargetIdHints(value[index], path + "[" + index + "]", depth + 1, hints);
        if (hints.length >= MAX_TARGETID_HINTS) {
          return;
        }
      }
      return;
    }
    const keys = Object.keys(value).slice(0, 12);
    for (const key of keys) {
      let nextValue;
      try {
        nextValue = value[key];
      } catch {
        continue;
      }
      const nextPath = path ? path + "." + key : key;
      if (key === "targetid" || key === "targetId") {
        hints.push({ path: nextPath, value: scalar(nextValue) });
        if (hints.length >= MAX_TARGETID_HINTS) {
          return;
        }
      }
      if (typeof nextValue === "string" && TARGETID_TEXT_RE.test(nextValue)) {
        hints.push({ path: nextPath, value: scalar(nextValue) });
        if (hints.length >= MAX_TARGETID_HINTS) {
          return;
        }
      }
      if (nextValue && typeof nextValue === "object") {
        collectTargetIdHints(nextValue, nextPath, depth + 1, hints);
        if (hints.length >= MAX_TARGETID_HINTS) {
          return;
        }
      }
    }
  };

  const maybeRecordTargetIdFlow = (stage, label, value, extra = {}) => {
    const hints = [];
    collectTargetIdHints(value, label, 0, hints);
    if (!hints.length) {
      return hints;
    }
    recordUnique(
      "targetid_flow_samples",
      JSON.stringify({ stage, label, hints }),
      {
        stage,
        label,
        hints,
        ...extra,
      },
      MAX_HITS
    );
    return hints;
  };

  const wrapField = (obj, key, label) => {
    if (!obj || typeof obj !== "object") {
      return;
    }
    const wrappedKeys = state._wrapped.get(obj) || new Set();
    if (wrappedKeys.has(key)) {
      return;
    }
    const descriptor = Object.getOwnPropertyDescriptor(obj, key);
    if (!descriptor || !descriptor.configurable) {
      return;
    }
    if (descriptor.get || descriptor.set) {
      return;
    }
    let current = obj[key];
    try {
      Object.defineProperty(obj, key, {
        configurable: true,
        enumerable: descriptor.enumerable !== false,
        get() {
          record(
            "access_events",
            {
              kind: "get",
              label,
              key,
              value: scalar(current),
            },
            MAX_EVENTS
          );
          return current;
        },
        set(nextValue) {
          record(
            "access_events",
            {
              kind: "set",
              label,
              key,
              old_value: scalar(current),
              value: scalar(nextValue),
            },
            MAX_EVENTS
          );
          current = nextValue;
        },
      });
      wrappedKeys.add(key);
      state._wrapped.set(obj, wrappedKeys);
      state.wrap_count += 1;
      if (state.wrapped_labels.length < MAX_HITS && !state.wrapped_labels.includes(label + ":" + key)) {
        state.wrapped_labels.push(label + ":" + key);
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "wrapField",
          label,
          key,
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  };

  const wrapFunctionField = (obj, key, label) => {
    if (!obj || (typeof obj !== "object" && typeof obj !== "function")) {
      return;
    }
    const wrappedKeys = state._wrappedFunctions.get(obj) || new Set();
    if (wrappedKeys.has(key)) {
      return;
    }
    let descriptor;
    try {
      descriptor = Object.getOwnPropertyDescriptor(obj, key);
    } catch {
      return;
    }
    if (descriptor && (descriptor.get || descriptor.set)) {
      return;
    }
    if (descriptor && descriptor.configurable === false && descriptor.writable === false) {
      return;
    }
    let original;
    try {
      original = obj[key];
    } catch {
      return;
    }
    if (typeof original !== "function") {
      return;
    }
    const functionName = original.name || key;
    if (!ATTACH_IFRAME_RE.test(key) && !ATTACH_IFRAME_RE.test(functionName)) {
      return;
    }
    const wrapped = function patchedAttachIframe(...args) {
      const targetidHints = maybeRecordTargetIdFlow("attach_iframe_call", label + ":" + key, args, {
        fn_name: functionName,
        arg_count: args.length,
      });
      record(
        "function_calls",
        {
          label,
          key,
          fn_name: functionName,
          arg_count: args.length,
          args_preview: args.slice(0, 4).map((value) => scalar(value)),
          targetid_hints: targetidHints,
          stack: captureStack(),
        },
        MAX_FUNCTION_CALLS
      );
      return original.apply(this, args);
    };
    try {
      Object.defineProperty(wrapped, "name", {
        configurable: true,
        value: functionName,
      });
    } catch {}
    try {
      if (descriptor && descriptor.configurable === false) {
        obj[key] = wrapped;
      } else {
        Object.defineProperty(obj, key, {
          configurable: descriptor ? descriptor.configurable !== false : true,
          enumerable: descriptor ? descriptor.enumerable !== false : true,
          writable: descriptor ? descriptor.writable !== false : true,
          value: wrapped,
        });
      }
      wrappedKeys.add(key);
      state._wrappedFunctions.set(obj, wrappedKeys);
      state.function_wrap_count += 1;
      if (
        state.wrapped_function_labels.length < MAX_HITS &&
        !state.wrapped_function_labels.includes(label + ":" + key)
      ) {
        state.wrapped_function_labels.push(label + ":" + key);
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "wrapFunctionField",
          label,
          key,
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  };

  const wrapEventBusField = (obj, key, label) => {
    if (!obj || (typeof obj !== "object" && typeof obj !== "function")) {
      return;
    }
    const isEmitKey = EVENT_BUS_EMIT_KEYS.includes(key);
    const isListenerKey = EVENT_BUS_LISTENER_KEYS.includes(key);
    if (!isEmitKey && !isListenerKey) {
      return;
    }
    const hasListenerApi =
      typeof obj.on === "function" ||
      typeof obj.off === "function" ||
      typeof obj.once === "function" ||
      typeof obj.addListener === "function";
    if (!hasListenerApi) {
      return;
    }
    const wrappedKeys = state._wrappedEventBusFunctions.get(obj) || new Set();
    if (wrappedKeys.has(key)) {
      return;
    }
    let descriptor;
    try {
      descriptor = Object.getOwnPropertyDescriptor(obj, key);
    } catch {
      return;
    }
    if (descriptor && (descriptor.get || descriptor.set)) {
      return;
    }
    if (descriptor && descriptor.configurable === false && descriptor.writable === false) {
      return;
    }
    let original;
    try {
      original = obj[key];
    } catch {
      return;
    }
    if (typeof original !== "function") {
      return;
    }
    const wrapped = isEmitKey
      ? function patchedEventBusEmit(...args) {
          const eventName = typeof args[0] === "string" ? args[0] : scalar(args[0]);
          const payload = args.length > 1 ? args[1] : undefined;
          const renderedName = typeof eventName === "string" ? eventName : renderPreview(eventName);
          const renderedPayload = renderPreview(payload) || "";
          const targetidHints = maybeRecordTargetIdFlow("event_bus_emit", label + ":" + key, payload, {
            event_name: renderedName,
          });
          if (
            REPORT_EVENT_RE.test(renderedName || "") ||
            targetidHints.length ||
            TARGETID_TEXT_RE.test(renderedPayload)
          ) {
            record(
              "event_bus_calls",
              {
                label,
                key,
                event_name: renderedName,
                args_preview: args.slice(0, 4).map((value) => scalar(value)),
                payload_preview: renderedPayload,
                targetid_hints: targetidHints,
                stack: captureStack(),
              },
              MAX_EVENT_BUS_CALLS
            );
          }
          return original.apply(this, args);
        }
      : function patchedEventBusListener(...args) {
          const eventName = typeof args[0] === "string" ? args[0] : scalar(args[0]);
          const renderedName = typeof eventName === "string" ? eventName : renderPreview(eventName);
          const handler = args.length > 1 ? args[1] : undefined;
          if (REPORT_EVENT_RE.test(renderedName || "")) {
            recordReportListenerReg(this, {
              label,
              key,
              event_name: renderedName,
              ctor_name: this && this.constructor && this.constructor.name ? this.constructor.name : "",
              handler_uses_data: /\\.data\\./.test(renderPreview(handler, 480)),
              handler_preview: renderPreview(handler, 480),
              stack: captureStack(),
            });
          }
          return original.apply(this, args);
        };
    try {
      Object.defineProperty(wrapped, "name", {
        configurable: true,
        value: original.name || key,
      });
    } catch {}
    try {
      if (descriptor && descriptor.configurable === false) {
        obj[key] = wrapped;
      } else {
        Object.defineProperty(obj, key, {
          configurable: descriptor ? descriptor.configurable !== false : true,
          enumerable: descriptor ? descriptor.enumerable !== false : true,
          writable: descriptor ? descriptor.writable !== false : true,
          value: wrapped,
        });
      }
      wrappedKeys.add(key);
      state._wrappedEventBusFunctions.set(obj, wrappedKeys);
      state.event_bus_wrap_count += 1;
      if (
        state.wrapped_event_bus_labels.length < MAX_HITS &&
        !state.wrapped_event_bus_labels.includes(label + ":" + key)
      ) {
        state.wrapped_event_bus_labels.push(label + ":" + key);
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "wrapEventBusField",
          label,
          key,
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  };

  const visit = (obj, label, path, depth) => {
    if (!obj || typeof obj !== "object" || state._seen.has(obj) || depth > MAX_DEPTH) {
      return;
    }
    state._seen.add(obj);
    const keys = Object.keys(obj);
    const interestingKeys = keys.filter((key) => TARGET_SET.has(key));
    if (interestingKeys.length) {
      const values = {};
      for (const key of interestingKeys) {
        values[key] = scalar(obj[key]);
        wrapField(obj, key, label + ":" + path);
      }
      record(
        "json_hits",
        {
          label,
          path,
          keys: interestingKeys,
          values,
        },
        MAX_HITS
      );
    }
    const childKeys = keys.slice(0, MAX_CHILDREN);
    for (const key of childKeys) {
      let nextValue;
      try {
        nextValue = obj[key];
      } catch {
        continue;
      }
      visit(nextValue, label, path ? path + "." + key : key, depth + 1);
    }
  };

  const scanRuntimeFunctions = () => {
    const seen = new WeakSet();
    const walk = (obj, label, depth) => {
      if (!obj || (typeof obj !== "object" && typeof obj !== "function") || seen.has(obj) || depth > MAX_RUNTIME_SCAN_DEPTH) {
        return;
      }
      seen.add(obj);
      let keys = [];
      try {
        keys = Object.getOwnPropertyNames(obj);
      } catch {
        try {
          keys = Object.keys(obj);
        } catch {
          return;
        }
      }
      keys = keys.slice(0, depth === 0 ? 240 : MAX_RUNTIME_SCAN_CHILDREN);
      for (const key of keys) {
        let value;
        try {
          value = obj[key];
        } catch {
          continue;
        }
        const childLabel = label ? label + "." + key : key;
        if (typeof value === "function") {
          if (ATTACH_IFRAME_RE.test(key) || ATTACH_IFRAME_RE.test(value.name || "")) {
            wrapFunctionField(obj, key, label);
          }
          if (EVENT_BUS_EMIT_KEYS.includes(key) || EVENT_BUS_LISTENER_KEYS.includes(key)) {
            wrapEventBusField(obj, key, label);
          }
        }
        if (depth < MAX_RUNTIME_SCAN_DEPTH && value && (typeof value === "object" || typeof value === "function")) {
          walk(value, childLabel, depth + 1);
        }
      }
    };
    try {
      walk(window, "window", 0);
    } catch (error) {
      record(
        "errors",
        {
          stage: "scanRuntimeFunctions",
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  };

  const patchIframeTargetIdSinks = () => {
    if (state._iframePatched) {
      return;
    }
    const proto = window.HTMLIFrameElement && window.HTMLIFrameElement.prototype;
    if (!proto) {
      return;
    }
    state._iframePatched = true;
    try {
      const srcDescriptor = Object.getOwnPropertyDescriptor(proto, "src");
      if (srcDescriptor && typeof srcDescriptor.set === "function") {
        Object.defineProperty(proto, "src", {
          configurable: srcDescriptor.configurable !== false,
          enumerable: srcDescriptor.enumerable !== false,
          get: srcDescriptor.get,
          set(value) {
            const targetidHints = maybeRecordTargetIdFlow("iframe_src_set", "iframe.src", value);
            if (targetidHints.length) {
              record(
                "iframe_events",
                {
                  kind: "src_set",
                  value: scalar(value),
                  targetid_hints: targetidHints,
                  stack: captureStack(),
                },
                MAX_FUNCTION_CALLS
              );
            }
            return srcDescriptor.set.call(this, value);
          },
        });
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "patchIframeTargetIdSinks:src",
          error: String(error),
        },
        MAX_ERRORS
      );
    }
    try {
      const originalSetAttribute = proto.setAttribute;
      if (typeof originalSetAttribute === "function") {
        proto.setAttribute = function patchedIframeSetAttribute(name, value) {
          if (String(name).toLowerCase() === "src") {
            const targetidHints = maybeRecordTargetIdFlow("iframe_setAttribute", "iframe.setAttribute", value);
            if (targetidHints.length) {
              record(
                "iframe_events",
                {
                  kind: "setAttribute",
                  value: scalar(value),
                  targetid_hints: targetidHints,
                  stack: captureStack(),
                },
                MAX_FUNCTION_CALLS
              );
            }
          }
          return originalSetAttribute.call(this, name, value);
        };
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "patchIframeTargetIdSinks:setAttribute",
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  };

  const patchKnownEventEmitterPrototype = () => {
    const proto = window.SuperPlayer && window.SuperPlayer.EvtEmitter && window.SuperPlayer.EvtEmitter.prototype;
    if (!proto || (typeof proto !== "object" && typeof proto !== "function")) {
      return;
    }
    for (const key of EVENT_BUS_LISTENER_KEYS.concat(EVENT_BUS_EMIT_KEYS)) {
      try {
        if (typeof proto[key] === "function") {
          wrapEventBusField(proto, key, "window.SuperPlayer.EvtEmitter.prototype");
        }
      } catch {}
    }
  };

  const originalParse = JSON.parse.bind(JSON);
  JSON.parse = function patchedParse(...args) {
    const result = originalParse(...args);
    try {
      visit(result, "json_parse", "root", 0);
    } catch (error) {
      record(
        "errors",
        {
          stage: "JSON.parse",
          error: String(error),
        },
        MAX_ERRORS
      );
    }
    return result;
  };

  const pickUnionSnapshot = () => {
    const ssr = window.__vikor__context__ && window.__vikor__context__.ssrPayloads;
    const union = ssr && ssr._piniaState && ssr._piniaState.union;
    if (!union || typeof union !== "object") {
      return null;
    }
    const coverMap = union.coverInfoMap || {};
    const videoMap = union.videoInfoMap || {};
    const cid = union.initialCid || Object.keys(coverMap)[0] || "";
    const vid = union.initialVid || Object.keys(videoMap)[0] || "";
    const cover = cid ? coverMap[cid] || {} : {};
    const video = vid ? videoMap[vid] || {} : {};
    if (cover && typeof cover === "object") {
      for (const key of ["pay_status", "pay_status_exchange", "show_gift", "positive_trailer", "positive_content_id", "F", "type", "type_name", "publish_date", "downright"]) {
        if (Object.prototype.hasOwnProperty.call(cover, key)) {
          wrapField(cover, key, "union.coverInfoMap[" + cid + "]");
        }
      }
    }
    if (video && typeof video === "object") {
      for (const key of ["state", "upload_src", "targetid", "targetId", "F", "pay_status", "positive_trailer", "positive_content_id", "type", "type_name", "publish_date", "downright"]) {
        if (Object.prototype.hasOwnProperty.call(video, key)) {
          wrapField(video, key, "union.videoInfoMap[" + vid + "]");
        }
      }
    }
    return {
      cid,
      vid,
      cover_pay_status: cover ? cover.pay_status : undefined,
      pay_status_exchange: cover ? cover.pay_status_exchange : undefined,
      show_gift: cover ? cover.show_gift : undefined,
      cover_positive_trailer: cover ? cover.positive_trailer : undefined,
      cover_positive_content_id: cover ? cover.positive_content_id : undefined,
      cover_has_F: !!(cover && Object.prototype.hasOwnProperty.call(cover, "F")),
      video_state: video ? video.state : undefined,
      video_has_upload_src: !!(video && Object.prototype.hasOwnProperty.call(video, "upload_src")),
      video_upload_src: video ? video.upload_src : undefined,
      video_has_targetid: !!(video && (Object.prototype.hasOwnProperty.call(video, "targetid") || Object.prototype.hasOwnProperty.call(video, "targetId"))),
      video_targetid: video ? (video.targetId !== undefined ? video.targetId : video.targetid) : undefined,
      video_has_F: !!(video && Object.prototype.hasOwnProperty.call(video, "F")),
    };
  };

  const maybeSnapshotUnion = () => {
    const snapshot = pickUnionSnapshot();
    if (!snapshot) {
      return;
    }
    const signature = JSON.stringify(snapshot);
    if (signature !== state._last_union_signature && state.union_snapshots.length < MAX_HITS) {
      state._last_union_signature = signature;
      state.union_snapshots.push({ elapsed_ms: elapsed(), ...snapshot });
    }
  };

  state.started_at_ms = elapsed();
  maybeSnapshotUnion();
  patchIframeTargetIdSinks();
  patchKnownEventEmitterPrototype();
  scanRuntimeFunctions();
  const timer = setInterval(() => {
    try {
      maybeSnapshotUnion();
      patchKnownEventEmitterPrototype();
      const ctx = window.__vikor__context__;
      if (ctx) {
        visit(ctx, "vikor_context", "__vikor__context__", 0);
      }
      state._runtimeScanCount += 1;
      if (state._runtimeScanCount <= 20 || state._runtimeScanCount % 10 === 0) {
        scanRuntimeFunctions();
      }
    } catch (error) {
      record(
        "errors",
        {
          stage: "interval",
          error: String(error),
        },
        MAX_ERRORS
      );
    }
  }, 50);
  window.__TV_DYNAMIC_HOOK__ = state;
  window.addEventListener("beforeunload", () => clearInterval(timer), { once: true });
})();
`;

function parseArgs(argv) {
  const args = {
    cases: [],
    waitMs: 12000,
    timeoutMs: 45000,
    syntheticReportWaitMs: 1800,
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
    if (token === "--synthetic-report-wait-ms") {
      args.syntheticReportWaitMs = Number(argv[++i]);
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
  if (!Number.isFinite(args.syntheticReportWaitMs) || args.syntheticReportWaitMs < 0) {
    throw new Error("--synthetic-report-wait-ms must be a non-negative number.");
  }
  if (!Number.isFinite(args.indent) || args.indent < 0) {
    throw new Error("--indent must be a non-negative number.");
  }
  return args;
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

function distillHookState(rawHook) {
  const hook = rawHook && typeof rawHook === "object" ? rawHook : {};
  const jsonHits = Array.isArray(hook.json_hits) ? hook.json_hits : [];
  const accessEvents = Array.isArray(hook.access_events) ? hook.access_events : [];
  const unionSnapshots = Array.isArray(hook.union_snapshots) ? hook.union_snapshots : [];
  const functionCalls = Array.isArray(hook.function_calls) ? hook.function_calls : [];
  const eventBusCalls = Array.isArray(hook.event_bus_calls) ? hook.event_bus_calls : [];
  const reportListenerRegs = Array.isArray(hook.report_listener_regs) ? hook.report_listener_regs : [];
  const iframeEvents = Array.isArray(hook.iframe_events) ? hook.iframe_events : [];
  const syntheticReportRuns = Array.isArray(hook.synthetic_report_runs) ? hook.synthetic_report_runs : [];
  const targetidFlowSamples = Array.isArray(hook.targetid_flow_samples) ? hook.targetid_flow_samples : [];

  const collectValues = (key) => {
    const values = [];
    for (const hit of jsonHits) {
      const hitValues = hit && typeof hit === "object" ? hit.values : null;
      if (!hitValues || typeof hitValues !== "object") {
        continue;
      }
      const value = hitValues[key];
      if (value === undefined) {
        continue;
      }
      const rendered = JSON.stringify(value);
      if (!values.includes(rendered)) {
        values.push(rendered);
      }
    }
    return values.map((value) => {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    });
  };

  const decodeTargetIdCandidate = (value) => {
    if (typeof value !== "string" || !/^[A-Za-z0-9+/=]+$/.test(value) || value.length < 8) {
      return null;
    }
    try {
      const decoded = Buffer.from(value, "base64").toString("utf8");
      if (/^\d{6,}$/.test(decoded)) {
        return decoded;
      }
    } catch {}
    return null;
  };

  const getCounts = {};
  const setCounts = {};
  const firstEvents = [];
  const interestingSamples = {
    pay_status: [],
    pay_status_exchange: [],
    show_gift: [],
    positive_trailer: [],
    state: [],
    targetid: [],
    targetId: [],
    upload_src: [],
    F: [],
    downright: [],
  };
  for (const event of accessEvents) {
    const key = event && typeof event === "object" ? event.key : "";
    const kind = event && typeof event === "object" ? event.kind : "";
    if (!key || !kind) {
      continue;
    }
    const target = kind === "get" ? getCounts : setCounts;
    target[key] = (target[key] || 0) + 1;
    if (firstEvents.length < 18) {
      firstEvents.push(event);
    }
    if (Object.prototype.hasOwnProperty.call(interestingSamples, key)) {
      const bucket = interestingSamples[key];
      if (Array.isArray(bucket) && bucket.length < 8) {
        bucket.push(event);
      }
    }
  }

  const targetidHitSamples = jsonHits
    .filter((hit) => {
      const values = hit && typeof hit === "object" ? hit.values : null;
      return !!values && (Object.prototype.hasOwnProperty.call(values, "targetid") || Object.prototype.hasOwnProperty.call(values, "targetId"));
    })
    .slice(0, 12)
    .map((hit) => {
      const values = hit && typeof hit === "object" ? hit.values : {};
      const rawValue = values.targetId !== undefined ? values.targetId : values.targetid;
      return {
        label: hit.label,
        path: hit.path,
        keys: hit.keys,
        raw_value: rawValue,
        decoded_numeric_value: decodeTargetIdCandidate(rawValue),
      };
    });

  const decodedTargetIdValues = [];
  for (const value of collectValues("targetid").concat(collectValues("targetId"))) {
    const decoded = decodeTargetIdCandidate(value);
    if (decoded && !decodedTargetIdValues.includes(decoded)) {
      decodedTargetIdValues.push(decoded);
    }
  }

  return {
    json_hits_count: jsonHits.length,
    access_event_count: accessEvents.length,
    union_snapshot_count: unionSnapshots.length,
    function_call_count: functionCalls.length,
    event_bus_call_count: eventBusCalls.length,
    iframe_event_count: iframeEvents.length,
    targetid_flow_count: targetidFlowSamples.length,
    first_union_snapshot: unionSnapshots[0] || null,
    last_union_snapshot: unionSnapshots[unionSnapshots.length - 1] || null,
    parsed_pay_status_values: collectValues("pay_status"),
    parsed_pay_status_exchange_values: collectValues("pay_status_exchange"),
    parsed_show_gift_values: collectValues("show_gift"),
    parsed_positive_trailer_values: collectValues("positive_trailer"),
    parsed_state_values: collectValues("state"),
    parsed_targetid_values: collectValues("targetid").concat(collectValues("targetId")),
    decoded_targetid_values: decodedTargetIdValues,
    parsed_upload_src_values: collectValues("upload_src").concat(collectValues("uploadSrc")),
    parsed_F_values: collectValues("F"),
    parsed_downright_values: collectValues("downright"),
    get_counts: getCounts,
    set_counts: setCounts,
    first_access_events: firstEvents,
    interesting_event_samples: interestingSamples,
    attach_iframe_targetid_call_count: functionCalls.filter(
      (event) => Array.isArray(event?.targetid_hints) && event.targetid_hints.length > 0
    ).length,
    iframe_targetid_event_count: iframeEvents.filter(
      (event) => Array.isArray(event?.targetid_hints) && event.targetid_hints.length > 0
    ).length,
    report_event_call_count: eventBusCalls.filter((event) =>
      /REQUEST_REPORT|DANMAKU_REPORT|danmaku:requestReport|danmaku:report/i.test(
        String(event?.event_name || "")
      )
    ).length,
    report_listener_reg_count: reportListenerRegs.length,
    first_function_calls: functionCalls.slice(0, 8),
    first_event_bus_calls: eventBusCalls.slice(0, 8),
    report_listener_regs: reportListenerRegs.slice(0, 8),
    iframe_event_samples: iframeEvents.slice(0, 8),
    synthetic_report_run_count: syntheticReportRuns.length,
    synthetic_report_runs: syntheticReportRuns.slice(0, 8),
    targetid_hit_samples: targetidHitSamples,
    targetid_flow_samples: targetidFlowSamples.slice(0, 8),
    function_wrap_count: Number.isFinite(hook.function_wrap_count) ? hook.function_wrap_count : 0,
    wrapped_function_labels: Array.isArray(hook.wrapped_function_labels)
      ? hook.wrapped_function_labels.slice(0, 24)
      : [],
    event_bus_wrap_count: Number.isFinite(hook.event_bus_wrap_count) ? hook.event_bus_wrap_count : 0,
    wrapped_event_bus_labels: Array.isArray(hook.wrapped_event_bus_labels)
      ? hook.wrapped_event_bus_labels.slice(0, 24)
      : [],
  };
}

function buildPageTakeaways(summary) {
  const takeaways = [];
  const first = summary.first_union_snapshot || {};
  if (first.cover_pay_status !== undefined) {
    takeaways.push(
      `first exposed union cover pay_status was already ${JSON.stringify(first.cover_pay_status)}`
    );
  }
  if ((summary.parsed_pay_status_values || []).length) {
    takeaways.push(
      `JSON.parse saw pay_status values ${summary.parsed_pay_status_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_upload_src_values || []).length) {
    takeaways.push(
      `JSON.parse saw upload_src values ${summary.parsed_upload_src_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_targetid_values || []).length) {
    takeaways.push(
      `JSON.parse saw targetId/targetid values ${summary.parsed_targetid_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.decoded_targetid_values || []).length) {
    takeaways.push(
      `base64-like targetId/targetid samples decode to numeric strings ${summary.decoded_targetid_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_F_values || []).length) {
    takeaways.push(
      `JSON.parse saw F values ${summary.parsed_F_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_pay_status_exchange_values || []).length) {
    takeaways.push(
      `JSON.parse saw pay_status_exchange values ${summary.parsed_pay_status_exchange_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_show_gift_values || []).length) {
    takeaways.push(
      `JSON.parse saw show_gift values ${summary.parsed_show_gift_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.parsed_downright_values || []).length) {
    takeaways.push(
      `JSON.parse saw downright values ${summary.parsed_downright_values
        .map((value) => JSON.stringify(value))
        .join(", ")}`
    );
  }
  if ((summary.get_counts && summary.get_counts.pay_status) || 0) {
    takeaways.push(`logged ${summary.get_counts.pay_status} runtime get(s) on pay_status`);
  }
  if ((summary.get_counts && summary.get_counts.pay_status_exchange) || 0) {
    takeaways.push(
      `logged ${summary.get_counts.pay_status_exchange} runtime get(s) on pay_status_exchange`
    );
  }
  if ((summary.get_counts && summary.get_counts.targetId) || 0 || (summary.get_counts && summary.get_counts.targetid) || 0) {
    const count = (summary.get_counts.targetId || 0) + (summary.get_counts.targetid || 0);
    takeaways.push(`logged ${count} runtime get(s) on targetId/targetid`);
  }
  if ((summary.attach_iframe_targetid_call_count || 0) > 0) {
    takeaways.push(
      `captured ${summary.attach_iframe_targetid_call_count} attachIframe-like call(s) carrying targetId/targetid hints`
    );
  } else if ((summary.function_call_count || 0) > 0) {
    takeaways.push(
      `wrapped attachIframe-like runtime function(s) and captured ${summary.function_call_count} call(s), but none exposed targetId/targetid hints`
    );
  }
  if ((summary.iframe_targetid_event_count || 0) > 0) {
    takeaways.push(
      `captured ${summary.iframe_targetid_event_count} iframe src handoff event(s) carrying targetId/targetid hints`
    );
  }
  if ((summary.report_event_call_count || 0) > 0) {
    takeaways.push(
      `captured ${summary.report_event_call_count} report-related event-bus emit call(s)`
    );
  }
  if ((summary.report_listener_reg_count || 0) > 0) {
    takeaways.push(
      `registered ${summary.report_listener_reg_count} report-related listener binding(s)`
    );
  }
  if ((summary.synthetic_report_run_count || 0) > 0) {
    takeaways.push(`recorded ${summary.synthetic_report_run_count} synthetic report probe run(s)`);
  }
  if ((summary.get_counts && summary.get_counts.upload_src) || 0) {
    takeaways.push(`logged ${summary.get_counts.upload_src} runtime get(s) on upload_src`);
  }
  if ((summary.get_counts && summary.get_counts.F) || 0) {
    takeaways.push(`logged ${summary.get_counts.F} runtime get(s) on F`);
  }
  if ((summary.get_counts && summary.get_counts.downright) || 0) {
    takeaways.push(`logged ${summary.get_counts.downright} runtime get(s) on downright`);
  }
  if (!takeaways.length) {
    takeaways.push("No target-field parse or access signal was captured.");
  }
  return takeaways;
}

function buildSyntheticReportTakeaways(probe) {
  const target = probe && typeof probe === "object" ? probe : {};
  const cases = Array.isArray(target.cases) ? target.cases : [];
  const takeaways = [];
  if (!target.attempted) {
    return takeaways;
  }
  if (target.chosen_bus_ctor) {
    takeaways.push(
      `synthetic DANMAKU_REPORT probe targeted ${target.chosen_bus_ctor} with ${target.candidate_count || 0} candidate bus ref(s)`
    );
  }
  const rawPresent = cases.find((item) => item && item.shape === "raw_present");
  const nestedPresent = cases.find((item) => item && item.shape === "nested_present");
  if (rawPresent && rawPresent.popup_contains_expected_id && rawPresent.popup_contains_expected_targetid) {
    takeaways.push("synthetic raw DANMAKU_REPORT payload propagated both id and targetId into the report popup URL");
  } else if (rawPresent && rawPresent.last_popup_src) {
    takeaways.push(`synthetic raw DANMAKU_REPORT payload ended at ${JSON.stringify(rawPresent.last_popup_src)}`);
  }
  if (nestedPresent && nestedPresent.last_popup_src) {
    takeaways.push(`synthetic nested DANMAKU_REPORT payload ended at ${JSON.stringify(nestedPresent.last_popup_src)}`);
  }
  return takeaways;
}

async function inspectCase(browser, testCase, options) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  try {
    await page.addInitScript({ content: INIT_HOOK_SCRIPT });
    await page.goto(testCase.url, {
      waitUntil: "domcontentloaded",
      timeout: options.timeoutMs,
    });
    if (options.waitMs > 0) {
      await page.waitForTimeout(options.waitMs);
    }
    const result = await page.evaluate(async (probeConfig) => {
      const hook = window.__TV_DYNAMIC_HOOK__ || null;
      const union = window.__vikor__context__?.ssrPayloads?._piniaState?.union || {};
      const coverMap = union.coverInfoMap || {};
      const videoMap = union.videoInfoMap || {};
      const cid = union.initialCid || Object.keys(coverMap)[0] || "";
      const vid = union.initialVid || Object.keys(videoMap)[0] || "";
      const cover = cid ? coverMap[cid] || {} : {};
      const video = vid ? videoMap[vid] || {} : {};
      const domNodes = Array.from(
        document.querySelectorAll("button, a, [role='button'], .btn, .button, .tag, .badge, .label")
      )
        .map((node) => {
          const text = (node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
          const rect = typeof node.getBoundingClientRect === "function" ? node.getBoundingClientRect() : null;
          const visible =
            !!text &&
            !!rect &&
            rect.width > 0 &&
            rect.height > 0 &&
            rect.bottom >= 0 &&
            rect.right >= 0;
          return visible
            ? {
                tag: node.tagName,
                text: text.slice(0, 48),
                className: (node.className || "").toString().slice(0, 120),
                href: node.tagName === "A" ? (node.getAttribute("href") || "") : "",
              }
            : null;
        })
        .filter(Boolean);
      const visibleTexts = [];
      const matchedNodes = [];
      for (const node of domNodes) {
        if (!node || !node.text) {
          continue;
        }
        if (!visibleTexts.includes(node.text) && visibleTexts.length < 24) {
          visibleTexts.push(node.text);
        }
        if (matchedNodes.length < 16) {
          matchedNodes.push(node);
        }
      }
      const joinedTexts = visibleTexts.join(" | ");
      const hasByRegex = (pattern) => pattern.test(joinedTexts);
      const domSnapshot = {
        visible_button_texts: visibleTexts,
        matched_nodes: matchedNodes,
        has_vip_cta: hasByRegex(/VIP|会员|开通|续费|解锁|付费/),
        has_try_watch_cta: hasByRegex(/试看|抢先看|预告/),
        has_trailer_badge: hasByRegex(/预告|抢先看/),
        has_download_entry: hasByRegex(/下载|缓存/),
        has_gift_entry: hasByRegex(/赠|礼包|送礼|礼物/),
      };
      const collectReportPopupSrcs = () =>
        Array.from(document.querySelectorAll("iframe"))
          .map((node) => {
            try {
              return node.getAttribute("src") || node.src || "";
            } catch {
              return "";
            }
          })
          .filter((value) => typeof value === "string" && /video-report-h5|reportType=5/i.test(value));
      const diffList = (beforeList, afterList) => {
        const counts = new Map();
        for (const value of beforeList) {
          counts.set(value, (counts.get(value) || 0) + 1);
        }
        const delta = [];
        for (const value of afterList) {
          const remaining = counts.get(value) || 0;
          if (remaining > 0) {
            counts.set(value, remaining - 1);
          } else if (delta.length < 12) {
            delta.push(value);
          }
        }
        return delta;
      };
      const syntheticReportProbe = {
        attempted: false,
        candidate_count: 0,
        chosen_bus_index: null,
        chosen_bus_ctor: null,
        listener_events: [],
        before_popup_srcs: [],
        cases: [],
        errors: [],
      };
      if (hook) {
        const reportRegs = Array.isArray(hook.report_listener_regs) ? hook.report_listener_regs : [];
        const busRefs = Array.isArray(hook._reportBusRefs) ? hook._reportBusRefs : [];
        const listenerCandidates = [];
        const seenRefIndices = new Set();
        for (const reg of reportRegs) {
          const refIndex = Number.isInteger(reg?.ref_index) ? reg.ref_index : -1;
          if (refIndex < 0 || seenRefIndices.has(refIndex)) {
            continue;
          }
          const bus = busRefs[refIndex];
          if (!bus || typeof bus.emit !== "function") {
            continue;
          }
          seenRefIndices.add(refIndex);
          listenerCandidates.push({
            ref_index: refIndex,
            bus,
            ctor_name: String(reg?.ctor_name || bus?.constructor?.name || ""),
            event_names: reportRegs
              .filter((entry) => entry?.ref_index === refIndex)
              .map((entry) => String(entry?.event_name || ""))
              .filter(Boolean),
          });
        }
        syntheticReportProbe.attempted = true;
        syntheticReportProbe.candidate_count = listenerCandidates.length;
        const chosenCandidate =
          listenerCandidates.find(
            (entry) =>
              entry.event_names.some((name) => /DANMAKU_REPORT/i.test(name)) &&
              /Dte/i.test(entry.ctor_name || "")
          ) ||
          listenerCandidates.find((entry) => entry.event_names.some((name) => /DANMAKU_REPORT/i.test(name))) ||
          listenerCandidates[0] ||
          null;
        if (chosenCandidate) {
          syntheticReportProbe.chosen_bus_index = chosenCandidate.ref_index;
          syntheticReportProbe.chosen_bus_ctor = chosenCandidate.ctor_name || null;
          syntheticReportProbe.listener_events = chosenCandidate.event_names.slice(0, 12);
          syntheticReportProbe.before_popup_srcs = collectReportPopupSrcs().slice(0, 12);
          const syntheticTargetId =
            typeof probeConfig?.targetId === "string" && probeConfig.targetId
              ? probeConfig.targetId
              : "7652145698";
          const syntheticWaitMs =
            Number.isFinite(probeConfig?.waitMs) && probeConfig.waitMs >= 0 ? probeConfig.waitMs : 1800;
          const cases = [
            { shape: "raw_missing", payload: { id: "synthetic_raw_missing" } },
            { shape: "raw_present", payload: { id: "synthetic_raw_present", targetId: syntheticTargetId } },
            {
              shape: "nested_present",
              payload: { data: { id: "synthetic_nested_present", targetId: syntheticTargetId } },
            },
          ];
          for (const entry of cases) {
            const beforePopupSrcs = collectReportPopupSrcs();
            const beforeIframeEventCount = Array.isArray(hook.iframe_events) ? hook.iframe_events.length : 0;
            const beforeEventBusCallCount = Array.isArray(hook.event_bus_calls) ? hook.event_bus_calls.length : 0;
            let emitError = null;
            try {
              chosenCandidate.bus.emit("DANMAKU_REPORT", entry.payload);
            } catch (error) {
              emitError = String(error);
            }
            await new Promise((resolve) => setTimeout(resolve, syntheticWaitMs));
            const afterPopupSrcs = collectReportPopupSrcs();
            const newIframeEvents = (Array.isArray(hook.iframe_events) ? hook.iframe_events : []).slice(
              beforeIframeEventCount
            );
            const newEventBusCalls = (Array.isArray(hook.event_bus_calls) ? hook.event_bus_calls : []).slice(
              beforeEventBusCallCount
            );
            const caseResult = {
              shape: entry.shape,
              payload_preview: JSON.stringify(entry.payload),
              emit_error: emitError,
              after_popup_srcs: afterPopupSrcs.slice(0, 12),
              new_popup_srcs: diffList(beforePopupSrcs, afterPopupSrcs),
              last_popup_src: afterPopupSrcs[afterPopupSrcs.length - 1] || null,
              matched_event_bus_calls: newEventBusCalls
                .filter((event) => /DANMAKU_REPORT/i.test(String(event?.event_name || "")))
                .slice(0, 6),
              matched_iframe_events: newIframeEvents
                .filter((event) => /video-report-h5|reportType=5/i.test(String(event?.value || "")))
                .slice(0, 6),
              popup_contains_expected_id: afterPopupSrcs.some((value) =>
                value.includes(`id=${entry.shape === "nested_present" ? "synthetic_nested_present" : entry.shape === "raw_present" ? "synthetic_raw_present" : "synthetic_raw_missing"}`)
              ),
              popup_contains_expected_targetid: afterPopupSrcs.some((value) =>
                value.includes(`targetid=${syntheticTargetId}`)
              ),
            };
            syntheticReportProbe.cases.push(caseResult);
            if (Array.isArray(hook.synthetic_report_runs) && hook.synthetic_report_runs.length < 12) {
              hook.synthetic_report_runs.push(caseResult);
            }
          }
        } else {
          syntheticReportProbe.errors.push("No report listener bus candidate exposed through listener registry.");
        }
      }
      return {
        final_url: location.href,
        title: document.title,
        cid,
        vid,
        exposed_union_snapshot: {
          cover_pay_status: cover.pay_status,
          pay_status_exchange: cover.pay_status_exchange,
          show_gift: cover.show_gift,
          cover_positive_trailer: cover.positive_trailer,
          cover_positive_content_id: cover.positive_content_id,
          cover_downright: Array.isArray(cover.downright) ? cover.downright.slice(0, 12) : cover.downright,
          cover_has_F: Object.prototype.hasOwnProperty.call(cover, "F"),
          video_state: video.state,
          video_has_upload_src: Object.prototype.hasOwnProperty.call(video, "upload_src"),
          video_upload_src: video.upload_src,
          video_has_targetid:
            Object.prototype.hasOwnProperty.call(video, "targetid") ||
            Object.prototype.hasOwnProperty.call(video, "targetId"),
          video_targetid: video.targetId !== undefined ? video.targetId : video.targetid,
          video_downright: Array.isArray(video.downright) ? video.downright.slice(0, 12) : video.downright,
          video_has_F: Object.prototype.hasOwnProperty.call(video, "F"),
        },
        dom_snapshot: domSnapshot,
        hook_state: hook
          ? {
              started_at_ms: hook.started_at_ms,
              json_hits: hook.json_hits,
              access_events: hook.access_events,
              union_snapshots: hook.union_snapshots,
              function_calls: hook.function_calls,
              event_bus_calls: hook.event_bus_calls,
              report_listener_regs: hook.report_listener_regs,
              iframe_events: hook.iframe_events,
              synthetic_report_runs: hook.synthetic_report_runs,
              targetid_flow_samples: hook.targetid_flow_samples,
              errors: hook.errors,
              wrap_count: hook.wrap_count,
              wrapped_labels: hook.wrapped_labels,
              function_wrap_count: hook.function_wrap_count,
              wrapped_function_labels: hook.wrapped_function_labels,
              event_bus_wrap_count: hook.event_bus_wrap_count,
              wrapped_event_bus_labels: hook.wrapped_event_bus_labels,
            }
          : null,
        synthetic_report_probe: syntheticReportProbe,
      };
    }, {
      targetId:
        typeof testCase.syntheticTargetId === "string" && testCase.syntheticTargetId
          ? testCase.syntheticTargetId
          : DEFAULT_SYNTHETIC_TARGET_ID,
      waitMs: Number.isFinite(options.syntheticReportWaitMs) ? options.syntheticReportWaitMs : 1800,
    });
    const hookSummary = distillHookState(result.hook_state);
    return {
      bucket: testCase.bucket,
      input_url: testCase.url,
      final_url: result.final_url,
      title: result.title,
      cid: result.cid,
      vid: result.vid,
      exposed_union_snapshot: result.exposed_union_snapshot,
      dom_snapshot: result.dom_snapshot,
      hook_summary: hookSummary,
      synthetic_report_probe: result.synthetic_report_probe,
      current_takeaways: buildPageTakeaways(hookSummary).concat(
        buildSyntheticReportTakeaways(result.synthetic_report_probe)
      ),
    };
  } finally {
    await page.close();
  }
}

function buildCrossPageTakeaways(pages) {
  const takeaways = [];
  const firstUnionValues = [];
  const parsedPayStatusValues = new Set();
  const targetReadBuckets = [];
  const attachIframeBuckets = [];
  const iframeTargetBuckets = [];
  const reportListenerBuckets = [];
  const syntheticRawSuccessBuckets = [];
  const syntheticNestedSuccessBuckets = [];
  const uploadReadBuckets = [];
  const fReadBuckets = [];
  const vipCtaBuckets = [];
  const downloadBuckets = [];
  const trailerBadgeBuckets = [];

  for (const page of pages) {
    const first = page.hook_summary?.first_union_snapshot;
    if (first && first.cover_pay_status !== undefined) {
      const rendered = JSON.stringify(first.cover_pay_status);
      if (!firstUnionValues.includes(rendered)) {
        firstUnionValues.push(rendered);
      }
    }
    for (const value of page.hook_summary?.parsed_pay_status_values || []) {
      parsedPayStatusValues.add(JSON.stringify(value));
    }
    const getCounts = page.hook_summary?.get_counts || {};
    if ((getCounts.targetId || 0) + (getCounts.targetid || 0) > 0) {
      targetReadBuckets.push(page.bucket);
    }
    if ((page.hook_summary?.attach_iframe_targetid_call_count || 0) > 0) {
      attachIframeBuckets.push(page.bucket);
    }
    if ((page.hook_summary?.iframe_targetid_event_count || 0) > 0) {
      iframeTargetBuckets.push(page.bucket);
    }
    if ((page.hook_summary?.report_listener_reg_count || 0) > 0) {
      reportListenerBuckets.push(page.bucket);
    }
    const syntheticCases = Array.isArray(page.synthetic_report_probe?.cases) ? page.synthetic_report_probe.cases : [];
    const rawPresent = syntheticCases.find((entry) => entry && entry.shape === "raw_present");
    const nestedPresent = syntheticCases.find((entry) => entry && entry.shape === "nested_present");
    if (rawPresent?.popup_contains_expected_id && rawPresent?.popup_contains_expected_targetid) {
      syntheticRawSuccessBuckets.push(page.bucket);
    }
    if (nestedPresent?.popup_contains_expected_id && nestedPresent?.popup_contains_expected_targetid) {
      syntheticNestedSuccessBuckets.push(page.bucket);
    }
    if ((getCounts.upload_src || 0) > 0) {
      uploadReadBuckets.push(page.bucket);
    }
    if ((getCounts.F || 0) > 0) {
      fReadBuckets.push(page.bucket);
    }
    const dom = page.dom_snapshot || {};
    if (dom.has_vip_cta) {
      vipCtaBuckets.push(page.bucket);
    }
    if (dom.has_download_entry) {
      downloadBuckets.push(page.bucket);
    }
    if (dom.has_trailer_badge) {
      trailerBadgeBuckets.push(page.bucket);
    }
  }

  if (firstUnionValues.length) {
    takeaways.push(
      `First observed exposed union pay_status values: ${firstUnionValues.join(", ")}.`
    );
  }
  if (parsedPayStatusValues.size) {
    takeaways.push(
      `JSON.parse still saw raw pay_status-like values: ${Array.from(parsedPayStatusValues).join(", ")}.`
    );
  }
  if (targetReadBuckets.length) {
    takeaways.push(`Runtime getter access on targetId/targetid was captured on: ${targetReadBuckets.join(", ")}.`);
  } else {
    takeaways.push("No runtime getter access on targetId/targetid was captured in this round.");
  }
  if (attachIframeBuckets.length) {
    takeaways.push(`attachIframe-like callsites carrying targetId/targetid hints were captured on: ${attachIframeBuckets.join(", ")}.`);
  } else {
    takeaways.push("No attachIframe-like callsite carrying targetId/targetid hints was captured in this round.");
  }
  if (iframeTargetBuckets.length) {
    takeaways.push(`iframe src handoff carrying targetId/targetid hints was captured on: ${iframeTargetBuckets.join(", ")}.`);
  } else {
    takeaways.push("No iframe src handoff carrying targetId/targetid hints was captured in this round.");
  }
  if (reportListenerBuckets.length) {
    takeaways.push(`Report-related listener registration was captured on: ${reportListenerBuckets.join(", ")}.`);
  }
  if (syntheticRawSuccessBuckets.length) {
    takeaways.push(
      `Synthetic raw DANMAKU_REPORT payload propagated id+targetId into report popup URLs on: ${syntheticRawSuccessBuckets.join(", ")}.`
    );
  }
  if (syntheticNestedSuccessBuckets.length) {
    takeaways.push(
      `Synthetic nested DANMAKU_REPORT payload propagated id+targetId into report popup URLs on: ${syntheticNestedSuccessBuckets.join(", ")}.`
    );
  }
  if (uploadReadBuckets.length) {
    takeaways.push(`Runtime getter access on upload_src was captured on: ${uploadReadBuckets.join(", ")}.`);
  } else {
    takeaways.push("No runtime getter access on upload_src was captured in this round.");
  }
  if (fReadBuckets.length) {
    takeaways.push(`Runtime getter access on F was captured on: ${fReadBuckets.join(", ")}.`);
  } else {
    takeaways.push("No runtime getter access on F was captured in this round.");
  }
  if (vipCtaBuckets.length) {
    takeaways.push(`Visible VIP-style CTA text was captured on: ${vipCtaBuckets.join(", ")}.`);
  }
  if (downloadBuckets.length) {
    takeaways.push(`Visible download/cache entry text was captured on: ${downloadBuckets.join(", ")}.`);
  }
  if (trailerBadgeBuckets.length) {
    takeaways.push(`Visible trailer/try-watch style text was captured on: ${trailerBadgeBuckets.join(", ")}.`);
  }
  return takeaways;
}

export async function runProbe(options = {}) {
  const cases = Array.isArray(options.cases) && options.cases.length ? options.cases : DEFAULT_CASES;
  const waitMs = Number.isFinite(options.waitMs) ? options.waitMs : 12000;
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 45000;
  const syntheticReportWaitMs = Number.isFinite(options.syntheticReportWaitMs)
    ? options.syntheticReportWaitMs
    : 1800;
  const browserPath = await resolveBrowserPath(options.browserPath || "");
  const playwright = await loadPlaywright();
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath,
  });
  const pages = [];
  try {
    for (const testCase of cases) {
      try {
        pages.push(await inspectCase(browser, testCase, { waitMs, timeoutMs, syntheticReportWaitMs }));
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
  const okPages = pages.filter((page) => !page.error);
  return {
    generated_at: new Date().toISOString(),
    scope: "browser-level dynamic hook on JSON.parse, exposed union store field access, and targetId handoff into attachIframe-like / iframe sinks",
    method: {
      browser: "system Chrome via Playwright",
      browser_executable: browserPath,
      wait_ms_after_domcontentloaded: waitMs,
      hook_targets: [
        "JSON.parse result objects",
        "window.__vikor__context__.ssrPayloads._piniaState.union.coverInfoMap",
        "window.__vikor__context__.ssrPayloads._piniaState.union.videoInfoMap",
        "attachIframe-like runtime function calls that carry targetId/targetid",
        "iframe src writes that carry targetId/targetid",
      ],
      cases,
    },
    pages,
    cross_page_takeaways: buildCrossPageTakeaways(okPages),
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
if (proc && Array.isArray(proc.argv) && proc.argv[1] && proc.argv[1].endsWith("tencent_frontend_dynamic_hook_probe.js")) {
  cliMain(proc.argv.slice(2)).catch((error) => {
    const rendered = error instanceof Error ? error.stack || error.message : String(error);
    if (proc && proc.stderr) {
      proc.stderr.write(rendered + "\\n");
    }
    if (proc) {
      proc.exitCode = 1;
    }
  });
}
