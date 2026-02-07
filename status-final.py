# ================================
# 配置区域 - 请修改下面的配置为你自己的
# ================================
# TigerAPI 配置
TIGER_API_URL = "https://your-tiger-api-url.com"
TIGER_USERNAME = "your-username"
TIGER_PASSWORD = "your-password"
TIGER_QUOTA_PER_UNIT = 500000  # 配额单位换算值：原始quota / 此值 = 美元余额

import json
import os
import time
import requests
import sys
import urllib3
import subprocess
from functools import wraps
from datetime import datetime

# 读取从Claude Code传递的JSON数据
claude_input = None
try:
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        claude_input = json.loads(stdin_data)
        # 调试：打印收到的完整JSON到文件
        debug_file = os.path.expanduser('~/.claude/statusline_debug.json')
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(claude_input, f, indent=2, ensure_ascii=False)
except:
    pass

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ANSI颜色代码
class Colors:
    # 基础颜色
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

def colorize(text, color=None, bg_color=None, bold=False, dim=False):
    """给文本添加颜色"""
    if not color and not bg_color and not bold and not dim:
        return text
    
    codes = []
    if bold:
        codes.append('1')
    if dim:
        codes.append('2')
    if color:
        codes.append(color.replace('\033[', '').replace('m', ''))
    if bg_color:
        codes.append(bg_color.replace('\033[', '').replace('m', ''))
    
    if codes:
        return f"\033[{';'.join(codes)}m{text}{Colors.RESET}"
    return text

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 统一错误处理装饰器
def safe_execute(default_return=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return default_return
        return wrapper
    return decorator


@safe_execute(None)
def login_xiaoai():
    """登录 XiaoAi 获取 Bearer Token"""
    try:
        response = requests.post(
            'https://xiaoai.ve-rel.com/api/user/login',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json={
                'email': XIAOAI_EMAIL,
                'password': XIAOAI_PASSWORD
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data', {}).get('token'):
                token = data['data']['token']
                # 缓存 token 到文件
                cache_file = os.path.expanduser('~/.claude/.xiaoai_token')
                try:
                    with open(cache_file, 'w') as f:
                        f.write(token)
                except:
                    pass
                return token
    except:
        pass
    return None

@safe_execute(None)
def login_tiger():
    """登录 TigerAPI 获取 session cookie"""
    try:
        session = requests.Session()
        response = session.post(
            f'{TIGER_API_URL}/api/user/login',
            headers={
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json={
                'username': TIGER_USERNAME,
                'password': TIGER_PASSWORD
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user_id = data.get('data', {}).get('id')
                # 获取 session cookie
                session_cookie = session.cookies.get('session')
                if session_cookie and user_id:
                    # 缓存 session 和 user_id 到文件
                    cache_file = os.path.expanduser('~/.claude/.tiger_session')
                    try:
                        with open(cache_file, 'w') as f:
                            json.dump({
                                'session': session_cookie,
                                'user_id': user_id,
                                'timestamp': time.time()
                            }, f)
                    except:
                        pass
                    return {'session': session_cookie, 'user_id': user_id}
    except:
        pass
    return None

@safe_execute(None)
def get_cached_tiger_session():
    """获取缓存的 TigerAPI session"""
    cache_file = os.path.expanduser('~/.claude/.tiger_session')
    try:
        if os.path.exists(cache_file):
            # 检查缓存文件是否在20小时内
            if time.time() - os.path.getmtime(cache_file) < 72000:  # 20小时
                with open(cache_file, 'r') as f:
                    return json.load(f)
    except:
        pass
    return None

@safe_execute(None)
def get_tiger_balance():
    """获取 TigerAPI 余额信息"""
    global _api_response_time
    try:
        # 先尝试使用缓存的 session
        cached = get_cached_tiger_session()

        # 如果没有缓存或缓存过期，重新登录
        if not cached:
            cached = login_tiger()
            if not cached:
                return None

        session_cookie = cached.get('session')
        user_id = cached.get('user_id')

        start_time = time.time()
        response = requests.get(
            f'{TIGER_API_URL}/api/user/self',
            headers={
                'accept': 'application/json, text/plain, */*',
                'new-api-user': str(user_id),
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            cookies={'session': session_cookie},
            timeout=5
        )

        end_time = time.time()
        _api_response_time = int((end_time - start_time) * 1000)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user_data = data.get('data', {})
                quota = user_data.get('quota', 0)
                used_quota = user_data.get('used_quota', 0)
                # 转换为美元 (quota / quota_per_unit)
                balance_usd = quota / TIGER_QUOTA_PER_UNIT
                used_usd = used_quota / TIGER_QUOTA_PER_UNIT
                return {
                    'balance': balance_usd,
                    'used': used_usd,
                    'raw_quota': quota,
                    'raw_used': used_quota
                }

        # 如果请求失败，可能 session 过期，删除缓存并重试
        if response.status_code == 401 or (response.status_code == 200 and not response.json().get('success')):
            cache_file = os.path.expanduser('~/.claude/.tiger_session')
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except:
                pass

            # 重新登录再试一次
            cached = login_tiger()
            if cached:
                response = requests.get(
                    f'{TIGER_API_URL}/api/user/self',
                    headers={
                        'accept': 'application/json, text/plain, */*',
                        'new-api-user': str(cached.get('user_id')),
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    cookies={'session': cached.get('session')},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        user_data = data.get('data', {})
                        quota = user_data.get('quota', 0)
                        used_quota = user_data.get('used_quota', 0)
                        balance_usd = quota / TIGER_QUOTA_PER_UNIT
                        used_usd = used_quota / TIGER_QUOTA_PER_UNIT
                        return {
                            'balance': balance_usd,
                            'used': used_usd,
                            'raw_quota': quota,
                            'raw_used': used_quota
                        }
    except:
        pass
    return None

@safe_execute(None)
def get_cached_token():
    """获取缓存的 token"""
    cache_file = os.path.expanduser('~/.claude/.xiaoai_token')
    try:
        if os.path.exists(cache_file):
            # 检查缓存文件是否在20小时内（JWT token 24小时过期，提前一点刷新）
            if time.time() - os.path.getmtime(cache_file) < 72000:  # 20小时
                with open(cache_file, 'r') as f:
                    return f.read().strip()
    except:
        pass
    return None

@safe_execute(None)
def get_claude_api_stats():
    """获取Claude API统计信息 - 使用新的Cubence API"""
    try:
        response = requests.get(
            'https://cubence.com/api/v1/user/subscription-info',
            headers={
                'Accept': '*/*',
                'Authorization': CUBENCE_API_KEY,
                'Content-Type': 'application/json'
            },
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()

            # 解析新API的数据结构
            # 数据格式: {"normal_balance": {...}, "subscription_window": {"five_hour": {...}, "weekly": {...}}}
            subscription = result.get('subscription_window', {})
            five_hour = subscription.get('five_hour', {})
            weekly = subscription.get('weekly', {})

            # 提取五小时窗口信息
            five_hour_limit = five_hour.get('limit', 0)
            five_hour_remaining = five_hour.get('remaining', 0)
            five_hour_used = five_hour.get('used', 0)
            five_hour_reset = five_hour.get('reset_at', 0)

            # 提取周窗口信息
            weekly_limit = weekly.get('limit', 0)
            weekly_remaining = weekly.get('remaining', 0)
            weekly_used = weekly.get('used', 0)
            weekly_reset = weekly.get('reset_at', 0)

            return {
                'five_hour': {
                    'limit': five_hour_limit,
                    'remaining': five_hour_remaining,
                    'used': five_hour_used,
                    'reset_at': five_hour_reset
                },
                'weekly': {
                    'limit': weekly_limit,
                    'remaining': weekly_remaining,
                    'used': weekly_used,
                    'reset_at': weekly_reset
                }
            }
    except:
        pass
    return None

@safe_execute("获取失败")
def format_total_cost_display(api_data):
    """格式化订阅配额显示 - 适配Cubence API"""
    if not api_data:
        return colorize("获取失败", Colors.RED)

    five_hour = api_data.get('five_hour', {})
    weekly = api_data.get('weekly', {})

    # 五小时窗口数据
    five_limit = five_hour.get('limit', 0)
    five_remaining = five_hour.get('remaining', 0)
    five_used = five_hour.get('used', 0)
    five_reset = five_hour.get('reset_at', 0)

    # 周窗口数据
    week_limit = weekly.get('limit', 0)
    week_remaining = weekly.get('remaining', 0)
    week_used = weekly.get('used', 0)
    week_reset = weekly.get('reset_at', 0)

    # 计算重置时间
    def format_reset_time(reset_timestamp):
        if reset_timestamp <= 0:
            return ""
        now = time.time()
        diff = reset_timestamp - now
        if diff <= 0:
            return "已重置"
        days = int(diff // 86400)
        hours = int((diff % 86400) // 3600)
        minutes = int((diff % 3600) // 60)
        if days > 0:
            return f"{days}d{hours}h"
        elif hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"

    # 生成进度条函数 - 每格5种状态：全绿→半绿→全黄→半红→全红
    def make_progress_bar(usage_ratio, bar_length=10):
        result = []
        precise_ratio = usage_ratio * bar_length
        full_blocks = int(precise_ratio)  # 完全填满的格子数
        partial = precise_ratio - full_blocks  # 当前格子的填充比例(0-1)
        
        # 已填满的格子都是全红（表示该格已完全用完）
        for i in range(full_blocks):
            result.append(colorize('█', Colors.RED))
        
        # 当前正在填充的格子，5种状态
        if full_blocks < bar_length and partial > 0:
            if partial < 0.2:
                # 0-20%: 全绿
                result.append(colorize('█', Colors.GREEN))
            elif partial < 0.4:
                # 20-40%: 半绿
                result.append(colorize('▓', Colors.GREEN))
            elif partial < 0.6:
                # 40-60%: 全黄
                result.append(colorize('█', Colors.YELLOW))
            elif partial < 0.8:
                # 60-80%: 半红
                result.append(colorize('▓', Colors.RED))
            else:
                # 80-100%: 全红
                result.append(colorize('█', Colors.RED))
            empty_start = full_blocks + 1
        else:
            empty_start = full_blocks
        
        # 未使用的格子是全绿（表示还可用）
        for i in range(empty_start, bar_length):
            result.append(colorize('█', Colors.GREEN))
        
        return ''.join(result)

    # === 五小时窗口 ===
    five_usage_ratio = five_used / five_limit if five_limit > 0 else 0
    five_reset_str = format_reset_time(five_reset)

    if five_usage_ratio >= 0.8:
        five_icon = "🚨"
        five_perc_color = Colors.RED
    elif five_usage_ratio >= 0.4:
        five_icon = "💸"
        five_perc_color = Colors.YELLOW
    else:
        five_icon = "💰"
        five_perc_color = Colors.WHITE

    five_bar = make_progress_bar(five_usage_ratio, 10)
    five_percentage = colorize(f"{five_usage_ratio * 100:.1f}%", five_perc_color)
    five_reset_part = colorize("(", Colors.DIM) + colorize(five_reset_str, Colors.YELLOW) + colorize("↻", Colors.BRIGHT_YELLOW) + colorize(")", Colors.DIM) if five_reset_str else ""

    five_part = (
        colorize(five_icon, five_perc_color) +
        colorize("5h:", Colors.BRIGHT_CYAN) +
        five_bar +
        five_percentage +
        five_reset_part
    )

    # === 周窗口 ===
    week_usage_ratio = week_used / week_limit if week_limit > 0 else 0
    week_reset_str = format_reset_time(week_reset)

    if week_usage_ratio >= 0.8:
        week_perc_color = Colors.RED
    elif week_usage_ratio >= 0.4:
        week_perc_color = Colors.YELLOW
    else:
        week_perc_color = Colors.WHITE

    week_bar = make_progress_bar(week_usage_ratio, 10)
    week_percentage = colorize(f"{week_usage_ratio * 100:.1f}%", week_perc_color)
    week_reset_part = colorize("(", Colors.DIM) + colorize(week_reset_str, Colors.YELLOW) + colorize("↻", Colors.BRIGHT_YELLOW) + colorize(")", Colors.DIM) if week_reset_str else ""

    week_part = (
        colorize("周:", Colors.BRIGHT_MAGENTA) +
        week_bar +
        week_percentage +
        week_reset_part
    )

    return five_part + " " + week_part

@safe_execute("💰N/A")
def format_tiger_balance_display(tiger_data):
    """格式化 TigerAPI 余额显示"""
    if not tiger_data:
        return colorize("🐯", Colors.YELLOW) + colorize("N/A", Colors.RED)

    balance = tiger_data.get('balance', 0)

    # 格式化余额显示
    if balance >= 1000:
        balance_str = f"${balance/1000:.2f}k"
    else:
        balance_str = f"${balance:.2f}"

    return (
        colorize("🐯", Colors.BRIGHT_GREEN) +
        colorize("Tiger:", Colors.BRIGHT_CYAN) +
        colorize(balance_str, Colors.BRIGHT_GREEN, bold=True)
    )

@safe_execute('🤖unknown')
def get_model_info():
    """获取模型信息"""
    model = ''

    # 优先使用从Claude Code传递的当前会话模型信息
    if claude_input and claude_input.get('model'):
        model_data = claude_input['model']
        model = model_data.get('display_name', '') or model_data.get('id', '')

    # 如果没有从输入获取到模型信息，尝试环境变量
    if not model:
        model = os.environ.get('ANTHROPIC_MODEL', '')

    # 如果还是没有，返回默认值
    if not model:
        return colorize("🤖", Colors.BLUE) + colorize("unknown", Colors.WHITE)

    # 根据模型类型选择图标
    model_lower = model.lower()
    if 'sonnet' in model_lower:
        icon = "⚡"  # 闪电 - Sonnet系列
    elif 'opus' in model_lower:
        icon = "✨"  # 星星 - Opus系列
    elif 'haiku' in model_lower:
        icon = "🍃"  # 叶子 - Haiku系列
    else:
        icon = "🤖"  # 默认机器人图标

    # 显示图标和模型名称
    return colorize(icon, Colors.BLUE) + colorize(model, Colors.BRIGHT_MAGENTA, bold=True)

@safe_execute("📂no-git")
def get_git_info():
    """获取Git分支、修改文件数、今日代码行数、落后最新分支"""
    try:
        branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        status_output = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        modified_count = len([line for line in status_output.split('\n') if line.strip()])

        # === 基础部分：分支 + 修改文件数 ===
        if modified_count > 0:
            if modified_count > 10:
                count_color = Colors.RED
            elif modified_count > 5:
                count_color = Colors.YELLOW
            else:
                count_color = Colors.BRIGHT_YELLOW

            base_part = (
                colorize("🌿", Colors.GREEN) +
                colorize(branch, Colors.BRIGHT_GREEN, bold=True) +
                colorize(f"({modified_count})", count_color, bold=True)
            )
        else:
            base_part = colorize("🌿", Colors.GREEN) + colorize(branch, Colors.BRIGHT_GREEN, bold=True)

        # === 今日代码行数 ===
        code_part = ""
        try:
            # 今日的 git log 统计
            today_stats = subprocess.check_output(
                ['git', 'log', '--since=00:00', '--pretty=format:', '--numstat'],
                stderr=subprocess.DEVNULL, timeout=5, encoding='utf-8'
            ).strip()

            # 当前未提交的变更
            unstaged_stats = subprocess.check_output(
                ['git', 'diff', '--numstat'],
                stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
            ).strip()

            staged_stats = subprocess.check_output(
                ['git', 'diff', '--cached', '--numstat'],
                stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
            ).strip()

            added = 0
            deleted = 0

            for stats in [today_stats, unstaged_stats, staged_stats]:
                if not stats:
                    continue
                for line in stats.split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            a = int(parts[0]) if parts[0] != '-' else 0
                            d = int(parts[1]) if parts[1] != '-' else 0
                            added += a
                            deleted += d
                        except:
                            continue

            if added > 0 or deleted > 0:
                code_part = (
                    " " +
                    colorize(f"+{added}", Colors.GREEN, bold=True) +
                    colorize(f"-{deleted}", Colors.RED, bold=True)
                )
        except:
            pass

        # === 落后最新分支 ===
        behind_part = ""
        try:
            # 获取所有远程分支，按最新提交时间排序
            result = subprocess.check_output(
                ['git', 'for-each-ref', '--sort=-committerdate', 'refs/remotes/origin/', '--format=%(refname:short)'],
                stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
            ).strip()

            if result:
                branches = result.split('\n')
                if branches:
                    latest_branch = branches[0]
                    # 如果最新分支不是当前分支的远程
                    if latest_branch != f"origin/{branch}":
                        behind_count = subprocess.check_output(
                            ['git', 'rev-list', '--count', f'HEAD..{latest_branch}'],
                            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
                        ).strip()
                        behind = int(behind_count)
                        if behind > 0:
                            if behind >= 10:
                                behind_color = Colors.RED
                            elif behind >= 5:
                                behind_color = Colors.YELLOW
                            else:
                                behind_color = Colors.BRIGHT_CYAN
                            behind_part = " " + colorize("↓", behind_color) + colorize(str(behind), behind_color, bold=True)
        except:
            pass

        return base_part + code_part + behind_part

    except:
        return colorize("📂", Colors.DIM) + colorize("no-git", Colors.DIM)

@safe_execute("unknown")
def get_project_info():
    """获取项目信息"""
    # 优先使用从Claude Code传递的工作空间信息
    if claude_input and claude_input.get('workspace'):
        workspace = claude_input['workspace']
        project_dir = workspace.get('project_dir', '')
        if project_dir:
            return os.path.basename(project_dir) or 'unknown'
    
    # 回退到当前目录
    return os.path.basename(os.getcwd()) or 'unknown'

@safe_execute("🧠0k/200k(0%)")
def get_context_display():
    """获取上下文显示信息"""
    context_usage = get_context_usage()
    if context_usage:
        used_tokens = context_usage['used']
        total = format_tokens(context_usage['total'])
        percentage = context_usage['percentage']

        # 改进1：根据百分比而非绝对值设置颜色，更直观
        # 改进2：降低警告阈值，提前提醒主人
        if percentage >= 70:  # 70%以上（140k+）- 红色警告
            icon = "🔥"  # 火焰：危险状态，建议清理上下文
            icon_color = Colors.RED
            used_color = Colors.RED
            perc_color = Colors.RED
        elif percentage >= 50:  # 50%-70%（100k-140k）- 黄色警告
            icon = "⚠️ "  # 警告：中等负载，需要注意
            icon_color = Colors.YELLOW
            used_color = Colors.YELLOW
            perc_color = Colors.YELLOW
        elif percentage >= 30:  # 30%-50%（60k-100k）- 蓝色正常
            icon = "🧠"  # 大脑：正常工作状态
            icon_color = Colors.BRIGHT_BLUE
            used_color = Colors.BRIGHT_CYAN
            perc_color = Colors.CYAN
        else:  # 0-30%（0-60k）- 绿色轻松
            icon = "🧠"  # 大脑：轻松状态
            icon_color = Colors.GREEN
            used_color = Colors.GREEN
            perc_color = Colors.GREEN

        used = format_tokens(used_tokens)

        icon_part = colorize(icon, icon_color)
        used_part = colorize(used, used_color, bold=True)
        separator = colorize("/", Colors.BRIGHT_CYAN)
        total_part = colorize(total, Colors.CYAN)
        perc_part = colorize(f"({percentage}%)", perc_color)

        return icon_part + used_part + separator + total_part + perc_part

    # 改进3：获取失败时显示"⚠️ERR"，区分"真的是0"和"获取失败"
    return colorize("⚠️", Colors.YELLOW) + colorize("ERR", Colors.YELLOW) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(??%)", Colors.DIM)

@safe_execute(None)
def get_context_usage():
    """获取当前会话的上下文使用量 - 使用 context_window.current_usage（最精确）"""
    if claude_input and claude_input.get('context_window'):
        ctx = claude_input['context_window']
        context_limit = ctx.get('context_window_size', 200000)
        current_usage = ctx.get('current_usage', {})

        if current_usage:
            input_tokens = current_usage.get('input_tokens', 0)
            cache_read = current_usage.get('cache_read_input_tokens', 0)
            cache_create = current_usage.get('cache_creation_input_tokens', 0)
            active_tokens = input_tokens + cache_read + cache_create

            if active_tokens > 0:
                return {
                    'used': active_tokens,
                    'total': context_limit,
                    'percentage': round((active_tokens / context_limit) * 100)
                }

    return None

@safe_execute("0")
def format_tokens(tokens):
    """格式化token显示"""
    return f"{round(tokens/1000)}k" if tokens >= 1000 else str(tokens)

@safe_execute("0k")
def get_project_token_info():
    """获取项目token信息 - 基于本地项目文件计算"""
    current_dir_path = os.getcwd()
    current_dir_name = os.path.basename(current_dir_path) or 'unknown'
    
    # Windows路径转换 - 修复Claude项目文件夹命名规则
    if current_dir_path.startswith('/c/'):
        # bash格式路径 /c/Users/Administrator -> C:\Users\Administrator
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        # bash格式路径 /d/IP_tracker -> D:\IP_tracker
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        # 已经是Windows格式
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path
    
    # Claude项目文件夹命名规则: C:\Users\Administrator -> C--Users-Administrator
    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    
    # 修复下划线和短横线的匹配问题
    claude_folder_name_alt = claude_folder_name.replace('_', '-')
    
    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),  # IP_tracker -> IP-tracker
        current_dir_name.replace('-', '_')   # IP-tracker -> IP_tracker  
    ]
    
    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "0k"
    
    project_tokens = 0
    
    # 在projects目录中查找匹配当前目录的文件夹
    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
            
        # 检查文件夹名是否包含当前目录的路径信息
        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break
        
        if is_current_project:
            # 统计该项目文件夹中所有jsonl文件的tokens
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.jsonl'):
                    file_path = os.path.join(folder_path, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        for line in lines:
                            data = json.loads(line.strip())
                            if data.get('type') == 'assistant' and data.get('message', {}).get('usage'):
                                usage = data['message']['usage']
                                input_tokens = usage.get('input_tokens', 0)
                                output_tokens = usage.get('output_tokens', 0)
                                cache_read_tokens = usage.get('cache_read_input_tokens', 0)
                                cache_create_tokens = usage.get('cache_create_input_tokens', 0)
                                # 统计所有4种tokens
                                project_tokens += input_tokens + output_tokens + cache_read_tokens + cache_create_tokens
                    except:
                        continue
    
    # 格式化显示
    if project_tokens >= 1000000:
        return f"{project_tokens/1000000:.1f}M"
    elif project_tokens >= 1000:
        return f"{project_tokens/1000:.1f}k"
    else:
        return str(project_tokens)

@safe_execute("$0.00")
def get_project_cost():
    """获取本目录消耗的费用 - 基于本地项目文件计算"""
    current_dir_path = os.getcwd()
    current_dir_name = os.path.basename(current_dir_path) or 'unknown'
    
    # Windows路径转换 - 修复Claude项目文件夹命名规则
    if current_dir_path.startswith('/c/'):
        # bash格式路径 /c/Users/Administrator -> C:\Users\Administrator
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        # bash格式路径 /d/IP_tracker -> D:\IP_tracker
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        # 已经是Windows格式
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path
    
    # Claude项目文件夹命名规则: C:\Users\Administrator -> C--Users-Administrator
    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    
    # 修复下划线和短横线的匹配问题
    claude_folder_name_alt = claude_folder_name.replace('_', '-')
    
    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),  # IP_tracker -> IP-tracker
        current_dir_name.replace('-', '_')   # IP-tracker -> IP_tracker  
    ]
    
    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "$0.00"
    
    project_cost = 0
    
    # 在projects目录中查找匹配当前目录的文件夹
    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
            
        # 检查文件夹名是否包含当前目录的路径信息
        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break
        
        if is_current_project:
            # 统计该项目文件夹中所有jsonl文件的费用
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.jsonl'):
                    file_path = os.path.join(folder_path, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        for line in lines:
                            data = json.loads(line.strip())
                            if data.get('type') == 'assistant' and data.get('message', {}).get('usage'):
                                usage = data['message']['usage']
                                input_tokens = usage.get('input_tokens', 0)
                                output_tokens = usage.get('output_tokens', 0)
                                cache_read_tokens = usage.get('cache_read_input_tokens', 0)
                                cache_create_tokens = usage.get('cache_create_input_tokens', 0)
                                
                                # 费用计算（包含所有4种tokens）
                                # input: $3/M, output: $15/M, cache_read: $0.3/M, cache_create: $3.75/M
                                cost = (
                                    input_tokens * 3.0 / 1000000 +
                                    output_tokens * 15.0 / 1000000 +
                                    cache_read_tokens * 0.3 / 1000000 +
                                    cache_create_tokens * 3.75 / 1000000
                                )
                                project_cost += cost
                    except:
                        continue
    
    return f"${project_cost:.2f}"

@safe_execute("0h")
def get_project_time():
    """获取本目录实际工作时间 - 基于会话计算"""
    current_dir_path = os.getcwd()
    current_dir_name = os.path.basename(current_dir_path) or 'unknown'
    
    # Windows路径转换 - 修复Claude项目文件夹命名规则
    if current_dir_path.startswith('/c/'):
        # bash格式路径 /c/Users/Administrator -> C:\Users\Administrator
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        # bash格式路径 /d/IP_tracker -> D:\IP_tracker
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        # 已经是Windows格式
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path
    
    # Claude项目文件夹命名规则: C:\Users\Administrator -> C--Users-Administrator
    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    
    # 修复下划线和短横线的匹配问题
    claude_folder_name_alt = claude_folder_name.replace('_', '-')
    
    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),  # IP_tracker -> IP-tracker
        current_dir_name.replace('-', '_')   # IP-tracker -> IP_tracker  
    ]
    
    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "0h"
    
    all_sessions = {}  # sessionId -> [timestamps]
    
    # 在projects目录中查找匹配当前目录的文件夹
    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
            
        # 检查文件夹名是否包含当前目录的路径信息
        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break
        
        if is_current_project:
            # 遍历该项目文件夹中所有jsonl文件，按会话收集时间戳
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.jsonl'):
                    file_path = os.path.join(folder_path, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        for line in lines:
                            data = json.loads(line.strip())
                            session_id = data.get('sessionId')
                            timestamp_str = data.get('timestamp')
                            if session_id and timestamp_str:
                                try:
                                    # 解析ISO 8601格式的时间字符串
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
                                    if session_id not in all_sessions:
                                        all_sessions[session_id] = []
                                    all_sessions[session_id].append(timestamp)
                                except:
                                    continue
                    except:
                        continue
    
    total_work_time = 0
    
    # 计算每个会话的工作时间
    for session_id, timestamps in all_sessions.items():
        if len(timestamps) >= 2:
            timestamps.sort()
            # 每个会话的工作时间 = 最后一条记录 - 第一条记录
            session_time = timestamps[-1] - timestamps[0]
            # 限制单个会话最长8小时（防止长时间未关闭的会话影响统计）
            session_time = min(session_time, 8 * 3600)
            total_work_time += session_time
    
    if total_work_time > 0:
        hours = total_work_time / 3600  # 转换为小时
        
        # 格式化显示
        if hours >= 1:
            return f"{hours:.1f}h"
        else:
            minutes = hours * 60
            return f"{minutes:.0f}m"
    
    return "0h"

@safe_execute(None)
def get_account_pool_summary():
    """获取账号池汇总信息 - 返回完整的 summary 数据"""
    try:
        # 先尝试使用缓存的 token
        bearer_token = get_cached_token()

        # 如果没有缓存或缓存过期，重新登录
        if not bearer_token:
            bearer_token = login_super_yi()
            if not bearer_token:
                return None

        response = requests.get(
            'https://super-yi.com/user-api/account-pool/summary?model=claude-sonnet-4-5-20250929',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'authorization': f'Bearer {bearer_token}',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('summary', {})

        # 如果 token 失效，删除缓存并重试一次
        if response.status_code == 401:
            cache_file = os.path.expanduser('~/.claude/.super_yi_token')
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except:
                pass

            # 重新登录再试一次
            bearer_token = login_super_yi()
            if bearer_token:
                response = requests.get(
                    'https://super-yi.com/user-api/account-pool/summary?model=claude-sonnet-4-5-20250929',
                    headers={
                        'accept': 'application/json, text/plain, */*',
                        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'authorization': f'Bearer {bearer_token}',
                        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-fetch-dest': 'empty',
                        'sec-fetch-mode': 'cors',
                        'sec-fetch-site': 'same-origin',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    timeout=3
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return data.get('summary', {})
    except:
        pass
    return None

@safe_execute("🔋N/A")
def format_account_pool_display(pool_data):
    """格式化账号池状态显示 - Claude官方详细 + Codex简化"""
    if not pool_data:
        return colorize("🔋", Colors.BRIGHT_BLUE) + colorize("N/A", Colors.DIM)

    # 获取 breakdown 数据
    breakdown = pool_data.get('breakdown', [])

    # 查找 Claude 官方和 Codex 账号数据
    claude_official = None
    codex = None

    for item in breakdown:
        if item.get('key') == 'claude_official':
            claude_official = item
        elif item.get('key') == 'codex':
            codex = item

    # 如果没有数据，返回默认显示
    if not claude_official and not codex:
        return colorize("🔋", Colors.BRIGHT_BLUE) + colorize("N/A", Colors.DIM)

    result_parts = []

    # === Claude 官方账号显示（详细） ===
    if claude_official:
        total = claude_official.get('total', 0)
        normal = claude_official.get('normal', 0)
        rate_limited = claude_official.get('rateLimited', 0)
        blocked = claude_official.get('blocked', 0)

        # 构建分段进度条
        bar_parts = []
        # 正常账号 - 绿色█
        for _ in range(normal):
            bar_parts.append(colorize("█", Colors.BRIGHT_GREEN))
        # 速率限制账号 - 黄色█
        for _ in range(rate_limited):
            bar_parts.append(colorize("█", Colors.BRIGHT_YELLOW))
        # 已阻止账号 - 红色█
        for _ in range(blocked):
            bar_parts.append(colorize("█", Colors.BRIGHT_RED))

        progress_bar = "".join(bar_parts) if bar_parts else colorize("░", Colors.DIM)

        # 组装：🔋Claude:3/4[进度条]
        claude_display = (
            colorize("🔋", Colors.BRIGHT_BLUE) +
            colorize("Claude:", Colors.BRIGHT_MAGENTA, bold=True) +
            colorize(str(normal), Colors.BRIGHT_GREEN, bold=True) +
            colorize("/", Colors.BRIGHT_CYAN) +
            colorize(str(total), Colors.WHITE, bold=True) +
            colorize("[", Colors.BRIGHT_CYAN) +
            progress_bar +
            colorize("]", Colors.BRIGHT_CYAN)
        )
        result_parts.append(claude_display)

    # === Codex 账号显示（简化） ===
    if codex:
        codex_total = codex.get('total', 0)
        codex_normal = codex.get('normal', 0)

        # 组装：Codex:25/50
        codex_display = (
            colorize("Codex:", Colors.CYAN, bold=True) +
            colorize(str(codex_normal), Colors.GREEN, bold=True) +
            colorize("/", Colors.BRIGHT_CYAN) +
            colorize(str(codex_total), Colors.WHITE, bold=True)
        )
        result_parts.append(codex_display)

    return " ".join(result_parts)

@safe_execute("00:00")
def get_current_time():
    """获取当前时间"""
    now = datetime.now()
    return now.strftime("%H:%M")

# ================================
# 新功能：5点功能增强
# ================================

@safe_execute("💬0")
def get_session_message_count():
    """获取本次会话消息轮数"""
    # 定位当前项目的文件夹
    current_dir_path = os.getcwd()

    # 统一转换为 Claude 项目文件夹命名格式
    # C:\Users\Administrator -> C--Users-Administrator
    # /c/Users/Administrator -> C--Users-Administrator
    if current_dir_path.startswith('/c/'):
        # bash格式: /c/Users/Administrator
        claude_folder_name = 'C--' + current_dir_path[3:].replace('/', '-')
    elif current_dir_path.startswith('/d/'):
        claude_folder_name = 'D--' + current_dir_path[3:].replace('/', '-')
    elif len(current_dir_path) > 2 and current_dir_path[1] == ':':
        # Windows格式: C:\Users\Administrator
        drive = current_dir_path[0].upper()
        path_part = current_dir_path[3:].replace('\\', '-').replace('/', '-')
        claude_folder_name = f'{drive}--{path_part}'
    else:
        claude_folder_name = current_dir_path.replace('/', '-').replace('\\', '-')

    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return colorize("💬", Colors.BRIGHT_CYAN) + colorize("0", Colors.WHITE)

    # 找到当前项目对应的文件夹
    target_folder = None
    for folder_name in os.listdir(projects_dir):
        if claude_folder_name in folder_name or folder_name in claude_folder_name:
            target_folder = os.path.join(projects_dir, folder_name)
            break

    if not target_folder or not os.path.isdir(target_folder):
        return colorize("💬", Colors.BRIGHT_CYAN) + colorize("0", Colors.WHITE)

    # 在项目文件夹中找最新的对话文件
    # 排除: agent- 开头的文件、只有 summary 的文件
    candidate_files = []

    for file_name in os.listdir(target_folder):
        if file_name.endswith('.jsonl') and not file_name.startswith('agent-'):
            file_path = os.path.join(target_folder, file_name)
            mtime = os.path.getmtime(file_path)
            # 检查文件是否包含 user 消息（快速检查前几行）
            has_user = False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i > 20:  # 只检查前20行
                            break
                        if '"type":"user"' in line or '"type": "user"' in line:
                            has_user = True
                            break
            except:
                pass
            if has_user:
                candidate_files.append((mtime, file_path))

    if not candidate_files:
        return colorize("💬", Colors.BRIGHT_CYAN) + colorize("0", Colors.WHITE)

    # 选择最新的对话文件
    candidate_files.sort(reverse=True)
    latest_file = candidate_files[0][1]

    # 统计该文件中所有 user 消息数量
    message_count = 0
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'user':
                        message_count += 1
                except:
                    continue
    except:
        pass

    # 颜色根据轮数变化
    if message_count >= 50:
        count_color = Colors.RED
    elif message_count >= 20:
        count_color = Colors.YELLOW
    else:
        count_color = Colors.WHITE

    return colorize("💬", Colors.BRIGHT_CYAN) + colorize(str(message_count), count_color, bold=True)

# 全局变量存储API响应时间
_api_response_time = None

@safe_execute(None)
def get_claude_api_stats_with_timing():
    """获取Claude API统计信息并记录响应时间"""
    global _api_response_time
    try:
        start_time = time.time()
        response = requests.get(
            'https://cubence.com/api/v1/user/subscription-info',
            headers={
                'Accept': '*/*',
                'Authorization': CUBENCE_API_KEY,
                'Content-Type': 'application/json'
            },
            timeout=5
        )
        end_time = time.time()
        _api_response_time = int((end_time - start_time) * 1000)  # 转换为毫秒

        if response.status_code == 200:
            result = response.json()
            subscription = result.get('subscription_window', {})
            five_hour = subscription.get('five_hour', {})
            weekly = subscription.get('weekly', {})

            return {
                'five_hour': {
                    'limit': five_hour.get('limit', 0),
                    'remaining': five_hour.get('remaining', 0),
                    'used': five_hour.get('used', 0),
                    'reset_at': five_hour.get('reset_at', 0)
                },
                'weekly': {
                    'limit': weekly.get('limit', 0),
                    'remaining': weekly.get('remaining', 0),
                    'used': weekly.get('used', 0),
                    'reset_at': weekly.get('reset_at', 0)
                }
            }
    except:
        _api_response_time = None
    return None

@safe_execute("⚡--")
def get_api_response_time():
    """获取API响应速度"""
    global _api_response_time
    if _api_response_time is None:
        return colorize("⚡", Colors.YELLOW) + colorize("--", Colors.DIM)

    ms = _api_response_time
    # 根据响应时间设置颜色
    if ms < 200:
        time_color = Colors.GREEN
    elif ms < 500:
        time_color = Colors.YELLOW
    else:
        time_color = Colors.RED

    return colorize("⚡", Colors.BRIGHT_YELLOW) + colorize(f"{ms}ms", time_color)

@safe_execute("")
def get_git_behind_info():
    """获取当前分支落后最新分支的commit数"""
    try:
        # 先 fetch 更新远程信息（静默）
        subprocess.run(
            ['git', 'fetch', '--all', '--quiet'],
            stderr=subprocess.DEVNULL, timeout=5
        )

        # 获取当前分支
        current_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        # 获取所有远程分支，按最新提交时间排序
        result = subprocess.check_output(
            ['git', 'for-each-ref', '--sort=-committerdate', 'refs/remotes/origin/', '--format=%(refname:short)'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        if not result:
            return ""

        branches = result.split('\n')
        if not branches:
            return ""

        # 最新的远程分支
        latest_branch = branches[0]

        # 如果最新分支就是当前分支的远程，不显示
        if latest_branch == f"origin/{current_branch}":
            return ""

        # 计算当前分支落后最新分支多少commit
        behind_count = subprocess.check_output(
            ['git', 'rev-list', '--count', f'HEAD..{latest_branch}'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        behind = int(behind_count)
        if behind == 0:
            return ""

        # 提取分支名（去掉 origin/ 前缀）
        branch_name = latest_branch.replace('origin/', '')

        # 颜色根据落后数量
        if behind >= 10:
            behind_color = Colors.RED
        elif behind >= 5:
            behind_color = Colors.YELLOW
        else:
            behind_color = Colors.BRIGHT_CYAN

        return colorize("↓", behind_color) + colorize(str(behind), behind_color, bold=True)

    except:
        return ""

@safe_execute("📝+0-0")
def get_today_code_lines():
    """获取今日代码变更行数"""
    try:
        # 今日的 git log 统计
        today_stats = subprocess.check_output(
            ['git', 'log', '--since=00:00', '--pretty=format:', '--numstat'],
            stderr=subprocess.DEVNULL, timeout=5, encoding='utf-8'
        ).strip()

        # 当前未提交的变更
        unstaged_stats = subprocess.check_output(
            ['git', 'diff', '--numstat'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        staged_stats = subprocess.check_output(
            ['git', 'diff', '--cached', '--numstat'],
            stderr=subprocess.DEVNULL, timeout=2, encoding='utf-8'
        ).strip()

        added = 0
        deleted = 0

        # 解析统计结果
        for stats in [today_stats, unstaged_stats, staged_stats]:
            if not stats:
                continue
            for line in stats.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        a = int(parts[0]) if parts[0] != '-' else 0
                        d = int(parts[1]) if parts[1] != '-' else 0
                        added += a
                        deleted += d
                    except:
                        continue

        # 格式化显示
        if added == 0 and deleted == 0:
            return colorize("📝", Colors.DIM) + colorize("+0-0", Colors.DIM)

        add_part = colorize(f"+{added}", Colors.GREEN, bold=True)
        del_part = colorize(f"-{deleted}", Colors.RED, bold=True)

        return colorize("📝", Colors.BRIGHT_GREEN) + add_part + del_part

    except:
        return colorize("📝", Colors.DIM) + colorize("+0-0", Colors.DIM)

@safe_execute("")
def get_shell_status():
    """获取后台Shell数量"""
    # 尝试从 Claude Code 的数据中获取
    shell_count = 0
    if claude_input and claude_input.get('background_shells'):
        shell_count = len(claude_input['background_shells'])
    elif claude_input and claude_input.get('shells'):
        shell_count = len([s for s in claude_input['shells'] if s.get('running')])

    if shell_count > 0:
        if shell_count >= 3:
            shell_color = Colors.YELLOW
        else:
            shell_color = Colors.GREEN
        return (
            colorize("⚙️", Colors.BRIGHT_CYAN) +
            colorize(str(shell_count), shell_color, bold=True)
        )

    return ""

def main():
    """主函数"""
    try:
        # 获取 TigerAPI 余额（替换原来的 Cubence API）
        tiger_data = get_tiger_balance()

        # 美化的分隔符 - 使用原始的"┃"符号并添加亮色
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "

        # 项目信息组合 - 简化显示
        project_name = get_project_info()
        project_tokens = get_project_token_info()
        project_cost = get_project_cost()
        project_time = get_project_time()

        # TigerAPI 余额显示（替换原来的 Cubence 配额）
        account_info = format_tiger_balance_display(tiger_data)

        # 当前时间
        current_time = get_current_time()

        # Git信息（已整合：分支+修改数+今日代码行数+落后最新分支）
        git_info = get_git_info()

        # 新功能：会话消息轮数 + API响应时间 + Shell状态（合并为一个部分，不用竖线分隔）
        session_parts = [get_session_message_count(), get_api_response_time()]
        shell_status = get_shell_status()
        if shell_status:
            session_parts.append(shell_status)
        session_info = " ".join(session_parts)

        # 格式：Administrator:2.9M($42.63) ⏱️ 2.5h 🕐20:49
        project_info = colorize("📁", Colors.YELLOW) + colorize(project_name, Colors.BRIGHT_WHITE, bold=True) + colorize(":", Colors.BRIGHT_CYAN) + colorize(project_tokens, Colors.GREEN, bold=True) + colorize("(", Colors.BRIGHT_WHITE) + colorize(project_cost, Colors.GREEN) + colorize(") ", Colors.BRIGHT_WHITE) + colorize("⏱️ ", Colors.CYAN) + colorize(project_time, Colors.BRIGHT_CYAN, bold=True) + " " + colorize("🕐", Colors.BRIGHT_CYAN) + colorize(current_time, Colors.BRIGHT_WHITE, bold=True)

        # 按新格式组织信息
        parts = [
            account_info,                           # TigerAPI 余额
            get_model_info(),                       # 模型
            git_info,                               # git信息（分支+修改数+代码行数+落后分支）
            get_context_display(),                  # 上下文
            session_info,                           # 会话轮数 + API响应 + Shell/MCP（无竖线）
        ]

        parts.append(project_info)                  # 目录信息:目录总token(项目费用) + 时间

        print(separator.join(parts))
        
    except Exception:
        # 美化的错误回退显示
        fallback_parts = [
            colorize("🐯", Colors.YELLOW) + colorize("Tiger:", Colors.BRIGHT_CYAN) + colorize("N/A", Colors.RED),
            colorize("🤖", Colors.BLUE) + colorize("unknown", Colors.WHITE),
            colorize("📂", Colors.DIM) + colorize("no-git", Colors.DIM),
            colorize("🧠", Colors.GREEN) + colorize("0k", Colors.GREEN) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(0%)", Colors.GREEN),
            colorize("📁", Colors.YELLOW) + colorize("unknown", Colors.BRIGHT_WHITE, bold=True) + colorize(":", Colors.BRIGHT_CYAN) + colorize("0k", Colors.GREEN, bold=True) + colorize("(", Colors.BRIGHT_WHITE) + colorize("$0.00", Colors.GREEN) + colorize(") ", Colors.BRIGHT_WHITE) + colorize("⏱️ ", Colors.CYAN) + colorize("0h", Colors.BRIGHT_CYAN, bold=True) + " " + colorize("🕐", Colors.BRIGHT_CYAN) + colorize("00:00", Colors.BRIGHT_WHITE, bold=True)
        ]
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "
        print(separator.join(fallback_parts))

if __name__ == "__main__":
    main()