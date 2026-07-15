# FlowX Cloud

FlowX Cloud 是本地 FastAPI 应用在 Cloudflare 免费层上的运行版本。

## 组件

- Cloudflare Worker：API、Google OAuth 身份验证、外部 AI/搜索调用
- Workers Static Assets：单页工作台
- D1（APAC）：加密配置和稿件库
- Worker Secrets：OAuth、会话签名与 AES-GCM 加密根密钥

## 能力

工作台按「选题、生产·审核、稿库·发布、设置」组织。百度、今日头条、抖音、微博、知乎、B站、36氪、澎湃由 Worker 优先直抓，并以可配置的 DailyHotApi 回退；支持 Tavily → 博查搜索回退、DeepSeek 写稿、Pexels 配图、规则 + AI 质检、定向优化、稿库、人工编辑与状态管理。

云端发布页通过 Wechatsync 浏览器扩展复用用户本机已有的今日头条、百家号和知乎登录态，可一键同步到所选平台草稿箱。平台 Cookie 不会进入 Worker；D1 只按 Google 邮箱保存同步状态、错误信息与平台返回的草稿链接。公开发布仍由用户在各平台草稿箱检查排版后确认。

## 安全约束

- 整个 Worker（包括静态入口）默认通过 Google OAuth 登录；登录会话使用安全 Cookie 在同一浏览器中保留 30 天。
- `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`SESSION_SECRET`、`ALLOWED_EMAILS` 与 `CONFIG_KEY` 只能通过 `wrangler secret put` 设置。
- 旧版 HTTP Basic 应急入口已停用，避免浏览器缓存凭证后无法退出或切换 Google 账号。
- DeepSeek、Tavily、博查与 Pexels Key 通过工作台写入时，在 Worker 内使用 AES-GCM 加密，并按 Google 邮箱隔离后进入 D1；热点偏好、赛道与稿库数据也按邮箱隔离。
- 不得把任何生产 Secret 写进 `wrangler.jsonc`、Git 或日志。
