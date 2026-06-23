# 腾讯视频两个接口说明

这份文档只写截至 2026-06-21 的真实接口回包与配套 replay 实测能坐实的东西。

不再用“低 / 中 / 高置信度”这类模糊说法，而是分成三层：

- `已实测确认`：已经被 live 返回直接坐实
- `形态已确认，业务语义待补命名`：知道字段长什么样、怎么用，但后端枚举名还不能 100% 命名
- `仍待补反例`：当前样本已经很强，但还缺决定性反例

## 1. 整体链路

```text
URL -> CID -> 接口1 -> VID -> 接口2 -> 结果
```

更具体一点：

1. 输入腾讯视频页面 URL
2. 从 URL 提取 `CID`
3. 调用接口 1，拿到 cover / 节目级信息，以及一个或多个 `VID`
4. 调用接口 2，按 `VID` 拉取单视频详细信息
5. 如有需要，再对 `defn` 里的清晰度体积做格式化

## 2. 本轮实测样本

这一轮除了最初 4 个样本，又补了电视剧、纪录片、综艺、少儿和免费合集样本。下面列文档里最常引用的代表样本：

| 页面 URL | 标题 | `type` / `type_name` | `pay_status` | 说明 |
| --- | --- | --- | --- | --- |
| `https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html` | 飞驰人生3 | `1 / 电影` | `6` | 电影单片 |
| `https://v.qq.com/x/cover/mzc002009qyd7nv/m4102tgsa8d.html` | 熊出没·年年有熊 | `1 / 电影` | `6` | 电影单片 |
| `https://v.qq.com/x/cover/mzc00200xxpsogl/j4101ouc4ve.html` | 剑来 第二季 | `3 / 动漫` | `6` | 动漫季页 |
| `https://v.qq.com/x/cover/mzc00200fobieel/u41010ju5vc.html` | 一人之下 第6季 | `3 / 动漫` | `6` | 动漫季页 |
| `https://v.qq.com/x/cover/mzc00200dfbfsrw.html` | 长安诺 | `2 / 电视剧` | `6` | 电视剧季页 |
| `https://v.qq.com/x/cover/mzc002002kqssyu/q4100dpkd26.html` | 庆余年第二季 | `2 / 电视剧` | `6` | 电视剧季页 |
| `https://v.qq.com/x/cover/mzc00200whxf2zp.html` | 问心2 | `2 / 电视剧` | `6` | 电视剧季页，`F=0/2/4/7` 同时出现 |
| `https://v.qq.com/x/cover/mzc00200nkzol5n.html` | 合成令 | `2 / 电视剧` | `8` | 电视剧专题页，`positive_trailer=2` 反例 |
| `https://v.qq.com/x/cover/mzc002001w361jz.html` | 尚公主 | `2 / 电视剧` | `6` | 电视剧页，`positive_trailer=2` 第二命中样本 |
| `https://v.qq.com/x/cover/mzc002009zwrmx4/z4100ysbbpi.html` | 探索新境·寻找王一博 | `9 / 纪录片` | `6` | 纪录片季页 |
| `https://v.qq.com/x/cover/mzc00200apbfiqs.html` | 畅游天下·云南篇 | `9 / 纪录片` | `8` | 纪录片专题页，新增 `type=9 + pay_status=8` |
| `https://v.qq.com/x/cover/mzc00383lw807hq.html` | 体育人物 | `4 / 体育` | `6` | 体育人物页，`positive_trailer=0` |
| `https://v.qq.com/x/cover/mzc002003u0t3rl.html` | 2026NBA总冠军巡游 | `4 / 体育` | `8` | 体育活动回放页，`publish_date` 全量非空 |
| `https://v.qq.com/x/cover/mzc00200c2gydkd.html` | 哈哈哈哈哈 第6季 | `10 / 综艺` | `6` | 综艺季页 |
| `https://v.qq.com/x/cover/mzc00200u2ay1kj/f41025rs2nj.html` | 开始推理吧 第4季 | `10 / 综艺` | `16` | 综艺季页，新增 `pay_status` 样本 |
| `https://v.qq.com/x/cover/mzc002001u873es.html` | 战至巅峰之赛事全局看 | `10 / 综艺` | `15` | 综艺专题壳页，`positive_trailer=0` |
| `https://v.qq.com/x/cover/mzc0020081c19hy.html` | 战至巅峰之第一视角 | `10 / 综艺` | `15` | `pay_status=15` 第 2 个复现样本 |
| `https://v.qq.com/x/cover/mzc00200lyd87zd.html` | 汪汪队立大功第五季[普通话版] | `106 / 少儿` | `6` | 少儿常规季页 |
| `https://v.qq.com/x/cover/mzc00200tuupfc2.html` | 汪汪队立大功免费合集 | `106 / 少儿` | `8` | 少儿免费合集 |
| `https://v.qq.com/x/cover/mzc002002cxp3uh.html` | 小猪佩奇免费合集 | `106 / 少儿` | `8` | 少儿免费合集 |
| `https://v.qq.com/x/cover/mzc0037hox1pzu9/j32834p57ol.html` | 我的心略大于整个宇宙 | `10 / 综艺` | `8` | 微综艺 / 轻内容 |
| `https://v.qq.com/x/cover/mzc00200zfenikz.html` | 普通人逆袭，超燃！ | `1 / 电影` | `8` | 电影聚合页 |
| `https://v.qq.com/x/cover/mzc00200ls5y7z0.html` | 奔跑的少年 | `1 / 电影` | `5` | `pay_status=5` 电影单片样本 |
| `https://v.qq.com/x/cover/mzc002006g6kqo4.html` | 黑鹰少年 | `1 / 电影` | `5` | `pay_status=5` 第 2 个电影样本 |
| `https://v.qq.com/x/cover/mzc003ikavbkqa7.html` | 逐风少年：决胜篮途 | `3 / 动漫` | `9` | `pay_status=9` 动漫样本 |
| `https://v.qq.com/x/cover/mzc00200iy331ds.html` | 五哈热点一网打尽 | `10 / 综艺` | `8` | 综艺热点聚合页 |
| `https://v.qq.com/x/cover/mzc00200j7l2u0p.html` | 免费动画屋 | `106 / 少儿` | `8` | 少儿大聚合页 |
| `https://v.qq.com/x/cover/mzc00200q00mv2h.html` | 暑期作战大联盟，全员待命去冒险！ | `113 / 表演演出` | `8` | 新 `type` 样本 |
| `https://v.qq.com/x/cover/mzc00200pfna6wj.html` | 鹅友新春来拜年【群星祝福视频】 | `10 / 综艺` | `8` | `pay_status=8 + positive_trailer=1` 反例 |
| `https://v.qq.com/x/cover/mzc002005shizp0/i0042gc1csd.html` | 《庆余年》手游虚拟直播发布会 | `6 / 游戏` | `8` | 新 `type` 样本 |
| `https://v.qq.com/x/cover/mzc00200tp4rwup/s4102l6hc82.html` | 2026腾讯游戏发布会 | `6 / 游戏` | `8` | 新 `type` 样本 |
| `https://v.qq.com/x/cover/mzc00200vzc9y78/h0046jwiuem.html` | 2023TMEA腾讯音乐娱乐盛典 | `22 / 音乐` | `8` | 新 `type` 样本 |
| `https://v.qq.com/x/cover/j5wzdu7t6vu3ute/h0021mnyfvf.html` | BIGBANG十周年演唱会首尔站 | `22 / 音乐` | `7` | `pay_status=7` 样本 |
| `https://v.qq.com/x/cover/mzc00200hrq1mru/j3096bi0245.html` | 音乐会《黄河大合唱》中国交响乐团 | `31 / 生活` | `7` | 新 `type` + `pay_status=7` 样本 |
| `https://v.qq.com/x/cover/mzc00200bhj36oq.html` | 小学自然科学 | `27 / 教育` | `8` | 新 `type=27` 样本 |
| `https://v.qq.com/x/cover/mzc00200p3gva5k.html` | 2023苹果秋季发布会 | `28 / 科技` | `8` | 新 `type=28` 样本 |
| `https://v.qq.com/x/cover/mzc00200aawkdfw.html` | 鸿蒙智行新品发布会 | `29 / 汽车` | `8` | 新 `type=29` 样本 |
| `https://v.qq.com/x/cover/mzc00200s6oqemg.html` | 零基础入门中国舞必备基本功—软开度教学 | `111 / 文化历史` | `7` | 新 `type=111` 样本，`upload_src=2048` 新值 |
| `https://v.qq.com/x/cover/mzc00200yilptw9.html` | 安崎的舞台2023时光日记 | `10 / 综艺` | `9` | `pay_status=9` 的综艺反例，已证伪“只在动漫” |
| `https://v.qq.com/x/cover/jrtrbrm2wjgg398.html` | 超燃好片一次看爽 | `1 / 电影` | `8` | `positive_content_id=1543607` 的电影聚合页反例 |

另外，为了摸清 `F` 值、`upload_src`、`publish_date`、`targetid`，本轮还额外回查了大量 `VID`，包括：

- 动漫中的预告、彩蛋、人物志、片尾曲、番外、速看
- 综艺里的正片上下、加更、纯享、抢先看
- 同一综艺 `CID` 下的正片、花絮、直播回放、抢先看
- 电视剧里的整季集号
- 少儿免费合集和常规季页

这一轮还额外把腾讯视频搜索后端当作补样本入口跑了一遍：

- 搜索后端不是主接口链的一部分
- 但它非常适合继续发现新的 `CID`
- 当前 `type=4 / 体育`、`type=27 / 教育`、`pay_status=5`、`pay_status=9`，都是靠这条补样本路径继续打出来的

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

### 4.1.1 参数契约与错误返回

这一轮把 API1 的“哪些参数是真的硬约束，哪些只是实现分支”补清楚了。

最稳的结论：

- 在单个 `tid / idlist` key 的 query 形态下，`tid` 和 `idlist` 是硬参数
- `tid` 是硬参数
  - 缺失 / `0` / `abc` 都返回：
    - `errorno=-111003`
    - `errormsg=错误的tid, 如果新申请的接口,请等待10分钟`
- `idlist` 是硬参数
  - 缺失 / 空串 / 空格都返回：
    - `errorno=-111004`
    - `errormsg=错误的idlist`
  - `idlist=,` 或 `idlist=,,` 返回：
    - `errorno=10010039`
    - `errormsg=keys empty`
- `appid / appkey` 不是“普通必填鉴权参数”那种直线逻辑
  - 不带 `appid`、不带 `appkey`，有效 `CID` 仍然成功
  - `appid=1`，有效 `CID` 仍然成功
  - `appid=10001005` 但不带 `appkey`，返回：
    - `errorno=10010110`
    - `errormsg=appkey error`
  - `appid=99999`，返回：
    - `errorno=10010108`
    - `errormsg=appid no find`
  - `appid=notanumber` 时，即使缺 `appkey` 或 `appkey` 乱填，也会成功，当前黑盒表现更像“旁路到忽略分支”
  - 新补的 repeated 对撞 case 已说明：在当前 API1 tested branches 下，repeated `appid` 与 repeated `appkey` 都表现为首值生效
    - `appid=10001005&appid=notanumber&appkey=deadbeef` 返回 `10010110 / appkey error`
    - `appid=notanumber&appid=10001005&appkey=deadbeef` 仍成功
    - `appid=10001005&appkey=good&appkey=deadbeef` 仍成功
    - `appid=10001005&appkey=deadbeef&appkey=good` 返回 `10010110 / appkey error`
- API1 的错误同样主要靠 body 里的 `errorno / errormsg` 表达，不能只看 HTTP 状态码
- 当前已确认 API1 正向 `tid` 至少分成 3 支：
  - `431` = canonical positive
    - 当前稳定返回 non-empty cover row + non-empty `video_ids` 家族
  - `453` = positive cover-shell-only
    - 当前可返回 non-empty `cover_id / title / type / type_name`
    - 但在 3 个 public CID 上 `video_ids` 都仍为空
  - `537` = success-shell-without-sample
    - 当前为更薄的 success shell
    - 在 3 个 public CID 上都没有补出 non-empty cover row 或 `video_ids`
- 新补的 [analysis/param_query_semantics_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_query_semantics_20260620.json) 还说明：
  - 当前 canonical tested branch 下，额外 `foo / callback / _` 都未改变 API1 的 XML 外壳和成功结果
  - repeated `tid` 与 repeated `idlist` 当前都表现为首值生效，而不是把多个同名 key merge 成更大的批量

多 `CID` 批量行为也已经补清，但下面这些结论都针对单个 `idlist=cid1,cid2,...` 的 CSV 形态成立：

- `idlist=cid1,cid2,...` 支持多 `CID`
- 重复 `CID` 不去重
- 混合有效 / 无效 `CID` 时，顶层不一定失败
- 调用方必须检查每个 `<results>` 的：
  - `id`
  - `retcode`
  - `cover_id`

这里还有一个很关键的黑盒细节：

- “无效 CID”至少分两类
  - 非法 key 形状：单值时常见顶层 `10010048 / key all illegal`
  - 形状合法但查无内容：顶层仍 `errorno=0`，该项 `retcode=0`，但 `cover_id/title/type/pay_status` 这类结果字段为空
- 混合批量时，坏项会退化成逐项 `retcode`，而不是统一顶层报错
- 如果空壳项排在前面，肉眼看顶层 `.//title/.//cover_id` 很容易误以为整批都空；调用方必须按 `<results>` 逐项读

代表例子：

- `idlist=invalidcid123`
  - 顶层：`errorno=10010048`，`errormsg=key all illegal`
- `idlist=mzc00000zzzzzzz`
  - 顶层仍 `errorno=0`
  - 但 `<results>` 内 `cover_id` 为空
- `idlist=invalidcid123,mzc00200idzf2m8`
  - 顶层仍 `errorno=0`
  - 坏项逐项落成 `retcode=10010045`

### 4.2 当前已确认的返回形态

接口 1 返回 XML，但“成功返回”并不只存在一种壳形。

这一轮最重要的结构结论：

- 下面这些较丰满的结构结论，当前主要对应 canonical `tid=431`
- `tid=453/537` 也可能返回 `errorno=0`
  - 但字段丰满度更薄
  - 不应默认等同于 `431`
- `video_ids` 是重复 XML 标签
- `clips_ids` 是重复 XML 标签
- `downright` 也是重复 XML 标签
- `nomal_ids` 是单个 XML 字段里的 JSON 数组字符串
- `vip_ids` 是单个 XML 字段里的 JSON 数组字符串
- `topic_id_list` 是单个 XML 字段里的 `+` 分隔 ID 串

所以不能把所有“多值字段”都粗暴当成 CSV。

### 4.3 接口 1 字段证据总表

| 字段 | 当前状态 | 数据形态 | 当前理解 | 本轮关键观察 |
| --- | --- | --- | --- | --- |
| `cover_id` | 已实测确认 | 单值 ID | 当前 cover / CID | 与 URL 里的 `CID` 对齐 |
| `id` | 已实测确认 | 单值 ID | 与 `cover_id` 等值 | 稳定 |
| `title` | 已实测确认 | 单值文本 | 节目或影片标题 | 稳定 |
| `type_name` | 已实测确认（部分仍属镜像占位） | 单值文本 | 内容类型名称 | 已见 `电影 / 电视剧 / 动漫 / 体育 / 游戏 / 纪录片 / 综艺 / 音乐 / 教育 / 科技 / 汽车 / 生活 / 少儿 / 文化历史 / 表演演出`；其中 `科技 / 汽车 / 文化历史` 当前仍主要按 `type` 层 1:1 镜像占位 |
| `type` | 已实测确认 | 单值数值字符串 | 类型编号 | 已见 `1=电影`、`2=电视剧`、`3=动漫`、`4=体育`、`6=游戏`、`9=纪录片`、`10=综艺`、`22=音乐`、`27=教育`、`28=科技`、`29=汽车`、`31=生活`、`106=少儿`、`111=文化历史`、`113=表演演出` |
| `video_ids` | 已实测确认 | 重复 XML 标签 | 当前 CID 关联的主播放条目集合 | 数量不等于 `episode_all` |
| `clips_ids` | 形态已确认，业务语义待补命名 | 重复 XML 标签 | 关联的预告 / 海报卷 / 加更 / 番外 / 花絮等条目集合 | 综艺和动漫样本里非常多 |
| `nomal_ids` | 已实测确认 | JSON 数组字符串 | 结构化条目列表，元素含 `F` 和 `V` | 稳定 |
| `vip_ids` | 已实测确认 | JSON 数组字符串 | 另一套结构化条目列表 | 稳定 |
| `episode_all` | 已实测确认 | 单值数值字符串 | 总集数 / 总期数 / 总话数 | 在电视剧、综艺、纪录片、少儿上都出现 |
| `episode_updated` | 已实测确认 | 单值展示文本 | 当前更新状态文本 | 形如 `全36集`、`更新至11集` |
| `pay_status` | 形态已确认，业务语义待补命名 | 单值数值字符串 | cover 级收费 / 运营状态码 | 当前稳定非空值已见 `5`、`6`、`7`、`8`、`9`、`15`、`16`；另见过空串异常壳页 |
| `downright` | 形态已确认，业务语义待补命名 | 重复 XML 标签 | cover 级权限 / 能力代码集合 | 不是条目级逐项映射 |
| `new_pic_hz` | 已实测确认 | 单值 URL | 横版封面图 | 稳定 |
| `new_pic_vt` | 已实测确认 | 单值 URL | 竖版封面图 | 稳定 |
| `topic_id_list` | 形态已确认，业务语义待补命名 | 单值 `+` 分隔 ID 串 | 话题 / 专题 ID 集合 | 稳定 |
| `positive_content_id` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 更像 cover 级内部配置 / 路由号，而不是内容自己的 ID | 已见 `1543606`、`1543607` |
| `positive_trailer` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 更像 cover 页形态 / 路由位，不是“是否预告片”布尔值 | 已实测到 `0`、`1`、`2`，且不是 `pay_status` 的附属位 |
| `column_id` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 栏目 / 专栏 ID | 多数样本为 `0` |
| `cover_checkup_grade` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 某种审核 / 评级字段 | 常见 `4` |
| `errorno` / `retcode` / `costtime` / `resptime` | 已实测确认 | 单值状态字段 | 服务端状态 / 耗时 / 时间戳 | 正常返回时稳定出现 |

### 4.4 `pay_status` 的当前结论

这一轮最重要的新进展之一，就是 `pay_status` 终于被拉开了。

目前已实测到：

- `5`
- `6`
- `7`
- `8`
- `9`
- `15`
- `16`

这意味着当前可以先把“稳定非空值”集合写成：

```text
{5, 6, 7, 8, 9, 15, 16}
```

另外仍然见过显式空串 `pay_status=""`，但目前更像异常壳页，不建议把空串直接提升成稳定枚举。

这一轮新增的 3 个重要分支是：

