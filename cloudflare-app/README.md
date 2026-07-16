# FlowX Cloud

FlowX Cloud 是本地 FastAPI 应用在 Cloudflare 免费层上的运行版本。

## 组件

- Cloudflare Worker：API、Google OAuth 身份验证、外部 AI/搜索调用
- Workers Static Assets：单页工作台
- D1（APAC）：加密配置和稿件库
- Worker Secrets：OAuth、会话签名与 AES-GCM 加密根密钥

## 能力

工作台前台按「选题、稿库·发布、设置」组织，生产与审核作为后台自动环节运行。百度、今日头条、抖音、微博、知乎、B站、36氪、澎湃由 Worker 优先直抓，并以可配置的 DailyHotApi 回退；支持 Tavily → 博查搜索回退、DeepSeek 写稿、Pexels 配图、规则 + AI 质检、自动二次修改与复检，以及单轮最多 20 篇受控并发生成。每篇稿件会提炼 3–6 处关键结论、数字或核心信息并加粗，稿库预览、富文本复制与平台同步均保留重点样式。写稿成功或手动删除的热点会按账号移出选题池。

稿库与发布已经合并为单一工作台，通过 Wechatsync 浏览器扩展复用用户本机已有的今日头条、百家号和知乎登录态。顶部统一勾选平台后，单篇“一键发布”和最多 20 篇批量发布都会进入持久队列并按稿件顺序执行。Cloudflare D1 按 Google 邮箱保存发布队列、重试状态、错误信息与平台返回的草稿链接；浏览器重新打开页面后会继续待处理任务。发布前若缺少封面，Worker 会调用当前账号的 Pexels Key 自动采集横版封面，并交给扩展上传。平台 Cookie 不会进入 Worker，公开发布仍由用户在各平台草稿箱检查排版后确认。

所有稿件从首次生成时间起采用 36 小时硬性生命周期，人工修改、质检、审批或发布均不会延长。Worker Cron 每分钟清理到期稿件及其发布记录和队列任务；稿库读取和浏览器到期计时会再次复核，避免过期内容继续显示。

## 安全约束

- 整个 Worker（包括静态入口）默认通过 Google OAuth 登录；登录会话使用安全 Cookie 在同一浏览器中保留 30 天。
- `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`SESSION_SECRET`、`ALLOWED_EMAILS` 与 `CONFIG_KEY` 只能通过 `wrangler secret put` 设置。
- 旧版 HTTP Basic 应急入口已停用，避免浏览器缓存凭证后无法退出或切换 Google 账号。
- DeepSeek、Tavily、博查与 Pexels Key 通过工作台写入时，在 Worker 内使用 AES-GCM 加密，并按 Google 邮箱隔离后进入 D1；热点偏好、赛道与稿库数据也按邮箱隔离。
- 不得把任何生产 Secret 写进 `wrangler.jsonc`、Git 或日志。
