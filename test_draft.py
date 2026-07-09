#!/usr/bin/env python3
"""
test_draft.py —— 单独测试『存草稿』(第④段)

不依赖热榜/DeepSeek，用一篇固定文章直接测：能不能自动填标题正文并存进头条草稿箱。
前提：已用 python login.py hans_toutiao 登录过（profile 里有登录态）。

用法：python test_draft.py
"""
from config import get_account
from publishers import get_publisher, Article


def main():
    account = get_account("hans_toutiao")
    pub = get_publisher(account)

    art = Article(
        title="自动化测试草稿",
        content="这是第一段测试正文，用来验证自动存草稿。\n"
                "这是第二段测试正文，检查分段是否正常。",
    )

    print("→ 正在测试存草稿（会打开头条发布页，自动填标题正文并点存草稿）...")
    r = pub.save_draft(art)
    if r.ok:
        print("✅ 存草稿成功！去头条后台『草稿箱』确认能看到这篇《自动化测试草稿》。")
    else:
        print(f"❌ 失败：{r.error}")


if __name__ == "__main__":
    main()
