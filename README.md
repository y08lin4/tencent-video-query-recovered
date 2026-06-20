# Tencent Video Query Recovered

这两个接口的核心用处，是把一个腾讯视频页面 URL 逐步转换成可用的数据结果：

- 先用接口 1 把 `CID` 转成节目级元信息和 `VID` 列表
- 再用接口 2 按 `VID` 获取视频标题、时长、页面地址、清晰度资源大小等详情

它们适合用来做这几类事情：

- 从腾讯视频页面 URL 提取结构化信息
- 批量查询某个节目或影片对应的视频 ID
- 获取视频时长、清晰度体积、封面和基础元数据
- 封装成命令行工具、接口服务、桌面工具或移动端查询工具

到 2026-06-20 为止，这个仓库已经不只是“能调通接口”的状态，而是把两类能力边界也摸清了一大半：

- 接口 1：`CID -> cover 元信息 + VID 集合 + cover 级枚举`
- 接口 2：`VID -> 单视频详情 + defn + 分类链 + 批量返回`
- 当前已补出主要契约与高信号规律：`type`、`pay_status`、`positive_trailer`、`state`、API1/API2 参数契约；`F` 的黑盒 family 已较稳，但在当前 tested detail + row-shell followup 里前端命名读取仍偏负；`upload_src` 现在不只停在形态确认，在当前 tested redirected-detail frontend slice 里也已经补出更强的 scoped-negative 证据；`positive_content_id` 仍以形态确认为主，而 `downright` 的单码语义仍待命名，但字段级前端用途已经坐实为下载工具栏 gating
- 新增增强层：前端语义层、环境维度矩阵、枚举值卡片化
- 新增确认：前端已坐实 `state` 会进入“未上架 / 下架 / 删除 / 不可播”校验分支；sampled runtime `union.coverInfoMap` 的 `pay_status` 已确认不是 raw API 直通；`upload_src=2048` 已不止 2 个正例 cover，且已经补出 same-type 纯 `0` 反例和 `2048/108` 混合 cover；2026-06-20 的 row-shell / network followup 里 `state/positive_trailer` 继续可见，但 `F/upload_src` 仍未补出正例
- 同日继续补强：已测 visible-card `getPage` row schema 也继续不带 `F/upload_src`；更稳的说法是，这个结论当前不只覆盖两条代表性 redirected detail 路径，还覆盖 3 个 stronger non-detail 候选在重定向进 detail 之后的 request/response slice；下一跳更该追 `getPage` tagged shaping、真实 `getCoverInfoBatch` 请求，或 SSR / vector-layout 提前整形
- 新增闭环：`frontend_startup_vs_runtime_diff_20260620.json` 已把 tested redirected-detail slice 压成更清楚的字段差分：`positive_trailer` 能从 startup/SSR 进 sampled `getPage`，`state` 会在 `FillUnionInfo` 补回来，`F` 目前仍停在 startup/SSR 可见层，而 `upload_src` 目前在 startup/SSR、sampled `getPage / FillUnionInfo`、以及 tested detail bundle 命名字串层都没命中
- 新增前端链路边界：`frontend_row_network_request_capture_20260620.json` 已把两条最强 redirected-detail 候选再做一轮 request-side + response-side 抓取；当前仍只看到 `PageService/getPage + FillUnionInfo`，没有真实 `getCoverInfoBatch` 请求
- 新增 targetid 边界：`frontend_targetid_report_identity_owner_bridge_20260620.json` 已把匿名评论举报 DOM 周边的 dataset / framework-owner 浅层身份也扫了一轮；当前仍只停在 `feed_id / cp_id` 这套身份族，`commentInfo.targetid/commentid` 的 natural producer 还没闭合，但负证据范围已经更清楚
- 新增环境闭环：`state=8` 正 family 已把 `482396nuyaelv0e` 和 `mzc002006tgfqvp` 补到 8 环境 same-day 稳定，且 `state/upload_src` 分布与 `2026-06-19` 基线一致；这能收紧“state=8 更像行级 small-family signal”的环境适用范围，但仍不把它写成页型桶
- 同日补到：`upload_src_2048_environment_20260620.json` 已把核心环境测试集里的 `2` 个 pure `2048` 正例、`1` 个 mixed `2048/108` cover、`1` 个 same-type pure-0 negative 补到 `8` 环境无漂移；这关闭的是 tested slice 的环境稳定性，不是跨出 `type=111` 的 family boundary
- 新增契约闭环：`api2_jsonp_batch_matrix_20260620.json` 已把 `otype=json` 的 `mixed valid+invalid / duplicate+empty / dup32 / dup33` 4 条镜像 batch case 补到 8 环境 same-day 稳定；当前最稳结论是 JSONP 只换外壳，不改这些 batch semantics
- 新增扩圈：`upload_src_2048_type111_search_expansion_20260620.json` 已把 `type=111` 的 sampled slice 扩到舞蹈 / 国画 / 书法教学三支，并首次补到 complete pure-2048 + empty `targetid` 反例 `mzc00200tjnrzs3`，所以 `upload_src=2048 => targetid 非空` 不再成立
- 额外确认：腾讯视频搜索后端可以作为补样本入口，用来继续发现新的 `CID / type / pay_status`
- 当前环境矩阵仍属于 same-day 结论；第二代表样本扩展里的多页已继续稳定，但按严格“桶级首代表 + 第 2 代表”口径，目前真正闭环的仍主要是 `电影单片 / 动漫季页 / 少儿免费合集`；`sec-ch-ua / sec-fetch-* / cookie` 真实浏览器头、sports replay 第 2 代表页和跨日复测还在继续补

研究状态导航：

- [docs/tencent_video_apis.md#9-已明确--未明确](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#10-枚举值状态表](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#11-前端语义层观察](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)
- [docs/tencent_video_apis.md#12-环境维度适用范围](C:/Users/lin/Documents/YM查询工具还原/docs/tencent_video_apis.md)

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
- [tools/tencent_enum_cards.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_enum_cards.py)
  - 从当前 `analysis` 结果自动合成枚举索引和枚举值卡片
- [android](C:/Users/lin/Documents/YM查询工具还原/android)
  - 最小 Android 客户端工程
- [.github/workflows/build-artifacts.yml](C:/Users/lin/Documents/YM查询工具还原/.github/workflows/build-artifacts.yml)
  - GitHub Actions 远端构建 `exe` 和 `apk`

## 当前内容重点

- URL 可先提取 `CID`
- 接口 1 返回 XML，核心字段是 `video_ids`
- 接口 2 返回 XML，但 `defn` 字段本身是 JSON 字符串
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
- API1 的硬参数是 `tid` 和 `idlist`；`appid / appkey` 当前 live 行为有明显分支，不能简单当普通必填鉴权参数
- API2 的错误默认仍走 `HTTP 200`；`otype=json` 成功和失败都会走 `QZOutputJson=...;` 的 JSONP 包裹，`union_platform` 当前看起来被忽略
- API1 也已经补出同样的 `32/33` 非空条目边界
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
- 接口 2 的 `idlist` 单次批量上限，当前实测是 `32` 个非空 item；重复值和无效值也占名额
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
  - API2 `otype=json` focused batch closure：把 mixed / duplicate / empty-slot / 32/33 这 4 条 JSONP 镜像 case 补成 8 环境机器证据
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
