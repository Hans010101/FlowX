"""
fetch.py —— 抓热榜：baidu/toutiao 官方接口原生直抓 + 其余源走本机 DailyHotApi 聚合（混合可降级）

- baidu / toutiao：官方接口直抓（免 Docker 免第三方），DailyHotApi 挂了也能用。
- 其它源（douyin/weibo/zhihu/bilibili/36kr/thepaper…）：调 settings.hotspot.base_url 指向的
  DailyHotApi（imsyy/DailyHotApi，默认 http://127.0.0.1:6688），路径即调用名：GET {base_url}/{source}。
  以后加平台 = 往 settings.hotspot.sources 加一个 DailyHotApi 调用名，不改代码。
在 settings.yaml 的 hotspot.sources 里控制抓哪些。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import requests

# 跨平台同话题模糊合并阈值（规范化标题相似度 ≥ 此值判同话题；误合多则调高，漏合多则调低）
SIM_THRESHOLD = 0.82

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

BAIDU_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
TOUTIAO_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"


@dataclass
class HotItem:
    title: str
    source: str                                   # 代表来源（兼容旧用法，= sources[0]）
    url: str | None = None                        # 主链接（第一个非空）
    sources: list[str] = field(default_factory=list)  # 合并后的全部来源码，如 ["baidu","toutiao"]
    urls: list[str] = field(default_factory=list)     # 合并后的去重链接列表


# 规范化标题：去表情、去常见标点、去空白（中文标题里空白只是分隔，直接去掉匹配更准）
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")
_PUNCT_RE = re.compile(r"[，。！？；：、“”‘’\"'《》〈〉（）()【】\[\]｛｝{}·…‥,.!?;:~～—\-–|｜#@\s]+")


def _norm_title(s: str) -> str:
    return _PUNCT_RE.sub("", _EMOJI_RE.sub("", (s or "").strip()))


def _same_topic(a: str, b: str) -> bool:
    """规范化标题相等 / 一方包含另一方 / 相似度 ≥ SIM_THRESHOLD，任一命中即同话题。"""
    if a == b or a in b or b in a:
        return True
    sm = SequenceMatcher(None, a, b)
    return sm.real_quick_ratio() >= SIM_THRESHOLD and sm.ratio() >= SIM_THRESHOLD


def _merge_items(raw: list[HotItem]) -> list[HotItem]:
    """跨平台同话题分组合并：代表标题取组内最长；sources/urls 去重保序；按首次出现顺序输出。"""
    groups: list[dict] = []   # {"norms": [规范化标题...], "items": [HotItem...]}
    for it in raw:
        norm = _norm_title(it.title) or it.title.strip()
        if not norm:
            continue
        hit = next((g for g in groups if any(_same_topic(norm, n) for n in g["norms"])), None)
        if hit:
            hit["norms"].append(norm)
            hit["items"].append(it)
        else:
            groups.append({"norms": [norm], "items": [it]})

    merged = []
    for g in groups:
        items = g["items"]
        rep = max(items, key=lambda x: len(x.title))
        sources = list(dict.fromkeys(x.source for x in items))
        urls = list(dict.fromkeys(x.url for x in items if x.url))
        if len(items) > 1:
            print(f"  ↳ 合并 {len(items)} 条同话题（{'/'.join(sources)}）：{rep.title[:36]}")
        merged.append(HotItem(title=rep.title, source=sources[0], url=urls[0] if urls else None,
                              sources=sources, urls=urls))
    return merged


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


def _fetch_dailyhot(base_url: str, source: str, top_n: int) -> list[HotItem]:
    """通用聚合 fetcher：GET {base_url}/{source}（DailyHotApi）。
    实测返回 {code:200, total, data:[{id,title,timestamp,hot,url,mobileUrl}]}。
    失败（服务没起/超时/结构不符）返回 []，不抛异常。"""
    try:
        r = requests.get(f"{base_url.rstrip('/')}/{source}", headers=UA, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data") or []
        if not isinstance(rows, list):
            raise ValueError(f"data 不是数组（code={data.get('code')}）")
    except Exception as e:
        print(f"  ⚠️ 聚合源『{source}』抓取失败（DailyHotApi {base_url}）：{e}")
        return []
    items = []
    for row in rows[:top_n]:
        title = str(row.get("title") or "").strip()
        if title:
            items.append(HotItem(title=title, source=source,
                                 url=row.get("url") or row.get("mobileUrl")))
    return items


_FETCHERS = {"baidu": _fetch_baidu, "toutiao": _fetch_toutiao}


def fetch_all(base_url: str, sources: list[str], top_n=30, provider: str = "official") -> list[HotItem]:
    """按 sources 抓热榜并做跨平台同话题合并：baidu/toutiao 走原生直抓，
    其余源在 base_url 非空时走 DailyHotApi 聚合，否则警告跳过。
    同话题（规范化标题相等/包含/相似度≥SIM_THRESHOLD）合并为一条，sources 标注全部命中平台。
    top_n 可为 int（各源统一条数）或 dict（按源分别设，如 {baidu:40, toutiao:10}，未列到默认30）。"""
    raw: list[HotItem] = []
    for src in sources:
        n = top_n.get(src, 30) if isinstance(top_n, dict) else top_n
        fetcher = _FETCHERS.get(src)
        if fetcher:
            raw.extend(fetcher(n))
        elif base_url:
            raw.extend(_fetch_dailyhot(base_url, src, n))
        else:
            print(f"  ⚠️ 暂不支持的源『{src}』（原生支持 baidu/toutiao；其它源需在 settings 配 hotspot.base_url 指向 DailyHotApi），跳过")
            continue

    merged = _merge_items(raw)
    got = {}
    for it in merged:
        for s in (it.sources or [it.source]):
            got[s] = got.get(s, 0) + 1
    print(f"  原始 {len(raw)} 条 → 合并后 {len(merged)} 条话题"
          f"（平台命中 {', '.join(f'{k}:{v}' for k, v in got.items()) or '无'}）")
    return merged
