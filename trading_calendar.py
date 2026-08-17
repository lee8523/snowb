#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日历模块
- 手动维护国务院公布的节假日安排（2026-2030）
- 提供 is_trading_day / next_trading_day 接口
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ── 节假日配置（国务院公布的放假安排）──
# 格式: 年份 -> [(开始月日, 结束月日, 名称)]
HOLIDAYS = {
    2026: [
        ((1, 1), (1, 1), "元旦"),
        ((2, 16), (2, 22), "春节"),   # 除夕到初六
        ((4, 4), (4, 6), "清明"),
        ((5, 1), (5, 5), "劳动节"),
        ((6, 19), (6, 21), "端午"),
        ((9, 25), (9, 27), "中秋"),
        ((10, 1), (10, 7), "国庆"),
    ],
    2027: [
        ((1, 1), (1, 1), "元旦"),
        ((2, 5), (2, 14), "春节"),   # 除夕到初九，2月15日上班
        ((4, 4), (4, 6), "清明"),
        ((5, 1), (5, 5), "劳动节"),
        ((6, 9), (6, 11), "端午"),
        ((9, 15), (9, 17), "中秋"),
        ((10, 1), (10, 7), "国庆"),
    ],
    2028: [
        ((1, 1), (1, 1), "元旦"),
        ((1, 25), (1, 31), "春节"),   # 除夕到初六
        ((4, 4), (4, 6), "清明"),
        ((5, 1), (5, 5), "劳动节"),
        ((5, 28), (5, 30), "端午"),
        ((10, 3), (10, 5), "中秋"),
        ((10, 1), (10, 7), "国庆"),
    ],
    2029: [
        ((1, 1), (1, 1), "元旦"),
        ((2, 12), (2, 18), "春节"),   # 除夕到初六
        ((4, 4), (4, 6), "清明"),
        ((5, 1), (5, 5), "劳动节"),
        ((6, 16), (6, 18), "端午"),
        ((9, 22), (9, 24), "中秋"),
        ((10, 1), (10, 7), "国庆"),
    ],
    2030: [
        ((1, 1), (1, 1), "元旦"),
        ((2, 2), (2, 8), "春节"),    # 除夕到初六
        ((4, 4), (4, 6), "清明"),
        ((5, 1), (5, 5), "劳动节"),
        ((6, 5), (6, 7), "端午"),
        ((9, 12), (9, 14), "中秋"),
        ((10, 1), (10, 7), "国庆"),
    ],
}


def _build_holiday_set() -> set[str]:
    """根据 HOLIDAYS 生成所有节假日日期集合"""
    holidays = set()
    for year, periods in HOLIDAYS.items():
        for (start_month, start_day), (end_month, end_day), _ in periods:
            start = datetime(year, start_month, start_day)
            end = datetime(year, end_month, end_day)
            current = start
            while current <= end:
                holidays.add(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
    return holidays


# 预计算节假日集合
_HOLIDAY_SET = _build_holiday_set()


def is_trading_day(date_str: str) -> bool:
    """判断是否为交易日（排除周末 + 国务院节假日）"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # 周末
    if dt.weekday() >= 5:
        return False
    # 节假日
    if date_str in _HOLIDAY_SET:
        return False
    return True


def next_trading_day(date_str: str) -> str:
    """获取下一个交易日"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    while True:
        dt += timedelta(days=1)
        s = dt.strftime("%Y-%m-%d")
        if is_trading_day(s):
            return s


def generate_trading_calendar(start_year: int = 2025, end_year: int = 2030) -> list[str]:
    """生成指定年份范围的交易日历"""
    import calendar
    trading_days = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            _, last_day = calendar.monthrange(year, month)
            for day in range(1, last_day + 1):
                dt = datetime(year, month, day)
                date_str = dt.strftime("%Y-%m-%d")
                if is_trading_day(date_str):
                    trading_days.append(date_str)
    return trading_days


def save_calendar(path: str | Path = "data/trading_calendar.json"):
    """生成并保存交易日历到 JSON"""
    trading_days = generate_trading_calendar()
    data = {"trading_days": trading_days}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(trading_days)


# ── 兼容旧版 JSON 日历（如果存在则加载）──
_trading_set = set()
_calendar_file = Path(__file__).parent / "data" / "trading_calendar.json"
if _calendar_file.exists():
    with open(_calendar_file, "r", encoding="utf-8") as f:
        _trading_set = set(json.load(f).get("trading_days", []))


def is_trading_day_json(date_str: str) -> bool:
    """优先使用 JSON 日历（如果已生成），否则用代码逻辑"""
    if _trading_set:
        return date_str in _trading_set
    return is_trading_day(date_str)
