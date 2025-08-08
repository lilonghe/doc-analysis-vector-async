from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import uuid
import os
from datetime import datetime
import redis
import json

app = FastAPI(title="Document Vector Processing API")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis连接
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

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
        
        # 初始化文件状态
        file_info = {
            "id": file_id,
            "filename": file.filename,
            "filepath": file_path,
            "status": "pending",
            "progress": 0,
            "message": "等待处理中...",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 存储到Redis
        redis_client.set(f"file:{file_id}", json.dumps(file_info))
        
        uploaded_files.append({
            "id": file_id,
            "filename": file.filename,
            "status": "pending"
        })
    
    return {"files": uploaded_files, "message": f"成功上传 {len(uploaded_files)} 个文件"}

@app.get("/api/files/status")
async def get_all_files_status():
    """获取所有文件的处理状态"""
    files = []
    keys = redis_client.keys("file:*")
    
    for key in keys:
        file_data = redis_client.get(key)
        if file_data:
            file_info = json.loads(file_data)
            files.append({
                "id": file_info["id"],
                "filename": file_info["filename"],
                "status": file_info["status"],
                "progress": file_info["progress"],
                "message": file_info["message"],
                "updated_at": file_info["updated_at"]
            })
    
    # 按创建时间排序
    files.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"files": files}

@app.get("/api/files/{file_id}/status")
async def get_file_status(file_id: str):
    """获取单个文件的处理状态"""
    file_data = redis_client.get(f"file:{file_id}")
    if not file_data:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_info = json.loads(file_data)
    return {
        "id": file_info["id"],
        "filename": file_info["filename"],
        "status": file_info["status"],
        "progress": file_info["progress"],
        "message": file_info["message"],
        "updated_at": file_info["updated_at"]
    }

@app.post("/api/files/{file_id}/process")
async def process_file(file_id: str):
    """开始处理单个文件"""
    file_data = redis_client.get(f"file:{file_id}")
    if not file_data:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 导入Celery任务
    from tasks import process_document
    
    # 更新状态为等待处理
    file_info = json.loads(file_data)
    file_info.update({
        "status": "pending",
        "message": "已加入处理队列...",
        "updated_at": datetime.now().isoformat()
    })
    redis_client.set(f"file:{file_id}", json.dumps(file_info))
    
    # 提交到Celery队列
    task = process_document.delay(file_id)
    
    return {"message": f"文件 {file_id} 已加入处理队列", "task_id": task.id}

@app.post("/api/process-all")
async def process_all_files():
    """开始处理所有待处理的文件"""
    from tasks import process_document
    
    keys = redis_client.keys("file:*")
    processed_count = 0
    task_ids = []
    
    for key in keys:
        file_data = redis_client.get(key)
        if file_data:
            file_info = json.loads(file_data)
            if file_info["status"] == "pending":
                # 提交到Celery队列
                task = process_document.delay(file_info["id"])
                task_ids.append(task.id)
                processed_count += 1
    
    return {
        "message": f"已将 {processed_count} 个文件加入处理队列",
        "task_ids": task_ids
    }

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    file_data = redis_client.get(f"file:{file_id}")
    if not file_data:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_info = json.loads(file_data)
    
    # 删除向量数据库中的数据
    try:
        from chroma_db import ChromaVectorDB
        db = ChromaVectorDB()
        db.delete_file_chunks(file_id)
    except Exception as e:
        print(f"删除向量数据失败: {str(e)}")
    
    # 删除物理文件
    if os.path.exists(file_info["filepath"]):
        os.remove(file_info["filepath"])
    
    # 删除Redis记录
    redis_client.delete(f"file:{file_id}")
    
    return {"message": f"文件 {file_info['filename']} 已删除"}

@app.post("/api/search")
async def search_documents(query: dict):
    """向量搜索文档"""
    try:
        from chroma_db import ChromaVectorDB
        
        query_text = query.get("query", "")
        n_results = query.get("n_results", 5)
        file_id = query.get("file_id")  # 可选：限制搜索特定文件
        
        if not query_text.strip():
            raise HTTPException(status_code=400, detail="查询文本不能为空")
        
        db = ChromaVectorDB()
        results = db.search_similar_documents(
            query_text=query_text,
            n_results=n_results,
            file_id=file_id
        )
        
        return {"query": query_text, "results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/database/stats")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        from chroma_db import ChromaVectorDB
        
        db = ChromaVectorDB()
        stats = db.get_collection_stats()
        
        return {"stats": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.get("/api/files/{file_id}/chunks")
async def get_file_chunks(file_id: str):
    """获取文件的所有文档块"""
    try:
        from chroma_db import ChromaVectorDB
        
        # 检查文件是否存在
        file_data = redis_client.get(f"file:{file_id}")
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        db = ChromaVectorDB()
        chunks = db.get_file_chunks(file_id)
        
        return {"file_id": file_id, "chunks": chunks}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档块失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)