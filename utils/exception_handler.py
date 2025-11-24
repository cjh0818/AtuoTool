#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: exception_handler.py
# @description: 异常处理模块，提供分层异常捕获和处理功能

import traceback
from functools import wraps
from utils.logger import logger


class ElementNotFound(Exception):
    """元素定位失败异常"""
    def __init__(self, element_name=None, message="元素定位失败"):
        self.element_name = element_name
        if element_name:
            message = f"元素定位失败: {element_name}"
        super().__init__(message)
        logger.error(f"元素定位失败异常: {message}")


class BranchExecutionError(Exception):
    """分支步骤执行异常"""
    def __init__(self, branch_name=None, message="分支步骤执行失败"):
        self.branch_name = branch_name
        if branch_name:
            message = f"分支步骤执行失败: {branch_name}"
        super().__init__(message)
        logger.error(f"分支步骤执行异常: {message}")


class ProcessExecutionError(Exception):
    """进程执行异常"""
    def __init__(self, process_name=None, message="进程执行失败"):
        self.process_name = process_name
        if process_name:
            message = f"进程执行失败: {process_name}"
        super().__init__(message)
        logger.error(f"进程执行异常: {message}")


class ToolCrash(Exception):
    """程序自身异常"""
    def __init__(self, component=None, message="程序自身异常"):
        self.component = component
        if component:
            message = f"程序自身异常: {component}"
        super().__init__(message)
        logger.error(f"程序自身异常: {message}")


class ResultParseError(Exception):
    """结果解析异常"""
    def __init__(self, result_type=None, message="结果解析失败"):
        self.result_type = result_type
        if result_type:
            message = f"结果解析失败: {result_type}"
        super().__init__(message)
        logger.error(f"结果解析异常: {message}")


class AutoToolException(Exception):
    """自动化工具基础异常类"""
    def __init__(self, message="自动化工具异常"):
        super().__init__(message)
        logger.error(f"自动化工具异常: {message}")


class ExceptionHandler:
    """异常处理器，提供分层异常捕获和处理功能"""
    
    @staticmethod
    def handle_element_not_found(func):
        """元素定位失败异常装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ElementNotFound as e:
                logger.error(f"元素定位失败: {e}")
                raise  # 重新抛出异常，让上层处理
            except Exception as e:
                # 将其他异常转换为元素定位失败异常
                error_msg = f"函数 {func.__name__} 执行失败，可能是元素定位问题: {str(e)}"
                logger.error(error_msg)
                raise ElementNotFound(message=error_msg) from e
        return wrapper
    
    @staticmethod
    def handle_branch_execution(func):
        """分支步骤执行异常装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BranchExecutionError as e:
                logger.error(f"分支步骤执行失败: {e}")
                raise
            except ElementNotFound as e:
                # 元素定位失败异常转换为分支执行异常
                error_msg = f"分支执行过程中元素定位失败: {str(e)}"
                logger.error(error_msg)
                raise BranchExecutionError(message=error_msg) from e
            except Exception as e:
                # 其他异常转换为分支执行异常
                error_msg = f"分支执行过程发生异常: {str(e)}"
                logger.error(error_msg)
                raise BranchExecutionError(message=error_msg) from e
        return wrapper
    
    @staticmethod
    def handle_process_execution(func):
        """进程执行异常装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ProcessExecutionError as e:
                logger.error(f"进程执行失败: {e}")
                raise
            except BranchExecutionError as e:
                # 分支执行异常转换为进程执行异常
                error_msg = f"进程执行过程中分支执行失败: {str(e)}"
                logger.error(error_msg)
                raise ProcessExecutionError(message=error_msg) from e
            except Exception as e:
                # 其他异常转换为进程执行异常
                error_msg = f"进程执行过程发生异常: {str(e)}"
                logger.error(error_msg)
                raise ProcessExecutionError(message=error_msg) from e
        return wrapper
    
    @staticmethod
    def handle_tool_crash(func):
        """程序自身异常装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ToolCrash as e:
                logger.error(f"程序自身异常: {e}")
                raise
            except ProcessExecutionError as e:
                # 进程执行异常转换为工具崩溃异常
                error_msg = f"工具组件崩溃: {str(e)}"
                logger.error(error_msg)
                raise ToolCrash(message=error_msg) from e
            except Exception as e:
                # 其他异常转换为工具崩溃异常
                error_msg = f"工具组件发生严重异常: {str(e)}"
                logger.error(error_msg)
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                raise ToolCrash(message=error_msg) from e
        return wrapper
    
    @staticmethod
    def handle_general_exception(func):
        """通用异常兜底装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ToolCrash as e:
                # 工具崩溃异常已经是最高层异常，不需要再转换，直接记录并返回
                logger.error(f"工具崩溃异常: {e}")
                return None
            except Exception as e:
                # 所有未捕获的异常都会被这里捕获
                error_msg = f"未处理的异常: {str(e)}"
                logger.error(error_msg)
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                return None
        return wrapper
    
    @staticmethod
    def safe_execute(func, default_return=None, log_errors=True):
        """安全执行函数，捕获所有异常并返回默认值"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
                return default_return
        return wrapper
    
    @staticmethod
    def handle_element_not_found_with_context(func_name="操作"):
        """带上下文的元素定位失败异常处理"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except ElementNotFound as e:
                    logger.error(f"在 {func_name} 中元素定位失败: {e}")
                    raise
                except Exception as e:
                    error_msg = f"{func_name} 过程中发生元素定位失败: {str(e)}"
                    logger.error(error_msg)
                    raise ElementNotFound(message=error_msg) from e
            return wrapper
        return decorator
    
    @staticmethod
    def handle_result_parse_with_context(result_type="结果解析"):
        """带上下文的结果解析异常处理"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except ResultParseError as e:
                    logger.error(f"在 {result_type} 中结果解析失败: {e}")
                    raise
                except Exception as e:
                    error_msg = f"{result_type} 过程中发生结果解析失败: {str(e)}"
                    logger.error(error_msg)
                    raise ResultParseError(message=error_msg) from e
            return wrapper
        return decorator
    
    @staticmethod
    def handle_branch_execution_with_context(branch_name="分支"):
        """带上下文的分支步骤执行异常处理"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except BranchExecutionError as e:
                    logger.error(f"在 {branch_name} 中分支执行失败: {e}")
                    raise
                except ElementNotFound as e:
                    error_msg = f"{branch_name} 执行过程中元素定位失败: {str(e)}"
                    logger.error(error_msg)
                    raise BranchExecutionError(message=error_msg) from e
                except Exception as e:
                    error_msg = f"{branch_name} 执行过程发生异常: {str(e)}"
                    logger.error(error_msg)
                    raise BranchExecutionError(message=error_msg) from e
            return wrapper
        return decorator