1. `pay_status=5`
   - 当前已经复现到多个电影单片样本：
     - `奔跑的少年`
     - `黑鹰少年`
     - `好像也没那么热血沸腾`
     - `不败雄心`
     - `屋顶足球`
   - 当前最稳的说法：
     - 它不是单点噪声
     - 它当前稳定落在 `type=1 / 电影`
     - 目前命中的样本都还是 `positive_trailer=1 + positive_content_id=1543606`

2. `pay_status=9`
   - 当前机器归档里至少已复现到 3 个独立样本：
     - `逐风少年：决胜篮途`
     - `趣界篮球单挑王`
     - `安崎的舞台2023时光日记`
   - 当前最稳的说法：
     - 它已经不是单点噪声
     - 它已经明确跨出“只在动漫”的旧结论
     - `upload_src=149` 只能解释动漫那一支，不能再拿来解释整个 `pay_status=9`

3. `pay_status=15`
   - 当前至少已复现 4 个独立样本：
      - `战至巅峰之赛事全局看`
      - `战至巅峰之第一视角`
      - `推市营业中·大奉打更人专场`
      - `推市营业中·与凤行专场`
   - 当前最稳的说法：
      - 它仍是小家族值，但已经不能再收缩成“只在《战至巅峰》体系内”
      - 它也不能再收缩成“只在 `positive_trailer=0` + `targetid 强阳性` 的专题 / 视角壳页”
      - 更稳的黑盒表达是：`type=10 / 综艺` 里一条窄运营分支，当前命中专题 / 视角壳和专场 / 运营支，但这些页型名仍是黑盒描述，不是官方命名
      - 新补的 depth-1 related-cover family expansion 还没从 `mzc00200k1tze71 / 推市营业中·大奉打更人专场` 与 `mzc00200sd1b239 / 推市营业中·与凤行专场` 再长出新的 cover；这轮只进一步坐实了这两支自身都是 `type=10 + pay_status=15 + positive_trailer=1 + positive_content_id=1543606`

4. `pay_status=16`
   - 当前机器归档与本轮 focused search 合起来，至少已打到 9 个代表性 cover：
       - `开始推理吧 第4季`
       - `五十公里桃花坞 第6季`
       - `脱口秀和Ta的朋友们 第3季`
    - 当前最稳的说法：
      - 它仍然更像综艺 bounded `small_family`，但已经不能再收缩成“只在《战至巅峰》主季页”或“固定常规综艺季页码”
      - `positive_trailer` 当前已见 `0 / 1 / 2`
      - `publish_date 强阳性 + targetid 强阴性` 只能算常见形状，不能当判别规则

其中 `7` 这次已经直接打到两个新类型样本：

- `BIGBANG十周年演唱会首尔站`
  - `type=22 / 音乐`
  - `pay_status=7`
- `音乐会《黄河大合唱》中国交响乐团`
  - `type=31 / 生活`
  - `pay_status=7`

当前最稳的结论：

1. `pay_status=6` 不是“VIP 内容”的简单同义词
   它同时出现在电影、动漫、电视剧、纪录片、综艺、少儿样本上。
   其中 `type=106 + positive_trailer=1 + positive_content_id=1543606` 这支少儿 family 已经不能再写成单一“常规季页”：
   - `mzc00200lyd87zd / 汪汪队立大功第五季[普通话版]`
   - `mzc00200qrzj493 / 小猪佩奇 第11季[普通话版]`
     都是 `publish_date=0/26 + targetid=0/26` 的 `double-zero` 分支
   - `zkbp0mrqhy0x1hl / 小猪佩奇第6季[普通话版]`
   - `ca1k6ja4k81h8ov / 汪汪队立大功第一季`
   - `ob6ak6eq2wp5qui / 超级飞侠 第五季[普通话版]`
     则都是 `publish_date=N/N + targetid=N/N` 的 clean season-style `dual-full` 分支
   - `mzc002006huuuiu / 小猪佩奇第10季[普通话版]`
   - `mzc00200syo2994 / 汪汪队大救援第五季`
     则继续说明“第N季”标题本身并不推出 `dual-full`
   - 所以它既不推出单一页型，也不推出固定 `upload_src=129`；当前更稳的说法是：kids 这支至少已跨 `小猪佩奇 / 汪汪队立大功 / 超级飞侠` 复现出 `double-zero` 与 clean season-style `dual-full` 两支

2. `pay_status=7` 当前已经不是单点异常
   它至少已经落到：
   - `22 / 音乐`
   - `31 / 生活`
   - `111 / 文化历史`

3. `pay_status=8` 已经不能只绑定到“少儿免费合集”，也不能简单绑定到某一种 `positive_trailer`
   已命中：
   - `合成令`（电视剧专题页）
   - `汪汪队立大功免费合集`
   - `小猪佩奇免费合集`
   - `我的心略大于整个宇宙`（微综艺 / 轻内容）
   - `普通人逆袭，超燃！`（电影聚合页）
   - `超燃好片一次看爽`（电影聚合页）
   - `五哈热点一网打尽`（综艺热点聚合页）
   - `免费动画屋`（少儿大聚合页）
   - `暑期作战大联盟，全员待命去冒险！`（`113 / 表演演出` cover）
   - `鹅友新春来拜年【群星祝福视频】`（综艺特殊聚合页）
   - `畅游天下·云南篇`（纪录片专题页）
   - `喜羊羊与灰太狼免费合集`
   - `喜羊羊与灰太狼合集`

4. `pay_status=16` 当前仍以综艺体系为主，但边界已经明显放宽
   - 它不再只落在《战至巅峰》这一条链
   - 当前至少已覆盖综艺季页、综艺衍生页、综艺活动页
   - 但目前仍未打到综艺之外的稳定类目

5. 接口 1 是 CID 级接口，不是 VID 级接口
   所以同一 `CID` 下，如果某个 URL 是预告片 `VID`，API1 仍然返回整个 cover 的 `pay_status`。

6. `type=4 / 体育` 这轮没有复现 `15`
   - 大量体育 seed 扩圈后，`type=4` 当前内部仍主要落在：
     - `pay_status=6`
     - `pay_status=8`
     - `pay_status=""`
   - 这说明 `15` 当前并不是“体育相关壳页”的通用码

7. 当前还见过显式空串 `pay_status=""`
   代表样本：
   - `勾魂公狒狒游戏集锦`
     - `type=6 / 游戏`
     - `positive_content_id=1543606`
   - `影说赛事`
     - `type=4 / 体育`
     - `positive_trailer=0`
   但目前更像异常壳页，不建议直接提升成稳定第 5 枚举。

目前还不能 100% 命名的是：

- `5` / `6` / `7` / `8` / `9` / `15` / `16` 的官方后台枚举名
- `8` 是否等于“更开放分发形态”，还是别的运营状态
- `7` 是否主要偏活动 / 演出 / 音乐壳页
- `9` 是否主要偏某类动漫页
- `15` 是否主要对应综艺专题 / 视角壳页
- `16` 是否主要对应常规综艺季页，还是只是当前样本巧合
- 是否还存在其他有效值

### 4.5 `downright` 的当前结论

这轮已经可以把一个旧误解排掉：

- `downright` 不是和 `nomal_ids` / `vip_ids` 按位置一一对应的条目表

硬证据：

- `飞驰人生3`：`downright_count=26`，但 `nomal_ids=1`
- `熊出没·年年有熊`：`downright_count=26`，但 `nomal_ids=1`
- `剑来 第二季`：`downright_count=29`，但 `nomal_ids=30`
- `一人之下 第6季`：`downright_count=30`，但 `nomal_ids=49`

所以当前最稳的理解是：

- `nomal_ids` / `vip_ids` 是条目级列表
- `downright` 更像 cover 级权限 / 能力码集合

基于这一轮补样本，可以先把几条旧说法收紧：

- `pay_status=16` 的 `开始推理吧 第4季`，其 `downright` 代码集合和 `pay_status=6` 的常规综艺季页高度一致  
  说明 `16` 至少不是靠整套 `downright` 的巨大变化来区分的
- `25` 已证伪“只在片单 / 合集”；电影单片 `mzc00200zfenikz` 也能命中
- `31` 已证伪“只在《一人之下 第6季》”；但当前第二样本仍偏高熵，暂时还不适合升级成稳定语义解释
- `41` 当前是相对最干净的差异码之一，已复现到 `mzc002002kqssyu` / `mzc00200dfbfsrw`
- `44` 已不再是单样本，当前至少能落到 `mzc002003r5yq45` / `mzc00200dfbfsrw`
- `62` 已有 4-cover 稳定 family，但 `mzc00200sq680j2` 说明它也能落到电影单片，不是某个单一专题专属
- `184` 当前最强簇仍在少儿 / 纪录片，但 `mzc00200sq680j2` 已给出电影单片反例

另外，还打到了更多 `downright_count=0` 的反例：

- `竞技体育电影合集：每一个人，都是自己的冠军！`
- `汪汪队之常识大百科`
- `汪汪队之海洋知识`
- `超燃好片一次看爽`
- `探索新境 第2季`

这说明：

- `downright` 不只是“数量多少”的问题
- 它甚至可能在一部分聚合 / 专题 / 知识页上直接为空
- 空 `downright` 目前同时覆盖 `pay_status=6/8`
- 空 `downright` 目前也同时覆盖 `positive_trailer=0/1`
- `探索新境 第2季` 这个样本说明：连明显 canonical 的纪录片季页也可能 `downright=0`

当前可以先把 `downright` 分成两层理解：

1. 一批“近乎全站常见”的基础代码  
   例如 `1/2/3/4/5/6/8/10/23/45/46`

2. 一批只在特定内容类型、运营形态、分发形态里出现的差异代码  
   例如 `25/31/41/44/62/184`

其中目前更稳的说法是：

- `25/31/41/44/62/184` 都更适合先归入“差异码桶”，而不是直接翻译成某个已命名业务状态
- `41/44` 当前相对更适合作为下一轮 clean family 追踪入口
- `62/184` 已经明确存在跨页型流动，不能再写成“单页面唯一命中”

还没完全解开的，仍然是每个代码本身的官方业务含义。

### 4.6 `positive_content_id` / `positive_trailer`

#### `positive_content_id`

这一轮已经把“全站常量”这个旧判断打掉了。

当前至少已见到两个值：

```text
1543606
1543607
```

代表样本：

- `1543606`
  - `飞驰人生3`
  - `问心2`
  - `开始推理吧 第4季`
  - `暑期作战大联盟，全员待命去冒险！`
- `1543607`
  - `五哈热点一网打尽`
  - `免费动画屋`
  - `汪汪队之海洋知识`
  - `超燃好片一次看爽`
  - `2026腾讯视频年度发布会直播`

所以目前最稳的说法是：

- 它不像内容自己的“正片 ID”
- 它也不是全站常量
- 它更像某种 cover 级内部配置 / 路由号
- 到 2026-06-19 这轮 fresh-entry 扩圈为止，强负证据仍只见 `1543606`、`1543607`，还没打出第 3 个值
- `1543607` 也不只落在少儿 / 综艺 / 轻内容，现在已经明确落到电影主题聚合页
- `1543607` 现在还明确落到了 `type=2 / 电视剧` 的运营直播页
- `1543607` 也不等于 `pay_status=8` 或 `positive_trailer=0`
  - `五哈团的变（受）形（难）记`：`pay_status=6 + positive_trailer=0 + positive_content_id=1543607`
  - `汪汪队之海洋知识`：`pay_status=6 + positive_trailer=1 + positive_content_id=1543607`
- 以 `1543607` 已知壳页为种子再做两轮 `depth=1` 扩圈后，这一支家族当前仍然只落出：
  - `positive_content_id={1543606,1543607}`
  - `pay_status={6,8}`
  - `type` 主要收敛到 `106/少儿`、`10/综艺`、`1/电影`

但 `1543606` 和 `1543607` 各自对应什么后台分流逻辑，当前还不能黑盒命名。

#### `positive_trailer`

这一轮已经明确：

- 它不是全站常量
- 它不是“这页是不是预告片”的简单布尔值

目前更稳妥的说法是：

- `0`：强相关于非 canonical 主详情壳层，常见于合集页、片单页、专题页、热点聚合页、微综艺 / 轻内容页
- `1`：常见于 canonical 内容页 / 正式节目页 / 正式季页
- `2`：当前已同时命中电视剧链和综艺同类对照组，前端第一层可见信号更像 preview-like / `预告` 支线，说明它至少不是 `0/1` 二元位

但这不是充分必要条件。

反证很关键：

- `飞驰人生・三部连看`、`熊抱快乐！熊出没大电影连看`、`过亿票房专区` 都不是预告页，但会出现 `0`
- `剑来 第二季`、`一人之下 第6季` 都有几十个 `video_ids`，仍然是 `1`
- `我的心略大于整个宇宙` 也会出现 `0`，说明 `0` 不只出现在聚合 / 专题页
- `鹅友新春来拜年【群星祝福视频】` 是明显的特殊聚合页，但仍然是 `pay_status=8 + positive_trailer=1`
- `合成令` 连续复测都返回 `pay_status=8 + positive_trailer=2`
- `尚公主` 也命中 `pay_status=6 + positive_trailer=2`

沿着 `合成令 / 尚公主` 的 related-cover 再跑一跳后，`positive_trailer=2` 这一支目前已经至少有 4 个 cover：

- `合成令`
- `尚公主`
- `百花杀`
- `三线谜回`

后面继续沿这条电视剧专题链专门扩圈，`positive_trailer=2` 当前已经不是“4 个样本的小反例”，而是一个可复现的小家族；本轮拿到的**电视剧这支 family** 里，已稳定扩到 20 个以上 cover。

但 2026-06-20 新补的同类 control group 也给了关键反例：`mzc00200tzs7ig5`（`type=10 / 综艺`）同样命中 `positive_trailer=2`，而且首屏更偏 `预告` badge。

所以电视剧链上这些共同点，现在只能写成 **drama branch 的局部共性**，不能再升级成 `positive_trailer=2` 的全局不变量：

- 在当前已扩圈的电视剧 family 里，`positive_content_id` 都还是 `1543606`
- 这支电视剧 family 的 `downright_count` 都还是 `26`
- 这支电视剧 family 的 `pay_status` 目前覆盖 `6` 和 `8`

此外，这一轮把 `cover_list -> 关联 cover` 这条链路直接跑通了：

- `飞驰人生3` 的 `cover_list` 能反查到：
  - `飞驰人生3`：`pay_status=6`、`positive_trailer=1`
  - `飞驰人生・三部连看`：`pay_status=6`、`positive_trailer=0`
  - `2026大片一次看够`：`pay_status=6`、`positive_trailer=0`
- `熊出没·年年有熊` 的 `cover_list` 能反查到：
  - `熊出没·年年有熊`：`pay_status=6`、`positive_trailer=1`
  - `熊抱快乐！熊出没大电影连看`：`pay_status=6`、`positive_trailer=0`

所以当前更稳的说法是：

- `positive_trailer=0` 当前是很强的非 canonical / 聚合 / 专题页相关信号
- 但它既不是必要条件，也不是充分条件
- `pay_status=6` 可以配 `positive_trailer=0/1`
- `pay_status=8` 可以配 `positive_trailer=0/1/2`
- `positive_trailer=2` 当前已不再是单点异常，也不再是只落在 `type=2 / 电视剧` 上的小家族；它至少已经跨到 `type=10 / 综艺`，而且第一层可见模式更偏 `预告` 支线
- `pay_status=16` 当前已见 `positive_trailer=0/1/2`

### 4.7 `nomal_ids` / `vip_ids` 的结构

这两个字段不是普通字符串，而是 JSON 数组字符串，例如：

```json
[{"F":2,"V":"j4101ouc4ve"},{"F":2,"V":"r4101sdqwpd"}]
```

当前已经可以稳定确认：

- `V` 就是 `VID`
- `F` 是某种条目分组 / 发行层级 / 运营槽位编码

### 4.8 `F` 值的当前最稳解释

这一轮把 `F` 的认知往前推了不少，尤其是电视剧、综艺、少儿免费合集样本非常关键。

| `F` 值 | 当前最稳观察 | 代表样本 |
| --- | --- | --- |
| `0` | 明显偏短预告 / 抢先看 / 先导类条目 | `《剑来2》预告片_27`、`五哈抢先看`、`《问心2》预告片_03` |
| `4` | 当前仍只命中过预告片，但已不止单样本 | `《问心2》预告片_05`、`一人之下 预告片_26` |
| `2` | 一类可播内容桶，既会命中长视频正片 / 纯享 / 直播回放，也会命中短运营型“栏目正片”条目 | `长安诺_01~04`、`开始推理吧` 纯享 / 直播回放、`五哈热点一网打尽` 的 36~60 秒短视频 |
| `7` | 另一类可播内容桶，会命中电影主片、后续正片集、纪录片全集、人物志 / 特辑 / 加更等 | `飞驰人生3`、`长安诺_05~56`、`探索新境` 全 12 集、`一人之下人物志` |

几个特别值钱的样本：

1. `长安诺`
   - `F=2`：`01~04`
   - `F=7`：`05~56`

2. `庆余年第二季`
   - `F=2`：`01`、`02`、`彩蛋`
   - `F=7`：`03~36`

3. `探索新境·寻找王一博`
   - 全部 `12` 集都是 `F=7`

4. `哈哈哈哈哈 第6季`
   - `F=2`：正片 `上 / 下`
   - `F=7`：加更、纯享、超长花絮、庆生特辑
   - `F=0`：抢先看

5. `开始推理吧 第4季`（同一 `CID` 对照）
   - 正片上 / 下、纯享、直播回放：`F=2`
   - 直播高清版回放、名场面特辑：`F=7`
   - 抢先看：`F=0`

6. `问心2`
   - `F=2`：`问心2_01`、`问心2_02`
   - `F=0`：`《问心2》预告片_03`、`《问心2》预告片_04`
   - `F=7`：`问心2_03`、`问心2_04`
   - `F=4`：`《问心2》预告片_05`、`《问心2》预告片_06`

7. `五哈热点一网打尽`
   - `F=0`：`五哈6首播看点划重点` 这类 20~35 秒短预告
   - `F=2`：`邓超说霸总台词`、`金志文被泼满脸泥反应亮了` 这类 36~60 秒“栏目正片”短内容

8. 本轮补的 6-cover 精确计数矩阵
   - `汪汪队立大功第五季[普通话版]`
     - `nomal={2:3,7:23}`
     - `vip={2:3,7:23}`
   - `汪汪队立大功免费合集`
     - `nomal={2:137}`
     - `vip={2:137}`
   - `小猪佩奇免费合集`
     - `nomal={2:38}`
     - `vip={2:38}`
   - `合成令`
     - `nomal={0:2,2:10}`
     - `vip={0:2,2:10}`
   - `畅游天下·云南篇`
     - `nomal={2:6,7:16}`
     - `vip={2:6,7:16}`
   - `免费动画屋`
     - `nomal={2:355,7:1}`
     - `vip={2:355,7:1}`

