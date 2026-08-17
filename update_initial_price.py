#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新产品期初价格：
1. 用 baostock 拉取中证1000历史K线
2. 按期初观察日匹配收盘价
3. 重新计算敲出/敲入价格
4. 更新 products.json
"""

import json
import baostock as bs
from datetime import datetime

DATA_FILE = 'D:/AI/sonwbo/data/products.json'

def fetch_kline(index_code='sh.000852', start_date='2025-09-01', end_date='2026-08-17'):
    """拉取历史K线，返回 {date: close_price} 字典"""
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"baostock登录失败: {lg.error_msg}")
    
    rs = bs.query_history_k_data_plus(
        index_code,
        'date,close',
        start_date=start_date,
        end_date=end_date,
        frequency='d'
    )
    
    price_map = {}
    while (rs.error_code == '0') & rs.next():
        row = rs.get_row_data()
        date_str = row[0]
        close_price = float(row[1])
        price_map[date_str] = close_price
    
    bs.logout()
    print(f"拉取完成: {len(price_map)} 条K线数据")
    return price_map

def update_products():
    # 1. 拉取历史数据
    price_map = fetch_kline()
    
    # 2. 加载产品数据
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    missing_dates = []
    
    for product in data['products']:
        obs_date = product.get('initial_observation_date')
        if not obs_date:
            continue
        
        # 匹配期初观察日收盘价
        if obs_date in price_map:
            initial_price = round(price_map[obs_date], 2)
            product['initial_price'] = initial_price
            
            # 重新计算敲出/敲入价格
            ko_ratio = product.get('knock_out_ratio', 100)
            ki_ratio = product.get('knock_in_ratio', 100)
            
            product['knock_out_price'] = round(initial_price * (ko_ratio / 100), 2)
            product['knock_in_price'] = round(initial_price * (ki_ratio / 100), 2)
            
            updated_count += 1
            print(f"✓ {product['code']}: 期初观察日={obs_date}, 期初价={initial_price}, "
                  f"敲出={product['knock_out_price']}, 敲入={product['knock_in_price']}")
        else:
            missing_dates.append((product['code'], obs_date))
            print(f"✗ {product['code']}: 期初观察日={obs_date} 无数据")
    
    # 3. 保存
    data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n更新完成: {updated_count}/{len(data['products'])} 只产品")
    if missing_dates:
        print(f"缺失数据: {len(missing_dates)} 个日期")
        for code, d in missing_dates:
            print(f"  {code}: {d}")

if __name__ == '__main__':
    update_products()
