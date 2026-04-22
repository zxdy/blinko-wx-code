import logging
import sys


def setup_logging(level: int = logging.INFO, log_format: str = None):
    """
    配置日志
    
    Args:
        level: 日志级别,默认INFO
        log_format: 日志格式,默认使用内置格式
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format=log_format
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称,通常使用__name__
        
    Returns:
        logging.Logger实例
    """
    return logging.getLogger(name)