这个子集本轮命中的并集是 `F={0,2,7}`，没有复现 `4`，但这不推翻全局结论；全局已知集合仍是 `F={0,2,4,7}`。

9. 新类型代表页子集的 `F` 矩阵
   - `《庆余年》手游虚拟直播发布会`
     - `nomal={2:11}`
     - `vip={2:11}`
   - `2026腾讯游戏发布会`
     - `nomal={2:40}`
     - `vip={2:40}`
   - `2023TMEA腾讯音乐娱乐盛典`
     - `nomal={2:32}`
     - `vip={2:32}`
   - `BIGBANG十周年演唱会首尔站`
     - `nomal={7:29}`
     - `vip={7:29}`
   - `音乐会《黄河大合唱》中国交响乐团`
     - `nomal={7:1}`
     - `vip={7:1}`
   - `暑期作战大联盟，全员待命去冒险！`
     - `nomal={2:222,7:61}`
     - `vip={2:222,7:61}`

这批 `type=6/22/31/113` 代表页本轮只命中 `F={2,7}`，既没有打出新值，也没有复现 `0/4`；但同样不推翻全局已知集合 `F={0,2,4,7}`。

因此，这一轮最重要的修正是：

- `F=2` 不能再简单写成“主正片集”或“长视频正片”
- `F=7` 也不能再简单写成“VIP 内容”或“花絮内容”
- `F=4` 现在已经不止一个命中样本，至少在 `一人之下 第6季` 和 `问心2` 里都明确命中过预告片；但当前还只能写成“在已测样本中强相关于预告类条目”
- `F=0` 和 `F=4` 当前都强相关于预告类条目
- `F=2` 和 `F=7` 更像两类不同的可播条目桶，它们和“正片路由 / 运营编排 / 分发层级”有关，但还不能只靠黑盒把后台枚举名定死

### 4.9 接口 1 当前最稳结论

1. `video_ids` 是重复 XML 标签列表
2. `nomal_ids` / `vip_ids` 是 JSON 数组字符串
3. `topic_id_list` 是 `+` 分隔 ID 串
4. `pay_status` 当前稳定非空值已实测到 `5`、`6`、`7`、`8`、`9`、`15`、`16`
5. `downright` 是 cover 级代码集合，不是条目级逐项权限
6. `positive_trailer` 不是“是否预告片”布尔值，当前至少已见 `0`、`1`、`2`
7. API1 当前至少已确认 3 类正向 `tid` 壳：
   - `431` = canonical positive
   - `453` = cover-only positive shell
   - `537` = sample-less success shell
   它们都属于成功分支，但 caller-facing 能力不同

## 5. 接口 2：VID -> 单视频详细信息

### 5.1 请求地址

```text
https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=<VID>
```

多 `VID` 时：

```text
idlist=vid1,vid2,vid3
```

### 5.1.1 参数契约与错误返回

API2 这一轮补得最值钱的一块，就是参数契约终于不只剩一个 “`idlist` 上限 32”。

最稳的结论：

- **错误默认也是 HTTP 200**
  - 不能靠 HTTP 状态码判断成功失败
  - 要看 body 内的 `errorno / errormsg`
- `tid` 是单 key query 下最硬的路由参数
  - 缺失 / 空 / `abc` / `0` / `-1`
    - `errorno=-111003`
    - `errormsg=错误的tid, 如果新申请的接口,请等待10分钟`
  - `tid=536`
    - `errorno=-111005`
    - `errormsg=获取配置错误`
  - `tid=431`
    - `errorno=10010048`
    - `errormsg=key all illegal`
- `otype` 不是 XML 路径上的硬必填参数
  - 缺失 / 空 / `foo` / `JSON`
    - 当前仍返回正常 XML 成功体
  - **单个 `otype` key 时，只有精确小写 `otype=json` 会切到 JSONP**
    - `Content-Type: application/x-javascript`
    - 默认 body 形如 `QZOutputJson=...;`
  - 这一点在成功和失败两种分支上都成立
    - `otype=json` + `tid/appid/appkey/idlist` 出错时，也不会退回 XML，默认仍然是 `QZOutputJson=...;`
- 额外 query key 这轮也补了一层
  - API2 XML canonical branch 下，额外 `foo / callback / _` 当前都未观察到变化
  - API2 JSONP canonical branch 下，额外 `foo` 与 `_` 当前都未观察到变化
  - 但 `callback` 在 JSONP 路径上现在已经补到第二层 practical value-space：
    - `callback=1` -> `1({...})`
    - `callback=cb1` -> `cb1({...})`
    - `callback=QZOutputJson` -> `QZOutputJson({...})`
    - `callback=foo.bar` -> `foo.bar({...})`
    - `callback=a-b / a[b] / $cb / foo bar / foo,bar / [0] / 中文 / a) / ) / a;b / a'b / a"b / a/ / a\ / //a / /*a / [ / [[` 也都会 raw passthrough 到 wrapper 前缀
    - `callback=` 空值不会生成空 callback-style 包裹，而是回落默认 `QZOutputJson=...;`
    - repeated `callback` 当前 same-day anonymous collision cases 也已经补到首值生效：
      - `callback=cb1&callback=` -> `cb1(...)`
      - `callback=&callback=cb1` -> 默认 `QZOutputJson=...;`
      - `callback=cb1&callback=a(` -> `cb1(...)`
      - `callback=a(&callback=cb1` -> 仍是 parse-breaking 坏壳
    - wrong-appkey JSONP 错误壳也仍然吃 `callback`：
      - `callback=cb1` -> `cb1({...error...})`
      - `callback=a(` -> 仍是 parse-breaking 坏壳
    - 这组 callback precedence / wrong-appkey error-shell 结论，已经在真实匿名 visitor-cookie replay 的 `PC Web` 与 `Mobile H5` 上各复打一遍，当前未观察到分叉
    - `callback=a(` 与 `callback=((` 会形成 `a(({...})` / `((({...})` 这类当前摘要路径不可解析的坏壳
    - 后续 pathological-tail probe 又补出一个更稳的 parse-breaking 代表：`callback=})();`
    - 2026-06-22 的 unmatched-delimiter follow-up 继续把 parse-breaking 代表族向外推宽：`callback=[(`、`callback={(`、`callback=/*(`、`callback=a[(`、`callback=)(`、`callback=](`、`callback=}(` 当前都会落到摘要路径不可解析的坏壳
    - 相对地，`callback=[` 与 `callback=[[` 当前仍是 raw passthrough；也就是说“带特殊字符”不等于一定坏壳
    - 当前最稳说法是：这些当前已测 callback 值族会保留 payload 家族，但会改写 JSONP wrapper 前缀；空 callback 走 fallback default；至少已确认存在一组 widened unmatched-delimiter / malformed-prefix parse-breaking 壳
    - 但这仍是 practical value-space 结论，不外推成“callback 任意取值都安全可解析”，也不外推成“凡是包含 `(` 都一定坏壳”
    - 这些结论也只覆盖已测 key，不外推成“所有未知 key 都会被忽略”

### 5.1.2 Demo 入口级已验证路径

下面这几条不是“所有页型/所有环境都闭环”的意思，而是说在**当前匿名 direct-call scope** 下，公开 Python/Go demo 的几个高频入口已经各自有 dedicated live validation：

- URL canonical chain
  - Python：`python examples/python/tencent_video_api_demo.py --url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" --json`
- Go：`go.exe -url "https://v.qq.com/x/cover/mzc00200idzf2m8/z4102qfi0x4.html" -json`
  - 当前已确认：demo 会先从 URL 提取 CID，再走 canonical API1 -> API2 链路拿到非空详情行

- API2 batch-size override
  - Python：`python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --vid j4101ouc4ve --api2-batch-size 1 --json`
- Go：`go.exe -cid mzc00200idzf2m8,mzc00200xxpsogl -api2-batch-size 1 -json`
  - 当前已确认：demo 显式分批入口可运行，guard 仍是 `1..32`；这不替代更底层的 API2 批量契约矩阵

- API2 union_platform explicit override
  - Python：`python examples/python/tencent_video_api_demo.py --vid z4102qfi0x4 --api2-union-platform 999 --json`
- Go：`go.exe -vids z4102qfi0x4 -api2-union-platform 999 -json`
  - 当前已确认：override 入口可运行，且在当前匿名样本上未观察到破坏性分叉；这不覆盖 `aged-cookie / login-state`，也不证明 `union_platform` 在所有环境全局无作用

统一证据见 [analysis/demo_validation_incremental_20260621d.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621d.json)。
- repeated `otype` 当前 tested branch 由首值决定 XML / JSONP 外壳
  - `otype=xml&otype=json` 仍返回 XML
  - `otype=json&otype=xml` 仍返回 JSONP
- `union_platform` 当前在匿名 canonical tested branches 与真实匿名 visitor cookie replay 下都未观察到可见行为差异
  - 缺失 / 空 / `0` / `2` / `abc` / `999` / `-1`
  - 当前都能成功
- `appid / appkey` 不是简单“必填且强校验”逻辑
  - `appid` 缺失 / 空 / `abc` / `1` / `1.0` / 带空格的 `1`
    - 当前都能成功
  - 数值型但不存在的 `appid`
    - 例如 `0 / 2 / -1 / 12345 / 99999999`
    - 返回 `10010108 / appid no find`
  - 当 `appid=20001238` 且 `appkey` 缺失 / 空 / 错时
    - 返回 `10010110 / appkey error`
  - 但当 `appid` 缺失 / `abc` / `1` 时，`appkey` 乱填也能成功
  - 新补的 repeated 对撞 case 已说明：在当前 API2 XML tested branches 下，repeated `appid` 与 repeated `appkey` 都表现为首值生效
    - `appid=20001238&appid=notanumber&appkey=deadbeef` 返回 `10010110 / appkey error`
    - `appid=notanumber&appid=20001238&appkey=deadbeef` 仍成功
    - `appid=20001238&appkey=good&appkey=deadbeef` 仍成功
    - `appid=20001238&appkey=deadbeef&appkey=good` 返回 `10010110 / appkey error`

这一轮还顺手把 API2 的一个实用边界钉出来了：

- `idlist` 一次传 `32` 个 `VID` 正常
- `idlist` 一次传 `33` 个 `VID` 会报：

```text
idlist个数错误, 为0或超过限制
```

但这一轮把边界条件也补清楚了，当前最稳的说法要更细一点；以下结论都针对单个 `idlist` key 的 CSV 语义成立：

- **单次最多 `32` 个非空 `idlist item`**
- 这里看的是清洗后的“非空 item 数量”，不是逗号分隔出来的原始槽位数
- 重复 `VID` 不会去重，照样占名额
- 无效 `VID` 也照样占名额
- 前导逗号、尾随逗号、连续逗号里的空槽位会被忽略
- 混合有效 / 无效 `VID` 时不会整体报错，而是按顺序返回 `<results>`；无效项对应一个空壳结果
- `idlist` 缺失、空字符串、空格：`errorno=-111004`，`errormsg=错误的idlist`
- `idlist=,` 或 `idlist=,,`：`errorno=10010039`，`errormsg=keys empty`
- 新补的 [analysis/api2_jsonp_batch_matrix_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_batch_matrix_20260620.json) 又把 `otype=json` 的 `mixed valid+invalid / duplicate+empty / dup32 / dup33` 4 条镜像 batch case 补到了当前 8 环境 same-day 稳定
  - 当前最稳结论是：**JSONP 只换外壳，不改这 4 条 batch semantics**
  - mixed valid+invalid 仍保序返回，非法项仍是 empty-shell 行
  - duplicate 仍占名额，empty slot 仍会被忽略
  - `dup32` 仍成功，`dup33` 仍返回 `-111001`
  - 但 repeated `idlist=a&idlist=b` 当前不会 merge 成第二种批量入口；tested branch 只消费首个 `idlist` 值

### 5.2 当前已确认的返回形态

接口 2 默认返回 XML。

但这轮已经确认还有一个稳定分支：

- 单个 `otype` key 为 `json`
  - 返回 JSONP
  - 默认外壳是 `QZOutputJson=...;`
  - 成功和失败都走这一层包裹，不会因为错误退回 XML
  - 但当前 direct query evidence 也说明：宽 callback 字符族都会把默认外壳改写成 callback-style 包裹，而空 `callback=` 会回落默认 `QZOutputJson=...;`；当前已确认的 parse-breaking 代表值至少包括未配对开括号 `callback=a(` / `callback=((`、pathological-tail 的 `callback=})();`，以及后续 unmatched-delimiter follow-up 补到的 `callback=[(` / `callback={(` / `callback=/*(` / `callback=a[(` / `callback=)(` / `callback=](` / `callback=}(`；相对地，`callback=[` 与 `callback=[[` 当前仍是 raw passthrough，所以不能把“带特殊字符”直接等同于坏壳
  - 当前 focused batch followup 还确认：`mixed valid+invalid / duplicate+empty / dup32 / dup33` 这些批量语义在 JSONP 侧和 XML 镜像 case 一致；变化只在外壳与 `Content-Type`
  - 如果 `otype` 重复，当前 tested branch 由首值决定 XML / JSONP 外壳

真实结构是：

- 批量响应是重复 `<results>` 块
- 每个 `<results>` 下有一个 `<fields>`
- `cover_list`、`category_map`、`vWH` 都可能是重复标签

也就是说，它不是旧文档里的 `<field>` 列表结构。

### 5.3 接口 2 字段证据总表

| 字段 | 当前状态 | 数据形态 | 当前理解 | 本轮关键观察 |
| --- | --- | --- | --- | --- |
| `vid` | 已实测确认 | 单值 ID | 当前视频 ID | 与 `<results><id>` 对齐 |
| `id` | 已实测确认 | 单值 ID | 当前 `<results>` 对应 ID | 与 `vid` 一致 |
| `title` | 已实测确认 | 单值文本 | 视频标题 | 稳定 |
| `duration` | 已实测确认 | 单值秒数字符串 | 时长（秒） | 稳定 |
| `url` | 已实测确认 | 单值 URL | 页面地址 | 稳定 |
| `defn` | 已实测确认 | JSON 对象字符串 | 清晰度 / 资源类型到体积的映射 | 稳定 |
| `cover_list` | 已实测确认 | 重复 XML 标签 | 该 `VID` 关联的 cover 列表 | 不一定只等于当前 CID |
| `c_covers` | 形态已确认，业务语义待补命名 | 单值 `+` 分隔 ID 串 | `cover_list` 的压缩表达 | 电影样本里常见多值 |
| `category_map` | 已实测确认 | 重复 XML 标签 | 扁平分类层级序列 | 形如 `id,name,id,name...` |
| `vWH` | 已实测确认 | 重复 XML 标签（2 个值） | 宽高二元组 | 稳定 |
| `state` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 视频状态枚举 | 已见 `4`、`8` |
| `upload_src` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 上传 / 入库来源枚举 | 已见 `0`、`6`、`7`、`20`、`31`、`105`、`107`、`108`、`116`、`117`、`129`、`138`、`141`、`146`、`149`、`2048` |
| `create_time` | 形态已确认，业务语义待补命名 | 单值时间串 | 记录创建 / 入库时间 | 形如 `YYYY-MM-DD HH:MM:SS` |
| `modify_time` | 形态已确认，业务语义待补命名 | 单值时间串 | 记录修改时间 | 多数与 `create_time` 相同 |
| `publish_date` | 形态已确认，业务语义待补命名 | 单值日期字段 | 不能直接当真实发布日期 | 目前既命中过真实样式日期，也命中过 `2010-01-01 00:00:00` 这种疑似占位值 |
| `targetid` | 形态已确认，业务语义待补命名 | 单值 ID / 空值 | 某种视频 / 业务目标实体 ID | 电视剧和少儿免费合集可非空，动漫 / 电影常为空 |
| `pic160x90` / `pic496x280` / `pic_640_360` | 已实测确认 | 单值 URL | 各尺寸封面图 | 稳定 |
| `is_normalized` | 形态已确认，业务语义待补命名 | 单值数值字符串 | 服务端内部状态位 | 稳定但未命名 |

### 5.4 `defn` 的当前最稳解释

`defn` 是 JSON 对象字符串，例如：

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

推荐展示口径：

| raw key | 推荐中文名 | 当前状态 |
| --- | --- | --- |
| `audio` | 音频 | 已实测确认 |
| `sd` | 标清（SD） | 已实测确认 |
| `hd` | 高清（HD） | 已实测确认 |
| `shd` | 超清（SHD） | 已实测确认 |
| `fhd` | 全高清 / 蓝光（FHD） | 已实测确认 |
| `uhd` | 超高清 / 4K（UHD） | 已实测确认 |
| `source` | 源片 / 原始片源（SOURCE） | 已实测确认 |

这一轮继续坐实了两点：

- `hd` 和 `shd` 必须拆开
- `sd` 并不是不存在，只是在部分电视剧 / 特殊条目上更容易出现

### 5.5 `cover_list` / `category_map` / `vWH`

#### `cover_list`

- 是重复 XML 标签
- 表示该 `VID` 关联的 cover 列表
- 不一定只包含当前 URL 的 `CID`

#### `category_map`

当前最稳解释是：

- 一个按 `id,name,id,name...` 扁平展开的分类层级序列

已实测示例：

- 电影：`10139, 正片, 1037, 电影, 1, 电影`
- 动漫：`10994, 正片, 1204, 动漫, 3, 动漫`
- 电视剧：`10470, 正片, 1089, 连续剧, 2, 电视剧`
- 电视剧预告片：`10479, 预告片, 1089, 连续剧, 2, 电视剧`
- 电视剧片花：`10481, 片花, 1089, 连续剧, 2, 电视剧`
- 电视剧花絮：`10480, 花絮, 1089, 连续剧, 2, 电视剧`
- 电视剧衍生资讯：`11876, 资讯节目, 1259, 电视剧衍生, 2, 电视剧`
- 娱乐资讯：`11408, 明星速闻, 11400, 明星资讯, 5, 娱乐`
- 饭拍饭制：`11420, 饭拍饭制, 11400, 明星资讯, 5, 娱乐`
- 纪录片：`10726, 正片, 1115, 腾讯自制纪录片, 9, 纪录片`
- 综艺：`10001, 正片, 1001, 栏目, 10, 综艺`
- 综艺花絮：`11862, 加更正片, 1001, 栏目, 10, 综艺`
- 综艺抢先看：`10004, 预告片, 1001, 栏目, 10, 综艺`
- 轻内容：`11922, 微综艺, 1001, 栏目, 10, 综艺`
- 少儿：`11244, 正片, 1250, 动画, 106, 少儿`

要特别注意：

- API1 的 `type / type_name` 更像 cover 外壳页自己的类型
- API2 的 `category_map` 更像单条视频本体的分类链
- 常规季页里两者通常大体对齐，但特殊聚合页 / 专题页可以明显错位

代表反例：

- `暑期作战大联盟，全员待命去冒险！`
  - API1：`113 / 表演演出`
  - API2 首批视频：`正片 > 玩具 / 动画 > 少儿`
