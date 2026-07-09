#!/usr/bin/env python3
"""
login.py —— 第一步：为某个账号登录（登录态记在该账号的独立 Chrome profile 里）

和之前 CDP 方案的区别：脚本自己用真实 Chrome 启动这个账号专属的 profile 目录，
你在弹出的窗口里登录一次，登录态就永久记在 profile_dir 里。
之后 publish.py 用同一个 profile 启动，就是已登录状态，不用再管 cookie 文件。

用法：
    python login.py hans_toutiao
（参数是 accounts.yaml 里的账号 name）
"""
from __future__ import annotations

import sys
import pathlib
from playwright.sync_api import sync_playwright

from config import get_account
from publishers import get_publisher


def main():
    if len(sys.argv) < 2:
        print("用法：python login.py <账号name>   例如：python login.py hans_toutiao")
        sys.exit(1)

    account = get_account(sys.argv[1])
    publisher = get_publisher(account)   # 借用发布器知道该平台的首页和登录判断
    profile_dir = account["profile_dir"]
    pathlib.Path(profile_dir).mkdir(parents=True, exist_ok=True)

    print(f"→ 账号：{account['name']}  平台：{account['platform']}")
    print(f"→ 用真实 Chrome 启动专属 profile：{profile_dir}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel=account.get("browser_channel", "chrome"),
            headless=False,   # 登录必须有界面
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(publisher.LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        print()
        print("请在弹出的 Chrome 窗口里登录该平台后台（扫码或账号密码都行）。")
        print(f"平台后台：{publisher.LOGIN_URL}")
        print()
        input("确认窗口里已是【登录后】的后台页面后，回到这里按回车 ...")

        # 刷新并检测登录状态
        page.goto(publisher.LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        if publisher.is_logged_in(page):
            print(f"✅ 登录成功，登录态已保存在 profile：{profile_dir}")
            print("   之后 publish.py 用这个 profile 启动就是已登录状态。")
        else:
            print("⚠️ 仍检测为未登录。请确认确实登录了；若确认登录了但这里判错，")
            print("   可能是 is_logged_in 的判断规则需要按实际页面微调（在对应 publisher 里）。")

        context.close()


if __name__ == "__main__":
    main()
