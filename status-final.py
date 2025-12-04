# ================================
# 配置区域 - 请修改下面的配置为你自己的
# ================================
# Cubence API 配置（从 https://cubence.com 获取）
CUBENCE_API_KEY = "sk-user-your-api-key-here"

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
def get_claude_api_stats():
    """获取Claude API统计信息 - 使用Cubence API"""
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

            # 解析API的数据结构
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

    # 生成进度条函数
    def make_progress_bar(usage_ratio, bar_length=10):
        precise_ratio = usage_ratio * bar_length
        full_blocks = int(precise_ratio)
        partial = precise_ratio - full_blocks

        # 根据使用率决定颜色
        if usage_ratio >= 0.8:
            fill_color = Colors.RED
        elif usage_ratio >= 0.4:
            fill_color = Colors.YELLOW
        else:
            fill_color = Colors.RED  # 已用部分用红色

        filled_bar = '█' * full_blocks
        partial_bar = '░' if partial > 0.5 else ''
        empty_length = bar_length - full_blocks - (1 if partial_bar else 0)
        empty_bar = '░' * empty_length

        return (
            colorize(filled_bar, fill_color) +
            colorize(partial_bar, Colors.YELLOW if partial > 0.5 else Colors.GREEN) +
            colorize(empty_bar, Colors.GREEN)
        )

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
    five_reset_part = colorize("(", Colors.DIM) + colorize("↻", Colors.BRIGHT_YELLOW) + colorize(five_reset_str, Colors.YELLOW) + colorize(")", Colors.DIM) if five_reset_str else ""

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
    week_reset_part = colorize("(", Colors.DIM) + colorize("↻", Colors.BRIGHT_YELLOW) + colorize(week_reset_str, Colors.YELLOW) + colorize(")", Colors.DIM) if week_reset_str else ""

    week_part = (
        colorize("周:", Colors.BRIGHT_MAGENTA) +
        week_bar +
        week_percentage +
        week_reset_part
    )

    return five_part + " " + week_part

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
    """获取Git分支和修改文件数"""
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

        # Git图标和颜色
        if modified_count > 0:
            if modified_count > 10:
                icon = "🔥"
                count_color = Colors.RED
            elif modified_count > 5:
                icon = "⚠️ "
                count_color = Colors.YELLOW
            else:
                icon = "📝"
                count_color = Colors.BRIGHT_YELLOW

            branch_part = colorize(f"🌿{branch}", Colors.GREEN)
            count_part = colorize(f"({modified_count})", count_color, bold=True)
            return colorize(icon, Colors.YELLOW) + branch_part + count_part
        else:
            return colorize("🌿", Colors.GREEN) + colorize(branch, Colors.BRIGHT_GREEN, bold=True)

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

        # 根据百分比设置颜色，更直观
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

    # 获取失败时显示"⚠️ERR"，区分"真的是0"和"获取失败"
    return colorize("⚠️", Colors.YELLOW) + colorize("ERR", Colors.YELLOW) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(??%)", Colors.DIM)

