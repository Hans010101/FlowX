"""
toutiao.py —— 今日头条图文自动发布器（定时发布，用头条默认时间）

选择器来自真实后台 codegen 录制（2026-07 后台改版后重录：插图按钮/本地上传/确定框已更新）。
流程：填标题 → 填正文 → 正文插入本地图（自动变封面）→ 定时发布 → 人工确认闸 → 最终提交。
⚠️ 头条无草稿箱预存，提交即真发（定时稿）——所以真正提交前有 input() 人工确认闸，
   回车才提交、Ctrl+C 放弃；设 TOUTIAO_DRY_RUN=1 则走到闸前停住不提交。
首跑请用 test_publish.py 只发 1 篇验证。
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

        # 3) 正文插入本地配图（图进正文后头条自动拿它当封面）—— 2026-07 改版后重录的选择器
        if article.cover_image and os.path.exists(article.cover_image):
            try:
                # 旧 .add-icon 已失效 → 工具栏图片按钮
                page.locator(".syl-toolbar-tool.image > div > .syl-toolbar-button").first.click()
                page.wait_for_timeout(1200)
                # 旧 button:has-text("本地上传") → 新按钮名「本地上传 Choose File」
                page.get_by_role("button", name="本地上传 Choose File").locator(
                    'input[type="file"]').set_input_files(os.path.abspath(article.cover_image))
                page.wait_for_timeout(2500)          # 等弹窗内上传完成
                try:
                    page.get_by_role("button", name="确定").click()   # 录到的插图确认框
                    print("    插图确认框：已点『确定』")
                except Exception:
                    self._confirm_if_any(page)
                # 等图片进正文：精确选择器 → 宽松"编辑区出现 img" → 延时兜底，不硬等到超时
                try:
                    page.wait_for_selector(".img-wrap img", timeout=12000)
                except Exception:
                    try:
                        page.wait_for_selector(
                            ".syl-editor img, .ProseMirror img, [class*='editor'] img", timeout=8000)
                    except Exception:
                        print("    ⚠️ 没等到正文图片节点，延时5秒兜底继续")
                        page.wait_for_timeout(5000)
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"    ⚠️ 正文插图失败（继续发文，无封面）：{e}")

        page.wait_for_timeout(1000)

        # 4) 定时发布（用头条默认时间，不改立即发布）
        page.get_by_role("button", name="定时发布").click()
        page.wait_for_timeout(1500)

        # 5) 找最终提交按钮：改版后文字可能变，按"最具体→最宽松"依次匹配
        final_btn, final_label = None, None
        for name, exact in (("预览并定时发布", False), ("预览并发布", False), ("预览", True)):
            try:
                btn = page.get_by_role("button", name=name, exact=exact)
                if btn.first.is_visible(timeout=1500):
                    final_btn, final_label = btn.first, name
                    break
            except Exception:
                continue
        if final_btn is None:
            shot = self._screenshot(page, "no-final-btn")
            return PublishResult(
                ok=False,
                error=f"没找到最终提交按钮（预览并定时发布/预览并发布/预览 都不可见）。截图：{shot}")

        # 6) 人工确认闸（硬要求）：程序不自己闷头提交，最后一步由人把关
        print(f"\n⚠️  即将发布到头条（定时稿，提交后公开可见）：《{article.title}》")
        print(f"    识别到的最终提交按钮：『{final_label}』")
        if os.environ.get("TOUTIAO_DRY_RUN") == "1":
            shot = self._screenshot(page, "dry-run")
            print(f"    [DRY RUN] 到确认闸为止，不提交。当前页截图：{shot}")
            return PublishResult(ok=True, url="DRY-RUN-NOT-SUBMITTED")
        input("    确认发布请按回车，放弃请 Ctrl+C ... ")

        print(f"    点击『{final_label}』提交 ...")
        final_btn.click()
        page.wait_for_timeout(4000)
        self._confirm_if_any(page)   # 预览弹窗里若还有"确认发布"类按钮
        page.wait_for_timeout(2000)
        print("    最终提交动作已完成")

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
