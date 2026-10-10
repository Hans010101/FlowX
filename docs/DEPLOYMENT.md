# 部署说明

## 完整工作台

完整 FlowX 应部署在用户本机或一台可长期运行的桌面主机上，因为它需要：

- 本地 SQLite 写入；
- Python 常驻进程和 APScheduler；
- 调用 Wechatsync CLI 子进程；
- 连接已登录平台账号的浏览器扩展。

推荐只监听 `127.0.0.1`。如果通过内网或 Tunnel 暴露，必须先增加身份认证，不能把当前管理接口直接公开到互联网。

## Cloudflare Pages

`cloudflare-site/` 是公开产品站，可使用 Cloudflare 免费的 `pages.dev` 域名部署：

```bash
npx wrangler pages deploy cloudflare-site --project-name flowx
```

Cloudflare 的边缘网络会自动选择离访问者较近的节点，不提供“固定选择亚洲服务器”的选项；亚洲用户通常会由亚洲 PoP 响应。

## Cloudflare Workers 云端工作台

`cloudflare-app/` 是为免费层重构的可操作版本，使用 Workers Static Assets + D1：

```bash
npx wrangler d1 create flowx-cloud-db
npx wrangler d1 execute flowx-cloud-db --remote --file cloudflare-app/schema.sql
npx wrangler secret put CONFIG_KEY --config cloudflare-app/wrangler.jsonc
npx wrangler secret put SESSION_SECRET --config cloudflare-app/wrangler.jsonc
npx wrangler secret put ALLOWED_EMAILS --config cloudflare-app/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_ID --config cloudflare-app/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_SECRET --config cloudflare-app/wrangler.jsonc
npx wrangler deploy --config cloudflare-app/wrangler.jsonc
```

在现有 Google Cloud“Web 应用”OAuth 客户端中确认：

- 已获授权的 JavaScript 来源：`https://flowx-app.bitman001.workers.dev`
- 已获授权的重定向 URI：`https://flowx-app.bitman001.workers.dev/auth/callback`

`ALLOWED_EMAILS` 使用英文逗号分隔允许登录的 Google 邮箱。`SESSION_SECRET` 应使用至少 32 字节的随机值。当前实例：<https://flowx-app.bitman001.workers.dev>。登录态由 `HttpOnly`、`Secure`、`SameSite=Lax` Cookie 保存 30 天；API Key 在 Worker 内以 AES-GCM 加密，并以 Google 邮箱作为数据分区写入 D1。稿库同样按邮箱隔离，仓库和前端只保存“是否已配置”。

### 002 账号迁移记录（2026-10-10）

- Cloudflare 账号：`a828bebda1f352216c7d7da425bad17a`
- Worker：<https://flowx-app.bitman001.workers.dev>
- D1：`dc5bc99b-bac3-4fc7-b51c-ba9b43c465ec`
- 定时任务：`* * * * *`
- 部署代码：Git 提交 `127f1c51fa4349f646bee6896cfed0457eef36e4`
- Google Cloud 项目：`FlowX Cloud`（`absolute-disk-502511-r5`）
- Google OAuth 客户端：`91623359067-idgm0q4mutlgkkjnh8ggjkc6840kdids.apps.googleusercontent.com`

现有 Google OAuth 客户端已保存并回读本节列出的 JavaScript 来源和重定向 URI。Chrome 已通过 `/auth/login` 完成真实登录并进入 002 工作台，原 007 Google 邮箱继续使用。默认 Wrangler 已切换为 002 Cloudflare OAuth；007 Wrangler OAuth 仅保存在受限迁移目录中作为备份，不要登录、刷新或覆盖共享凭据。旧 007 Cloudflare 资源仍作为迁移备份保留，不要新建或重置 Google OAuth 客户端。

最终部署与只读核验证据保存在：

- `/Users/hans.pan/Library/Application Support/Dianjinshou/migration-002-20261009/flowx-final-deployed-20261010.json`
- `/Users/hans.pan/Library/Application Support/Dianjinshou/migration-002-20261009/flowx-final-readonly-verified-20261010.json`
- `/Users/hans.pan/Library/Application Support/Dianjinshou/migration-002-20261009/flowx-google-callback-002-20261010.png`
- `/Users/hans.pan/Library/Application Support/Dianjinshou/migration-002-20261009/flowx-login-002-verified-20261010.png`

### 007 删除就绪验收（2026-10-10）

在不触发写稿、发布或外部消息的前提下，已按“007 Cloudflare 资源全部不存在”完成增量只读验收：

- 当前 `wrangler.jsonc`、线上 Worker 绑定和 OAuth 回调均只指向 002 账号；D1 绑定为 `dc5bc99b-bac3-4fc7-b51c-ba9b43c465ec`，没有 R2 绑定，定时任务仍为 `* * * * *`。
- 使用 `hans.pan007@gmail.com` 从 Google OAuth 登录 002 Worker 成功；设置页能读取该邮箱独立保存的 4 项 API 配置状态、8 个热点源、9 个赛道和 DailyHot 公共地址，未发现旧 Worker 主机、旧账号 ID 或旧 D1 ID。
- 线上选题页和稿库页读取正常；当前稿库为 0 篇，符合 36 小时保留策略。部署包含 `scheduled` 处理器，且定时任务仍在线，历史迁移快照中的 2 篇稿件现已不再出现在有效稿库中。
- 迁移后的目标 D1 快照包含 5 张用户表、14 条按邮箱加密的配置和 2 篇稿件；图片 JSON 全部有效，图片只引用 `images.pexels.com`，发布记录与发布任务均无孤儿记录。
- 对当前在线 002 D1 的 7 张表、51 个文本字段执行只读扫描，共检查 17 个旧 Worker 主机、旧账号 ID、旧 D1 ID 变体，命中数均为 0，写入行数为 0。历史文章正文未改写。
- 线上界面已显示“2 张主题配图”，实现为 1 张封面与 1 张正文图；当前部署包含提交 `7ac56fa`。

结论：FlowX 当前运行时、OAuth、D1、定时清理和图片附件均不再依赖 007 Cloudflare 资源，可以把 007 作为独立备份处置。发布到今日头条、百家号、知乎仍依赖当前浏览器中的文章同步助手及各平台登录 Cookie；验收时扩展未连接，因此这只表示“FlowX 已与 007 解耦”，不表示外部平台登录态已全部可用。

本次在线 D1 只读扫描证据：

- `/Users/hans.pan/Library/Application Support/Dianjinshou/migration-002-20261009/002-deletion-flowx-db-scan-20261010.json`

## 为什么不把 FastAPI 原样放进 Workers

原始后端使用 SQLite、本地文件、后台调度线程和 `subprocess`，发布环节还要求浏览器扩展登录态。这些能力不属于 Cloudflare Pages/Workers 的运行模型。因此云端版改用 D1、Web Crypto 和 Worker `fetch`，并明确移除依赖本机浏览器的发布链路。

若未来要实现真正云端版，应拆分为：Cloudflare 前端与鉴权、云数据库/对象存储、队列化任务执行器，以及运行在用户设备上的“发布代理”。
