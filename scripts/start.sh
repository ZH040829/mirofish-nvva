#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== MiroFish 女娲 - 启动脚本 ==="

# 检查并启动 Go 仿真引擎
if ! curl -sf http://localhost:9090/api/health > /dev/null 2>&1; then
    echo "[1/3] 启动 Go 仿真引擎..."
    cd "$PROJECT_DIR"
    if [ ! -f bin/mirofish ]; then
        echo "  编译 Go 后端..."
        go build -o bin/mirofish ./cmd/server
    fi
    nohup ./bin/mirofish > /tmp/mirofish.log 2>&1 &
    echo "  Go 仿真引擎已启动 (PID: $!)"
else
    echo "[1/3] Go 仿真引擎已在运行"
fi

# 检查并启动 Python AI 智能体服务
if ! curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "[2/3] 启动女娲 AI 智能体..."
    cd "$PROJECT_DIR/ai-agent"
    nohup python main.py > /tmp/nuwa-ai.log 2>&1 &
    echo "  女娲 AI 智能体已启动 (PID: $!)"
else
    echo "[2/3] 女娲 AI 智能体已在运行"
fi

# 验证所有服务
echo "[3/3] 验证服务状态..."
sleep 2

GO_OK=$(curl -sf http://localhost:9090/api/health 2>/dev/null && echo "OK" || echo "FAIL")
AI_OK=$(curl -sf http://localhost:8000/api/health 2>/dev/null && echo "OK" || echo "FAIL")

echo ""
echo "=== 服务状态 ==="
echo "Go 仿真引擎  (9090): $GO_OK"
echo "女娲 AI 服务  (8000): $AI_OK"
echo ""
echo "访问地址:"
echo "  前端: https://zh040829.github.io/mirofish-nvva/"
echo "  Go API: http://localhost:9090/api/health"
echo "  AI API: http://localhost:8000/api/health"
