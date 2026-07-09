# 头条自动化流水线（phase1：本地审阅 → 手动发）

每天定时：抓多平台热榜 → 按赛道筛选 → DeepSeek 出文(标题≤30字+正文) → Pexels 自动配封面
→ 汇成本地网页 output/review.html。你打开网页，一键复制标题正文、下载配图，到头条手动发。
内容验证 OK 后，settings.yaml 的 mode 从 review 改成 publish，即切换为浏览器自动发。

## 目录
```
hotspot/     ① 抓热榜 + ② 按赛道筛选
tracks.yaml  赛道：方向开关 + 关键词 + 提示词（选方向在这）
generate/    ③ 出文(writer) + 配封面图(illustrate) + DeepSeek客户端(llm)
review/      ④ 生成审阅网页(render)
publishers/  phase2 自动发布（toutiao 已填选择器；phase1 用不到）
store/       去重 + 内部记录(SQLite)
settings.yaml 模式/账号/条数/配图/热榜源
run_daily.py 每日流水线（定时入口）
output/      review.html + images/（生成物）
```

## 安装
```bash
cd ~/toutiao-auto
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

## 一次性准备（3 个 key/服务）
1. DeepSeek（出文）：`export DEEPSEEK_API_KEY=你的key`
2. Pexels（配图，免费）：注册 https://www.pexels.com/api/ 后 `export PEXELS_API_KEY=你的key`
3. 热榜：默认用公开聚合API vvhan，**免Docker、免部署，无需任何设置**。

## 选题方向（tracks.yaml）
每个赛道 = 开关 + 关键词 + 提示词。只想跑体育科技？把 minsheng、yule 的 enabled 设 false。
关键词跨赛道撞车会误判（如"曝光"归娱乐、"发布"归科技），删掉模糊词、只留强特征词最准。

## 跑（phase1）
确认 settings.yaml 里 mode: review，然后：
```bash
python run_daily.py
```
跑完打开 output/review.html：每篇一张卡片，封面图 + 标题（复制）+ 正文（复制）+ 下载配图，
底部小字标赛道/来源/时间（内部参考，不进复制内容）。复制到头条手动发。

## 定时（launchd，每天自动）
编辑 com.hans.toutiao-auto.plist：换真实路径、填 DEEPSEEK_API_KEY 和 PEXELS_API_KEY、改时间，然后：
```bash
cp com.hans.toutiao-auto.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hans.toutiao-auto.plist
```
每天定时生成 review.html，你打开审阅即可。停用：launchctl unload 同路径。

## 从"手动发"切到"自动发"（phase2）
验证几天内容能用后：
1. 确认 publishers/toutiao.py 的发布选择器（预览并发布→确认发布那步待补录）。
2. settings.yaml 的 mode 改成 publish。
之后 run_daily 会用浏览器自动发到头条（需先 python login.py hans_toutiao 登录过）。

## 加账号/加平台
加账号：accounts.yaml 复制一条改 name+profile_dir。加平台：填 publishers/baijiahao.py 并注册。

## 安全
DEEPSEEK/PEXELS key 用环境变量；profiles/ 是登录凭证已 .gitignore；仅个人自用。
