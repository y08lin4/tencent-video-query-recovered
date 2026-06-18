# 腾讯视频两个接口说明

这份文档只聚焦两个接口本身：它们分别做什么、输入什么、返回什么、字段代表什么，以及应该怎么串起来使用。

## 1. 整体逻辑

这套调用链可以概括成：

1. 输入一个腾讯视频页面 URL
2. 从 URL 中提取 `CID`
3. 调用接口 1，用 `CID` 换出节目/影片级信息和 `VID`
4. 调用接口 2，用 `VID` 换出视频详细信息
5. 对时长和清晰度资源大小做格式化
6. 输出表格或 JSON

也就是：

- 输入：腾讯视频 URL
- 中间值：`CID`、`VID` 列表
- 输出：视频标题、VID、时长、音频/清晰度资源大小等信息

一个最小调用链路大致是：

```python
cid = extract_cid_from_url(url)
cover_info = fetch_cover_info(cid)
details = fetch_video_details(cover_info["video_ids"])
```

## 2. URL 到 CID 的提取规则

已确认支持两种 URL 形态：

```text
https://v.qq.com/x/cover/<cid>/<vid>.html
https://v.qq.com/x/cover/<cid>.html
```

对应的提取逻辑可以写成：

```python
patterns = [
    r"/cover/([^/]+)/[^/]+\.html",
    r"/cover/([^/]+)\.html",
]
```

所以这套链路的第一步不是直接从 URL 提取 `VID`，而是优先提取 `CID`。

## 3. 接口 1：CID -> 节目元信息 + VID 列表

### 3.1 作用

接口 1 的核心能力是：

- 根据 `CID` 获取节目、影片或 cover 级别元信息
- 返回一个或多个 `VID`
- 提供是否 VIP、是否付费、封面图、集数信息等附加字段

对单部电影来说，通常只会拿到一个主 `VID`。  
对剧集、综艺这类内容，理论上可能拿到多个 `VID`。

### 3.2 请求地址

```text
https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

### 3.3 参数说明

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `tid` | `431` | 当前研究样例里的固定值 |
| `idlist` | `mzc00200idzf2m8` | 输入的 `CID` |
| `appid` | `10001005` | 当前研究样例里的固定值 |
| `appkey` | `0d1a9ddd94de871b` | 当前研究样例里的固定值 |

### 3.4 返回格式

- 返回体是 XML
- 常用关注点：
  - `.//video_ids`
  - `.//error`

如果返回中带 `.//error`，一般应视为接口调用失败。

### 3.5 关键能力

这个接口至少具备以下能力：

- `CID -> 主视频 VID`
- `CID -> clip 列表`
- `CID -> 标题、类型`
- `CID -> VIP/付费状态`
- `CID -> 横版/竖版封面图`
- `CID -> 集数/更新状态`

### 3.6 关键字段说明

| 字段 | 示例值 | 含义 | 置信度 |
| --- | --- | --- | --- |
| `cover_id` | `mzc00200idzf2m8` | 当前内容的 cover/CID | 高 |
| `title` | `飞驰人生3` | 节目或影片标题 | 高 |
| `type` | `1` | 内容类型编号 | 中 |
| `type_name` | `电影` | 内容类型名称 | 高 |
| `video_ids` | `z4102qfi0x4` | 主视频 `VID` 列表，逗号分隔时可表示多个 | 高 |
| `clips_ids` | 多个 clip-like ID | 片段、分段或附加条目列表 | 中 |
| `nomal_ids` | `[{"F":7,"V":"z4102qfi0x4"}]` | 常规播放条目列表，字段名原样如此拼写 | 中 |
| `vip_ids` | `[{"F":7,"V":"z4102qfi0x4"}]` | VIP 条目列表 | 高 |
| `pay_status` | `6` | 付费/VIP 状态位 | 中 |
| `new_pic_hz` | 图片 URL | 横版封面图 | 高 |
| `new_pic_vt` | 图片 URL | 竖版封面图 | 高 |
| `episode_all` | 数值 | 总集数 | 中 |
| `episode_updated` | 数值 | 当前更新到第几集 | 中 |
| `downright` | 数值 | 下载/权益相关状态字段 | 低到中 |
| `positive_content_id` | ID | 正片内容 ID | 中 |
| `positive_trailer` | 标志位 | 是否预告/正片相关标志 | 低到中 |
| `column_id` | ID | 专栏或栏目维度 ID | 低到中 |
| `topic_id_list` | ID 列表 | 话题或专题关联字段 | 低到中 |

