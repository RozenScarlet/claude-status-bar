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

本项目支持两种 Claude API 付费方式，请根据您的情况选择对应的版本：

### 方式一：按月付费（推荐大多数用户）

**获取 API ID：**

您的 Claude API ID 可以从 Claude API 后台获取。输入你的key点击查询后,浏览器的链接就会变成 `http://124.14.22.95:3002/admin-next/api-stats?apiId=你的api-id`

**配置方法：**

编辑 `status-final.py`（或 `~/.claude/status-final.py`），修改配置：

```python
CLAUDE_API_ID = "你的API_ID"
```

### 方式二：按量付费（SuperXiaoAi 用户）

如果您使用的是 SuperXiaoAi 的按量付费服务，需要使用 `status-final-按量付费.py` 文件。

**获取 SESSION_COOKIE 和 NEW_API_USER_ID：**

1. **打开 SuperXiaoAi 网站**
   - 在浏览器中访问：https://superxiaoai.com
   - 登录你的账号

2. **打开开发者工具**
   - 按键盘 `F12` 键
   - 或者右键点击页面 → 选择"检查"

3. **切换到 Network 标签**
   - 在开发者工具顶部找到 **Network**（网络）标签
   - 点击它

4. **刷新页面**
   - 按 `F5` 刷新页面
   - 或者访问你的用户中心页面

5. **找到 API 请求**
   - 在 Network 列表中找到 `user/self` 或 `api/user/self` 这个请求
   - 点击这个请求

6. **获取 NEW_API_USER_ID**
   - 在右侧找到 **Headers**（请求头）部分
   - 往下滚动找到 **Request Headers**
   - 找到 `new-api-user: 319` 这一行（数字会不同）
   - 这个数字就是你的 **NEW_API_USER_ID**

7. **获取 SESSION_COOKIE**
   - 在同一个请求的 Headers 中
   - 找到 **Cookie** 那一行
   - 找到 `session=MTc1O...` 这样的内容
   - 复制 `session=` 后面的整个长字符串（非常长，确保全部复制）
   - 这就是你的 **SESSION_COOKIE**

**配置方法：**

编辑 `status-final-按量付费.py`（或 `~/.claude/status-final-按量付费.py`），修改配置：

```python
SESSION_COOKIE = "你的SESSION_COOKIE"
NEW_API_USER_ID = "你的USER_ID"
```

**⚠️ 安全提醒：** 这两个值相当于你的登录凭证，请妥善保管，不要分享给他人！

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

### 2. 配置 API ID

编辑 `~/.claude/status-final.py`，修改第一行的 API ID：

```python
CLAUDE_API_ID = "你的API_ID"
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
