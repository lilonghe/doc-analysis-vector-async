from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import uuid
import os
from datetime import datetime
from database import get_database_manager, file_record_to_dict
from chroma_db import ChromaVectorDB

app = FastAPI(title="Document Vector Processing API")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库管理器
db_manager = get_database_manager()

# 全局ChromaDB实例
vector_db = None

def get_vector_db():
    """获取ChromaDB实例（单例模式）"""
    global vector_db
    if vector_db is None:
        vector_db = ChromaVectorDB()
    return vector_db

# 确保上传目录存在
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Document Vector Processing API"}

@app.post("/api/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """批量上传PDF文件"""
    uploaded_files = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"只支持PDF文件: {file.filename}")
        
        # 生成唯一文件ID
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 创建数据库记录
        try:
            db_manager.create_file_record(
                file_id=file_id,
                filename=file.filename,
                filepath=file_path
            )
            
            uploaded_files.append({
                "id": file_id,
                "filename": file.filename,
                "status": "pending"
            })
        except Exception as e:
            # 如果数据库操作失败，删除已保存的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")
    
    return {"files": uploaded_files, "message": f"成功上传 {len(uploaded_files)} 个文件"}

@app.get("/api/files/status")
async def get_all_files_status():
    """获取所有文件的处理状态"""
    try:
        file_records = db_manager.get_all_file_records()
        files = [file_record_to_dict(record) for record in file_records]
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件状态失败: {str(e)}")

@app.get("/api/files/{file_id}/status")
async def get_file_status(file_id: str):
    """获取单个文件的处理状态"""
    try:
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return file_record_to_dict(file_record)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件状态失败: {str(e)}")

@app.post("/api/files/{file_id}/process")
async def process_file(file_id: str):
    """开始处理单个文件"""
    try:
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 导入Celery任务
        from tasks import process_document
        
        # 更新状态为等待处理
        db_manager.update_file_status(file_id, "pending", 0, "已加入处理队列...")
        
        # 提交到Celery队列
        task = process_document.delay(file_id)
        
        return {"message": f"文件 {file_id} 已加入处理队列", "task_id": task.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动处理失败: {str(e)}")

@app.post("/api/process-all")
async def process_all_files():
    """开始处理所有待处理的文件"""
    try:
        from tasks import process_document
        
        # 获取所有待处理的文件
        all_records = db_manager.get_all_file_records()
        pending_files = [record for record in all_records if record.status == "pending"]
        
        task_ids = []
        for file_record in pending_files:
            # 提交到Celery队列
            task = process_document.delay(file_record.id)
            task_ids.append(task.id)
        
        return {
            "message": f"已将 {len(pending_files)} 个文件加入处理队列",
            "task_ids": task_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    try:
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除向量数据库中的数据
        try:
            db = get_vector_db()
            db.delete_file_chunks(file_id)
        except Exception as e:
            print(f"删除向量数据失败: {str(e)}")
        
        # 删除物理文件
        if os.path.exists(file_record.filepath):
            os.remove(file_record.filepath)
        
        # 删除数据库记录
        db_manager.delete_file_record(file_id)
        
        return {"message": f"文件 {file_record.filename} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@app.post("/api/search")
async def search_documents(query: dict):
    """向量搜索文档"""
    try:
        query_text = query.get("query", "")
        n_results = query.get("n_results", 5)
        file_id = query.get("file_id")  # 可选：限制搜索特定文件
        
        if not query_text.strip():
            raise HTTPException(status_code=400, detail="查询文本不能为空")
        
        db = get_vector_db()
        results = db.search_similar_documents(
            query_text=query_text,
            n_results=n_results,
            file_id=file_id
        )
        
        return {"query": query_text, "results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/database/stats")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        # 获取处理统计
        processing_stats = db_manager.get_processing_statistics()
        
        # 获取向量数据库统计
        try:
            vector_db_instance = get_vector_db()
            vector_stats = vector_db_instance.get_collection_stats()
        except Exception as e:
            print(f"获取向量数据库统计失败: {str(e)}")
            vector_stats = {"error": "无法获取向量数据库统计"}
        
        return {
            "stats": {
                **processing_stats,
                "vector_db": vector_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.get("/api/files/{file_id}/chunks")
async def get_file_chunks(file_id: str):
    """获取文件的所有文档块"""
    try:
        # 检查文件是否存在
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        db = get_vector_db()
        chunks = db.get_file_chunks(file_id)
        
        return {"file_id": file_id, "chunks": chunks}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档块失败: {str(e)}")

@app.get("/api/files/{file_id}/logs")
async def get_file_processing_logs(file_id: str):
    """获取文件处理日志"""
    try:
        file_record = db_manager.get_file_record(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        logs = db_manager.get_processing_logs(file_id)
        log_data = []
        for log in logs:
            log_data.append({
                "stage": log.stage,
                "status": log.status,
                "message": log.message,
                "duration": log.duration,
                "created_at": log.created_at.isoformat()
            })
        
        return {"file_id": file_id, "logs": log_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处理日志失败: {str(e)}")

@app.post("/api/database/cleanup")
async def cleanup_old_records():
    """清理旧记录"""
    try:
        result = db_manager.cleanup_old_records(days=7)
        return {
            "message": "清理完成",
            "deleted_files": result["deleted_files"],
            "deleted_logs": result["deleted_logs"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)