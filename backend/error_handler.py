"""
错误处理和重试机制模块
提供统一的错误处理、重试逻辑和异常管理
"""

import time
import functools
import logging
from typing import Callable, Any, Optional, Type
import traceback
from enum import Enum

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    FILE_ERROR = "file_error"
    PARSING_ERROR = "parsing_error"
    DATABASE_ERROR = "database_error"
    UNKNOWN_ERROR = "unknown_error"

class RetryableError(Exception):
    """可重试的错误"""
    def __init__(self, message: str, error_type: ErrorType, original_error: Exception = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(message)

class NonRetryableError(Exception):
    """不可重试的错误"""
    def __init__(self, message: str, error_type: ErrorType, original_error: Exception = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(message)

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (RetryableError, ConnectionError, TimeoutError)
):
    """
    带指数退避的重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
        retryable_exceptions: 可重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"函数 {func.__name__} 在 {max_retries} 次重试后仍然失败: {str(e)}")
                        raise
                    
                    # 计算延迟时间
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}, {delay:.1f}秒后重试")
                    time.sleep(delay)
                    
                except NonRetryableError as e:
                    logger.error(f"函数 {func.__name__} 发生不可重试错误: {str(e)}")
                    raise
                    
                except Exception as e:
                    # 未知错误，默认不重试
                    logger.error(f"函数 {func.__name__} 发生未知错误: {str(e)}")
                    raise NonRetryableError(f"未知错误: {str(e)}", ErrorType.UNKNOWN_ERROR, e)
            
            # 如果到这里，说明重试次数用完了
            raise last_exception
            
        return wrapper
    return decorator

class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_file_error(e: Exception, file_path: str) -> NonRetryableError:
        """处理文件相关错误"""
        if isinstance(e, FileNotFoundError):
            return NonRetryableError(f"文件不存在: {file_path}", ErrorType.FILE_ERROR, e)
        elif isinstance(e, PermissionError):
            return NonRetryableError(f"文件权限错误: {file_path}", ErrorType.FILE_ERROR, e)
        elif isinstance(e, IOError):
            return RetryableError(f"文件IO错误: {file_path}", ErrorType.FILE_ERROR, e)
        else:
            return NonRetryableError(f"文件处理错误: {str(e)}", ErrorType.FILE_ERROR, e)
    
    @staticmethod
    def handle_api_error(e: Exception, api_name: str) -> Exception:
        """处理API相关错误"""
        error_msg = str(e).lower()
        
        # OpenAI API 错误处理
        if "rate limit" in error_msg or "quota" in error_msg:
            return RetryableError(f"{api_name} API限额错误: {str(e)}", ErrorType.API_ERROR, e)
        elif "timeout" in error_msg:
            return RetryableError(f"{api_name} API超时: {str(e)}", ErrorType.API_ERROR, e)
        elif "connection" in error_msg or "network" in error_msg:
            return RetryableError(f"{api_name} 网络连接错误: {str(e)}", ErrorType.NETWORK_ERROR, e)
        elif "unauthorized" in error_msg or "authentication" in error_msg:
            return NonRetryableError(f"{api_name} 认证失败: {str(e)}", ErrorType.API_ERROR, e)
        elif "bad request" in error_msg or "invalid" in error_msg:
            return NonRetryableError(f"{api_name} 请求参数错误: {str(e)}", ErrorType.API_ERROR, e)
        else:
            return RetryableError(f"{api_name} API错误: {str(e)}", ErrorType.API_ERROR, e)
    
    @staticmethod
    def handle_database_error(e: Exception, operation: str) -> Exception:
        """处理数据库相关错误"""
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "timeout" in error_msg:
            return RetryableError(f"数据库连接错误 ({operation}): {str(e)}", ErrorType.DATABASE_ERROR, e)
        elif "lock" in error_msg or "busy" in error_msg:
            return RetryableError(f"数据库忙碌 ({operation}): {str(e)}", ErrorType.DATABASE_ERROR, e)
        elif "disk" in error_msg or "space" in error_msg:
            return NonRetryableError(f"数据库存储空间不足 ({operation}): {str(e)}", ErrorType.DATABASE_ERROR, e)
        else:
            return RetryableError(f"数据库操作错误 ({operation}): {str(e)}", ErrorType.DATABASE_ERROR, e)
    
    @staticmethod
    def handle_parsing_error(e: Exception, file_name: str) -> Exception:
        """处理文档解析相关错误"""
        error_msg = str(e).lower()
        
        if "corrupted" in error_msg or "damaged" in error_msg:
            return NonRetryableError(f"文档损坏 ({file_name}): {str(e)}", ErrorType.PARSING_ERROR, e)
        elif "unsupported" in error_msg or "format" in error_msg:
            return NonRetryableError(f"不支持的文档格式 ({file_name}): {str(e)}", ErrorType.PARSING_ERROR, e)
        elif "memory" in error_msg or "resource" in error_msg:
            return RetryableError(f"解析资源不足 ({file_name}): {str(e)}", ErrorType.PARSING_ERROR, e)
        else:
            return RetryableError(f"文档解析错误 ({file_name}): {str(e)}", ErrorType.PARSING_ERROR, e)

def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[Exception]]:
    """
    安全执行函数，捕获所有异常
    
    Returns:
        (success, result, error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        logger.error(f"执行 {func.__name__} 时发生错误: {str(e)}")
        logger.debug(traceback.format_exc())
        return False, None, e

class TaskErrorTracker:
    """任务错误跟踪器"""
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
    
    def record_error(self, task_id: str, error: Exception):
        """记录错误"""
        if task_id not in self.error_counts:
            self.error_counts[task_id] = 0
        
        self.error_counts[task_id] += 1
        
        error_record = {
            "task_id": task_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time()
        }
        
        self.error_history.append(error_record)
        
        # 保持历史记录在合理范围内
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
    
    def get_error_count(self, task_id: str) -> int:
        """获取任务错误次数"""
        return self.error_counts.get(task_id, 0)
    
    def should_skip_task(self, task_id: str, max_errors: int = 5) -> bool:
        """判断是否应该跳过任务"""
        return self.get_error_count(task_id) >= max_errors
    
    def get_error_summary(self) -> dict:
        """获取错误摘要"""
        total_errors = len(self.error_history)
        error_types = {}
        
        for record in self.error_history[-100:]:  # 最近100个错误
            error_type = record["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": total_errors,
            "error_types": error_types,
            "tasks_with_errors": len(self.error_counts)
        }

# 全局错误跟踪器实例
error_tracker = TaskErrorTracker()

def log_and_handle_error(task_id: str, error: Exception, context: str = "") -> Exception:
    """
    记录并处理错误
    
    Args:
        task_id: 任务ID
        error: 原始错误
        context: 错误上下文
        
    Returns:
        处理后的错误
    """
    # 记录错误
    error_tracker.record_error(task_id, error)
    
    # 记录日志
    logger.error(f"任务 {task_id} 在 {context} 阶段发生错误: {str(error)}")
    
    # 根据错误类型返回适当的异常
    if "openai" in str(error).lower() or "api" in str(error).lower():
        return ErrorHandler.handle_api_error(error, "OpenAI")
    elif "file" in str(error).lower() or "path" in str(error).lower():
        return ErrorHandler.handle_file_error(error, context)
    elif "database" in str(error).lower() or "chroma" in str(error).lower():
        return ErrorHandler.handle_database_error(error, context)
    elif "parse" in str(error).lower() or "mineru" in str(error).lower():
        return ErrorHandler.handle_parsing_error(error, context)
    else:
        return RetryableError(f"未分类错误: {str(error)}", ErrorType.UNKNOWN_ERROR, error)

if __name__ == "__main__":
    # 测试重试机制
    @retry_with_backoff(max_retries=2, base_delay=0.1)
    def test_function():
        import random
        if random.random() < 0.7:
            raise RetryableError("模拟可重试错误", ErrorType.API_ERROR)
        return "成功"
    
    try:
        result = test_function()
        print(f"测试结果: {result}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
    
    # 测试错误跟踪
    print("错误跟踪测试:")
    error_tracker.record_error("test_task", Exception("测试错误"))
    print(error_tracker.get_error_summary())