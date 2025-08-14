# Go 后端服务

基于 Go 1.23 开发的文档分析向量数据库后端服务，采用现代化技术栈实现高性能文档处理。

## ✨ 技术栈

### 🎯 核心框架
- **Web 框架**: Gin v1.10+ (高性能 HTTP 框架)
- **数据库 ORM**: GORM v1.25+ (支持 SQLite/PostgreSQL)
- **任务队列**: Asynq v0.25+ + Redis (持久化任务处理)
- **配置管理**: 环境变量 + .env 文件
- **容器化**: Docker 多阶段构建

### 📦 主要依赖
```go
require (
    github.com/gin-contrib/cors v1.7.6      // CORS 中间件
    github.com/gin-gonic/gin v1.10.1        // Web 框架
    github.com/hibiken/asynq v0.25.1        // 任务队列
    github.com/redis/go-redis/v9 v9.12.1    // Redis 客户端
    gorm.io/gorm v1.25.12                   // ORM
    github.com/google/uuid v1.6.0           // UUID 生成
    github.com/joho/godotenv v1.5.1         // 环境变量加载
)
```

## 🏗️ 架构设计

```
backend-go/
├── main.go                    # 应用入口
├── config/
│   └── config.go             # 配置管理
├── models/
│   └── models.go             # 数据模型
├── database/
│   └── database.go           # 数据库连接
├── queue/
│   └── queue.go              # 任务队列
├── handlers/
│   └── file_handler.go       # HTTP 处理器
├── services/
│   └── chroma_service.go     # ChromaDB 服务
├── middleware/
│   └── middleware.go         # 中间件
├── utils/
│   └── response.go           # 响应工具
├── uploads/                  # 文件上传目录
├── Dockerfile               # Docker 构建
└── .env                     # 环境配置
```

## 🚀 核心功能

### 📁 文件管理
- ✅ 批量文件上传 (`POST /api/upload-files`)
- ✅ 文件状态查询 (`GET /api/files/status`)
- ✅ 单个文件状态 (`GET /api/files/:id/status`)
- ✅ 文件处理触发 (`POST /api/files/:id/process`)
- ✅ 批量处理 (`POST /api/process-all`)
- ✅ 文件删除 (`DELETE /api/files/:id`)

### ⚡ 任务处理
- **持久化任务队列**: 基于 Asynq + Redis
- **故障恢复**: 程序重启不丢失任务
- **状态追踪**: 实时任务状态更新
- **重试机制**: 自动重试失败任务
- **并发处理**: 支持多 Worker 处理

### 🗄️ 数据存储
- **关系数据库**: SQLite/PostgreSQL 存储元数据
- **向量数据库**: ChromaDB HTTP 客户端集成
- **文件系统**: 本地文件存储

## ⚙️ 配置说明

### 环境变量
```bash
# 服务器配置
HOST=0.0.0.0
PORT=8080

# 数据库配置
DATABASE_DRIVER=sqlite
DATABASE_URL=./data.db

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

## 🚀 快速启动

### 方式1: 本地开发
```bash
cd backend-go

# 安装依赖
go mod tidy

# 配置环境变量
cp .env.example .env  # 编辑配置

# 启动依赖服务（Redis + ChromaDB）
docker-compose up redis chromadb -d

# 启动 Go 服务
go run main.go
```

### 方式2: Docker 完整部署
```bash
cd backend-go

# 一键启动所有服务
./start.sh

# 或手动启动
docker-compose up --build -d
```

### 方式3: 集成现有环境
```bash
# 在主项目目录
docker-compose up --build

# Go 后端将在 8080 端口启动
# 替换原 Python + Celery 架构
```

## 📊 性能特点

### 🎯 性能优势
- **启动时间**: < 1秒 (vs Python ~5秒)
- **内存占用**: ~50MB (vs Python ~200MB)
- **并发处理**: 支持数万并发连接
- **CPU 效率**: 原生编译，无解释器开销

### 📈 扩展性
- **水平扩展**: 支持多实例部署
- **任务分发**: Redis 队列天然支持分布式
- **数据库**: 支持 PostgreSQL 集群
- **容器化**: Docker + K8s 友好

## 🔧 开发指南

### 添加新的 API 端点
```go
// handlers/new_handler.go
func (h *NewHandler) NewEndpoint(c *gin.Context) {
    utils.Success(c, map[string]interface{}{
        "message": "success",
    })
}

// main.go
api.GET("/new-endpoint", newHandler.NewEndpoint)
```

### 添加新的任务类型
```go
// queue/queue.go
const TaskNewType = "new_task_type"

func EnqueueNewTask(data string) error {
    // 实现任务入队逻辑
}

func HandleNewTask(ctx context.Context, t *asynq.Task) error {
    // 实现任务处理逻辑
}
```

## 🔍 监控和调试

### 健康检查
```bash
curl http://localhost:8080/health
```

### 任务队列监控
- Asynq 提供 Web UI: `asynq.WebUI()`
- Redis CLI 查看队列状态

### 日志配置
- 结构化日志输出
- 支持不同日志级别
- 请求链路追踪

## 🚦 状态码说明

| 状态 | 描述 |
|------|------|
| pending | 等待处理 |
| processing | 正在处理 |
| completed | 处理完成 |
| error | 处理失败 |

## 🔄 与 Python 版本对比

| 特性 | Python 版本 | Go 版本 |
|------|-------------|---------|
| Web 框架 | FastAPI | Gin |
| 任务队列 | Celery | Asynq |
| ORM | SQLAlchemy | GORM |
| 启动时间 | ~5秒 | <1秒 |
| 内存占用 | ~200MB | ~50MB |
| 并发能力 | 受 GIL 限制 | 原生协程 |
| 部署复杂度 | 高 | 低 |

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 发起 Pull Request

## 📄 许可证

MIT License