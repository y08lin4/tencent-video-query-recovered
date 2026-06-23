# 腾讯视频接口直接调用手册

这份手册只做一件事：把当前仓库里已经坐实的匿名直连能力，整理成最短可执行路径。

它不替代完整研究台账，重点是：

- 我现在手里有 `URL / CID / VID` 时该怎么调
- 什么时候该走 API1，什么时候该走 API2
- 哪些默认值最稳
- 哪些结论只在当前匿名 direct-call scope 下成立

## 0. 先看这些

- 参数 quick reference：
  [analysis/parameter_contract_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_contract_quick_reference_20260621.json)
- 参数总表增强版：
  [analysis/direct_call_parameter_total_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_parameter_total_table_20260621.json)
- 原生直调矩阵：
  [analysis/direct_call_raw_http_matrix_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_matrix_20260621.json)
- 原生直调 live validation：
  [analysis/direct_call_raw_http_validation_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_20260621.json)
- API1 `tid=537` 独立 raw probe validation：
  [analysis/direct_call_raw_http_validation_tid537_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_tid537_20260622.json)
- API1 `tid=453` 独立 raw validation：
  [analysis/direct_call_raw_http_validation_tid453_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_tid453_20260623.json)
- API1 `tid=483` 独立 raw validation：
  [analysis/direct_call_raw_http_validation_tid483_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_tid483_20260623.json)
- API2 `tid=506` 独立 raw validation：
  [analysis/direct_call_raw_http_validation_api2_tid506_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_api2_tid506_20260623.json)
- 能力 quick reference：
  [analysis/capability_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_quick_reference_20260621.json)
- 能力总表增强版：
  [analysis/direct_call_capability_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_capability_table_20260621.json)
- 回归样本：
  [analysis/regression_samples_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/regression_samples_20260620.json)
- 如果你准备补 aged/login 环境闭环，直接再看：
  [docs/environment_replay_runbook.md](C:/Users/lin/Documents/YM查询工具还原/docs/environment_replay_runbook.md)

如果你想把当前公开 Python/Go demo surface 整体重跑一遍，不想手敲每条命令，直接用：

```bash
python tools/tencent_demo_validation_runner.py --output analysis/demo_validation_rerun_local.json --strict
```

它当前覆盖的是：

- canonical `CID -> API1 -> API2 XML`
- API1 `tid=453/483/537` 非 canonical caller-facing shells
- API2 JSONP callback override
- API2 alternate positive tid `488/502/540/541`
- API2 `tid=506` near-empty success shell
- canonical XML 双 `VID` batch
- all-invalid JSONP batch 的 caller-side consumer rule

如果你想把 caller-facing raw HTTP recipe 直接实跑一遍，不经过 Python/Go demo 包装，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --timeout 60 --retries 3 --strict --output analysis/direct_call_raw_http_validation_20260621.json
```

它当前验证的是：

- API1 canonical single-CID
- API1 direct multi-CID
- API1 `tid=453` cover-only positive shell
- API1 `tid=483` video_ids-led thin shell
- API1 `tid=537` sample-less shell probe
- API2 canonical XML / JSONP
- API2 alternate positive tid `488/502/540/541`
- API2 `tid=506` near-empty success shell
- `tid=541 + union_platform=0003` thin-shell spot-check
- API2 canonical multi-VID batch spot-check
- all-invalid JSONP batch 的 caller-side success rule

如果你只想补跑 `API1 tid=537` 的 caller-facing raw 证据，不想重跑整套 raw matrix，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --surface api1_tid537_probe_shell --strict --output analysis/direct_call_raw_http_validation_tid537_20260622.json
```

如果你只想补跑 `API1 tid=453` 的 caller-facing raw 证据，不想重跑整套 raw matrix，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --surface api1_tid453_cover_shell_only --strict --output analysis/direct_call_raw_http_validation_tid453_20260623.json
```

如果你只想补跑 `API1 tid=483` 的 caller-facing raw 证据，不想重跑整套 raw matrix，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --surface api1_tid483_video_ids_led_thin_shell --strict --output analysis/direct_call_raw_http_validation_tid483_20260623.json
```

