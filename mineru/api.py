"""
MinerU API服务
提供HTTP API接口用于PDF文档解析
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import traceback

try:
    from magic_pdf.api import convert_pdf_to_markdown
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False
    print("Warning: MinerU not available")

app = FastAPI(title="MinerU API", version="1.0.0")

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "mineru_available": MINERU_AVAILABLE
    }

@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    """解析PDF文档"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not MINERU_AVAILABLE:
        raise HTTPException(status_code=503, detail="MinerU not available")
    
    temp_dir = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="mineru_")
        
        # 保存上传的文件
        pdf_path = os.path.join(temp_dir, file.filename)
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 创建输出目录
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用MinerU解析
        result = convert_pdf_to_markdown(
            pdf_path=pdf_path,
            output_dir=output_dir,
            ocr_lang="zh-CN",
            parse_method="auto",
            output_format="markdown"
        )
        
        # 处理结果
        parsed_result = process_mineru_result(result, output_dir)
        
        return JSONResponse(content=parsed_result)
        
    except Exception as e:
        print(f"MinerU解析错误: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")
        
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

def process_mineru_result(result: Any, output_dir: str) -> Dict[str, Any]:
    """处理MinerU解析结果"""
    parsed_data = {
        "content": "",
        "metadata": {
            "total_pages": 0,
            "tables_count": 0,
            "images_count": 0,
            "formulas_count": 0
        },
        "tables": [],
        "images": [],
        "structure": {
            "headings": [],
            "paragraphs": [],
            "lists": []
        }
    }
    
    try:
        # 查找输出的markdown文件
        markdown_files = list(Path(output_dir).glob("*.md"))
        if markdown_files:
            markdown_path = markdown_files[0]
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            parsed_data["content"] = content
            
            # 简单统计
            parsed_data["metadata"]["total_pages"] = content.count("---")
            parsed_data["metadata"]["tables_count"] = content.count("|")
            parsed_data["metadata"]["images_count"] = content.count("![")
            parsed_data["metadata"]["formulas_count"] = content.count("$$")
            
            # 提取结构信息
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # 标题
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('# ').strip()
                    if title:
                        parsed_data["structure"]["headings"].append({
                            "level": level,
                            "title": title
                        })
                elif line and not line.startswith('#') and not line.startswith('|'):
                    # 段落
                    if len(line) > 10:  # 忽略太短的行
                        parsed_data["structure"]["paragraphs"].append(line)
        
    except Exception as e:
        print(f"处理MinerU结果时出错: {str(e)}")
        
    return parsed_data

if __name__ == "__main__":
    host = os.getenv("MINERU_API_HOST", "0.0.0.0")
    port = int(os.getenv("MINERU_API_PORT", "8888"))
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=False,
        workers=1
    )