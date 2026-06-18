# 腾讯视频两个接口说明

这份文档不再用“低 / 中 / 高置信度”去模糊描述字段，而是按真实证据分层：

- `已实测确认`：已经被 2026-06-18 的真实接口返回直接坐实
- `形态已确认，业务语义待补样本`：数据长什么样已经清楚，但业务含义还需要更多样本拉开
- `仍待补样本`：字段名知道，但当前样本还不足以做稳定说明

## 1. 整体链路

```text
URL -> CID -> 接口1 -> VID -> 接口2 -> 结果
```

更具体一点：

1. 输入腾讯视频页面 URL
2. 从 URL 提取 `CID`
3. 调用接口 1，拿到 cover / 节目级信息，以及一个或多个 `VID`
4. 调用接口 2，按 `VID` 拉取单视频详细信息
5. 对 `defn` 里的清晰度体积做格式化

## 2. 本轮实测样本

本轮文档结论基于 4 个真实样本：

| 页面 URL | CID | URL 自带 VID | 标题 | 类型 |
| --- | --- | --- | --- | --- |
| `https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html` | `mzc00200idzf2m8` | `z4102qfi0x4` | 飞驰人生3 | 电影 |
| `https://v.qq.com/x/cover/mzc00200xxpsogl/j4101ouc4ve.html` | `mzc00200xxpsogl` | `j4101ouc4ve` | 剑来 第二季 | 动漫 |
| `https://v.qq.com/x/cover/mzc00200fobieel/u41010ju5vc.html` | `mzc00200fobieel` | `u41010ju5vc` | 一人之下 第6季 | 动漫 |
| `https://v.qq.com/x/cover/mzc002009qyd7nv/m4102tgsa8d.html` | `mzc002009qyd7nv` | `m4102tgsa8d` | 熊出没·年年有熊 | 电影 |

另外，为了看清 `nomal_ids` / `vip_ids` 里的 `F` 值含义，本轮还额外对部分 `VID` 做了回查。

## 3. URL 到 CID 的提取规则

已确认支持：

```text
https://v.qq.com/x/cover/<cid>/<vid>.html
https://v.qq.com/x/cover/<cid>.html
```

对应正则：

```python
patterns = [
    r"/cover/([^/]+)/[^/]+\.html",
    r"/cover/([^/]+)\.html",
]
```

## 4. 接口 1：CID -> cover / 节目级信息 + VID 集合

### 4.1 请求地址

```text
https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=<CID>&appid=10001005&appkey=0d1a9ddd94de871b
```

### 4.2 当前已确认的返回形态

接口 1 返回 XML。

这一轮最重要的结构结论是：

- `video_ids` 是 **重复 XML 标签**，一个标签对应一个 `VID`
- `clips_ids` 是 **重复 XML 标签**
- `downright` 也是 **重复 XML 标签**
- `nomal_ids` 是 **单个 XML 字段里的 JSON 数组字符串**
- `vip_ids` 是 **单个 XML 字段里的 JSON 数组字符串**
- `topic_id_list` 是 **单个 XML 字段里的 `+` 分隔 ID 串**

所以对接口 1 来说，不能把所有“多值字段”都粗暴当成 CSV。

### 4.3 接口 1 字段证据总表

