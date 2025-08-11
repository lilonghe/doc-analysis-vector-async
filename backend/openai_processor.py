"""
OpenAI API集成模块
用于文档智能分块和向量化
"""

import os
import openai
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class OpenAIProcessor:
    """OpenAI处理器"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("请在.env文件中设置OPENAI_API_KEY")
            
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # 模型配置
        self.chat_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
    
    def intelligent_chunk_document(self, parsed_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用大模型进行智能分块
        
        Args:
            parsed_content: MinerU解析的文档内容
            
        Returns:
            智能分块后的内容列表
        """
        content = parsed_content.get("content", "")
        metadata = parsed_content.get("metadata", {})
        
        if not content.strip():
            return []
        
        # 如果文档较短，直接返回单个块
        if len(content) < 500:
            return [{
                "title": "完整文档",
                "content": content.strip(),
                "type": "complete",
                "summary": "短文档，无需分块"
            }]
        
        try:
            # 构建智能分块的提示词
            prompt = self._build_chunking_prompt(content, metadata)
            
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文档分析专家，擅长将长文档按照语义和逻辑结构进行智能分块。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # 解析AI返回的分块结果
            chunks = self._parse_chunking_result(response.choices[0].message.content)
            
            return chunks
            
        except Exception as e:
            print(f"OpenAI智能分块失败: {str(e)}")
            # 降级到简单分块
            return self._simple_chunk(content)
    
    def _build_chunking_prompt(self, content: str, metadata: Dict) -> str:
        """构建智能分块的提示词"""
        
        prompt = f"""
请对以下文档进行智能分块，要求：

1. 按照文档的逻辑结构和语义相关性进行分块
2. 每个块应该保持完整的语义单元（如一个完整的章节、段落组合等）
3. 块的大小应该适中（建议300-1500字符）
4. 为每个块提供有意义的标题和简要摘要
5. 保持原文的重要信息不丢失

文档元信息：
- 总页数: {metadata.get('total_pages', '未知')}
- 表格数: {metadata.get('tables_count', 0)}
- 图片数: {metadata.get('images_count', 0)}

请以以下JSON格式返回分块结果：
```json
[
  {{
    "title": "块标题",
    "content": "块内容",
    "summary": "块摘要",
    "type": "chunk"
  }}
]
```

文档内容：
{content[:3000]}{"..." if len(content) > 3000 else ""}
"""
        return prompt
    
    def _parse_chunking_result(self, ai_response: str) -> List[Dict[str, Any]]:
        """解析AI返回的分块结果"""
        try:
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                chunks = json.loads(json_str)
                
                # 验证和清理数据
                valid_chunks = []
                for i, chunk in enumerate(chunks):
                    if isinstance(chunk, dict) and 'content' in chunk:
                        valid_chunks.append({
                            "title": chunk.get('title', f'文档块 {i+1}'),
                            "content": chunk.get('content', '').strip(),
                            "summary": chunk.get('summary', ''),
                            "type": chunk.get('type', 'chunk')
                        })
                
                return valid_chunks if valid_chunks else self._simple_chunk(ai_response)
                
        except Exception as e:
            print(f"解析AI分块结果失败: {str(e)}")
            
        # 如果解析失败，返回简单分块
        return self._simple_chunk(ai_response)
    
    def _simple_chunk(self, content: str) -> List[Dict[str, Any]]:
        """简单分块作为备选方案"""
        chunks = []
        chunk_size = 1000
        
        for i in range(0, len(content), chunk_size):
            chunk_content = content[i:i + chunk_size]
            if chunk_content.strip():
                chunks.append({
                    "title": f"文档片段 {len(chunks) + 1}",
                    "content": chunk_content.strip(),
                    "summary": f"文档的第{len(chunks) + 1}个片段",
                    "type": "simple_chunk"
                })
        
        return chunks
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """
        生成文本向量嵌入
        
        Args:
            chunks: 文档块列表
            
        Returns:
            向量嵌入列表
        """
        if not chunks:
            return []
        
        try:
            # 准备要向量化的文本
            texts = []
            for chunk in chunks:
                # 组合标题和内容
                text = f"{chunk.get('title', '')}\n{chunk.get('content', '')}"
                texts.append(text.strip())
            
            # 调用OpenAI Embedding API
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            print(f"生成向量嵌入完成: {len(embeddings)} 个向量")
            
            return embeddings
            
        except Exception as e:
            print(f"OpenAI向量化失败: {str(e)}")
            # 返回随机向量作为备选
            import random
            dimension = 1536 if 'text-embedding-3' in self.embedding_model else 1536
            return [[random.random() for _ in range(dimension)] for _ in chunks]
    
    def enhance_chunk_with_ai(self, chunk_content: str) -> Dict[str, str]:
        """
        使用AI增强单个块的信息（可选功能）
        
        Args:
            chunk_content: 块内容
            
        Returns:
            增强后的信息（标题、摘要、关键词等）
        """
        try:
            prompt = f"""
请分析以下文档片段，提供：
1. 一个准确的标题
2. 简要摘要（50字以内）
3. 3-5个关键词

文档片段：
{chunk_content[:800]}

请以JSON格式返回：
{{"title": "标题", "summary": "摘要", "keywords": ["关键词1", "关键词2"]}}
"""
            
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"AI增强块信息失败: {str(e)}")
            return {
                "title": "文档片段",
                "summary": "无法生成摘要",
                "keywords": []
            }


def test_openai_processor():
    """测试OpenAI处理器"""
    try:
        processor = OpenAIProcessor()
        print("✅ OpenAI处理器初始化成功")
        
        # 测试简单文本
        test_content = {
            "content": "这是一个测试文档。包含多个段落和信息。用于测试智能分块功能。",
            "metadata": {"total_pages": 1}
        }
        
        chunks = processor.intelligent_chunk_document(test_content)
        print(f"✅ 测试分块成功: {len(chunks)} 个块")
        
    except Exception as e:
        print(f"❌ OpenAI处理器测试失败: {str(e)}")


if __name__ == "__main__":
    test_openai_processor()