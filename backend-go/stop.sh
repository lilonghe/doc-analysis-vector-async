#!/bin/bash

# Go 后端服务停止脚本

echo "🛑 停止 Go 后端服务..."

# 停止并删除容器
docker-compose down

# 可选：清理数据卷（谨慎使用）
if [ "$1" = "--clean" ]; then
    echo "🗑️  清理数据卷..."
    docker-compose down -v
    docker volume prune -f
fi

echo "✅ 服务已停止"