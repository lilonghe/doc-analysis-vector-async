# Docker 部署指南

本指南介绍如何使用 Docker 启动 Redis、PostgreSQL 和 ChromaDB，程序本地运行。

## 快速开始

### 1. 启动数据库服务

```bash
# 启动所有数据库服务
./start-services.sh
```

或者手动启动：

```bash
docker-compose up -d postgres redis chromadb
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑环境变量（可选，默认值已经配置好）
nano backend/.env
```

### 3. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 确保 Ollama 运行

```bash
# 启动 Ollama 服务
ollama serve

# 拉取所需模型
ollama pull llama3:8b
ollama pull nomic-embed-text
```

### 5. 启动应用程序

```bash
# 启动后端服务
cd backend
uvicorn main:app --reload --port 8001

# 启动 Celery 工作进程（另一个终端）
cd backend
celery -A tasks worker --loglevel=info --concurrency=2

# 启动前端服务（如果需要）
cd frontend
npm install
npm run dev
```

## 服务端口

- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379  
- **ChromaDB**: localhost:8000
- **后端API**: localhost:8001
- **前端**: localhost:3000

## 环境变量说明

```env
# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Redis配置
REDIS_URL=redis://localhost:6379/0

# PostgreSQL数据库配置
DATABASE_URL=postgresql://doc_user:doc_password@localhost:5432/doc_analysis

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8000

# 文件上传配置
MAX_FILE_SIZE=100  # MB
UPLOAD_DIR=uploads
```

## 数据库信息

### PostgreSQL
- **数据库**: doc_analysis
- **用户**: doc_user  
- **密码**: doc_password
- **端口**: 5432

### Redis
- **端口**: 6379
- **持久化**: AOF 已启用
- **数据目录**: docker volume `redis_data`

### ChromaDB
- **端口**: 8000
- **数据目录**: docker volume `chroma_data`

## 常用命令

### 启动/停止服务

```bash
# 启动服务
./start-services.sh

# 停止服务  
./stop-services.sh

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

### 数据库管理

```bash
# 连接到 PostgreSQL
docker-compose exec postgres psql -U doc_user -d doc_analysis

# 连接到 Redis
docker-compose exec redis redis-cli

# 检查 ChromaDB
curl http://localhost:8000/api/v1/heartbeat
```

### 数据备份与恢复

```bash
# PostgreSQL 备份
docker-compose exec postgres pg_dump -U doc_user doc_analysis > backup.sql

# PostgreSQL 恢复
docker-compose exec -T postgres psql -U doc_user doc_analysis < backup.sql

# 查看数据卷
docker volume ls | grep doc-analysis
```

## 故障排除

### 1. 端口冲突

如果端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "5433:5432"  # 改为其他端口
```

### 2. 数据库连接失败

检查环境变量中的数据库 URL 是否正确：

```bash
# 测试数据库连接
cd backend
python -c "from database import DatabaseManager; dm = DatabaseManager(); print('连接成功')"
```

### 3. Ollama 连接失败

确保 Ollama 服务在运行，并且模型已下载：

```bash
ollama list
curl http://localhost:11434/api/tags
```

### 4. ChromaDB 无法访问

检查 ChromaDB 服务状态：

```bash
docker-compose logs chromadb
curl http://localhost:8000/api/v1/heartbeat
```

## 数据持久化

所有数据都存储在 Docker volumes 中：

- `postgres_data`: PostgreSQL 数据
- `redis_data`: Redis 数据  
- `chroma_data`: ChromaDB 向量数据

### 清理数据

```bash
# 停止服务并删除数据卷
docker-compose down -v

# 重新启动（会重新初始化数据库）
./start-services.sh
```

## 生产环境建议

1. **修改默认密码**: 更改 PostgreSQL 默认密码
2. **配置备份**: 设置定期数据库备份
3. **监控服务**: 添加服务健康检查
4. **资源限制**: 在 docker-compose.yml 中设置资源限制
5. **日志管理**: 配置日志轮转

```yaml
# 在 docker-compose.yml 中添加资源限制
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```