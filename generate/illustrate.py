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


# ========== 抓报道原图（优先级 + 过滤 + 候选池）==========
# 优先级：og:image / twitter:image 最高 → 正文区(article/main)内图片次之 → 页面其它图片兜底。
# 过滤：URL 特征(logo/banner/ad…)、宽高<300、宽高比>3:1 的细长条。
# 产出：有序候选池（主图=第一张有效的），其余留给 /reimage「换图」依次用。
import re
import struct
from urllib.parse import urljoin, unquote

MIN_BYTES = 15000               # <15KB 多半是logo/缩略图
MAX_BYTES = 20 * 1024 * 1024    # 20M 上限（头条限制）
MIN_DIM = 300                   # 宽或高小于此的排除（拿不到尺寸则跳过该规则）
MAX_ASPECT = 3.0                # 宽高比超过 3:1 / 1:3 视为 banner/装饰条

_OG_PATTERNS = [
    r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
]
# URL 特征黑名单（按路径分段匹配，避免 upload/load 误伤 ad）
_IMG_URL_BAD = re.compile(
    r'(?:^|[/_\-.])(logos?|icons?|avatars?|sprites?|placeholder|banners?|ads?|adv|'
    r'qrcode|favicon|spacer|blank|default|btn|button|emoji|watermark)(?=$|[/_\-.@?])', re.I)
_IMG_FULLTAG_RE = re.compile(r"<img\b[^>]*>", re.I)
_IMG_SRC_RE = re.compile(
    r'(?:data-original|data-src|src)=["\'](https?://[^"\']+?\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', re.I)
_IMG_ALT_RE = re.compile(r'alt=["\']([^"\']*)["\']', re.I)


def _img_size(data: bytes) -> tuple[int, int] | None:
    """从文件头读宽高（PNG/JPEG/GIF/WebP），拿不到返回 None（不报错）。"""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:3] == b"GIF":
            return struct.unpack("<HH", data[6:10])
        if data[:2] == b"\xff\xd8":  # JPEG：扫 SOF 段
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            fmt = data[12:16]
            if fmt == b"VP8X":
                return (int.from_bytes(data[24:27], "little") + 1,
                        int.from_bytes(data[27:30], "little") + 1)
            if fmt == b"VP8 ":
                return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                        int.from_bytes(data[28:30], "little") & 0x3FFF)
            if fmt == b"VP8L":
                b0, b1, b2, b3 = data[21:25]
                return (((b1 & 0x3F) << 8 | b0) + 1,
                        ((b3 & 0x0F) << 10 | b2 << 2 | (b1 & 0xC0) >> 6) + 1)
    except Exception:
        pass
    return None


def _region(html: str, tag: str) -> str:
    m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.I | re.S)
    return m.group(1) if m else ""


def _imgs_in(seg: str) -> list[tuple[str, str]]:
    """片段里的 (图片URL, alt文本) 列表。"""
    out = []
    for tag in _IMG_FULLTAG_RE.findall(seg):
        m = _IMG_SRC_RE.search(tag)
        if not m:
            continue
        alt = _IMG_ALT_RE.search(tag)
        out.append((m.group(1), (alt.group(1).strip() if alt else "")))
    return out


def _page_candidates(html: str, base_url: str) -> list[dict]:
    """单个页面的有序候选 {url, alt, og}：og/twitter → article/main 区内图 → 其它正文图；
    过 URL 黑名单、去重（重复 URL 的 alt 取非空的那份）。"""
    ordered = []
    for pat in _OG_PATTERNS:
        for m in re.finditer(pat, html, re.I):
            ordered.append({"url": urljoin(base_url, m.group(1).strip()), "alt": "", "og": True})
    for region_tag in ("article", "main"):
        seg = _region(html, region_tag)
        if seg:
            ordered.extend({"url": u, "alt": a, "og": False} for u, a in _imgs_in(seg))
            break
    ordered.extend({"url": u, "alt": a, "og": False} for u, a in _imgs_in(html))
    out, seen = [], {}
    for c in ordered:
        u = c["url"]
        if not u.startswith("http") or _IMG_URL_BAD.search(u):
            continue
        if u in seen:
            if c["alt"] and not seen[u]["alt"]:
                seen[u]["alt"] = c["alt"]
            continue
        seen[u] = c
        out.append(c)
    return out[:12]


