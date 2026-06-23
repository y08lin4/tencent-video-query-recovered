# Tencent Video Query Recovered

这两个接口的核心用处，是把一个腾讯视频页面 URL 逐步转换成可用的数据结果：

- 先用接口 1 把 `CID` 转成节目级元信息和 `VID` 列表
- 再用接口 2 按 `VID` 获取视频标题、时长、页面地址、清晰度资源大小等详情

它们适合用来做这几类事情：

- 从腾讯视频页面 URL 提取结构化信息
- 批量查询某个节目或影片对应的视频 ID
- 获取视频时长、清晰度体积、封面和基础元数据
- 封装成命令行工具、接口服务、桌面工具或移动端查询工具

到 2026-06-20 为止，这个仓库已经不只是“能调通接口”的状态；在当前匿名直连范围内，主调用路径已经压得比较实，但整体参数闭环与环境闭环仍未完成：

- 接口 1：`CID -> cover 元信息 + VID 集合 + cover 级枚举`
- 接口 2：canonical 路径下通常是 `VID -> 较完整的单视频详情 + defn + 分类链 + 批量返回`；但在已知 alternate positive tid 下，`488` 当前更像 `title + url` 的更薄正壳，`502` 当前更像 `title + url + vid + duration + cover_list + create_time` 的较厚 alternate shell，`540` 当前更像 `title + duration + url` 的较薄正壳，`541` 当前更像仅 `title + url` 的更薄正壳；它们都不保证 `defn / category_map / state / upload_src` 等字段齐全
- 当前已补出主要契约与高信号规律：`type`、`pay_status`、`positive_trailer`、`state`、API1/API2 参数契约；`F` 的 black-box family 在当前已测样本内更稳，但前端命名读取仍偏负；`upload_src` 当前不只停在形态确认，在 tested redirected-detail frontend slice 里也补出了更强的 scoped-negative 证据；`positive_content_id` 仍以形态确认为主，而 `downright` 的单码语义仍待命名，但字段级前端用途已经坐实为下载工具栏 gating
- 新增增强层：前端语义层、环境维度矩阵、枚举值卡片化
- 新增确认：前端已坐实 `state` 会进入“未上架 / 下架 / 删除 / 不可播”校验分支；sampled runtime `union.coverInfoMap` 的 `pay_status` 已确认不是 raw API 直通；`upload_src=2048` 已不止 2 个正例 cover，且已经补出 same-type 纯 `0` 反例和 `2048/108` 混合 cover；2026-06-20 的 row-shell / network followup 里 `state/positive_trailer` 继续可见，但 `F/upload_src` 仍未补出正例
- 同日继续补强：已测 visible-card `getPage` row schema 也继续不带 `F/upload_src`；更稳的说法是，这个结论当前不只覆盖两条代表性 redirected detail 路径，还覆盖 3 个 stronger non-detail 候选在重定向进 detail 之后的 request/response slice；下一跳更该追 `getPage` tagged shaping、真实 `getCoverInfoBatch` 请求，或 SSR / vector-layout 提前整形
- 新增闭环：`frontend_startup_vs_runtime_diff_20260620.json` 已把 tested redirected-detail slice 压成更清楚的字段差分：`positive_trailer` 能从 startup/SSR 进 sampled `getPage`，`state` 会在 `FillUnionInfo` 补回来，`F` 目前仍停在 startup/SSR 可见层，而 `upload_src` 目前在 startup/SSR、sampled `getPage / FillUnionInfo`、以及 tested detail bundle 命名字串层都没命中
- 新增前端链路边界：`frontend_row_network_request_capture_20260620.json` 已把两条最强 redirected-detail 候选再做一轮 request-side + response-side 抓取；当前仍只看到 `PageService/getPage + FillUnionInfo`，没有真实 `getCoverInfoBatch` 请求
- 新增 targetid 边界：`frontend_targetid_report_identity_owner_bridge_20260620.json` 已把匿名评论举报 DOM 周边的 dataset / framework-owner 浅层身份也扫了一轮；当前仍只停在 `feed_id / cp_id` 这套身份族，`commentInfo.targetid/commentid` 的 natural producer 还没闭合，但负证据范围已经更清楚
- 新增环境闭环：`state=8` 正 family 已把 `482396nuyaelv0e` 和 `mzc002006tgfqvp` 补到 8 环境 same-day 稳定，且 `state/upload_src` 分布与 `2026-06-19` 基线一致；这能收紧“state=8 更像行级 small-family signal”的环境适用范围，但仍不把它写成页型桶
- 同日补到：`upload_src_2048_environment_20260620.json` 已把核心环境测试集里的 `2` 个 pure `2048` 正例、`1` 个 mixed `2048/108` cover、`1` 个 same-type pure-0 negative 补到 `8` 环境无漂移；这关闭的是 tested slice 的环境稳定性，不是跨出 `type=111` 的 family boundary
- 新增契约闭环：`api2_jsonp_batch_matrix_20260620.json` 已把单个 `otype=json` + 单个 `idlist` key 的 `mixed valid+invalid / duplicate+empty / dup32 / dup33` 4 条镜像 batch case 补到 8 环境 same-day 稳定；当前最稳结论是 JSONP 只换外壳，不改这些 batch semantics
- 新增 query parser 语义：`param_query_semantics_20260620.json` 已补出当前匿名 canonical tested branches 下的 extra/repeated key 行为；API1 的 `foo/callback/_`、API2 XML 的 `foo/callback/_`、API2 JSONP 的 `foo/_` 当前都未观察到变化；API2 JSONP `callback` 现在已经补到更宽的第二层 practical value-space：`1 / cb1 / QZOutputJson / foo.bar / a-b / a[b] / $cb / foo bar / foo,bar / [0] / 中文 / a) / ) / a;b / a'b / a\"b / a/ / a\\ / //a / /*a / [ / [[` 在当前已测样例里都会改写 wrapper，空 `callback=` 会回落默认 `QZOutputJson=` 外壳，而 `callback=a(`、`callback=((`、`callback=})();` 与后续补到的 `callback=[(` / `callback={(` / `callback=/*(` / `callback=a[(` / `callback=)(` / `callback=](` / `callback=}(` 都已经进入当前已确认的 parse-breaking 代表值集合；API1 `tid/idlist/appid/appkey` 与 API2 `tid/idlist/otype/appid/appkey` 的 repeated key 在当前已测对撞组合下都表现为首值生效
- 新增 `tid` 扩圈进展：`positive_tid_summary_20260620.json` 先压了 focused `428-434 / 533-540` 高信号带宽，`positive_tid_summary_20260621.json` 又把 `420-445 / 530-550` 往外扩了一圈，`positive_tid_probe_446_455_summary_20260623.json` 再把 `446-455` 窄带补了一刀，`positive_tid_probe_456_521_summary_20260623.json` 则把中间主走廊继续压实；当前已确认 API1 canonical 正分支 `431`、API1 新的 cover-only positive shell 分支 `453`、API1 独立 `success_shell_without_sample` 分支 `537`，并新增 API1 的 `476/506` success-shell family、`483` video_ids-only shell，以及 API2 新的稳定正分支 `488/502` 和 `506` success-shell family。到 `2026-06-23` 为止，`453` 已在 3 个 public CID 上重复成 non-empty cover shell + empty `video_ids` 的正向分支，`476/506` 已在 3 个 public CID 上重复成更薄的 success shell，`483` 已在 3 个 public CID 上重复成仅露出 `video_ids` 的 video_ids-only shell，`488` 已在 3 个 public VID 上重复成 `title + url + pic` 薄正壳，`502` 已在 3 个 public VID 上重复成 `title + url + duration + type + vid + cover_list` 更厚一点的 alternate positive shell，`540` 已在 3 个 public VID 上重复成 `title + duration + url` 的 score-3 薄正壳，`541` 已在 3 个 public VID 上重复成 `title + url` 的 score-2 更薄正壳；它们都不默认等同 canonical `431/535` 的字段丰满度。caller-selected `636-640 / 648-652` 补测也仍全部回到标准错误支，所以这轮是在已知正簇之外继续收紧外带，不足以把 positive tid 空间写成已扫清
- 新增 callback pathological tail follow-up：`api2_jsonp_callback_pathological_tail_20260621.json` 已把更激进的 closer-heavy / punctuation-heavy 值再压一轮；当前 `] / { / } / a] / a} / a)) / a}}) / a&b / a#b / a%20b / a> / a=` 这批仍大多 raw passthrough，而 `callback=})();` 新增为当前已确认的 parse-breaking 代表值
- 新增 callback 契约收口：`api2_jsonp_callback_contract_20260621.json` 已把最值钱的 6 条 callback precedence / error-shell case 补出来；当前 same-day anonymous JSONP collision cases 下，repeated `callback` 也表现为首值生效，而 wrong-appkey JSONP 错误壳仍然会吃 `callback` wrapper 改写
- 新增环境复核：`api2_jsonp_callback_contract_real_cookie_pc_20260621.json`、`api2_jsonp_callback_contract_real_cookie_mobile_20260621.json` 和 `api2_jsonp_callback_contract_real_cookie_summary_20260621.json` 已把这组 callback precedence / wrong-appkey error-shell 结论再压到真实匿名 visitor-cookie replay 的 PC Web / Mobile H5，两边当前都没观察到分叉
- 新增扩圈：`upload_src_2048_type111_search_expansion_20260620.json` 已把 `type=111` 的 sampled slice 扩到舞蹈 / 国画 / 书法教学三支，并首次补到 complete pure-2048 + empty `targetid` 反例 `mzc00200tjnrzs3`，所以 `upload_src=2048 => targetid 非空` 不再成立
- 额外确认：腾讯视频搜索后端可以作为补样本入口，用来继续发现新的 `CID / type / pay_status`
- 当前环境矩阵仍属于 same-day 结论；第二代表样本扩展里的多页已继续稳定，但按严格“桶级首代表 + 第 2 代表”口径，目前真正闭环的仍主要是 `电影单片 / 动漫季页 / 少儿免费合集`；`sec-ch-ua / sec-fetch-* / cookie` 真实浏览器头、sports replay 第 2 代表页和跨日复测还在继续补

