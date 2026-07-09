"""
revise.py —— 质检定向优化：按质检问题清单对稿件二次修订（对症下药，不是重写）

revise(article_dict, problems) -> Article
复用 llm.chat 改写、writer._clean_body/_extract_title 清洗兜底；重检与入库由调用方（/revise）负责。
"""
from __future__ import annotations

from publishers import Article
from .llm import chat
from .writer import _clean_body, _extract_title

_SYSTEM = (
    "你是今日头条资深内容编辑，负责按质检意见对稿件做定向修订。"
    "你的任务是修复被点名的问题，不是重写文章。"
)

_RULES = """修订硬性要求：
1. 只针对【质检问题清单】逐条修复；清单没点名的句子、结构、风格保持原样，不整篇重写、不改选题主旨。
   清单里无法靠改文字解决的问题（如"没有配图"）直接跳过。
2. 【合规红线·最重要】遇到「编造/未证实/缺来源/夸大/绝对化」类问题，只允许三种修法：
   a) 删掉该具体主张；
   b) 软化为观点/分析表述（如"有分析认为…""从趋势看…""业内普遍预计…"）；
   c) 泛化（去掉具体数字/日期，改成"近期""多次"这类模糊表述）。
   绝对禁止为了"补来源"而新增任何来源、机构名、日期、数字、数据——修订版里不允许出现原文没有的具体事实。
   例1：原文"该技术已让成本下降37%"被指缺来源 → 改成"业内分析认为这项技术能明显摊薄成本"，或整句删掉；
   例2："史上最强""必然颠覆行业"被指夸大 → 改成中性表述"表现突出""可能改变行业格局"。
3. 配图匹配类问题（如"搜图词与标题重复/不具体"）：只需降低标题与正文表述的重复度、
   让正文的画面感细节更具体；不得在文中出现"配图""搜图词"这类词。
4. 标题类问题（断尾/过长/与正文不一致）：给出完整通顺的新标题，20字以内，
   不得以"的/和/在"等虚词结尾；没点名标题问题就保留原标题。
5. 输出格式：第一行只写标题，空一行后写正文；纯文本、不用任何 Markdown 符号；
   绝对不出现「素材」「据资料」「质检」「修订」等暴露加工过程的字眼。
6. 正文保持 500-700 字左右，口语自然、像真人写的。"""


def revise(article: dict, problems: list[str]) -> Article:
    title = (article.get("title") or "").strip()
    body = article.get("body") or ""
    plist = [str(p).strip() for p in problems if str(p).strip()] \
        or ["整体润色提升：行文更自然、更像真人写的，观点更清楚"]
    prob_text = "\n".join(f"{i}. {p}" for i, p in enumerate(plist, 1))

    user_msg = (
        f"{_RULES}\n\n"
        f"=== 原标题 ===\n{title}\n\n"
        f"=== 原正文 ===\n{body}\n\n"
        f"=== 质检问题清单（逐条修复）===\n{prob_text}"
    )
    content = chat(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_msg}],
        temperature=0.5, timeout=120,
    )
    lines = content.strip().splitlines()
    body_raw = "\n".join(lines[1:]) if len(lines) > 1 else content
    new_body = _clean_body(body_raw)
    new_title = _extract_title(content)
    if not new_title or "未提取到" in new_title:
        new_title = title  # 提不出标题就保留原标题
    return Article(title=new_title, content=new_body, tags=[])
