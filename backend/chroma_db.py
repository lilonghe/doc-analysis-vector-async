"""
ChromaDB向量数据库集成模块
用于存储和检索文档向量
"""

import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
import json
from datetime import datetime


class ChromaVectorDB:
    """ChromaDB向量数据库管理器"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        初始化ChromaDB
        
        Args:
            persist_directory: 数据库持久化目录
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            # 创建ChromaDB客户端
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "文档向量存储集合"}
            )
            
            print(f"✅ ChromaDB初始化成功，存储路径: {persist_directory}")
            
        except Exception as e:
            print(f"❌ ChromaDB初始化失败: {str(e)}")
            raise
    
    def store_document_chunks(self, file_id: str, filename: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> bool:
        """
        存储文档块到向量数据库
        
        Args:
            file_id: 文件ID
            filename: 文件名
            chunks: 文档块列表
            embeddings: 对应的向量嵌入列表
            
        Returns:
            存储是否成功
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError(f"块数量({len(chunks)})与向量数量({len(embeddings)})不匹配")
            
            # 准备数据
            ids = []
            documents = []
            metadatas = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{file_id}_chunk_{i}"
                ids.append(chunk_id)
                
                # 文档内容
                documents.append(chunk.get('content', ''))
                
                # 元数据
                metadata = {
                    "file_id": file_id,
                    "filename": filename,
                    "chunk_index": i,
                    "chunk_title": chunk.get('title', ''),
                    "chunk_summary": chunk.get('summary', ''),
                    "chunk_type": chunk.get('type', 'unknown'),
                    "created_at": datetime.now().isoformat(),
                    "content_length": len(chunk.get('content', ''))
                }
                metadatas.append(metadata)
            
            # 添加到集合
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            print(f"✅ 文档块存储成功: {filename} ({len(chunks)} 块)")
            return True
            
        except Exception as e:
            print(f"❌ 存储文档块失败: {str(e)}")
            return False
    
    def search_similar_documents(self, query_text: str, n_results: int = 5, file_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相似文档
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            file_id: 可选，限制搜索特定文件
            
        Returns:
            相似文档列表
        """
        try:
            # 构建查询条件
            where_clause = {}
            if file_id:
                where_clause["file_id"] = file_id
            
            # 执行搜索
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "distance": results['distances'][0][i],
                        "metadata": results['metadatas'][0][i]
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")
            return []
    
    def get_file_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """
        获取特定文件的所有块
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件块列表
        """
        try:
            results = self.collection.get(
                where={"file_id": file_id}
            )
            
            chunks = []
            if results['documents']:
                for i in range(len(results['documents'])):
                    chunk = {
                        "id": results['ids'][i],
                        "content": results['documents'][i],
                        "metadata": results['metadatas'][i]
                    }
                    chunks.append(chunk)
            
            # 按chunk_index排序
            chunks.sort(key=lambda x: x['metadata'].get('chunk_index', 0))
            return chunks
            
        except Exception as e:
            print(f"❌ 获取文件块失败: {str(e)}")
            return []
    
    def delete_file_chunks(self, file_id: str) -> bool:
        """
        删除特定文件的所有块
        
        Args:
            file_id: 文件ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取要删除的块ID
            results = self.collection.get(
                where={"file_id": file_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"✅ 已删除文件块: {file_id} ({len(results['ids'])} 块)")
                return True
            else:
                print(f"⚠️  文件块不存在: {file_id}")
                return True
                
        except Exception as e:
            print(f"❌ 删除文件块失败: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 获取所有数据
            all_data = self.collection.get()
            
            total_chunks = len(all_data['ids']) if all_data['ids'] else 0
            
            # 统计文件数量
            file_ids = set()
            if all_data['metadatas']:
                for metadata in all_data['metadatas']:
                    file_ids.add(metadata.get('file_id', ''))
            
            stats = {
                "total_files": len(file_ids),
                "total_chunks": total_chunks,
                "collection_name": self.collection.name,
                "persist_directory": self.persist_directory
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    def backup_collection(self, backup_path: str) -> bool:
        """
        备份集合数据
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            备份是否成功
        """
        try:
            all_data = self.collection.get()
            
            backup_data = {
                "collection_name": self.collection.name,
                "backup_time": datetime.now().isoformat(),
                "data": all_data
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 数据备份成功: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ 数据备份失败: {str(e)}")
            return False


def test_chroma_db():
    """测试ChromaDB功能"""
    try:
        # 创建测试实例
        db = ChromaVectorDB("./test_chroma_db")
        
        # 测试数据
        test_chunks = [
            {
                "title": "测试标题1",
                "content": "这是第一个测试文档块的内容",
                "summary": "第一个块的摘要",
                "type": "test"
            },
            {
                "title": "测试标题2", 
                "content": "这是第二个测试文档块的内容",
                "summary": "第二个块的摘要",
                "type": "test"
            }
        ]
        
        # 测试向量（随机）
        import random
        test_embeddings = [[random.random() for _ in range(1536)] for _ in range(2)]
        
        # 测试存储
        success = db.store_document_chunks(
            file_id="test_file_1",
            filename="test_document.pdf",
            chunks=test_chunks,
            embeddings=test_embeddings
        )
        
        if success:
            print("✅ ChromaDB测试成功")
            
            # 测试统计
            stats = db.get_collection_stats()
            print(f"📊 数据库统计: {stats}")
            
        else:
            print("❌ ChromaDB测试失败")
            
    except Exception as e:
        print(f"❌ ChromaDB测试出错: {str(e)}")


if __name__ == "__main__":
    test_chroma_db()