def collect_candidates(urls: list[str]) -> list[dict]:
    """按报道链接顺序收集全部候选 {url, alt, og}（有序去重）。"""
    out, seen = [], set()
    for url in urls[:5]:
        if not url:
            continue
        try:
            r = requests.get(url, headers=UA_HDR, timeout=12)
            r.raise_for_status()
        except Exception:
            continue
        for c in _page_candidates(r.text, url):
            if c["url"] not in seen:
                seen.add(c["url"])
                out.append(c)
    return out


# —— 语义弱排序：候选与标题的关键词重合度（alt 文本 + URL 解码），og 图给基础分保持领先 ——
def _title_keywords(title: str) -> set[str]:
    """标题 → 关键词集：英文/数字 token（≥3位且非纯数字）+ 中文 2 字滑窗。"""
    kws = set()
    for tok in re.split(r"[\W_]+", title):
        if not tok:
            continue
        if re.fullmatch(r"[A-Za-z0-9]+", tok):
            tok = tok.lower()
            if len(tok) >= 3 and not tok.isdigit():   # 短数字串会误配 URL 哈希，丢弃
                kws.add(tok)
        else:
            for i in range(len(tok) - 1):
                sh = tok[i:i + 2]
                if not sh.isascii():
                    kws.add(sh)
    return kws


def _relevance(cand: dict, kws: set[str]) -> int:
    hay = (cand.get("alt") or "") + " " + unquote(cand["url"]).lower()
    score = sum(1 for k in kws if k in hay)
    return score + (1 if cand.get("og") else 0)   # og 是编辑选的封面，基础分保持主图优先


def rank_candidates(cands: list[dict], title: str) -> list[dict]:
    """稳定排序：按相关度降序，同分保持原有优先级顺序（og→正文区→其它 × 报道页顺序）。"""
    kws = _title_keywords(title)
    return sorted(cands, key=lambda c: -_relevance(c, kws))


def download_valid_image(iu: str) -> bytes | None:
    """下载并校验一张候选图：content-type / 字节数 / 尺寸≥300 / 宽高比≤3:1。不合格返回 None。"""
    try:
        r = requests.get(iu, headers=UA_HDR, timeout=18)
        if r.status_code != 200 or "image" not in r.headers.get("content-type", "").lower():
            return None
        data = r.content
        if not (MIN_BYTES <= len(data) <= MAX_BYTES):
            return None
        size = _img_size(data)
        if size:
            w, h = size
            if w < MIN_DIM or h < MIN_DIM:
                return None
            if w > h * MAX_ASPECT or h > w * MAX_ASPECT:
                return None
        return data
    except Exception:
        return None


def save_image_bytes(data: bytes, key: str, out_dir: str = "output/images") -> str:
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    fn = hashlib.md5(key.encode("utf-8")).hexdigest()[:10] + ".jpg"
    with open(os.path.join(out_dir, fn), "wb") as f:
        f.write(data)
    return os.path.join("images", fn)


def scrape_cover_pool(urls: list[str], title: str = "",
                      out_dir: str = "output/images") -> tuple[str | None, list[str], int]:
    """抓报道配图：返回 (主图相对路径|None, 有序候选URL池, 主图在池中的索引|-1)。
    候选池入库前先按与标题的相关度弱排序（alt/URL 关键词重合，og 领先），
    主图 = 排序后第一张通过校验的候选，/reimage 按此顺序取即相关度优先。"""
    cands = rank_candidates(collect_candidates(urls), title)
    pool = [c["url"] for c in cands]
    for i, c in enumerate(cands):
        data = download_valid_image(c["url"])
        if data:
            rel = save_image_bytes(data, title + c["url"], out_dir)
            print(f"  抓到报道配图（{len(data) // 1024}KB，候选第{i + 1}/{len(pool)}张：{c['url'][:50]}...）")
            return rel, pool, i
    print(f"  ⚠️ 没抓到合适的报道配图（候选{len(pool)}张均未过校验，将留空，可换图/手动配）")
    return None, pool, -1


def scrape_cover(urls: list[str], title: str = "", out_dir: str = "output/images") -> str | None:
    """向后兼容旧调用（run_daily 等）：只要主图。"""
    return scrape_cover_pool(urls, title, out_dir)[0]
