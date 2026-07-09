"""
fetch.py —— 抓热榜（百度热搜 + 今日头条热榜，官方接口，免Docker免第三方）

经实测：微博/知乎官方接口需登录态抓不了；百度、头条官方接口可直接抓。
在 settings.yaml 的 hotspot.sources 里控制抓哪些：baidu / toutiao。
"""
from __future__ import annotations

from dataclasses import dataclass
import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

BAIDU_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
TOUTIAO_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"


@dataclass
class HotItem:
    title: str
    source: str
    url: str | None = None


def _baidu_row_title(row: dict):
    return (row.get("word") or row.get("query") or row.get("title") or "").strip()


def _fetch_baidu(top_n: int) -> list[HotItem]:
    try:
        r = requests.get(BAIDU_URL, headers=UA, timeout=10)
        r.raise_for_status()
        cards = r.json().get("data", {}).get("cards", [])
    except Exception as e:
        print(f"  ⚠️ 抓百度热搜失败：{e}")
        return []
    items, seen = [], set()
    # 遍历所有卡片、兼容内容再嵌一层的情况
    for card in cards:
        for row in card.get("content", []) or []:
            candidates = [row] + (row.get("content", []) if isinstance(row.get("content"), list) else [])
            for c in candidates:
                if not isinstance(c, dict):
                    continue
                title = _baidu_row_title(c)
                if title and title not in seen:
                    seen.add(title)
                    items.append(HotItem(title=title, source="baidu",
                                         url=c.get("url") or c.get("rawUrl")))
    return items[:top_n]


def _fetch_toutiao(top_n: int) -> list[HotItem]:
    try:
        r = requests.get(TOUTIAO_URL, headers=UA, timeout=10)
        r.raise_for_status()
        rows = r.json().get("data", [])
    except Exception as e:
        print(f"  ⚠️ 抓头条热榜失败：{e}")
        return []
    items = []
    for row in rows[:top_n]:
        title = (row.get("Title") or row.get("title") or "").strip()
        if title:
            items.append(HotItem(title=title, source="toutiao", url=row.get("Url") or row.get("url")))
    return items


_FETCHERS = {"baidu": _fetch_baidu, "toutiao": _fetch_toutiao}


def fetch_all(base_url: str, sources: list[str], top_n=30, provider: str = "official") -> list[HotItem]:
    """按 sources 抓热榜并按标题去重。当前支持：baidu, toutiao。
    top_n 可为 int（各源统一条数）或 dict（按源分别设，如 {baidu:40, toutiao:10}）。"""
    raw: list[HotItem] = []
    for src in sources:
        fetcher = _FETCHERS.get(src)
        if not fetcher:
            print(f"  ⚠️ 暂不支持的源『{src}』（当前可用：baidu, toutiao），跳过")
            continue
        n = top_n.get(src, 30) if isinstance(top_n, dict) else top_n
        raw.extend(fetcher(n))

    seen, merged = set(), []
    for it in raw:
        if it.title not in seen:
            seen.add(it.title)
            merged.append(it)
    got = {}
    for it in merged:
        got[it.source] = got.get(it.source, 0) + 1
    print(f"  共抓到 {len(merged)} 条去重热点（{', '.join(f'{k}:{v}' for k,v in got.items()) or '无'}）")
    return merged
