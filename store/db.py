"""
db.py —— 稿件库（SQLite）：存完整稿件 + 状态 + 质检结果，供管理页读取

状态：未发 / 已发 / 待修复。生成时质检绿黄记"未发"、红档记"待修复"，自动发布后记"已发"。
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
            id          TEXT PRIMARY KEY,
            title       TEXT,
            body        TEXT,
            image       TEXT,
            track       TEXT,
            source      TEXT,
            status      TEXT,
            created_at  TEXT,
            qc_score    INTEGER,
            qc_level    TEXT,
            qc_problems TEXT,
            img_candidates TEXT,
            image_idx   INTEGER
        )
    """)
    # 旧库迁移：缺列则补
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(articles)")}
        for col, typ in (("qc_score", "INTEGER"), ("qc_level", "TEXT"), ("qc_problems", "TEXT"),
                         ("img_candidates", "TEXT"), ("image_idx", "INTEGER")):
            if col not in cols:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {col} {typ}")
        conn.commit()
    except Exception as e:
        print(f"  ⚠️ 稿件库列迁移失败（不影响旧功能）：{e}")
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
    """存一篇稿件。item 需含 title/body/image/track/source，
    可带 qc_score/qc_level/qc_problems/img_candidates/image_idx（不带存 NULL）。"""
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO articles "
            "(id,title,body,image,track,source,status,created_at,qc_score,qc_level,qc_problems,"
            "img_candidates,image_idx) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_aid(item["title"]), item["title"], item.get("body", ""), item.get("image"),
             item.get("track", ""), item.get("source", ""), status,
             item.get("time") or time.strftime("%Y-%m-%d %H:%M"),
             item.get("qc_score"), item.get("qc_level"), item.get("qc_problems"),
             item.get("img_candidates"), item.get("image_idx")))
        conn.commit()
    finally:
        conn.close()


def delete_article(article_id: str):
    """按 id 删一篇（/revise 改标题时旧 id 行要移除，避免留重复稿）。"""
    conn = _conn()
    try:
        conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
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
