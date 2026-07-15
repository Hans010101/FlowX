"""
base.py —— 发布器统一接口（所有平台共用）

关键设计：publish() 带一个 as_draft 开关。
- as_draft=True  → 存草稿箱（前几天用这个，自动存不发出）
- as_draft=False → 直接发布（验证内容OK后切这个，全自动直发）
两者共用同一个发布页、同一批选择器，只是最后点的按钮不同。
所以"手动那几天"和"以后全自动"是同一套代码，改个开关而已。
"""

from __future__ import annotations

import time
import pathlib
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright, Page, BrowserContext
from .models import Article, PublishResult


# ---------- 发布器基类 ----------

class BasePublisher(ABC):
    platform: str = "base"
    LOGIN_URL: str = ""
    PUBLISH_URL: str = ""

    def __init__(self, account: dict):
        self.account = account
        self.name = account.get("name", "unknown")
        self.profile_dir = account["profile_dir"]
        self.channel = account.get("browser_channel", "chrome")
        self.headless = account.get("headless", False)

    def _launch(self, p) -> BrowserContext:
        pathlib.Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
        return p.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            channel=self.channel,
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

    def _screenshot(self, page: Page, tag: str):
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = f"logs/{self.platform}-{self.name}-{tag}-{ts}.png"
        pathlib.Path("logs").mkdir(exist_ok=True)
        try:
            page.screenshot(path=path)
            return path
        except Exception:
            return None

    def save_draft(self, article: Article) -> PublishResult:
        """存草稿箱（便捷方法）。前几天用这个。"""
        return self._run(article, as_draft=True)

    def publish(self, article: Article) -> PublishResult:
        """直接发布。验证内容OK后用这个。"""
        return self._run(article, as_draft=False)

    def _run(self, article: Article, as_draft: bool) -> PublishResult:
        with sync_playwright() as p:
            context = self._launch(p)
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                if not self.is_logged_in(page):
                    shot = self._screenshot(page, "not-logged-in")
                    return PublishResult(
                        ok=False, platform=self.platform, account=self.name,
                        as_draft=as_draft,
                        error=f"未登录，请先运行 login.py 登录该账号。截图：{shot}",
                    )
                result = self.do_publish(page, article, as_draft=as_draft)
                result.platform = self.platform
                result.account = self.name
                result.as_draft = as_draft
                return result
            except Exception as e:
                shot = self._screenshot(page, "error")
                return PublishResult(
                    ok=False, platform=self.platform, account=self.name,
                    as_draft=as_draft,
                    error=f"{type(e).__name__}: {e} | 截图：{shot}",
                )
            finally:
                context.close()

    # ---- 子类实现 ----
    @abstractmethod
    def is_logged_in(self, page: Page) -> bool: ...

    @abstractmethod
    def do_publish(self, page: Page, article: Article, as_draft: bool) -> PublishResult:
        """填标题/正文/封面；as_draft 决定最后点『存草稿』还是『发布』。"""
        ...
