#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TigerAPI 登录测试和诊断工具
用于排查登录和 Session 获取问题
"""

import sys
import os
import requests
import json
from datetime import datetime

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ANSI 颜色代码
class Colors:
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_step(step, text):
    print(f"{Colors.BLUE}[{step}]{Colors.RESET} {text}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(key, value):
    print(f"  {Colors.CYAN}{key}:{Colors.RESET} {value}")

def load_config():
    """从 status-final.py 读取 TigerAPI 配置"""
    config_file = os.path.expanduser('~/.claude/status-final.py')

    if not os.path.exists(config_file):
        print_error(f"配置文件不存在: {config_file}")
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        url_match = re.search(r'TIGER_API_URL\s*=\s*["\'](.+?)["\']', content)
        user_match = re.search(r'TIGER_USERNAME\s*=\s*["\'](.+?)["\']', content)
        pass_match = re.search(r'TIGER_PASSWORD\s*=\s*["\'](.+?)["\']', content)
        quota_match = re.search(r'TIGER_QUOTA_PER_UNIT\s*=\s*(\d+)', content)

        if not url_match or not user_match or not pass_match:
            print_error("配置文件中未找到 TigerAPI 配置项")
            return None

        config = {
            'url': url_match.group(1),
            'username': user_match.group(1),
            'password': pass_match.group(1),
            'quota_per_unit': int(quota_match.group(1)) if quota_match else 500000
        }

        # 检查是否为默认值
        if config['url'] == "https://your-tiger-api-url.com" or config['username'] == "your-username":
            print_error("配置文件包含默认值，请先配置您的 TigerAPI 信息")
            print_info("配置文件路径", config_file)
            return None

        return config

    except Exception as e:
        print_error(f"读取配置文件失败: {e}")
        return None

def test_network(api_url):
    """测试网络连接"""
    print_step("1/4", "测试网络连接...")

    try:
        response = requests.get(api_url, timeout=5)
        print_success(f"网络连接正常 (状态码: {response.status_code})")
        return True
    except requests.exceptions.Timeout:
        print_error("网络连接超时，请检查网络设置")
        return False
    except requests.exceptions.ConnectionError:
        print_error(f"无法连接到 {api_url}，请检查网络或防火墙设置")
        return False
    except Exception as e:
        print_error(f"网络测试失败: {e}")
        return False

def test_login(api_url, username, password):
    """测试 TigerAPI 登录"""
    print_step("2/4", "测试登录...")
    print_info("API URL", api_url)
    print_info("用户名", username)
    print_info("密码", "*" * len(password))

    try:
        session = requests.Session()
        response = session.post(
            f'{api_url}/api/user/login',
            headers={
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json={
                'username': username,
                'password': password
            },
            timeout=10
        )

        print_info("HTTP 状态码", response.status_code)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                user_id = data.get('data', {}).get('id')
                session_cookie = session.cookies.get('session')

                if session_cookie and user_id:
                    print_success(f"登录成功！获取到 Session (user_id: {user_id})")
                    print_info("Session 前30字符", session_cookie[:30] + "...")
                    return {'session': session_cookie, 'user_id': user_id}
                else:
                    print_error("登录成功但未获取到 Session Cookie 或 User ID")
                    print_info("响应数据", json.dumps(data, indent=2, ensure_ascii=False))
                    return None
            else:
                error_msg = data.get('message', '未知错误')
                print_error(f"登录失败: {error_msg}")
                return None
        elif response.status_code == 401:
            print_error("用户名或密码错误，请检查配置")
            return None
        else:
            print_error(f"登录请求失败，HTTP 状态码: {response.status_code}")
            print_info("响应内容", response.text[:200])
            return None

    except requests.exceptions.Timeout:
        print_error("登录请求超时")
        return None
    except Exception as e:
        print_error(f"登录测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def test_user_info(api_url, session_info, quota_per_unit):
    """测试获取用户信息"""
    print_step("3/4", "测试获取用户信息...")

    try:
        response = requests.get(
            f'{api_url}/api/user/self',
            headers={
                'accept': 'application/json, text/plain, */*',
                'new-api-user': str(session_info['user_id']),
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            cookies={'session': session_info['session']},
            timeout=10
        )

        print_info("HTTP 状态码", response.status_code)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                user_data = data.get('data', {})
                quota = user_data.get('quota', 0)
                used_quota = user_data.get('used_quota', 0)

                balance_usd = quota / quota_per_unit
                used_usd = used_quota / quota_per_unit

                print_success("成功获取用户信息！")
                print_info("原始配额", f"{quota}")
                print_info("已使用配额", f"{used_quota}")
                print_info("余额(USD)", f"${balance_usd:.2f}")
                print_info("已使用(USD)", f"${used_usd:.2f}")
                return True
            else:
                print_error("获取用户信息失败")
                print_info("响应", json.dumps(data, indent=2, ensure_ascii=False))
                return False
        else:
            print_error(f"API 请求失败，HTTP 状态码: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"获取用户信息失败: {e}")
        return False

def save_session(session_info):
    """保存 Session 到缓存文件"""
    print_step("4/4", "保存 Session 到缓存...")

    cache_file = os.path.expanduser('~/.claude/.tiger_session')

    try:
        cache_data = {
            'session': session_info['session'],
            'user_id': session_info['user_id'],
            'timestamp': time.time()
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print_success(f"Session 已保存到: {cache_file}")

        if os.path.exists(cache_file):
            file_size = os.path.getsize(cache_file)
            print_info("文件大小", f"{file_size} 字节")
            print_info("修改时间", datetime.fromtimestamp(os.path.getmtime(cache_file)).strftime('%Y-%m-%d %H:%M:%S'))

        return True
    except Exception as e:
        print_error(f"保存 Session 失败: {e}")
        return False

def main():
    print_header("TigerAPI 登录诊断工具")

    print("本工具将帮助您诊断 TigerAPI 登录和余额获取问题\n")

    # 加载配置
    print_step("0/4", "读取配置文件...")
    config = load_config()

    if not config:
        print("\n" + "="*60)
        print(f"{Colors.RED}配置检查失败，无法继续{Colors.RESET}")
        print("="*60)
        print("\n请先配置您的 TigerAPI 信息:")
        print(f"  1. 编辑文件: {Colors.CYAN}~/.claude/status-final.py{Colors.RESET}")
        print(f"  2. 修改以下配置:")
        print(f"     {Colors.YELLOW}TIGER_API_URL = \"https://your-tiger-api-url.com\"{Colors.RESET}")
        print(f"     {Colors.YELLOW}TIGER_USERNAME = \"your-username\"{Colors.RESET}")
        print(f"     {Colors.YELLOW}TIGER_PASSWORD = \"your-password\"{Colors.RESET}")
        print(f"  3. 替换为您的真实 TigerAPI 信息")
        return 1

    print_success("配置文件读取成功")
    print()

    # 测试网络
    if not test_network(config['url']):
        return 1
    print()

    # 测试登录
    session_info = test_login(config['url'], config['username'], config['password'])
    if not session_info:
        print("\n" + "="*60)
        print(f"{Colors.RED}登录失败{Colors.RESET}")
        print("="*60)
        print("\n可能的原因:")
        print("  1. 用户名或密码错误")
        print("  2. API 地址不正确")
        print("  3. 网络问题")
        print("\n建议:")
        print("  1. 检查配置文件中的用户名密码是否正确")
        print("  2. 确认 TigerAPI 地址可以访问")
        print("  3. 检查网络连接和防火墙设置")
        return 1
    print()

    # 测试获取用户信息
    if not test_user_info(config['url'], session_info, config['quota_per_unit']):
        return 1
    print()

    # 保存 Session
    if not save_session(session_info):
        return 1

    # 成功
    print("\n" + "="*60)
    print(f"{Colors.GREEN}{Colors.BOLD}诊断完成！所有测试通过 ✓{Colors.RESET}")
    print("="*60)
    print("\n您的状态栏脚本现在应该可以正常工作了")
    print("请重启 Claude Code 查看状态栏\n")

    return 0

if __name__ == "__main__":
    import time
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}用户中断{Colors.RESET}")
        sys.exit(1)
