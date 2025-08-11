# 文档向量化处理系统

基于 MinerU + 大模型的智能文档解析和向量化存储系统，支持批量处理多个 PDF 文件。

## 🌟 功能特点

- 📁 **批量文件上传** - 支持多文件拖拽上传，实时进度显示
- 🤖 **智能文档解析** - 基于 MinerU 的高质量 PDF 解析，支持表格、图片、公式
- 🧠 **AI 智能分块** - 使用 OpenAI GPT 进行语义化智能分块
- 🔍 **向量化存储** - OpenAI Embedding + ChromaDB 向量数据库
- 📊 **实时状态追踪** - 文件处理进度实时展示，数据库持久化存储
- ⚡ **并发处理** - Celery 任务队列支持多文件并行处理
- 🔄 **错误重试** - 智能错误处理和重试机制
- 🔍 **语义搜索** - 基于向量相似度的文档内容搜索
- 💾 **数据持久化** - SQLite数据库存储，重启不丢失处理状态

## 🏗️ 技术架构

### 前端
- **React + TypeScript** - 现代化用户界面
- **Vite** - 快速开发构建工具  
- **TailwindCSS** - 响应式样式框架
- **Axios** - HTTP 客户端

### 后端
- **Python FastAPI** - 高性能 Web 框架
- **MinerU** - 专业文档解析引擎
- **OpenAI API** - 智能分块 + 向量化
- **ChromaDB** - 向量数据库
- **SQLite + SQLAlchemy** - 状态持久化存储
- **Celery + Redis** - 异步任务队列
- **Redis** - 消息代理（仅用于Celery）

### 核心处理流程
```
PDF 文件 → MinerU 解析 → OpenAI 智能分块 → OpenAI 向量化 → ChromaDB 存储
```

## 🚀 快速开始

### 环境要求
- **Python 3.8+**
- **Node.js 16+**
- **Redis**

### 1. 克隆项目
```bash
git clone <repository-url>
cd doc-vector
```

### 2. 后端设置
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 OPENAI_API_KEY 等参数
```

### 3. 前端设置
```bash
cd frontend

# 安装依赖
npm install
```

### 4. 启动服务

#### 方式一：使用启动脚本（推荐）
```bash
# 在项目根目录
./start.sh
```

#### 方式二：手动启动各服务
```bash
# 1. 启动 Redis
redis-server

# 2. 启动后端 API (终端1)
cd backend
uvicorn main:app --reload --port 8989

# 3. 启动 Celery Worker (终端2) 
cd backend
celery -A tasks worker --loglevel=info

# 4. 启动前端 (终端3)
cd frontend
npm run dev
```

### 5. 访问系统
- **前端界面**: http://localhost:3000
- **后端 API**: http://localhost:8989
- **API 文档**: http://localhost:8989/docs

## 💡 使用说明

### 1. 上传文档
- 支持拖拽或点击上传多个 PDF 文件
- 文件大小限制：100MB
- 支持批量处理

### 2. 处理流程
系统会自动显示每个文件的处理状态：
- ⏳ **等待处理** - 文件已上传，等待开始处理
- 🔄 **MinerU解析中** - 提取文档内容、表格、图片
- 🔄 **智能分块中** - AI 分析文档结构，进行语义分块  
- 🔄 **向量化中** - 生成文本嵌入向量
- 🔄 **存储中** - 保存到向量数据库
- ✅ **处理完成** - 可进行搜索查询

### 3. 文档搜索
处理完成后可以：
- 输入关键词进行语义搜索
- 查看相似度排序的搜索结果
- 查看数据库统计信息

### 4. 状态管理
- 实时查看处理进度和状态
- 支持删除单个文件
- 支持清空所有文件

## ⚙️ 配置说明

### 环境变量 (.env)
```bash
# OpenAI API 配置
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Redis 配置（仅用于Celery消息代理）
REDIS_URL=redis://localhost:6379/0

# 数据库配置
DATABASE_URL=sqlite:///./doc_vector.db

# 文件上传配置
MAX_FILE_SIZE=100
UPLOAD_DIR=uploads

# 向量数据库配置
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

## 📊 系统监控

### API 端点
- `GET /api/files/status` - 获取所有文件状态
- `POST /api/upload-files` - 批量上传文件
- `POST /api/process-all` - 开始处理所有文件
- `POST /api/search` - 向量搜索
- `GET /api/database/stats` - 数据库统计
- `GET /api/files/{file_id}/chunks` - 获取文件文档块
- `GET /api/files/{file_id}/logs` - 获取文件处理日志
- `POST /api/database/cleanup` - 清理旧记录
- `DELETE /api/files/{file_id}` - 删除文件

### 错误处理
系统具备完善的错误处理机制：
- **网络错误** - 自动重试
- **API 限额** - 智能退避重试
- **文件损坏** - 标记为不可重试
- **资源不足** - 暂停并重试

## 🔧 开发说明

### 项目结构
```
doc-vector/
├── backend/                 # Python 后端
│   ├── main.py             # FastAPI 主应用
│   ├── tasks.py            # Celery 任务定义
│   ├── database.py         # SQLAlchemy 数据库模型
│   ├── mineru_parser.py    # MinerU 解析器
│   ├── openai_processor.py # OpenAI 处理器
│   ├── chroma_db.py        # ChromaDB 操作
│   ├── error_handler.py    # 错误处理
│   ├── requirements.txt    # Python 依赖
│   ├── .env.example        # 环境变量示例
│   └── doc_vector.db       # SQLite 数据库文件
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── api.ts         # API 接口
│   │   └── types.ts       # 类型定义
│   └── package.json       # Node.js 依赖
├── uploads/               # 文件上传目录
├── chroma_db/            # ChromaDB 数据目录
├── start.sh              # 启动脚本
└── README.md             # 项目文档
```

### 扩展功能
- 支持更多文档格式（Word、PPT 等）
- 添加更多向量数据库支持
- 集成其他大模型 API
- 增加文档预处理功能

## 🐛 故障排除

### 常见问题
1. **Redis 连接失败**
   - 确保 Redis 服务已启动
   - 检查 REDIS_URL 配置

2. **OpenAI API 错误**
   - 验证 API Key 是否正确
   - 检查 API 额度是否充足

3. **MinerU 解析失败**
   - 检查 PDF 文件是否损坏
   - 确保系统内存充足

4. **数据库错误**
   - 检查数据库文件权限
   - 确保磁盘空间充足
   - 数据库会自动创建，无需手动初始化

5. **Celery Worker 无法启动**
   - 检查 Redis 连接
   - 确认依赖已正确安装

### 日志查看
- **后端日志**: 控制台输出
- **Celery 日志**: Worker 进程输出
- **前端日志**: 浏览器控制台

## 📈 性能优化

- **并发处理**: 默认 3 个文件同时处理
- **内存管理**: 大文件分批处理
- **数据持久化**: SQLite 数据库存储，重启不丢失状态
- **智能缓存**: 处理结果和状态本地缓存
- **错误恢复**: 智能重试机制
- **资源监控**: 详细的处理日志和统计信息

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 开源协议

MIT License

---

**🚀 Powered by MinerU + OpenAI + ChromaDB**

如有问题请查看 [API 文档](http://localhost:8000/docs) 或提交 Issue。