| 字段 | 当前状态 | 数据形态 | 当前理解 | 本轮观察 |
| --- | --- | --- | --- | --- |
| `cover_id` | 已实测确认 | 单值 ID | 当前 cover / CID | 4/4 样本稳定 |
| `id` | 已实测确认 | 单值 ID | 与 `cover_id` 等值 | 4/4 样本稳定 |
| `title` | 已实测确认 | 单值文本 | 节目或影片标题 | 4/4 样本稳定 |
| `type_name` | 已实测确认 | 单值文本 | 内容类型名称 | 本轮见到 `电影` / `动漫` |
| `type` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 类型编号 | 本轮见到 `1`=电影，`3`=动漫 |
| `video_ids` | 已实测确认 | 重复 XML 标签 | 当前 CID 关联的 `VID` 集合 | 电影样本为 1 个；动漫样本为多集 |
| `clips_ids` | 形态已确认，业务语义待补样本 | 重复 XML 标签 | 片段 / 花絮 / 附加条目 `VID` 集合 | 多集样本里数量很多 |
| `nomal_ids` | 已实测确认 | JSON 数组字符串 | 结构化条目列表，元素含 `F` 和 `V` | 4/4 样本稳定 |
| `vip_ids` | 已实测确认 | JSON 数组字符串 | 结构化 VIP 视角条目列表 | 4/4 样本稳定 |
| `episode_all` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 总集数 / 总话数 | 只在动漫样本出现：`27`、`26` |
| `episode_updated` | 形态已确认，业务语义待补样本 | 单值展示文本 | 当前更新状态文本 | 本轮见到 `全27集`、`更新至25集` |
| `pay_status` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 收费模式状态码 | 4 个样本都是 `6`，还不足以解码枚举 |
| `downright` | 形态已确认，业务语义待补样本 | 重复 XML 标签 | 条目级权限 / 能力码序列 | 不是单个全局值 |
| `new_pic_hz` | 已实测确认 | 单值 URL | 横版封面图 | 4/4 样本稳定 |
| `new_pic_vt` | 已实测确认 | 单值 URL | 竖版封面图 | 4/4 样本稳定 |
| `topic_id_list` | 形态已确认，业务语义待补样本 | 单值 `+` 分隔 ID 串 | 话题 / 专题 ID 集合 | 4/4 样本稳定 |
| `positive_content_id` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 某种“正片”相关内部 ID | 4 个样本都为 `1543606` |
| `positive_trailer` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 某种正片 / 预告关系标记 | 4 个样本都为 `1` |
| `column_id` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 栏目 / 专栏 ID | 本轮都为 `0` |
| `cover_checkup_grade` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 某种审核 / 评级字段 | 本轮都为 `4` |
| `errorno` / `retcode` / `costtime` / `resptime` | 已实测确认 | 单值状态字段 | 服务端状态 / 耗时 / 时间戳 | 正常返回时稳定出现 |

### 4.4 `nomal_ids` / `vip_ids` 的结构

这两个字段不是普通字符串，而是 JSON 数组字符串。例如：

```json
[{"F":2,"V":"j4101ouc4ve"},{"F":2,"V":"r4101sdqwpd"}]
```

当前已经可以稳定确认：

- `V` 就是 `VID`
- `F` 是某种条目类型 / 权限层 / 内容槽位编码

但 `F` 不能简单解释成“是否 VIP”。

### 4.5 `F` 值的当前观察

基于回查结果，本轮能落到文档里的最稳观察如下：

| `F` 值 | 当前观察 | 当前结论 |
| --- | --- | --- |
| `0` | 命中过 `《剑来2》预告片_27`、`彩蛋` | 明显偏预告 / 彩蛋 / 附加短内容 |
| `2` | 命中过 `剑来2_01`、`剑来2_02`、`一人之下6_01` 到 `一人之下6_24` | 明显覆盖主正片集 |
| `4` | 命中过 `预告片_26` | 当前只看到预告型内容，样本还少 |
| `7` | 命中过整部电影、`剑来2_27`、`一人之下6_25`、`人物志`、`片尾曲`、`番外篇` | 明显不是简单的“VIP=7”，更像覆盖主正片末集、正片长内容、番外和部分特辑的混合类型 |

所以当前最稳的结论是：

- `F=0` 可以视为“预告 / 彩蛋类短内容”
- `F=2` 可以视为“主正片集”的高概率类型
- `F=7` 目前不能粗暴翻译成“VIP 内容”，它包含电影主片、末集、番外、人物志、片尾曲等

### 4.6 接口 1 目前最稳的结论

1. `video_ids` 是 **重复标签 VID 列表**
2. `nomal_ids` / `vip_ids` 是 **JSON 数组字符串**
3. `topic_id_list` 是 **`+` 分隔 ID 串**
4. `episode_all` / `episode_updated` 只在多集内容上有意义
5. `downright` 不是一个简单的全局单值，而更像 **重复的权限位序列**

### 4.7 接口 1 仍待继续补样本的点

