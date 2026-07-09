"""
app.py —— FastAPI 接口层

只编排现有引擎，不重写：
  POST /hotspots -> hotspot.fetch_all + hotspot.classify，按赛道分组返回（不做每赛道篇数限制）
  POST /generate -> 对用户勾选的热点逐条：search_results→build_material→write→scrape_cover
                    →quality_check（绿/黄→"未发"，红→"待修复"）→save_article
  POST /recheck  -> 按稿件 id 重新质检并更新 qc_* 和 status
  GET  /articles -> store.all_articles
"""
from __future__ import annotations

import json
import os
import time

import html as html_escape_mod
import re
import subprocess
import tempfile

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (load_env, load_settings, enabled_tracks, get_account,
                    load_tracks, set_hotspot_sources, set_track_enabled, set_research_thresholds,
                    ordered_track_keys, set_track_order)
from hotspot import fetch_all, classify
from generate import write, pick_cover
from generate.illustrate import scrape_cover_pool, download_valid_image, save_image_bytes
from generate.revise import revise
from research import search_results, build_material, search_with_fallback
from publishers import get_publisher, Article
from quality import quality_check
import store
from store.db import _aid


def _qc_safe(art_item: dict) -> dict:
    """质检保险层：异常不中断整批，降级为黄档提醒人工复核。"""
    try:
        return quality_check(art_item)
    except Exception as e:
        print(f"  ⚠️ 质检异常，降级为黄档：{e}")
        return {"score": None, "level": "yellow", "problems": [f"质检异常（{e}），请人工复核"]}


def _apply_qc(art_item: dict) -> str:
    """对 art_item 就地写入 qc_*，返回按档位定的 status（red→待修复，其余→未发）。"""
    qc = _qc_safe(art_item)
    art_item["qc_score"] = qc["score"]
    art_item["qc_level"] = qc["level"]
    art_item["qc_problems"] = json.dumps(qc["problems"], ensure_ascii=False)
    return "待修复" if qc["level"] == "red" else "未发"

load_env()

app = FastAPI(title="头条内容工作流 API")


class HotspotsRequest(BaseModel):
    sources: list[str] | None = None
    top_n: int | dict[str, int] | None = None
    provider: str | None = None
    base_url: str | None = None
    enabled_tracks: list[str] | None = None  # 前端页1的赛道开关（track_key 列表）；不传则用 tracks.yaml 默认


@app.post("/hotspots")
def get_hotspots(req: HotspotsRequest | None = None):
    """抓热榜 + 按赛道分类，返回 {track_key: {name, items: [...]}}，未命中任何赛道的热点放在 unclassified。
    命中已开启赛道的热点全部列出，不做每赛道篇数限制；最终写几篇由用户在选题筛选页勾选决定。"""
    settings = load_settings()
    hconf = settings.get("hotspot", {})
    req = req or HotspotsRequest()

    sources = req.sources if req.sources is not None else hconf.get("sources", ["baidu"])
    top_n = req.top_n if req.top_n is not None else hconf.get("top_n", 30)
    provider = req.provider if req.provider is not None else hconf.get("provider", "official")
    base_url = req.base_url if req.base_url is not None else hconf.get("base_url", "")

    items = fetch_all(base_url, sources, top_n, provider=provider)
    tracks = enabled_tracks()
    if req.enabled_tracks is not None:
        tracks = {k: v for k, v in tracks.items() if k in req.enabled_tracks}

    grouped: dict[str, dict] = {}
    unclassified = []
    for item in items:
        hit = classify(item, tracks)
        entry = {"title": item.title, "sources": item.sources or [item.source], "url": item.url,
                 "hot": item.hot}
        if not hit:
            unclassified.append(entry)
            continue
        if store.is_processed(item.title):   # 6小时内写过稿的选题不再列出（超窗可重新采集）
            continue
        track_key, track_conf = hit
        bucket = grouped.setdefault(track_key, {"name": track_conf["name"], "items": []})
        bucket["items"].append(entry)

    # 分组按持久化的赛道顺序输出（JSON 保序，前端按此渲染）
    grouped = {k: grouped[k] for k in ordered_track_keys(grouped)}
    return {"total": len(items), "tracks": grouped, "unclassified": unclassified}


