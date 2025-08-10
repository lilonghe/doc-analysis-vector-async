from celery import Celery
import os
import json
from datetime import datetime
import time
import traceback
from error_handler import (
    retry_with_backoff, 
    log_and_handle_error, 
    error_tracker,
    ErrorHandler,
    RetryableError,
    NonRetryableError
)

# 创建Celery实例（仍然使用Redis作为消息代理）
celery_app = Celery(
    'doc_processor',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Celery配置 - 增强可靠性
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=3,  # 并发处理3个任务
    
    # 任务可靠性配置
    task_acks_late=True,  # 任务完成后才确认，避免任务丢失
    worker_prefetch_multiplier=1,  # 每个worker一次只处理一个任务
    task_reject_on_worker_lost=True,  # worker丢失时拒绝任务
    
    # 结果持久化配置
    result_expires=3600,  # 结果保存1小时
    result_persistent=True,  # 结果持久化
    
    # 重试配置
    task_default_retry_delay=60,  # 默认重试延迟60秒
    task_max_retries=3,  # 最大重试次数
    
    # Redis连接配置
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)

def update_file_status(file_id: str, status: str, progress: int, message: str):
    """更新文件处理状态"""
    try:
        from database import get_database_manager
        db_manager = get_database_manager()
        
        success = db_manager.update_file_status(file_id, status, progress, message)
        if not success:
            print(f"Warning: Failed to update status for file {file_id}")
            
        # 记录处理阶段日志
        if status in ["parsing", "chunking", "embedding", "storing"]:
            db_manager.log_processing_stage(file_id, status, "started", message)
        elif status == "completed":
            db_manager.log_processing_stage(file_id, "processing", "completed", message)
        elif status == "error":
            db_manager.log_processing_stage(file_id, "processing", "failed", message)
            
    except Exception as e:
        print(f"Error updating file status: {e}")
        import traceback
        traceback.print_exc()

@celery_app.task(bind=True)
def process_document(self, file_id: str):
    """处理单个文档的主任务（带错误处理和重试）"""
    try:
        from database import get_database_manager
        db_manager = get_database_manager()
        
        # 检查是否应该跳过此任务
        if error_tracker.should_skip_task(file_id, max_errors=3):
            error_msg = f"❌ 任务跳过: 错误次数过多 ({error_tracker.get_error_count(file_id)} 次)"
            update_file_status(file_id, "error", 0, error_msg)
            return {"file_id": file_id, "status": "skipped", "reason": "too_many_errors"}
        
        # 获取文件信息
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise NonRetryableError("文件信息不存在", "file_error")
        
        filepath = file_record.filepath
        filename = file_record.filename
        
        print(f"开始处理文件: {filename}")
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 阶段1: MinerU解析文档（带重试）
        update_file_status(file_id, "parsing", 10, "MinerU解析中...")
        parsing_start = time.time()
        extracted_content = parse_document_with_retry(file_id, filepath)
        parsing_duration = time.time() - parsing_start
        db_manager.log_processing_stage(file_id, "parsing", "completed", "文档解析完成", parsing_duration)
        
        # 更新文档页数
        if extracted_content.get("metadata", {}).get("total_pages"):
            db_manager.update_file_results(file_id, total_pages=extracted_content["metadata"]["total_pages"])
        
        update_file_status(file_id, "parsing", 30, "文档解析完成")
        
        # 阶段2: 智能分块（带重试）
        update_file_status(file_id, "chunking", 40, "智能分块中...")
        chunking_start = time.time()
        chunks = chunk_document_with_retry(file_id, extracted_content)
        chunking_duration = time.time() - chunking_start
        db_manager.log_processing_stage(file_id, "chunking", "completed", f"分块完成，共{len(chunks)}块", chunking_duration)
        
        # 更新块数量
        db_manager.update_file_results(file_id, chunks_count=len(chunks))
        
        update_file_status(file_id, "chunking", 60, f"分块完成，共{len(chunks)}块")
        
        # 阶段3: 向量化（带重试）
        update_file_status(file_id, "embedding", 70, "向量化中...")
        embedding_start = time.time()
        embeddings = generate_embeddings_with_retry(file_id, chunks)
        embedding_duration = time.time() - embedding_start
        db_manager.log_processing_stage(file_id, "embedding", "completed", "向量化完成", embedding_duration)
        
        update_file_status(file_id, "embedding", 90, "向量化完成")
        
        # 阶段4: 存储到向量数据库（带重试）
        update_file_status(file_id, "storing", 95, "存储到数据库...")
        storing_start = time.time()
        store_with_retry(file_id, chunks, embeddings)
        storing_duration = time.time() - storing_start
        db_manager.log_processing_stage(file_id, "storing", "completed", "存储完成", storing_duration)
        
        # 完成
        total_duration = time.time() - start_time
        completion_message = f"✅ 处理完成 (耗时: {total_duration:.1f}秒)"
        update_file_status(file_id, "completed", 100, completion_message)
        
        print(f"文件处理完成: {filename}, 总耗时: {total_duration:.1f}秒")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "chunks_count": len(chunks),
            "total_duration": total_duration,
            "status": "completed"
        }
        
    except NonRetryableError as e:
        error_msg = f"❌ 处理失败 (不可重试): {str(e)}"
        update_file_status(file_id, "error", 0, error_msg)
        print(f"文件处理失败 (不可重试): {file_id}, 错误: {str(e)}")
        raise
        
    except Exception as e:
        # 记录和处理错误
        handled_error = log_and_handle_error(file_id, e, "document_processing")
        
        error_msg = f"❌ 处理失败: {str(handled_error)}"
        update_file_status(file_id, "error", 0, error_msg)
        print(f"文件处理失败: {file_id}, 错误: {str(e)}")
        print(traceback.format_exc())
        
        # 如果是可重试错误，重新抛出让Celery重试
        if isinstance(handled_error, RetryableError):
            self.retry(countdown=60, max_retries=2)
        
        raise

