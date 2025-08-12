"""
PDF文档解析模块
使用PyPDF2进行PDF文档解析
"""

import os
from typing import Dict, Any
import traceback


class MinerUParser:
    """PDF文档解析器"""
    
    def __init__(self, api_host: str = None, api_port: int = None):
        """
        初始化PDF解析器
        """
        # 保留参数以兼容旧版本调用
        pass
        
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        解析PDF文档
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            解析结果字典，包含文本内容、表格、图片等信息
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        try:
            print(f"📄 使用PyPDF2解析PDF: {os.path.basename(pdf_path)}")
            return self._pypdf2_parse(pdf_path)
            
        except Exception as e:
            print(f"PDF解析失败: {str(e)}")
            print(traceback.format_exc())
            return {
                "content": f"解析失败: {str(e)}",
                "metadata": {"total_pages": 0, "parser": "failed"},
                "tables": [],
                "images": [],
                "structure": {"headings": [], "paragraphs": [], "lists": []}
            }
    
    def _pypdf2_parse(self, pdf_path: str) -> Dict[str, Any]:
        """使用PyPDF2解析PDF"""
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = ""
                total_pages = len(pdf_reader.pages)
                
                print(f"📖 开始解析 {total_pages} 页PDF文档...")
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        content += f"\n=== 第 {page_num + 1} 页 ===\n"
                        content += page_text + "\n"
                        
                        if (page_num + 1) % 5 == 0:  # 每5页打印一次进度
                            print(f"📄 已解析 {page_num + 1}/{total_pages} 页")
                            
                    except Exception as e:
                        print(f"⚠️ 第{page_num + 1}页解析出错: {str(e)}")
                        content += f"\n=== 第 {page_num + 1} 页 (解析失败) ===\n"
                        content += f"解析错误: {str(e)}\n"
                
                # 简单的内容分析
                lines = content.split('\n')
                paragraphs = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
                
                # 统计信息
                tables_count = content.count('|') // 10  # 简单估算表格数量
                
                result = {
                    "content": content,
                    "metadata": {
                        "total_pages": total_pages,
                        "tables_count": tables_count,
                        "images_count": 0,  # PyPDF2无法提取图片
                        "formulas_count": content.count('$') // 2,  # 简单估算公式
                        "parser": "PyPDF2",
                        "content_length": len(content)
                    },
                    "tables": [],  # PyPDF2无法提取结构化表格
                    "images": [],  # PyPDF2无法提取图片
                    "structure": {
                        "headings": self._extract_headings(content),
                        "paragraphs": paragraphs[:50],  # 限制段落数量
                        "lists": []
                    }
                }
                
                print(f"✅ PyPDF2解析完成: {total_pages} 页，{len(content)} 字符")
                return result
                
        except ImportError:
            raise Exception("PyPDF2 未安装，无法解析PDF")
        except Exception as e:
            print(f"PyPDF2解析失败: {str(e)}")
            raise
    
    def _extract_headings(self, content: str) -> list:
        """从内容中提取可能的标题"""
        lines = content.split('\n')
        headings = []
        
        for line in lines:
            line = line.strip()
            # 简单的标题识别规则
            if (line and len(line) < 100 and  # 不太长
                any(char.isdigit() for char in line) and  # 包含数字
                (line.endswith('。') or line.endswith('.') or  # 以句号结尾
                 any(word in line for word in ['章', '节', '部分', '摘要', '结论', 'Chapter', 'Section']))):  # 包含关键词
                headings.append({
                    "level": 1,  # 简单设为1级标题
                    "title": line[:50]  # 限制标题长度
                })
                
        return headings[:10]  # 限制标题数量


def test_mineru_parser():
    """测试PDF解析器"""
    parser = MinerUParser()
    
    print("PDF解析器测试:")
    print("✅ 使用PyPDF2作为PDF解析引擎")
    print("📋 功能: 提取文本内容、基础结构分析")
    print("⚠️  限制: 无法提取图片、表格结构，但稳定可靠")


if __name__ == "__main__":
    test_mineru_parser()