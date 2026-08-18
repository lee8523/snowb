#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球产品数据更新模块
- 期初价：按期初观察日指数收盘价
- 每日价：更新当前指数价格
- 状态：敲出/敲入/存续/待期初
- 观察日历：生成敲出观察日序列
"""

import json
import os
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path

import baostock as bs

from trading_calendar import is_trading_day

# ── 路径 ──
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "products.json"
BACKUP_DIR = DATA_DIR / "backup"


# ── 行情 ──
def fetch_index_price(index_code="sh.000852") -> float | None:
    """获取指数最新收盘价，失败返回 None"""
    try:
        lg = bs.login()
        if lg.error_code != "0":
            return None
        
        today = date.today().strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(
            index_code, "date,close",
            start_date=today, end_date=today, frequency="d"
        )
        price = None
        while (rs.error_code == "0") & rs.next():
            price = float(rs.get_row_data()[1])
        bs.logout()
        return price
    except Exception:
        return None


def fetch_kline(index_code="sh.000852", start_date: str = None, end_date: str = None) -> dict[str, float]:
    """拉取历史K线，返回 {date: close}"""
    if end_date is None:
        end_date = date.today().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock登录失败: {lg.error_msg}")
    
    rs = bs.query_history_k_data_plus(
        index_code, "date,close",
        start_date=start_date, end_date=end_date, frequency="d"
    )
    
    price_map = {}
    while (rs.error_code == "0") & rs.next():
        row = rs.get_row_data()
        price_map[row[0]] = float(row[1])
    
    bs.logout()
    return price_map


# ── 产品计算 ──
def get_knock_out_ratio(product: dict, month: int) -> float:
    """获取指定月份的敲出系数，无逐月序列则返回固定系数"""
    schedule = product.get("knock_out_schedule", [])
    for item in schedule:
        if item.get("month") == month:
            return item.get("ratio", product.get("knock_out_ratio", 100))
    return product.get("knock_out_ratio", 100)


def calc_knock_out_price(product: dict, month: int) -> float:
    """计算指定月份的敲出价格"""
    initial_price = product.get("initial_price", 10000)
    ratio = get_knock_out_ratio(product, month)
    return round(initial_price * (ratio / 100), 2)


def calc_observation_calendar(initial_date: str, start_month: int, term_months: int) -> list[dict]:
    """生成敲出观察日历"""
    import calendar as cal
    
    dt = datetime.strptime(initial_date, "%Y-%m-%d")
    observations = []
    
    for m in range(start_month, term_months + 1):
        new_month = dt.month + m
        new_year = dt.year + (new_month - 1) // 12
        new_month = (new_month - 1) % 12 + 1
        _, last_day = cal.monthrange(new_year, new_month)
        
        obs = dt.replace(year=new_year, month=new_month, day=min(dt.day, last_day))
        obs_str = obs.strftime("%Y-%m-%d")
        
        # 遇非交易日顺延
        while not is_trading_day(obs_str):
            obs += timedelta(days=1)
            obs_str = obs.strftime("%Y-%m-%d")
        
        observations.append({
            "period": m,
            "date": obs_str,
            "price": None,
            "status": "待观察"
        })
    
    return observations


def calc_status(product: dict, today: str) -> str:
    """
    计算产品状态：
    - 待期初：今天 < 期初观察日
    - 已敲出：任一观察日价格 >= 对应月份敲出价
    - 存续中：到期前未敲出未敲入
    - 已敲入：期末观察日价格 < 敲入价（且未敲出）
    """
    initial_date = product.get("initial_observation_date")
    final_date = product.get("final_observation_date")
    
    if initial_date and today < initial_date:
        return "待期初"
    
    # 检查是否已敲出
    for obs in product.get("observation_history", []):
        if obs.get("status") == "已敲出":
            return "已敲出"
    
    # 敲入只在期末判断
    if final_date and today >= final_date:
        current_price = product.get("current_price", 0)
        knock_in_price = product.get("knock_in_price", 0)
        if current_price > 0 and knock_in_price > 0 and current_price <= knock_in_price:
            return "已敲入"
    
    return "存续中"


# ── IO ──
def load_data() -> dict:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    """保存数据，带备份"""
    BACKUP_DIR.mkdir(exist_ok=True)
    
    if DATA_FILE.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"products_{ts}.json"
        shutil.copy2(DATA_FILE, backup_path)
    
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 主流程 ──
def update_initial_prices():
    """更新期初价：按期初观察日指数收盘价，重新计算敲入价格"""
    data = load_data()
    
    dates = [p.get("initial_observation_date") for p in data["products"] if p.get("initial_observation_date")]
    if not dates:
        print("无期初观察日需要更新")
        return
    
    start = min(dates)
    end = max(dates)
    price_map = fetch_kline(start_date=start, end_date=end)
    
    updated = 0
    missing = []
    
    for p in data["products"]:
        obs = p.get("initial_observation_date")
        if not obs:
            continue
        
        if obs in price_map:
            ip = round(price_map[obs], 2)
            p["initial_price"] = ip
            p["knock_in_price"] = round(ip * (p.get("knock_in_ratio", 100) / 100), 2)
            updated += 1
            print(f"  {p['code']}: 期初价={ip}, 敲入={p['knock_in_price']}")
        else:
            missing.append((p["code"], obs))
    
    save_data(data)
    print(f"\n期初价更新: {updated}/{len(data['products'])} 只")
    if missing:
        print(f"缺失: {', '.join(f'{c}({d})' for c, d in missing)}")


def update_daily():
    """每日更新：当前价格、状态、观察日历、距下次观察日天数
    
    敲出判断：用观察日的历史收盘价，不是最新价格
    """
    data = load_data()
    today = date.today().strftime("%Y-%m-%d")
    today_dt = date.today()
    
    market_price = fetch_index_price()
    if market_price is None:
        print("获取行情失败，跳过更新")
        return
    
    print(f"中证1000最新价: {market_price}")
    
    # 收集所有已过但待观察（或需要重新判断）的观察日
    pending_dates = set()
    for p in data["products"]:
        for obs in p.get("observation_history", []):
            if obs["date"] <= today:
                pending_dates.add(obs["date"])
    
    # 拉取历史K线（用于判断敲出）
    price_map = {}
    if pending_dates:
        start = min(pending_dates)
        end = max(pending_dates)
        price_map = fetch_kline(start_date=start, end_date=end)
        print(f"拉取历史K线: {start} ~ {end}, 共 {len(price_map)} 天")
    
    for p in data["products"]:
        p["current_price"] = market_price
        
        # 生成/更新观察日历
        if p.get("initial_observation_date") and not p.get("observation_history"):
            p["observation_history"] = calc_observation_calendar(
                p["initial_observation_date"],
                p.get("knock_out_start_month", 3),
                p.get("term_months", 36)
            )
        
        # 更新观察状态：用观察日历史收盘价判断
        knocked_out = False
        for obs in p.get("observation_history", []):
            if obs["date"] <= today and obs["status"] in ("待观察", "未敲出"):
                ko_price = calc_knock_out_price(p, obs["period"])
                obs_price = price_map.get(obs["date"])
                
                if obs_price is None:
                    # 无历史数据，保持待观察
                    continue
                
                if obs_price >= ko_price:
                    obs["status"] = "已敲出"
                    obs["price"] = obs_price
                    knocked_out = True
                else:
                    obs["status"] = "未敲出"
                    obs["price"] = obs_price
        
        # 计算状态
        p["status"] = calc_status(p, today)
        
        # 已敲出产品：清空下次观察日
        if knocked_out or p["status"] == "已敲出":
            p["next_observation_date"] = None
            p["days_to_next"] = None
        else:
            # 距下次观察日
            for obs in p.get("observation_history", []):
                if obs["date"] >= today:
                    p["next_observation_date"] = obs["date"]
                    obs_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()
                    p["days_to_next"] = (obs_date - today_dt).days
                    break
    
    save_data(data)
    print(f"\n每日更新完成: {len(data['products'])} 只产品")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python updater.py <initial|daily>")
        print("  initial  - 更新期初价（一次性）")
        print("  daily    - 每日更新行情和状态")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "initial":
        update_initial_prices()
    elif cmd == "daily":
        update_daily()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