### 3.7 调用示例

`curl`：

```bash
curl "https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b"
```

Python：

```python
import requests
import xml.etree.ElementTree as ET

cid = "mzc00200idzf2m8"
url = (
    "https://data.video.qq.com/fcgi-bin/data"
    "?tid=431"
    f"&idlist={cid}"
    "&appid=10001005"
    "&appkey=0d1a9ddd94de871b"
)

resp = requests.get(url, timeout=10)
resp.raise_for_status()
root = ET.fromstring(resp.text)

video_ids = [node.text for node in root.findall(".//video_ids") if node.text]
print(video_ids)
```

### 3.8 简化返回片段

```xml
<root>
  <cover_id>mzc00200idzf2m8</cover_id>
  <title>飞驰人生3</title>
  <type>1</type>
  <type_name>电影</type_name>
  <video_ids>z4102qfi0x4</video_ids>
  <clips_ids>...</clips_ids>
  <nomal_ids>[{"F":7,"V":"z4102qfi0x4"}]</nomal_ids>
  <vip_ids>[{"F":7,"V":"z4102qfi0x4"}]</vip_ids>
  <pay_status>6</pay_status>
  <new_pic_hz>https://...</new_pic_hz>
  <new_pic_vt>https://...</new_pic_vt>
</root>
```

## 4. 接口 2：VID -> 视频详细信息

### 4.1 作用

接口 2 的核心能力是：

- 根据一个或多个 `VID` 批量查询视频详情
- 返回标题、时长、视频页 URL、封面、标签、发布时间等信息
- 返回 `defn` 字段，用于描述不同清晰度资源大小

这个接口是最终展示结果的直接数据来源。

### 4.2 请求地址

```text
https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=<VID>
```

如果是多个 `VID`，则放在同一个 `idlist` 中，逗号分隔。本仓库示例脚本默认按每批 10 个处理。

### 4.3 参数说明

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `otype` | `xml` | 明确要求返回 XML |
| `tid` | `535` | 当前研究样例里的固定值 |
| `appid` | `20001238` | 当前研究样例里的固定值 |
| `appkey` | `6c03bbe9658448a4` | 当前研究样例里的固定值 |
| `union_platform` | `3` | 当前研究样例里的固定值 |
| `idlist` | `z4102qfi0x4` | 一个或多个 `VID` |

### 4.4 返回格式

- 外层是 XML
- 每个视频详情位于一个 `.//field`
- 常用关注点：
  - `.//title`
  - `.//duration`
  - `.//vid`
  - `.//defn`
  - `.//error`

其中 `defn` 本身又是一个 JSON 字符串，这一点很关键。

### 4.5 关键能力

这个接口至少具备以下能力：

- `VID -> 标题`
- `VID -> 时长`
- `VID -> 页面 URL`
- `VID -> 清晰度资源大小`
- `VID -> 封面图`
- `VID -> 标签、关键词、演员、发布时间`

### 4.6 关键字段说明

