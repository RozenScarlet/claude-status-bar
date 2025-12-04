#!/bin/bash

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo
echo "========================================"
echo "  Claude Status Bar v2.0 一键配置工具"
echo "========================================"
echo

# 检测操作系统
OS_TYPE="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="mac"
fi
echo -e "${BLUE}[*] 检测到系统: $OS_TYPE${NC}"

# 检查 Python 是否已安装
echo -e "${BLUE}[1/5] 检查 Python 环境...${NC}"
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[错误] 未检测到 Python，请先安装 Python 3.6 或更高版本${NC}"
    echo "安装方法:"
    if [ "$OS_TYPE" = "mac" ]; then
        echo "  brew install python3"
    else
        echo "  sudo apt-get install python3 python3-pip  # Ubuntu/Debian"
        echo "  sudo yum install python3 python3-pip      # CentOS/RHEL"
    fi
    exit 1
fi
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}[√] Python 已安装: $PYTHON_VERSION${NC}"
echo

# 检查 pip
echo -e "${BLUE}[*] 检查 pip...${NC}"
PIP_CMD=""
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo -e "${YELLOW}[警告] 未找到 pip，尝试使用 python -m pip${NC}"
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# 安装依赖包
echo -e "${BLUE}[2/5] 安装Python依赖包...${NC}"
$PIP_CMD install --quiet requests urllib3 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[警告] 依赖包安装可能失败，但继续尝试...${NC}"
else
    echo -e "${GREEN}[√] 依赖包安装完成${NC}"
fi
echo

# 询问用户输入 API Key
echo -e "${BLUE}[3/5] 配置 Cubence API Key...${NC}"
echo "请输入您的 Cubence API Key:"
echo "(从 https://cubence.com 获取)"
read -p "API Key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo -e "${RED}[错误] API Key 不能为空${NC}"
    exit 1
fi
echo -e "${GREEN}[√] API Key 配置完成${NC}"
echo

# 定位 .claude 文件夹
echo -e "${BLUE}[4/5] 配置 Claude Code 设置...${NC}"
CLAUDE_DIR="$HOME/.claude"
if [ ! -d "$CLAUDE_DIR" ]; then
    echo -e "${RED}[错误] 未找到 .claude 文件夹: $CLAUDE_DIR${NC}"
    echo "请确保已安装 Claude Code"
    exit 1
fi
echo -e "${GREEN}[√] 找到 .claude 文件夹: $CLAUDE_DIR${NC}"

# 备份原settings.json
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "${BLUE}[*] 备份原设置文件...${NC}"
    BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE" 2>/dev/null
    echo -e "${GREEN}[√] 已备份到: $BACKUP_FILE${NC}"
fi

# 复制文件到 .claude 文件夹
echo -e "${BLUE}[*] 复制状态栏文件...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/status-final.py" "$CLAUDE_DIR/status-final.py"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 复制 status-final.py 失败${NC}"
    exit 1
fi
cp "$SCRIPT_DIR/run-status.bat" "$CLAUDE_DIR/run-status.bat" 2>/dev/null

# 创建 Unix shell 脚本版本
cat > "$CLAUDE_DIR/run-status.sh" << 'EOFSCRIPT'
#!/bin/bash
export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/status-final.py"
EOFSCRIPT

chmod +x "$CLAUDE_DIR/run-status.sh"
echo -e "${GREEN}[√] 文件复制完成${NC}"

# 替换 status-final.py 中的 API Key
echo -e "${BLUE}[*] 配置 API Key...${NC}"
STATUS_PY="$CLAUDE_DIR/status-final.py"

$PYTHON_CMD << EOF
import re
try:
    with open(r'$STATUS_PY', 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'CUBENCE_API_KEY\s*=\s*[\'"].*?[\'"]', 'CUBENCE_API_KEY = "$API_KEY"', content)
    with open(r'$STATUS_PY', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 配置 API Key 失败${NC}"
    exit 1
fi
echo -e "${GREEN}[√] API Key 配置完成${NC}"

# 更新 settings.json
echo -e "${BLUE}[*] 更新 Claude Code 配置...${NC}"

# 根据操作系统选择合适的启动脚本
if [ "$OS_TYPE" = "mac" ] || [ "$OS_TYPE" = "linux" ]; then
    RUN_SCRIPT="$CLAUDE_DIR/run-status.sh"
else
    RUN_SCRIPT="$CLAUDE_DIR/run-status.bat"
fi

$PYTHON_CMD << EOF
import json
import os

settings_file = "$SETTINGS_FILE"
run_script = "$RUN_SCRIPT"

# 读取现有配置
config = {}
if os.path.exists(settings_file):
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        pass

# 添加 statusLine 配置
config['statusLine'] = {
    'type': 'command',
    'command': run_script
}

# 写入配置
with open(settings_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("SUCCESS")
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 更新 settings.json 失败${NC}"
    exit 1
fi
echo -e "${GREEN}[√] Claude Code 配置更新完成${NC}"
echo

# 测试运行
echo -e "${BLUE}[5/5] 测试状态栏...${NC}"
echo
echo "----------------------------------------"
bash "$CLAUDE_DIR/run-status.sh" 2>/dev/null || $PYTHON_CMD "$CLAUDE_DIR/status-final.py"
echo "----------------------------------------"
echo

echo
echo "========================================"
echo -e "${GREEN}  配置完成！${NC}"
echo "========================================"
echo
echo "配置详情:"
echo "  - API Key: ${API_KEY:0:20}..."
echo "  - 状态栏脚本: $CLAUDE_DIR/status-final.py"
echo "  - 启动脚本: $RUN_SCRIPT"
echo "  - 配置文件: $SETTINGS_FILE"
echo
echo "请重启 Claude Code 以查看状态栏效果"
echo
