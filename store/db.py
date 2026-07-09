"""
db.py —— 稿件库（SQLite）：存完整稿件 + 状态，供管理页读取

状态：未发 / 已发。生成时记"未发"，自动发布后记"已发"。
"""
from __future__ import annotations

import sqlite3
import time
import hashlib
import pathlib

DB_PATH = "store/pipeline.db"


def _conn():
    pathlib.Path("store").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id         TEXT PRIMARY KEY,
            title      TEXT,
            body       TEXT,
            image      TEXT,
            track      TEXT,
            source     TEXT,
            status     TEXT,
            created_at TEXT
        )
    """)
    return conn


def _aid(title: str) -> str:
    return hashlib.md5(title.encode("utf-8")).hexdigest()[:12]


def is_processed(title: str) -> bool:
    conn = _conn()
    try:
        return conn.execute("SELECT 1 FROM articles WHERE id=?", (_aid(title),)).fetchone() is not None
    finally:
        conn.close()


def save_article(item: dict, status: str = "未发"):
    """存一篇稿件。item 需含 title/body/image/track/source。"""
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO articles (id,title,body,image,track,source,status,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (_aid(item["title"]), item["title"], item.get("body", ""), item.get("image"),
             item.get("track", ""), item.get("source", ""), status,
             item.get("time") or time.strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    finally:
        conn.close()


def set_status(title: str, status: str):
    conn = _conn()
    try:
        conn.execute("UPDATE articles SET status=? WHERE id=?", (status, _aid(title)))
        conn.commit()
    finally:
        conn.close()


def all_articles(limit: int = 500) -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# 兼容旧调用名
def mark(title, track, source, status):
    save_article({"title": title, "track": track, "source": source}, status)