| 字段 | 示例值 | 含义 | 置信度 |
| --- | --- | --- | --- |
| `vid` | `z4102qfi0x4` | 视频 ID | 高 |
| `title` | `飞驰人生3` | 视频标题 | 高 |
| `duration` | `7550` | 时长，单位秒 | 高 |
| `url` | `https://v.qq.com/x/page/z4102qfi0x4.html` | 视频访问地址 | 高 |
| `defn` | `{"audio":...,"hd":...}` | 各清晰度资源大小映射，JSON 字符串 | 高 |
| `cover_list` | 含 `mzc00200idzf2m8` | 关联 cover/CID 列表 | 高 |
| `desc` | 文本 | 简介 | 中 |
| `publish_date` | 日期 | 发布日期 | 中 |
| `create_time` | 时间戳/时间串 | 记录创建时间 | 中 |
| `modify_time` | 时间戳/时间串 | 记录更新时间 | 中 |
| `state` | 数值 | 状态字段 | 低到中 |
| `tag` | 文本/列表 | 标签 | 中 |
| `keyword` | 文本 | 关键词 | 中 |
| `leading_actor` | 文本 | 主演信息 | 中 |
| `category_map` | 结构化数据 | 分类映射 | 中 |
| `pic160x90` | 图片 URL | 小尺寸封面 | 中 |
| `pic496x280` | 图片 URL | 中尺寸封面 | 中 |
| `pic_640_360` | 图片 URL | 大尺寸封面 | 中 |
| `vWH` | 结构化值 | 分辨率相关字段 | 中 |
| `targetid` | ID | 目标内容 ID | 低到中 |
| `upload_src` | 标志位/来源值 | 上传来源或来源类型 | 低到中 |

### 4.7 `defn` 字段的实际意义

`defn` 不是普通文本，而是一个 JSON 对象。本仓库当前示例正是靠它来生成“音频 / 标清 / 高清 / 蓝光 / 4K”这几类结果。

真实样例中观察到的键包括：

| `defn` 键 | 含义 | 备注 |
| --- | --- | --- |
| `audio` | 音频资源大小 | 直接映射到 `音频` |
| `sd` | 标清资源大小 | 样例里未出现也属正常 |
| `hd` | 高清资源大小 | 可能和 `shd` 同时存在 |
| `shd` | 更高一级的高清/超清资源大小 | 适合单独展示出来 |
| `fhd` | 蓝光/全高清资源大小 | 常映射到 `蓝光` |
| `uhd` | 4K 资源大小 | 常映射到 `4K` |
| `source` | 原始片源或源文件大小 | 可选扩展字段 |

一个常见的格式化逻辑大致是：

```python
audio = format_size(defn_data.get("audio"))
sd = format_size(defn_data.get("sd"))
hd = format_size(defn_data.get("hd"))
shd = format_size(defn_data.get("shd"))
fhd = format_size(defn_data.get("fhd"))
uhd = format_size(defn_data.get("uhd"))
source = format_size(defn_data.get("source"))
```

这里要注意一个细节：如果只从字段字面看，`shd` 更像“超清”。所以展示层到底应该把 `hd` 还是 `shd` 归到“高清”列，仍然值得继续用更多样本校准。

### 4.8 调用示例

`curl`：

```bash
curl "https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4"
```

Python：

```python
import json
import requests
import xml.etree.ElementTree as ET

vid = "z4102qfi0x4"
url = (
    "https://union.video.qq.com/fcgi-bin/data"
    "?otype=xml"
    "&tid=535"
    "&appid=20001238"
    "&appkey=6c03bbe9658448a4"
    "&union_platform=3"
    f"&idlist={vid}"
)

resp = requests.get(url, timeout=10)
resp.raise_for_status()
root = ET.fromstring(resp.text)

for field in root.findall(".//field"):
    title = field.findtext(".//title")
    duration = field.findtext(".//duration")
    defn_raw = field.findtext(".//defn") or "{}"
    defn = json.loads(defn_raw)
    print(title, duration, defn)
```

### 4.9 简化返回片段

