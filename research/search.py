"""
search.py —— 搜索热点，返回素材文本 + 报道链接（链接用于抓报道配图）

provider: tavily（免费，默认）| bocha（付费）。
"""
from __future__ import annotations

import os
import requests

TAVILY_API = "https://api.tavily.com/search"
BOCHA_API = "https://api.bochaai.com/v1/web-search"


def _search_tavily(query: str, count: int) -> list[dict]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        print("  ⚠️ 未设置 TAVILY_API_KEY，跳过搜索")
        return []
    try:
        resp = requests.post(
            TAVILY_API,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"query": query, "search_depth": "basic", "max_results": count,
                  "include_answer": False, "api_key": key},
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json().get("results", []) or []
    except Exception as e:
        print(f"  ⚠️ Tavily 搜索失败：{e}")
        return []
    return [{"title": (r.get("title") or "").strip(),
             "content": (r.get("content") or "").strip(),
             "url": r.get("url")} for r in rows[:count]]


def _search_bocha(query: str, count: int) -> list[dict]:
    key = os.environ.get("BOCHA_API_KEY")
    if not key:
        print("  ⚠️ 未设置 BOCHA_API_KEY，跳过搜索")
        return []
    try:
        resp = requests.post(
            BOCHA_API,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"query": query, "summary": True, "count": count, "freshness": "oneWeek"},
            timeout=30,
        )
        resp.raise_for_status()
        pages = (resp.json().get("data", {}) or {}).get("webPages", {}).get("value", []) or []
    except Exception as e:
        print(f"  ⚠️ 博查搜索失败：{e}")
        return []
    return [{"title": (p.get("name") or "").strip(),
             "content": (p.get("summary") or p.get("snippet") or "").strip(),
             "url": p.get("url")} for p in pages[:count]]


def search_results(query: str, count: int = 5, provider: str = "tavily") -> list[dict]:
    """返回 [{title, content, url}, ...]"""
    return _search_bocha(query, count) if provider == "bocha" else _search_tavily(query, count)


def build_material(results: list[dict]) -> str:
    """把搜索结果拼成给 DeepSeek 的素材文本。"""
    chunks = []
    for i, r in enumerate(results, 1):
        if r.get("content"):
            chunks.append(f"【素材{i}】{r.get('title','')}\n{r['content']}")
    return "\n\n".join(chunks)


def gather_material(query: str, count: int = 5, provider: str = "tavily") -> str:
    """兼容旧调用：只要素材文本。"""
    return build_material(search_results(query, count, provider))
