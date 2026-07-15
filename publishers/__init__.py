"""
publishers 包入口 —— 发布器注册表（工厂）

编排层拿到一条账号配置后，用 get_publisher(account) 就能得到对应平台的发布器，
完全不用写 if platform == "toutiao" 这种分支。

加平台 = 在 REGISTRY 里加一行。
"""

from .models import Article, PublishResult

# platform 字符串 -> 发布器类
REGISTRY = {}


def _registry():
    """延迟加载已冻结的 Playwright 发布器，避免核心生成/质检被浏览器依赖绑死。"""
    if not REGISTRY:
        from .base import BasePublisher
        from .toutiao import ToutiaoPublisher
        from .baijiahao import BaijiahaoPublisher
        REGISTRY.update({"toutiao": ToutiaoPublisher, "baijiahao": BaijiahaoPublisher})
    return REGISTRY


def get_publisher(account: dict):
    """按账号配置里的 platform 返回对应发布器实例。"""
    platform = account.get("platform")
    registry = _registry()
    if platform not in registry:
        raise ValueError(
            f"未知平台 '{platform}'，已支持：{list(registry.keys())}。"
            "如需新增，请在 publishers/ 下实现并注册到 REGISTRY。"
        )
    return registry[platform](account)


__all__ = [
    "Article", "PublishResult", "REGISTRY", "get_publisher",
]
