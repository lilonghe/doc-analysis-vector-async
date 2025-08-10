#!/bin/bash

echo "=== 停止文档分析系统的数据库服务 ==="

# 停止服务
docker-compose down

echo "✅ 所有服务已停止"
echo ""
echo "📋 可选操作："
echo "- 查看日志: docker-compose logs -f"
echo "- 清理数据: docker-compose down -v"
echo "- 重新启动: ./start-services.sh"