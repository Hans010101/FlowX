#!/usr/bin/env python3
"""
test_publish.py —— 从稿件库取【最新一篇未发的真实稿子】测试自动发布（定时发布）

比发死内容更有意义：发真标题、真正文、真配图，一次看清真实效果。
发成功后自动把这篇在库里标记为"已发"。
用法：python test_publish.py
前提：已 python login.py hans_toutiao 登录过，且库里有未发稿件（先跑过 run_daily.py）。
"""
import os
from config import get_account, load_env
from publishers import get_publisher, Article
import store


def main():
    load_env()

    # 从库里找最新一篇"未发"的真实稿子
    unsent = [a for a in store.all_articles() if a.get("status") != "已发"]
    if not unsent:
        print("库里没有未发稿件。先跑 python run_daily.py 生成一批。")
        return
    a = unsent[0]
    print(f"将测试发布这篇未发稿：《{a['title']}》（{a.get('track','')}）")

    # 配图：库里存的是相对 output/ 的路径
    cover = None
    if a.get("image"):
        p = os.path.join("output", a["image"])
        cover = os.path.abspath(p) if os.path.exists(p) else None
    print(f"配图：{cover or '无（将不插图）'}")

    art = Article(title=a["title"], content=a["body"], cover_image=cover)
    print("→ 开始自动定时发布（打开头条、自动填充、插图、定时发布）...")
    r = get_publisher(get_account("hans_toutiao")).publish(art)
    if r.ok:
        store.set_status(a["title"], "已发")
        print("✅ 已提交定时发布！去头条后台『内容管理』看这篇待发布的定时文章。")
        print("   这篇已在库里标记为『已发』（重开 dashboard 可见）。")
    else:
        print(f"✗ 失败：{r.error}")


if __name__ == "__main__":
    main()
