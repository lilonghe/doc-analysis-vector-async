#!/bin/bash

# 文档向量化处理系统启动脚本

echo "🚀 启动文档向量化处理系统..."

# 检查Redis是否运行
echo "📡 检查Redis服务..."
if ! pgrep -x "redis-server" > /dev/null; then
    echo "启动Redis服务器..."
    redis-server --daemonize yes
    sleep 2
fi

# 检查环境变量文件
if [ ! -f "backend/.env" ]; then
    echo "⚠️  请先复制 backend/.env.example 到 backend/.env 并配置相关参数"
    cp backend/.env.example backend/.env
    echo "✅ 已创建 backend/.env 文件，请编辑后重新运行"
    exit 1
fi

# 启动后端API服务器
echo "🌐 启动后端API服务器 (端口8000)..."
cd backend
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 3

# 启动Celery Worker
echo "⚙️  启动Celery任务队列..."
celery -A tasks worker --loglevel=info --concurrency=3 &
CELERY_PID=$!

sleep 2

# 启动前端开发服务器
echo "🎨 启动前端开发服务器 (端口3000)..."
cd ../frontend

# 检查是否安装了依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

echo ""
echo "🎉 系统启动完成!"
echo ""
echo "📍 服务地址:"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "🛑 按 Ctrl+C 停止所有服务"
echo ""

# 等待用户中断
trap 'echo "正在停止服务..."; kill $BACKEND_PID $CELERY_PID $FRONTEND_PID; exit' INT
wait