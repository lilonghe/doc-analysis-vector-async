#!/usr/bin/env python3
"""
数据库维护和管理脚本
用于数据库迁移、清理和统计
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_database_manager, DatabaseManager

def init_database():
    """初始化数据库"""
    try:
        db_manager = DatabaseManager()
        print("✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        return False

def show_statistics():
    """显示数据库统计信息"""
    try:
        db_manager = get_database_manager()
        stats = db_manager.get_processing_statistics()
        
        print("\n📊 数据库统计信息:")
        print(f"总文件数: {stats['total_files']}")
        print(f"已完成: {stats['completed_files']}")
        print(f"处理中: {stats['processing_files']}")
        print(f"等待处理: {stats['pending_files']}")
        print(f"失败: {stats['error_files']}")
        print(f"总文档块: {stats['total_chunks']}")
        print(f"成功率: {stats['success_rate']}%")
        
        # 显示错误文件
        error_files = db_manager.get_error_files()
        if error_files:
            print(f"\n❌ 错误文件 ({len(error_files)} 个):")
            for file_record in error_files[:5]:  # 只显示前5个
                print(f"  - {file_record.filename}: {file_record.last_error}")
            if len(error_files) > 5:
                print(f"  ... 还有 {len(error_files) - 5} 个错误文件")
        
        return True
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")
        return False

def cleanup_old_data(days=7):
    """清理旧数据"""
    try:
        db_manager = get_database_manager()
        result = db_manager.cleanup_old_records(days=days)
        
        print(f"🧹 清理完成:")
        print(f"删除文件记录: {result['deleted_files']} 个")
        print(f"删除处理日志: {result['deleted_logs']} 个")
        return True
    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
        return False

def export_data(output_file):
    """导出数据"""
    try:
        import json
        db_manager = get_database_manager()
        
        # 获取所有文件记录
        all_files = db_manager.get_all_file_records()
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "total_files": len(all_files),
            "files": []
        }
        
        for file_record in all_files:
            file_data = {
                "id": file_record.id,
                "filename": file_record.filename,
                "status": file_record.status,
                "progress": file_record.progress,
                "total_pages": file_record.total_pages,
                "chunks_count": file_record.chunks_count,
                "error_count": file_record.error_count,
                "created_at": file_record.created_at.isoformat(),
                "updated_at": file_record.updated_at.isoformat()
            }
            
            # 获取处理日志
            logs = db_manager.get_processing_logs(file_record.id)
            file_data["logs"] = [
                {
                    "stage": log.stage,
                    "status": log.status,
                    "message": log.message,
                    "duration": log.duration,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
            
            export_data["files"].append(file_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 数据导出成功: {output_file}")
        print(f"导出文件数: {len(all_files)}")
        return True
    except Exception as e:
        print(f"❌ 数据导出失败: {str(e)}")
        return False

def reset_database():
    """重置数据库（危险操作）"""
    try:
        confirm = input("⚠️  这将删除所有数据，确认继续？(输入 'YES' 确认): ")
        if confirm != "YES":
            print("操作已取消")
            return False
        
        # 删除数据库文件
        db_file = "doc_vector.db"
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"🗑️  删除数据库文件: {db_file}")
        
        # 重新初始化
        init_database()
        print("✅ 数据库重置完成")
        return True
    except Exception as e:
        print(f"❌ 数据库重置失败: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="数据库维护和管理工具")
    parser.add_argument("command", choices=[
        "init", "stats", "cleanup", "export", "reset"
    ], help="要执行的命令")
    
    parser.add_argument("--days", type=int, default=7, 
                       help="清理多少天前的数据 (默认: 7)")
    parser.add_argument("--output", type=str, default="export.json",
                       help="导出文件名 (默认: export.json)")
    
    args = parser.parse_args()
    
    print(f"🚀 执行命令: {args.command}")
    
    if args.command == "init":
        success = init_database()
    elif args.command == "stats":
        success = show_statistics()
    elif args.command == "cleanup":
        success = cleanup_old_data(args.days)
    elif args.command == "export":
        success = export_data(args.output)
    elif args.command == "reset":
        success = reset_database()
    else:
        print(f"未知命令: {args.command}")
        success = False
    
    if success:
        print("✅ 操作完成")
        sys.exit(0)
    else:
        print("❌ 操作失败")
        sys.exit(1)

if __name__ == "__main__":
    main()