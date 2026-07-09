"""
schedule_plan.py —— 把当天要发的 N 篇，错开排到 07:00–23:00 的定时发布时间

规则：均匀铺开 + 随机抖动，避免整点规律（防风控）；不排到过去时间；
若跑得太晚（当天排不下），顺延到次日 07:00 起。
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta


def schedule_times(n: int, now: datetime | None = None,
                   start_hour: int = 7, end_hour: int = 23,
                   buffer_min: int = 20) -> list[datetime]:
    if n <= 0:
        return []
    now = now or datetime.now()
    start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    # 现在已过 start，就从 now+buffer 开始；若已过 end，顺延到次日
    earliest = now + timedelta(minutes=buffer_min)
    if earliest > start:
        start = earliest
    if start >= end:
        start = (now + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end = (now + timedelta(days=1)).replace(hour=end_hour, minute=0, second=0, microsecond=0)

    window = (end - start).total_seconds()
    step = window / n                      # 每篇一个时段
    times = []
    prev = start - timedelta(minutes=1)
    for i in range(n):
        base = start + timedelta(seconds=step * i + step / 2)   # 落在各时段中点
        jitter = random.uniform(-min(step * 0.3, 600), min(step * 0.3, 600))  # ±抖动，最多10分钟
        t = base + timedelta(seconds=jitter)
        if t <= prev:                      # 保证严格递增
            t = prev + timedelta(minutes=3)
        if t > end:
            t = end
        t = t.replace(second=0, microsecond=0)
        times.append(t)
        prev = t
    return times


if __name__ == "__main__":
    for t in schedule_times(6, datetime(2026, 7, 6, 6, 30)):
        print(t.strftime("%m-%d %H:%M"))
