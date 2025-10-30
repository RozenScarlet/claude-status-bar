# Claude Status Bar

为 Claude Code 添加一个功能丰富的自定义状态栏，实时显示 API 使用情况、项目统计、Git 信息等。

## 功能特性

- 💰 实时显示 API 使用成本和代币消耗
- 📊 当前会话的统计信息（代币、成本、时长）
- 🤖 当前使用的模型信息
- 📁 项目文件统计（总行数、文件数等）
- 🔄 Git 仓库状态（分支、修改数等）
- 📈 上下文使用情况
- 🎨 彩色输出，清晰易读

## 快速开始

### 一键安装 🚀

#### Windows 用户

```bash
# 1. 克隆或下载本项目
git clone https://github.com/你的用户名/claude-status-bar.git
cd claude-status-bar

# 2. 运行安装脚本
setup.bat
```

#### Linux/Mac 用户

```bash
# 1. 克隆或下载本项目
git clone https://github.com/你的用户名/claude-status-bar.git
cd claude-status-bar

# 2. 运行安装脚本
chmod +x setup.sh
./setup.sh
```

安装脚本会自动：
1. ✅ 检查 Python 环境
2. ✅ 安装所需依赖（requests、urllib3）
3. ✅ 提示您输入 Claude API ID
4. ✅ 复制文件到 `~/.claude` 目录
5. ✅ 配置 API ID
6. ✅ 更新 Claude Code 的 `settings.json`
7. ✅ 自动备份原配置文件
8. ✅ 测试运行状态栏

安装完成后，重启 Claude Code 即可看到状态栏效果！

## 系统要求

- Python 3.6+
- Claude Code
- 依赖包：`requests`、`urllib3`（安装脚本会自动安装）

## 配置说明

本项目支持 **Super-Yi API**，使用自动登录获取 Token，无需手动配置复杂的 Cookie 信息！

### 配置步骤

编辑 `~/.claude/status-final.py`，修改顶部的配置信息：

```python
# Super-Yi 账号配置
SUPER_YI_EMAIL = "your-email@example.com"
SUPER_YI_PASSWORD = "your-password"
```

将 `your-email@example.com` 和 `your-password` 替换为你的 Super-Yi 账号和密码。

### 工作原理

脚本会自动：
1. ✅ 使用账号密码登录 Super-Yi API
2. ✅ 获取 Bearer Token 并缓存到本地（`~/.claude/.super_yi_token`）
3. ✅ Token 缓存 20 小时，过期自动刷新
4. ✅ 失败自动重试，无需人工干预

**⚠️ 安全提醒：**
- 配置文件包含您的登录凭证，请妥善保管
- 不要将包含真实账号密码的配置文件上传到公开仓库
- Token 缓存在本地，仅供当前用户访问

## 手动安装（不推荐）

如果自动安装脚本遇到问题，您也可以手动安装：

### 1. 复制文件

将 `status-final.py` 和 `run-status.bat`（Windows）复制到 `~/.claude` 目录：

```bash
# Windows
copy status-final.py %USERPROFILE%\.claude\
copy run-status.bat %USERPROFILE%\.claude\

# Linux/Mac
cp status-final.py ~/.claude/
cp run-status.bat ~/.claude/
```

### 2. 配置账号信息

编辑 `~/.claude/status-final.py`，修改顶部的配置：

```python
# Super-Yi 账号配置
SUPER_YI_EMAIL = "your-email@example.com"
SUPER_YI_PASSWORD = "your-password"
```

### 3. 安装依赖

```bash
pip install requests urllib3
```

### 4. 配置 Claude Code

编辑 `~/.claude/settings.json`，添加以下配置：

#### Windows

```json
{
  "statusLine": {
    "type": "command",
    "command": "C:\\Users\\你的用户名\\.claude\\run-status.bat"
  }
}
```

#### Linux/Mac

首先创建 `run-status.sh`：

```bash
cat > ~/.claude/run-status.sh << 'EOF'
#!/bin/bash
export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/status-final.py"
EOF

chmod +x ~/.claude/run-status.sh
```

然后配置：

```json
{
  "statusLine": {
    "type": "command",
    "command": "/home/你的用户名/.claude/run-status.sh"
  }
}
```

### 5. 重启 Claude Code

重启 Claude Code 以查看状态栏效果。

## 状态栏显示内容

状态栏包含以下信息：

- **总用量**: API 总代币数和总成本
- **模型**: 当前使用的 AI 模型
- **上下文**: 当前会话的上下文使用情况
- **项目**: 当前项目的统计信息（代币、成本、用时）
- **Git**: Git 仓库信息（如果在 Git 仓库中）

## 常见问题

### Q: 状态栏不显示怎么办？

1. 确认已正确配置 `settings.json`
2. 检查 Python 是否正确安装
3. 确认依赖包已安装：`pip list | grep requests`
4. 尝试手动运行脚本测试：`python ~/.claude/status-final.py`

### Q: API 统计信息不显示？

请确认您的 API ID 配置正确，并且 API 服务器可访问。

### Q: 如何卸载？

1. 删除 `~/.claude/status-final.py` 和 `~/.claude/run-status.bat`
2. 从 `~/.claude/settings.json` 中移除 `statusLine` 配置
3. 重启 Claude Code

## 自定义

您可以编辑 `status-final.py` 来自定义状态栏的显示内容和样式。脚本使用 ANSI 颜色代码来美化输出。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 支持

如果遇到问题，请在 GitHub 上提交 Issue。
