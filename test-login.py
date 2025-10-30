#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super-Yi 登录测试和诊断工具
用于排查登录和 Token 获取问题
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
    """打印标题"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_step(step, text):
    """打印步骤"""
    print(f"{Colors.BLUE}[{step}]{Colors.RESET} {text}")

def print_success(text):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(key, value):
    """打印信息"""
    print(f"  {Colors.CYAN}{key}:{Colors.RESET} {value}")

def load_config():
    """从 status-final.py 读取配置"""
    config_file = os.path.expanduser('~/.claude/status-final.py')

    if not os.path.exists(config_file):
        print_error(f"配置文件不存在: {config_file}")
        return None, None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取邮箱和密码
        import re
        email_match = re.search(r'SUPER_YI_EMAIL\s*=\s*["\'](.+?)["\']', content)
        password_match = re.search(r'SUPER_YI_PASSWORD\s*=\s*["\'](.+?)["\']', content)

        if not email_match or not password_match:
            print_error("配置文件中未找到 SUPER_YI_EMAIL 或 SUPER_YI_PASSWORD")
            return None, None

        email = email_match.group(1)
        password = password_match.group(1)

        # 检查是否为默认值
        if email == "your-email@example.com" or password == "your-password":
            print_error("配置文件包含默认值，请先配置您的账号信息")
            print_info("配置文件路径", config_file)
            return None, None

        return email, password

    except Exception as e:
        print_error(f"读取配置文件失败: {e}")
        return None, None

def test_network():
    """测试网络连接"""
    print_step("1/4", "测试网络连接...")

    try:
        response = requests.get('https://super-yi.com', timeout=5)
        print_success(f"网络连接正常 (状态码: {response.status_code})")
        return True
    except requests.exceptions.Timeout:
        print_error("网络连接超时，请检查网络设置")
        return False
    except requests.exceptions.ConnectionError:
        print_error("无法连接到 super-yi.com，请检查网络或防火墙设置")
        return False
    except Exception as e:
        print_error(f"网络测试失败: {e}")
        return False

def test_login(email, password):
    """测试登录"""
    print_step("2/4", "测试登录...")
    print_info("邮箱", email)
    print_info("密码", "*" * len(password))

    try:
        response = requests.post(
            'https://super-yi.com/auth/login',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json={
                'email': email,
                'password': password
            },
            timeout=10
        )

        print_info("HTTP 状态码", response.status_code)

        if response.status_code == 200:
            data = response.json()
            print_info("响应数据", json.dumps(data, indent=2, ensure_ascii=False))

            if data.get('success'):
                if data.get('token'):
                    token = data['token']
                    print_success(f"登录成功！获取到 Token (长度: {len(token)})")
                    print_info("Token 前50字符", token[:50] + "...")
                    return token
                else:
                    print_error("登录成功但未返回 Token")
                    print_warning("响应数据中缺少 'token' 字段")
                    return None
            else:
                error_msg = data.get('message', '未知错误')
                print_error(f"登录失败: {error_msg}")
                return None
        elif response.status_code == 401:
            print_error("账号或密码错误，请检查配置")
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

def test_profile(token):
    """测试获取用户信息"""
    print_step("3/4", "测试获取用户信息...")

    try:
        response = requests.get(
            'https://super-yi.com/user-api/profile',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'authorization': f'Bearer {token}',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout=10
        )

        print_info("HTTP 状态码", response.status_code)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                user_data = data.get('user', {})
                balance_cents = user_data.get('balanceCents', 0)
                total_cost_cents = user_data.get('usage', {}).get('totalCostCents', 0)

                balance = balance_cents / 100.0
                current_cost = total_cost_cents / 100.0
                total_limit = balance + current_cost

                print_success("成功获取用户信息！")
                print_info("余额", f"${balance:.2f}")
                print_info("已使用", f"${current_cost:.2f}")
                print_info("总额度", f"${total_limit:.2f}")
                return True
            else:
                print_error("获取用户信息失败")
                return False
        else:
            print_error(f"API 请求失败，HTTP 状态码: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"获取用户信息失败: {e}")
        return False

def save_token(token):
    """保存 Token 到缓存文件"""
    print_step("4/4", "保存 Token 到缓存...")

    cache_file = os.path.expanduser('~/.claude/.super_yi_token')

    try:
        with open(cache_file, 'w') as f:
            f.write(token)
        print_success(f"Token 已保存到: {cache_file}")

        # 验证文件
        if os.path.exists(cache_file):
            file_size = os.path.getsize(cache_file)
            print_info("文件大小", f"{file_size} 字节")
            print_info("修改时间", datetime.fromtimestamp(os.path.getmtime(cache_file)).strftime('%Y-%m-%d %H:%M:%S'))

        return True
    except Exception as e:
        print_error(f"保存 Token 失败: {e}")
        return False

def main():
    """主函数"""
    print_header("Super-Yi 登录诊断工具")

    print("本工具将帮助您诊断登录和 Token 获取问题\n")

    # 加载配置
    print_step("0/4", "读取配置文件...")
    email, password = load_config()

    if not email or not password:
        print("\n" + "="*60)
        print(f"{Colors.RED}配置检查失败，无法继续{Colors.RESET}")
        print("="*60)
        print("\n请先配置您的账号信息:")
        print(f"  1. 编辑文件: {Colors.CYAN}~/.claude/status-final.py{Colors.RESET}")
        print(f"  2. 修改以下两行:")
        print(f"     {Colors.YELLOW}SUPER_YI_EMAIL = \"your-email@example.com\"{Colors.RESET}")
        print(f"     {Colors.YELLOW}SUPER_YI_PASSWORD = \"your-password\"{Colors.RESET}")
        print(f"  3. 替换为您的真实账号信息")
        return 1

    print_success("配置文件读取成功")
    print()

    # 测试网络
    if not test_network():
        return 1
    print()

    # 测试登录
    token = test_login(email, password)
    if not token:
        print("\n" + "="*60)
        print(f"{Colors.RED}登录失败{Colors.RESET}")
        print("="*60)
        print("\n可能的原因:")
        print("  1. 账号或密码错误")
        print("  2. API 接口变更")
        print("  3. 网络问题")
        print("\n建议:")
        print("  1. 检查配置文件中的账号密码是否正确")
        print("  2. 尝试在浏览器中登录 https://super-yi.com 验证账号")
        print("  3. 检查网络连接和防火墙设置")
        return 1
    print()

    # 测试获取用户信息
    if not test_profile(token):
        return 1
    print()

    # 保存 Token
    if not save_token(token):
        return 1

    # 成功
    print("\n" + "="*60)
    print(f"{Colors.GREEN}{Colors.BOLD}诊断完成！所有测试通过 ✓{Colors.RESET}")
    print("="*60)
    print("\n您的状态栏脚本现在应该可以正常工作了")
    print("请重启 Claude Code 查看状态栏\n")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}用户中断{Colors.RESET}")
        sys.exit(1)