- `鹅友新春来拜年【群星祝福视频】`
  - API1：`10 / 综艺`
  - API2 首批视频：`片花 / 预告片 > 连续剧 > 电视剧`
- `合成令`
  - API1：`2 / 电视剧`
  - API2 同页视频既有 `片花 / 预告片 > 连续剧 > 电视剧`
  - 也有 `明星速闻 / 饭拍饭制 > 明星资讯 > 娱乐`

#### `vWH`

- 是重复 XML 标签
- 每个视频稳定出现 2 个数值
- 可直接解释成 `WIDTH, HEIGHT`

### 5.6 `state` / `upload_src` / `publish_date` / `targetid`

#### `state`

当前至少已实测到：

```text
4
8
```

这一轮把原始逐条证据也补硬了：

- `暑期作战大联盟，全员待命去冒险！`
  - `video_count=283`
  - `state_counts={4:281, 8:2}`
  - `upload_counts={20:71, 105:2, 108:199, 141:11}`
  - 两条 `state=8` 原始记录：
    - `n3122jif99n`
      - `玩具开箱：艾米儿带来了舒克贝塔的玩具飞机和玩具坦克`
      - `state=8`
      - `upload_src=108`
      - `category_map=11249,正片,1251,玩具,106,少儿`
      - `https://v.qq.com/x/page/n3122jif99n.html`
    - `l3119lm045g`
      - `舒克贝塔飞机坦克玩具套装玩玩乐！团结合作完成救援恐龙任务！`
      - `state=8`
      - `upload_src=108`
      - `category_map=11244,正片,1250,动画,106,少儿`
      - `https://v.qq.com/x/page/l3119lm045g.html`

因此当前最稳的说法是：

- 字段形态已确认
- `4` 不是全站唯一值
- `8` 已经不再是 `mzc00200q00mv2h` 单点异常；后续已在 `type=106/少儿` 与 `type=113/表演演出` 两支复现到多个 cover
- `state=8` 当前更像行级 small-family signal，不是某个 cover 级固定壳标签
- `pay_status=8` 不推出 `state=8`，`state=8` 也不推出 `pay_status=8`
- 新补的 [analysis/state8_positive_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/state8_positive_environment_20260620.json) 已把 `482396nuyaelv0e` 与 `mzc002006tgfqvp` 这两个正 family 补到 `8` 个请求环境 same-day 稳定，且 `state/upload_src` 分布与 `2026-06-19` 基线一致
- 新补的 [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json) 已把 `mzc00200s6oqemg / mzc00200ua6uec2 / mzc002008tghx9y / mzc00200rcuv1sy` 这 4-cover core set 补到 `8` 个请求环境无漂移：两个 pure `2048` 正例继续保持 `targetid_nonempty_count=7`，mixed cover 继续保持 `2048/108` 共存，same-type pure-0 negative 继续保持 `targetid_nonempty_count=0`
- 当前待补的是：为什么有些 sibling cover 只有稀疏 `state=8` 行，而有些 cover 会变成 `state=8`-heavy family；以及它是否还会稳定扩到更多独立 family

#### `upload_src`

本轮已实测到：

- `0`
- `6`
- `7`
- `20`
- `31`
- `105`
- `107`
- `108`
- `116`
- `117`
- `129`
- `138`
- `141`

已见到的分布特征：

- `0`：当前已在 `喜羊羊与灰太狼合集`、`精彩动画大荟萃` 中直接复现
- `6`：当前已在 `精彩动画大荟萃` 和 `一人之下 第2季` 里直接复现，代表条目包括 `遵守课堂纪律`、`玩手机`、`邻居`、`一人之下_01`
- `20`：默认最常见
- `7`：已命中过电影主片和少儿长剧集，不是某个单类型专属值
- `31`：当前已命中 `跑男五哈高能游戏，承包男生笑点！`、`请查收你的五一快乐`，以及 `剑来 第二季` 里的国剧盛典荣誉 / 主创亮相类视频
- `105`：当前命中少儿安全教育短视频
- `107`：在 `五哈热点一网打尽` 里稳定命中 36~60 秒的“栏目正片”短内容；少儿短内容里也大量出现
- `108`：既会命中 `问心2` 的 `片花 / 花絮`，也会命中少儿混装运营页中的大量短内容
- `116`：当前命中 `熊出没之冬日乐翻天_01~05`
- `117`：当前已命中 `好评如潮！青春励志电影片单 -> 废柴联盟`
- `129`：在 `问心2` 的正片与预告片中稳定出现，也命中过少儿单条正片
- `138`：不只是 `我的心略大于整个宇宙` 孤例，在 `五哈热点一网打尽` 里也稳定落在 `微综艺 / 资讯节目 / 评论解读`
- `141`：当前命中过少儿音乐、英语启蒙和一部分少儿短内容

`问心2` 这组样本尤其说明：

- `category_map=预告片` 的主条目会命中 `129`
- `category_map=片花` 的 clip 抽样会混合命中 `107/108/20`
- `category_map=花絮` 的 clip 抽样会命中 `108/20`
- `category_map=资讯节目` 的 clip 抽样目前命中 `20`

所以 `upload_src` 和 `category_map` 明显相关，但并不是一一对应关系。

而这轮补回来的 3 个脏页原始证据，又把几个关键枚举钉得更实：

- `五哈热点一网打尽`
  - `video_count=114`
  - `state_counts={4:114}`
  - `upload_counts={20:28, 107:18, 108:63, 138:5}`
  - `upload_src=107` 代表条目：
    - `f41023gibme` / `邓超说霸总台词 一分钟八百个动作` / `state=4` / `10001,正片,1001,栏目,10,综艺`
    - `g4102k4sv6b` / `金志文被泼满脸泥反应亮了` / `state=4` / `10001,正片,1001,栏目,10,综艺`
    - `r4102i22si5` / `感谢“鹿角”先生给孩子们的足球装备` / `state=4` / `10010,片段,1001,栏目,10,综艺`
    - `j4102f0hj42` / `邓超庆祝五哈6定档，与小黑人共舞被强制下班` / `state=4` / `10004,预告片,1001,栏目,10,综艺`
  - `upload_src=138` 代表条目：
    - `g31977cqq04` / `五哈铁三角邓超陈赫鹿晗合体，谁的下饭伴侣回归了《五哈6》` / `state=4` / `11881,评论解读,1001,栏目,10,综艺`
    - `f3197n42wk9` / `《五哈6》官宣，鹿晗回归后“铁三角”终于重聚，依旧是熟悉的面孔` / `state=4` / `11880,资讯节目,1001,栏目,10,综艺`
    - `r31970xkhnb` / `邓超陈赫鹿晗“铁三角”再度合体，快乐都要溢出屏幕啦《五哈6》` / `state=4` / `11922,微综艺,1001,栏目,10,综艺`
    - `d3197nta6q6` / `《五哈6》官宣定档4月4日，鹿晗邓超陈赫再合体，泥地摔跤放飞自我` / `state=4` / `11880,资讯节目,1001,栏目,10,综艺`
- `免费动画屋`
  - `video_count=356`
  - `state_counts={4:356}`
  - `upload_counts={7:21, 20:225, 107:104, 116:5, 129:1}`
  - `upload_src=107` 代表条目：
    - `s0025v443sh` / `雪地搜索` / `state=4`
    - `l002517vjlb` / `海上救援` / `state=4`
    - `g0025x0npkg` / `狗狗拯救海龟` / `state=4`
    - `w002527exh2` / `冰上救援` / `state=4`
- `鹅友新春来拜年【群星祝福视频】`
  - `video_count=33`
  - `state_counts={4:33}`
  - `upload_counts={20:33}`
  - 这页没有打到 `state=8`、`upload_src=107`、`upload_src=138`

而新类型代表页子集，这一轮也给出了一个很干净的负证据：

- `type=6 / 游戏`
  - `《庆余年》手游虚拟直播发布会`
    - `state_counts={4:11}`
    - `upload_counts={31:1,108:10}`
  - `2026腾讯游戏发布会`
    - `state_counts={4:40}`
    - `upload_counts={20:40}`
- `type=22 / 音乐`
  - `2023TMEA腾讯音乐娱乐盛典`
    - `state_counts={4:32}`
    - `upload_counts={20:32}`
  - `BIGBANG十周年演唱会首尔站`
    - `state_counts={4:29}`
    - `upload_counts={20:1,31:28}`
- `type=31 / 生活`
  - `音乐会《黄河大合唱》中国交响乐团`
    - `state_counts={4:1}`
    - `upload_counts={0:1}`
- `type=113 / 表演演出`
  - `暑期作战大联盟，全员待命去冒险！`
    - `state_counts={4:281,8:2}`
    - `upload_counts={20:71,105:2,108:199,141:11}`

所以这批新类型代表页本轮也没有扩出新的 `state`，但后来继续补体育 / 动漫 / 教育 / 文化历史样本后，`upload_src` 还新增了 `146`、`149`、`2048`。当前全局已知集合是：

- `state={4,8}`
- `upload_src={0,6,7,20,31,105,107,108,116,117,129,138,141,146,149,2048}`

其中 `upload_src=2048` 这轮已经单独补到了 [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json)：当前 tested 4-cover core set 在 `8` 个请求环境下都无漂移，所以它现在更适合写成“环境稳定但 family boundary 仍未闭合”的小家族值，而不是单环境观察。

而 `五哈热点一网打尽`、`免费动画屋`、`暑期作战大联盟，全员待命去冒险！` 这几页又说明：

- `pay_status=8` 并不对应某个固定 `upload_src`
- 大聚合 / 运营页最容易把 `upload_src` 新枚举打出来
- 这类页适合“扩枚举”，但不适合把某个单值语义写死

而 `精彩动画大荟萃` 和 `喜羊羊与灰太狼合集` 又说明：

- 少儿混装大聚合页还能继续扩出 `0`、`6`
- `upload_src=0`、`6` 当前都已经不是单条孤点

但这些还只是黑盒分布观察，不能直接把它们命名成“UGC / PGC / 宣传片源 / 正片片源”。

#### `publish_date / targetid` 的页型解释框架

到这一轮为止，这两个字段最稳的解释轴已经不是单独看 `type`，而是先看“页型 + 编排形态”。

| 页型桶 | 代表样本 | `publish_date` 非空率 | `targetid` 非空率 | 当前最稳规则 |
| --- | --- | ---: | ---: | --- |
| 常规电视剧季页 | `长安诺` | `0/56` | `56/56` | `publish_date` 近乎全空，`targetid` 强阳性 |
| 综艺季页 | `开始推理吧 第4季` + `哈哈哈哈哈 第6季` | `95/99` | `0/99` | `publish_date` 对主条目强阳性，`targetid` 强阴性 |
| 综艺专题 / 视角壳页 | `战至巅峰之赛事全局看` + `战至巅峰之第一视角` | `2/56` | `56/56` | 当前更接近“`targetid` 强阳性但 `publish_date` 近乎全空”的窄专题页 |
| 体育人物 / 赛事资讯壳页 | `体育人物` + `影说赛事` + `NBA总决赛名局纪录片：星耀传奇` | `0/197` | `0/197` | 当前样本层面稳定双空，且 `targetid` 强阴性；但内部仍可能再拆人物 / 资讯 / 纪录片子支 |
| 体育活动回放页 | `2026NBA总冠军巡游` + `2026FE电动方程式世界锦标赛迈阿密站 正赛` | `53/53` | `0/53` | `publish_date` 强阳性，`targetid` 强阴性；当前第 2 代表也已补到同规格 same-day probe |
| 体育比赛集锦 / 单轮赛事合集壳页 | `22/23赛季欧冠1/8决赛次回合视频集锦` + `22/23赛季欧冠1/8决赛次回合：曼城7-0RB莱比锡（总比分8-1）` | `0/54` | `54/54` | 当前 clean representative 已补到 `mzc002003fh665c`：更像围绕单轮/单场赛事的球队集锦、进球集锦、球星集锦、十佳球等二级条目的 collection shell；`mzc0020069a6anp` 则更像混入回放与盘点短片的 sibling event hub |
| 电影单片 | `飞驰人生3` + `熊出没·年年有熊` | `0/2` | `0/2` | 当前样本层面稳定双空，但还别写死成全站绝对规则 |
| 动漫季页 | `一人之下 第6季` + `剑来 第二季` | `1/77` | `1/77` | 主体接近双空，但存在“番外孤点”异常 |
| 少儿 `double-zero` 分支 | `汪汪队立大功第五季[普通话版]` + `小猪佩奇 第11季[普通话版]` + `汪汪队大救援第五季` | `0/87` | `0/87` | 当前已跨 IP 复现，且 [analysis/environment_page_shape_kids_retest_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_kids_retest_20260619.json) 已把 `mzc00200qrzj493` 的 base-4 same-day 稳定性补齐；这支也已证伪“固定 `upload_src=129`” |
| 少儿 clean season-style `dual-full` 分支 | `小猪佩奇第6季[普通话版]` + `汪汪队立大功第一季` + `超级飞侠 第五季[普通话版]` | `72/72` | `72/72` | 当前已跨 IP 复现，说明这不再是单一 IP 内部偶发分支 |
| 少儿合集 / 主题聚合壳（邻近 hybrid，暂定） | `小猪佩奇合集[普通话版]` + `小猪佩奇快乐旅行` | `245/395` | `395/395` | 当前 `targetid` 可全满，但 `publish_date` 不是全满；更像邻近 hybrid/aggregation branch，不宜直接并入 strict `dual-full` |
| 少儿免费合集 | `汪汪队立大功免费合集` + `小猪佩奇免费合集` | `123/175` | `166/175` | `targetid` 几乎总有；`publish_date` 也常非空，但大量是 `2010-01-01 00:00:00` 占位值 |
| 专题页 | `合成令` + `畅游天下·云南篇` | `0/34` | `7/34` | `publish_date` 很稳地空；`targetid` 可稀疏出现，不能写成全空 |

这一轮 kids 拆桶新增的直接证据主要来自：

- [analysis/kids_pay6_branch_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/kids_pay6_branch_followup_20260619.json)
- [analysis/search_kids_cross_ip_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/search_kids_cross_ip_followup_20260619.json)
- [analysis/kids_cross_ip_field_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/kids_cross_ip_field_followup_20260619.json)
- [analysis/environment_page_shape_sports_kids_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_sports_kids_followup_20260619.json)
- [analysis/kids_hybrid_family_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/kids_hybrid_family_followup_20260619.json)

因此更稳的表述是：

- `publish_date / targetid` 更像“页型字段”，不是单纯的“内容类型字段”
- `type` 仍有作用，但更适合在页型桶内再做第二层细分
- `type=4 / 体育` 当前至少已经打出 3 条稳定页型解释支路：
  - `体育活动回放页`
  - `体育人物 / 赛事资讯壳页`
  - `体育比赛集锦 / 单轮赛事合集壳页`
- `mzc002003fh665c / 22/23赛季欧冠1/8决赛次回合视频集锦` 当前已经补到 base-4 cross-day followup，继续稳定在 `publish_date=0/23 + targetid=23/23 + upload_src=20`，因此更适合当这条 sports collection shell 的 clean representative
- 所以 `mzc0020069a6anp` 不能再当 replay 第 2 代表候选；它更像混入回放与盘点短片的 sibling event hub，而不是这条桶里最干净的代表
- 第二轮 replay hunt 里，`mzc0020086fhhzs / NBA全明星正赛` 虽然也满足 `type=4 + pay_status=8 + positive_trailer=1`，但它的页型是 `publish_date=2/88`、`targetid=0/88`，更像赛事聚合主壳，不像 clean replay 第二代表
- 当前真正更接近 replay 第二代表的是 `mzc00200k9sp5r2 / 2026FE电动方程式世界锦标赛迈阿密站 正赛`：`publish_date=22/22`、`targetid=0/22`、`upload_src` 以 `31` 为主，且 base-4 same-day probe 稳定
- `jynqzy9n3wfrsfp` 在 2026-06-20 的 base-4 cross-day followup 里仍落在 `publish_date=20/20 + targetid=20/20 + upload_src=20`，因此更应回到 clean dual-full，而不是继续挂在 hybrid 候选上
- `bzfkv5se8qaqel2` 与 `mzc00200yokeal4` 在 2026-06-20 的 base-4 cross-day followup 里也继续分别稳定在 `221/354`、`24/41` 这类 `targetid` 全满但 `publish_date` 只部分非空的形态，更像邻近 hybrid/aggregation branch

#### `publish_date`

这轮有一个关键修正：

- 它不能直接当“真实发布日期”

目前命中的非空样本包括：

- `番外篇 天师下山`
  - `publish_date = 2010-01-01 00:00:00`
- `开始推理吧 第4季` 同 `CID` 下的条目
  - 正片：`2026-06-18 00:00:00`
  - 花絮：`2026-05-30 00:00:00`
  - 直播回放：`2026-03-24 00:00:00`
  - 抢先看：`2026-06-24 00:00:00`
  - 同一 cover 下的 38 个主条目，本轮都能命中非空 `publish_date`

所以当前最稳的表述是：

- `publish_date` 有时会给出真实样式日期
- 但它也会给出明显像占位值的日期
- 它的非空率首先更受页型影响
  - 综艺季页：强阳性
  - 少儿免费合集：高频非空，但大量是占位值
  - 电视剧常规季页 / 电影单片 / 专题页：强阴性
- 因此不能直接把它当“真实发布日期”

#### `targetid`

当前最稳的结论：

- 它不是 cover ID
- 它也不是稳定必填字段
- 它更像某种视频 / 业务实体 ID

已见到的分布：

- `长安诺` 全 56 集都有各自不同的 `targetid`
- `汪汪队立大功免费合集` 的首条 `VID` 非空
- `小猪佩奇免费合集` 的首条 `VID` 非空
- `畅游天下·云南篇` 这种专题页也能稀疏非空
- 电影、纪录片、很多动漫条目则为空

因此这里也不能再只按 `type` 解释，更稳的说法是：

- 常规电视剧季页：强阳性
- 综艺季页：强阴性
- 少儿免费合集：高密度阳性
- 专题页：可稀疏出现，但不能写成全空
- 动漫季页 / 电影单片：当前样本整体偏空，但还要保留孤点例外

## 6. 本轮新增的硬结论

1. `type` 当前至少已补到 15 种：
   - `1=电影`
   - `2=电视剧`
   - `3=动漫`
   - `4=体育`
   - `6=游戏`
   - `9=纪录片`
   - `10=综艺`
   - `22=音乐`
   - `27=教育`
   - `28=科技`
   - `29=汽车`
   - `31=生活`
   - `106=少儿`
   - `111=文化历史`
   - `113=表演演出`

2. `pay_status` 当前稳定非空值已见 `5`、`6`、`7`、`8`、`9`、`15`、`16`；另见过空串异常壳页，但还不建议把空串提升成稳定枚举
   - 其中 `pay_status=9` 已明确不是“只在动漫”；当前也已在 `type=10 / 综艺` 上复现