class GenerateItem(BaseModel):
    title: str
    source: str = ""
    url: str | None = None
    track_key: str


class GenerateRequest(BaseModel):
    items: list[GenerateItem]


@app.post("/generate")
def generate_articles(req: GenerateRequest):
    """按用户勾选的热点逐条出稿：数量=勾选数量，不做均衡限额。
    每条：search_results → build_material → write → scrape_cover/pick_cover → save_article("未发")。
    单条失败不影响其它条，失败原因放在该条的 error 里。"""
    settings = load_settings()
    hconf = settings.get("hotspot", {})
    iconf = settings.get("image", {})
    rconf = settings.get("research", {})
    research_providers = rconf.get("providers") or []   # 兜底链；空则退回单一 provider（兼容旧配置）
    research_provider = rconf.get("provider", "tavily")
    research_count = hconf.get("research_count", 5)
    skip_img_tracks = set(iconf.get("skip_tracks", []))
    img_mode = iconf.get("mode", "scrape")

    tracks = enabled_tracks()
    results = []
    for item in req.items:
        track_conf = tracks.get(item.track_key)
        if not track_conf:
            results.append({"ok": False, "title": item.title, "error": f"赛道『{item.track_key}』未启用或不存在"})
            continue
        try:
            if research_providers:
                search_res, used_provider = search_with_fallback(
                    item.title, count=research_count, providers=research_providers,
                    min_results=rconf.get("min_results", 3), min_chars=rconf.get("min_chars", 300))
                print(f"  🔍 [{item.title[:20]}] 素材来源：{used_provider}（{len(search_res)}条）")
            else:
                search_res = search_results(item.title, count=research_count, provider=research_provider)
            material = build_material(search_res)
            article = write(item.title, track_conf["prompt"], material=material)
        except Exception as e:
            results.append({"ok": False, "title": item.title, "error": str(e)})
            continue

        img_candidates, image_idx = None, None
        if track_conf["name"] in skip_img_tracks:
            image_rel = None
        elif img_mode == "scrape":
            urls = [r.get("url") for r in search_res if r.get("url")]
            image_rel, pool, idx = scrape_cover_pool(urls, article.title)
            if pool:
                img_candidates = json.dumps(pool, ensure_ascii=False)
                image_idx = idx if idx >= 0 else None
        else:
            image_rel = pick_cover(article.title, article.content)

        art_item = {
            "title": article.title, "body": article.content, "image": image_rel,
            "track": track_conf["name"], "source": item.source,
            "img_candidates": img_candidates, "image_idx": image_idx,
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        status = _apply_qc(art_item)
        store.save_article(art_item, status)
        store.mark_topic_processed(item.title)   # 记录热点选题+时间戳（6小时窗口去重用；手动/自动共用此入口）
        results.append({"ok": True, "id": _aid(art_item["title"]), "status": status, **art_item})

    return {"results": results}


class RecheckRequest(BaseModel):
    id: str


@app.post("/recheck")
def recheck_article(req: RecheckRequest):
    """按稿件 id 重新质检：更新该稿 qc_* 与 status（red→待修复，其余→未发）。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == req.id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")

    status = _apply_qc(art)
    art["time"] = art.get("created_at")  # 保留原创建时间（save_article 按 title 的 md5 覆盖同一行）
    store.save_article(art, status)
    return {"id": req.id, "title": art["title"], "status": status,
            "qc_score": art["qc_score"], "qc_level": art["qc_level"],
            "qc_problems": json.loads(art["qc_problems"])}


@app.get("/articles")
def get_articles(limit: int = 500):
    """取稿件库里的稿件（新→旧）。"""
    return {"articles": store.all_articles(limit=limit)}


class StatusRequest(BaseModel):
    status: str


@app.post("/articles/{article_id}/status")
def set_article_status(article_id: str, req: StatusRequest):
    """手动流转稿件状态（同步进草稿箱后去平台发布，FlowX 感知不到，靠用户点「标记已发」）。
    只改 status（复用 store.set_status 的 UPDATE），不触发重检、不动任何其它字段。"""
    if req.status not in ("已发", "未发"):
        raise HTTPException(status_code=400, detail="status 只接受「已发」或「未发」")
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == article_id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")
    store.set_status(art["title"], req.status)
    return {"ok": True, "id": article_id, "status": req.status}


# ================= 文章预览页（只读）：干净的独立文章页，供 Wechatsync 等扩展提取同步 =================
_ARTICLE_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body{{margin:0;background:#fff;color:#222;font:17px/1.9 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}}
  article{{max-width:680px;margin:0 auto;padding:48px 24px 80px}}
  h1{{font-size:26px;line-height:1.4;margin:0 0 28px}}
  p{{margin:0 0 22px}}
  img{{max-width:100%;height:auto;display:block;margin:0 auto 26px;border-radius:4px}}
</style>
</head>
<body>
<article>
<h1>{title}</h1>
{image}
{paras}
</article>
</body>
</html>"""


def _article_html(art: dict, img_prefix: str = "") -> str:
    """稿件 → 干净文章页 HTML：h1 标题 + 首图 + 每段 <p>。
    img_prefix：/article 页用空（同源相对路径）；/sync 走 CLI 时传完整 base URL（扩展才抓得到图）。"""
    esc = html_escape_mod.escape
    title = esc(art["title"])
    paras = "\n".join(f"<p>{esc(p.strip())}</p>"
                      for p in (art.get("body") or "").split("\n") if p.strip())
    image = f'<img src="{img_prefix}/output/{esc(art["image"])}" alt="{title}">' if art.get("image") else ""
    return _ARTICLE_PAGE.format(title=title, image=image, paras=paras)


@app.get("/article/{article_id}", response_class=HTMLResponse)
def article_preview(article_id: str):
    """按 id 渲染一篇干净的文章页。只读，不改任何数据。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == article_id), None)
    if not art:
        return HTMLResponse(
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><title>404</title></head>"
            "<body style='font-family:sans-serif;padding:60px;text-align:center'>"
            "<h1>404</h1><p>稿件不存在或已被删除</p></body></html>", status_code=404)
    return HTMLResponse(_article_html(art))


# ================= 路2：后端调 wechatsync CLI 自动发布（借浏览器扩展登录态，发进各平台草稿箱）=================
# CLI 是 nvm 装的，uvicorn 的 PATH 里通常没有 → 必须绝对路径；路径可用 WECHATSYNC_CLI_PATH 覆盖
_WECHATSYNC_CLI_DEFAULT = "/Users/hans.pan/.nvm/versions/node/v20.20.2/bin/wechatsync"


def _wechatsync_cli() -> str:
    return os.environ.get("WECHATSYNC_CLI_PATH") or _WECHATSYNC_CLI_DEFAULT


def _parse_sync_output(out: str, platforms: list[str]) -> list[dict]:
    """从 CLI 输出解析每个平台的结果（如「✓ toutiao (草稿) https://...」）。
    解析不出的标 unknown，前端会展示原始输出兜底。"""
    results = []
    for p in platforms:
        status, url = "unknown", None
        for line in out.splitlines():
            if p not in line:
                continue
            low = line.lower()
            failed = ("✗" in line or "×" in line or "失败" in line
                      or "fail" in low or "error" in low)
            m = re.search(r"https?://\S+", line)
            if failed:
                status = "fail"
                break
            if "✓" in line or "成功" in line or "success" in low or m:
                status = "ok"
                if m:
                    url = m.group(0).rstrip(".,;)]』」》")
                break
        results.append({"platform": p, "status": status, "url": url})
    return results


def _sync_article_via_cli(art: dict, platforms: list[str], base_url: str,
                          with_cover: bool = False) -> dict:
    """CLI 发草稿内核（/sync 接口与自动流水线共用）：
    稿件 → 临时 HTML（图片完整URL）→ wechatsync CLI → 解析各平台结果。
    token 只进子进程环境，不回前端、不进日志。"""
    token = os.environ.get("WECHATSYNC_TOKEN", "")
    if not token:
        return {"ok": False, "error": "未配置 WECHATSYNC_TOKEN（请填入 .env）", "raw": ""}
    cli = _wechatsync_cli()
    if not os.path.exists(cli):
        return {"ok": False, "error": f"wechatsync CLI 不存在：{cli}（可用 WECHATSYNC_CLI_PATH 环境变量指定）", "raw": ""}

    aid = _aid(art["title"])
    tmp_path = os.path.join(tempfile.gettempdir(), f"flowx_sync_{aid}.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(_article_html(art, img_prefix=base_url))

    # 子进程环境：PATH 追加 node bin 目录（CLI 内部要找 node）+ token
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(cli) + os.pathsep + env.get("PATH", "")
    env["WECHATSYNC_TOKEN"] = token

    cmd = [cli, "sync", tmp_path, "-p", ",".join(platforms)]
    if with_cover and art.get("image"):
        cmd += ["--cover", f"{base_url}/output/{art['image']}"]

    def _run(c):
        return subprocess.run(c, env=env, capture_output=True, text=True, timeout=120)

    print(f"  ⚡ CLI 发草稿《{art['title'][:24]}》 -> {','.join(platforms)}"
          f"{'（带 --cover）' if '--cover' in cmd else ''}")   # 不打印 env/token
    try:
        proc = _run(cmd)
        # 旧版 CLI 可能不认 --cover：报 unknown option 就去掉重试一次
        if with_cover and proc.returncode != 0 and "unknown option" in ((proc.stderr or "") + (proc.stdout or "")).lower():
            print("    CLI 不认 --cover，去掉重试（草稿封面将不设置）")
            proc = _run([cli, "sync", tmp_path, "-p", ",".join(platforms)])
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "CLI 执行超时（120秒），可改用「🚀 同步发布」手动同步", "raw": ""}
    except Exception as e:
        return {"ok": False, "error": f"CLI 调用失败：{e}", "raw": ""}

    raw = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
    raw = raw.replace(token, "***")           # 原始输出兜底展示前先抹掉 token
    results = _parse_sync_output(proc.stdout or "", platforms)
    if proc.returncode != 0 and not any(r["status"] == "ok" for r in results):
        return {"ok": False, "error": f"CLI 退出码 {proc.returncode}", "results": results, "raw": raw[-2000:]}
    return {"ok": True, "results": results, "raw": raw[-2000:]}


class SyncRequest(BaseModel):
    id: str
    platforms: list[str]


@app.post("/sync")
def sync_article(req: SyncRequest, request: Request):
    """稿件 → wechatsync CLI 发进所选平台草稿箱（不改稿件 status，草稿不算已发）。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == req.id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")
    platforms = [p.strip() for p in req.platforms if p and p.strip()]
    if not platforms:
        raise HTTPException(status_code=400, detail="至少选择一个平台")
    return _sync_article_via_cli(art, platforms, str(request.base_url).rstrip("/"))


# ================= 自动流水线：定时 选题→生成→质检→筛档→CLI进草稿箱（无人值守）=================
# ⚠️ CLI 借浏览器扩展登录态发草稿：自动任务运行时需 浏览器 + Wechatsync 扩展 开着
AUTO_RUNS_LOG = "logs/auto_runs.jsonl"
_SELF_BASE = os.environ.get("FLOWX_BASE_URL", "http://127.0.0.1:8000")  # 扩展抓图要能访问到本服务


def _append_auto_run(record: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        with open(AUTO_RUNS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"  ⚠️ 自动流水线记录写入失败：{e}")


def run_auto_pipeline(trigger: str = "manual", overrides: dict | None = None) -> dict:
    """编排层：串现有引擎（fetch_all/classify → generate_articles → 质量闸 → CLI草稿）。
    整体 try/except，单篇失败不影响整批、不崩服务；每轮写一条 jsonl 运行记录。"""
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    settings = load_settings()
    auto = {**settings.get("auto", {}), **(overrides or {})}
    record: dict = {"time": started, "trigger": trigger, "ok": True}

    if trigger == "schedule" and not auto.get("enabled"):
        record.update(ok=False, skipped="auto.enabled=false，本轮跳过")
        print("  ⏰ 自动流水线：auto.enabled=false，跳过本轮")
        _append_auto_run(record)
        return record

    try:
        # 1) 选题：现有抓取+归类；auto.tracks 非空则只留这些赛道；跳过已写过的选题
        hconf = settings.get("hotspot", {})
        items = fetch_all(hconf.get("base_url", ""), hconf.get("sources", ["baidu"]),
                          hconf.get("top_n", 30), provider=hconf.get("provider", "official"))
        tracks = enabled_tracks()
        want = auto.get("tracks") or []
        if want:
            tracks = {k: v for k, v in tracks.items() if k in want}
        count = max(1, int(auto.get("count", 3)))
        picked = []
        for it in items:
            hit = classify(it, tracks)
            if not hit or store.is_processed(it.title):
                continue
            picked.append((it, hit[0]))
            if len(picked) >= count:
                break
        record["picked"] = [{"title": it.title, "track": tk,
                             "sources": it.sources or [it.source], "hot": it.hot}
                            for it, tk in picked]
        print(f"  ⏰ 自动流水线（{trigger}）：选题 {len(picked)}/{count} 条")
        if not picked:
            record["summary"] = "没有可写的新选题（命中赛道的都已写过），本轮结束"
            _append_auto_run(record)
            return record

        # 2+3) 生成+质检+入库：直接复用 /generate 处理函数（搜索兜底/配图池/质检/红档拦截全都在）
        src_name = dict(ALL_HOT_SOURCES)   # 来源码→中文（与前端 srcLabel 一致）
        gen_items = [GenerateItem(
            title=it.title,
            source="、".join(src_name.get(s, s) for s in (it.sources or [it.source])),
            url=it.url or "", track_key=tk) for it, tk in picked]
        results = generate_articles(GenerateRequest(items=gen_items))["results"]
        gen_ok = [r for r in results if r.get("ok")]
        record["generated"] = [
            ({"id": r.get("id"), "title": r.get("title"), "status": r.get("status"),
              "qc": f"{r.get('qc_score')}/{r.get('qc_level')}"} if r.get("ok")
             else {"title": r.get("title"), "error": r.get("error")}) for r in results]

        # 4) 质量闸：green 只留绿档；green+yellow 留绿黄；红档一律不进草稿
        min_level = str(auto.get("min_level", "green"))
        allowed = {"green"} if min_level == "green" else {"green", "yellow"}
        passed = [r for r in gen_ok if r.get("qc_level") in allowed]

        # 5) CLI 发草稿（带 --cover 顺带再验一次草稿封面）
        platforms = auto.get("platforms") or ["toutiao"]
        drafts = []
        for r in passed:
            try:
                res = _sync_article_via_cli(r, platforms, _SELF_BASE, with_cover=True)
            except Exception as e:
                res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            drafts.append({"id": r.get("id"), "title": r.get("title"), "ok": res.get("ok"),
                           "results": res.get("results"), "error": res.get("error"),
                           "raw_tail": (res.get("raw") or "")[-300:]})   # 留CLI输出尾部便于查封面/链接
        record["drafts"] = drafts

        # ── 第二层预留：真发布开关（占位，不接任何真发布动作）──
        if auto.get("auto_publish"):
            note = "auto_publish=true：真发布开关已开，但真发布功能待实现——请手动去平台后台发布"
            print(f"  ⚠️ {note}")
            record["auto_publish_note"] = note

        n_draft_ok = sum(1 for d in drafts
                         if d["ok"] and any(x.get("status") == "ok" for x in (d.get("results") or [])))
        record["summary"] = (f"选题{len(picked)} → 生成成功{len(gen_ok)} → "
                             f"过质量闸({min_level}){len(passed)} → 草稿成功{n_draft_ok}")
        print(f"  ⏰ 自动流水线完成：{record['summary']}")
    except Exception as e:
        record.update(ok=False, error=f"{type(e).__name__}: {e}")
        print(f"  ⚠️ 自动流水线异常终止：{e}")
    _append_auto_run(record)
    return record


class AutoRunRequest(BaseModel):
    count: int | None = None
    min_level: str | None = None
    platforms: list[str] | None = None
    auto_publish: bool | None = None


@app.post("/auto/run")
def auto_run(req: AutoRunRequest | None = None):
    """手动触发一轮自动流水线（忽略 enabled 总开关；可传覆盖参数用于测试）。"""
    overrides = {k: v for k, v in (req.model_dump() if req else {}).items() if v is not None}
    return run_auto_pipeline("manual", overrides)


@app.get("/auto/runs")
def auto_runs(limit: int = 10):
    """查最近的自动流水线运行记录（新→旧）。"""
    if not os.path.exists(AUTO_RUNS_LOG):
        return {"runs": []}
    try:
        lines = [l for l in open(AUTO_RUNS_LOG, encoding="utf-8").read().splitlines() if l.strip()]
        return {"runs": [json.loads(l) for l in reversed(lines[-limit:])]}
    except Exception as e:
        return {"runs": [], "error": str(e)}


@app.on_event("startup")
def _start_auto_scheduler():
    """服务启动时注册每日定时 job。enabled 在每轮运行时现读（开关即改即生效）；改 schedule 需重启。"""
    auto = load_settings().get("auto", {})
    sched = str(auto.get("schedule", "")).strip()
    if not sched:
        return
    try:
        hh, mm = sched.split(":")
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        scheduler = BackgroundScheduler()
        scheduler.add_job(lambda: run_auto_pipeline("schedule"),
                          CronTrigger(hour=int(hh), minute=int(mm)),
                          id="auto_pipeline", misfire_grace_time=3600)
        scheduler.start()
        app.state.auto_scheduler = scheduler
        print(f"  ⏰ 自动流水线定时已注册：每天 {sched}（enabled={auto.get('enabled')}，运行时现读；需浏览器+Wechatsync扩展开着）")
    except Exception as e:
        print(f"  ⚠️ 自动流水线定时注册失败（不影响其它功能）：{e}")


# ================= 设置读写（key 绝不经接口读写，只返回是否已配的 bool）=================
ALL_HOT_SOURCES = [("baidu", "百度"), ("toutiao", "今日头条"), ("douyin", "抖音"), ("weibo", "微博"),
                   ("zhihu", "知乎"), ("bilibili", "B站"), ("36kr", "36氪"), ("thepaper", "澎湃")]
_DIRECT_SOURCES = {"baidu", "toutiao"}  # 官方直抓，不依赖聚合服务


def _key_configured(env_name: str) -> bool:
    """key 是否已配置：非空且不是中文占位符。只返回 bool，绝不返回 key 值。"""
    v = os.environ.get(env_name, "")
    return bool(v) and v.isascii()


@app.get("/settings")
def get_app_settings():
    s = load_settings()
    h = s.get("hotspot", {})
    r = s.get("research", {})
    base_url = h.get("base_url", "")

    dailyhot = "offline"
    if base_url:
        try:  # 通了就算在线（个别源上游 500 是另一回事）
            requests.get(f"{base_url.rstrip('/')}/douyin", timeout=1)
            dailyhot = "online"
        except Exception:
            dailyhot = "offline"

    all_tracks = load_tracks()
    tracks = [{"key": k, "name": all_tracks[k].get("name", k),
               "enabled": bool(all_tracks[k].get("enabled")),
               "keywords": all_tracks[k].get("keywords", [])}
              for k in ordered_track_keys(all_tracks)]   # 按持久化顺序返回（芯片/设置页共用）

    auto = s.get("auto", {})
    last_run = None
    try:
        if os.path.exists(AUTO_RUNS_LOG):
            lines = [l for l in open(AUTO_RUNS_LOG, encoding="utf-8").read().splitlines() if l.strip()]
            if lines:
                lr = json.loads(lines[-1])
                last_run = {k: lr.get(k) for k in ("time", "trigger", "ok", "summary", "skipped", "error")}
    except Exception:
        pass
    return {
        "auto": {
            "enabled": bool(auto.get("enabled")),
            "schedule": auto.get("schedule", ""),
            "count": auto.get("count", 3),
            "min_level": auto.get("min_level", "green"),
            "tracks": auto.get("tracks") or [],
            "platforms": auto.get("platforms") or ["toutiao"],
            "auto_publish": bool(auto.get("auto_publish")),
            "last_run": last_run,
        },
        "hotspot": {
            "sources": h.get("sources", []),
            "base_url": base_url,
            "all_sources": [{"code": c, "name": n, "direct": c in _DIRECT_SOURCES}
                            for c, n in ALL_HOT_SOURCES],
        },
        "research": {
            "providers": r.get("providers") or [r.get("provider", "tavily")],
            "min_results": r.get("min_results", 3),
            "min_chars": r.get("min_chars", 300),
            "keys": {"tavily": _key_configured("TAVILY_API_KEY"),
                     "bocha": _key_configured("BOCHA_API_KEY")},
        },
        "tracks": tracks,
        "services": {"dailyhot": dailyhot},
    }


class SourcesRequest(BaseModel):
    sources: list[str]


@app.post("/settings/sources")
def post_settings_sources(req: SourcesRequest):
    """写回启用的热点来源（只改 settings.yaml 的 hotspot.sources，按固定顺序保序）。"""
    valid = [c for c, _ in ALL_HOT_SOURCES]
    sources = sorted({s for s in req.sources if s in valid}, key=valid.index)
    if not sources:
        raise HTTPException(status_code=400, detail="至少保留一个热点来源")
    set_hotspot_sources(sources)
    return {"ok": True, "sources": sources}


class TrackOrderRequest(BaseModel):
    order: list[str]


@app.post("/settings/track-order")
def post_settings_track_order(req: TrackOrderRequest):
    """写回赛道显示顺序：过滤未知 key，未提及的赛道按现有顺序补在后面。"""
    tracks = load_tracks()
    keys = [k for k in req.order if k in tracks]
    if not keys:
        raise HTTPException(status_code=400, detail="顺序里没有有效的赛道 key")
    keys += [k for k in ordered_track_keys(tracks) if k not in keys]
    set_track_order(keys)
    return {"ok": True, "order": keys}


class ResearchThresholdsRequest(BaseModel):
    min_results: int
    min_chars: int


@app.post("/settings/research")
def post_settings_research(req: ResearchThresholdsRequest):
    """写回搜索兜底链阈值。越界钳制到合理范围（min_results 1~10、min_chars 100~1500）。"""
    mr = max(1, min(10, req.min_results))
    mc = max(100, min(1500, req.min_chars))
    set_research_thresholds(mr, mc)
    return {"ok": True, "min_results": mr, "min_chars": mc}


class TrackToggleRequest(BaseModel):
    key: str
    enabled: bool


@app.post("/settings/tracks")
def post_settings_tracks(req: TrackToggleRequest):
    """改 tracks.yaml 里某赛道的 enabled（只改开关，不动 keywords/prompt）。"""
    if req.key not in load_tracks():
        raise HTTPException(status_code=404, detail=f"赛道 {req.key} 不存在")
    set_track_enabled(req.key, req.enabled)
    return {"ok": True, "key": req.key, "enabled": req.enabled}


class ReviseRequest(BaseModel):
    id: str


@app.post("/revise")
def revise_article(req: ReviseRequest):
    """一键定向优化：按稿件已存的质检问题清单二次修订 → 重新质检 → 入库。
    标题变了 id 跟着变（id=md5(title)）：先存新行、再删旧行，是"移动"不是"复制"。
    revise 失败则原稿原样保留，只返回 ok:false。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == req.id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")

    try:
        problems = json.loads(art.get("qc_problems") or "[]")
    except Exception:
        problems = []
    before = {"qc_score": art.get("qc_score"), "qc_level": art.get("qc_level")}

    try:
        revised = revise(art, problems)
    except Exception as e:
        return {"ok": False, "error": f"优化失败，原稿保留：{e}"}

    new_item = {
        "title": revised.title, "body": revised.content, "image": art.get("image"),
        "track": art.get("track", ""), "source": art.get("source", ""),
        "img_candidates": art.get("img_candidates"), "image_idx": art.get("image_idx"),  # 保住换图候选池
        "time": art.get("created_at"),  # 沿用原创建时间
    }
    status = _apply_qc(new_item)
    store.save_article(new_item, status)
    new_id = _aid(new_item["title"])
    if new_id != req.id:
        store.delete_article(req.id)
    return {"ok": True, "id": new_id, "status": status, "before": before, **new_item}


class ReimageRequest(BaseModel):
    id: str


@app.post("/reimage")
def reimage_article(req: ReimageRequest):
    """一键换图：取该稿候选池里下一张有效报道图；候选用尽退回 Pexels。
    只换 image / image_idx，其它字段（qc_*、status、created_at）原样保留，不触发重新质检。
    失败 {ok:false} 且不动原稿。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == req.id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")

    try:
        pool = json.loads(art.get("img_candidates") or "[]")
    except Exception:
        pool = []
    idx = art.get("image_idx")
    idx = -1 if idx is None else int(idx)

    def _save_with(image_rel: str, new_idx: int, source: str):
        art["image"], art["image_idx"] = image_rel, new_idx
        art["img_candidates"] = json.dumps(pool, ensure_ascii=False) if pool else None
        art["time"] = art.get("created_at")
        store.save_article(art, art["status"])
        return {"ok": True, "id": req.id, "image": image_rel, "source": source, "idx": new_idx}

    # 依次试候选池里下一张
    for i in range(idx + 1, len(pool)):
        data = download_valid_image(pool[i])
        if data:
            rel = save_image_bytes(data, art["title"] + pool[i])
            return _save_with(rel, i, "report")

    # 候选用尽 → Pexels 兜底
    rel = pick_cover(art["title"], art.get("body") or "")
    if rel:
        return _save_with(rel, len(pool), "pexels")
    return {"ok": False, "error": "候选报道图已用尽，Pexels 兜底也没出图（检查 PEXELS_API_KEY），原图保留"}


class PublishRequest(BaseModel):
    id: str
    account: str | None = None


@app.post("/publish")
def publish_article(req: PublishRequest):
    """按稿件 id 找到稿件 -> get_publisher(account).publish() -> 成功则 set_status("已发")。
    前提：该账号 profile 已用 login.py 登录过，否则 publisher 会返回未登录的失败信息。"""
    art = next((a for a in store.all_articles(limit=1000) if a["id"] == req.id), None)
    if not art:
        raise HTTPException(status_code=404, detail="稿件不存在")

    account_name = req.account or load_settings().get("pipeline", {}).get("account", "hans_toutiao")
    account = get_account(account_name)
    pub = get_publisher(account)

    img = art.get("image")
    cover = os.path.join("output", img) if img else None
    article = Article(title=art["title"], content=art["body"], cover_image=cover)

    result = pub.publish(article)
    if result.ok:
        store.set_status(art["title"], "已发")
    return {"ok": result.ok, "url": result.url, "error": result.error}


# 配图（store 里存的是相对 output/ 的路径，如 images/xxx.jpg）
app.mount("/output", StaticFiles(directory="output"), name="output")
# 前端静态页面，挂载在最后，避免遮蔽上面的 /hotspots /articles 接口
app.mount("/", StaticFiles(directory="static", html=True), name="static")
