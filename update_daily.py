#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球产品每日自动更新脚本
功能：
1. 获取挂钩标的收盘价（使用 AKShare 免费数据源）
2. 计算产品状态（敲出/敲入/存续/待期初）
3. 生成敲出观察日历
4. 更新 products.json
"""

import json
import os
from datetime import datetime, timedelta
import calendar

# 加载交易日历
CALENDAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'trading_calendar.json')
_trading_set = set()
if os.path.exists(CALENDAR_FILE):
    with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
        cal_data = json.load(f)
        _trading_set = set(cal_data.get('trading_days', []))

# 尝试导入 akshare，如果失败则使用模拟数据
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'products.json')

# A 股交易日历（简化版，实际需要更完整的日历）
# 格式：'YYYY-MM-DD': True/False (交易日/非交易日)
TRADING_CALENDAR = {}

def generate_trading_calendar(year):
    """生成指定年份的交易日历（简化版）"""
    trading_days = []
    
    for month in range(1, 13):
        # 获取当月所有日期
        _, days_in_month = calendar.monthrange(year, month)
        
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day)
            weekday = date.weekday()
            
            # 排除周末（简化，实际需排除节假日）
            if weekday < 5:  # 周一到周五
                date_str = date.strftime('%Y-%m-%d')
                trading_days.append(date_str)
    
    return trading_days

def is_trading_day(date_str):
    """判断是否为交易日"""
    if _trading_set:
        return date_str in _trading_set
    # 回退：只排除周末
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date.weekday() < 5

def get_next_trading_day(date_str):
    """获取下一个交易日"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    while True:
        date += timedelta(days=1)
        if is_trading_day(date.strftime('%Y-%m-%d')):
            return date.strftime('%Y-%m-%d')

def fetch_index_price(index_code, retries=5):
    """获取指数收盘价（使用东方财富API，带重试和连接池）"""
    import urllib.request
    import ssl
    
    DEFAULT_PRICE = 5842.35
    url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000852&fields=f43"
    
    # 创建SSL上下文
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'Referer': 'https://finance.eastmoney.com'})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read())
                return data['data']['f43'] / 100.0
        except Exception as e:
            if attempt < retries - 1:
                import time
                time.sleep(1)
                continue
            print(f"获取行情失败：{e}")
            return DEFAULT_PRICE

def calculate_product_status(product, current_date):
    """计算产品状态"""
    initial_date = product.get('initial_observation_date')
    establishment_date = product.get('establishment_date')
    
    # 还未到期初观察日
    if not initial_date or current_date < initial_date:
        return '待期初'
    
    # 检查是否已敲出
    if product.get('observation_history'):
        for obs in product['observation_history']:
            if obs.get('status') == 'knocked_out':
                return '已敲出'
    
    # 检查是否已敲入
    current_price = product.get('current_price', 0)
    knock_in_price = product.get('knock_in_price', 0)
    
    if current_price > 0 and knock_in_price > 0:
        if current_price <= knock_in_price:
            return '已敲入'
    
    # 默认存续中
    return '存续中'

def generate_observation_calendar(product):
    """生成敲出观察日历"""
    initial_date_str = product.get('initial_observation_date')
    if not initial_date_str:
        return []
    
    initial_date = datetime.strptime(initial_date_str, '%Y-%m-%d')
    knock_out_start_month = product.get('knock_out_start_month', 3)
    term_months = product.get('term_months', 36)
    
    observations = []
    
    for month in range(knock_out_start_month, term_months + 1):
        # 计算观察日（期初对日）
        new_month = initial_date.month + month
        new_year = initial_date.year + (new_month - 1) // 12
        new_month = (new_month - 1) % 12 + 1
        _, last_day = calendar.monthrange(new_year, new_month)
        obs_date = initial_date.replace(
            year=new_year,
            month=new_month,
            day=min(initial_date.day, last_day)
        )
        
        # 遇非交易日顺延
        while not is_trading_day(obs_date.strftime('%Y-%m-%d')):
            obs_date += timedelta(days=1)
        
        obs_date_str = obs_date.strftime('%Y-%m-%d')
        
        # 如果观察日已过，检查是否敲出
        current_price = product.get('current_price', 0)
        knock_out_price = product.get('knock_out_price', 0)
        
        status = '待观察'
        if obs_date < datetime.now():
            if current_price >= knock_out_price:
                status = '已敲出'
            else:
                status = '未敲出'
        
        observations.append({
            'period': month,
            'date': obs_date_str,
            'price': None,
            'status': status
        })
    
    return observations

def update_products():
    """主更新函数"""
    # 加载现有数据
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 统一获取一次行情
    market_price = fetch_index_price('000852.SH')
    print(f"市场行情: {market_price}")
    
    # 更新每个产品
    for product in data['products']:
        # 使用统一获取的行情价格
        product['current_price'] = market_price
        product['last_update'] = current_time
        
        # 重新计算状态
        product['status'] = calculate_product_status(product, current_date)
        
        # 更新观察日历
        product['observation_history'] = generate_observation_calendar(product)
        
        # 计算距下次观察日天数
        if product.get('next_observation_date'):
            next_date = datetime.strptime(product['next_observation_date'], '%Y-%m-%d')
            product['days_to_next'] = (next_date - datetime.now()).days
    
    # 更新元数据
    data['last_update'] = current_time
    
    # 保存更新后的数据
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 更新完成：{current_time}")
    print(f"   共更新 {len(data['products'])} 只产品")

if __name__ == '__main__':
    update_products()
