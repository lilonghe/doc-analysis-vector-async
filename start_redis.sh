#!/bin/bash

# Redis 启动脚本，使用持久化配置

echo "启动 Redis 服务器（带持久化配置）..."

# 创建数据目录
mkdir -p redis_data

# 启动 Redis
redis-server redis.conf --daemonize yes

# 检查启动状态
if pgrep -f "redis-server" > /dev/null; then
    echo "✅ Redis 服务启动成功"
    echo "   - RDB 持久化: 开启"
    echo "   - AOF 持久化: 开启" 
    echo "   - 数据目录: ./redis_data"
    echo "   - 日志文件: redis.log"
else
    echo "❌ Redis 服务启动失败"
    exit 1
fi