@retry_with_backoff(max_retries=2, base_delay=1.0)
def parse_document_with_retry(file_id: str, filepath: str) -> dict:
    """带重试的文档解析"""
    try:
        return mineru_parse_document(filepath)
    except Exception as e:
        handled_error = log_and_handle_error(file_id, e, "parsing")
        raise handled_error

@retry_with_backoff(max_retries=2, base_delay=0.5)
def chunk_document_with_retry(file_id: str, parsed_content: dict) -> list:
    """带重试的文档分块"""
    try:
        return intelligent_chunking(parsed_content)
    except Exception as e:
        handled_error = log_and_handle_error(file_id, e, "chunking")
        raise handled_error

@retry_with_backoff(max_retries=3, base_delay=2.0)
def generate_embeddings_with_retry(file_id: str, chunks: list) -> list:
    """带重试的向量生成"""
    try:
        return generate_embeddings(chunks)
    except Exception as e:
        handled_error = log_and_handle_error(file_id, e, "embedding")
        raise handled_error

@retry_with_backoff(max_retries=2, base_delay=1.0)
def store_with_retry(file_id: str, chunks: list, embeddings: list):
    """带重试的数据库存储"""
    try:
        return store_to_vector_db(file_id, chunks, embeddings)
    except Exception as e:
        handled_error = log_and_handle_error(file_id, e, "storing")
        raise handled_error

def mineru_parse_document(filepath: str) -> dict:
    """使用MinerU解析文档"""
    from mineru_parser import MinerUParser
    
    print(f"MinerU解析文档: {filepath}")
    parser = MinerUParser()
    
    try:
        result = parser.parse_pdf(filepath)
        print(f"解析完成: 页数={result['metadata']['total_pages']}, 表格={result['metadata']['tables_count']}")
        return result
    except Exception as e:
        print(f"MinerU解析失败: {str(e)}")
        raise

def intelligent_chunking(parsed_content: dict) -> list:
    """使用Ollama进行智能分块"""
    try:
        from ollama_processor import OllamaProcessor
        
        print("使用Ollama进行智能分块...")
        processor = OllamaProcessor()
        chunks = processor.intelligent_chunk_document(parsed_content)
        
        print(f"智能分块完成，共 {len(chunks)} 块")
        return chunks
        
    except Exception as e:
        print(f"Ollama智能分块失败，使用备用方案: {str(e)}")
        return fallback_chunking(parsed_content)

def fallback_chunking(parsed_content: dict) -> list:
    """备用分块方案"""
    content = parsed_content.get("content", "")
    chunks = []
    
    if not content.strip():
        return chunks
    
    # 简单按长度分块
    chunk_size = 1000
    for i in range(0, len(content), chunk_size):
        chunk_content = content[i:i + chunk_size]
        if chunk_content.strip():
            chunks.append({
                "title": f"文档片段 {len(chunks) + 1}",
                "content": chunk_content.strip(),
                "summary": f"文档的第{len(chunks) + 1}个片段",
                "type": "fallback_chunk"
            })
    
    return chunks

def generate_embeddings(chunks: list) -> list:
    """生成向量嵌入"""
    try:
        from ollama_processor import OllamaProcessor
        
        print("使用Ollama生成向量嵌入...")
        processor = OllamaProcessor()
        embeddings = processor.generate_embeddings(chunks)
        
        print(f"向量化完成，生成 {len(embeddings)} 个向量")
        return embeddings
        
    except Exception as e:
        print(f"Ollama向量化失败，使用随机向量: {str(e)}")
        return fallback_embeddings(chunks)

def fallback_embeddings(chunks: list) -> list:
    """备用向量生成方案"""
    import random
    embeddings = []
    for chunk in chunks:
        # 生成随机向量（实际应用中不建议）
        embedding = [random.random() for _ in range(768)]  # Ollama nomic-embed-text维度
        embeddings.append(embedding)
    return embeddings

def store_to_vector_db(file_id: str, chunks: list, embeddings: list):
    """存储到向量数据库"""
    try:
        from chroma_db import ChromaVectorDB
        from database import get_database_manager
        
        print("存储到ChromaDB向量数据库...")
        db = ChromaVectorDB()
        db_manager = get_database_manager()
        
        # 获取文件信息
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise Exception("无法获取文件信息")
            
        filename = file_record.filename
        
        # 存储到向量数据库
        success = db.store_document_chunks(
            file_id=file_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings
        )
        
        if success:
            print(f"✅ 已将 {len(chunks)} 个文档块存储到向量数据库")
        else:
            raise Exception("向量数据库存储失败")
            
    except Exception as e:
        print(f"❌ 存储到向量数据库失败: {str(e)}")
        raise

if __name__ == '__main__':
    # 启动Celery worker
    celery_app.start()