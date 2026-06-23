# 环境回放执行手册

这份手册只做一件事：

把当前仓库里**还没有闭环**的 `aged-cookie / login-state` 环境回放，整理成一套可以直接执行的步骤。

它的目标不是重复参数研究结论，而是把下面这些问题压成明确动作：

- 你需要准备什么输入
- 这些输入应该放到哪个文件
- 先跑哪个命令
- 产物会落到哪里
- 跑完以后最值得先看哪几份结果

## 0. 什么时候需要看这份

当你已经接受下面这件事时，就应该直接看这份手册：

- 当前仓库内的匿名直连闭环已经比较实
- 当前真正最高价值的剩余缺口，主要就是：
  - `aged-cookie replay`
  - `login-state replay`
  - 在这两个环境下复测 `union_platform`
  - 在这两个环境下复测 `auth-ish extra keys`

如果你只是想直接调用匿名直连能力，先看：

- [analysis/direct_call_parameter_total_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_parameter_total_table_20260621.json)
- [analysis/direct_call_capability_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_capability_table_20260621.json)
- [docs/direct_call_playbook.md](C:/Users/lin/Documents/YM查询工具还原/docs/direct_call_playbook.md)

## 1. 你需要准备的最小输入

### aged-cookie

准备一个桌面端 Cookie header 文本文件：

- 模板：
  [examples/environment/pc_aged_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_aged_cookie_header.template.txt)

把整条 `Cookie:` 请求头的值替换进去，文件内容只保留 header value 本身。

### login-state

准备一个桌面端登录态 Cookie header 文本文件：

- 模板：
  [examples/environment/pc_login_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_login_cookie_header.template.txt)

同样只保留 `Cookie:` header 的 value。

### 可选：移动端 Cookie

如果你手里也有 mobile H5 的 Cookie header，可以一并准备。

当前最小闭环并**不要求**你必须先拿到 mobile H5；只用 PC Web 先跑一轮也有价值。

## 2. 你会得到什么 env JSON

如果你想直接理解最终 header 结构，可以先看模板：

- [examples/environment/real_cookie_env.template.json](C:/Users/lin/Documents/YM查询工具还原/examples/environment/real_cookie_env.template.json)

这个模板里已经把 6 个目标环境写好了：

- `pc_web_real_cookie_replay`
- `mobile_h5_real_cookie_replay`
- `pc_web_aged_cookie_replay`
- `mobile_h5_aged_cookie_replay`
- `pc_web_login_state_replay`
- `mobile_h5_login_state_replay`

## 3. 第一步：把 Cookie header 转成 env JSON

如果你更想直接复制现成命令模板，而不是手动读整篇手册，也可以先看：

- [analysis/tooling_entrypoint_quick_reference_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tooling_entrypoint_quick_reference_20260621.json)

里面现在已经补了：

- `aged_cookie_env_build`
- `login_state_env_build`
- `aged_cookie_environment_matrix`
- `login_state_environment_matrix`
- `aged_cookie_full_bundle`
- `login_state_full_bundle`

如果你想把“输入是否齐了、哪些步骤必须跑、跑完以后该核对什么”也交给机器可读清单来驱动，再看：

- [analysis/environment_replay_closure_checklist_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_closure_checklist_20260621.json)

### aged-cookie

```bash
python tools/tencent_cookie_env_from_headers.py ^
  --mode aged ^
  --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt ^
  --output analysis/aged_cookie_env_20260621.json
```

### login-state

```bash
python tools/tencent_cookie_env_from_headers.py ^
  --mode login ^
  --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt ^
  --output analysis/login_state_env_20260621.json
```

如果你同时有 mobile H5 Cookie，可以把 `--mobile-cookie-file` 一起带上。

## 4. 第二步：先跑环境矩阵

这一步的目标是判断：

- 基础契约有没有因为环境变化而分叉
- `missing_tid / appkey error / 32/33 boundary / JSONP mirror` 这些关键 case 有没有变

### aged-cookie matrix

```bash
python tools/tencent_environment_matrix_probe.py ^
  --extra-env-json analysis/aged_cookie_env_20260621.json ^
  --output analysis/environment_matrix_aged_cookie_20260621.json
```

### login-state matrix

```bash
python tools/tencent_environment_matrix_probe.py ^
  --extra-env-json analysis/login_state_env_20260621.json ^
  --output analysis/environment_matrix_login_state_20260621.json
```

## 5. 第三步：再跑 full semantics bundle

这一步的目标是把高价值候选项一起带上：

- `union_platform`
- `auth-ish extra keys`
- `callback` edge cases
- `540/541` 这类 alt positive tid family

### aged-cookie bundle

```bash
python tools/tencent_replay_bundle_runner.py ^
  --mode aged ^
  --env-json analysis/aged_cookie_env_20260621.json ^
  --semantics-profile full ^
  --artifact-output-dir analysis/replay_bundle_aged_cookie_20260621
```

### login-state bundle

