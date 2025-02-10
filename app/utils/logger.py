import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_LEVEL_DEFAULT = 'INFO'
LOG_DIR_DEFAULT = 'logs'
LOG_FILE_SIZE_DEFAULT = '50M'
LOG_BACKUP_COUNT_DEFAULT = 5

# 缓冲区，用于存储在logger实例创建前需要记录的日志消息
_log_buffer_for_setup_logger = []

def parse_log_file_size(size_str: str) -> int:
    """
    解析日志文件大小的字符串，返回字节数。

    Args:
        size_str: 例如 '50M' 或 '1G'

    Returns:
        int: 对应的字节数
    """
    size_str = size_str.strip().upper()
    try:
        if size_str.endswith('K') or size_str.endswith('KB') or size_str.endswith('KIB'):
            return int(size_str.strip('K')[0]) * 1024  # 转换为字节
        elif size_str.endswith('M') or size_str.endswith('MB') or size_str.endswith('MIB'):
            return int(size_str.strip('M')[0]) * 1024 * 1024  # 转换为字节
        elif size_str.endswith('G') or size_str.endswith('GB') or size_str.endswith('GIB'):
            return int(size_str.strip('G')[0]) * 1024 * 1024 * 1024  # 转换为字节
        else:
            return int(size_str)  # 默认返回字节数
    except Exception as e:
        if size_str == LOG_FILE_SIZE_DEFAULT:
            raise RuntimeError(f"致命错误 FATAL ERROR, 日志默认大小{LOG_FILE_SIZE_DEFAULT}解析失败。错误信息: {e}")
        _log_buffer_for_setup_logger.append({
            'level': 'warning',
            'message': f"解析日志文件大小失败: {size_str}。使用默认大小{LOG_FILE_SIZE_DEFAULT}。错误信息: {e}"
        })
        return parse_log_file_size(LOG_FILE_SIZE_DEFAULT)  # 默认返回50MB

def setup_logger(name='wx-backend'):
    """
    配置logger

    Args:
        name: logger名称

    Returns:
        logging.Logger: 配置好的logger实例
    """
    # 创建logger
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    log_level = getattr(logging, os.getenv('LOG_LEVEL', LOG_LEVEL_DEFAULT).upper(), logging.INFO)
    logger.setLevel(log_level)  # 设置日志等级
    _log_buffer_for_setup_logger.append({
        'level': 'info',
        'message': f"LOG_LEVEL: {logging.getLevelName(log_level)}"
    })

    # 创建logs目录（如果不存在）
    log_dir = os.getenv('LOG_DIR', LOG_DIR_DEFAULT)  # 从环境变量读取LOGs目录路径，如果不存在则设置为logs

    # 检查LOG_DIR的合法性
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            _log_buffer_for_setup_logger.append({
                'level': 'info',
                'message': f"创建日志目录: {log_dir}"
            })
        except Exception as e:
            _log_buffer_for_setup_logger.append({
                'level': 'warning',
                'message': f"无法创建日志目录: {log_dir}。使用默认日志目录{LOG_DIR_DEFAULT}。错误信息: {e}"
            })
            log_dir = LOG_DIR_DEFAULT  # 使用默认日志目录
    _log_buffer_for_setup_logger.append({
        'level': 'info',
        'message': f"LOG_DIR: {log_dir}"
    })

    # 解析日志文件大小
    max_bytes = parse_log_file_size(os.getenv('LOG_FILE_SIZE', LOG_FILE_SIZE_DEFAULT))  # 默认50MB
    _log_buffer_for_setup_logger.append({
        'level': 'info',
        'message': f"LOG_FILE_SIZE: {max_bytes} bytes"
    })

    # 检查LOG_BACKUP_COUNT的合法性
    try:
        backup_count = int(os.getenv('LOG_BACKUP_COUNT', LOG_BACKUP_COUNT_DEFAULT))
        if backup_count < 0:
            raise ValueError("备份数量不能为负数")
        _log_buffer_for_setup_logger.append({
            'level': 'info',
            'message': f"LOG_BACKUP_COUNT: {backup_count}"
        })
    except ValueError as e:
        _log_buffer_for_setup_logger.append({
            'level': 'warning',
            'message': f"LOG_BACKUP_COUNT无效，使用默认值{LOG_BACKUP_COUNT_DEFAULT}。错误信息: {e}"
        })
        backup_count = LOG_BACKUP_COUNT_DEFAULT  # 使用默认备份数量

    # 配置文件处理器
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f'ars_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        maxBytes=max_bytes,  # 使用解析后的最大字节数
        backupCount=backup_count,  # 从环境变量读取备份文件数量，默认为5
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)

    # 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建默认logger实例
logger = setup_logger()

# 在logger实例创建后，处理缓冲区中的日志消息
for log_message in _log_buffer_for_setup_logger:
    getattr(logger, log_message['level'])(log_message['message'])

# 清空缓冲区
_log_buffer_for_setup_logger.clear()
