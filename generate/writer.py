"""
writer.py —— DeepSeek 基于素材改写（标题≤30字 + 正文），并清理 Markdown
"""
from __future__ import annotations

import re
from publishers import Article
from .llm import chat


_LEAK_PATTERNS = [
    r'素材(里|中|里面|中提到|显示|写|指出|提及)[，,、：:]?\s*',
    r'据(素材|资料|了解到的信息|上文|上述)[，,、：:]?\s*',
    r'(资料|上文|上述|前文)(显示|提到|指出|提及)[，,、：:]?\s*',
    r'根据(素材|资料|以上信息)[，,、：:]?\s*',
]


def _strip_meta_leak(s: str) -> str:
    for pat in _LEAK_PATTERNS:
        s = re.sub(pat, '', s)
    return s


def _clean_body(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        s = _strip_meta_leak(ln)
        s = re.sub(r'^\s*#{1,6}\s*', '', s)
        s = re.sub(r'^\s*[-*+]\s+', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'(?<!\*)\*(?!\*)(.+?)\*', r'\1', s)
        s = s.replace('`', '')
        lines.append(s)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def _extract_title(text: str) -> str:
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        s = re.sub(r'^#{1,6}\s*', '', s)
        s = re.sub(r'^(备选标题|标题|备选)\s*[\d一二三]*\s*[:：、.\)]*\s*', '', s)
        s = re.sub(r'^[\d一二三][\.\、\)]\s*', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = s.replace('*', '').strip()
        s = s.strip('《》"" ').strip()
        if s and s not in ("备选标题", "标题", "正文") and len(s) >= 4:
            return s[:30]
    return "（未提取到标题，请手动填）"


def _gen_title(body: str, hot_title: str) -> str:
    """正文写完后，单独生成一个完整通顺的标题（避免从正文抠出断尾标题）。"""
    try:
        t = chat(
            [{"role": "system",
              "content": "你是今日头条标题高手。根据给定的文章正文，写1个标题。硬性要求："
                         "①20字以内；②必须是完整通顺的一句话，绝对不能截断、不能缺字、"
                         "不能以'这次''的''了''是'等虚词硬性结尾；③风格：用具体数字或悬念+情绪，"
                         "可用感叹号，可用冒号引出金句。只输出标题本身，不要引号、不要解释、不要序号。"},
             {"role": "user", "content": f"选题：{hot_title}\n\n正文：\n{body[:1200]}"}],
            temperature=0.8, timeout=40,
        )
        title = _extract_title(t)
        if title and "未提取到" not in title:
            return title
    except Exception:
        pass
    return ""


def write(hot_title: str, track_prompt: str, material: str = "") -> Article:
    if material:
        user_msg = (
            f"热点选题：{hot_title}\n\n"
            f"下面提供一些关于该选题的背景资料。请你写一篇文章。硬性要求：\n"
            f"1. 把这些资料当成你本人已经掌握的事实，直接、自然地写出来。\n"
            f"2. 绝对禁止出现『素材』『据素材』『资料显示』『上文提到』『据了解到的信息』等任何"
            f"暴露写作过程或提及参考资料的字眼——读者看不到这些资料，出现这类词会很突兀。\n"
            f"3. 优先使用资料里的真实数字、事实、案例；不得编造资料之外的具体数字或事实。\n"
            f"4. 标题必须是一句完整通顺的话，不允许残缺结尾（如『5187mAh史』这种断掉的表达）。\n"
            f"5. 写完从头到尾通读一遍：句子之间衔接自然、逻辑连贯、读起来顺口，"
            f"避免生硬转折和莫名其妙的断句。\n\n"
            f"=== 背景资料 ===\n{material}\n=== 资料结束 ==="
        )
    else:
        # 没搜到素材时的降级：仅按标题写，并提醒不要编造硬数据
        user_msg = (
            f"热点选题：{hot_title}\n\n"
            f"没有可用素材，请围绕这个选题写一篇文章。注意：不要编造具体的数字、金额、"
            f"统计数据或未经证实的'内幕'，可以做分析、评论和背景介绍。"
        )

    content = chat(
        [{"role": "system", "content": track_prompt},
         {"role": "user", "content": user_msg}],
        temperature=0.9,
    )
    lines = content.strip().splitlines()
    body_raw = "\n".join(lines[1:]) if len(lines) > 1 else content
    body = _clean_body(body_raw)
    # 标题单独重生（更完整），失败才退回从正文抠
    title = _gen_title(body, hot_title) or _extract_title(content)
    return Article(title=title, content=body, tags=[])
