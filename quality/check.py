"""
check.py —— 质检：规则检测 + AI 检测（DeepSeek 审稿，含去AI味维度），合并打分分档

quality_check(article_dict) -> {"score": int, "level": "green|yellow|red", "problems": [...]}
分档：总分≥80 且未命中严重规则项 → green；60–79 → yellow；总分<60 或命中任一严重规则项 → red
"""
from __future__ import annotations

import json
import re

from generate.llm import chat
from generate.writer import _LEAK_PATTERNS

SEVERE_DEDUCT = 30
MINOR_DEDUCT = 10

# 标题断尾的虚词，分两档（长词在前，优先匹配）：
# 严重 = 结构性虚词结尾，标题必然悬空（"了"不在列：以"了"结尾多为完整句，如"养老金涨了"）
_SEVERE_TAILS = sorted(
    ["的", "地", "和", "与", "及", "或", "跟", "并", "而", "在", "对", "把", "被",
     "将", "为", "向", "从", "由", "以", "比", "给"],
    key=len, reverse=True)
# 一般 = 有歧义的结尾（可能完整可能断），只扣分不单独挂红
_MINOR_TAILS = sorted(["是", "这次"], key=len, reverse=True)
# 成对标点（左右字符不同，按计数配对）
_PAIRED_MARKS = [("《", "》"), ("“", "”"), ("「", "」"), ("(", ")"), ("（", "）"), ("【", "】"), ("[", "]")]
# 判断断尾前先剥掉结尾的整句标点
_TAIL_PUNCT = "！？。!?…～~"


def _title_bad_tail(title: str) -> tuple[str, str] | None:
    """标题以虚词硬结尾则返回 (档位, 命中词)，档位为 severe/minor；否则 None。"""
    t = title.strip().rstrip(_TAIL_PUNCT)
    for w in _SEVERE_TAILS:
        if t.endswith(w):
            return ("severe", w)
    for w in _MINOR_TAILS:
        if t.endswith(w):
            return ("minor", w)
    return None


def _title_unbalanced(title: str) -> bool:
    return any(title.count(a) != title.count(b) for a, b in _PAIRED_MARKS)


def rule_check(article: dict) -> tuple[list[str], int, bool]:
    """返回 (problems, deductions, has_severe)。严重 -30、一般 -10。"""
    title = (article.get("title") or "").strip()
    body = article.get("body") or ""
    problems: list[str] = []
    severe = 0
    minor = 0

    # 标题断尾：结构性虚词【严重】，歧义词【一般】
    tail = _title_bad_tail(title)
    if tail:
        grade, word = tail
        if grade == "severe":
            problems.append(f"标题断尾：以结构性虚词『{word}』结尾")
            severe += 1
        else:
            problems.append(f"标题结尾存疑：以『{word}』结尾，请确认是否完整")
            minor += 1
    if _title_unbalanced(title):
        problems.append("标题含未闭合的引号/括号")
        severe += 1

    # 标题长度【一般】
    if len(title) > 30:
        problems.append(f"标题过长（{len(title)}字，>30）")
        minor += 1
    elif len(title) < 8:
        problems.append(f"标题过短（{len(title)}字，<8）")
        minor += 1

    # 正文字数【一般】（去空白后按字符数）
    n = len(re.sub(r"\s", "", body))
    if n < 400:
        problems.append(f"正文过短（{n}字，<400）")
        minor += 1
    elif n > 900:
        problems.append(f"正文过长（{n}字，>900）")
        minor += 1

    # 素材字眼残留【严重】—— 复用 writer 的泄漏词正则
    leaked = [m.group(0).strip("，,、：: \t") for pat in _LEAK_PATTERNS for m in [re.search(pat, body)] if m]
    if leaked:
        problems.append(f"正文残留素材字眼：{'、'.join(dict.fromkeys(leaked))}")
        severe += 1

    # Markdown 残留【一般】（对应 writer._clean_body 清理的符号类）
    md_hits = []
    if re.search(r"(?m)^\s*#{1,6}\s", body):
        md_hits.append("#标题符")
    if re.search(r"\*\*.+?\*\*", body):
        md_hits.append("**加粗**")
    if "`" in body:
        md_hits.append("反引号")
    if re.search(r"(?m)^\s*[-*+]\s+", body):
        md_hits.append("列表符")
    if md_hits:
        problems.append(f"正文残留 Markdown 符号：{'、'.join(md_hits)}")
        minor += 1

    # 大空格/空行【一般】：连续3行以上空行，或异常连续空白
    if re.search(r"\n(?:[ \t　]*\n){3,}", body) or re.search(r"[ 　]{6,}", body):
        problems.append("正文存在连续空行或异常大段空白")
        minor += 1

    # 无配图【一般】
    if not article.get("image"):
        problems.append("没有配图")
        minor += 1

    return problems, severe * SEVERE_DEDUCT + minor * MINOR_DEDUCT, severe > 0


