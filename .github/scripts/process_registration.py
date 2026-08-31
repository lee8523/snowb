#!/usr/bin/env python3
"""
GitHub Actions 脚本：自动处理用户注册申请
从 Issue 内容中提取用户信息，验证后写入 users.json
"""

import os
import re
import json
from datetime import datetime, timezone

def parse_issue_body(body):
    """解析 Issue 内容，提取用户注册信息"""
    # 尝试多种可能的格式
    username_match = re.search(r'(?:\*\*)?用户名 (?:\*\*)?:\s*(.+)', body, re.IGNORECASE)
    password_hash_match = re.re.search(r'(?:\*\*)?密码 (?:哈希)?(?:\*\*)?:\s*(\S+)', body, re.IGNORECASE)
    email_match = re.search(r'(?:\*\*)?邮箱 (?:\*\*)?:\s*(.+)', body, re.IGNORECASE)
    captcha_match = re.search(r'(?:\*\*)?验证答案 (?:\*\*)?:\s*(.+)', body, re.IGNORECASE)
    
    if not all([username_match, password_hash_match, captcha_match]):
        print("无法解析必要字段")
        return None
    
    username = username_match.group(1).strip()
    password_hash = password_hash_match.group(1).strip()
    email = email_match.group(1).strip() if email_match else None
    captcha_answer = captcha_match.group(1).strip() if captcha_match else None
    
    # 验证问题答案（必须包含"中国银行"和"分行"）
    if not captcha_answer or '中国银行' not in captcha_answer or '分行' not in captcha_answer:
        print(f"验证问题答案错误：{captcha_answer}")
        return None
    
    # 验证用户名格式（6-20 位字母数字下划线）
    if len(username) < 6 or len(username) > 20:
        print(f"用户名长度不符合要求：{username} (长度{len(username)})")
        return None
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        print(f"用户名格式不符合要求：{username}")
        return None
    
    return {
        'username': username,
        'password_hash': password_hash,
        'email': email,
        'captcha_verified': True,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'registered_via': 'github_issue_auto'
    }

def main():
    issue_body = os.environ.get('ISSUE_BODY', '')
    
    if not issue_body:
        print("未找到 Issue 内容")
        return
    
    user_info = parse_issue_body(issue_body)
    
    if not user_info:
        print("用户信息解析失败或验证未通过")
        # 退出码 1 表示失败，GitHub Actions 会标记为 failure
        exit(1)
    
    # 读取现有的 users.json
    users_file_path = 'data/users.json'
    if os.path.exists(users_file_path):
        with open(users_file_path, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
    else:
        users_data = {'users': [], 'last_updated': datetime.now(timezone.utc).isoformat()}
    
    # 检查用户名是否已存在
    existing_usernames = [u['username'] for u in users_data.get('users', [])]
    if user_info['username'] in existing_usernames:
        print(f"用户名 {user_info['username']} 已存在")
        exit(1)
    
    # 添加新用户
    users_data['users'].append(user_info)
    users_data['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    # 确保目录存在
    os.makedirs('data', exist_ok=True)
    
    # 写入 users.json
    with open(users_file_path, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 用户 {user_info['username']} 注册成功！")

if __name__ == '__main__':
    main()
