"""
illustrate.py —— 自动配封面图（路线B：Pexels 图库真实照片）

配图准确度策略：
1. 体育类先用"项目映射表"锁定可靠英文词（乒乓→table tennis…），保证项目对得上。
2. 其它类让 DeepSeek 给"最核心的可拍摄物体名词"（1-3词），禁止 victory/celebration 这类
   修饰词——正是它们让 Pexels 返回跑偏的人物照。
需 export PEXELS_API_KEY=你的key。配图失败返回 None，不阻断。
"""
from __future__ import annotations

import os
import pathlib
import hashlib
import requests

from .llm import chat

PEXELS_API = "https://api.pexels.com/v1/search"
UA_HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# 体育项目映射：标题里含左边词，就用右边可靠英文词（按具体→泛化排序，先匹配到先用）
SPORT_MAP = [
    ("乒乓", "table tennis"),
    ("世乒赛", "table tennis"),
    ("国乒", "table tennis"),
    ("乒联", "table tennis"),
    ("WTT", "table tennis"),
    ("男篮", "basketball game"),
    ("女篮", "basketball game"),
    ("篮球", "basketball game"),
    ("NBA", "basketball game"),
    ("CBA", "basketball game"),
    ("羽毛球", "badminton"),
    ("网球", "tennis court"),
    ("排球", "volleyball"),
    ("游泳", "swimming race"),
    ("田径", "running track athletics"),
    ("国足", "soccer football"),
    ("中超", "soccer football"),
    ("欧冠", "soccer football"),
    ("英超", "soccer football"),
    ("点球", "soccer football"),
    ("绿茵", "soccer football"),
    ("足球", "soccer football"),
    ("世界杯", "soccer football"),   # 泛化兜底放最后（篮球相关词已在上面先匹配）
    ("欧洲杯", "soccer football"),
]


def _sport_query(text: str) -> str | None:
    for kw, q in SPORT_MAP:
        if kw in text:
            return q
    return None


def english_query(title: str) -> str:
    """让 DeepSeek 给一个最核心的可拍摄物体名词（1-3词），失败回退标题。"""
    try:
        q = chat(
            [{"role": "system",
              "content": "Give the single most concrete, photographable object or subject for a "
                         "Chinese news headline, as 1-3 English words for a stock photo search. "
                         "Prefer a physical object or thing. ABSOLUTELY NO emotion or action words "
                         "(no 'celebration', 'victory', 'disappointment', 'success'). "
                         "Examples: '养老金上调' -> 'chinese money cash'; 'iPhone发布' -> 'smartphone'; "
                         "'芯片突破' -> 'computer chip'; '房价下跌' -> 'apartment buildings'; "
                         "'暴雨预警' -> 'heavy rain city'. Output ONLY the words."},
             {"role": "user", "content": title}],
            temperature=0.2, timeout=30,
        ).strip().strip('"').strip()
        return q or title
    except Exception:
        return title


def pick_cover(title: str, body: str = "", out_dir: str = "output/images") -> str | None:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        print("  ⚠️ 未设置 PEXELS_API_KEY，跳过配图")
        return None

    # 体育类优先用映射表（标题+正文一起判项目）；否则用 DeepSeek 给核心物体词
    query = _sport_query(title + " " + body[:300]) or english_query(title)
    try:
        resp = requests.get(
            PEXELS_API,
            headers={"Authorization": key},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=20,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            print(f"  ⚠️ Pexels 没搜到『{query}』的图，跳过配图")
            return None
        src = photos[0]["src"]
        img_bytes = requests.get(src.get("original") or src.get("large2x") or src["large"], timeout=30).content
    except Exception as e:
        print(f"  ⚠️ 配图失败：{e}")
        return None

    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    fn = hashlib.md5(title.encode("utf-8")).hexdigest()[:10] + ".jpg"
    with open(os.path.join(out_dir, fn), "wb") as f:
        f.write(img_bytes)
    print(f"  配图完成（搜图词：{query}）")
    return os.path.join("images", fn)


# ========== 抓报道原图（og:image）==========
import re
from urllib.parse import urljoin

_OG_PATTERNS = [
    r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
]


def _extract_og_image(html: str, base_url: str) -> str | None:
    for pat in _OG_PATTERNS:
        m = re.search(pat, html, re.I)
        if m:
            return urljoin(base_url, m.group(1).strip())
    return None


def _candidate_images(html: str, base_url: str) -> list[str]:
    """从页面提取所有候选图片URL：og/twitter 主图 + 正文 <img>。"""
    cands = []
    for pat in _OG_PATTERNS:
        m = re.search(pat, html, re.I)
        if m:
            cands.append(urljoin(base_url, m.group(1).strip()))
    # 正文里的 img（含懒加载 data-src），只要常见图片格式
    for m in re.finditer(
            r'<img[^>]+(?:data-original|data-src|src)=["\'](https?://[^"\']+?\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            html, re.I):
        cands.append(m.group(1))
    seen, out = set(), []
    for u in cands:
        if u.startswith("http") and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def scrape_cover(urls: list[str], title: str = "", out_dir: str = "output/images") -> str | None:
    """访问报道链接，抓页面上文件最大（最清晰）的一张图；跳过logo和>20M。全失败返回None。"""
    MIN_BYTES = 15000            # 小于15KB多半是logo/缩略图，跳过
    MAX_BYTES = 20 * 1024 * 1024  # 20M 上限（头条限制）
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, headers=UA_HDR, timeout=12)
            r.raise_for_status()
            candidates = _candidate_images(r.text, url)[:8]
        except Exception:
            continue
        best_data, best_size = None, 0
        for iu in candidates:
            try:
                ir = requests.get(iu, headers=UA_HDR, timeout=18)
                if ir.status_code != 200:
                    continue
                if "image" not in ir.headers.get("content-type", "").lower():
                    continue
                data = ir.content
                sz = len(data)
                if sz < MIN_BYTES or sz > MAX_BYTES:
                    continue
                if sz > best_size:              # 挑文件最大的（通常最清晰）
                    best_data, best_size = data, sz
            except Exception:
                continue
        if best_data:
            pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
            fn = hashlib.md5((title + url).encode("utf-8")).hexdigest()[:10] + ".jpg"
            with open(os.path.join(out_dir, fn), "wb") as f:
                f.write(best_data)
            print(f"  抓到报道配图（{best_size // 1024}KB，来自 {url[:40]}...）")
            return os.path.join("images", fn)
    print("  ⚠️ 没抓到合适的报道配图（将留空，可手动配）")
    return None
