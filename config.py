"""config.py —— 读取 .env 和 accounts/tracks/settings 配置 + 设置回写（来源/赛道开关）"""
from __future__ import annotations
import re
import sys
import yaml
import os


def load_env(path: str = ".env"):
    """读取 .env 文件把 key 写入环境变量（不覆盖已存在的）。无需第三方库。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---- 账号 ----
def load_accounts(path: str = "accounts.yaml") -> list[dict]:
    return _load(path).get("accounts", [])


def get_account(name: str, path: str = "accounts.yaml") -> dict:
    for acc in load_accounts(path):
        if acc.get("name") == name:
            return acc
    names = [a.get("name") for a in load_accounts(path)]
    print(f"❌ 找不到账号 '{name}'。accounts.yaml 里现有：{names}")
    sys.exit(1)


# ---- 赛道 ----
def load_tracks(path: str = "tracks.yaml") -> dict:
    """返回 {track_key: {name, enabled, keywords, prompt}}"""
    return _load(path).get("tracks", {})


def enabled_tracks(path: str = "tracks.yaml") -> dict:
    return {k: v for k, v in load_tracks(path).items() if v.get("enabled", False)}


# ---- 流水线设置 ----
def load_settings(path: str = "settings.yaml") -> dict:
    return _load(path)


# ---- 设置回写（只改目标字段；优先定点文本替换以保留注释，失败退回 safe_dump）----
def _write_validated(path: str, new_text: str, check) -> bool:
    """新文本必须能被 yaml 解析且 check(data) 通过才落盘，否则不动原文件。"""
    try:
        data = yaml.safe_load(new_text) or {}
        if not check(data):
            return False
    except Exception:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True


def _dump_fallback(path: str, data: dict):
    """兜底回写：语义正确但会丢注释（正常路径用不到）。"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def set_hotspot_sources(sources: list[str], path: str = "settings.yaml"):
    """把启用的热点来源写回 settings.yaml 的 hotspot.sources，其它内容（含注释）原样保留。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    flow = "[" + ", ".join(sources) + "]"
    new_text, n = re.subn(r"(?m)^(\s*sources:\s*)\[[^\]]*\]", lambda m: m.group(1) + flow, text, count=1)
    if n == 1 and _write_validated(path, new_text,
                                   lambda d: d.get("hotspot", {}).get("sources") == sources):
        return
    data = _load(path)
    data.setdefault("hotspot", {})["sources"] = sources
    _dump_fallback(path, data)


def set_track_enabled(key: str, enabled: bool, path: str = "tracks.yaml"):
    """改 tracks.yaml 里某赛道的 enabled，keywords/prompt/注释原样保留。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if key not in (_load(path).get("tracks") or {}):
        raise KeyError(f"赛道 '{key}' 不存在")
    val = "true" if enabled else "false"
    # 定位「  key:」块内的第一个「    enabled:」行，只改那一行
    pat = re.compile(rf"(?m)(^  {re.escape(key)}:\s*\n(?:(?!^  \S).*\n)*?^\s{{4}}enabled:\s*)(\S+)")
    new_text, n = pat.subn(lambda m: m.group(1) + val, text, count=1)
    if n == 1 and _write_validated(path, new_text,
                                   lambda d: bool(d.get("tracks", {}).get(key, {}).get("enabled")) == enabled):
        return
    data = _load(path)
    data["tracks"][key]["enabled"] = enabled
    _dump_fallback(path, data)
