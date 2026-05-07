#!/bin/bash
set -e

echo "=== MiroFish 女娲 - 停止脚本 ==="

# 停止 Go 仿真引擎
if pgrep -f "bin/mirofish" > /dev/null; then
    pkill -f "bin/mirofish"
    echo "Go 仿真引擎已停止"
else
    echo "Go 仿真引擎未运行"
fi

# 停止 Python AI 智能体
if pgrep -f "ai-agent/main.py" > /dev/null; then
    pkill -f "ai-agent/main.py"
    echo "女娲 AI 智能体已停止"
else
    echo "女娲 AI 智能体未运行"
fi

echo "=== 所有服务已停止 ==="