@safe_execute(None)
def get_context_usage():
    """获取当前会话的上下文使用量"""
    # 方法1：优先从 Claude Code stdin 获取（最准确）
    if claude_input:
        # 检查是否有 context 信息
        if claude_input.get('context'):
            context = claude_input['context']
            used = context.get('used_tokens', 0) or context.get('used', 0)
            total = context.get('limit', 200000) or context.get('total', 200000)
            if used > 0:
                return {
                    'used': used,
                    'total': total,
                    'percentage': round((used / total) * 100)
                }

        # 增强 usage 信息提取，支持更多字段
        if claude_input.get('usage'):
            usage = claude_input['usage']
            input_tokens = usage.get('input_tokens', 0)
            cache_read = usage.get('cache_read_input_tokens', 0)
            cache_create = usage.get('cache_creation_input_tokens', 0) or usage.get('cache_create_input_tokens', 0)

            if input_tokens > 0 or cache_read > 0:
                # input_tokens 已包含所有内容（系统提示+工具+消息）
                # cache_read 是从缓存读取的 tokens，也应计入上下文使用量
                active_tokens = input_tokens + cache_read + cache_create
                context_limit = 200000
                return {
                    'used': active_tokens,
                    'total': context_limit,
                    'percentage': round((active_tokens / context_limit) * 100)
                }

    # 方法2：解析最新的 transcript.jsonl 文件
    possible_dirs = [
        os.path.expanduser('~/.claude/projects'),
        os.path.expanduser('~/.claude/conversations'),
        os.path.join(os.getcwd(), '.claude'),
    ]

    latest_file = None
    latest_time = 0

    for projects_dir in possible_dirs:
        if not os.path.exists(projects_dir):
            continue

        for root, dirs, files in os.walk(projects_dir):
            for file in files:
                if file.endswith('.jsonl') or file == 'transcript.jsonl':
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = file_path

    if not latest_file:
        return None

    # 增加读取行数到100行，提高找到最新数据的概率
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 优先查找最近的完整消息对（user + assistant）
        # 从后往前找最新的 assistant 消息的 usage
        for line in reversed(lines[-100:]):
            try:
                data = json.loads(line.strip())
                usage = None

                # 支持更多的数据结构格式
                if data.get('type') == 'assistant' and data.get('message', {}).get('usage'):
                    usage = data['message']['usage']
                elif data.get('usage'):
                    usage = data['usage']
                elif data.get('response', {}).get('usage'):
                    usage = data['response']['usage']

                if usage and (usage.get('input_tokens', 0) > 0 or usage.get('cache_read_input_tokens', 0) > 0):
                    input_tokens = usage.get('input_tokens', 0)
                    cache_read = usage.get('cache_read_input_tokens', 0)
                    cache_create = usage.get('cache_creation_input_tokens', 0) or usage.get('cache_create_input_tokens', 0)

                    active_tokens = input_tokens + cache_read + cache_create
                    context_limit = 200000

                    return {
                        'used': active_tokens,
                        'total': context_limit,
                        'percentage': round((active_tokens / context_limit) * 100)
                    }
            except:
                continue
    except:
        pass

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
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path

    # Claude项目文件夹命名规则: C:\Users\Administrator -> C--Users-Administrator
    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    claude_folder_name_alt = claude_folder_name.replace('_', '-')

    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),
        current_dir_name.replace('-', '_')
    ]

    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "0k"

    project_tokens = 0

    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break

        if is_current_project:
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
                                project_tokens += input_tokens + output_tokens + cache_read_tokens + cache_create_tokens
                    except:
                        continue

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

    if current_dir_path.startswith('/c/'):
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path

    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    claude_folder_name_alt = claude_folder_name.replace('_', '-')

    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),
        current_dir_name.replace('-', '_')
    ]

    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "$0.00"

    project_cost = 0

    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break

        if is_current_project:
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

                                # 费用计算（Sonnet 3.5价格）
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

    if current_dir_path.startswith('/c/'):
        windows_path = 'C:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('/d/'):
        windows_path = 'D:' + current_dir_path[2:].replace('/', '\\')
    elif current_dir_path.startswith('C:') or current_dir_path.startswith('D:'):
        windows_path = current_dir_path
    else:
        windows_path = current_dir_path

    claude_folder_name = windows_path.replace(':', '--').replace('\\', '-')
    claude_folder_name_alt = claude_folder_name.replace('_', '-')

    project_dir_patterns = [
        claude_folder_name,
        claude_folder_name_alt,
        current_dir_name,
        current_dir_name.replace('_', '-'),
        current_dir_name.replace('-', '_')
    ]

    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.exists(projects_dir):
        return "0h"

    all_sessions = {}

    for folder_name in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        is_current_project = False
        for pattern in project_dir_patterns:
            if pattern in folder_name:
                is_current_project = True
                break

        if is_current_project:
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
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
                                    if session_id not in all_sessions:
                                        all_sessions[session_id] = []
                                    all_sessions[session_id].append(timestamp)
                                except:
                                    continue
                    except:
                        continue

    total_work_time = 0

    for session_id, timestamps in all_sessions.items():
        if len(timestamps) >= 2:
            timestamps.sort()
            session_time = timestamps[-1] - timestamps[0]
            session_time = min(session_time, 8 * 3600)  # 限制单个会话最长8小时
            total_work_time += session_time

    if total_work_time > 0:
        hours = total_work_time / 3600
        if hours >= 1:
            return f"{hours:.1f}h"
        else:
            minutes = hours * 60
            return f"{minutes:.0f}m"

    return "0h"