_AI_SCORE_KEYS = ("logic_score", "fact_score", "compliance_score", "image_match_score", "ai_taste_score")

_AI_SYSTEM = "你是今日头条资深审稿编辑，负责稿件发布前的最后一道质检，眼光挑剔、直说问题。"

_AI_USER_TMPL = """请从五个维度评估下面这篇稿件，每个维度打 0-100 分：
1. logic_score 逻辑通顺：句子衔接自然、结构连贯、无莫名断句或生硬转折；
2. fact_score 事实一致：正文前后数字与说法无矛盾，标题与正文说法一致；
3. compliance_score 合规：无绝对化承诺、无夸大或编造，未证实的事不得写成已证实，无违规表述；
4. image_match_score 配图匹配：按下面的配图搜图词与文章主题的相关度判断；
5. ai_taste_score 去AI味：越像真人写的分越高。低分特征：工整列表腔、过度对仗、四平八稳无观点、\
连接词堆砌（首先/其次/总而言之）、缺少个人视角和口语感。

发现的具体问题写进 problems 数组（中文短句，没有就给空数组）。
对「缺来源/未证实/数据无出处/夸大/绝对化」类问题，问题描述里给的修改方向只能是三种：
删除该具体主张 / 软化为观点或分析表述（如"有分析认为…"）/ 去掉无法核实的具体数字、日期。
绝对不要建议"补充来源""补充数据""注明出处"这类需要新增事实的修法——本系统禁止为过检而编造来源。
只输出一个 JSON 对象，不要 markdown 代码块、不要任何多余文字，格式：
{{"logic_score":0,"fact_score":0,"compliance_score":0,"image_match_score":0,"ai_taste_score":0,"problems":[]}}

【标题】{title}
【配图搜图词】{image_query}
【正文】
{body}"""


def _degraded(reason: str) -> dict:
    d = {k: 75 for k in _AI_SCORE_KEYS}
    d["problems"] = [f"AI检测{reason}，仅按规则判定"]
    return d


def _parse_ai_json(raw: str) -> dict:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        raise ValueError("回复里没有 JSON 对象")
    return json.loads(m.group(0))


def ai_check(title: str, body: str, image_query: str = "") -> dict:
    """DeepSeek 审稿，返回五维分数 + problems。调用/解析失败一律降级（五项=75），不让文章因此挂红。"""
    try:
        raw = chat(
            [{"role": "system", "content": _AI_SYSTEM},
             {"role": "user", "content": _AI_USER_TMPL.format(
                 title=title, image_query=image_query or title, body=body)}],
            temperature=0.2, timeout=90,
        )
    except Exception as e:
        print(f"  ⚠️ AI质检调用失败，降级为仅规则判定：{e}")
        return _degraded("调用失败")

    try:
        data = _parse_ai_json(raw)
    except Exception as e:
        print(f"  ⚠️ AI质检解析失败，降级为仅规则判定：{e}｜原始回复前120字：{raw[:120]!r}")
        return _degraded("解析失败")

    out = {}
    for k in _AI_SCORE_KEYS:
        try:
            out[k] = max(0, min(100, int(round(float(data.get(k, 75))))))
        except (TypeError, ValueError):
            out[k] = 75
    probs = data.get("problems") or []
    out["problems"] = [str(p).strip() for p in probs if str(p).strip()] if isinstance(probs, list) else []
    return out


def quality_check(article: dict) -> dict:
    """规则 + AI 合并：总分 = 规则分×0.4 + AI五维均分×0.6。"""
    rule_problems, deductions, has_severe = rule_check(article)
    rule_score = max(0, 100 - deductions)

    ai = ai_check(article.get("title") or "", article.get("body") or "",
                  image_query=article.get("title") or "")
    ai_score = sum(ai[k] for k in _AI_SCORE_KEYS) / len(_AI_SCORE_KEYS)

    score = round(rule_score * 0.4 + ai_score * 0.6)
    if has_severe or score < 60:
        level = "red"
    elif score >= 80:
        level = "green"
    else:
        level = "yellow"

    problems = list(dict.fromkeys(rule_problems + ai["problems"]))
    return {"score": score, "level": level, "problems": problems}