- `pay_status` 的枚举含义
- `downright` 每个数值位的业务解释
- `positive_content_id` / `positive_trailer` 的内部语义
- `F=4` / `F=7` 的完整分类边界

## 5. 接口 2：VID -> 单视频详细信息

### 5.1 请求地址

```text
https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=<VID>
```

多 `VID` 时：

```text
idlist=vid1,vid2,vid3
```

### 5.2 当前已确认的返回形态

接口 2 同样返回 XML，但结构和我们之前文档里的“`<field>` 列表”假设不一样。

当前已确认的真实结构是：

- 单个 `VID`：

```xml
<root>
  <results>
    <fields>...</fields>
    <id>z4102qfi0x4</id>
    <retcode>0</retcode>
  </results>
</root>
```

- 多个 `VID`：

```xml
<root>
  <results>...</results>
  <results>...</results>
  <results>...</results>
</root>
```

也就是说：

- 批量响应是 **重复 `<results>` 块**
- 每个 `<results>` 下面有一个 `<fields>`
- `cover_list`、`category_map`、`vWH` 都可能是 **重复标签**

### 5.3 接口 2 字段证据总表

| 字段 | 当前状态 | 数据形态 | 当前理解 | 本轮观察 |
| --- | --- | --- | --- | --- |
| `vid` | 已实测确认 | 单值 ID | 当前视频 ID | 与批量 `<results><id>` 对齐 |
| `id` | 已实测确认 | 单值 ID | 当前 `<results>` 对应 ID | 与 `vid` 一致 |
| `title` | 已实测确认 | 单值文本 | 视频标题 | 4/4 样本稳定 |
| `duration` | 已实测确认 | 单值秒数字符串 | 时长（秒） | 4/4 样本稳定 |
| `url` | 已实测确认 | 单值 URL | 页面地址 | 4/4 样本稳定 |
| `defn` | 已实测确认 | JSON 对象字符串 | 清晰度 / 资源类型到体积的映射 | 4/4 样本稳定 |
| `cover_list` | 已实测确认 | 重复 XML 标签 | 该 `VID` 关联的 cover 列表 | 不一定只等于当前 CID |
| `c_covers` | 形态已确认，业务语义待补样本 | 单值 `+` 分隔 ID 串 | 关联 cover 集合的另一种压缩表达 | 电影样本里可见多个 cover |
| `category_map` | 形态已确认，业务语义待补样本 | 重复 XML 标签 | 扁平分类层级序列 | 数值与中文名称交替出现 |
| `vWH` | 已实测确认 | 重复 XML 标签（2 个值） | 宽高二元组 | 本轮见到 `1920x814`、`2600x1080` 等 |
| `state` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 视频状态枚举 | 4 个样本都为 `4` |
| `upload_src` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 上传 / 入库来源枚举 | 本轮见到 `20`、`129`、`108` |
| `create_time` | 形态已确认，业务语义待补样本 | 单值时间串 | 记录创建 / 入库时间 | 形如 `YYYY-MM-DD HH:MM:SS` |
| `modify_time` | 形态已确认，业务语义待补样本 | 单值时间串 | 记录修改时间 | 本轮与 `create_time` 相同 |
| `publish_date` | 形态已确认，业务语义待补样本 | 单值日期字段 | 意图上像发布日期 | 本轮样本都为空 |
| `pic160x90` / `pic496x280` / `pic_640_360` | 已实测确认 | 单值 URL | 各尺寸封面图 | 4/4 样本稳定 |
| `targetid` | 形态已确认，业务语义待补样本 | 单值 ID / 空值 | 某种目标实体 ID | 本轮为空 |
| `is_normalized` | 形态已确认，业务语义待补样本 | 单值数值字符串 | 服务端内部状态位 | 本轮稳定但语义未解码 |
| `cover_pic_resolution` / `pioneer_tag_ids` | 仍待补样本 | 单值或重复值 | 当前样本不足 | 只在少量样本出现或为空 |

### 5.4 `defn` 的当前最稳解释

`defn` 是接口 2 里最值得单独说明的字段。

它不是普通文本，而是 JSON 对象字符串，例如：

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