3. API1 的参数契约在当前同日 4 环境矩阵下已经实测确认：
   - `tid` / `idlist` 是硬参数
   - `appid / appkey` 是分支式校验，不是普通必填鉴权参数
   - 多 `CID` 批量必须检查每个 `<results>` 的 `retcode`

4. `downright` 不是条目级映射，而是 cover 级代码集合；而且它在一部分 cover 上可以直接为空，不只会出现在专题 / 聚合页上，也已经明确出现在 canonical 纪录片季页和 canonical 电影单片页上

5. `positive_content_id` 不是内容自己的 ID，也不是全站常量；当前强负证据仍只见 `1543606`、`1543607`，而且 `1543607` 已明确落到电影、综艺、少儿、电视剧直播壳页，也不等于某个固定 `pay_status` 或 `positive_trailer`

6. `positive_trailer` 不是“是否预告片”布尔值；当前至少已见 `0/1/2`，其中 `0` 是很强的非 canonical / 聚合页信号，但不是充分必要条件，而 `2` 当前已从电视剧链扩到综艺同类对照组，第一层可见模式更偏 preview-like / `预告` 支线，但仍不能把它升级成严格 UI 开关

7. `F=0` 和 `F=4` 当前都强相关于预告类条目；`F=2` 和 `F=7` 都是可播条目桶，但都不能再简单翻译成“正片 / 花絮”或“长视频 / 短视频”

8. API2 的参数契约在当前 8 环境 focused matrix + 代表页 field-drift retest 下已继续补强：
   - 错误默认仍是 `HTTP 200`
   - 单 key query 下，`tid` 是硬路由参数；如果 `tid` 重复，当前 tested branch 由首值决定路由/错误分支
   - 当且仅当单个 `otype=json` key 生效时，成功和失败默认都会返回 `QZOutputJson=...;`
   - 新补的 JSONP mirror batch 说明：单个 `otype=json` + 单个 `idlist` key 时，也保持 `mixed valid+invalid / duplicate+empty / 32/33` 这 4 条批量边界语义，不会因为换壳而改行为
   - `union_platform` 当前在匿名 canonical tested branches 与真实匿名 visitor cookie replay 下都未观察到可见行为差异
   - `appid / appkey` 仍是分支式校验；新补的 XML repeated 对撞 case 又说明：当前 tested branches 下，repeated `appid / appkey` 也都是首值生效

9. API2 的 `state` 已不止 `4`，还直接打出了 `8`；当前更稳的说法是：`8` 已明确是一个跨 `type=106/113` 的小家族 / 行级 signal，但离全局页型标签还差反证

10. `upload_src` 已扩到 `0`、`6`、`7`、`20`、`31`、`105`、`107`、`108`、`116`、`117`、`129`、`138`、`141`、`146`、`149`、`2048`
    - 其中 `2048` 已从单点异常升级成至少 2 个独立 `type=111 / 文化历史` 样本的小家族，但“能否跨出 type=111”仍待补反例

11. API1 的 `type / type_name` 和 API2 的 `category_map` 在特殊聚合页上可以明显错位，甚至会从 `电视剧` 直接混到 `娱乐`

12. API2 单次批量请求的 `idlist` 实测上限是 `32` 个非空 item；重复值和无效值都占名额，空槽位会被忽略；这条边界当前在 XML 与 `otype=json` 两条壳层上都已闭环

13. `publish_date / targetid` 更像“页型字段”而不是单纯的“内容类型字段”
   - `publish_date` 至少在当前样本里不能直接拿来当真实发布日期
   - `targetid` 在电视剧和部分少儿样本里很有用，但仍不是稳定必填字段

14. 环境矩阵这一轮已经补到“contract + representative field drift + page-shape second representative”三层：
    - API1 / API2 都已确认 `32` 个非空 `idlist` item 成功、`33` 个触发 `-111001`
    - 这条边界在基础 4 环境，以及新增 browser-like 4 环境里，`2026-06-19` same-day 与 `2026-06-20` cross-day retest 都没有打出稳定分叉
    - 当前最稳的说法是：这两套接口的 tested contract cases 主要受 query 参数控制，而不是受本轮所测请求头环境控制
    - 第一轮 5 个 canonical representative field-drift 页面，在 8 个已测环境里先完成了 same-day 稳定；到 `2026-06-20` 为止，这 5 页的 selected-row 字段签名又继续保持 8 环境 cross-day 稳定
    - 当前已补到 base-4 cross-day stable 的 second representative / followup，包括：`电影单片 / 动漫季页 / 常规电视剧季页 / 综艺季页 / generic 专题页 / 少儿免费合集 / 少儿 double-zero 分支 / sports collection shell clean representative / kids clean dual-full / kids hybrid 邻近两条 followup`
    - [analysis/environment_page_shape_kids_retest_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_kids_retest_20260619.json) 进一步说明：`mzc00200qrzj493` 之前那次 `referer_origin -> no_video_rows` 更像瞬时 probe failure，而不是稳定环境分支
    - 当前环境层的主要缺口已经从“契约或 canonical field-drift 是否受请求头环境影响”转成两类尾项：一类是真实登录态 / 老化 Cookie，另一类是还没补 cross-day 的页型桶
    - browser-like `sec-ch-ua / sec-fetch-* / synthetic-cookie` 已补测，真实匿名 visitor cookie replay 也已补到；真实登录态 / 老化 Cookie 会话环境仍未闭合
    - 这条线的匿名 replay 输入面已经补好：可先用 [tools/tencent_anonymous_cookie_replay_env_capture.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_anonymous_cookie_replay_env_capture.js) 导出真实匿名 replay JSON，再通过 [tools/tencent_environment_matrix_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_environment_matrix_probe.py) 的 `--extra-env-json` 注入；`aged-cookie / login-state` 也已有 [tools/tencent_cookie_env_from_headers.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_cookie_env_from_headers.py) 这种 header-to-env 构造入口，但尚无正式实测产物。手工模板仍见 [examples/environment/real_cookie_env.template.json](C:/Users/lin/Documents/YM查询工具还原/examples/environment/real_cookie_env.template.json)

## 7. 这一轮之后，还剩什么没完全命名

如果只谈“接口怎么解析、字段长什么样、哪些旧理解是错的”，这一轮已经基本摸清了。

剩下没有完全闭合的，不只剩后端枚举名，还包括少量 family boundary、前端次级链路消费，以及环境跨日 / `aged-cookie` / `login-state` 矩阵。后台正式命名仍然是最大块未解项：

- `pay_status=5` / `6` / `7` / `8` / `9` / `15` / `16` 的官方后台命名
- `downright` 每个数字代码的精确业务含义
- `F=2` / `F=7` 的官方后台命名
- `positive_trailer=0/1/2` 的官方后台命名
- `state=4` / `8` 的后台枚举名
- `upload_src=0/6/7/20/31/105/107/108/116/117/129/138/141/146/149/2048` 的后台枚举名
- `targetid` 精确对应哪类实体
- `positive_content_id=1543606/1543607` 各自对应什么后台配置或分流逻辑

也就是说，黑盒层面的“不确定”，现在已经很少是“这字段到底在干嘛”，更多是三类尾项：

- 后台把这个值正式叫啥
- 少量 family boundary 还能不能继续扩圈
- 前端次级链路 / 跨日环境矩阵还要不要补反证

## 8. 调用示例

`curl`：

```bash
curl "https://data.video.qq.com/fcgi-bin/data?tid=431&idlist=mzc00200idzf2m8&appid=10001005&appkey=0d1a9ddd94de871b"
curl "https://union.video.qq.com/fcgi-bin/data?otype=xml&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4"
curl "https://union.video.qq.com/fcgi-bin/data?otype=json&tid=535&appid=20001238&appkey=6c03bbe9658448a4&union_platform=3&idlist=z4102qfi0x4"
```

真实匿名 visitor cookie replay 环境矩阵：

```bash
"C:\Users\lin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" tools/tencent_anonymous_cookie_replay_env_capture.js --output analysis/anonymous_real_cookie_env_20260621.json
python tools/tencent_environment_matrix_probe.py --include-browser-like --extra-env-json analysis/anonymous_real_cookie_env_20260621.json --output analysis/environment_matrix_anonymous_real_cookie_20260621.json
```

`aged-cookie / login-state` replay 输入构造：

```bash
python tools/tencent_cookie_env_from_headers.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt --output analysis/aged_cookie_env_20260621.json
python tools/tencent_cookie_env_from_headers.py --mode login --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt --output analysis/login_state_env_20260621.json
```

`--mobile-cookie-file` 可以按需补；按当前 env-builder 契约，第一轮 `aged/login` replay 的最小输入就是一份 `PC Web Cookie`，`mobile H5 Cookie` 仍然只是可选增强。其余 `User-Agent / Accept / Referer / Origin` 由脚本自动填充。这里的 `analysis/aged_cookie_env_20260621.json` 与 `analysis/login_state_env_20260621.json` 是首次执行时生成的输出路径示例，不是仓库预置输入文件。

如果要把 `aged-cookie / login-state` 的最后闭环路径收成单命令，而不是手工串多条 probe，可直接用：

```bash
python tools/tencent_replay_bundle_runner.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt
python tools/tencent_replay_bundle_runner.py --mode login --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt
```

它会自动生成 env JSON、环境矩阵输出、`authish` 语义复测输出，并再写一份 top-level summary。

如果要把 `callback` pathological-tail 和 full semantics 一起带进 replay，当前推荐显式写：

```bash
python tools/tencent_replay_bundle_runner.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt --semantics-profile full --probe-extra-callback-value "})();"
python tools/tencent_replay_bundle_runner.py --mode login --desktop-cookie-file examples/environment/pc_login_cookie_header.template.txt --semantics-profile full --probe-extra-callback-file analysis/callback_tail_values.txt
```

如果要先看“这条 replay 总入口到底承诺了什么、哪些输入是真硬要求、哪些结论现在还不能升级”，现在有 3 份专门的契约层归档：

- [analysis/environment_replay_runner_contract_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_runner_contract_20260622.json)
- [analysis/environment_replay_input_boundary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_input_boundary_20260622.json)
- [analysis/environment_replay_hard_block_table_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_hard_block_table_20260622.json)

在本地受限环境里，如果子进程往仓库 `analysis/` 直接落盘会碰路径策略，可再加：

```bash
python tools/tencent_replay_bundle_runner.py --mode aged --desktop-cookie-file examples/environment/pc_aged_cookie_header.template.txt --semantics-profile full --artifact-output-dir C:/Users/lin/AppData/Local/Temp/replay_bundle_artifacts --subprocess-output-dir C:/Users/lin/AppData/Local/Temp/replay_bundle_stage
```

这两个输出目录参数的职责是分开的：

- `--subprocess-output-dir`
  - 子进程 JSON 先写到 staging 目录
- `--artifact-output-dir`
  - 父进程再把最终 env / matrix / semantics / summary 产物落到指定目录

这条链路已经有正式自测证据，不再只是脚本里“理论支持”。

Python 示例：

- [examples/python/tencent_video_api_demo.py](C:/Users/lin/Documents/YM查询工具还原/examples/python/tencent_video_api_demo.py)
  - 已内置 `api2_batch_diagnostics`
  - API2 JSONP 全坏批量时，会把逐项结果标成 `empty_shell=true`
  - 当整批都是 `empty_shell=true` 时，调用方应按 `all-invalid/empty-shell batch` 处理，而不是只看顶层 `errorno` / 逐项 `retcode`

Go 示例：

- [examples/go/main.go](C:/Users/lin/Documents/YM查询工具还原/examples/go/main.go)
  - 已同步补齐 `api2_batch_diagnostics` 与 `empty_shell` 识别

字段巡检脚本：

- [tools/tencent_video_field_survey.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_video_field_survey.py)

参数契约探针：

- [tools/tencent_api_contract_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_api_contract_probe.py)

增强层探针 / 归档：

- [tools/tencent_search_seed_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_search_seed_probe.py)
- [tools/tencent_value_family_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_value_family_probe.py)
- [tools/tencent_gap_ledger.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_gap_ledger.py)
- [tools/tencent_frontend_semantic_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_frontend_semantic_probe.py)
- [tools/tencent_frontend_dynamic_hook_probe.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_frontend_dynamic_hook_probe.js)
- [tools/tencent_frontend_runtime_store_probe.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_frontend_runtime_store_probe.js)
- [tools/tencent_environment_matrix_probe.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_environment_matrix_probe.py)
- [tools/tencent_anonymous_cookie_replay_env_capture.js](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_anonymous_cookie_replay_env_capture.js)
- [tools/tencent_replay_bundle_runner.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_replay_bundle_runner.py)
- [tools/tencent_enum_cards.py](C:/Users/lin/Documents/YM查询工具还原/tools/tencent_enum_cards.py)

## 9. 已明确 / 部分明确 / 未明确

### 已明确（当前匿名直连与已测样本范围内）

- API1 / API2 的基础契约、错误码外壳、批量行为、`32/33` 非空 item 边界
- `pay_status=5/6/7/8/9/15/16` 都已不是“想当然的单点猜测”
- `type` 已补到 `15` 种，新增 `28/科技`、`29/汽车`、`111/文化历史`
- `publish_date / targetid` 主要由“页型环境”决定，`type` 是第二层解释轴
- 前端主 bundle 已能坐实几条消费链：
  - `pay_status` 参与 VIP 相关逻辑/上报；但 sampled runtime `union.coverInfoMap` 槽位已经不是 raw API pay_status 直通
  - `positive_trailer` 归一化后仍进入前端状态；当前代表页已补到第一层可见 UI 模式：`2` 更常落到 `精彩预告` / `预告` badge，`1` 在 kids 代表页落到 `精彩片花` tab，`0` 在综艺专题代表页落到 `选集` / `SVIP` / `纯享` surface；但这仍属于 page-shape-correlated evidence，不是同构因果闭环
  - `state` 会进入 “未上架 / 已下架 / 已删除 / 不可用 / 不可播” 校验分支
  - `downright` 参与下载按钮逻辑
  - `cover_list / c_covers / topic_id_list` 会先被前端合并去重，再进入后续请求链
  - `publish_date` 会先被格式化，再受 `usePublishDate` 之类的前端开关控制
  - `targetid` 已能定位到静态 player/danmaku sink，并补到 `root.base.commentInfo.targetid` 这条评论/社区侧次级容器；当前 `REQUEST_REPORT -> DANMAKU_REPORT -> attachIframe(...)` 的 consumer 映射已被 synthetic runtime probe 闭合，但自然 producer 仍未拿到

### 部分明确（形态已确认，语义待命名）

- `positive_content_id=1543606 / 1543607`
- `positive_trailer=0/1/2` 的后台枚举名
- `state=4/8` 的后台枚举名
- `upload_src=0/6/7/20/31/105/107/108/116/117/129/138/141/146/149/2048`
- `F=0/2/4/7`
- `downright` 的具体数字码业务名
- `targetid` 精确对应的实体类型

### 未明确（仍待补反例）

- `pay_status=15` 是否还能继续长到综艺之外，或者仍只稳定落在综艺窄运营链
- `pay_status=16` 是否会跨出综艺体系
- `pay_status=9` 是否能继续补到更多明确 type 的独立样本
- `state=8` 的 family boundary 和占比差异：为什么有些 sibling cover 只有稀疏 `state=8` 行，而有些 cover 会变成 `state=8`-heavy family
- `upload_src=2048` 是否会跨出当前 `type=111 / 文化历史` 家族
- 前端是否只会在更早的 `getPage` tagged shaping / SSR / vector-layout 层吃掉 `upload_src / F`；新补的 stronger non-detail 候选仍会重定向进 detail，且 request-side 只打到 `getPage + FillUnionInfo`，还没见到真实 `getCoverInfoBatch` 请求
- `downright` 差异码全集是否还能继续补全，尤其是 `41 / 184`

## 10. 枚举值状态表

完整卡片见：

- [analysis/enum_index_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_index_20260619.json)
- [analysis/enum_cards_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_cards_20260619.json)
- [analysis/pay_status_manual_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/pay_status_manual_followup_20260619.json)
- [analysis/upload_src_2048_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_followup_20260619.json)
- [analysis/state8_positive_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/state8_positive_environment_20260620.json)
- [analysis/frontend_true_nondetail_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_true_nondetail_probe_20260620.json)
- [analysis/frontend_startup_vs_runtime_diff_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_vs_runtime_diff_20260620.json)
- [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json)
- [analysis/upload_src_2048_type111_search_expansion_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_type111_search_expansion_20260620.json)
- [analysis/enum_followup_pay_status7_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_followup_pay_status7_20260619.json)
- [analysis/enum_followup_f_downright_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/enum_followup_f_downright_20260619.json)

这里先放高信号摘要表，不替代完整卡片：

