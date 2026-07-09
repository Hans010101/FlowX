#!/usr/bin/env python3
"""dashboard.py —— 随时重建稿件管理台（不跑生成，只把库里的稿件渲染成网页）"""
import review, store
out = review.render_dashboard(store.all_articles())
print(f"稿件管理台已生成：{out}")
print(f"库里共 {len(store.all_articles())} 篇。双击打开查看。")