#### 推荐展示口径

| raw key | 推荐中文名 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| `audio` | 音频 | 已实测确认 | 独立音频资源体积 |
| `sd` | 标清（SD） | 形态已确认，业务语义待补样本 | 这 4 个样本里没出现，但命名稳定 |
| `hd` | 高清（HD） | 已实测确认 | 不能再和 `shd` 混成一列 |
| `shd` | 超清（SHD） | 已实测确认 | 比 `hd` 更高一档 |
| `fhd` | 全高清 / 蓝光（FHD） | 已实测确认 | 文档里建议保留 `FHD` 原始键名语义 |
| `uhd` | 超高清 / 4K（UHD） | 已实测确认 | 不建议只写“4K”而丢掉原始键名 |
| `source` | 源片 / 原始片源（SOURCE） | 已实测确认 | 明显不是普通消费档位，体积远大于 `uhd/fhd` |

这一轮最重要的修正是：

- `hd` 和 `shd` 必须拆开
- `source` 不该和常规清晰度档位平铺在一行里
- 文档展示时应该保留 raw key，避免以后再次把 `hd/shd` 混掉

### 5.5 `cover_list` / `category_map` / `vWH`

#### `cover_list`

- 是重复 XML 标签
- 表示该 `VID` 关联的 cover 列表
- 不一定只包含“当前 URL 的 CID”

例如 `z4102qfi0x4` 的 `cover_list` 不止一个值，说明它可能同时挂在单片页和合集页下。

#### `category_map`

当前最稳的解释不是“真正的 map”，而是：

- 一个按 `id,name,id,name...` 扁平展开的分类层级序列

电影样本实测：

```text
10139, 正片, 1037, 电影, 1, 电影
```

动漫样本实测：

```text
10994, 正片, 1204, 动漫, 3, 动漫
```

#### `vWH`

- 是重复 XML 标签
- 每个视频稳定出现 2 个数值
- 当前可直接解释成 `WIDTH, HEIGHT`

本轮实测到：

- `1920 x 814`
- `1920 x 804`
- `2600 x 1080`
- `1920 x 810`

## 6. 关键样本结论

### 6.1 电影样本

电影样本的特点：

- `video_ids` 只有 1 个
- `nomal_ids` / `vip_ids` 里只看到 1 个 `F=7`
- 接口 2 中 `cover_list` 可能仍是多值

### 6.2 多集动漫样本

多集动漫样本的特点：

- `video_ids` 是多条重复标签
- `episode_all` / `episode_updated` 会出现
- `nomal_ids` / `vip_ids` 是一整个 JSON 数组字符串
- `F` 值不止一种，且不能简单翻译成“是否 VIP”

## 7. 当前最稳的结论

1. 接口 1 的 `video_ids` 是重复 XML 标签，不是单个 CSV
2. 接口 1 的 `nomal_ids` / `vip_ids` 是 JSON 数组字符串
3. 接口 1 的 `topic_id_list` 是 `+` 分隔 ID 串
4. 接口 2 的批量响应是重复 `<results>` 块
5. 接口 2 的 `defn` 是 JSON 对象字符串
6. 接口 2 的 `cover_list` / `category_map` / `vWH` 都可能是重复标签
7. `hd` 和 `shd` 必须拆开，不应该继续混成一个“高清”列

## 8. 仍待继续补样本的点

这次已经把接口的大骨架摸清了，但以下点仍建议继续补样本：

- `pay_status` 的完整枚举
- `downright` 每个数值位的业务解释
- `positive_content_id` / `positive_trailer` 的内部语义
- `upload_src` 的完整来源映射
- `state` 的枚举含义
- `publish_date` 在哪些内容类型下才会填充
- `targetid` 在哪些内容形态下会非空

## 9. 调用示例

`curl`：

```bash
curl "https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b"
curl "https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4"
```

Python 示例：

- [examples/python/tencent_video_api_demo.py](C:/Users/lin/Documents/YM查询工具还原/examples/python/tencent_video_api_demo.py)

Go 示例：

- [examples/go/main.go](C:/Users/lin/Documents/YM查询工具还原/examples/go/main.go)
