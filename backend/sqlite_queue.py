"""
数据库任务队列 - 作为 Redis 的替代方案
使用 SQLite 作为消息代理，提供更好的持久化保证
"""

import sqlite3
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from threading import Lock
import os

class SQLiteTaskQueue:
    """基于SQLite的任务队列"""
    
    def __init__(self, db_path: str = "task_queue.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_queue (
                    id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    args TEXT NOT NULL,
                    kwargs TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TIMESTAMP NULL,
                    result TEXT NULL,
                    error_message TEXT NULL
                )
            ''')
            
            # 创建索引优化查询
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON task_queue(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_next_retry ON task_queue(next_retry_at)')
    
    def enqueue(self, task_name: str, *args, **kwargs) -> str:
        """添加任务到队列"""
        task_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO task_queue (id, task_name, args, kwargs)
                VALUES (?, ?, ?, ?)
            ''', (task_id, task_name, json.dumps(args), json.dumps(kwargs)))
        
        print(f"任务入队: {task_name} ({task_id})")
        return task_id
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """从队列中获取下一个任务"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 获取待处理的任务（包括需要重试的任务）
                cursor = conn.execute('''
                    SELECT * FROM task_queue 
                    WHERE status IN ('pending', 'retry') 
                    AND (next_retry_at IS NULL OR next_retry_at <= ?)
                    ORDER BY created_at ASC 
                    LIMIT 1
                ''', (datetime.now(),))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                task = dict(row)
                
                # 标记任务为执行中
                conn.execute('''
                    UPDATE task_queue 
                    SET status = 'processing', started_at = ?
                    WHERE id = ?
                ''', (datetime.now(), task['id']))
                
                return {
                    'id': task['id'],
                    'task_name': task['task_name'],
                    'args': json.loads(task['args']),
                    'kwargs': json.loads(task['kwargs']),
                    'retry_count': task['retry_count']
                }
    
    def complete_task(self, task_id: str, result: Any = None):
        """标记任务完成"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE task_queue 
                SET status = 'completed', completed_at = ?, result = ?
                WHERE id = ?
            ''', (datetime.now(), json.dumps(result) if result else None, task_id))
        
        print(f"任务完成: {task_id}")
    
    def fail_task(self, task_id: str, error_message: str, retry: bool = True):
        """标记任务失败"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 获取当前任务信息
            cursor = conn.execute('''
                SELECT retry_count, max_retries FROM task_queue WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return
            
            retry_count = row['retry_count']
            max_retries = row['max_retries']
            
            if retry and retry_count < max_retries:
                # 安排重试
                next_retry = datetime.now() + timedelta(minutes=2 ** retry_count)  # 指数退避
                conn.execute('''
                    UPDATE task_queue 
                    SET status = 'retry', retry_count = ?, 
                        next_retry_at = ?, error_message = ?
                    WHERE id = ?
                ''', (retry_count + 1, next_retry, error_message, task_id))
                
                print(f"任务安排重试: {task_id} (第 {retry_count + 1} 次)")
            else:
                # 彻底失败
                conn.execute('''
                    UPDATE task_queue 
                    SET status = 'failed', error_message = ?
                    WHERE id = ?
                ''', (error_message, task_id))
                
                print(f"任务彻底失败: {task_id}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM task_queue WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_queue_stats(self) -> Dict[str, int]:
        """获取队列统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM task_queue 
                GROUP BY status
            ''')
            
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return stats
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM task_queue 
                WHERE status IN ('completed', 'failed') 
                AND completed_at < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            print(f"清理了 {deleted_count} 个旧任务")
            return deleted_count


# 简单的任务处理器
class SQLiteTaskWorker:
    """SQLite任务队列的工作进程"""
    
    def __init__(self, queue: SQLiteTaskQueue):
        self.queue = queue
        self.running = False
        self.task_registry = {}
    
    def register_task(self, name: str, func):
        """注册任务函数"""
        self.task_registry[name] = func
    
    def start(self):
        """开始处理任务"""
        self.running = True
        print("SQLite 任务工作进程启动")
        
        while self.running:
            try:
                task = self.queue.dequeue()
                if not task:
                    time.sleep(1)  # 没有任务时等待1秒
                    continue
                
                self.process_task(task)
                
            except KeyboardInterrupt:
                print("接收到停止信号")
                self.running = False
                break
            except Exception as e:
                print(f"工作进程错误: {e}")
                time.sleep(5)  # 出错时等待5秒
    
    def stop(self):
        """停止任务处理"""
        self.running = False
    
    def process_task(self, task: Dict[str, Any]):
        """处理单个任务"""
        task_id = task['id']
        task_name = task['task_name']
        args = task['args']
        kwargs = task['kwargs']
        
        print(f"处理任务: {task_name} ({task_id})")
        
        if task_name not in self.task_registry:
            self.queue.fail_task(task_id, f"未知任务类型: {task_name}", retry=False)
            return
        
        try:
            func = self.task_registry[task_name]
            result = func(*args, **kwargs)
            self.queue.complete_task(task_id, result)
            
        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            print(error_msg)
            self.queue.fail_task(task_id, error_msg)


if __name__ == "__main__":
    # 测试用例
    queue = SQLiteTaskQueue()
    
    # 添加测试任务
    task_id = queue.enqueue("test_task", "arg1", keyword="value1")
    print(f"添加任务: {task_id}")
    
    # 查看队列状态
    stats = queue.get_queue_stats()
    print(f"队列统计: {stats}")