```xml
<root>
  <field>
    <vid>z4102qfi0x4</vid>
    <title>飞驰人生3</title>
    <duration>7550</duration>
    <url>https://v.qq.com/x/page/z4102qfi0x4.html</url>
    <cover_list>mzc00200idzf2m8</cover_list>
    <defn>{"audio":49836544,"fhd":4284008562,"hd":500215446,"shd":775278845,"source":39050354633,"uhd":13955191741}</defn>
  </field>
</root>
```

## 5. 实测样例：`飞驰人生3`

### 5.1 输入 URL

```text
https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html
```

### 5.2 第一步解析结果

- `CID = mzc00200idzf2m8`
- `VID = z4102qfi0x4`

说明：

- 这个 URL 本身已经带了 `VID`
- 但本仓库的推荐流程仍然是先提 `CID`，再走接口 1 查 `VID`

### 5.3 接口 1 返回中的关键值

| 字段 | 实测值 |
| --- | --- |
| `cover_id` | `mzc00200idzf2m8` |
| `title` | `飞驰人生3` |
| `type` | `1` |
| `type_name` | `电影` |
| `video_ids` | `z4102qfi0x4` |
| `nomal_ids` | `[{"F":7,"V":"z4102qfi0x4"}]` |
| `vip_ids` | `[{"F":7,"V":"z4102qfi0x4"}]` |
| `pay_status` | `6` |
| `new_pic_hz` | 横版封面 URL |
| `new_pic_vt` | 竖版封面 URL |

### 5.4 接口 2 返回中的关键值

| 字段 | 实测值 |
| --- | --- |
| `title` | `飞驰人生3` |
| `vid` | `z4102qfi0x4` |
| `duration` | `7550` |
| 格式化时长 | `02:05:50` |
| `url` | `https://v.qq.com/x/page/z4102qfi0x4.html` |
| `cover_list` | 包含 `mzc00200idzf2m8` |

`defn` 的实测值：

```json
{
  "audio": 49836544,
  "fhd": 4284008562,
  "hd": 500215446,
  "shd": 775278845,
  "source": 39050354633,
  "uhd": 13955191741
}
```

格式化后可读值：

| 项目 | 原始值 | 格式化结果 |
| --- | --- | --- |
| `audio` | `49836544` | `47.5 MB` |
| `hd` | `500215446` | `477.0 MB` |
| `shd` | `775278845` | `739.4 MB` |
| `fhd` | `4284008562` | `4.0 GB` |
| `uhd` | `13955191741` | `13.0 GB` |
| `source` | `39050354633` | `36.4 GB` |

如果按本仓库当前的展示口径，这个样例最终可以整理为：

| 视频标题 | 视频VID | 影片时长 | 音频 | 标清 | 高清 | 超清 | 蓝光 | 4K |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 飞驰人生3 | z4102qfi0x4 | 02:05:50 | 47.5 MB | - | 477.0 MB | 739.4 MB | 4.0 GB | 13.0 GB |

## 6. 错误处理与边界情况

按本仓库当前示例实现，至少应该考虑下面几类异常：

- URL 为空
- URL 中无法提取 `CID`
- 接口 1 请求失败
- 接口 1 返回 XML 解析失败
- 接口 1 返回 `.//error`
- 接口 1 没找到任何 `VID`
- 接口 2 请求失败
- 接口 2 返回 XML 解析失败
- 接口 2 返回 `.//error`
- 接口 2 里的 `defn` JSON 解析失败

## 7. 对这两个接口的最终理解

如果只用一句话概括：

- 接口 1 负责把“腾讯视频页面/节目层 ID”转换成“视频层 ID”
- 接口 2 负责把“视频层 ID”转换成“用户真正想看的详细信息”

所以它们不是平级替代关系，而是明显的上下游关系：

```text
URL -> CID -> 接口1 -> VID -> 接口2 -> 表格结果
```

## 8. 备注

- 这份文档基于真实样例验证和调用链整理而成。
- 接口 URL、关键参数、核心字段、主流程是高置信度结论。
- 个别字段的精确业务语义，例如某些状态位、某些枚举值，仍适合继续补样本验证。
