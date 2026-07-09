import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://mp.toutiao.com/auth/page/login?redirect_url=JTJGcHJvZmlsZV92NCUyRmdyYXBoaWMlMkZwdWJsaXNo")
    page.locator("div").filter(has_text="验证码登录获取验证码我已阅读并同意《用户协议》和《隐私政策》登录扫码登录“今日头条App - 我的”左上角“扫一扫”其他登录方式抖音登录QQ").nth(2).click()
    page.goto("https://mp.toutiao.com/profile_v4/graphic/publish?is_new_connect=0&is_new_user=0")
    page.locator(".byte-drawer-mask").click()
    page.get_by_role("textbox", name="请输入文章标题（2～30个字）").click()
    page.locator("div").filter(has_text=re.compile(r"^请输入正文$")).click()
    page.get_by_role("paragraph").click()
    page.get_by_role("textbox", name="请输入文章标题（2～30个字）").click()
    page.get_by_role("textbox", name="请输入文章标题（2～30个字）").fill("测试")
    page.get_by_role("paragraph").click()
    page.locator("div").filter(has_text=re.compile(r"^请输入正文$")).click()
    page.get_by_role("paragraph").click()
    page.locator(".add-icon").click()
    page.get_by_role("button", name="本地上传 Choose File").locator("input[type=\"file\"]").click()
    page.get_by_role("button", name="本地上传 Choose File").locator("input[type=\"file\"]").set_input_files("be2556095c.jpg")
    page.locator(".img-wrap > img").click()
    page.locator(".img-wrap > img").click()
    page.get_by_text("免费正版图片").click()
    page.get_by_role("listitem").nth(2).click()
    page.get_by_role("button", name="确定").nth(1).click()
    page.get_by_role("button", name="定时发布").click()
    page.locator("button").filter(has_text="预览并定时发布").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
