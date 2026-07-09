#!/usr/bin/env python3
"""
run_daily.py —— 每日流水线（定时入口）

流程：抓热榜 → 按赛道筛选 → 各赛道均衡轮流选题(避免一类占满、同事件不重复选)
      → 搜索素材 → DeepSeek 基于素材改写 → 配封面图(体育类默认跳过) → 生成审阅网页。
mode: review=生成本地网页手动发；publish=自动发头条（以后）。
"""
from __future__ import annotations

import time
from collections import defaultdict

from config import get_account, enabled_tracks, load_settings, load_env
from hotspot import fetch_all, classify
from generate import write, pick_cover
from generate.illustrate import scrape_cover
from research import search_results, build_material
import review
import store


def _similar(a: str, b: str) -> bool:
    """两个标题是否疑似同一件事：有3字以上公共子串，或二元字组重合度高。"""
    if not a or not b:
        return False
    tri = {a[i:i+3] for i in range(len(a) - 2)}
    if any(t in b for t in tri):
        return True
    ba = {a[i:i+2] for i in range(len(a) - 1)}
    bb = {b[i:i+2] for i in range(len(b) - 1)}
    if not ba or not bb:
        return False
    return len(ba & bb) / len(ba | bb) >= 0.4


def _flag_duplicates(items: list[dict]):
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _similar(items[i]["_hot"], items[j]["_hot"]) or _similar(items[i]["title"], items[j]["title"]):
                items[i].setdefault("dup", []).append(items[j]["title"])
                items[j].setdefault("dup", []).append(items[i]["title"])


def _balanced_select(hot_items, tracks, max_per_run, quota, default_q):
    """按各赛道名额轮流选题；同事件（标题相似）不重复选。quota: {赛道名: 篇数}"""
    buckets = defaultdict(list)     # track_key -> [(item, track_conf), ...]
    name_by_key = {k: v["name"] for k, v in tracks.items()}
    for item in hot_items:
        hit = classify(item, tracks)
        if not hit:
            continue
        if store.is_processed(item.title):
            continue
        buckets[hit[0]].append((item, hit[1]))

    selected, picked_titles, counts = [], [], defaultdict(int)
    progress = True
    while len(selected) < max_per_run and progress:
        progress = False
        for tk in tracks:                       # 固定顺序轮流
            cap = quota.get(name_by_key[tk], default_q)
            if counts[tk] >= cap:
                continue
            while buckets[tk]:
                item, conf = buckets[tk].pop(0)
                if any(_similar(item.title, p) for p in picked_titles):
                    continue                     # 跳过同事件，试该赛道下一条
                selected.append((item, tk, conf))
                picked_titles.append(item.title)
                counts[tk] += 1
                progress = True
                break
            if len(selected) >= max_per_run:
                break
    return selected


def main():
    load_env()
    settings = load_settings()
    pconf = settings.get("pipeline", {})
    hconf = settings.get("hotspot", {})
    iconf = settings.get("image", {})
    mode = pconf.get("mode", "review")
    max_per_run = pconf.get("max_per_run", 8)
    quota = pconf.get("per_track_quota", {})
    default_q = pconf.get("per_track_default", 1)
    skip_img_tracks = set(iconf.get("skip_tracks", []))
    img_mode = iconf.get("mode", "scrape")

    tracks = enabled_tracks()
    print(f"=== 流水线启动 | 模式:{mode} | 名额:{quota or ('每赛道'+str(default_q))} 总≤{max_per_run} ===")

    print("→ 抓多平台热榜 ...")
    hot_items = fetch_all(hconf.get("base_url", ""), hconf.get("sources", ["baidu"]),
                          hconf.get("top_n", 30), provider=hconf.get("provider", "official"))

    selected = _balanced_select(hot_items, tracks, max_per_run, quota, default_q)
    print(f"→ 均衡选出 {len(selected)} 个选题："
          f"{', '.join(tc['name'] for _, _, tc in selected)}")

    collected = []
    for item, track_key, track_conf in selected:
        print(f"\n→ 【{track_conf['name']}】{item.title}")
        results = search_results(item.title, count=hconf.get("research_count", 5),
                                 provider=settings.get("research", {}).get("provider", "tavily"))
        material = build_material(results)
        if material:
            print(f"  搜到素材（共 {len(material)} 字）")
        try:
            article = write(item.title, track_conf["prompt"], material=material)
            print(f"  出文完成，标题：{article.title}")
        except Exception as e:
            print(f"  ✗ 出文失败：{e}")
            store.mark(item.title, track_key, item.source, "write_error")
            continue

        # 配图：默认抓报道原图（贴合内容、体育也能拿到真实赛事图）；某些赛道可配置跳过
        if track_conf["name"] in skip_img_tracks:
            image_rel = None
            print("  （该赛道跳过自动配图，请手动配）")
        elif img_mode == "scrape":
            urls = [r.get("url") for r in results if r.get("url")]
            image_rel = scrape_cover(urls, article.title)
        else:
            image_rel = pick_cover(article.title, article.content)

        art_item = {
            "title": article.title, "body": article.content, "image": image_rel,
            "track": track_conf["name"], "source": item.source,
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        store.save_article(art_item, "未发")
        collected.append(art_item)

    if mode == "publish":
        _auto_publish(collected)
    out = review.render_dashboard(store.all_articles())
    print(f"\n=== 完成 {len(collected)} 篇 | 稿件管理台：{out} ===")
    print("   双击打开 dashboard.html：所有稿件都在，可按未发/已发筛选。")


def _auto_publish(collected):
    from publishers import get_publisher, Article
    account = get_account(load_settings()["pipeline"].get("account", "hans_toutiao"))
    pub = get_publisher(account)
    import os
    for it in collected:
        img = it.get("image")
        cover = os.path.join("output", img) if img else None
        art = Article(title=it["title"], content=it["body"], cover_image=cover)
        print(f"→ 定时发布：{it['title']}")
        r = pub.publish(art)
        if r.ok:
            store.set_status(it["title"], "已发")
        print(("  ✅ 已提交定时发布：" if r.ok else "  ✗ 失败：") + (r.url or r.error or ""))


if __name__ == "__main__":
    main()