研究状态导航：

- [docs/tencent_video_apis.md#9-已明确--部分明确--未明确](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#10-枚举值状态表](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#11-前端语义层观察](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#12-环境维度适用范围](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)

下面这几份还是当前主链最值得先看的 canonical 总表；它们的文件名多数仍停在 `20260620`，但参数总表、能力面、配方表、回归样本，以及新增的两张调用者 join 总表，已经刷新到 `2026-06-21` 证据口径，另外再配合下方的增量摘要一起读更稳。

- [analysis/api_param_inventory_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api_param_inventory_20260620.json)
  - 两个主接口的参数总表：作用、硬约束、条件分支、边界与未闭合点
- [analysis/parameter_capability_index_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_capability_index_20260621.json)
  - 统一参数索引：把显式参数、候选参数、replay/tooling 参数，与能力配方、回归样本、关键证据串成一张机器可读入口
- [analysis/capability_surface_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_surface_20260620.json)
  - 当前可直接调用的能力面：单条/批量、XML/JSONP、32/33 边界、环境适用范围
- [analysis/capability_recipes_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_recipes_20260620.json)
  - 能力配方表：按“做什么 -> 用哪个接口 -> 带哪些参数 -> 怎么调示例”组织
- [analysis/regression_samples_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/regression_samples_20260620.json)
  - 参数闭环回归样本：baseline、mixed、duplicate、dup32、dup33、JSONP 镜像
- [analysis/param_gap_priority_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_gap_priority_20260620.json)
  - 当前只按“参数闭环”排序后的 gap 台账，避免继续被字段语义线带偏
- [analysis/callback_tail_values.txt](C:/Users/lin/Documents/YM查询工具还原/analysis/callback_tail_values.txt)
  - replay bundle 的 callback pathological-tail 输入样例文件：一行一个已实测值，可直接配合 `--probe-extra-callback-file` 使用
- [examples/environment/pc_aged_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_aged_cookie_header.template.txt)
  - aged-cookie replay 的最小输入模板：给 `tencent_cookie_env_from_headers.py` 或 `tencent_replay_bundle_runner.py` 的 `--desktop-cookie-file` 使用
- [examples/environment/pc_login_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_login_cookie_header.template.txt)
  - login-state replay 的最小输入模板：给 `tencent_cookie_env_from_headers.py` 或 `tencent_replay_bundle_runner.py` 的 `--desktop-cookie-file` 使用
- [analysis/environment_replay_runner_contract_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_runner_contract_20260622.json)
  - replay bundle 契约表：把 `tencent_replay_bundle_runner.py` 的 CLI、步骤、summary 字段、skip 语义压成机器可读 contract
- [analysis/environment_replay_input_boundary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_input_boundary_20260622.json)
  - replay 输入边界：明确 `desktop cookie required, mobile optional`，以及 env-builder 的最小可执行输入模型
- [analysis/environment_replay_hard_block_table_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_hard_block_table_20260622.json)
  - replay hard-block 边界：把 `union_platform / auth-ish extra keys / 540/541 shell thickness` 这些“当前只能 scoped-negative”的项单独列出来
- [analysis/param_query_semantics_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_query_semantics_20260620.json)
  - 当前 canonical tested branches 下的 extra key / repeated key 语义证据；适合直接看 `first-value-wins` 与“当前未观察到变化”的边界
- [analysis/api2_all_invalid_jsonp_consumer_rule_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_all_invalid_jsonp_consumer_rule_20260620.json)
  - API2 全坏 JSONP 批量的统一调用方识别规则：`top-level success + 全部 empty_shell=true` 应视为整批无效
- [analysis/api2_jsonp_callback_value_space_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_value_space_20260620.json)
  - API2 JSONP callback 第二层 practical value-space：宽字符族 raw passthrough + 空 callback fallback
- [analysis/api2_jsonp_callback_pathological_tail_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_pathological_tail_20260621.json)
  - API2 JSONP callback pathological tail follow-up：closer-heavy / punctuation-heavy 家族大多仍 raw passthrough，`})();` 新增为 parse-breaking 代表值
- [analysis/api2_jsonp_callback_contract_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_20260621.json)
  - API2 JSONP callback precedence / error-shell 最小契约组：repeated `callback` 在当前匿名 collision cases 下表现为首值生效，wrong-appkey JSONP 错误壳也仍然吃 `callback` wrapper 改写
- [analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json)
  - 同一组 callback precedence / wrong-appkey error-shell case 在真实匿名 visitor-cookie replay 的 PC Web / Mobile H5 上都未观察到分叉
- [analysis/api2_jsonp_callback_unmatched_delimiter_summary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_unmatched_delimiter_summary_20260622.json)
  - 2026-06-22 callback boundary follow-up：`[` / `[[` 当前仍 raw passthrough，而 `[(` / `{(` / `/*(` / `a[(` / `)(` / `](` / `}(` 进入当前已确认的 widened parse-breaking 代表族
- [analysis/reserved_extra_key_sweep_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/reserved_extra_key_sweep_20260620.json)
  - 第一轮 reserved-looking extra key sweep：`format / output / version / v / platform / source` 在当前匿名 canonical branches 下都未见作用
- [analysis/authish_extra_key_sweep_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/authish_extra_key_sweep_20260620.json)
- 第一轮 auth-ish extra key sweep：`token / sign / sig / appver / access_token / authkey / openid` 在当前匿名 canonical branches 下都未触发可观察分支
- [analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json)
  - 真实匿名 visitor cookie replay 下的 auth-ish / union_platform / callback 关键分支对比摘要：当前只支持“已测 key 集 + 已测 tid anchor + 匿名 baseline”这一层 scoped-negative，未观察到相对匿名 baseline 的翻转；剩余环境差异问题收窄到 `aged-cookie / login-state`，也不能据此外推 `union_platform` 或 auth-ish key 在所有 tid/sample/会话态下全局无作用
- [analysis/positive_tid_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_summary_20260620.json)
  - focused 高信号带宽摘要：先确认 API1 `431`、API2 `535 / 540`，并把 API1 `537` 单独落成 success-shell-without-sample
- [analysis/positive_tid_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_summary_20260621.json)
  - 更宽扩圈摘要：API2 `541` 已补成新正向分支，并用第二个样本复核通过；`542-550` 当前回落为标准错误带
- [analysis/positive_tid_probe_446_455_summary_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_446_455_summary_20260623.json)
  - 新增 `446-455` follow-up 摘要：API1 `453` 已补成 3-CID confirmed 的 positive cover-shell-only 分支，而 API2 `453` 仍稳定在 `key all illegal`
- [analysis/positive_tid_probe_524_529_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_524_529_summary_20260621.json)
  - `524-529` 窄带补测摘要：没有新增正分支；`525` 在第二、第三样本里都稳定落到 `-111013`，其余点仍是标准 `-111005`
- [analysis/positive_tid_api1_boundary_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_api1_boundary_summary_20260621.json)
  - API1 新补 `418-421` 和 `526-536` 两段只收紧了错误边界，没有新增正分支；`535` 现在已经在第二个 CID 上复现为稳定的局部 `key all illegal` 边界点
- [analysis/positive_tid_probe_641_647_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_641_647_summary_20260621.json)
  - 匿名 `641-647` jump-scan 已跑完：没有扫出新正簇；第二、第三个 sample 里 `642` 都额外落到了 `-111013`，说明这段存在稳定的局部错误族异质性
- [analysis/positive_tid_probe_636_640_648_652_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_636_640_648_652_20260622.json)
  - 围绕 `642` 两侧补了 `636-640` 和 `648-652`：API1、API2 XML、API2 JSONP 全部回到标准 `-111005`，当前更支持 `642` 是局部异常岛，而不是更大正簇或更宽 `-111013` 家族的边缘
- [analysis/positive_tid_probe_522_525_summary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_522_525_summary_20260622.json)
  - 新补的 cross-interface lower-edge follow-up 说明：`522-524` 在 API1、API2 XML、API2 JSONP 上都稳定是标准 `-111005`，而 `525` 在两组 public sample 里同步是 `-111013`；这把 `525` 从 API2-only anomaly 升级成了跨接口局部错误岛
- [analysis/demo_validation_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_20260621.json)
  - Python / Go live demo 验证摘要：canonical `535` 默认链路与 JSONP callback override 都已跑通；`tid=541` 也能返回正壳，但字段丰满度不应默认等同于 `535`
- [analysis/direct_call_raw_http_validation_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_20260621.json)
  - caller-facing raw HTTP live validation 摘要：把 canonical XML / JSONP、alternate positive tid、`541 + union_platform=0003`、API1 direct batch，以及 all-invalid JSONP consumer rule 直接按原生 HTTP 重跑了一遍；这仍只覆盖匿名 direct-call scope
- [analysis/api2_alt_tid_capability_delta_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_alt_tid_capability_delta_20260621.json)
  - `535/540/541` 能力差异摘要：当前更稳的说法是它们属于同一正分支 family，但 `540/541` 都只坐实为 alternate positive shell，不应默认等同于 canonical `535` 的字段丰满度
- [analysis/api1_tid_shell_family_delta_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api1_tid_shell_family_delta_20260623.json)
  - API1 `431/453/476/483/506/537` 壳层差异摘要：`431` 仍是 canonical 正分支，`453` 是最厚的非 canonical cover-only shell，`483` 是以 `video_ids` 为主的薄成功壳，`476/506/537` 则继续停在更薄的 success-shell family
- [analysis/api2_extended_tid_capability_delta_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_extended_tid_capability_delta_20260623.json)
  - API2 扩展后 `488/502/506/535/540/541` 能力差异摘要：`488/502` 已补进 alternate-positive family，`502` 明显比 `488/540/541` 更厚，但仍不等同 canonical `535`；`506` 当前继续保守读成 near-empty success shell
- [analysis/demo_validation_incremental_api2_tid488_502_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_api2_tid488_502_20260623.json)
  - Python / Go 对 `API2 tid=488/502` 的增量 live validation：`488` 当前稳定是 title+url 的更薄正壳，`502` 当前稳定是带 `vid + duration + cover_list + create_time` 的较厚 alternate shell
- [analysis/direct_call_raw_http_validation_api2_tid488_502_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_api2_tid488_502_20260623.json)
  - `API2 tid=488/502` 的 caller-facing raw HTTP live validation：把这两条 alternate shell 直接按原生 HTTP 坐实到可回归层
- [analysis/tid_richness_matrix_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tid_richness_matrix_20260622.json)
  - `431/537` 与 `535/540/541` 的多样本字段丰度矩阵：`537` 在 3 个 public CID 上都还是 sample-less success shell；`540` 在 3 个 public VID 上稳定是 score-3 薄正壳；`541` 在 3 个 public VID 上稳定是 score-2 更薄正壳
- [analysis/tid_richness_matrix_extended_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tid_richness_matrix_extended_20260623.json)
  - 扩展矩阵：把 API1 `431/453/476/483/506/537` 与 API2 `488/502/506/535/540/541` 拉到同一套 Python demo 多样本比较框架里，方便统一看壳层厚度
- [analysis/demo_validation_incremental_tid453_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_tid453_20260623.json)
  - Python / Go demo 对 `API1 tid=453` 的 live validation：当前 caller-facing 输出稳定是 cover-only positive shell，不会继续产出 API2 详情
- [analysis/direct_call_raw_http_validation_tid453_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_tid453_20260623.json)
  - `API1 tid=453` 的 caller-facing raw HTTP live validation：`errorno=0`、非空 `cover_title`、`video_ids_count=0`
- [analysis/parameter_closure_matrix_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_closure_matrix_20260621.json)
  - 参数闭环矩阵：把 API1/API2 每个已暴露参数以及 `callback / auth-ish extra keys / reserved extra keys` 这些候选参数家族收成统一台账，明确 `requiredness / role / 失败形态 / 依赖分支 / 环境范围 / 已解锁能力 / 剩余缺口`
- [analysis/parameter_contract_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_contract_quick_reference_20260621.json)
  - 调用者视角参数总表：把 API1/API2 已坐实参数压成“推荐怎么填 / 乱填会报什么 / 哪些结论只在匿名直连范围内成立”的 quick reference
- [analysis/direct_call_parameter_total_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_parameter_total_table_20260621.json)
  - 调用者参数总表增强版：把“推荐填法 / 成功判据 / 重复 key 语义 / 32/33 计数规则 / 已证实环境 / 未证实环境”压成一张更适合 SDK 和脚本作者直接照着用的总表
- [analysis/capability_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_quick_reference_20260621.json)
  - 调用者视角能力配方总表：把“什么时候该用哪条 recipe、默认怎么调、会踩什么坑”压成 quick reference
- [analysis/direct_call_capability_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_capability_table_20260621.json)
  - 调用者能力总表增强版：按“一行一个可调用能力面”串起 `use_when / 参数层级 / 成功规则 / 风险边界 / live 验证状态 / 回归样本`
- [analysis/direct_call_delivery_manifest_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_delivery_manifest_20260621.json)
  - 交付总入口：按调用者 / SDK 作者 / 研究者三类入口，把参数总表、能力配方、示例、回归样本和剩余闭环缺口串成一张清单
- [analysis/parameter_closure_shortlist_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_closure_shortlist_20260622.json)
  - 参数闭环短清单：把 `must-wait external inputs / 仍可无输入推进 / 低优先级发现尾项` 压成一张更短的执行入口
- [docs/environment_replay_runbook.md](C:/Users/lin/Documents/YM查询工具还原/docs/environment_replay_runbook.md)
  - 环境回放执行手册：把 `aged-cookie / login-state` 还差什么输入、输入放哪、先跑哪个命令、输出先看什么，压成可执行步骤
- [analysis/environment_replay_closure_checklist_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_closure_checklist_20260621.json)
  - 环境闭环 checklist：把缺失输入、执行顺序、必须复核的 matrix/bundle 检查点、以及回写目标压成机器可读清单
- [docs/direct_call_playbook.md](C:/Users/lin/Documents/YM查询工具还原/docs/direct_call_playbook.md)
  - 直接调用手册：按 `URL / CID / VID / JSONP / 批量 / replay` 分流，给出最短可执行路径
- [analysis/tooling_entrypoint_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tooling_entrypoint_quick_reference_20260621.json)
  - tooling 入口总表：把 Python/Go demo、replay tooling、参数探针的核心 CLI 入口和常用 flag 收成一张快速索引
- [analysis/replay_bundle_real_full_semantics_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/replay_bundle_real_full_semantics_summary_20260621.json)
  - anonymous real-cookie full semantics 摘要：记录 `full + callback tail` 回放在 PC Web / Mobile H5 真实匿名 Cookie 环境下没有新增参数分支
- [analysis/demo_capability_coverage_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_capability_coverage_20260621.json)
  - 示例覆盖矩阵：区分 Python/Go 示例“已支持的能力面”和“已经 live 验证过的能力面”，避免把仅有 CLI 支持误写成已实测闭环
- [analysis/demo_validation_incremental_20260621b.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621b.json)
  - 新增 live 验证补丁：把 `go + tid=540` 与 Python/Go 的 all-invalid JSONP consumer-rule 路径补成正式证据
- [analysis/demo_validation_incremental_20260621c.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621c.json)
  - 新增 live 验证补丁：把 Python/Go 的 API1 batch 示例路径也补成正式证据；当前匿名直连范围内，示例覆盖矩阵已无高价值未实测路径
- [analysis/objective_coverage_audit_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/objective_coverage_audit_20260621.json)
  - 目标覆盖审计：把最终目标拆成参数总表 / 能力配方 / Python/Go 示例 / 回归样本 / 候选参数 / 环境闭环等交付项，明确哪些已覆盖，哪些仍只部分覆盖

## 最短上手

Python，按 URL 走完整链路：

```bash
python examples/python/tencent_video_api_demo.py --url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" --json
```

这条 URL 入口当前已经有 dedicated live 验证，见 [analysis/demo_validation_incremental_20260621d.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621d.json)。

Python，显式切 API2 JSONP：

```bash
python examples/python/tencent_video_api_demo.py --cid mzc00200idzf2m8 --api2-otype json --json
```

Python，显式切 API2 JSONP 并改写 callback wrapper：

```bash
python examples/python/tencent_video_api_demo.py --cid mzc00200idzf2m8 --api2-otype json --api2-callback cb1 --json
```

先抓真实匿名 visitor cookie replay 环境：

```bash
"C:\Users\lin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" tools/tencent_anonymous_cookie_replay_env_capture.js --output analysis/anonymous_real_cookie_env_20260621.json
```

再跑真实匿名 visitor cookie replay 环境矩阵：

```bash
python tools/tencent_environment_matrix_probe.py --include-browser-like --extra-env-json analysis/anonymous_real_cookie_env_20260621.json --output analysis/environment_matrix_anonymous_real_cookie_20260621.json
```

如果要构造 `aged-cookie / login-state` replay 输入，不需要手写整份 JSON，直接把原始 `Cookie:` 头喂给 helper 即可：

```bash
python tools/tencent_cookie_env_from_headers.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt --output analysis/aged_cookie_env_20260621.json
python tools/tencent_cookie_env_from_headers.py --mode login --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt --output analysis/login_state_env_20260621.json
```

`--mobile-cookie-file` 可以按需再补；按当前 builder 契约，第一轮 `aged/login` replay 的最小输入就是一份 `PC Web Cookie`，`mobile H5 Cookie` 仍然只是可选增强。脚本会自动补 `User-Agent / Accept / Referer / Origin`。这里的 `analysis/aged_cookie_env_20260621.json` 与 `analysis/login_state_env_20260621.json` 是首次执行时生成的输出路径示例，不是仓库预置输入文件。当前只有真实匿名 visitor cookie replay 已有正式产物，`aged-cookie / login-state` 仍待实测闭环。

如果要把最后这条环境闭环路径收成单命令，而不是手工串多条 probe，可直接用：

```bash
python tools/tencent_replay_bundle_runner.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt
python tools/tencent_replay_bundle_runner.py --mode login --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt
```

它会自动生成 env JSON、环境矩阵输出、`authish` 语义复测输出，并再写一份 top-level summary。

如果你要把 callback pathological-tail 一起带进 replay，可再加：

```bash
python tools/tencent_replay_bundle_runner.py --mode real --env-json analysis/anonymous_real_cookie_env_20260621.json --skip-matrix --semantics-profile full --probe-extra-callback-value '})();' --probe-extra-callback-value 'a}})' --artifact-output-dir C:/Users/lin/AppData/Local/Temp/replay_bundle_demo
```

这条不是新的环境结论，而是新的可执行能力：runner 现在能带 full semantics、额外 callback 值，并把整包结果稳定落到可写目录。

如果你想先看“runner 到底承诺了什么、哪些输入真是硬要求、哪些环境结论现在不能先说满”，直接看：

- [analysis/environment_replay_runner_contract_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_runner_contract_20260622.json)
- [analysis/environment_replay_input_boundary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_input_boundary_20260622.json)
- [analysis/environment_replay_hard_block_table_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_hard_block_table_20260622.json)

Go，按 URL 走完整链路：

```bash
go.exe -url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" -json
```

Go，显式切 API2 JSONP：

```bash
go.exe -cid mzc00200idzf2m8 -api2-otype json -json
```

Go，显式切 API2 JSONP 并改写 callback wrapper：

```bash
go.exe -cid mzc00200idzf2m8 -api2-otype json -api2-callback cb1 -json
```

## 能力与入口

| 能力 | 当前入口 | 说明 |
| --- | --- | --- |
| `CID -> cover 壳 + VID 集合` | 文档、Python demo、Go demo | API1 基础能力 |
| `CID[] -> 批量 cover 查询` | 文档、Python demo、Go demo、analysis、contract probe | 已闭合到单个 `idlist` 参数内 CSV 的 32/33；重复 `idlist` 当前不是第二种批量入口；Python/Go demo 现在都显式输出 `cover_infos` 与 `api1_batch_diagnostics` |
| `VID -> 单条详情` | 文档、Python demo、Go demo | API2 XML / JSONP 都可走 |
| `VID[] -> 批量详情` | 文档、Python demo、Go demo | Python 与 Go 现在都支持按批分发 API2，并暴露了 `--api2-batch-size` / `-api2-batch-size`（当前 guard 为 `1..32`） |
| `otype=json` JSONP 外壳 | 文档、Python demo、Go demo | 当且仅当单个 `otype` key 为精确小写 `json` 时切到 JSONP；Python/Go demo 现在都支持 `api2-callback` 覆盖 wrapper，空 `callback=` 回落默认壳，repeated `callback` 在当前匿名 collision cases 下表现为首值生效，而当前已知会打坏摘要解析的代表 case 包括 `callback=a(`、`callback=((`、`callback=})();`，以及后续补到的 `callback=[(` / `callback={(` / `callback=/*(` / `callback=a[(` / `callback=)(` / `callback=](` / `callback=}(`；相对地，`callback=[` / `callback=[[` 仍是 raw passthrough |
| `all-invalid JSONP` 调用方识别 | 文档、Python demo、Go demo、analysis | 当前统一规则：`top-level success + 全部 empty_shell=true` 视为整批无效 |
| 参数契约 / 错误壳探测 | `tools/tencent_api_contract_probe.py` | 适合复现单键 `tid / idlist / appid / appkey / otype / union_platform` 分支 |
| extra/repeated key 语义 | `tools/tencent_param_semantics_probe.py` | 专门复现 `foo/callback/_`、API2 JSONP `callback` wrapper 变化、以及 repeated `tid / idlist / otype / appid / appkey / union_platform` 的 parser 行为；现在也支持 `--api2-tid / --api2-idlist / --case-profile authish|callback_contract`，以及 `--extra-callback-value / --extra-callback-file` 这种窄范围 callback 尾项扩测 |
| replay 环境矩阵 | `tools/tencent_environment_matrix_probe.py` + [examples/environment/real_cookie_env.template.json](C:/Users/lin/Documents/YM查询工具还原/examples/environment/real_cookie_env.template.json) | 真实匿名 visitor cookie replay 已有正式产物；`aged-cookie / login-state` 也已有 header-to-env 构造入口，但仍待补实测。推荐先用 `tools/tencent_cookie_env_from_headers.py` 从原始 `Cookie:` 头生成 `--extra-env-json` |
| replay bundle 串联 | `tools/tencent_replay_bundle_runner.py` | 现在除了 `authish` 轻量语义回放，也支持 `--semantics-profile full` 以及 `--probe-extra-callback-value / --probe-extra-callback-file`，可以把 callback pathological-tail case 一起带进后续 aged/login replay；同时新增 `--artifact-output-dir / --subprocess-output-dir`，在本地受限环境里也能先把整包结果完整落到可写目录。相关自测见 `replay_bundle_semantics_callback_support_20260621.json` 与 `replay_bundle_artifact_dir_selfcheck_20260621.json` |

当前匿名直连范围内，下面这几条 demo 入口已经补成 dedicated live validation：

- `--url / -url`
  - Python：`python examples/python/tencent_video_api_demo.py --url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" --json`
- Go：`go.exe -url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" -json`
- `--api2-batch-size / -api2-batch-size`
  - Python：`python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --vid j4101ouc4ve --api2-batch-size 1 --json`
- Go：`go.exe -vids z4102qfi0x4,j4101ouc4ve -api2-batch-size 1 -json`
- `--cid / -cid` 多 CID 直批
  - Python：`python examples/python/tencent_video_api_demo.py --cid mzc00200idzf2m8 --cid mzc00200xxpsogl --json`
  - Go：`go.exe -cid mzc00200idzf2m8,mzc00200xxpsogl -json`
- `--api2-union-platform / -api2-union-platform`
  - Python：`python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --api2-union-platform 999 --json`
- Go：`go.exe -vids z4102qfi0x4 -api2-union-platform 999 -json`
- `--env-json / -env-json`
  - Python：`python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --env-json analysis/anonymous_real_cookie_env_20260621.json --env-name pc_web_real_cookie_replay --json`
  - Go：`go.exe -vids z4102qfi0x4 -env-json analysis/anonymous_real_cookie_env_20260621.json -env-name pc_web_real_cookie_replay -json`

这些验证只说明 demo 入口在当前匿名 direct-call scope 下可运行，不外推到 `aged-cookie / login-state`，也不据此把 `union_platform` 写成全局无作用。既有统一证据见 [analysis/demo_validation_incremental_20260621d.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621d.json)，而多 `CID` / `api2-batch-size` 相关的最新 targeted rerun 见 [analysis/demo_validation_incremental_20260621e.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621e.json)。

## 回归样本

当前最小回归样本包见 [analysis/regression_samples_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/regression_samples_20260620.json)，已经覆盖：

- API1 baseline / missing `tid` / canonical `appid` 缺 `appkey`
- API1 mixed valid+invalid / duplicate+empty-slot / `dup32` / `dup33`
- API2 XML baseline / JSONP baseline
- API2 mixed valid+invalid / all-invalid JSONP / duplicate+empty-slot / `dup32_json` / `dup33_json`

这个仓库现在围绕三块内容展开：

1. 两个腾讯视频接口的说明文档
2. Python / Go 调用示例
3. GitHub Actions 远端构建产物：
   - Windows `exe`
   - Android `apk`

项目主线不再讨论来源背景，直接聚焦接口本身和可运行示例。

当前仓库里的字段说明和示例实现，基于 2026-06-19 的多轮 live 测试整理，样本已经扩到电影、动漫、电视剧、纪录片、综艺、少儿、免费合集、合集页、专题页、直播运营页和跨类混装页，不再只是单样本猜测。

## 接口链路

```text
URL -> CID -> 接口1 -> VID -> 接口2 -> 结果
```

- 接口 1：`CID -> 节目元信息 + VID 列表`
- 接口 2：`VID -> 视频详细信息`

## 仓库结构

- [docs/tencent_video_apis.md](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
  - 两个接口的作用、参数、字段说明、调用示例、实测样例
- [examples/python/tencent_video_api_demo.py](C:/Users/lin/Documents/YM查询工具还原/examples/python/tencent_video_api_demo.py)
  - Python 标准库示例
- [examples/go/main.go](C:/Users/lin/Documents/YM查询工具还原/examples/go/main.go)
  - Go 标准库示例
- [tools/tencent_video_field_survey.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_video_field_survey.py)
  - 多 URL 字段巡检脚本，支持 `clips_ids` 抽样、HTTP 重试、cover / video / clip 异常值摘要
- [tools/tencent_cover_graph_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_cover_graph_probe.py)
  - related cover BFS 探测脚本，用来压 `pay_status / positive_trailer / positive_content_id / downright` 这类 cover 级不确定性
- [tools/tencent_api_contract_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_api_contract_probe.py)
  - API1 / API2 参数契约探针，用来压 `tid / idlist / appid / appkey / otype / union_platform` 的错误码和返回形态
- [tools/tencent_param_semantics_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_param_semantics_probe.py)
  - extra key / repeated key 语义探针，用来压 query parser 在当前 tested branch 下如何处理同名 key 与保留字风格 key
- [tools/tencent_search_seed_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_search_seed_probe.py)
  - 搜索后端补种子探针，用来继续发现新的 `CID / type / pay_status`
- [tools/tencent_value_family_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_value_family_probe.py)
  - 稀有值 family 探针，把 cover graph 和 field survey 合在一起压边界
- [tools/tencent_gap_ledger.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_gap_ledger.py)
  - 从当前 `analysis` 结果里生成 gap ledger
- [tools/tencent_frontend_semantic_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_frontend_semantic_probe.py)
  - 抽样页面 SSR 和主 bundle，并对照同页 API1/API2 快照，定位前端如何消费 API 字段
- [tools/tencent_frontend_nondetail_chain_probe.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_frontend_nondetail_chain_probe.js)
  - 从 cover-like 输入页继续追 `PageService/getPage / FillUnionInfo`，专门补 non-detail / aggregation 路径上的 `F / upload_src` 证据
- [tools/tencent_environment_matrix_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_environment_matrix_probe.py)
  - 跑 `PC Web UA / Mobile H5 UA / 最小请求头 / Referer+Origin` 的环境矩阵，生成 API1/API2 契约与代表页字段漂移对照
- [tools/tencent_anonymous_cookie_replay_env_capture.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_anonymous_cookie_replay_env_capture.js)
  - 用真实匿名页面浏览态抓取可复用的 replay 环境 JSON，直接喂给 `--extra-env-json`
- [tools/tencent_cookie_env_from_headers.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_cookie_env_from_headers.py)
  - 从原始 `Cookie:` 请求头直接生成 `real / aged / login-state` replay env JSON；desktop 必填，mobile 可选
- [tools/tencent_replay_bundle_runner.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_replay_bundle_runner.py)
  - 把 `aged / login-state` 最后一公里收成一条总入口：自动串联 `cookie_env -> environment_matrix -> authish semantics`，拿到 Cookie 头后可一键跑 replay bundle
- [tools/tencent_enum_cards.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_enum_cards.py)
  - 从当前 `analysis` 结果自动合成枚举索引和枚举值卡片
- [android](C:/Users/lin/Documents/YM查询工具还原/android)
  - 最小 Android 客户端工程
- [.github/workflows/build-artifacts.yml](C:/Users/lin/Documents/YM查询工具还原/.github/workflows/build-artifacts.yml)
  - GitHub Actions 远端构建 `exe` 和 `apk`

## 当前内容重点

- URL 可先提取 `CID`
- 接口 1 返回 XML；canonical `tid=431` 下最核心的可消费字段家族是 `video_ids`，但 API1 还存在 `453/537` 这类更薄的 success shell，不应把“成功”默认等同于“必有 video_ids”
- 接口 2 默认返回 XML；当且仅当单个 `otype` key 为精确小写 `json` 时返回 JSONP，`defn` 字段本身仍是 JSON 字符串
- 接口 2 的批量返回是重复 `<results>` 块，不是旧假设里的 `<field>` 列表
- `defn` 里的关键键包括：
  - `audio`
  - `sd`
  - `hd`
  - `shd`
  - `fhd`
  - `uhd`
  - `source`

当前已经确认：

- `video_ids` 是重复 XML 标签
- `nomal_ids` / `vip_ids` 是 XML 里的 JSON 数组字符串
- `cover_list` / `category_map` / `vWH` 在接口 2 里都可能是重复标签
- `hd` 和 `shd` 需要拆开理解，不能再合并成一列“高清”
- API1 在单 key query 下，`tid` 和 `idlist` 是硬参数；`appid / appkey` 当前 live 行为有明显分支，不能简单当普通必填鉴权参数；如果同名 key 重复，当前 tested branch 观察到 `tid / idlist` 以首值生效
- API1 的 repeated `appid / appkey` 现在也已经补出当前 tested collision branches 的口径：在“canonical numeric appid + 错误 appkey”这类已测对撞组里，首值决定最终走严格校验还是旁路分支
- API2 的错误默认仍走 `HTTP 200`；当且仅当单个 `otype=json` key 生效时，成功和失败都会走 `QZOutputJson=...;` 或 callback-style 的 JSONP 包裹；如果 `otype` 重复，当前已测对撞组由首值决定 XML / JSONP 外壳；而 API2 JSONP 的 `callback` 当前只对已测 value family 有较强证据：`callback=1 / cb1 / QZOutputJson / foo.bar / a-b / a[b] / $cb / foo bar / foo,bar / [0] / 中文 / a) / ) / a;b / a'b / a\"b / a/ / a\\ / //a / /*a / [ / [[` 会改写默认 `QZOutputJson=` 包裹，空 `callback=` 会回落默认壳，`callback=a(` / `callback=((` / `callback=})();` 以及后续补到的 `callback=[(` / `callback={(` / `callback=/*(` / `callback=a[(` / `callback=)(` / `callback=](` / `callback=}(` 会打成当前摘要路径不可解析；但这仍只是 practical value-space，不外推成完整 callback 语法闭环；`union_platform` 当前在匿名 canonical branches 和真实匿名 visitor cookie replay 下都未观察到可见行为差异，但这不代表已经证明它在 `aged-cookie / login-state` 下也全局无作用
- 真实匿名 visitor cookie replay 现已补完：新增 [analysis/anonymous_real_cookie_env_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/anonymous_real_cookie_env_20260621.json)、[analysis/environment_matrix_anonymous_real_cookie_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_anonymous_real_cookie_20260621.json)、[analysis/environment_matrix_anonymous_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_anonymous_real_cookie_summary_20260621.json) 和 [analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json)；当前结论是 API1/API2 契约层与已测 auth-ish extra keys 都未因真实匿名 cookie 产生新的分叉，剩余更高价值缺口转向 `aged-cookie / login-state`
- `tools/tencent_replay_bundle_runner.py` 也已经用现成真实匿名 replay 环境自测通过，正式产物见 [analysis/replay_bundle_real_summary_20260621_realcheck.json](C:/Users/lin/Documents/YM查询工具还原/analysis/replay_bundle_real_summary_20260621_realcheck.json)；说明 `env_json -> environment_matrix -> authish semantics` 这条最后一公里工具链本身已通，后面真正缺的是 `aged/login` 外部 Cookie 输入
- API1 也已经补出同样的 `32/33` 非空条目边界；当前同样按单个 `idlist` key 内的非空 CSV item 计数
- `pay_status` 目前已实测到 `5`、`6`、`7`、`8`、`9`、`15`、`16`，另外还见过空串异常壳页，但暂不把空串当稳定枚举
- `pay_status=9` 已证伪“只在动漫”
- `positive_trailer` 目前已实测到 `0`、`1`、`2`，其中 `2` 已确认不再是单点异常，也不再只落在 `type=2 / 电视剧`；它至少已经跨到 `type=10 / 综艺`，当前更适合先写成 preview-like 的小分支
- `positive_content_id` 目前强负证据仍只见 `1543606`、`1543607`，已经能确认它不是全站常量，而且 `1543607` 已覆盖电影 / 综艺 / 少儿 / 电视剧直播壳页
- `type` 目前已实测到：
  - `1` = 电影
  - `2` = 电视剧
  - `3` = 动漫
  - `4` = 体育
  - `6` = 游戏
  - `9` = 纪录片
  - `10` = 综艺
  - `22` = 音乐
  - `27` = 教育
  - `28` = 科技
  - `29` = 汽车
  - `31` = 生活
  - `106` = 少儿
  - `111` = 文化历史
  - `113` = 表演演出
- `F=0/F=4` 明显偏预告类，`F=2/F=7` 都属于可播条目桶，但分工不能简单翻译成“正片/花絮”或“免费/VIP”；其中 `F=2` 也能命中短运营内容
- `state` 目前已实测到 `4`、`8`
- `upload_src` 目前已实测到 `0`、`6`、`7`、`20`、`31`、`105`、`107`、`108`、`116`、`117`、`129`、`138`、`141`、`146`、`149`、`2048`
- 接口 2 的 `idlist` 单次批量上限，当前实测是单个 `idlist` key 内 `32` 个非空 CSV item；重复值和无效值也占名额；多个 `idlist` key 当前不会 merge，tested branch 只消费首个值
- `publish_date / targetid` 更像受“页型 + 编排形态”影响，而不只是受 `type` 影响
- 部分体育页型当前常见 `targetid` 强阴性，但这属于页型观察，不是 `type=4 / 体育` 的全局命名；`pay_status=15` 现已在 focused search 里补到第 4 个综艺样本，`pay_status=16` 的代表 cover 也已扩到 9 个

## 研究归档

- [analysis/environment_matrix_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_20260619.json)
  - 环境维度矩阵：哪些结论在不同 UA / 头环境 / 批量形态下仍稳定
- [analysis/environment_page_shape_extension_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_extension_20260619.json)
  - 第二代表样本环境扩展：补电影 / 动漫 / 电视剧 / 综艺 / 少儿 / 专题页的 same-day 稳定性
- [analysis/pay_status_manual_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/pay_status_manual_followup_20260619.json)
  - `pay_status=9/15/16` 定向 followup：把文档里已提到的综艺 / 衍生页样本补成机器证据
- [analysis/api2_jsonp_batch_matrix_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_batch_matrix_20260620.json)
  - API2 单个 `otype=json` + 单个 `idlist` key focused batch closure：把 mixed / duplicate / empty-slot / 32/33 这 4 条 JSONP 镜像 case 补成 8 环境机器证据
- [analysis/frontend_semantic_map_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_semantic_map_20260619.json)
  - 前端语义层：SSR、bundle、请求链之间的字段映射
- [analysis/frontend_field_consumption_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_field_consumption_20260619.json)
  - 每个重点字段目前在前端是逻辑分支、展示字段，还是暂未观察到消费
- [analysis/frontend_backend_mismatch_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_backend_mismatch_20260619.json)
  - API 原值、SSR 值、前端消费值之间的改写/归一化/遗漏
- [analysis/frontend_startup_payload_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_payload_probe_20260619.json)
  - 代表页 startup / SSR payload 抽样：哪些字段首屏就出现，哪些仍未进入 detail startup 主链
- [analysis/frontend_runtime_store_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_runtime_store_probe_20260619.json)
  - 浏览器级 runtime store 抽样：前端 `union` store 里到底保留了哪些字段，哪些 raw 值已经被归一化或丢掉
- [analysis/frontend_row_shell_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_row_shell_probe_20260620.json)
  - row-shell followup：对 `问心2` / `五哈热点一网打尽` 的 detail slice 再补一轮可见卡片与 runtime row 映射，当前仍偏负
- [analysis/frontend_row_network_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_row_network_probe_20260620.json)
  - row-shell network followup：同两页继续抓 document/xhr/script 响应，当前还能稳定看到 `positive_trailer/state`，但仍没补出 `F/upload_src`
- [analysis/frontend_row_schema_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_row_schema_probe_20260620.json)
  - visible-card row schema followup：把可见卡片标题回勾到 `PageService/getPage` 行对象，当前两页都继续不带 `F/upload_src`
- [analysis/frontend_nondetail_chain_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_nondetail_chain_probe_20260620.json)
  - non-detail-targeted chain probe：3 个 cover-like 输入页仍都重定向进 detail，但 kids free pack 已打出更大的 `c_covers / cover_list` 合并链，`getPage / FillUnionInfo` 里仍没补出 `F/upload_src`
- [analysis/frontend_true_nondetail_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_true_nondetail_probe_20260620.json)
  - stronger non-detail 候选 probe：`教育 cover-only / 电视剧专题壳 / 纪录片专题壳` 这 3 条也都重定向进 detail；request-side 只打到 `getPage + FillUnionInfo`，`getCoverInfoBatch` 目前只在 bundle code reference 里出现
- [analysis/frontend_startup_vs_runtime_diff_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_vs_runtime_diff_20260620.json)
  - cross-artifact frontend diff：把 tested redirected-detail slice 压成 `startup/SSR -> getPage -> FillUnionInfo` 的字段出现/缺失/改形差分，并补了一轮 detail bundle 命名字串审计
- [analysis/state8_positive_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/state8_positive_environment_20260620.json)
  - `state=8` 正 family 环境闭环：`482396nuyaelv0e` 与 `mzc002006tgfqvp` 在 8 个请求环境下同日稳定，且和 `2026-06-19` 的 `state/upload_src` 分布一致
- [analysis/enum_escape_search_parent_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_escape_search_parent_20260620.json)
  - 父线程 focused search spot-check：`pay_status=15` 补到第 4 个样本，`pay_status=16` 在本轮继续只落 `10/综艺`
- [analysis/pay_status_15_family_expansion_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/pay_status_15_family_expansion_20260620.json)
  - `pay_status=15` 双 seed related-cover / field-union 扩圈：这轮没再长出新 cover，但把两条“推市营业中”运营支的共同签名压实了
- [analysis/agent_round_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/agent_round_summary_20260620.json)
  - 6 个代理本轮合并摘要：`15/16/2048/state=8/F-upload_src` 的新证据、边界和 guardrail
- [analysis/upload_src_2048_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_followup_20260619.json)
  - `upload_src=2048` live followup：把 2 个独立 cover 的机器证据单独落盘
- [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json)
  - `upload_src=2048` 环境矩阵摘要：`2` 个 pure `2048` 正例、`1` 个 mixed `2048/108` cover、`1` 个 same-type pure-0 negative 在 8 个请求环境下都无漂移
- [analysis/upload_src_2048_type111_search_expansion_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_type111_search_expansion_20260620.json)
  - search-backed `type=111` 扩圈：当前 sampled slice 已同时出现 complete pure-2048、mixed `2048/108`、mixed `2048/0`、pure `108`、pure `0`，并首次补到 pure-2048 + empty `targetid` 反例
- [analysis/enum_index_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_index_20260619.json)
  - 枚举字段总索引
- [analysis/enum_cards_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_cards_20260619.json)
  - 枚举值卡片：样本、相关性、反例、当前结论、未确认项
- [analysis/gap_ledger_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/gap_ledger_20260619.json)
  - 当前还没闭合的 gap，总结后续多 agent 轮次怎么继续压

## 实测样例

```text
https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html
```

当前已整理出的关键值：

- `CID = mzc00200idzf2m8`
- `VID = z4102qfi0x4`
- 标题：`飞驰人生3`
- 类型：`电影`
- 时长：`7550` 秒

## 构建产物

GitHub Actions 会产出两个工件：

- `tencent-video-query-windows-amd64.exe`
  - 由 Go 示例交叉编译得到
- `tencent-video-query-debug.apk`
  - 由最小 Android 客户端工程构建得到

目前 APK 先走 `debug` 构建，优点是简单、稳定、方便先跑通远端构建链路；后续如果你要发正式包，再补签名和 release workflow 就行。

## 本地归档

`analysis/` 和 `recovered/` 现在只当作本地归档目录使用，不属于项目主内容，也不会纳入仓库主叙事。
