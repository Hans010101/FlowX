"""
publishers 包入口 —— 发布器注册表（工厂）

编排层拿到一条账号配置后，用 get_publisher(account) 就能得到对应平台的发布器，
完全不用写 if platform == "toutiao" 这种分支。

加平台 = 在 REGISTRY 里加一行。
"""

from .base import BasePublisher, Article, PublishResult
from .toutiao import ToutiaoPublisher
from .baijiahao import BaijiahaoPublisher

# platform 字符串 -> 发布器类
REGISTRY: dict[str, type[BasePublisher]] = {
    "toutiao": ToutiaoPublisher,
    "baijiahao": BaijiahaoPublisher,
    # 以后加平台就在这里加一行，例如：
    # "dayuhao": DayuhaoPublisher,
}


def get_publisher(account: dict) -> BasePublisher:
    """按账号配置里的 platform 返回对应发布器实例。"""
    platform = account.get("platform")
    if platform not in REGISTRY:
        raise ValueError(
            f"未知平台 '{platform}'，已支持：{list(REGISTRY.keys())}。"
            "如需新增，请在 publishers/ 下实现并注册到 REGISTRY。"
        )
    return REGISTRY[platform](account)


__all__ = [
    "BasePublisher", "Article", "PublishResult",
    "REGISTRY", "get_publisher",
]
