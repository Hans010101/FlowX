# 引擎接口清单（ENGINE_API）

> 给 Claude Code 的地图：现有引擎已实现的可复用函数、输入输出、配置与环境变量。
> **产品化时直接调用这些，不要重写。** 界面层/接口层（FastAPI）只需编排这些函数。
> 规范示例见项目根目录 `run_daily.py`（整条流水线的现成串法）。

---

## 0. 数据结构（贯穿全流程）

```python
# hotspot/fetch.py
@dataclass
class HotItem:
    title: str            # 热点标题
    source: str           # 来源：baidu / toutiao
    url: str | None       # 报道链接（抓配图用）

# publishers/base.py
@dataclass
class Article:
    title: str            # 文章标题（≤30字）
    content: str          # 正文（纯文本，段落用\n分隔）
    cover_image: str | None = None   # 本地图片路径
    tags: list = []

@dataclass
class PublishResult:
    ok: bool              # 是否成功
    platform: str         # toutiao
    account: str          # 账号名
    as_draft: bool        # 是否存草稿（当前恒为发布）
    url: str | None       # 发布后链接
    error: str | None     # 失败原因（含自动截图路径）
```

稿件在库里/管理页用的是 **dict**，字段：
`{title, body, image, track, source, status, created_at}`
（注意：库里正文字段叫 `body`，Article 里叫 `content`，编排时注意转换）

---

## 1. 环境变量（API key，从 .env 读）

```
DEEPSEEK_API_KEY   出文（必需）
TAVILY_API_KEY     搜索素材（免费，默认搜索源）
PEXELS_API_KEY     图库配图（mode=pexels 时用）
BOCHA_API_KEY      搜索素材（付费，provider=bocha 时用）
```
`config.load_env()` 会把 `.env` 读进 `os.environ`。程序入口先调它一次。

---

## 2. 配置读取 —— config.py

```python
load_env(path=".env")                    # 读 .env 里的 key 到环境变量
load_settings() -> dict                  # 读 settings.yaml（流水线参数）
enabled_tracks() -> dict                 # 读 tracks.yaml 里 enabled=true 的赛道
                                         # 返回 {track_key: {name, keywords, prompt, enabled}}
load_accounts() -> list[dict]            # 读 accounts.yaml
get_account(name) -> dict                # 按名取一个账号配置
```

**配置文件字段：**
- `settings.yaml` → pipeline{mode, account, max_per_run, per_track_quota{赛道名:数}, per_track_default}
  、image{mode(scrape/pexels), skip_tracks}、hotspot{provider, sources, top_n, research_count}
  、research{provider(tavily/bocha)}
- `tracks.yaml` → tracks{赛道key:{name, enabled, keywords[], prompt}}
- `accounts.yaml` → accounts[{name, platform, profile_dir, browser_channel, headless, enabled}]

> 产品化后：这些 YAML 的内容应改成**界面里可视化配置**，写回文件或数据库。

---

## 3. 抓热点 + 筛选 —— hotspot/

```python
from hotspot import fetch_all, classify

# 抓多平台热榜（百度+头条官方接口，免Docker免key）
items = fetch_all(base_url="", sources=["baidu","toutiao"], top_n=30, provider="official")
# -> list[HotItem]

# 判断某热点属于哪个赛道
hit = classify(item, enabled_tracks())   # -> (track_key, track_conf) 或 None
# track_conf 含 name / keywords / prompt
```

---

## 4. 搜索素材 —— research/

```python
from research import search_results, build_material

results = search_results(query=hot_title, count=5, provider="tavily")
# -> list[{title, content, url}]   （url 供抓配图用）
material = build_material(results)   # -> 拼接好的素材文本（喂给 writer）
```

---

## 5. 出文 —— generate/writer.py

```python
from generate import write   # 或 from generate.writer import write

article = write(hot_title, track_prompt, material="")
# -> Article(title, content)
# track_prompt 来自 track_conf["prompt"]；material 为空时降级为"仅按标题写"
```

---

## 6. 配图 —— generate/illustrate.py

