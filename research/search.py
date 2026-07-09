"""
search.py —— 搜索热点，返回素材文本 + 报道链接（链接用于抓报道配图）

provider: tavily（免费，默认）| bocha（付费）。
search_with_fallback：按 providers 链依次尝试（tavily 优先省成本），
结果不达标（条数不足/素材太薄）自动回退下一个源。
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


def _good_enough(results: list[dict], min_results: int, min_chars: int) -> bool:
    """结果是否够好：条数和素材总字数都达标。"""
    return (len(results) >= min_results
            and sum(len(r.get("content") or "") for r in results) >= min_chars)


def search_with_fallback(query: str, count: int = 5, providers: list[str] | None = None,
                         min_results: int = 3, min_chars: int = 300) -> tuple[list[dict], str]:
    """按 providers 顺序逐个搜：第一个"够好"的立即返回（不再调后面的，省成本）；
    都不达标则返回内容最多的那次（避免返回空）。返回 (results, used_provider)。"""
    providers = [p for p in (providers or ["tavily"]) if p]
    best: list[dict] = []
    best_used = providers[0]
    for i, p in enumerate(providers):
        fn = _search_bocha if p == "bocha" else _search_tavily
        try:
            res = fn(query, count)
        except Exception as e:  # fetcher 内部已兜底，这里再保一道
            print(f"  ⚠️ 搜索源 {p} 异常：{e}")
            res = []
        chars = sum(len(r.get("content") or "") for r in res)
        if _good_enough(res, min_results, min_chars):
            print(f"  🔍 搜索命中 {p}（{len(res)}条/{chars}字），不再调后续源")
            return res, p
        reason = "条数不足" if len(res) < min_results else "素材太薄"
        nxt = f"→ 回退 {providers[i+1]}" if i + 1 < len(providers) else "（已是最后一个源）"
        print(f"  ⚠️ 搜索源 {p} {reason}（{len(res)}条/{chars}字，阈值 {min_results}条/{min_chars}字）{nxt}")
        if chars > sum(len(r.get("content") or "") for r in best):
            best, best_used = res, p
    print(f"  🔍 各源均不达标，取内容最多的一次：{best_used}（{len(best)}条）")
    return best, best_used


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
