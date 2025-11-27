#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: step_executor.py
# @description: 步骤执行器模块，负责执行解析后的步骤列表

"""
步骤执行器模块
负责按顺序执行解析后的步骤列表，处理异常和特殊等待逻辑
"""

import time
from typing import List, Tuple, Callable, Dict, Any, Optional
from utils.logger import logger
from utils.exception_handler import (
    ExceptionHandler, ElementNotFound, BranchExecutionError, 
    ProcessExecutionError, ToolCrash
)
from utils.util import log_module_completion
from config import Timing, StepDescriptions, ConfigStructure


class StepExecutor:
    """步骤执行器类"""
    
    @ExceptionHandler.handle_general_exception
    def execute_steps(self, steps: List[Tuple[str, Callable]],
                     config: Optional[Dict[str, Any]] = None,
                     module_name: Optional[str] = None,
                     cli_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        执行步骤列表
        
        Args:
            steps: 步骤列表，每个元素为(描述, 执行函数)元组
            config: 配置对象
            module_name: 模块名称
            cli_params: 命令行参数
            
        Returns:
            执行结果
        """
        # 获取全局pause时间
        pause_time = self._get_pause_time(config)
        
        for desc, func in steps:
            logger.debug(f"步骤开始: {desc}")
            
            try:
                result = func()
                
                if result is False:
                    raise ToolCrash(component="步骤执行器", message=f"步骤失败: {desc}")
            except ElementNotFound as e:
                self._handle_element_not_found(e, desc, config, module_name)
            except BranchExecutionError as e:
                self._handle_branch_execution_error(e, desc)
            except ProcessExecutionError as e:
                self._handle_process_execution_error(e, desc)
            except Exception as e:
                self._handle_unexpected_error(e, desc)
            
            # 处理特定步骤的等待时间
            self._handle_step_wait_time(desc, pause_time)
        
        # 功能执行完毕，打印完成日志
        log_module_completion(module_name, cli_params)
        
        return True
    
    def _get_pause_time(self, config: Optional[Dict[str, Any]]) -> int:
        """获取全局pause时间"""
        pause_time = Timing.DEFAULT_PAUSE
        
        if config:
            try:
                if ConfigStructure.LAUNCH_KEY in config:
                    pause_time = config[ConfigStructure.LAUNCH_KEY].get(
                        ConfigStructure.PAUSE_KEY, Timing.DEFAULT_PAUSE
                    )
                    try:
                        pause_time = int(pause_time)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"pause参数类型错误，使用默认值{Timing.DEFAULT_PAUSE}秒: {e}")
                        pause_time = Timing.DEFAULT_PAUSE
            except Exception as e:
                logger.warning(f"读取配置文件pause参数失败，使用默认值{Timing.DEFAULT_PAUSE}秒: {e}")
        
        return pause_time
    
    def _handle_element_not_found(self, e: ElementNotFound, desc: str, 
                                 config: Dict[str, Any], module_name: str) -> None:
        """处理元素定位失败异常"""
        logger.error(f"步骤中元素定位失败: {desc}, 错误: {str(e)}")
        
        # 检查是否是recognize_action抛出的异常
        if "recognize_action" in str(e):
            logger.debug("检测到recognize_action异常，开始执行当前模块的res_process步骤")
            self._execute_module_res_process(config, module_name)
            raise ToolCrash(
                component="步骤执行器", 
                message=f"识别到错误弹窗，执行res_process后退出: {str(e)}"
            ) from e
        else:
            raise BranchExecutionError(
                branch_name=desc, 
                message=f"步骤中元素定位失败: {str(e)}"
            ) from e
    
    def _handle_branch_execution_error(self, e: BranchExecutionError, desc: str) -> None:
        """处理分支执行错误"""
        logger.error(f"步骤中分支执行失败: {desc}, 错误: {str(e)}")
        raise ProcessExecutionError(
            process_name="步骤执行器", 
            message=f"步骤中分支执行失败: {str(e)}"
        ) from e
    
    def _handle_process_execution_error(self, e: ProcessExecutionError, desc: str) -> None:
        """处理进程执行错误"""
        logger.error(f"步骤中进程执行失败: {desc}, 错误: {str(e)}")
        raise ToolCrash(
            component="步骤执行器", 
            message=f"步骤中进程执行失败: {str(e)}"
        ) from e
    
    def _handle_unexpected_error(self, e: Exception, desc: str) -> None:
        """处理意外错误"""
        logger.error(f"步骤执行异常: {desc}, 错误: {str(e)}")
        raise ToolCrash(
            component="步骤执行器", 
            message=f"步骤执行异常: {desc}, 错误: {str(e)}"
        ) from e
    
    def _execute_module_res_process(self, config: Dict[str, Any], module_name: str) -> None:
        """执行当前模块的res_process步骤"""
        if not module_name:
            logger.warning("未找到当前模块名，跳过res_process执行")
            return
        
        from core.step_parser import StepParser
        parser = StepParser()
        
        for model in config.get(ConfigStructure.MODEL_KEY, []):
            if model[ConfigStructure.NAME_KEY] == module_name:
                res_process_steps = parser.parse_process_list(
                    model.get(ConfigStructure.RES_PROCESS_KEY, []), 
                    {}, 
                    config
                )
                if res_process_steps:
                    logger.debug(f"开始执行当前模块 {module_name} 的res_process步骤")
                    self.execute_steps(res_process_steps, config, None, None)
                break
    
    def _handle_step_wait_time(self, desc: str, pause_time: int) -> None:
        """处理步骤等待时间"""
        # 特定步骤执行后添加等待初始化时间
        if StepDescriptions.CONTROL_INTERFACE in desc:
            time.sleep(Timing.CONTROL_INTERFACE_WAIT)
        elif StepDescriptions.SCAN_BUTTON in desc:
            time.sleep(Timing.SCAN_BUTTON_WAIT)
        elif StepDescriptions.REMOTE_HOST_CONNECT in desc:
            time.sleep(Timing.REMOTE_HOST_CONNECT_WAIT)
        elif StepDescriptions.INPUT_MEMORY in desc:
            time.sleep(Timing.INPUT_MEMORY_WAIT)
        elif StepDescriptions.DOWN_SAMPLE in desc:
            time.sleep(Timing.DOWN_SAMPLE_WAIT)
        elif StepDescriptions.INSTALL_CLICK in desc:
            time.sleep(Timing.INSTALL_CLICK_WAIT)
        elif pause_time > 0:
            # 普通操作使用launch-pause间隔时间
            time.sleep(pause_time)
    

