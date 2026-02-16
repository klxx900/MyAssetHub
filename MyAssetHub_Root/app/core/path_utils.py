# app/core/path_utils.py

"""
路径工具模块 - 用于处理 EXE 打包后的路径问题。

确保在开发环境和打包后的 EXE 环境中都能正确找到数据目录。
"""

import os
import sys


def get_base_dir() -> str:
    """
    获取应用程序的基础目录。
    
    在开发环境中，返回 app 目录。
    在打包后的 EXE 环境中，返回 EXE 所在的目录。
    
    Returns:
        基础目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        # sys.executable 指向 EXE 文件路径
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        # 获取当前文件所在目录（app/core/），然后返回 app 目录
        current_file = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(current_file))
    
    return os.path.abspath(base_dir)


def get_data_dir() -> str:
    """
    获取数据目录路径（data/）。
    
    Returns:
        data 目录的绝对路径
    """
    base_dir = get_base_dir()
    data_dir = os.path.join(base_dir, "data")
    return os.path.abspath(data_dir)


def get_cache_dir() -> str:
    """
    获取缓存目录路径（data/.cache/）。
    
    Returns:
        data/.cache 目录的绝对路径
    """
    data_dir = get_data_dir()
    cache_dir = os.path.join(data_dir, ".cache")
    return os.path.abspath(cache_dir)


def get_db_path() -> str:
    """
    获取数据库文件路径（data/library.db）。
    
    Returns:
        data/library.db 的绝对路径
    """
    data_dir = get_data_dir()
    db_path = os.path.join(data_dir, "library.db")
    return os.path.abspath(db_path)


def get_config_path() -> str:
    """
    获取配置文件路径（data/config.json）。
    
    Returns:
        data/config.json 的绝对路径
    """
    data_dir = get_data_dir()
    config_path = os.path.join(data_dir, "config.json")
    return os.path.abspath(config_path)


def ensure_data_dirs() -> None:
    """
    确保数据目录和缓存目录存在，如果不存在则创建。
    
    应该在程序启动时调用此函数。
    """
    data_dir = get_data_dir()
    cache_dir = get_cache_dir()
    
    # 创建 data 目录
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    # 创建 data/.cache 目录
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
