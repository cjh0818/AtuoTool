#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: logger.py
# @description: 日志系统模块，提供统一的日志记录功能

import logging
import os
import sys

class MatchProcessFilter(logging.Filter):
    """
    自定义过滤器，用于过滤掉匹配过程的详细日志信息
    """
    def filter(self, record):
        # 如果日志消息包含"方法:"和"+"，则认为是匹配过程的详细信息，不显示在控制台
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if "方法:" in record.msg and "+" in record.msg:
                return False
            
            # 过滤特定的图像匹配日志信息
            filter_keywords = [
                "开始多种图像处理方法和匹配算法的组合测试",
                "二次验证通过，验证分数:",
                "最佳加权匹配度:",
                "原始匹配度:",
                "匹配位置:",
                "高置信度匹配数量:",
                "已记录上一次点击位置:",
                "执行前截图已保存:",
                "执行后截图已保存:",
                "使用默认下拉选项",
                "用户指定下拉选项",
                "处理下拉选项",
                "开始解析步骤列表，可用变量映射:",
                "已点击",
                "使用配置文件中的pause时间",
                "匹配到候选进程",
                "跳过常见进程窗口",
                "跳过包含常见误判模式的窗口",
                "异常堆栈"
            ]
            
            for keyword in filter_keywords:
                if keyword in record.msg:
                    return False
        
        return True

def setup_logger(name="autotool", log_file=None, level=logging.INFO):
    """
    设置日志系统
    
    :param name: 日志器名称
    :param log_file: 日志文件路径，如果为None则使用默认路径
    :param level: 日志级别
    :return: 配置好的日志器
    """
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 获取程序所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包的可执行文件
        program_dir = os.path.dirname(sys.executable)
    else:
        # 如果是Python脚本
        program_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 创建logs目录（如果不存在）
    logs_dir = os.path.join(program_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 设置日志文件路径
    if log_file is None:
        log_file = os.path.join(logs_dir, "autotool.log")
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别的日志
    
    # 创建自定义过滤器并添加到控制台处理器
    match_process_filter = MatchProcessFilter()
    console_handler.addFilter(match_process_filter)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置格式化器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 记录日志系统启动信息
    logger.debug(f"日志系统已初始化，日志文件: {log_file}")
    
    return logger

def set_log_level(level):
    """
    设置日志级别
    
    :param level: 日志级别字符串 ("debug" 或 "info")
    """
    
    if level.lower() == "debug":
        log_level = logging.DEBUG
    elif level.lower() == "info":
        log_level = logging.INFO
    else:
        logger.warning(f"未知的日志级别: {level}，使用默认的 INFO 级别")
        log_level = logging.INFO
    
    # 设置日志器的级别
    logger.setLevel(log_level)
    
    # 更新所有处理器的级别
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(log_level)
        elif isinstance(handler, logging.StreamHandler):
            handler.setLevel(log_level)
    
    logger.debug(f"日志级别已设置为: {level.upper()}")

# 创建默认日志器
logger = setup_logger()