#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: branch_executor.py
# @description: 分支执行器模块，处理成功和失败分支的执行逻辑

"""
分支执行器模块
根据success_res_image的识别结果，决定执行success或error分支
"""

from typing import List, Tuple, Callable, Dict, Any, Optional
from utils.logger import logger
from core.action import recognize_template


class BranchExecutor:
    """分支执行器类"""
    
    @staticmethod
    def make_branch_executor(success_steps: List[Tuple[str, Callable]], 
                           error_steps: List[Tuple[str, Callable]], 
                           success_res_image: str, 
                           config: Dict[str, Any], 
                           module_name: Optional[str] = None) -> Callable:
        """
        创建分支执行器函数
        
        根据success_res_image的识别结果，决定执行success或error分支
        返回值为识别布尔值：True表示识别到success_res，False表示未识别到
        
        Args:
            success_steps: 成功分支步骤列表
            error_steps: 错误分支步骤列表  
            success_res_image: 成功标志图像路径
            config: 配置对象
            module_name: 模块名称
            
        Returns:
            分支执行器函数
        """
        def _executor() -> bool:
            from core.step_executor import StepExecutor
            executor = StepExecutor()
            
            is_success = False
            res_process_executed = False
            
            try:
                is_success = recognize_template(success_res_image)
                if is_success:
                    logger.debug(f"识别到标志: {success_res_image}")
                    executor.execute_steps(success_steps, config, None, None)
                    # 成功分支执行完毕，不需要在finally中执行res_process
                    res_process_executed = True
                else:
                    logger.debug(f"未识别到标志: {success_res_image}")
                    logger.error("当前参数输入不正确，请检查输入参数重新执行")
                    executor.execute_steps(error_steps, config, None, None)
            except Exception as e:
                logger.warning(f"识别标志时发生异常: {str(e)}")
                logger.debug(f"执行error分支步骤")
                try:
                    executor.execute_steps(error_steps, config, None, None)
                    logger.error("当前参数输入不正确，请检查输入参数重新执行")
                except Exception as error_exec_exception:
                    logger.error(f"执行error分支步骤时发生异常: {str(error_exec_exception)}")
            finally:
                # 只有在失败或异常情况下才执行res_process步骤
                if not res_process_executed and not is_success and module_name:
                    BranchExecutor._execute_res_process(config, module_name, executor)
            
            return is_success
        
        return _executor
    
    @staticmethod
    def _execute_res_process(config: Dict[str, Any], module_name: str, executor) -> None:
        """执行res_process步骤"""
        from core.step_parser import StepParser
        from config import ConfigStructure
        
        parser = StepParser()
        
        for model in config.get(ConfigStructure.MODEL_KEY, []):
            if model[ConfigStructure.NAME_KEY] == module_name:
                res_process_steps = parser.parse_process_list(
                    model.get(ConfigStructure.RES_PROCESS_KEY, []), 
                    {}, 
                    config
                )
                if res_process_steps:
                    logger.debug(f"开始执行模块 {module_name} 的res_process步骤")
                    executor.execute_steps(res_process_steps, config, None, None)
                break
