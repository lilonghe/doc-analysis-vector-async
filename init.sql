-- PostgreSQL 初始化脚本
-- 创建文档分析系统所需的数据表

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 文件信息表
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'uploaded',
    progress INTEGER DEFAULT 0,
    message TEXT,
    total_pages INTEGER,
    chunks_count INTEGER,
    processing_duration FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP，
    error_count INTEGER DEFAULT 0,
    last_error TEXT
);

-- 处理阶段日志表
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    duration FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 文档块表（可选，如果需要在关系数据库中也存储块信息）
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    summary TEXT,
    chunk_type VARCHAR(50) DEFAULT 'chunk',
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_files_upload_time ON files(upload_time);
CREATE INDEX IF NOT EXISTS idx_processing_logs_file_id ON processing_logs(file_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(stage);
CREATE INDEX IF NOT EXISTS idx_document_chunks_file_id ON document_chunks(file_id);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为 files 表添加更新时间触发器
DROP TRIGGER IF EXISTS update_files_updated_at ON files;
CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON files
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入一些示例数据（可选）
INSERT INTO files (filename, filepath, file_size, mime_type, status) 
VALUES 
    ('sample.pdf', '/uploads/sample.pdf', 1024000, 'application/pdf', 'uploaded')
ON CONFLICT DO NOTHING;

-- 创建数据库用户权限（如果需要）
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO doc_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO doc_user;

-- 显示创建的表
\dt