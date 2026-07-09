"""
toutiao.py —— 今日头条图文自动发布器（定时发布，用头条默认时间）

选择器来自真实后台 codegen 录制。流程：
  填标题 → 填正文 → 正文插入本地图（自动变封面）→ 定时发布 → 预览并定时发布。
我无法在本地实测头条后台，选择器为录制提取的最佳值；首跑请用 test_publish.py 只发1篇验证。
"""
from __future__ import annotations

import re
import os
from playwright.sync_api import Page

from .base import BasePublisher, Article, PublishResult


class ToutiaoPublisher(BasePublisher):
    platform = "toutiao"
    LOGIN_URL = "https://mp.toutiao.com/"
    PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"

    def is_logged_in(self, page: Page) -> bool:
        url = page.url
        if any(k in url for k in ("sso", "login", "passport", "auth")):
            return False
        try:
            if page.locator("text=登录").first.is_visible(timeout=1500):
                return False
        except Exception:
            pass
        return True

    def _dismiss_drawer(self, page: Page):
        try:
            mask = page.locator(".byte-drawer-mask")
            if mask.first.is_visible(timeout=2000):
                mask.first.click()
                page.wait_for_timeout(500)
        except Exception:
            pass

    def do_publish(self, page: Page, article: Article, as_draft: bool) -> PublishResult:
        page.goto(self.PUBLISH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        self._dismiss_drawer(page)

        # 1) 标题
        page.get_by_role("textbox", name="请输入文章标题（2～30个字）").fill(article.title)
        page.wait_for_timeout(600)

        # 2) 正文：点占位区聚焦后逐段输入
        page.locator("div").filter(has_text=re.compile(r"^请输入正文$")).first.click()
        page.wait_for_timeout(400)
        for i, para in enumerate(article.content.split("\n")):
            if i > 0:
                page.keyboard.press("Enter")
            if para.strip():
                page.keyboard.type(para)
        page.wait_for_timeout(1000)

        # 3) 正文插入本地配图（图进正文后头条自动拿它当封面）
        if article.cover_image and os.path.exists(article.cover_image):
            try:
                page.locator(".add-icon").first.click()
                page.wait_for_timeout(1200)
                page.locator('button:has-text("本地上传") input[type="file"]').set_input_files(
                    os.path.abspath(article.cover_image))
                # 等图片上传出现在正文里
                page.wait_for_selector(".img-wrap img", timeout=40000)
                page.wait_for_timeout(2500)
                # 若弹出封面/图片确认框，点确定
                self._confirm_if_any(page)
            except Exception as e:
                print(f"    ⚠️ 正文插图失败（继续发文，无封面）：{e}")

        page.wait_for_timeout(1000)

        # 4) 定时发布（用头条默认时间，不手动选）
        page.get_by_role("button", name="定时发布").click()
        page.wait_for_timeout(1500)

        # 5) 最终提交：预览并定时发布
        page.locator("button").filter(has_text="预览并定时发布").click()
        page.wait_for_timeout(4000)
        self._confirm_if_any(page)   # 预览弹窗里若还有确认按钮
        page.wait_for_timeout(2000)

        return PublishResult(ok=True, url=page.url)

    def _confirm_if_any(self, page: Page):
        """出现"确定/发布/确认发布"这类按钮就点一下（用于封面框、预览框）。"""
        for name in ("确认发布", "确定发布", "确定", "发布"):
            try:
                btn = page.get_by_role("button", name=name)
                if btn.last.is_visible(timeout=1500):
                    btn.last.click()
                    page.wait_for_timeout(1500)
                    return
            except Exception:
                continue