如果你只想补跑 `API2 tid=488/502` 的 caller-facing raw 证据，不想重跑整套 raw matrix，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --surface api2_single_detail_xml_tid488_alt_positive_shell --surface api2_single_detail_xml_tid502_alt_positive_shell --strict --output analysis/direct_call_raw_http_validation_api2_tid488_502_20260623.json
```

如果你只想补跑 `API2 tid=506` 的 caller-facing raw 证据，不想重跑整套 raw matrix，直接用：

```bash
python tools/tencent_raw_http_validation_runner.py --surface api2_single_detail_xml_tid506_near_empty_success_shell --strict --output analysis/direct_call_raw_http_validation_api2_tid506_20260623.json
```

当前口径要收紧地读：

- 这份 raw validation 只覆盖匿名 direct-call scope
- `488/540/541` 与 `541 + union_platform=0003` 仍然只应读成 thin positive shell，`502` 则应读成 richer alternate shell
- `506` 当前已经补到 dedicated demo/raw validation，但验证结果是稳定 near-empty success shell，不是更厚的 positive-detail branch
- batch 行当前是 canonical multi-VID branch spot-check，不是重新做了一次 `32/33` 饱和边界实验

工具入口总表：
[analysis/tooling_entrypoint_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tooling_entrypoint_quick_reference_20260621.json)

## 1. 你手里是 URL

目标：
先从 URL 拿到 CID，再走 canonical API1 -> API2 链路。

Python：

```bash
python examples/python/tencent_video_api_demo.py --url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" --json
```

Go：

```bash
go.exe -url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" -json
```

当前最稳读法：

- demo 会先从 URL 提取 CID
- 再走 API1 canonical cover 查询
- 再把取到的 `video_ids` 送进 API2 canonical detail 查询

证据：
[analysis/demo_validation_incremental_20260621d.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621d.json)

## 2. 你手里是 CID

目标：
拿 cover 壳、节目级枚举字段、以及 `video_ids` 家族。

最稳 raw API：

```text
https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --cid <CID> --json
```

Go：

```bash
go.exe -cid <CID> -json
```

当前最稳默认：

- `tid=431`
- `appid=10001005`
- `appkey=0d1a9ddd94de871b`

如果你只是想稳定拿 cover 壳，不要先改这些 canonical 值。

如果你想显式探 API1 的独立 `tid=453` positive cover shell，而不是走 canonical `431`：

raw API：

```text
https://data.video.qq.com/fcgi-bin/data?tid=453&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --cid <CID> --api1-tid 453 --json
```

Go：

```bash
go.exe -cid <CID> -api1-tid 453 -json
```

当前最稳读法：

- 这不是 `431` 的等价替代
- 到 `2026-06-23` 为止，它在 3 个 public CID 上都重复成了 non-empty cover shell + empty `video_ids` 的正向分支
- 也就是说，`errorno=0` 和非空标题不代表你会拿到 `video_ids` 家族或继续走 canonical API2 详情链路

如果你想显式探 API1 的独立 `tid=483` video_ids-led thin shell，而不是走 canonical `431`：

raw API：

```text
https://data.video.qq.com/fcgi-bin/data?tid=483&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --cid <CID> --api1-tid 483 --json
```

Go：

```bash
go.exe -cid <CID> -api1-tid 483 -json
```

当前最稳读法：

- 这不是 `431` 的等价替代
- 到 `2026-06-23` 为止，它在 3 个 public CID 上都重复成了 `cover_title/type/pay_status` 为空、但 `video_ids` 非空的 thin shell
- 对 raw API1 来说，这意味着它更像“只把节目链路往下游推给 `video_ids`”的成功壳
- 对 Python/Go demo 来说，这条壳仍然能继续驱动 downstream canonical API2 详情查询，但这不等于 API1 自己已经恢复出 canonical `431` 的 cover 丰度

如果你想显式探 API1 的独立 `tid=537` success shell，而不是走 canonical `431`：

raw API：

```text
https://data.video.qq.com/fcgi-bin/data?tid=537&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --cid <CID> --api1-tid 537 --json
```

Go：

```bash
go.exe -cid <CID> -api1-tid 537 -json
```

当前最稳读法：

- 这不是 `431` 的等价替代
- 到 `2026-06-22` 为止，它在 3 个 public CID 上都重复成了 sample-less success shell
- 也就是说，`errorno=0` 不代表你会拿到 `video_ids` 家族

## 3. 你手里是多个 CID

目标：
一请求拿多个 cover 壳。

最干净路径仍然是 raw API1：

```text
https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=<CID1>,<CID2>,...&appid=10001005&appkey=0d1a9ddd94de871b
```

当前 caveat：

- Python/Go demo 现在已经把这条能力提成显式入口
- 输出里会同时保留：
  - `cover_info`：第一条 cover 的兼容锚点
  - `cover_infos`：完整多 cover 列表
  - `api1_batch_diagnostics`：请求 CID 数、返回 cover 数、聚合 `video_ids` 计数
- 如果你不额外传 `VID`，demo 仍会把全部 cover 的 `video_ids` 聚合送去打 API2

Python：

```bash
python examples/python/tencent_video_api_demo.py --cid mzc00200idzf2m8 --cid mzc00200xxpsogl --json
```

Go：

```bash
go.exe -cid mzc00200idzf2m8,mzc00200xxpsogl -json
```

所以：

- 想看纯 API1 多 cover 壳，直接读 `cover_infos`
- 想继续走节目级详情链路，可以直接复用 demo 聚合出的 `video_details`

## 4. 你手里是单个 VID，想拿最完整详情

目标：
拿最丰满、最稳的 detail row。

最稳 raw API：

```text
https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=<VID>
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID> --json
```

Go：

```bash
go.exe -vids <VID> -json
```

当前最稳默认：

- `otype=xml`
- `tid=535`
- `appid=20001238`
- `appkey=6c03bbe9658448a4`
- `union_platform=3`

当前最稳读法：

- `tid=535` 仍是 canonical full-detail branch
- 这是默认最推荐的 detail recipe

## 5. 你手里是单个 VID，但需要 JSONP

目标：
明确走 JSONP wrapper，而不是 XML。

raw API：

```text
https://union.video.qq.com/fcgi-bin/data?otype=json&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=<VID>
```

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-otype json --json
```

