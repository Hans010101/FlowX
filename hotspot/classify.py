"""
classify.py —— 把热点归入赛道

规则：对每个赛道的全部命中词计分，命中词越多、越具体，得分越高。
同分时保持 tracks.yaml 的既有顺序，兼容原有人工优先级。
都不命中 → 返回 None（这条热点跳过，不出文）。
"""
from __future__ import annotations

from .fetch import HotItem


def classify(item: HotItem, enabled_tracks: dict) -> tuple[str, dict] | None:
    """
    enabled_tracks: {track_key: {name, keywords, prompt, ...}}
    返回 (track_key, track_conf) 或 None。
    """
    title = item.title.casefold()
    winner = None
    winner_rank = (0, 0, 0)
    for key, conf in enabled_tracks.items():
        hits = {str(kw).strip().casefold() for kw in conf.get("keywords", [])
                if str(kw).strip() and str(kw).strip().casefold() in title}
        if not hits:
            continue
        # 长词通常更具体：平方权重抑制“回应/曝光”等短泛词抢走强命中。
        rank = (sum(len(kw) ** 2 for kw in hits), len(hits), max(map(len, hits)))
        if rank > winner_rank:
            winner = (key, conf)
            winner_rank = rank
    return winner
