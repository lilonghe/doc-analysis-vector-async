#!/bin/bash

echo "=== 启动文档分析系统的数据库服务 ==="

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

echo "📦 启动 PostgreSQL、Redis 和 ChromaDB..."

# 启动服务
docker-compose up -d postgres redis chromadb

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."

# 检查 PostgreSQL
if docker-compose exec -T postgres pg_isready -U doc_user -d doc_analysis > /dev/null 2>&1; then
    echo "✅ PostgreSQL 启动成功"
    echo "   - 主机: localhost:5432"
    echo "   - 数据库: doc_analysis"
    echo "   - 用户: doc_user"
else
    echo "❌ PostgreSQL 启动失败"
fi

# 检查 Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis 启动成功"
    echo "   - 主机: localhost:6379"
    echo "   - 持久化: AOF 已启用"
else
    echo "❌ Redis 启动失败"
fi

# 检查 ChromaDB
if curl -f http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
    echo "✅ ChromaDB 启动成功"
    echo "   - 主机: localhost:8000"
else
    echo "❌ ChromaDB 启动失败"
fi

echo ""
echo "🚀 数据库服务启动完成！"
echo ""
echo "📝 接下来的步骤："
echo "1. 复制环境变量文件: cp backend/.env.example backend/.env"
echo "2. 安装 Python 依赖: pip install -r backend/requirements.txt"
echo "3. 启动后端服务: cd backend && uvicorn main:app --reload"
echo "4. 启动 Celery 工作进程: cd backend && celery -A tasks worker --loglevel=info"
echo ""
echo "📋 停止服务命令: docker-compose down"
echo "📋 查看日志命令: docker-compose logs -f"