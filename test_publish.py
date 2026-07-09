#!/usr/bin/env python3
"""
test_publish.py —— 从稿件库取【一篇】未发稿测试自动发布（定时发布，强制单篇）

安全设计：
  - 只发一篇：默认取最新一篇「未发」（不含待修复/已发），或 python test_publish.py <稿件id> 指定；绝不循环批量。
  - 发布前打印 标题 / 正文前50字 / 配图路径 / 质检分 供核对；
  - 真正提交前发布器里还有人工确认闸：回车才提交，Ctrl+C 放弃。
  - dry-run：TOUTIAO_DRY_RUN=1 python test_publish.py —— 自动填充+插图后在确认闸前停住，不提交。
用法：python test_publish.py [稿件id]
前提：已 python login.py hans_toutiao 登录过。
"""
import os
import sys

from config import get_account, load_env
from publishers import get_publisher, Article
import store


def main():
    load_env()

    arts = store.all_articles()
    want_id = sys.argv[1] if len(sys.argv) > 1 else None
    if want_id:
        a = next((x for x in arts if x["id"] == want_id), None)
        if not a:
            print(f"找不到 id={want_id} 的稿件。")
            return
    else:
        unsent = [x for x in arts if x.get("status") == "未发"]
        if not unsent:
            print("库里没有「未发」稿件（待修复的不发）。先去界面生成一篇。")
            return
        a = unsent[0]

    # 配图：库里存的是相对 output/ 的路径
    cover = None
    if a.get("image"):
        p = os.path.join("output", a["image"])
        cover = os.path.abspath(p) if os.path.exists(p) else None

    print("=" * 56)
    print("只发这【一篇】，请核对：")
    print(f"  标题：《{a['title']}》")
    print(f"  正文前50字：{(a.get('body') or '')[:50]}…")
    print(f"  配图：{cover or '无（将不插图）'}")
    print(f"  质检：{a.get('qc_score')}（{a.get('qc_level')}）· 状态：{a.get('status')} · id：{a['id']}")
    print("=" * 56)

    art = Article(title=a["title"], content=a["body"], cover_image=cover)
    print("→ 打开头条后台自动填充（定时发布；真正提交前还会要你按回车确认）...")
    r = get_publisher(get_account("hans_toutiao")).publish(art)

    if r.ok and r.url == "DRY-RUN-NOT-SUBMITTED":
        print("🌵 DRY RUN 完成：已填充并走到人工确认闸前，未提交，库里状态不变。")
    elif r.ok:
        store.set_status(a["title"], "已发")
        print(f"✅ 已提交定时发布！url: {r.url}")
        print("   这篇已在库里标记为『已发』。去头条后台『内容管理』看定时文章。")
    else:
        print(f"✗ 失败/放弃：{r.error}")


if __name__ == "__main__":
    main()