@safe_execute("00:00")
def get_current_time():
    """获取当前时间"""
    now = datetime.now()
    return now.strftime("%H:%M")

def main():
    """主函数"""
    try:
        # 获取API统计数据
        api_data = get_claude_api_stats()

        # 美化的分隔符
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "

        # 项目信息组合
        project_name = get_project_info()
        project_tokens = get_project_token_info()
        project_cost = get_project_cost()
        project_time = get_project_time()

        # 账户配额显示
        account_info = format_total_cost_display(api_data)

        # 当前时间
        current_time = get_current_time()

        # 格式：📁项目名:总token($费用) ⏱️工作时间 🕐当前时间
        project_info = (
            colorize("📁", Colors.YELLOW) +
            colorize(project_name, Colors.BRIGHT_WHITE, bold=True) +
            colorize(":", Colors.BRIGHT_CYAN) +
            colorize(project_tokens, Colors.GREEN, bold=True) +
            colorize("(", Colors.BRIGHT_WHITE) +
            colorize(project_cost, Colors.GREEN) +
            colorize(") ", Colors.BRIGHT_WHITE) +
            colorize("⏱️ ", Colors.CYAN) +
            colorize(project_time, Colors.BRIGHT_CYAN, bold=True) +
            " " +
            colorize("🕐", Colors.BRIGHT_CYAN) +
            colorize(current_time, Colors.BRIGHT_WHITE, bold=True)
        )

        # 按格式组织信息
        parts = [
            account_info,           # 配额信息（5h + 周）
            get_model_info(),       # 模型
            get_git_info(),         # git信息
            get_context_display(),  # 上下文
            project_info            # 项目信息
        ]

        print(separator.join(parts))

    except Exception:
        # 错误回退显示
        fallback_parts = [
            colorize("💰", Colors.GREEN) + colorize("5h:", Colors.BRIGHT_CYAN) + colorize("N/A", Colors.RED) + " " + colorize("周:", Colors.BRIGHT_MAGENTA) + colorize("N/A", Colors.RED),
            colorize("🤖", Colors.BLUE) + colorize("unknown", Colors.WHITE),
            colorize("📂", Colors.DIM) + colorize("no-git", Colors.DIM),
            colorize("🧠", Colors.GREEN) + colorize("0k", Colors.GREEN) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(0%)", Colors.GREEN),
            colorize("📁", Colors.YELLOW) + colorize("unknown", Colors.BRIGHT_WHITE, bold=True) + colorize(":", Colors.BRIGHT_CYAN) + colorize("0k", Colors.GREEN, bold=True) + colorize("(", Colors.BRIGHT_WHITE) + colorize("$0.00", Colors.GREEN) + colorize(") ", Colors.BRIGHT_WHITE) + colorize("⏱️ ", Colors.CYAN) + colorize("0h", Colors.BRIGHT_CYAN, bold=True) + " " + colorize("🕐", Colors.BRIGHT_CYAN) + colorize("00:00", Colors.BRIGHT_WHITE, bold=True)
        ]
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "
        print(separator.join(fallback_parts))

if __name__ == "__main__":
    main()
