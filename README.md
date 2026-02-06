# Claude Status Bar

为 Claude Code 添加一个功能丰富的自定义状态栏，实时显示 API 使用情况、项目统计、Git 信息等。

## 功能特性

- 💰 **TigerAPI 余额监控**：实时显示 TigerAPI 账户余额
- 🤖 **模型信息显示**：当前使用的模型（Opus/Sonnet/Haiku）带专属图标
- 📁 **项目统计**：当前项目的总Token消耗、费用、工作时间
- 🔄 **Git 仓库状态**：分支名、修改文件数等
- 🧠 **上下文使用情况**：基于百分比的智能颜色提示
- 🎨 **彩色输出**：ANSI颜色代码美化，清晰易读
- 🕐 **当前时间**：实时显示系统时间

## 状态栏预览

```
🐯Tiger:$123.45 ┃ ✨Opus 4.5 ┃ 🌿main(3) ┃ 🧠45k/200k(22%) ┃ 📁my-project:1.2M($18.50) ⏱️ 5.2h 🕐14:30
```

## 快速开始

### 一键安装

#### Windows 用户

```bash
# 1. 克隆项目
git clone https://github.com/RozenScarlet/claude-status-bar.git
cd claude-status-bar

# 2. 运行安装脚本
setup.bat
```

#### Linux/Mac 用户

```bash
# 1. 克隆项目
git clone https://github.com/RozenScarlet/claude-status-bar.git
cd claude-status-bar

# 2. 运行安装脚本
chmod +x setup.sh
./setup.sh
```

安装脚本会自动：
1. 检查 Python 环境
2. 安装所需依赖（requests、urllib3）
3. 复制文件到 `~/.claude` 目录
4. 提示您配置 API Key
5. 更新 Claude Code 的 `settings.json`
6. 自动备份原配置文件
7. 测试运行状态栏

## 系统要求

- Python 3.6+
- Claude Code
- 依赖包：`requests`、`urllib3`（安装脚本会自动安装）

## 配置说明

本项目支持 **TigerAPI**，用于获取账户余额信息。

### 配置步骤

编辑 `~/.claude/status-final.py`，修改顶部的配置信息：

```python
# TigerAPI 配置
TIGER_API_URL = "https://your-tiger-api-url.com"
TIGER_USERNAME = "your-username"
TIGER_PASSWORD = "your-password"
TIGER_QUOTA_PER_UNIT = 500000
```

按照实际的 TigerAPI 账户信息填写上述配置。

### 获取 TigerAPI 账户信息

1. 访问 TigerAPI 管理平台
2. 登录你的账号
3. 获取 API URL、用户名和密码

## 手动安装

如果自动安装脚本遇到问题，您也可以手动安装：

### 1. 复制文件

将 `status-final.py` 和 `run-status.bat`（Windows）复制到 `~/.claude` 目录：

```bash
# Windows
copy status-final.py %USERPROFILE%\.claude\
copy run-status.bat %USERPROFILE%\.claude\

# Linux/Mac
cp status-final.py ~/.claude/
```

### 2. 配置 TigerAPI

编辑 `~/.claude/status-final.py`，修改顶部的配置：

```python
TIGER_API_URL = "https://your-tiger-api-url.com"
TIGER_USERNAME = "your-username"
TIGER_PASSWORD = "your-password"
TIGER_QUOTA_PER_UNIT = 500000
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

状态栏包含以下信息（从左到右）：

| 模块 | 说明 | 示例 |
|------|------|------|
| **配额信息** | TigerAPI 账户余额 | `🐯Tiger:$123.45` |
| **模型** | 当前使用的 AI 模型 | `✨Opus 4.5` / `⚡Sonnet` / `🍃Haiku` |
| **Git** | Git 仓库信息 | `🌿main(3)` |
| **上下文** | 当前会话上下文使用量 | `🧠45k/200k(22%)` |
| **项目** | 项目统计信息 | `📁项目:1.2M($18.50) ⏱️5.2h 🕐14:30` |

### 颜色含义

#### TigerAPI 余额
- 绿色：余额充足（> $50）
- 黄色：余额偏低（$10 - $50）
- 红色：余额不足（< $10）

#### 上下文使用率
- 绿色：0-30%（轻松）
- 青色/蓝色：30-50%（正常）
- 黄色：50-70%（警告）
- 红色：70%以上（危险，建议清理）

#### Git 修改文件数
- 黄色数字：1-5个文件
- 橙色数字：6-10个文件
- 红色火焰：10个以上文件

## 常见问题

### Q: 状态栏不显示怎么办？

1. 确认已正确配置 `settings.json`
2. 检查 Python 是否正确安装
3. 确认依赖包已安装：`pip list | grep requests`
4. 尝试手动运行脚本测试：`python ~/.claude/status-final.py`

### Q: 配额信息显示"获取失败"？

请确认：
1. TigerAPI 配置信息正确（URL、用户名、密码）
2. 网络连接正常
3. TigerAPI 服务可访问

### Q: 上下文显示"ERR"？

这表示无法从 Claude Code 获取上下文信息。可能原因：
- 新启动的会话还没有消息
- transcript.jsonl 文件不存在

### Q: 如何自定义显示内容？

您可以编辑 `status-final.py` 中的 `main()` 函数来自定义状态栏的显示内容和顺序。

### Q: 如何卸载？

1. 删除 `~/.claude/status-final.py` 和 `~/.claude/run-status.bat`
2. 从 `~/.claude/settings.json` 中移除 `statusLine` 配置
3. 重启 Claude Code

## 更新日志

### v3.0.0 (2025-02)
- 新增：迁移至 TigerAPI，显示账户余额
- 新增：余额颜色分级提示（绿/黄/红）
- 移除：Cubence API 支持
- 移除：5小时+周窗口配额进度条

### v2.0.0 (2024-12)
- 新增：Cubence API 支持，5小时+周窗口配额显示
- 新增：重置时间倒计时显示
- 优化：上下文使用率改为基于百分比的阈值判断
- 优化：进度条视觉效果改进
- 优化：增强的数据结构支持，提高上下文获取成功率

### v1.0.0 (2024-10)
- 初始版本
- 支持 Super-Yi API
- 基础状态栏功能

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 支持

如果遇到问题，请在 GitHub 上提交 Issue。
