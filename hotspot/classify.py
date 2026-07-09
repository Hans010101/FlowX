"""
classify.py —— 把热点归入赛道

规则：热点标题里包含某个已启用赛道的任一关键词，就归入该赛道（取第一个命中的）。
都不命中 → 返回 None（这条热点跳过，不出文）。
"""
from __future__ import annotations

from .fetch import HotItem


def classify(item: HotItem, enabled_tracks: dict) -> tuple[str, dict] | None:
    """
    enabled_tracks: {track_key: {name, keywords, prompt, ...}}
    返回 (track_key, track_conf) 或 None。
    """
    title = item.title
    for key, conf in enabled_tracks.items():
        for kw in conf.get("keywords", []):
            if kw and kw in title:
                return key, conf
    return None
