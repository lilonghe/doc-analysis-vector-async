#!/bin/bash

# Go 后端服务启动脚本

echo "🚀 启动 Go 后端服务..."

# 检查 Docker 是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 未启动，请先启动 Docker"
    exit 1
fi

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose down

# 构建并启动服务
echo "🔨 构建并启动服务..."
docker-compose up --build -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "📋 服务地址:"
echo "   - Go 后端: http://localhost:8081"
echo "   - 健康检查: http://localhost:8081/health"
echo "   - Redis: localhost:6379"
echo "   - ChromaDB: http://localhost:8000"
echo ""
echo "🔧 常用命令:"
echo "   - 查看日志: docker-compose logs -f backend-go"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart backend-go"
echo ""

# 检查服务健康状态
echo "🏥 检查服务健康状态..."
sleep 5

if curl -s http://localhost:8081/health > /dev/null; then
    echo "✅ Go 后端服务健康"
else
    echo "❌ Go 后端服务异常，请检查日志"
    docker-compose logs backend-go
fi