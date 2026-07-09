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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import load_env, load_settings, enabled_tracks, get_account
from hotspot import fetch_all, classify
from generate import write, pick_cover
from generate.illustrate import scrape_cover
from research import search_results, build_material
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
        entry = {"title": item.title, "source": item.source, "url": item.url}
        if not hit:
            unclassified.append(entry)
            continue
        track_key, track_conf = hit
        bucket = grouped.setdefault(track_key, {"name": track_conf["name"], "items": []})
        bucket["items"].append(entry)

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
    research_provider = settings.get("research", {}).get("provider", "tavily")
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
            search_res = search_results(item.title, count=research_count, provider=research_provider)
            material = build_material(search_res)
            article = write(item.title, track_conf["prompt"], material=material)
        except Exception as e:
            results.append({"ok": False, "title": item.title, "error": str(e)})
            continue

        if track_conf["name"] in skip_img_tracks:
            image_rel = None
        elif img_mode == "scrape":
            urls = [r.get("url") for r in search_res if r.get("url")]
            image_rel = scrape_cover(urls, article.title)
        else:
            image_rel = pick_cover(article.title, article.content)

        art_item = {
            "title": article.title, "body": article.content, "image": image_rel,
            "track": track_conf["name"], "source": item.source,
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        status = _apply_qc(art_item)
        store.save_article(art_item, status)
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
