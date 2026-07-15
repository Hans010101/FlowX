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
    # 已处理热点选题（id=md5(热点标题)，带生成时间戳，供时间窗口去重；独立新表不动旧数据）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_topics (
            id           TEXT PRIMARY KEY,
            title        TEXT,
            processed_at TEXT
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


def mark_topic_processed(title: str):
    """记录某热点选题已生成过稿（带时间戳，供 6 小时窗口去重）。"""
    conn = _conn()
    try:
        conn.execute("INSERT OR REPLACE INTO processed_topics (id,title,processed_at) VALUES (?,?,?)",
                     (_aid(title), title, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()


def _within(ts_str: str, fmt: str, hours: float) -> bool:
    try:
        return (time.time() - time.mktime(time.strptime(ts_str, fmt))) < hours * 3600
    except Exception:
        return True   # 时间解析不了按"窗口内"保守处理


def is_processed(title: str, within_hours: float | None = 6) -> bool:
    """该热点选题是否在时间窗口内已写过稿：
    - 优先查 processed_topics（有生成时间戳）；within_hours=None 表示永久去重。
    - 兼容旧数据：老库无 processed_topics 记录时，退回查 articles 同标题稿（按其 created_at 套同一窗口）。
    超过窗口的选题视为可重新采集出稿。"""
    conn = _conn()
    try:
        row = conn.execute("SELECT processed_at FROM processed_topics WHERE id=?",
                           (_aid(title),)).fetchone()
        if row:
            return True if within_hours is None else _within(row["processed_at"], "%Y-%m-%d %H:%M:%S", within_hours)
        row2 = conn.execute("SELECT created_at FROM articles WHERE id=?", (_aid(title),)).fetchone()
        if not row2:
            return False
        return True if within_hours is None else _within(row2["created_at"] or "", "%Y-%m-%d %H:%M", within_hours)
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


def update_article(article_id: str, item: dict, status: str) -> str:
    """更新稿件正文并返回新 id；标题变化时原子地移除旧 id 行。"""
    new_id = _aid(item["title"])
    conn = _conn()
    try:
        existing = conn.execute("SELECT created_at FROM articles WHERE id=?", (article_id,)).fetchone()
        if not existing:
            raise KeyError(article_id)
        if new_id != article_id:
            collision = conn.execute("SELECT 1 FROM articles WHERE id=?", (new_id,)).fetchone()
            if collision:
                raise ValueError("已有同标题稿件，请换一个标题")
        conn.execute(
            "INSERT OR REPLACE INTO articles "
            "(id,title,body,image,track,source,status,created_at,qc_score,qc_level,qc_problems,"
            "img_candidates,image_idx) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id, item["title"], item.get("body", ""), item.get("image"),
             item.get("track", ""), item.get("source", ""), status,
             existing["created_at"], item.get("qc_score"), item.get("qc_level"),
             item.get("qc_problems"), item.get("img_candidates"), item.get("image_idx")))
        if new_id != article_id:
            conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
        conn.commit()
        return new_id
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