| 字段 | 值 | 当前状态 | 样本数 | 分布(type/page_shape) | 代表样本 | 当前最稳结论 | 未确认项 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pay_status` | `6` | 稳定值 | `66` | `4/体育`、`106/少儿`、`2/电视剧`、`3/动漫`、`9/纪录片`；其中 `type=106` 当前已拆成 `double-zero`、clean season-style `dual-full`，以及邻近 hybrid/aggregation 分支 | `mzc00200qrzj493` / `zkbp0mrqhy0x1hl` / `ca1k6ja4k81h8ov` / `ob6ak6eq2wp5qui` | 不能再写成单一少儿常规季页，也不能推出固定 `upload_src=129`；kids 这支已跨多个 IP 复现 | hybrid/aggregation 边界；官方后台命名 |
| `pay_status` | `9` | 小家族值 | `3` | `3/动漫`、`10/综艺`；原创动漫季页 / 综艺衍生轻页 | `mzc003ikavbkqa7` / `mzc00200yilptw9` | 已明确跨出“只在动漫”；当前至少覆盖动漫、综艺两支 | 是否还能继续扩到更多类目；官方后台命名 |
| `pay_status` | `15` | 小家族值 | `4` | `10/综艺`；当前更像综艺专题 / 视角 / 专场运营-like 壳 | `mzc002001u873es` / `mzc00200k1tze71` / `mzc00200sd1b239` | 当前更像综艺内窄运营 `small_family`；focused runtime followup 已在 `variety_topic_pay15` 抓到 parse-layer raw `15`，但 exposed `union.coverInfoMap.pay_status` 仍是 `0` | 是否会跨出综艺；这些页型名是否只是黑盒近似；官方后台命名 |
| `pay_status` | `16` | 小家族值 | `9` | `10/综艺`；当前更像综艺主季页 / 衍生页 / 活动页-like 壳 | `mzc00200u2ay1kj` / `mzc00200c24ypkp` / `mzc00200tzs7ig5` | 当前更像综艺 bounded `small_family`，比分布在专题/视角/运营-like 壳附近的 `15` 更靠近综艺主季页周边，但还不能命名成固定业务码 | 是否会跨出综艺；和 `15` 的分界是否只是分布偏好；官方后台命名 |
| `state` | `8` | 小家族值 | `6` | 当前正例主要落在少儿聚合壳稀疏行；现有 `106/少儿`、`113/表演演出` 只是已确认正样本 family，不是完整 observed universe | `mzc00200q00mv2h` / `mzc002006tgfqvp` | 已跨多个 cover，更像行级 small-family signal，不是 sports/kids 页型桶或单一 cover 壳标签；其中 `482396nuyaelv0e` 与 `mzc002006tgfqvp` 已补到 8 环境 same-day 稳定并匹配 `2026-06-19` 基线 | sibling 里稀疏 / heavy 差异原因；是否继续扩到更多 family；官方后台命名 |
| `upload_src` | `2048` | 小家族值 | `35 = 20` complete pure-2048 `+ 3` partial-only-2048 `+ 12` mixed | 当前 sampled slice 仍只见 `111/文化历史`，但已经扩到舞蹈 / 国画 / 书法教学类 cover；同 type 里现已同时补出 pure `0`、pure `108`、`2048/108`、`2048/0` | `mzc00200s6oqemg` / `mzc00200fq96jcg` / `mzc002005kpqrxs` / `mzc00200tjnrzs3` | 当前仍像 `type=111` teaching-family cluster，但已经不能写成整个 `type=111` 的统一值；新 8 环境 replay 说明 tested core set 的 pure-positive / mixed / same-type-negative 边界不是请求环境偶然现象，而新的 search expansion 还首次补到 complete pure-2048 + empty `targetid` 反例 `mzc00200tjnrzs3` | 是否会跨出 `type=111`；当前 dance / painting / calligraphy teaching 分支是否还要继续拆细；官方后台命名 |
| `F` | `2` | 稳定值 | `4+` | 当前主可播桶之一 | `mzc00200tuupfc2` / `mzc00200bhj36oq` | 可播条目主桶之一，但不能简单翻译成“正片” | 官方后台命名 |
| `F` | `7` | 稳定值 | `5+` | 另一条主可播桶 | `mzc002001u873es` / `mzc00200ls5y7z0` | 另一条主可播桶，但不能简单翻译成“花絮/短视频” | 官方后台命名 |
| `downright` | `31` | 形态已确认、语义未知 | `1` | 当前仍缺更干净第 2 样本 | `mzc00200sq680j2` | 已证伪“只在一人之下 第6季”的旧说法，但边界仍不稳 | 更干净的第 2 样本；官方后台命名 |
| `downright` | `41` | 形态已确认、语义未知 | `2` | 当前相对最干净的差异码簇之一 | `mzc002002kqssyu` / `mzc00200dfbfsrw` | 已复现，但还不能命名具体码义 | 官方后台命名 |
| `downright` | `44` | 形态已确认、语义未知 | `2` | 当前主要落在高熵电影样本附近 | `mzc002003r5yq45` / `mzc00200dfbfsrw` | 已不再是单样本，但语义仍待对账 | 官方后台命名 |
| `downright` | `62` | 形态已确认、语义未知 | `5` | 当前已形成跨 4+ cover family，但非单类目专属 | `mzc00383lw807hq` / `mzc003ikavbkqa7` | 已有稳定 family 形态，但电影反例说明它不是窄类目专属 | 官方后台命名 |
| `downright` | `184` | 形态已确认、语义未知 | `2` | 当前最强簇在少儿/纪录片，但已有电影反例 | `mzc002009zwrmx4` / `mzc00200sq680j2` | 不能再写成窄类目专属码 | 官方后台命名 |

## 11. 前端语义层观察

本轮新增前端语义归档：

- [analysis/frontend_semantic_map_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_semantic_map_20260619.json)
- [analysis/frontend_field_consumption_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_field_consumption_20260619.json)
- [analysis/frontend_backend_mismatch_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_backend_mismatch_20260619.json)
- [analysis/frontend_startup_payload_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_payload_probe_20260619.json)
- [analysis/frontend_runtime_store_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_runtime_store_probe_20260619.json)
- [analysis/frontend_dynamic_hook_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_probe_20260619.json)
- [analysis/frontend_dynamic_hook_paystatus_focus_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_paystatus_focus_20260619.json)
- [analysis/frontend_dynamic_hook_branch_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_branch_followup_20260619.json)
- [analysis/frontend_startup_vs_runtime_diff_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_vs_runtime_diff_20260620.json)
  - cross-artifact frontend diff：把当前 tested redirected-detail slice 压成 `startup/SSR -> getPage -> FillUnionInfo` 的字段出现/缺失/改形差分，并补了一轮 detail bundle 命名字串审计
- [analysis/frontend_targetid_runtime_followup_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_runtime_followup_20260620.json)
- [analysis/frontend_targetid_interaction_network_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_interaction_network_20260620.json)
- [analysis/frontend_targetid_semantics_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_semantics_20260620.json)
- [analysis/frontend_targetid_commentinfo_scan_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_commentinfo_scan_20260620.json)
- [analysis/frontend_targetid_report_chain_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_report_chain_20260620.json)
- [analysis/frontend_targetid_synthetic_runtime_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_synthetic_runtime_20260620.json)
- [analysis/frontend_targetid_natural_report_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_natural_report_probe_20260620.json)
- [analysis/frontend_targetid_report_identity_owner_bridge_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_report_identity_owner_bridge_20260620.json)
- [analysis/frontend_positive_trailer_branch_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_positive_trailer_branch_probe_20260620.json)
- [analysis/frontend_true_nondetail_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_true_nondetail_probe_20260620.json)
- [analysis/frontend_row_network_request_capture_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_row_network_request_capture_20260620.json)
  - request-side + response-side followup：把两条最强 redirected-detail 候选在 tab-priority、lazy scroll 条件下再抓一轮，当前仍只看到 `PageService/getPage + FillUnionInfo`

当前最值钱的前端层结论：

1. 页面 SSR 不是纯 HTML 模板，而是会把 API 衍生字段直接塞进：
   - `window.__vikor__context__.ssrPayloads`
   - `coverInfoMap`
   - `videoInfoMap`

2. 前端不会把所有字段原样暴露在当前 `union` store：
   - `positive_trailer`、`type` 会先做值归一化
   - 当前新增的 [analysis/frontend_dynamic_hook_probe_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_probe_20260619.json) 显示：在 2026-06-19 这 4 个 PC Web detail case 里，`JSON.parse` 层仍能看到 raw-like `pay_status` 值，但 first exposed `union.coverInfoMap.pay_status` 已经是 `0`
   - 进一步的 [analysis/frontend_dynamic_hook_paystatus_focus_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_paystatus_focus_20260619.json) 已把这个点压得更实：当前 focused runtime followup 直接在代表页上抓到了 parse-layer raw `6/8/15`，但 exposed `union.coverInfoMap.pay_status` 依然统一是 `0`
   - `publish_date` 会先变成 `publishDate`，再受 `usePublishDate` 之类的前端开关控制
   - `cover_list / c_covers / topic_id_list` 会先合并去重，并指向候选后续请求链；到 2026-06-20 这轮增强 row-network request capture 为止，在两条最强 redirected-detail 候选上加了 request-side + response-side、tab-priority、lazy scroll 之后，当前 tested slice 里仍只抓到 `PageService/getPage + FillUnionInfo`，还没抓到真实 `getCoverInfoBatch` request/response
   - `targetid` 在静态 bundle 里会 reshape 成 `targetId`；到 2026-06-20 为止，动态 hook 已能把非零样本压到 `root.base.commentInfo.targetid` 这类次级 payload。新补的 [analysis/frontend_targetid_semantics_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_semantics_20260620.json) 进一步坐实：`kids_dualfull_targetid` 页里 `root.base.commentInfo` 是稳定容器，非空样本共用 `id/time/seq/scene/platfrom/commentInfo/relation/shareInfo/msgId` 这组 owner 壳层；而 `variety_topic_pay15_targetid` 页虽然也有 `commentInfo` 容器，但当前 probe 里保持空对象

3. 已坐实或基本坐实的逻辑消费：
   - `pay_status` 会被前端读取去做 `report_cover_pay_status / report_vid_pay_status` 上报，并保留相邻的 `pay_status_exchange -> showGive` gating；但当前 detail runtime 暴露出来的 union-store 槽位并不保留 raw API pay_status
   - focused runtime followup 还补了一个关键反例：`pay_status=6` 本身不推出单一前端分支。`movie_single_pay6_exchange_true` 与 `tv_season_pay6_exchange_false` 都先暴露 `cover_pay_status=0`，但 `pay_status_exchange` 一真一假，说明前端更像先塌缩 raw pay_status，再由派生布尔接管分支
   - `state` 会进入 `union` store，随后参与 “未上架 / 已下架 / 已删除 / 不可用 / 不可播” 校验分支
   - `downright` 会直接 gate 下载工具栏按钮态 / 按钮文案
   - `cover_list / c_covers / topic_id_list` 会先被前端合并去重，再指向候选后续请求链；当前 tested redirected-detail slice 仍只确认 merge path，没有抓到真实 `getCoverInfoBatch` request/response
   - `publish_date` 会先被格式化，再受 `usePublishDate` 之类的前端开关控制

4. `positive_trailer` 已确认“先归一化再入状态”，并补到了第一层可见 UI 证据；2026-06-20 这一轮还把证据从“跨页型相关”往“同类对照组分化”再推了一步，但还没到同构因果闭环：
   - [analysis/frontend_dynamic_hook_branch_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_dynamic_hook_branch_followup_20260619.json) 已把 `positive_trailer=0/1/2` 的代表页直接跑进 runtime：`mzc00200nkzol5n` / `mzc002001w361jz` / `mzc002001u873es` / `jynqzy9n3wfrsfp` 的 exposed `cover_positive_trailer` 仍保持 `2/2/0/1`，且 getter 会重复命中
   - 新增的 [analysis/frontend_positive_trailer_branch_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_positive_trailer_branch_probe_20260620.json) 把这条线从“只有 getter 命中”往前推了一步：`positive_trailer=2` 的代表页都稳定出现 `精彩预告` 模块标题，首批卡片都带明确 `预告` badge
   - 新增的 [analysis/frontend_positive_trailer_control_groups_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_positive_trailer_control_groups_20260620.json) 又把它推进到同类对照组层面：在 `type=10 / 综艺` 里，`pt=0` 更靠近 `选集 / SVIP / 纯享` surface，`pt=1` 更像 `看点&花絮 / 直播回顾 / 打包看`，`pt=2` 则直接打出更强的 `预告` badge；`type=106 / 少儿` 里也复现了 `pt=1 -> 精彩片花`、`pt=0 -> 远离片花 tab` 这条差异
   - `type=4 / 体育` 的同类对照组也没有把 `pt=0/1` 压成完全相同的首屏模式，说明 `positive_trailer` 的前端分化并不只停留在综艺 / 少儿两支
   - 但这仍该写成 page-shape-correlated evidence，而不是“同一布局里只改 `positive_trailer` 就会稳定触发该模块”的 strict causal proof；后台枚举正式命名也仍未知

补充观察：`category_map` 当前只保留在观察层：
   - 当前 bundle 里已经看到它和 UA 条件一起参与环境提示分支
   - 但这条还没有升级进本轮 canonical confirmed 集合，不与 `pay_status / state / downright` 同级

5. `targetid`：当前已经从“静态 sink + 部分 runtime 侧证”升级到 `commentInfo-layer + synthetic consumer closure`，但自然 producer 仍待补：
   - 这轮线索先从 runtime getter 命中开始：
     - 在 [analysis/frontend_targetid_runtime_followup_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_runtime_followup_20260620.json) 里，`variety_topic_pay15_targetid_uploadsrc`、`education_coveronly_pay8_targetid_uploadsrc`、`kids_dualfull_targetid` 三个 targetid-heavy 页面都已经抓到 runtime getter 命中；但 sampled exposed `union` 行仍然都是 `video_has_targetid=false`
     - 这轮最有价值的新线索来自 `kids_dualfull_targetid`：非零 `targetid` 不是从主 `union.videoInfoMap` 行里冒出来，而是落在 `root.base.commentInfo.targetid`，且值是 base64-like 字符串，当前可直接解到 `7652145698 / 7651921070 / 7650573812 / 1409064448 ...` 这类 numeric-looking id
     - 新补的 [analysis/frontend_targetid_commentinfo_scan_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_commentinfo_scan_20260620.json) 把这条线从 kids 单点样本升级成了跨页型证据：`tv_season_second / 长安诺_01` 现在稳定打出 `24` 个非空 `root.base.commentInfo.targetid/commentid` 命中，`targetid` 可解到 `5868283771 / 5975589641 / 6061389597 ...`，`commentid` 也能解到 `6709790764822624863 / 6709816745823554421 ...`；`sports_collection_shell / 22/23赛季欧冠1/8决赛次回合视频集锦` 也补出了 `targetid=8149102728` 这一支非 kids 正例
     - 这份批量扫描也同时给了 family boundary：`tv_season_qyn2 / 庆余年第二季_01` 虽然和 `长安诺_01` 同属常规电视剧季页 targetid-heavy 桶，但当前仍是“`commentInfo` 容器存在、内容为空”；`show_perspective_pay15 / 赖美云第一视角` 也同样停在空容器；而 `topic_page_second / 畅游天下·云南篇` 这类 generic topic page 则直接没有扫到 `commentInfo` 容器
     - [analysis/frontend_targetid_interaction_network_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_interaction_network_20260620.json) 进一步说明：把 variety topic 页的客户端弹窗遮罩移掉、强制点进 `讨论 / 热门 / 最新 / 查看更多评论 / 写长文` 之后，前端确实会打出 `barrage` / `doki extra_info` / `community` 邻近请求链，但这轮仍没有抓到带字面 `targetId/targetid` 的 iframe src 或 attachIframe-like handoff
     - 新补的 focused probe 还把 `commentInfo` 邻居关系压清楚了：kids 页同时稳定出现 `pg_dokiid=2100140789`、`relateDoki.dokiId`、`request dokiid=2100140789`、`response ftid=2100140789`，而 `commentInfo.targetid/commentid` 解出的 `7652145698 / 1409064448 / 6770912520198877582 ...` 与这些请求链 id 没有交集
     - `长安诺_01` 这支新的非 kids 正例也延续了这条分离轴：当前扫描里 `pg_dokiid=2100084287`，而 `commentInfo.targetid/commentid` 解出的 `5868283771 / 6709790764822624863 / 6830185840526629004 ...` 仍然明显是另一套 id family；`sports_collection_shell` 当前也只看到 `commentInfo.targetid=8149102728`，而 `relateDoki.dokiId` 解到的是 `2101191593`
     - 新补的 [analysis/frontend_targetid_report_chain_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_report_chain_20260620.json) 又把静态 report 链压清了一层：当前 live `magic-danmaku` bundle 里能看到的 `REQUEST_REPORT` producer 只发 `{id:getDanmakuId(...)}`，紧接着 detail bundle 的 forwarder 也只是把 `a.data` 原样转成 `Bt.DANMAKU_REPORT`；但再下游的 consumer 却在读 `b.data.targetId` 并拼成 `attachIframe(5,{id:b.data.id,targetid:b.data.targetId})`
     - 这意味着当前静态链本身就存在 shape discontinuity：已观察到的 producer/forwarder 没造出 `targetId`，而 sink 在期待它；再结合 popup bundle 的裸字符串拼接规则，如果某次调用真的带着 `targetid: undefined` 进入 `attachIframe(...)`，最终 query 会是字面 `targetid=undefined`
     - 新补的 [analysis/frontend_targetid_synthetic_runtime_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_synthetic_runtime_20260620.json) 把这条链又往前闭了一层：两个代表页都暴露出真实 `Dte` listener instance，直接对它发 `emit("DANMAKU_REPORT", { id: "synthetic_raw_present", targetId: "7652145698" })` 时，最终 popup URL 都稳定落成 `...id=synthetic_raw_present&targetid=7652145698`；而改成 nested payload `emit("DANMAKU_REPORT", { data: { ... } })` 时，又稳定退化成 `...id=undefined&targetid=undefined`
     - 这说明当前最稳的 runtime 解释已经升级成：detail 页真正消费 `DANMAKU_REPORT` 时，listener 边界上确实存在 `.data` 包装，所以**向真实 listener bus 发 raw payload 才是对的**；nested payload 会被再包一层，最终打穿成 `undefined/undefined`
     - [analysis/frontend_targetid_natural_report_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_natural_report_probe_20260620.json) 又把自然路径这侧压成了正式负证据：匿名 PC Web 下，kids / variety 两个代表页虽然都能扫到大量评论区 `举报` DOM（`46` / `35` 个），但这些入口当前都停在 `visibility:hidden` 的隐藏态；采样 hover、程序化 click、以及播放器右键反馈菜单检查，都没有自然产出带非空 `targetid` 的 report popup / iframe / `window.open(...)`
     - 新补的 [analysis/frontend_targetid_report_identity_audit_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_report_identity_audit_20260620.json) 又把这个负证据收紧了一层：在 `kids_dualfull_targetid`、`tv_season_second`、`sports_collection_shell` 这些 `commentInfo.targetid/commentid` 非空页上，匿名评论举报按钮 `dt-params` 暴露的仍是 `feed_id / cp_id / father_feed_id / counters` 这套 id family；它和 `commentInfo.targetid/commentid`、以及当前观察到的 `dokiid/ftid` 讨论链都没有交集，强制显露后点击也仍然没有产出带 `targetid` 的 popup / iframe
     - 紧接着补的 [analysis/frontend_targetid_report_identity_owner_bridge_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_targetid_report_identity_owner_bridge_20260620.json) 再往前推了一步：把匿名评论举报 DOM 周边的 `dataset / __reactProps$* / __reactFiber$* / __vue*` 也浅扫了一轮，当前 owner bridge 仍然只停在 `feed_id / cp_id` 这套身份族，和 `commentInfo.targetid/commentid` 依然不相交
     - 因此当前 `targetid` 的 runtime 结论不该再写成“只有静态 sink + getter hit”，而应写成“`commentInfo-layer + synthetic consumer closure`”：`targetid` 当前更像评论 / 社区侧次级实体 id，这条证据已经稳定跨到 `kids dual-full / 常规电视剧季页 / sports collection shell` 三个不同 family；但同 family sibling 仍可能只给空容器，说明它不是单纯由 backend `targetid` 强阳性自动推出。另一方面，raw `DANMAKU_REPORT` synthetic probe 已经闭合了 `targetId -> popup query targetid` 这段 consumer 映射，而匿名评论举报 DOM 当前看起来更像另一套 `feed_id/cp_id` 身份族。仍未闭合的是：**自然 live producer** 到底谁来提供 `targetId`

6. 已确认进入 startup payload，但当前 tested detail startup / main / runtime slice 里仍没抓到稳定命名消费的字段：
   - `F`
   - `upload_src`
   - 当前电影 / 动漫 / cover-only 代表页的 inline startup script 都已经能看到原始 `F`
   - 当前仍没在 detail 主 bundle、`txv.core.js`、`superplayer-txv.js`、`FillUnionInfo` 主链、dynamic hook 命名 getter，或 sampled runtime `union` store 里定位到干净的命名读取
   - 新增的 focused branch runtime followup 也延续这一点：4 个代表页里 `F` / `upload_src` 仍都是 `0` 次命名 getter 命中，而 `downright` 依然能稳定命中
   - 2026-06-20 的 row-shell followup 继续沿 `问心2` 和 `五哈热点一网打尽` 这两页深挖，但当前 sampled detail runtime slice 里仍只拿到 `cover_nomal_ids_count=0`、`frontend_upload_src_counts={}`、`visible_nomal_f_counts={}` 这类负结果，没补出可见卡片到 `F/upload_src` 的 runtime 映射
   - 同日的 network followup 也继续偏负：后续 document/xhr/script 响应里还能稳定看到 `positive_trailer` / `state`，但这轮仍没抓到 `F` / `upload_src`；而两页初始 document payload 里的 `normal_ids` / `vip_ids` 当时已经是空串
   - 新增的 [analysis/frontend_row_network_request_capture_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_row_network_request_capture_20260620.json) 把这个点再压紧了一层：在 `问心2` / `五哈热点一网打尽` 这两条当前最强 redirected-detail 候选上，把 request-side + response-side、tab-priority、lazy scroll 都加上之后，当前仍只打出 `PageService/getPage + FillUnionInfo`，没有真实 `getCoverInfoBatch` 请求；所以当前更像 deeper shaping / later lazy follow-up 未闭合，而不是 initial capture 太浅
   - 新增的 row-schema probe 又把这条负证据往前闭了一层：它直接把可见卡片标题回勾到 `PageService/getPage` 的行对象。`问心2` 这一支命中的可见卡片 row 还能带 `vid + c_title_detail + positive_trailer + state`，`五哈热点一网打尽` 这一支命中的可见卡片 row 还能带 `vid + title_new + positive_trailer + targetid`，但两支当前都继续不带 `F / upload_src`

这里都不能写成“前端一定不用”，更稳的说法是：当前两条已测代表性 redirected detail 路径的 startup / 主链路 / runtime / row-shell followup slice 里没有直接暴露或消费，而且当前已测 visible-card `getPage` row schema 也继续不带它们；如果后面还有消费，更像在可见 row schema 之前的隐藏整形层、真正触发出来的 `getCoverInfoBatch` 后续请求链、更早的 SSR / vector-layout shaping，或者别的 non-detail 路径里才会读。

2026-06-20 又补了一轮 non-detail-targeted chain probe，输入页选的是：

- `mzc002001u873es / 战至巅峰之赛事全局看`
- `mzc002003fh665c / 22/23赛季欧冠1/8决赛次回合视频集锦`
- `mzc00200q00mv2h / 暑期作战大联盟，全员待命去冒险！`

这轮新增的高信号结论：

- 这 3 个 cover-like 输入 URL 最终都还是跳进了 video detail final URL，所以当前还没真正打到“完全不重定向的 non-detail frontend family”
- 但 kids free pack 这支已经把更深一层的 `pc_sv_mixed_feeds` 和大 `c_covers / cover_list` 合并链打出来了
- 即便如此，这轮 `PageService/getPage` 与 `FillUnionInfo` 里仍然只稳定看到 `positive_trailer / state / cover_list / c_covers / topic_id_list`，没有补出 `F / upload_src`
- 这说明下一跳更该追的是：
  - `getPage` 响应后的 tagged shaping
  - 真正能触发 `getCoverInfoBatch` 的路径
  - 或者压根不是浏览器端，而是 SSR / vector-layout 提前把 `F / upload_src` 吃掉了

同日又把 stronger non-detail 候选往前推了一步，新增的 [analysis/frontend_true_nondetail_probe_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_true_nondetail_probe_20260620.json) 这轮改成了：

- `mzc00200bhj36oq / 小学自然科学`（教育 cover-only 候选）
- `mzc00200nkzol5n / 合成令`（电视剧专题壳）
- `mzc00200apbfiqs / 畅游天下·云南篇`（纪录片专题壳）

这轮最值钱的新结论是：

- 这 3 个 stronger 候选最终也都还是跳进了 detail final URL，所以“更像聚合壳”不等于“前端 runtime 一定留在 non-detail family”
- refined probe 已把 request-side 和 response-side 拆开，当前 request-side 只稳定打到 `PageService/getPage` 与 `FillUnionInfo`
- `getCoverInfoBatch` 这次终于被更干净地区分成“bundle code reference 存在”，而不是“真实请求已经触发”；实际 request/response 里仍没看到 `getCoverInfoBatch`
- `mzc00200bhj36oq` 这条教育 cover-only 候选还顺手补硬了一点：`FillUnionInfo.video_infos[e3075bgqeto]` 里能看到 `c_covers / cover_list / state / type_name=教育 / type=27`，但仍然没有 `F / upload_src`

紧接着补的 [analysis/frontend_startup_vs_runtime_diff_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/frontend_startup_vs_runtime_diff_20260620.json) 又把这一层压得更细：

- 它不是假装 same-run end-to-end 的“闭环图”，而是明确标注为 cross-artifact diff
- `education cover-only / 电视剧专题壳 / 纪录片专题壳` 这 3 条当前都落成同一条 tested redirected-detail slice：`positive_trailer` 能进 sampled `getPage`，`state` 会在 `FillUnionInfo` 补回来，`cover_list / c_covers / topic_id_list` 会在 runtime 邻近层出现
- `F` 当前最稳的说法已经收敛成“startup/SSR 可见，但 sampled `getPage / FillUnionInfo` 不见”；`upload_src` 当前最稳的说法已经收敛成“startup/SSR、sampled `getPage / FillUnionInfo`、以及 tested detail bundle 命名字串层都没命中”
- 所以这一步补强的是 tested redirected-detail slice 的前端语义边界，而不是“前端全局一定不用 `F/upload_src`”

前后端差异审计摘要：

| API 原值 / 形态 | 前端形态 | 当前判断 |
| --- | --- | --- |
| `pay_status=6/8/15...` | 在 2026-06-19 这 4 个 PC Web detail case 里，sampled `union.coverInfoMap` first slot 统一是 `pay_status=0`，而 dynamic hook 的 `JSON.parse` 层仍能见到 `0/6/8/15`；`pay_status_exchange / show_gift` 仍保留相邻 gating 信息 | 当前暴露出来的 union store 槽位不是 raw pay_status 直通；remap/defaulting/shaping 的确切发生点仍待补证据 |
| `positive_trailer=0/1/2` | 先经归一化函数，再写进 cover info state；focused branch runtime followup 已直接覆盖 `0/1/2`，且 exposed `union` 行仍保持这些归一化值。2026-06-20 visible probe 又补到第一层 module/card pattern：`2` 更常落在 `精彩预告` / `预告` badge，`1` 当前 kids 代表页落在 `精彩片花` tab，`0` 当前综艺专题代表页落在 `选集` / `SVIP` / `纯享` surface | 当前更像类型层 remap，不是语义重命名；可见模块模式已经出现，但仍不是 same-layout causal proof |
| `publish_date` | 变成 `publishDate`，再受 `usePublishDate` 类前端开关控制 | 前端可以主动隐藏后端日期 |
| `cover_list` + `c_covers` + `topic_id_list` | 先合并去重，并指向后续 `getCoverInfoBatch` 邻近链路；当前 tested slice 只确认 merge path 与 bundle code reference，尚未抓到真实 `getCoverInfoBatch` request/response | 前端不会原样消费后端返回形态，但后续请求链仍未完全闭合 |
| `targetid` | 静态 sink 侧使用 camelCase `targetId`；2026-06-20 followup 已把非零 targetid 进一步压到 `root.base.commentInfo.targetid`，且这条 evidence 现在已跨出 kids：`长安诺_01` 稳定打出多组 base64-like `targetid/commentid -> numeric id`，`sports_collection_shell` 也补出了 `targetid=8149102728`；但 `庆余年第二季_01`、`赖美云第一视角` 这类 sibling 仍可能只有空 `commentInfo` 容器。当前 live `magic-danmaku` REPORT-click producer 只静态发出 `{id}`，未见 `targetId / targetid / commentid`；但 synthetic runtime probe 已证明：对真实 `Dte` listener 发 raw `DANMAKU_REPORT` payload 时，`targetId` 会稳定映射进 popup `targetid=` query，而 nested payload 会退化成 `id=undefined&targetid=undefined`。新补的 report-identity audit 还说明：匿名评论举报 DOM 的 `dt-params` 当前暴露的是 `feed_id/cp_id` 这套身份族，它与 `commentInfo.targetid/commentid` 以及 `dokiid/ftid` 都不相交 | 字段当前更像 survives 到 comment/community 邻近 payload，而不是 detail 主 `union.videoInfoMap` 直出；commentInfo-layer 证据已跨多个 page-shape family，但自然 producer 仍待补 |
| `upload_src` | 当前未在已测 startup payload / 主 bundle / `FillUnionInfo` 主链、dynamic hook 命名 getter，或 sampled runtime `union` store 里命中命名读取；focused branch runtime followup 仍是 `0` 次命名 getter 命中；2026-06-20 row-shell / network followup 也还没补出正例；新增的 row-schema probe 还说明当前 visible-card `getPage` row schema 也不带它；同日 stronger non-detail 候选 probe 仍只打到 `getPage + FillUnionInfo`，没有真实 `getCoverInfoBatch` 请求 | 不能下结论说“前端不用”，只能说当前 tested detail startup / 主链 / runtime / row-shell followup / visible-card row-schema slice 未直接观察到；如果有消费，更像在更早的 tagged shaping、SSR / vector-layout，或尚未触发出来的后续请求链 |
| `F` | 当前已能在 startup payload 里看到原始值，但还没在主 bundle / `FillUnionInfo` 主链、dynamic hook 命名 getter，或 sampled runtime `union` store 里命中命名读取；focused branch runtime followup 仍是 `0` 次命名 getter 命中；2026-06-20 row-shell / network followup 也还没补出正例；新增 stronger non-detail 候选 probe 里，`getCoverInfoBatch` 这次只以 bundle code reference 形式出现 | 字段 survives into frontend startup，但 semantic consumption 仍待补证据；当前 tested detail + row-shell followup 更偏向负证据，而不是 row-shell 已消费，并且它还可能在 visible-card row-schema 之前就已被抹平 |

## 12. 环境维度适用范围

本轮新增环境矩阵归档：

- [analysis/environment_matrix_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_20260619.json)
- [analysis/environment_matrix_browserlike_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_browserlike_20260619.json)
- [analysis/api2_jsonp_batch_matrix_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_batch_matrix_20260620.json)
- [analysis/agent_api_contract_crossday_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/agent_api_contract_crossday_20260620.json)
- [analysis/environment_crossday_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_crossday_summary_20260620.json)
- [analysis/environment_field_drift_crossday_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_field_drift_crossday_20260620.json)
- [analysis/environment_page_shape_extension_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_extension_20260619.json)
- [analysis/environment_page_shape_kids_retest_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_kids_retest_20260619.json)
- [analysis/environment_page_shape_sports_kids_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_sports_kids_followup_20260619.json)
- [analysis/environment_page_shape_crossday_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_crossday_20260620.json)
- [analysis/agent_sports_kids_crossday_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/agent_sports_kids_crossday_summary_20260620.json)
- [analysis/environment_page_shape_targeted_all_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_targeted_all_20260619.json)
- [analysis/gap_ledger_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/gap_ledger_20260619.json)
- [analysis/gap_ledger_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/gap_ledger_20260620.json)
- [analysis/sports_candidate_mzc0020069a6anp_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/sports_candidate_mzc0020069a6anp_20260619.json)
- [analysis/sports_replay_candidate_mzc0020086fhhzs_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/sports_replay_candidate_mzc0020086fhhzs_20260619.json)
- [analysis/sports_replay_candidate_mzc00200k9sp5r2_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/sports_replay_candidate_mzc00200k9sp5r2_20260619.json)
- [analysis/targeted_page_shape_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/targeted_page_shape_followup_20260619.json)
- [analysis/search_replay_hunt_round2_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/search_replay_hunt_round2_20260619.json)
- [analysis/state8_positive_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/state8_positive_environment_20260620.json)
- [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json)
  - `upload_src=2048` 环境矩阵摘要：`2` 个 pure `2048` 正例、`1` 个 mixed `2048/108` cover、`1` 个 same-type pure-0 negative 在 `8` 个请求环境下都无漂移

同日 followup 里先补了 4 个 base-4 稳定样本，到 `2026-06-20` 这 4 个又继续补到 cross-day 稳定：

- `sports_provisional_followup = mzc002003fh665c`
- `kids_hybrid_seed = jynqzy9n3wfrsfp`
- `kids_hybrid_pack = bzfkv5se8qaqel2`
- `kids_hybrid_trip = mzc00200yokeal4`

它们在 [analysis/environment_page_shape_sports_kids_followup_20260619.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_page_shape_sports_kids_followup_20260619.json) 里先保持 `unique_signature_count=1`，随后又在 [analysis/agent_sports_kids_crossday_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/agent_sports_kids_crossday_summary_20260620.json) 里继续保持 `cross_day_same=true`，所以当前新增的 sports collection shell clean representative 与 kids hybrid 邻近样本，已经补到 base-4 cross-day 稳定。

而 `state=8` 这条线也补上了此前明确缺的一块：新加的 [analysis/state8_positive_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/state8_positive_environment_20260620.json) 已把 `482396nuyaelv0e` 与 `mzc002006tgfqvp` 这两个正 family 补到 `8` 个请求环境 same-day 稳定，且 `state/upload_src` 分布与 `2026-06-19` 一致。这个证据可以收紧“state=8 是行级 small-family signal”的环境适用范围，但仍不能把它升级成页型桶。

同轮的 [analysis/upload_src_2048_environment_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/upload_src_2048_environment_20260620.json) 也把 `upload_src=2048` 的 tested core set 补到了 `8` 环境 same-day 稳定：`2` 个 pure `2048` 正例、`1` 个 mixed `2048/108` cover、`1` 个 same-type pure-0 negative 都没有出现环境漂移。这个闭环收紧的是当前 tested core set 的环境稳定性，不是把整条 family 升级成“已跨出 type=111”。

当前最稳的环境层结论：

1. 已实测基础环境：
   - `PC Web UA`
   - `Mobile H5 UA`
   - `最小请求头`
   - `Referer + Origin`

2. 已实测扩展环境：
   - `pc_web_browser_like`
   - `pc_web_browser_like_cookie`
   - `mobile_h5_browser_like`
   - `mobile_h5_browser_like_cookie`
   - 其中 `cookie` 目前只是 synthetic placeholder，用来回答“Cookie 头存在是否触发分支”，**不是**真实登录态 / 老化会话复测
   - `mobile_h5_browser_like*` 当前更适合当 exploratory side evidence；closure-grade 解释优先看 desktop browser-like 两个环境

3. 当前没打出环境分叉的结论：
   - 在 `2026-06-19` same-day 与 `2026-06-20` cross-day retest 里，API1 / API2 的已测契约 case 都没有稳定分叉；contract 层当前已经补到 8 环境跨日稳定
   - API1 / API2 的 `tid`、`appid`、`appkey` 契约
   - 单个 `otype` key 时，API2 只有精确小写 `otype=json` 会切 JSONP；`otype=JSON` 会回落到 XML；若 `otype` 重复，当前 tested branch 由首值决定外壳
   - API2 JSONP canonical branch 下，`callback=1 / cb1 / QZOutputJson / foo.bar / a-b / a[b] / $cb / foo bar / foo,bar / [0] / 中文 / a) / ) / a;b / a'b / a"b / a/ / a\ / //a / /*a / [ / [[` 都会把默认 `QZOutputJson=...;` 外壳改写成 callback-style 包裹；空 `callback=` 会回落默认壳；`callback=a(` / `callback=((` / `callback=})();` 以及后续补到的 `callback=[(` / `callback={(` / `callback=/*(` / `callback=a[(` / `callback=)(` / `callback=](` / `callback=}(` 当前都会打成摘要路径不可解析的坏壳；`_` 当前未观察到变化；这仍只是 practical value-space 结论，不外推成完整 callback 语法闭环
   - API2 `union_platform` 当前在匿名 canonical tested branches 与真实匿名 visitor cookie replay 下都未观察到可见行为差异
   - API1 / API2 的 `32/33` 非空 item 边界，当前都按单个 `idlist` key 内的非空 CSV item 计数
   - mixed valid+invalid / duplicate / empty-slot / 32/33 的批量行为（包括新补的 JSONP mirror cases），当前都建立在单个 `idlist` key 的 CSV 语义上
   - API2 全坏 VID 的 JSONP 批量，当前仍可能是顶层 `errorno=0` + 逐项 `retcode=0`，只能靠空壳字段识别
   - `film_single / anime_season / variety_topic / sports_replay / kids_free_pack` 这 5 个 canonical representative field-drift 页面，在 8 种已测环境里先完成 same-day 稳定，随后又在 [analysis/environment_field_drift_crossday_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_field_drift_crossday_20260620.json) 里补到 8 环境 cross-day 稳定
   - `film_single_second / anime_season_second / tv_season_second / variety_season_second / kids_regular_season / kids_free_pack_second / topic_page_second` 当前都已经补到基础 4 环境跨日稳定
   - `sports_provisional_followup / kids_hybrid_seed / kids_hybrid_pack / kids_hybrid_trip` 也都已经补到基础 4 环境跨日稳定
   - 后续 targeted followup 又补出 4 个稳定 second-rep / sports-shell followup：
     - `variety_viewangle_second = mzc0020081c19hy / z0047w712qa`
     - `sports_info_second = mzc003t8r55x4z7 / c3183jvmmo8`
     - `sports_feature_doc = mzc00200ti1wj2i / h4102basruv`
     - `sports_replay_second = mzc00200k9sp5r2 / q4101u7frq2`
   - 其中 `sports_replay_second` 的形态与首代表同向：`publish_date=22/22`、`targetid=0/22`、`upload_src` 以 `31` 为主

