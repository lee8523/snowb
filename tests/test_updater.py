#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""updater 纯函数与交易日历的单元测试（无网络、无文件依赖）

运行: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_calendar import is_trading_day, next_trading_day
from updater import (
    calc_knock_out_price,
    calc_observation_calendar,
    calc_status,
    get_knock_out_ratio,
)


class TestKnockOutRatio(unittest.TestCase):
    def setUp(self):
        self.product = {
            "knock_out_ratio": 100,
            "knock_out_schedule": [
                {"month": 3, "ratio": 103},
                {"month": 4, "ratio": 101.5},
            ],
        }

    def test_schedule_hit(self):
        self.assertEqual(get_knock_out_ratio(self.product, 3), 103)
        self.assertEqual(get_knock_out_ratio(self.product, 4), 101.5)

    def test_schedule_miss_falls_back_to_fixed(self):
        self.assertEqual(get_knock_out_ratio(self.product, 5), 100)

    def test_no_schedule_no_ratio_defaults_100(self):
        self.assertEqual(get_knock_out_ratio({}, 3), 100)

    def test_knock_out_price(self):
        self.assertEqual(
            calc_knock_out_price({"initial_price": 10000, "knock_out_ratio": 103}, 5), 10300.0
        )
        self.assertEqual(calc_knock_out_price(self.product, 4), 10150.0)

    def test_knock_out_price_defaults(self):
        # 无期初价时按 10000 兜底
        self.assertEqual(calc_knock_out_price({"knock_out_ratio": 100}, 3), 10000.0)


class TestObservationCalendar(unittest.TestCase):
    def test_basic_monthly_sequence(self):
        obs = calc_observation_calendar("2026-01-15", 3, 6)
        self.assertEqual([o["period"] for o in obs], [3, 4, 5, 6])
        self.assertEqual(
            [o["date"] for o in obs],
            ["2026-04-15", "2026-05-15", "2026-06-15", "2026-07-15"],
        )

    def test_all_dates_are_trading_days(self):
        obs = calc_observation_calendar("2026-01-15", 3, 24)
        self.assertEqual(len(obs), 22)
        for o in obs:
            self.assertTrue(is_trading_day(o["date"]), o["date"])

    def test_holiday_rollforward_over_cny(self):
        # 2026-02-20 落在春节假期(2/16-2/22)，顺延到 2/23 周一
        obs = calc_observation_calendar("2025-11-20", 3, 3)
        self.assertEqual(obs[0]["date"], "2026-02-23")

    def test_month_end_clamp_and_weekend_roll(self):
        # 1/31 对日：4 月无 31 日取 4/30；5/31 是周日顺延到 6/1
        obs = calc_observation_calendar("2026-01-31", 3, 4)
        self.assertEqual([o["date"] for o in obs], ["2026-04-30", "2026-06-01"])

    def test_weekend_rollforward_2027(self):
        # 2027-02-20 是周六（2027 春节为 2/5-2/14，此处不冲突），顺延到 2/22 周一
        obs = calc_observation_calendar("2026-11-20", 3, 3)
        self.assertEqual(obs[0]["date"], "2027-02-22")


class TestCalcStatus(unittest.TestCase):
    def test_pending_initial(self):
        p = {"initial_observation_date": "2026-12-01"}
        self.assertEqual(calc_status(p, "2026-09-09"), "待期初")

    def test_knocked_out(self):
        p = {
            "initial_observation_date": "2026-01-10",
            "observation_history": [{"period": 3, "date": "2026-04-10", "status": "已敲出"}],
        }
        self.assertEqual(calc_status(p, "2026-09-09"), "已敲出")

    def test_knocked_in_at_maturity(self):
        p = {
            "initial_observation_date": "2026-01-10",
            "final_observation_date": "2026-06-10",
            "current_price": 6500,
            "knock_in_price": 7000,
        }
        self.assertEqual(calc_status(p, "2026-09-09"), "已敲入")

    def test_knocked_in_boundary_equal_price(self):
        p = {
            "initial_observation_date": "2026-01-10",
            "final_observation_date": "2026-06-10",
            "current_price": 7000,
            "knock_in_price": 7000,
        }
        self.assertEqual(calc_status(p, "2026-09-09"), "已敲入")

    def test_active_before_maturity(self):
        p = {
            "initial_observation_date": "2026-01-10",
            "final_observation_date": "2026-12-10",
            "current_price": 6500,
            "knock_in_price": 7000,
        }
        self.assertEqual(calc_status(p, "2026-09-09"), "存续中")

    def test_matured_above_knock_in_stays_active(self):
        p = {
            "initial_observation_date": "2026-01-10",
            "final_observation_date": "2026-06-10",
            "current_price": 8000,
            "knock_in_price": 7000,
        }
        self.assertEqual(calc_status(p, "2026-09-09"), "存续中")


class TestTradingCalendar(unittest.TestCase):
    def test_known_days(self):
        self.assertTrue(is_trading_day("2026-09-09"))   # 周三
        self.assertFalse(is_trading_day("2026-01-03"))  # 周六
        self.assertFalse(is_trading_day("2026-02-17"))  # 春节
        self.assertFalse(is_trading_day("2026-10-01"))  # 国庆

    def test_next_trading_day_over_weekend(self):
        self.assertEqual(next_trading_day("2026-10-07"), "2026-10-08")

    def test_next_trading_day_over_cny(self):
        # 2026 春节假期 2/16-2/22，从 2/16 直接跳到 2/23
        self.assertEqual(next_trading_day("2026-02-16"), "2026-02-23")


if __name__ == "__main__":
    unittest.main()
