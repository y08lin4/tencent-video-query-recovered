# Tencent Video Query Recovered

这两个接口的核心用处，是把一个腾讯视频页面 URL 逐步转换成可用的数据结果：

- 先用接口 1 把 `CID` 转成节目级元信息和 `VID` 列表
- 再用接口 2 按 `VID` 获取视频标题、时长、页面地址、清晰度资源大小等详情

它们适合用来做这几类事情：

- 从腾讯视频页面 URL 提取结构化信息
- 批量查询某个节目或影片对应的视频 ID
- 获取视频时长、清晰度体积、封面和基础元数据
- 封装成命令行工具、接口服务、桌面工具或移动端查询工具

这个仓库现在围绕三块内容展开：

1. 两个腾讯视频接口的说明文档
2. Python / Go 调用示例
3. GitHub Actions 远端构建产物：
   - Windows `exe`
   - Android `apk`

项目主线不再讨论来源背景，直接聚焦接口本身和可运行示例。

当前仓库里的字段说明和示例实现，基于 2026-06-18 对 4 个真实样本 URL 的 live 测试结果整理，不再只是单样本猜测。

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
  - 多 URL 字段巡检脚本，会输出 cover / video / defn 字段矩阵
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
