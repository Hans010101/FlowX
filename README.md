# FlowX

FlowX 是一套面向中文内容团队的本地优先 AI 内容工作流：抓取多平台热点，按赛道归类，检索素材，生成文章与配图，自动质检和定向修订，再同步到多个内容平台的草稿箱。

> 抓热点 → AI 写稿 → 配图 → 质检 → 定向优化 → 稿库 → 平台草稿箱 → 人工发布

## 在线使用

- 云端工作台：<https://flowx-app.hans-pan007.workers.dev>
- 产品介绍站：<https://flowx-2hv.pages.dev>

云端工作台运行在 Cloudflare Workers + D1，支持热点抓取、AI 生成、质检、稿库、编辑与状态管理。首次访问需要维护者提供的登录密码，登录后在“API 设置”中配置自己的 DeepSeek 与 Tavily Key。

## 为什么是“本地优先”

FlowX 的发布能力依赖本机浏览器中的 Wechatsync 扩展和各平台登录态。API Key、Cookie 与平台会话留在用户设备上；这也意味着当前完整版本不能原样运行在 Cloudflare Pages/Workers 等纯无服务器环境。Cloudflare 可承载公开产品站，核心工作台仍应在本机或常驻桌面主机运行。

## 已有能力

- 百度、头条直抓；抖音、微博、知乎、B 站、36 氪、澎湃等通过 DailyHotApi 聚合
- 9 个内容赛道，可配置开关、关键词、写作提示词与展示顺序
- 多关键词加权归类、跨平台话题合并、6 小时选题去重
- Tavily → 博查素材检索回退链
- DeepSeek 写稿、原报道图候选池与 Pexels 兜底
- 规则 + AI 五维质检，绿/黄/红质量闸与防编造修订红线
- 稿库、人工编辑、换图、重新质检、发布状态管理
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

1. 安装并登录 Wechatsync 浏览器扩展。
2. 安装 Wechatsync CLI，设置 `WECHATSYNC_TOKEN` 和 `WECHATSYNC_CLI_PATH`。
3. 在稿库点击“自动发布”。FlowX 会先检查 CLI、扩展连接和目标平台登录态；检查通过后才允许同步。

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
