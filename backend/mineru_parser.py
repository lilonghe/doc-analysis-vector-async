"""
MinerU文档解析模块
使用MinerU进行高质量PDF文档解析
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

try:
    from magic_pdf.api import convert_pdf_to_markdown
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False
    print("Warning: MinerU not available, using fallback parser")


class MinerUParser:
    """MinerU文档解析器"""
    
    def __init__(self):
        self.temp_dir = None
        
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
            
        if not MINERU_AVAILABLE:
            return self._fallback_parse(pdf_path)
            
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="mineru_")
            output_dir = os.path.join(self.temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 使用MinerU转换PDF到Markdown
            result = convert_pdf_to_markdown(
                pdf_path=pdf_path,
                output_dir=output_dir,
                ocr_lang="zh-CN",  # 支持中文OCR
                parse_method="auto",  # 自动选择解析方法
                output_format="markdown"
            )
            
            # 解析结果
            parsed_result = self._process_mineru_result(result, output_dir)
            
            return parsed_result
            
        except Exception as e:
            print(f"MinerU解析失败: {str(e)}")
            print(traceback.format_exc())
            # 降级到备用解析方法
            return self._fallback_parse(pdf_path)
            
        finally:
            # 清理临时文件
            self._cleanup()
    
    def _process_mineru_result(self, result: Any, output_dir: str) -> Dict[str, Any]:
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
            
            # 查找JSON输出文件（如果有）
            json_files = list(Path(output_dir).glob("*.json"))
            if json_files:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    # 可以从JSON中提取更详细的结构信息
                    if "tables" in json_data:
                        parsed_data["tables"] = json_data["tables"]
                    if "images" in json_data:
                        parsed_data["images"] = json_data["images"]
                        
        except Exception as e:
            print(f"处理MinerU结果时出错: {str(e)}")
            
        return parsed_data
    
    def _fallback_parse(self, pdf_path: str) -> Dict[str, Any]:
        """备用解析方法，使用PyPDF2"""
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    content += f"\n--- 第{page_num + 1}页 ---\n"
                    content += page_text + "\n"
                
                return {
                    "content": content,
                    "metadata": {
                        "total_pages": len(pdf_reader.pages),
                        "tables_count": 0,
                        "images_count": 0,
                        "formulas_count": 0,
                        "parser": "PyPDF2"
                    },
                    "tables": [],
                    "images": [],
                    "structure": {
                        "headings": [],
                        "paragraphs": content.split('\n'),
                        "lists": []
                    }
                }
                
        except Exception as e:
            print(f"备用解析也失败: {str(e)}")
            return {
                "content": f"解析失败: {str(e)}",
                "metadata": {"total_pages": 0, "parser": "failed"},
                "tables": [],
                "images": [],
                "structure": {"headings": [], "paragraphs": [], "lists": []}
            }
    
    def _cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")


def test_mineru_parser():
    """测试MinerU解析器"""
    parser = MinerUParser()
    
    # 创建一个简单的测试
    print("MinerU解析器测试:")
    print(f"MinerU可用: {MINERU_AVAILABLE}")
    
    if MINERU_AVAILABLE:
        print("✅ MinerU已安装")
    else:
        print("⚠️  MinerU未安装，将使用PyPDF2备用解析")


if __name__ == "__main__":
    test_mineru_parser()