# ================================
# 配置区域 - 请修改下面的配置为你自己的
# ================================
# Super-Yi 账号配置
SUPER_YI_EMAIL = "your-email@example.com"
SUPER_YI_PASSWORD = "your-password"

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
def login_super_yi():
    """登录 Super-Yi 获取 Bearer Token"""
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
                'email': SUPER_YI_EMAIL,
                'password': SUPER_YI_PASSWORD
            },
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('token'):
                token = data['token']
                # 缓存 token 到文件
                cache_file = os.path.expanduser('~/.claude/.super_yi_token')
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
def get_cached_token():
    """获取缓存的 token"""
    cache_file = os.path.expanduser('~/.claude/.super_yi_token')
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
    """获取Claude API统计信息"""
    try:
        # 先尝试使用缓存的 token
        bearer_token = get_cached_token()

        # 如果没有缓存或缓存过期，重新登录
        if not bearer_token:
            bearer_token = login_super_yi()
            if not bearer_token:
                return None

        response = requests.get(
            'https://super-yi.com/user-api/profile',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'authorization': f'Bearer {bearer_token}',
                'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
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
                user_data = data.get('user', {})

                # balanceCents: 剩余余额（美分）
                # totalCostCents: 已使用金额（美分）
                balance_cents = user_data.get('balanceCents', 0)
                total_cost_cents = user_data.get('usage', {}).get('totalCostCents', 0)

                # 转换为美元
                balance = balance_cents / 100.0
                current_cost = total_cost_cents / 100.0
                total_limit = balance + current_cost

                return {
                    'totalCost': current_cost,
                    'totalLimit': total_limit,
                    'dailyCost': 0,  # API未提供当日费用
                    'dailyLimit': 0
                }

        # 如果 token 失效(401或其他错误)，删除缓存并重试一次
        if response.status_code == 401 or response.status_code != 200:
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
                    'https://super-yi.com/user-api/profile',
                    headers={
                        'accept': 'application/json, text/plain, */*',
                        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'authorization': f'Bearer {bearer_token}',
                        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
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
                        user_data = data.get('user', {})
                        balance_cents = user_data.get('balanceCents', 0)
                        total_cost_cents = user_data.get('usage', {}).get('totalCostCents', 0)

                        balance = balance_cents / 100.0
                        current_cost = total_cost_cents / 100.0
                        total_limit = balance + current_cost

                        return {
                            'totalCost': current_cost,
                            'totalLimit': total_limit,
                            'dailyCost': 0,
                            'dailyLimit': 0
                        }
    except:
        pass
    return None

@safe_execute("获取失败")
def format_total_cost_display(api_data):
    """格式化总费用显示"""
    if not api_data:
        return colorize("获取失败", Colors.RED)

    current_cost = api_data.get('totalCost', 0)
    total_limit = api_data.get('totalLimit', 100)

    # 根据使用比例决定颜色和图标
    usage_ratio = current_cost / total_limit if total_limit > 0 else 0

    if usage_ratio >= 0.8:  # 80%以上
        cost_color = Colors.RED
        icon = "🚨"  # 警报：危险状态
    elif usage_ratio >= 0.4:  # 40-80%
        cost_color = Colors.YELLOW
        icon = "💸"  # 钱飞走：警告状态
    else:  # 0-40%
        cost_color = Colors.GREEN
        icon = "💰"  # 钱袋：安全状态

    cost_part = colorize(f"${current_cost:.2f}", cost_color)
    separator = colorize("/", Colors.BRIGHT_CYAN)
    limit_part = colorize(f"${total_limit:.2f}", Colors.CYAN)

    # 生成进度条 - 每格5%，内部6个状态（绿→黄→红，░→█）
    bar_length = 20  # 进度条显示长度（20格，每格5%）
    precise_ratio = usage_ratio * bar_length  # 精确的格数（0-20之间的小数）

    full_blocks = int(precise_ratio)  # 完整的格数
    partial = precise_ratio - full_blocks  # 小数部分（0-1）

    # 计算当前格内的百分比（0-5%）
    partial_percent = partial * 5

    # 根据格内进度确定字符和颜色
    if partial_percent < 1:  # 0-1%
        partial_char = '░'
        partial_color = Colors.GREEN
    elif partial_percent < 2:  # 1-2%
        partial_char = '█'
        partial_color = Colors.GREEN
    elif partial_percent < 3:  # 2-3%
        partial_char = '░'
        partial_color = Colors.YELLOW
    elif partial_percent < 4:  # 3-4%
        partial_char = '█'
        partial_color = Colors.YELLOW
    elif partial_percent < 5:  # 4-5%
        partial_char = '░'
        partial_color = Colors.RED
    else:  # 接近5%（会进位到下一格）
        partial_char = '█'
        partial_color = Colors.RED

    # 构建进度条：完整块（红色█） + 当前格 + 空白格（绿色░）
    filled_bar = '█' * full_blocks
    partial_bar = partial_char if partial > 0 else ''
    empty_length = bar_length - full_blocks - (1 if partial_bar else 0)
    empty_bar_chars = '░' * empty_length

    # 组装进度条
    progress_bar = (
        colorize(filled_bar, Colors.RED) +
        colorize(partial_bar, partial_color) +
        colorize(empty_bar_chars, Colors.GREEN)
    )

    # 百分比显示 - 根据使用率决定颜色
    if usage_ratio >= 0.8:
        perc_color = Colors.RED
    elif usage_ratio >= 0.4:
        perc_color = Colors.YELLOW
    else:
        perc_color = Colors.WHITE

    percentage = colorize(f" {usage_ratio * 100:.2f}%", perc_color)

    return colorize(icon, cost_color) + cost_part + separator + limit_part + " " + progress_bar + percentage

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
        
        # 根据token绝对数量设置颜色和图标：0-100k绿色，100k-150k黄色，150k-200k红色
        if used_tokens >= 150000:  # 150k以上
            icon = "😵‍💫"  # 头晕：高负载状态
            icon_color = Colors.RED
            used_color = Colors.RED
            perc_color = Colors.RED
        elif used_tokens >= 100000:  # 100k-150k
            icon = "🤔"  # 思考：中等负载状态
            icon_color = Colors.YELLOW
            used_color = Colors.YELLOW
            perc_color = Colors.YELLOW
        else:  # 0-100k
            icon = "🧠"  # 大脑：正常状态
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
    
    return colorize("🧠", Colors.GREEN) + colorize("0k", Colors.GREEN) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(0%)", Colors.GREEN)

@safe_execute(None)
def get_context_usage():
    """获取当前会话的上下文使用量 - 改进版"""
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

        # 检查是否有 usage 信息（有时在顶层）
        if claude_input.get('usage'):
            usage = claude_input['usage']
            input_tokens = usage.get('input_tokens', 0)
            cache_read = usage.get('cache_read_input_tokens', 0)
            if input_tokens > 0 or cache_read > 0:
                # 加上系统提示和工具定义的估算值
                system_overhead = 30000  # 系统提示+工具定义约30k
                active_tokens = input_tokens + cache_read + system_overhead
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

    # 读取最新的 usage 信息（改进：读取最后一条完整的消息对）
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 从后往前找最新的 assistant 消息的 usage
        for line in reversed(lines[-50:]):  # 增加到50行以确保找到完整信息
            try:
                data = json.loads(line.strip())
                usage = None

                if data.get('type') == 'assistant' and data.get('message', {}).get('usage'):
                    usage = data['message']['usage']
                elif data.get('usage'):
                    usage = data['usage']

                if usage and (usage.get('input_tokens', 0) > 0 or usage.get('cache_read_input_tokens', 0) > 0):
                    input_tokens = usage.get('input_tokens', 0)
                    cache_read = usage.get('cache_read_input_tokens', 0)

                    # 改进：系统开销包括系统提示(5k) + 工具定义(12k) + MCP工具(12k) + 预留(45k) ≈ 70-75k
                    # 但这部分已经在 input_tokens 中了，所以只需要加上预留空间
                    system_overhead = 50000  # 预留空间 + 一些系统开销

                    active_tokens = input_tokens + cache_read + system_overhead
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
    """获取账号池汇总信息"""
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
                return data.get('summary', {}).get('overall', {})

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
                        return data.get('summary', {}).get('overall', {})
    except:
        pass
    return None

@safe_execute("🔋N/A")
def format_account_pool_display(pool_data):
    """格式化账号池状态显示 - 分段进度条版（仅3种核心状态）"""
    if not pool_data:
        return colorize("🔋", Colors.BRIGHT_BLUE) + colorize("N/A", Colors.DIM)

    # 提取3种核心状态的账号数量
    total = pool_data.get('total', 0)
    normal = pool_data.get('normal', 0)          # 正常可用
    rate_limited = pool_data.get('rateLimited', 0)  # 速率限制
    blocked = pool_data.get('blocked', 0)        # 已阻止

    if total == 0:
        return colorize("🔋", Colors.BRIGHT_BLUE) + colorize("0", Colors.DIM)

    # 构建分段进度条 - 只显示3种核心状态
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

    # 组装显示：🔢总数[进度条]
    progress_bar = "".join(bar_parts)

    return (
        colorize("🔋", Colors.BRIGHT_BLUE) +
        colorize(str(total), Colors.WHITE, bold=True) +
        colorize("[", Colors.BRIGHT_CYAN) +
        progress_bar +
        colorize("]", Colors.BRIGHT_CYAN)
    )

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
        
        # 美化的分隔符 - 使用原始的"┃"符号并添加亮色
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "
        
        # 项目信息组合 - 简化显示
        project_name = get_project_info()
        project_tokens = get_project_token_info()
        project_cost = get_project_cost()
        project_time = get_project_time()

        # 账号池信息
        pool_data = get_account_pool_summary()

        # 账户余额 + 账号池状态组合（添加分隔符）
        account_info = format_total_cost_display(api_data) + " " + colorize("┃", Colors.BRIGHT_CYAN) + " " + format_account_pool_display(pool_data)

        # 当前时间
        current_time = get_current_time()

        # 格式：Administrator:2.9M($42.63) ⏱️ 2.5h 🕐20:49
        project_info = colorize("📁", Colors.YELLOW) + colorize(project_name, Colors.BRIGHT_WHITE, bold=True) + colorize(":", Colors.BRIGHT_CYAN) + colorize(project_tokens, Colors.GREEN, bold=True) + colorize("(", Colors.BRIGHT_WHITE) + colorize(project_cost, Colors.GREEN) + colorize(") ", Colors.BRIGHT_WHITE) + colorize("⏱️ ", Colors.CYAN) + colorize(project_time, Colors.BRIGHT_CYAN, bold=True) + " " + colorize("🕐", Colors.BRIGHT_CYAN) + colorize(current_time, Colors.BRIGHT_WHITE, bold=True)

        # 按新格式组织信息
        parts = [
            account_info,                           # 账户余额 + 今日费用
            get_model_info(),                       # 模型
            get_git_info(),                         # git信息
            get_context_display(),                  # 上下文
            project_info                            # 目录信息:目录总token(项目费用) + 时间
        ]
        
        print(separator.join(parts))
        
    except Exception:
        # 美化的错误回退显示
        fallback_parts = [
            colorize("获取失败", Colors.RED) + " " + colorize("┃", Colors.BRIGHT_CYAN) + " " + colorize("🔋", Colors.BRIGHT_BLUE) + colorize("N/A", Colors.DIM),
            colorize("🤖", Colors.BLUE) + colorize("unknown", Colors.WHITE),
            colorize("📂", Colors.DIM) + colorize("no-git", Colors.DIM),
            colorize("🧠", Colors.GREEN) + colorize("0k", Colors.GREEN) + colorize("/", Colors.BRIGHT_CYAN) + colorize("200k", Colors.CYAN) + colorize("(0%)", Colors.GREEN),
            colorize("📁", Colors.YELLOW) + colorize("unknown", Colors.BRIGHT_WHITE, bold=True) + colorize(":", Colors.BRIGHT_CYAN) + colorize("0k", Colors.GREEN, bold=True) + colorize("(", Colors.BRIGHT_WHITE) + colorize("$0.00", Colors.GREEN) + colorize(") ", Colors.BRIGHT_WHITE) + colorize("⏱️ ", Colors.CYAN) + colorize("0h", Colors.BRIGHT_CYAN, bold=True) + " " + colorize("🕐", Colors.BRIGHT_CYAN) + colorize("00:00", Colors.BRIGHT_WHITE, bold=True)
        ]
        separator = " " + colorize("┃", Colors.BRIGHT_CYAN) + " "
        print(separator.join(fallback_parts))

if __name__ == "__main__":
    main()