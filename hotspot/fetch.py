"""
fetch.py —— 抓热榜：baidu/toutiao 官方接口原生直抓 + 其余源走本机 DailyHotApi 聚合（混合可降级）

- baidu / toutiao：官方接口直抓（免 Docker 免第三方），DailyHotApi 挂了也能用。
- 其它源（douyin/weibo/zhihu/bilibili/36kr/thepaper…）：调 settings.hotspot.base_url 指向的
  DailyHotApi（imsyy/DailyHotApi，默认 http://127.0.0.1:6688），路径即调用名：GET {base_url}/{source}。
  以后加平台 = 往 settings.hotspot.sources 加一个 DailyHotApi 调用名，不改代码。
在 settings.yaml 的 hotspot.sources 里控制抓哪些。
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
    """按 sources 抓热榜并按标题去重：baidu/toutiao 走原生直抓，
    其余源在 base_url 非空时走 DailyHotApi 聚合，否则警告跳过。
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
