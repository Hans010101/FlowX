"""config.py —— 读取 .env 和 accounts/tracks/settings 配置"""
from __future__ import annotations
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
