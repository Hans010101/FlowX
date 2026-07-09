"""llm.py —— DeepSeek 对话客户端（writer 和 illustrate 共用）"""
from __future__ import annotations
import os
import requests

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def chat(messages: list[dict], temperature: float = 1.0, timeout: int = 120) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY 环境变量")
    resp = requests.post(
        DEEPSEEK_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": temperature, "stream": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
