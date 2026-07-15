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

在 Google Cloud 创建“Web 应用”OAuth 客户端，并配置：

- 已获授权的 JavaScript 来源：`https://flowx-app.hans-pan007.workers.dev`
- 已获授权的重定向 URI：`https://flowx-app.hans-pan007.workers.dev/auth/callback`

`ALLOWED_EMAILS` 使用英文逗号分隔允许登录的 Google 邮箱。`SESSION_SECRET` 应使用至少 32 字节的随机值。当前实例：<https://flowx-app.hans-pan007.workers.dev>。登录态由 `HttpOnly`、`Secure`、`SameSite=Lax` Cookie 保存 30 天；API Key 在 Worker 内以 AES-GCM 加密，并以 Google 邮箱作为数据分区写入 D1。稿库同样按邮箱隔离，仓库和前端只保存“是否已配置”。

## 为什么不把 FastAPI 原样放进 Workers

原始后端使用 SQLite、本地文件、后台调度线程和 `subprocess`，发布环节还要求浏览器扩展登录态。这些能力不属于 Cloudflare Pages/Workers 的运行模型。因此云端版改用 D1、Web Crypto 和 Worker `fetch`，并明确移除依赖本机浏览器的发布链路。

若未来要实现真正云端版，应拆分为：Cloudflare 前端与鉴权、云数据库/对象存储、队列化任务执行器，以及运行在用户设备上的“发布代理”。