Go：

```bash
go.exe -vids <VID> -api2-otype json -json
```

当前规则：

- 只有**精确小写** `otype=json` 会切到 JSONP
- 其他值当前不要当成稳定 JSONP 入口

## 6. 你想探 alternate / success-shell tid

当前已确认 API2 正/成功壳 family：

- `535`
- `488`
- `502`
- `506`
- `540`
- `541`

但最稳口径是：

- `535` 是 canonical full-detail branch
- `488` 当前更像 `title + url` 的更薄 **alternate positive shell**
- `502` 当前更像 `title + url + vid + duration + cover_list + create_time` 的较厚 **alternate positive shell**
- `506` 当前更像 `retcode=0` 但 caller-facing row 仍然 `empty_shell=true` 的 **near-empty success shell**
- `540` 当前更像 `title + duration + url` 的 score-3 **alternate positive shell**
- `541` 当前更像 `title + url` 的 score-2 **alternate positive shell**
- 不要默认它们字段丰满度等同于 `535`，也不要把 `488` 和 `502` 混成同一厚度；`506` 更不能被当成“更薄一点的 535”

Python 例子：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-tid 488 --json
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-tid 502 --json
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-tid 506 --json
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-tid 540 --json
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-tid 541 --json
```

Go 例子：

```bash
go.exe -vids <VID> -api2-tid 488 -json
go.exe -vids <VID> -api2-tid 502 -json
go.exe -vids <VID> -api2-tid 506 -json
go.exe -vids <VID> -api2-tid 540 -json
go.exe -vids <VID> -api2-tid 541 -json
```

## 7. 你想做 API2 批量查询

当前 clean 正向上限：

- `32` 个非空项

`33` 个非空项当前会触发 over-limit error。

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID1> --vid <VID2> --json
```

Go：

```bash
go.exe -vids <VID1>,<VID2> -json
```

如果你想显式控制 demo 的分批大小：

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --vid j4101ouc4ve --api2-batch-size 1 --json
```

Go：

```bash
go.exe -vids z4102qfi0x4,j4101ouc4ve -api2-batch-size 1 -json
```

当前读法：

- `api2-batch-size` 是 demo 层分批入口
- 它不替代底层 API2 批量契约结论
- 底层契约仍看：
  [analysis/parameter_contract_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_contract_quick_reference_20260621.json)

## 8. 你想改 union_platform

当前 canonical detail 调用仍建议保留：

- `union_platform=3`

如果你只是想验证 demo override 路径是否能跑：

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --api2-union-platform 999 --json
```

Go：

```bash
go.exe -vids z4102qfi0x4 -api2-union-platform 999 -json
```

但当前最稳口径一定要记住：