```bash
python tools/tencent_replay_bundle_runner.py ^
  --mode login ^
  --env-json analysis/login_state_env_20260621.json ^
  --semantics-profile full ^
  --artifact-output-dir analysis/replay_bundle_login_state_20260621
```

如果要把更多 callback pathological-tail 一起带上，可以补：

```bash
--probe-extra-callback-file analysis/callback_tail_values.txt
```

## 6. 先看哪几份输出

跑完以后，不要一上来先看所有中间文件。先看这几类：

### 环境矩阵摘要

- `analysis/environment_matrix_aged_cookie_20260621.json`
- `analysis/environment_matrix_login_state_20260621.json`

先看：

- API1 `baseline_single_valid`
- API1 `missing_tid`
- API1 `canonical_appid_missing_appkey`
- API2 `baseline_xml_single`
- API2 `otype_json_single`
- API2 `all_invalid_jsonp_batch`
- API2 `duplicate_and_empty_slots_json`
- API2 `dup33_json`

### bundle 摘要

看各自 artifact dir 里的 summary 文件，重点盯：

- 有没有新增参数分支
- `union_platform` 是否开始有可见 effect
- `auth-ish extra keys` 是否开始有可见 effect
- `540/541` 是否出现环境相关的壳层变化

## 7. 这轮回放最值钱的判断标准

跑完以后，最重要的不是“有没有任何差异”，而是这 4 个问题：

1. `aged-cookie` 会不会改写 API1/API2 的基础契约
2. `login-state` 会不会让 `union_platform` 从 scoped-negative 变成有作用
3. `login-state` 会不会让 `auth-ish extra keys` 从 scoped-negative 变成有作用
4. `540/541` 会不会在真实环境下出现比匿名直连更“厚”的 detail shell

## 8. 当前不要误判的地方

- 匿名 real-cookie replay 通过，**不等于** aged-cookie / login-state 也通过
- `union_platform` 当前只是“匿名范围未观察到变化”，**不是** 全局无作用
- `auth-ish extra keys` 当前只是“匿名范围未观察到变化”，**不是** 全局无作用
- `540/541` 当前只是 alternate positive shell，**不是** `535` 的等价替代

## 9. 跑完以后该回写哪里

如果下一轮继续推进，最值得先更新的是：

- [analysis/objective_coverage_audit_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/objective_coverage_audit_20260621.json)
- [analysis/parameter_closure_matrix_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_closure_matrix_20260621.json)
- [analysis/param_gap_priority_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_gap_priority_20260620.json)
- [analysis/direct_call_delivery_manifest_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_delivery_manifest_20260621.json)

如果 aged/login 两轮都没有新分支，再回头重新评估：

- 是否还存在高价值未闭环项
- 是否可以把环境适用范围从 `partially_covered` 再往上推进

## 10. 现在已经可以当契约用的东西

这一轮又补了 3 份“无需新 Cookie 也能成立”的机器表：

- [analysis/environment_replay_runner_contract_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_runner_contract_20260622.json)
- [analysis/environment_replay_input_boundary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_input_boundary_20260622.json)
- [analysis/environment_replay_hard_block_table_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_hard_block_table_20260622.json)

它们分别回答 3 件不同的事：

- `runner_contract`：
  `tencent_replay_bundle_runner.py` 现在到底承诺了哪些输入、步骤、summary 字段、失败状态和分阶段跑法。
- `input_boundary`：
  `tencent_cookie_env_from_headers.py` 的最小输入模型是什么，哪些输入是硬要求，哪些只是可选增强。
- `hard_block_table`：
  哪些结论确实必须等 `aged-cookie / login-state` 真实头部，哪些匿名态结论现在只能保留在 scoped-negative 范围。

如果你现在只想看“下一步最短该做什么”，再直接看：

- [analysis/parameter_closure_shortlist_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_closure_shortlist_20260622.json)

这份短清单把剩余工作收成 3 层：

- `must_wait_external_inputs`
- `still_actionable_without_new_inputs`
- `lower_priority_discovery_after_environment_replay`

## 11. 当前最重要的边界，别再写过头

在拿到真实 `aged-cookie / login-state` 头部之前，下面这些话都不要升级成全局结论：

- `union_platform` 现在只能说：在**已测试匿名范围**里没观察到可见 effect
- `auth-ish extra keys` 现在只能说：在**已测试匿名范围**里没观察到可见 effect
- `callback` 的 precedence / error-shell 行为现在只能说：在**已测试匿名 replay** 范围里稳定
- `540/541` 现在只能说：当前是 alternate positive shell，不能直接当成 `535` 的环境等价分支

换句话说，这一轮新增的契约层产物，解决的是：

- 怎么跑
- 跑完会得到什么形状的产物
- 没有外部输入之前，哪些话不能先说满

它们**没有**解决的是：

- aged-cookie 会不会改写 API1/API2 契约
- login-state 会不会让 `union_platform` 生效
- login-state 会不会让 `auth-ish extra keys` 生效
- `540/541` 会不会在真实环境下变厚

这 4 个问题，还是要等真实回放证据。