4. 当前还不能写成“全局稳定”的部分：
   - 尚未覆盖所有 page-shape bucket / second representative / `aged-cookie` / `login-state` 环境的跨日复测
   - `aged-cookie` / 登录态环境
   - `type=4 / 体育` 又新增了一条 provisional `体育比赛集锦 / 合集壳页` 分支，说明体育页型拆桶还没彻底收口
   - `type=4 / 体育` 的 `人物 / 资讯壳 / 赛事纪录片 / 比赛集锦壳` 这些子支虽然都已有样本，但边界命名还没完全定死

## 13. 参数闭环交付物

如果当前关注点是“把接口能力直接用起来”，而不是继续扩字段语义，这几份调用者主工件最值得先看：

这里也先把口径说清楚：这些 canonical 总表的文件名多数仍停在 `20260620`，但参数总表、能力面、配方表、回归样本，以及新增的两张调用者 join 总表，已经刷新到 `2026-06-21` 的证据口径；同一节下面再挂增量摘要，主要是为了把边界与环境尾项单独说清楚。

- [analysis/api_param_inventory_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api_param_inventory_20260620.json)
  - API1 / API2 参数总表：已知参数全集、硬约束、条件分支、边界和未闭合项
- [analysis/direct_call_parameter_total_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_parameter_total_table_20260621.json)
  - 调用者参数总表增强版：把“推荐填法 / 成功判据 / 重复 key 语义 / 32/33 计数规则 / 已证实环境 / 未证实环境”压成一张更适合 SDK 和脚本作者直接照着用的总表