- 当前匿名 same-day + real anonymous visitor-cookie replay 下，`union_platform` 没观察到明显分叉
- 这不是“全局无作用”证明
- `aged-cookie / login-state` 下仍未闭环

## 9. 你想自定义 JSONP callback

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID> --api2-otype json --api2-callback cb1 --json
```

Go：

```bash
go.exe -vids <VID> -api2-otype json -api2-callback cb1 -json
```

当前重点不是“能不能改”，而是“会不会打坏调用方解析”。

当前已知：

- 空 `callback=` 会回落默认 `QZOutputJson=...;`
- 在当前 same-day anonymous JSONP collision cases 里，repeated `callback` 表现为首值生效：
  - `callback=cb1&callback=` -> `cb1(...)`
  - `callback=&callback=cb1` -> 默认 `QZOutputJson=...;`
  - `callback=cb1&callback=a(` -> `cb1(...)`
  - `callback=a(&callback=cb1` -> 仍是 parse-breaking 坏壳
- `otype=json` 的 wrong-appkey 错误壳也仍然吃 `callback`：
  - `callback=cb1` 会把错误壳改成 `cb1({...error...})`
  - `callback=a(` 仍会形成 parse-breaking 坏壳
- 这组 precedence / wrong-appkey error-shell 结论，已经在真实匿名 visitor-cookie replay 的 `PC Web` 与 `Mobile H5` 上各复打一遍，当前未观察到分叉
- 这些已经确认会打坏当前摘要解析路径：
  - `callback=a(`
  - `callback=((`
  - `callback=})();`
- 2026-06-22 的 unmatched-delimiter follow-up 继续把 parse-breaking 代表族向外推宽：
  - `callback=[(`
  - `callback={(`
  - `callback=/*(`
  - `callback=a[(`
  - `callback=)(`
  - `callback=](`
  - `callback=}(`
- 相对地，`callback=[` 与 `callback=[[` 当前仍是 raw passthrough，所以“带特殊字符”不等于一定坏壳

证据见 [analysis/api2_jsonp_callback_contract_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_20260621.json)、[analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json) 与 [analysis/api2_jsonp_callback_unmatched_delimiter_summary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_unmatched_delimiter_summary_20260622.json)。

## 10. 你想跑真实环境 replay

当前 tooling 已经 ready，但高价值结论还依赖外部 Cookie 输入。

先把原始头转成 env：

```bash
python tools/tencent_cookie_env_from_headers.py --mode <aged|login> --desktop-cookie-file <cookie_header.txt> --output <env.json>
```

再跑环境矩阵：

```bash
python tools/tencent_environment_matrix_probe.py --extra-env-json <env.json> --output <matrix.json>
```

或者直接跑 bundle：

```bash
python tools/tencent_replay_bundle_runner.py --mode <real|aged|login> --env-json <env.json> --semantics-profile full --artifact-output-dir <dir>
```

如果你只是想把同一套 Python/Go demo 直接切到某个 replay 环境，不想换工具，也可以这样跑：

Python：

```bash
python examples/python/tencent_video_api_demo.py --vid <VID> --env-json <env.json> --env-name pc_web_real_cookie_replay --json
```

Go：

```bash
go.exe -vids <VID> -env-json <env.json> -env-name pc_web_real_cookie_replay -json
```

当前要收紧地读：

- 这两个 demo 现在支持 header/cookie 环境注入，但仍然是“业务友好调用面”
- 如果你要复现 repeated `callback`、repeated `idlist`、repeated `otype` 这种 raw query parser 语义，还是优先走 raw URL 或 probe tooling，不通过 demo 入口复现

当前最高价值、最影响是否能外推结论的未闭环点，主要集中在这里：

- `aged-cookie replay`
- `login-state replay`
- `union_platform` 跨环境
- `auth-ish extra keys` 跨环境
- `tid` 正分支空间是否还会在真实环境下出现分叉
- 更宽 `positive tid` 空间与 callback 边界是否还存在次级未决项

## 11. 一句总策略

如果你只想**稳定调用当前匿名直连范围内最稳的主调用能力**：

1. `CID -> API1 tid=431`
2. `VID -> API2 tid=535 + otype=xml`
3. 批量时守住 `32` 非空项上限
4. JSONP 只用精确小写 `otype=json`
5. `union_platform` 先保留 `3`
6. 需要更深结论时，再进 replay
