# FlowX Cloud

FlowX Cloud 是本地 FastAPI 应用在 Cloudflare 免费层上的运行版本。

## 组件

- Cloudflare Worker：API、身份验证、外部 AI/搜索调用
- Workers Static Assets：单页工作台
- D1（APAC）：加密配置和稿件库
- Worker Secrets：登录密码与 AES-GCM 加密根密钥

## 能力

热点抓取、赛道分类、Tavily 素材搜索、DeepSeek 写稿、规则 + AI 质检、定向优化、稿库、人工编辑、状态管理。

Wechatsync 与平台同步发布不在云端版中，因为它需要用户电脑上的浏览器 Cookie、扩展和 CLI。该部分继续由本地完整版承担。

## 安全约束

- 整个 Worker（包括静态入口）必须通过 HTTP Basic Authentication。
- `FLOWX_PASSWORD`、`CONFIG_KEY` 只能通过 `wrangler secret put` 设置。
- DeepSeek/Tavily Key 通过工作台写入时，在 Worker 内使用 AES-GCM 加密后进入 D1。
- 不得把任何生产 Secret 写进 `wrangler.jsonc`、Git 或日志。
