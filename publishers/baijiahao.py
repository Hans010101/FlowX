"""
baijiahao.py —— 百家号发布器（占位）

以后要加百家号时，只需要把下面两个方法按百家号后台实测填好即可，
其它代码（编排、登录工具、配置）一行都不用动——这就是多平台骨架的意义。

百家号后台：https://baijiahao.baidu.com/
图文发布页一般在：https://baijiahao.baidu.com/builder/rich/home
（具体以实测为准，用 playwright codegen 扒选择器。）
"""

from __future__ import annotations

from playwright.sync_api import Page

from .base import BasePublisher, Article, PublishResult


class BaijiahaoPublisher(BasePublisher):
    platform = "baijiahao"
    LOGIN_URL = "https://baijiahao.baidu.com/"
    PUBLISH_URL = "https://baijiahao.baidu.com/builder/rich/home"

    def is_logged_in(self, page: Page) -> bool:
        url = page.url
        if any(k in url for k in ("login", "passport", "wappass")):
            return False
        return True

    def do_publish(self, page: Page, article: Article, as_draft: bool) -> PublishResult:
        raise NotImplementedError(
            "百家号发布器尚未实现。以后需要时，按本文件说明用 codegen 扒出选择器，"
            "参照 toutiao.py 的结构填好 do_publish 即可。"
        )
