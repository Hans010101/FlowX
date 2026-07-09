#!/usr/bin/env python3
"""
publish.py —— 编排：把一篇文章通过指定账号发出去

现在是骨架 + 示例。真正的自动化里，article 会来自「DeepSeek 出文」那一步，
account 会按热点所属赛道自动选。目前先支持手动指定账号发一篇，验证发布链路。

用法：
    python publish.py hans_toutiao
"""
from __future__ import annotations

import sys

from config import get_account
from publishers import get_publisher, Article


def build_demo_article() -> Article:
    """示例文章。以后这里换成从 DeepSeek 出文环节拿到的内容。"""
    return Article(
        title="这是一篇测试标题，用来验证发布链路",
        content="这是测试正文第一段。\n\n这是测试正文第二段。",
        cover_image=None,
        tags=["测试"],
    )


def main():
    if len(sys.argv) < 2:
        print("用法：python publish.py <账号name>   例如：python publish.py hans_toutiao")
        sys.exit(1)

    account = get_account(sys.argv[1])
    publisher = get_publisher(account)
    article = build_demo_article()

    print(f"→ 用账号 {account['name']}（{account['platform']}）发布：{article.title}")
    result = publisher.publish(article)

    if result.ok:
        print(f"✅ 发布成功！{result.url or ''}")
    else:
        print(f"❌ 发布失败：{result.error}")


if __name__ == "__main__":
    main()
