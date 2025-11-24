#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: recognizer.py
# @description: 图像识别执行器模块，处理recognize动作的复杂逻辑

"""
图像识别执行器模块
处理recognize动作的复杂识别和分支执行逻辑
"""

from typing import Dict, Any, Optional, List
from utils.logger import logger
from utils.exception_handler import ElementNotFound
from core.action import recognize_template
from config import BranchConfig


class RecognitionExecutor:
    """图像识别执行器类"""
    
    def __init__(self, step: Dict[str, Any], config: Dict[str, Any], module_name: str,
                 cli_params: Optional[Dict[str, Any]] = None,
                 parsed_success_steps: Optional[List] = None):
        """
        初始化识别执行器
        
        Args:
            step: 步骤配置
            config: 配置对象
            module_name: 模块名称
            cli_params: 命令行参数
            parsed_success_steps: 预解析的success分支步骤（优先使用）
        """
        self.step = step
        self.config = config
        self.module_name = module_name
        self.cli_params = cli_params or {}
        self.parsed_success_steps = parsed_success_steps  # 新增：保存预解析的步骤
        self.image_path = step.get("position") or step.get("image")
        self.step_param = step.get("step", "")
        self.type_param = step.get("type", BranchConfig.TYPE_ERROR)  # 新增：type参数，默认为error
    
    def execute(self) -> bool:
        """
        执行识别操作
        
        识别到图片：
            - 如果step为continue：执行success分支
            - 如果type为success：执行success分支
            - 否则（默认type为error）：报错，执行res_process分支
        没有识别到图片：
            - 如果type为success：抛出异常
            - 否则：继续执行其他步骤
        
        Returns:
            执行结果
        """
        if not self.image_path:
            logger.warning("recognize_action缺少image_path参数，跳过识别")
            return True
        
        # 使用静默模式，避免打印不必要的 ERROR 日志
        is_recognized = recognize_template(self.image_path, silent=True)
        
        if is_recognized:
            return self._handle_recognition_success()
        else:
            return self._handle_recognition_failure()
    
    def _handle_recognition_success(self) -> bool:
        """处理识别成功的情况"""
        logger.debug(f"识别到图片: {self.image_path}")
        
        if self.step_param == BranchConfig.CONTINUE_STEP:
            # 当step为continue时，直接执行success分支
            logger.debug(f"step=continue，执行success分支")
            return self._execute_success_branch()
        elif self.type_param == BranchConfig.TYPE_SUCCESS:
            # 当type为success时，执行success分支
            logger.debug(f"type=success，执行success分支")
            return self._execute_success_branch()
        else:
            # 默认行为（type=error）：报错并执行res_process分支
            logger.error(f"识别到错误提示弹窗: {self.image_path}, 执行res_process分支")
            raise ElementNotFound(
                element_name="recognize_action",
                message=f"识别到配置文件中的图片: {self.image_path}"
            )
    
    def _handle_recognition_failure(self) -> bool:
        """处理识别失败的情况"""
        if self.type_param == BranchConfig.TYPE_SUCCESS:
            # 当type为success时，识别失败则抛出异常
            logger.error(f"type=success但未识别到图片: {self.image_path}，抛出异常")
            raise ElementNotFound(
                element_name="recognize_action",
                message=f"type=success但未识别到配置文件中的图片: {self.image_path}"
            )
        else:
            # 默认行为：继续执行其他步骤
            logger.debug(f"未识别到配置文件中的图片: {self.image_path}，继续执行其他步骤")
            return True
    
    def _execute_success_branch(self) -> bool:
        """执行success分支"""
        from core.step_executor import StepExecutor
        
        # 优先使用预解析的步骤（由step_parser统一解析，确保cli_params正确传递）
        success_steps = self.parsed_success_steps
        
        # 如果没有预解析的步骤，则自行解析（向后兼容）
        if success_steps is None and BranchConfig.BRANCH_KEY in self.step and BranchConfig.SUCCESS_BRANCH in self.step[BranchConfig.BRANCH_KEY]:
            from core.step_parser import StepParser
            parser = StepParser()
            success_steps = parser.parse_process_list(
                self.step[BranchConfig.BRANCH_KEY][BranchConfig.SUCCESS_BRANCH], 
                self.cli_params,
                self.config, 
                None, 
                self.module_name
            )
        
        if success_steps:
            logger.debug(f"开始执行success分支，共{len(success_steps)}个步骤")
            executor = StepExecutor()
            # 子流程执行时不传入module_name，避免过早打印完成日志
            executor.execute_steps(success_steps, self.config, None, None)
        
        return True