```python
from generate.illustrate import scrape_cover, pick_cover

# 方式A（默认）：抓报道原图（挑页面最大最清晰的图）
img_rel = scrape_cover(urls=[r["url"] for r in results], title=article.title)
# 方式B：Pexels 图库兜底
img_rel = pick_cover(article.title, article.content)
# 都返回相对 output/ 的路径 "images/xxx.jpg" 或 None（失败）
```

---

## 7. 稿件库 —— store/db.py（SQLite，稿件持久化 + 状态）

```python
import store

store.is_processed(title) -> bool                     # 去重：这标题处理过没
store.save_article(item_dict, status="未发")           # 存/更新一篇稿件
    # item_dict = {title, body, image, track, source, time}
store.set_status(title, "已发")                        # 改状态
store.all_articles(limit=500) -> list[dict]            # 取所有稿件（新→旧）
```
状态取值：`未发` / `已发`。

---

## 8. 发布 —— publishers/

```python
from publishers import get_publisher, Article

pub = get_publisher(get_account("hans_toutiao"))
result = pub.publish(article)    # -> PublishResult；自动定时发布（用头条默认时间）
# 前提：该账号 profile 已登录（先跑过 login.py）
# publisher 内部用 Playwright 持久化 Chrome（profile_dir）驱动头条后台
```
- 发布器基于 codegen 录制的选择器，可能因头条改版失效，需保留可维护性。
- 正文会自动去多余空行、插入 cover_image 到正文（自动变封面）。

---

## 9. 定时排班 —— schedule_plan.py

```python
from schedule_plan import schedule_times
times = schedule_times(n=5)   # -> list[datetime]，把 n 篇错开排在当天 7:00–23:00
```

---

## 10. 稿件管理页渲染 —— review/render.py

```python
import review
review.render_dashboard(store.all_articles(), out_path="output/dashboard.html")
# 生成静态管理页（未发/已发筛选、复制、手动标记）
# 产品化后：这个会被 FastAPI 动态页面取代，但可参考它的卡片/交互
```

---

## 11. 建议的 FastAPI 接口 → 现有函数映射

产品化时，界面层调这些接口，接口层内部调上面的函数：

| 页面 | 接口 | 内部调用 |
|---|---|---|
| 配置页 | `GET/POST /config` | load_settings / load_env / 写回 yaml 或 db |
| 选题页 | `POST /hotspots` | fetch_all → 逐条 classify → 按赛道分组返回 |
| 筛选页 | （前端勾选，无需接口） | — |
| 生成页 | `POST /generate`（传勾选的热点） | search_results→build_material→write→scrape_cover→save_article("未发") |
| 生成页 | `POST /regenerate` | 同上，单篇重跑 |
| 发布页 | `GET /articles` | all_articles |
| 发布页 | `POST /publish`（传稿件id/标题） | get_publisher.publish → set_status("已发") |

**整条流水线的现成写法，直接看 `run_daily.py` 的 main()** —— 它已经把
"抓→筛→均衡选题→搜索→出文→配图→存库→（发布/渲染）"串好了，
FastAPI 接口基本是把这套逻辑按页面拆成几段。

---

## 12. 给 Code 的注意事项

1. **复用，别重写**：上面所有函数都能直接 import 调用，引擎已验证可用。
2. **依赖别抄 AIWriteX**：借鉴它 pywebview+FastAPI 的**结构**和打包方式，
   但依赖用本项目 requirements.txt（AIWriteX 的依赖有版本冲突坑）。
3. **正文字段名**：库里是 `body`，Article 是 `content`，转换时注意。
4. **图片路径**：库里/管理页存相对路径 `images/xxx.jpg`，实际文件在 `output/images/`，
   发布时要拼成 `output/images/xxx.jpg` 的完整路径传给 Article.cover_image。
5. **key 管理**：现在从 .env 读；产品化后改成界面填、加密存本地。
6. **分阶段、小步提交**：先做后端接口跑通（curl 能调），再做页面，最后套壳打包。