- [analysis/parameter_capability_index_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/parameter_capability_index_20260621.json)
  - 统一参数索引：把显式参数、候选参数、replay/tooling 参数，与能力配方、回归样本、关键证据串成一张机器可读入口
- [analysis/capability_surface_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_surface_20260620.json)
  - 当前可直接调用的能力面：单条/批量、XML/JSONP、32/33 边界、环境适用范围
- [analysis/capability_recipes_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/capability_recipes_20260620.json)
  - 能力配方表：按“能力 -> 参数 -> curl / Python / Go 入口 -> 预期返回亮点”组织
- [analysis/direct_call_capability_table_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_capability_table_20260621.json)
  - 调用者能力总表增强版：按“一行一个可调用能力面”串起 `use_when / 参数层级 / 成功规则 / 风险边界 / live 验证状态 / 回归样本`
- [analysis/direct_call_delivery_manifest_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_delivery_manifest_20260621.json)
  - 交付总入口：按调用者 / SDK 作者 / 研究者三类入口，把参数总表、能力配方、示例、回归样本和剩余闭环缺口串成一张清单
- [analysis/regression_samples_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/regression_samples_20260620.json)
  - 参数闭环回归样本：baseline、mixed、duplicate、`dup32`、`dup33`、JSONP 镜像
- [analysis/param_gap_priority_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_gap_priority_20260620.json)
  - 当前只按“参数闭环”排序的 gap 台账，已经把 `pay_status / upload_src / F / targetid` 这类旁线问题降级出主链
- [analysis/callback_tail_values.txt](C:/Users/lin/Documents/YM查询工具还原/analysis/callback_tail_values.txt)
  - replay bundle 的 callback pathological-tail 输入样例文件：一行一个已实测值，可直接配合 `--probe-extra-callback-file` 使用
- [examples/environment/pc_aged_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_aged_cookie_header.template.txt)
  - aged-cookie replay 的最小输入模板：给 `tencent_cookie_env_from_headers.py` 或 `tencent_replay_bundle_runner.py` 的 `--desktop-cookie-file` 使用
- [examples/environment/pc_login_cookie_header.template.txt](C:/Users/lin/Documents/YM查询工具还原/examples/environment/pc_login_cookie_header.template.txt)
  - login-state replay 的最小输入模板：给 `tencent_cookie_env_from_headers.py` 或 `tencent_replay_bundle_runner.py` 的 `--desktop-cookie-file` 使用
- [analysis/param_query_semantics_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/param_query_semantics_20260620.json)
  - extra key / repeated key 语义归档：当前 canonical tested branches 下，API1 `tid/idlist` 与 API2 `tid/idlist/otype` 的 repeated key 已补到首值生效，`union_platform` 仍只到“当前未观察到变化”
- [analysis/api2_all_invalid_jsonp_consumer_rule_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_all_invalid_jsonp_consumer_rule_20260620.json)
  - API2 全坏 JSONP 批量的统一调用方识别规则：`top-level success + 全部 empty_shell=true` 应视为整批无效
- [analysis/api2_jsonp_callback_value_space_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_value_space_20260620.json)
  - API2 JSONP callback 第二层 practical value-space：宽字符族 raw passthrough + 空 callback fallback
- [analysis/api2_jsonp_callback_contract_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_20260621.json)
  - API2 JSONP callback precedence / error-shell 最小契约组：repeated `callback` 在当前匿名 collision cases 下表现为首值生效，wrong-appkey JSONP 错误壳也仍然吃 `callback` wrapper 改写
- [analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_jsonp_callback_contract_real_cookie_summary_20260621.json)
  - 同一组 callback precedence / wrong-appkey error-shell case 在真实匿名 visitor-cookie replay 的 PC Web / Mobile H5 上都未观察到分叉
- [analysis/reserved_extra_key_sweep_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/reserved_extra_key_sweep_20260620.json)
  - 第一轮 reserved-looking extra key sweep：`format / output / version / v / platform / source` 在当前匿名 canonical branches 下都未见作用
- [analysis/authish_extra_key_sweep_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/authish_extra_key_sweep_20260620.json)
  - 第一轮 auth-ish extra key sweep：`token / sign / sig / appver / access_token / authkey / openid` 在当前匿名 canonical branches 下都未见作用
- [analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/authish_extra_key_replay_anonymous_real_cookie_summary_20260621.json)
  - 真实匿名 visitor cookie replay 对比摘要：已测 auth-ish extra keys、repeated `union_platform`、repeated `otype`、空 callback fallback、以及一个已知 parse-breaking callback 壳都未相对匿名 baseline 出现新分叉
- [analysis/positive_tid_summary_20260620.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_summary_20260620.json)
  - focused 高信号带宽摘要：先确认 API1 `431`、API2 `535 / 540`，并把 API1 `537` 单独落成 success-shell-without-sample
- [analysis/positive_tid_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_summary_20260621.json)
  - 更宽扩圈摘要：API2 `541` 已补成新正向分支，并用第二个样本复核通过；`542-550` 当前回落为标准错误带
- [analysis/positive_tid_probe_446_455_summary_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_446_455_summary_20260623.json)
  - 新增 `446-455` follow-up 摘要：API1 `453` 已补成 3-CID confirmed 的 positive cover-shell-only 分支，而 API2 `453` 仍稳定在 `key all illegal`
- [analysis/positive_tid_probe_456_521_summary_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_456_521_summary_20260623.json)
  - 新增 `456-521` 中间主走廊摘要：API1 `476/506` 已补成更薄的 success-shell family，`483` 已补成 video_ids-only shell，API2 `488/502` 已补成新的稳定正分支，`506` 当前更像 success shell
- [analysis/api1_tid_shell_family_delta_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api1_tid_shell_family_delta_20260623.json)
  - API1 壳层差异摘要：把 `431/453/476/483/506/537` 统一压回“caller-facing 能力厚度”视角，避免把新的 success-shell family 误写成 recipe
- [analysis/api2_extended_tid_capability_delta_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_extended_tid_capability_delta_20260623.json)
  - API2 扩展壳层差异摘要：`488/502` 已纳入 alternate-positive family，`502` 当前明显比 `488/540/541` 更厚，但仍不等同 canonical `535`；`506` 继续保守读成 near-empty success shell
- [analysis/demo_validation_incremental_api2_tid488_502_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_api2_tid488_502_20260623.json)
  - API2 `488/502` 的 Python / Go 增量 live validation：`488` 当前稳定是 title+url 的更薄正壳，`502` 当前稳定是带 `vid + duration + cover_list + create_time` 的较厚 alternate shell
- [analysis/direct_call_raw_http_validation_api2_tid488_502_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_api2_tid488_502_20260623.json)
  - API2 `488/502` 的 caller-facing raw HTTP 增量 validation：把这两条 alternate shell 直接按原生 HTTP 坐实到可回归层
- [analysis/positive_tid_probe_524_529_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_524_529_summary_20260621.json)
  - `524-529` 窄带补测摘要：没有新增正分支；`525` 在第二、第三样本里都稳定落到 `-111013`，其余点仍是标准 `-111005`
- [analysis/positive_tid_api1_boundary_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_api1_boundary_summary_20260621.json)
  - API1 新补 `418-421` 与 `526-536` 两段后，边界解释更清楚：`419->420`、`529->530->531`、`534->535->536` 都是错误族切换，不构成新的正分支；其中 `535` 已在第二个 CID 上复现为稳定局部边界
- [analysis/positive_tid_probe_641_647_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_641_647_summary_20260621.json)
  - 匿名 `641-647` jump-scan 已补完：没有扫出新正簇；第二、第三个 sample 里 `642` 都额外落到 `-111013`，所以当前不支持早先那条 `+106` 偏移正簇猜想，但这段在错误侧存在稳定局部异质性
- [analysis/positive_tid_probe_636_640_648_652_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_636_640_648_652_20260622.json)
  - 围绕 `642` 两侧补了 `636-640` 和 `648-652`：API1、API2 XML、API2 JSONP 全部回到标准 `-111005`；这进一步支持 `642` 当前更像局部异常岛，而不是更大正簇或更宽 `-111013` 家族的边缘
- [analysis/positive_tid_probe_522_525_summary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/positive_tid_probe_522_525_summary_20260622.json)
  - 新补的 cross-interface lower-edge follow-up 说明：`522-524` 在 API1、API2 XML、API2 JSONP 上都稳定是标准 `-111005`，而 `525` 在两组 public sample 里同步是 `-111013`；这把 `525` 从 API2-only anomaly 升级成了跨接口局部错误岛，而不是新正簇前兆
- [analysis/demo_validation_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_20260621.json)
  - Python / Go live demo 验证摘要：canonical `535` 默认链路与 JSONP callback override 都已跑通；`tid=541` 在 live demo 上也能回正壳，但字段不一定和 `535` 一样丰满
- [analysis/direct_call_raw_http_validation_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_20260621.json)
  - caller-facing raw HTTP live validation 摘要：canonical XML / JSONP、alternate positive tid、`541 + union_platform=0003`、API1 direct batch、以及 all-invalid JSONP consumer rule 都已经按原生 HTTP 直调重跑；这仍只覆盖匿名 direct-call scope，batch 行当前读作 canonical multi-VID spot-check，不外推成新的 `32/33` 饱和边界实验
- [analysis/direct_call_raw_http_validation_tid453_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/direct_call_raw_http_validation_tid453_20260623.json)
  - API1 `tid=453` 独立 raw validation：当前 3-CID confirmed 的 positive cover-shell-only 分支已经补到 caller-facing 直调证据层，结果仍是 non-empty cover shell + empty `video_ids`
- [analysis/api2_alt_tid_capability_delta_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/api2_alt_tid_capability_delta_20260621.json)
  - `535/540/541` 能力差异摘要：当前更稳的说法是它们属于同一正分支 family，但 `540/541` 都只坐实为 alternate positive shell，不应默认等同于 canonical `535` 的字段丰满度
- [analysis/tid_richness_matrix_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tid_richness_matrix_20260622.json)
  - `431/453/537` 与 `535/540/541` 的多样本字段丰度矩阵：`453` 在 3 个 public CID 上稳定是 non-empty cover shell + empty `video_ids` 的 positive cover-shell-only 分支；`537` 在 3 个 public CID 上都还是 sample-less success shell；`540` 在 3 个 public VID 上稳定是 score-3 薄正壳；`541` 在 3 个 public VID 上稳定是 score-2 更薄正壳
- [analysis/tid_richness_matrix_extended_20260623.json](C:/Users/lin/Documents/YM查询工具还原/analysis/tid_richness_matrix_extended_20260623.json)
  - 扩展多样本字段丰度矩阵：把 API1 `431/453/476/483/506/537` 与 API2 `488/502/506/535/540/541` 都放进统一 demo 视角，便于直接对比壳层厚度
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
- [analysis/demo_validation_incremental_20260621d.json](C:/Users/lin/Documents/YM查询工具还原/analysis/demo_validation_incremental_20260621d.json)
  - 新增 live 验证补丁：把 Python/Go 的 URL 入口、`api2-batch-size`、以及 `api2-union-platform` 显式 override 路径补成正式证据；这仍只覆盖匿名 direct-call scope，不外推到 `aged-cookie / login-state`
- [analysis/objective_coverage_audit_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/objective_coverage_audit_20260621.json)
  - 目标覆盖审计：把最终目标拆成参数总表 / 能力配方 / Python/Go 示例 / 回归样本 / 候选参数 / 环境闭环等交付项，明确哪些已覆盖，哪些仍只部分覆盖
- [analysis/anonymous_real_cookie_env_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/anonymous_real_cookie_env_20260621.json)
  - 真实匿名 visitor cookie replay 输入：由真实页面浏览态导出的 `--extra-env-json`
- [analysis/environment_matrix_anonymous_real_cookie_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_anonymous_real_cookie_20260621.json)
  - 真实匿名 visitor cookie replay 矩阵：在原 8 环境基础上新增 `pc_web_real_cookie_replay / mobile_h5_real_cookie_replay`
- [analysis/environment_matrix_anonymous_real_cookie_summary_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_matrix_anonymous_real_cookie_summary_20260621.json)
  - 结论摘要：当前 API1/API2 契约层未因真实匿名 cookie 产生新的参数分叉，剩余高价值 gap 转向 aged-cookie / login-state
- [analysis/replay_bundle_real_summary_20260621_realcheck.json](C:/Users/lin/Documents/YM查询工具还原/analysis/replay_bundle_real_summary_20260621_realcheck.json)
  - replay bundle 总入口自测：已用现成真实匿名 replay 环境端到端跑通 `env_json -> environment_matrix -> authish semantics`，说明最后一公里工具链本身已通
- [analysis/replay_bundle_semantics_callback_support_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/replay_bundle_semantics_callback_support_20260621.json)
  - replay bundle 参数扩展自测：`--semantics-profile full`、`--probe-extra-callback-value`、`--probe-extra-callback-file` 已接进总入口，后续 aged/login replay 可以直接把 callback pathological-tail 一起带进去
- [analysis/replay_bundle_artifact_dir_selfcheck_20260621.json](C:/Users/lin/Documents/YM查询工具还原/analysis/replay_bundle_artifact_dir_selfcheck_20260621.json)
  - replay bundle 输出路径自测：`--artifact-output-dir / --subprocess-output-dir` 已证明可在受限本地环境下完整跑通，`status=ok`，两份 semantics 子步骤都已 `returncode=0`
- [analysis/environment_replay_runner_contract_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_runner_contract_20260622.json)
  - replay bundle 契约表：把 `tencent_replay_bundle_runner.py` 的 CLI、phase sequence、status 枚举、summary schema、skip 语义压成机器可读 contract
- [analysis/environment_replay_input_boundary_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_input_boundary_20260622.json)
  - replay 输入边界：明确 `desktop cookie required, mobile optional`，并把 env-builder 的 mode/key 映射和最小输入模型压成机器表
- [analysis/environment_replay_hard_block_table_20260622.json](C:/Users/lin/Documents/YM查询工具还原/analysis/environment_replay_hard_block_table_20260622.json)
  - replay hard-block 边界：把 `union_platform / auth-ish extra keys / 540/541 shell thickness` 这些当前只能保留在 scoped-negative 范围的项单独列出来

当前最稳的交付视角总结：

1. API1 当前已知 query key 只有 `tid / idlist / appid / appkey`
2. API2 当前主 fetch key 集是 `otype / tid / appid / appkey / union_platform / idlist`；另有 JSONP-only auxiliary key `callback`
3. API1 / API2 的 `32/33` 非空 item 边界都已有仓库证据，但当前证据口径是单个 `idlist` key 内的非空 CSV item
4. API2 单个 `otype` key 为精确小写 `json` 时会切 JSONP；如果 `otype` 重复，当前 tested branch 由首值决定外壳
5. 当前 canonical tested branches 下，API1 `tid/idlist` 与 API2 `tid/idlist/otype` 的 repeated key 已补到首值生效；API1 / API2 的 repeated `appid/appkey` 目前则只在已测 collision branches 下补到首值生效。已测 extra key 里，API1 `foo/callback/_`、API2 XML `foo/callback/_`、API2 JSONP `foo/_`、以及 `format / output / version / v / platform / source` 当前都未见作用；而 API2 JSONP 的 `callback` 第二层 practical value-space 也已经补到：当前已测宽字符族会改写 wrapper 前缀但不改 payload 家族，空 `callback=` 会回落默认壳。`union_platform` 当前最稳的说法只到：在匿名 canonical branches 与真实匿名 visitor cookie replay 下未观察到可见差异；这还没有覆盖 `aged-cookie / login-state`，也不证明它对所有 tid/sample 全局无作用。
6. 当前 API1 已确认 3 条不同厚度的 `tid` 分支：`431` 仍是 canonical positive branch；`453` 到 `2026-06-23` 为止已在 3 个 public CID 上稳定复现成 non-empty cover shell + empty `video_ids` 的 positive cover-shell-only 分支；`537` 则已在 3 个 public CID 上重复成 success-shell-without-sample 分支。后两者都不默认等同 canonical `431` 的字段丰满度。
7. 当前真实匿名 visitor cookie replay 与同日匿名扩圈合并后，API2 已确认的 positive tid family 已不止 `535 / 540 / 541`，还包括中间主走廊里新补出的 `488 / 502`，以及当前更适合保守读取为 success shell 的 `506`。但“family 确认”只指正向返回族，不等于字段丰满度已经等价：到 `2026-06-23` 为止，`488` 在 3 个 public VID 上更稳地表现为 `title + url + pic` 薄正壳，`502` 在 3 个 public VID 上更稳地表现为 `title + url + duration + type + vid + cover_list` 的更厚 alternate positive shell，`540` 在 3 个 public VID 上更稳地表现为 `title + duration + url` 的 score-3 薄正壳，`541` 在 3 个 public VID 上更稳地表现为 `title + url` 的 score-2 更薄正壳；它们都不默认等同 canonical `535` 的字段丰满度。对已测 auth-ish extra key（`token / sign / sig / appver / access_token / authkey / openid`）也只是在已测 tid anchor 与已测样本上，未观察到相对匿名 baseline 的可见分叉，这条负结论不能外推成“所有 auth-ish key / 所有会话态都无作用”。
   到 `2026-06-22` 为止，这 3 类边界（`union_platform`、`auth-ish extra keys`、`540/541 environment shell thickness`）都已经被单独列进 hard-block 表，统一按 `scoped-negative` 管理。
8. 当前最高 ROI 的剩余参数 gap，不是继续追字段语义，而是：
   - `login-state / aged-cookie` 环境
   - API1 其他 positive `tid`，以及 API2 是否还存在当前已确认 `488 / 502 / 535 / 540 / 541` family 之外的稀疏新簇
   - API2 JSONP `callback` 的更激进 unmatched-delimiter / pathological parse-breaking 探针
   - auth-leaning extra key 在 `aged-cookie / login-state` replay 下的分支差异
   - 到 `2026-06-22` 为止，caller-selected `636-640 / 648-652` 补测也仍全部回到 `-111005`，所以当前更稳的口径仍是“已确认正向小簇 = `535 / 540 / 541`；其外侧若干邻近 tid 继续是错误带”，而不是“535 之外已经没有新正支”
   - 也就是说，下一跳仍是 `aged-cookie / login-state` replay，而不是继续在真实匿名 visitor cookie 上重复扫同一组 auth-ish key
