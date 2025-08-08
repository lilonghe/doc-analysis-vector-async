"""
数据库模型和状态管理
使用SQLAlchemy + SQLite进行状态持久化存储
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./doc_vector.db')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class FileRecord(Base):
    """文件记录表"""
    __tablename__ = "files"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, parsing, chunking, embedding, storing, completed, error
    progress = Column(Integer, default=0)
    message = Column(String, default="等待处理中...")
    
    # 处理结果
    total_pages = Column(Integer, default=0)
    chunks_count = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 错误信息
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

class ProcessingLog(Base):
    """处理日志表"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, nullable=False)
    stage = Column(String, nullable=False)  # parsing, chunking, embedding, storing
    status = Column(String, nullable=False)  # started, completed, failed
    message = Column(Text, nullable=True)
    duration = Column(Float, nullable=True)  # 耗时（秒）
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_db(self) -> Session:
        """获取数据库会话"""
        db = self.SessionLocal()
        try:
            return db
        finally:
            pass  # 不在这里关闭，由调用方负责
    
    def create_file_record(self, file_id: str, filename: str, filepath: str) -> FileRecord:
        """创建文件记录"""
        db = self.get_db()
        try:
            file_record = FileRecord(
                id=file_id,
                filename=filename,
                filepath=filepath,
                status="pending",
                progress=0,
                message="等待处理中..."
            )
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            return file_record
        finally:
            db.close()
    
    def update_file_status(self, file_id: str, status: str, progress: int, message: str):
        """更新文件状态"""
        db = self.get_db()
        try:
            file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
            if file_record:
                file_record.status = status
                file_record.progress = progress
                file_record.message = message
                file_record.updated_at = datetime.utcnow()
                
                # 如果是错误状态，增加错误计数
                if status == "error":
                    file_record.error_count += 1
                    file_record.last_error = message
                
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def get_file_record(self, file_id: str) -> Optional[FileRecord]:
        """获取文件记录"""
        db = self.get_db()
        try:
            return db.query(FileRecord).filter(FileRecord.id == file_id).first()
        finally:
            db.close()
    
    def get_all_file_records(self) -> List[FileRecord]:
        """获取所有文件记录"""
        db = self.get_db()
        try:
            return db.query(FileRecord).order_by(FileRecord.created_at.desc()).all()
        finally:
            db.close()
    
    def delete_file_record(self, file_id: str) -> bool:
        """删除文件记录"""
        db = self.get_db()
        try:
            file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
            if file_record:
                # 同时删除相关日志
                db.query(ProcessingLog).filter(ProcessingLog.file_id == file_id).delete()
                db.delete(file_record)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def update_file_results(self, file_id: str, total_pages: int = 0, chunks_count: int = 0):
        """更新文件处理结果"""
        db = self.get_db()
        try:
            file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
            if file_record:
                if total_pages > 0:
                    file_record.total_pages = total_pages
                if chunks_count > 0:
                    file_record.chunks_count = chunks_count
                file_record.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def log_processing_stage(self, file_id: str, stage: str, status: str, message: str = None, duration: float = None):
        """记录处理阶段日志"""
        db = self.get_db()
        try:
            log = ProcessingLog(
                file_id=file_id,
                stage=stage,
                status=status,
                message=message,
                duration=duration
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    
    def get_processing_logs(self, file_id: str) -> List[ProcessingLog]:
        """获取文件处理日志"""
        db = self.get_db()
        try:
            return db.query(ProcessingLog).filter(
                ProcessingLog.file_id == file_id
            ).order_by(ProcessingLog.created_at.asc()).all()
        finally:
            db.close()
    
    def get_error_files(self) -> List[FileRecord]:
        """获取错误文件列表"""
        db = self.get_db()
        try:
            return db.query(FileRecord).filter(FileRecord.status == "error").all()
        finally:
            db.close()
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        db = self.get_db()
        try:
            total_files = db.query(FileRecord).count()
            completed_files = db.query(FileRecord).filter(FileRecord.status == "completed").count()
            error_files = db.query(FileRecord).filter(FileRecord.status == "error").count()
            processing_files = db.query(FileRecord).filter(
                FileRecord.status.in_(["parsing", "chunking", "embedding", "storing"])
            ).count()
            pending_files = db.query(FileRecord).filter(FileRecord.status == "pending").count()
            
            total_chunks = db.query(FileRecord).with_entities(
                db.func.sum(FileRecord.chunks_count)
            ).scalar() or 0
            
            return {
                "total_files": total_files,
                "completed_files": completed_files,
                "error_files": error_files,
                "processing_files": processing_files,
                "pending_files": pending_files,
                "total_chunks": int(total_chunks),
                "success_rate": round(completed_files / max(total_files, 1) * 100, 2)
            }
        finally:
            db.close()
    
    def cleanup_old_records(self, days: int = 7):
        """清理旧记录"""
        db = self.get_db()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 删除旧的已完成文件记录
            deleted_files = db.query(FileRecord).filter(
                FileRecord.status == "completed",
                FileRecord.updated_at < cutoff_date
            ).delete()
            
            # 删除旧的处理日志
            deleted_logs = db.query(ProcessingLog).filter(
                ProcessingLog.created_at < cutoff_date
            ).delete()
            
            db.commit()
            return {"deleted_files": deleted_files, "deleted_logs": deleted_logs}
        finally:
            db.close()

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager

def file_record_to_dict(record: FileRecord) -> Dict[str, Any]:
    """将文件记录转换为字典"""
    return {
        "id": record.id,
        "filename": record.filename,
        "filepath": record.filepath,
        "status": record.status,
        "progress": record.progress,
        "message": record.message,
        "total_pages": record.total_pages,
        "chunks_count": record.chunks_count,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "error_count": record.error_count,
        "last_error": record.last_error
    }

if __name__ == "__main__":
    # 测试数据库连接
    try:
        db_manager = DatabaseManager()
        print("✅ 数据库初始化成功")
        
        # 创建测试记录
        test_record = db_manager.create_file_record(
            file_id="test_123",
            filename="test.pdf",
            filepath="/tmp/test.pdf"
        )
        print(f"✅ 创建测试记录: {test_record.id}")
        
        # 更新状态
        db_manager.update_file_status("test_123", "completed", 100, "测试完成")
        print("✅ 状态更新成功")
        
        # 获取统计信息
        stats = db_manager.get_processing_statistics()
        print(f"📊 统计信息: {stats}")
        
        # 清理测试记录
        db_manager.delete_file_record("test_123")
        print("✅ 清理测试记录成功")
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {str(e)}")
        import traceback
        traceback.print_exc()