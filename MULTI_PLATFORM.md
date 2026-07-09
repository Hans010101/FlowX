# 多平台发布 · 架构与规划（MULTI_PLATFORM）

> 目标：从只发头条，扩展到百家号、搜狐号、微信公众号等。
> 策略：**架构和界面位置现在留好，平台逐个实现；先一稿多发，内容适配以后再说。**

---

## 一、好消息：架构底子已经留好了

现有 `publishers/` 就是为多平台设计的可插拔结构：
- `base.py` → `BasePublisher` 抽象基类（定义统一接口 publish/is_logged_in/do_publish）
- `__init__.py` → `REGISTRY` 注册表 + `get_publisher(account)` 工厂
- `toutiao.py` → 头条实现（已完成）
- `baijiahao.py` → 百家号占位（早就留了，待填选择器）

**加一个平台 = 加一个文件 + 注册一行**，其它代码不动。

---

## 二、平台分两类，实现方式不同

| 平台 | 官方API | 实现方式 | 复用现有架构 | 优先级 |
|---|---|---|---|---|
| 今日头条 | 无 | 浏览器自动化 + cookie | ✅ 已完成 | — |
| 百家号 | 无 | 浏览器自动化（同头条套路） | ✅ 复用 base，填选择器 | 1 |
| 搜狐号 | 无 | 浏览器自动化 | ✅ 复用 base，填选择器 | 2 |
| 微信公众号 | **有** | 调官方API（AppID/Secret） | ⚠️ 另一套逻辑，见下 | 3 |

### A. 浏览器自动化类（百家号 / 搜狐号）
完全复制 `toutiao.py` 的模式：
1. 复制 toutiao.py → baijiahao.py，改 LOGIN_URL / PUBLISH_URL
2. 用 `playwright codegen` 在该平台后台录制发布流程，提取选择器填入 do_publish
3. 在 REGISTRY 注册
4. 每个平台一个独立 Chrome profile（各自登录）

### B. 官方API类（微信公众号）
和浏览器类不同——**不用浏览器，调接口**：
- 需要用户填 AppID + AppSecret（公众号后台拿）
- 用微信"草稿箱/发布"接口发文（先上传图文素材，再发布）
- 实现：`wechat.py` 继承 BasePublisher，但 **override publish()** 直接走 API，
  不用 base 的浏览器逻辑（base 需小改：允许非浏览器发布器）
- 反而比浏览器类稳定（不怕改版），但要处理素材上传、access_token 等

> 注：base.py 需要小重构——把"浏览器启动"从 publish 主流程里解耦，
> 让浏览器类和 API 类都能实现同一个 `publish(article) -> PublishResult` 接口。

---

## 三、一稿多发（先做这个）

模型：**一篇稿子 → 选择目标平台（可多选）→ 逐个平台发布 → 分别记录状态**

- `accounts.yaml` 支持多平台多账号：
  ```yaml
  accounts:
    - {name: hans_toutiao,   platform: toutiao,   profile_dir: profiles/toutiao,   enabled: true}
    - {name: hans_baijiahao, platform: baijiahao, profile_dir: profiles/baijiahao, enabled: true}
    - {name: hans_wechat,    platform: wechat,    app_id: xxx, app_secret: xxx,     enabled: true}
  ```
- 发布函数：`publish_to(article, target_accounts: list) -> dict[平台, PublishResult]`
  逐个平台调 `get_publisher(acc).publish(article)`，汇总结果。
- **每平台独立成功/失败**：头条发成功、百家号失败，互不影响，各自记状态。

### 数据结构：按平台记状态
新增表 `article_publish`：
```
article_id  TEXT      -- 关联 articles
platform    TEXT      -- toutiao / baijiahao / ...
status      TEXT      -- 未发 / 已发 / 失败
url         TEXT      -- 发布后链接
error       TEXT      -- 失败原因
published_at TEXT
```
一篇稿子 → 多条平台状态记录。管理页按平台显示。

---

## 四、内容适配（以后做，先留接口）

先"一稿多发"（所有平台发同一版）。以后每平台各适配一版时，加一步：
`adapt_for_platform(article, platform) -> article`（调 DeepSeek 按平台调性改写）
- 公众号：偏深度长文、需排版
- 百家号：和头条近似，审核更严
- 小红书（若加）：短、口语、多标签

现在把这个函数留成"直接返回原文"的占位，以后填。

---

## 五、界面位置（原型已体现）

1. **系统设置 → 平台管理**：每个平台一张卡片
   - 状态：已连接 / 待接入
   - 浏览器类：显示登录状态 + "登录"按钮
   - API类（公众号）：填 AppID / AppSecret
2. **发布环节**：发布时勾选目标平台（可多选，一稿多发）
3. **发布管理**：每张稿件卡片显示各平台状态（头条✓ · 百家号 待发 · 公众号 —）

---

## 六、实现路线（分期）

- **阶段A（现在）**：架构留好、界面留好（本文档 + 原型）
- **阶段B**：百家号（复制头条模式 + codegen 录制）
- **阶段C**：搜狐号（同上）
- **阶段D**：微信公众号（官方API，base 小重构）
- **阶段E**：内容按平台适配（DeepSeek 平台改写）

每加一个平台，都是"填一个 publisher + 界面加一张平台卡片"，不影响已有平台。
