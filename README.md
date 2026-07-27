# FlowX

FlowX 是一套面向中文内容团队的本地优先 AI 内容工作流：抓取多平台热点，按赛道归类，检索素材，生成文章与配图，自动质检和定向修订，再同步到多个内容平台的草稿箱。

> 抓热点 → AI 写稿 → 配图 → 质检 → 定向优化 → 稿库 → 平台草稿箱 → 人工发布

## 在线使用

- 云端工作台：<https://flowx-app.hans-pan007.workers.dev>
- 产品介绍站：<https://flowx-2hv.pages.dev>

云端工作台运行在 Cloudflare Workers + D1，前台只保留「选题、稿库·发布、设置」：勾选热点并开始撰稿后，检索、写作和质检在后台执行，完成的稿件直接进入稿库。首次访问使用获准的 Google 账号登录；登录会话在同一浏览器中保留 30 天。登录后可按账号配置 DeepSeek、Tavily、博查、Pexels Key、热点来源与赛道，并通过 Wechatsync 浏览器扩展一键同步到今日头条、百家号和知乎草稿箱。

## 为什么是“本地优先”

FlowX 的云端版已经覆盖选题、检索、写稿、配图、质检、稿库和三平台草稿同步。平台登录态仍由本机浏览器中的 Wechatsync 扩展管理，Cookie 不上传到 Cloudflare；Cloudflare 只保存当前 Google 账号的非敏感同步结果。

## 已有能力

- 百度、头条、抖音、微博、知乎、B 站、36 氪、澎湃由 Worker 优先直抓，并以可配置的 DailyHotApi 作为回退
- 9 个内容赛道，可配置开关、关键词、写作提示词与展示顺序
- 多关键词加权归类、跨平台话题合并、6 小时选题去重
- Tavily → 博查素材检索回退链
- DeepSeek 独立负责首稿、短稿扩写和稿件修改，写作链路不会回退到 Workers AI
- Cloudflare Workers AI 优先承担质检、配图检索词和图片相关性判断等基础任务，异常时由 DeepSeek 兜底
- 规则 + AI 五维质检，绿/黄/红质量闸与防编造修订红线
- 稿库与发布一体化：自动二次修改与复检、智能换配图、全局平台选择、单篇或最多 20 篇顺序发布
- 选题写稿成功后自动移出热点池，也支持批量删除不需要二创的热点
- 快阅读排版：每篇稿件自动提炼 3–6 处关键结论、数字或核心信息并加粗，稿库预览、富文本复制和平台同步均保留重点样式
- 差异化写作：先确定独特切入角度，再围绕明确观点重建文章结构；自动比较候选标题与热点原标题的相似度，过于接近时调用 DeepSeek 重新命名
- 标准文章结构：正文净字数控制在 600–1000 字；开头提供 100 字以内导语，正文用 2–3 层事实与分析推进，末尾以自然语气给出专业观点、影响判断或趋势预测
- 热点内容时效：稿件及关联的审批、发布记录和发布任务自首次生成起只保留 36 小时；修改或发布不会续期，Cloudflare 每分钟清理一次，稿库打开及到期时还会即时复核
- 云端一键同步到今日头条、百家号、知乎草稿箱，逐平台展示结果和草稿链接
- 账号隔离的云端发布任务队列，支持中断恢复、失败重试和发布记录管理
- 每篇自动从 Pexels 匹配 2–3 张横版图片（1 张封面、1–2 张正文图），检索词围绕事件主体、地点和行业场景生成，候选图还会结合图片描述做相关性复核；图片随正文交给 Wechatsync 同步
- Wechatsync 发布前连接预检、手动同步与 CLI 自动进草稿箱
- APScheduler 定时流水线与运行记录

## 快速开始

要求：Python 3.11+。只有使用已冻结的 Playwright 兜底发布器时才需要额外安装 `requirements-publishers.txt` 和浏览器运行时。

```bash
git clone https://github.com/Hans010101/FlowX.git
cd FlowX
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>。至少需要配置 `DEEPSEEK_API_KEY` 与 `TAVILY_API_KEY`；其余变量见 [.env.example](.env.example)。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 自动同步到平台草稿箱

云端工作台：

1. 在 Chrome 安装 Wechatsync 浏览器扩展，并登录今日头条、百家号和知乎。
2. 打开 FlowX 的“稿库 · 发布”，点击“检测登录状态”。
3. 选择目标平台后点击稿件的“一键发布”。FlowX 会显示逐平台进度并保存草稿链接。

选定顶部平台后，可直接点击单篇“一键发布”，也可勾选最多 20 篇批量排队。配图不足 2 张时 FlowX 会先从 Pexels 自动补齐主题配图；也可以在稿件卡片中点击“智能换配图”整体替换。发布任务和执行结果按当前 Google 邮箱保存在 D1，浏览器中断后会重新排队，并在下次打开稿库与发布页时继续执行。

本地完整版也可安装 Wechatsync CLI，设置 `WECHATSYNC_TOKEN` 和 `WECHATSYNC_CLI_PATH`，通过本地服务同步。

注意：同步到草稿箱不等于公开发布。FlowX 无法感知用户在平台后台的最终发布动作，因此“标记已发”保持人工确认。

## 项目结构

```text
app.py              FastAPI 接口与工作流编排
static/             单页工作台
hotspot/            热点抓取、合并与赛道归类
research/           素材检索与回退链
generate/           写稿、修订、配图
quality/            规则与 AI 质检
store/              SQLite 稿库和选题去重
publishers/         已冻结的 Playwright 兜底发布器
cloudflare-site/    可部署到 Cloudflare Pages 的公开产品站
cloudflare-app/     Workers + D1 云端工作台
tests/              不依赖外部 API 的核心回归测试
```

## 部署边界

- 本机/桌面主机：完整功能，包括浏览器扩展发布、SQLite 与定时任务。
- Cloudflare Pages：公开产品介绍、文档与下载入口。
- Cloudflare Workers：不支持本项目依赖的本机浏览器扩展、`subprocess`、持久 Python 调度进程与本地 SQLite，不能直接承载完整后端。

进一步说明见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) 和 [docs/PRODUCT-ROADMAP.md](docs/PRODUCT-ROADMAP.md)。

## 安全原则

- 不提交 `.env`、SQLite 数据库、运行日志、生成内容或浏览器 Profile。
- `/settings` 只返回 Key 是否已配置，不返回 Key 内容。
- CLI Token 只进入子进程环境，所有返回文本在展示前会脱敏。
- 缺少来源的事实只能删除、软化或去掉具体数字，禁止为了通过质检而编造来源。

如发现安全问题，请不要创建公开 Issue，按 [SECURITY.md](SECURITY.md) 中的方式联系维护者。

## 许可证

[MIT](LICENSE)
