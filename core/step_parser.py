#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: step_parser.py
# @description: 步骤解析器模块，负责解析YAML配置并生成执行步骤

"""
步骤解析器模块
负责解析YAML配置文件，生成可执行的步骤列表
"""

from typing import Dict, Any, List, Tuple, Callable, Optional
from utils.logger import logger
from config import ConfigStructure, BranchConfig, ActionTypes
from core.action_mapper import ActionMapper
from core.branch_executor import BranchExecutor


class StepParser:
    """步骤解析器类"""
    
    def __init__(self):
        """初始化解析器"""
        self.action_mapper = ActionMapper()
        self._logged = False  # 避免重复日志
    
    def parse_yaml_steps(self, config: Dict[str, Any], module_name: str, 
                        cli_params: Dict[str, Any]) -> List[Tuple[str, Callable]]:
        """
        解析YAML配置文件，生成执行步骤列表
        
        Args:
            config: 配置对象
            module_name: 模块名称
            cli_params: 命令行参数
            
        Returns:
            执行步骤列表
        """
        from core.param_processor import ParamProcessor
        processor = ParamProcessor()
        
        for model in config.get(ConfigStructure.MODEL_KEY, []):
            if model[ConfigStructure.NAME_KEY] == module_name:
                # 处理参数
                final_params = self._process_model_params(model, cli_params, processor)
                
                # 构造变量映射字典
                variable_map = self._build_variable_map(
                    model.get(ConfigStructure.DROPDOWN_OPTIONS_KEY, {}), 
                    final_params
                )
                
                # 解析步骤列表
                steps = []
                steps.extend(self.parse_process_list(
                    model.get(ConfigStructure.PROCESS_KEY, []), 
                    final_params, config, variable_map, module_name
                ))
                steps.extend(self.parse_process_list(
                    model.get(ConfigStructure.RES_PROCESS_KEY, []), 
                    final_params, config, variable_map, module_name
                ))
                return steps
        
        logger.error(f"未找到模块: {module_name}")
        return []
    
    def _process_model_params(self, model: Dict[str, Any], cli_params: Dict[str, Any], 
                             processor) -> Dict[str, Any]:
        """处理模型参数"""
        dropdown_options = model.get(ConfigStructure.DROPDOWN_OPTIONS_KEY, {})
        dropdown_dependencies = model.get(ConfigStructure.DROPDOWN_DEPENDENCIES_KEY, [])
        default_params = model.get(ConfigStructure.DEFAULT_PARAMS_KEY, {})
        
        # 处理下拉框选项映射
        processed_cli_params = processor.process_dropdown_params(
            cli_params, dropdown_options, default_params
        )
        
        # 合并参数
        final_params = dict(default_params)
        final_params.update(processed_cli_params)
        
        # 应用下拉框依赖处理逻辑
        final_params = processor.apply_dropdown_dependencies(
            final_params, dropdown_dependencies, dropdown_options
        )
        
        # 处理文件路径参数
        final_params = processor.override_params(final_params, cli_params)
        
        return final_params
    
    def _build_variable_map(self, dropdown_options: Dict[str, Dict[str, str]], 
                           final_params: Dict[str, Any]) -> Dict[str, str]:
        """构建变量映射字典"""
        variable_map = {}
        
        for dropdown_key, options in dropdown_options.items():
            option_key = final_params.get(f"{dropdown_key}_option")
            logger.debug(f"处理下拉选项 {dropdown_key}={option_key}")
            
            if option_key and option_key in options:
                image_path = options[option_key]
                variable_map[f"{dropdown_key}_option_image"] = image_path
            else:
                logger.warning(f"下拉选项 {dropdown_key} 的值 {option_key} 无效或为空")
        
        return variable_map
    
    def parse_process_list(self, process_list: List[Dict[str, Any]], 
                          cli_params: Dict[str, Any], 
                          config: Optional[Dict[str, Any]] = None, 
                          variable_map: Optional[Dict[str, str]] = None, 
                          module_name: Optional[str] = None) -> List[Tuple[str, Callable]]:
        """
        解析步骤列表，支持变量替换和分支处理
        
        Args:
            process_list: 步骤列表
            cli_params: 命令行参数
            config: 配置对象
            variable_map: 变量映射字典
            module_name: 模块名称
            
        Returns:
            解析后的执行步骤列表
        """
        steps = []
        variable_map = variable_map or {}
        
        # 只在第一次解析时输出日志
        if not self._logged:
            logger.debug(f"开始解析步骤列表，可用变量映射: {variable_map}")
            self._logged = True
        
        for step in process_list:
            # 处理变量替换
            self._replace_step_variables(step, variable_map)
            
            # 映射Action函数
            action = step.get("action", "")
            if action:
                try:
                    mapped = self.action_mapper.map_action(step, cli_params, config, module_name)
                    if isinstance(mapped, list):
                        steps.extend(mapped)
                    else:
                        steps.append(mapped)
                except ValueError as e:
                    logger.warning(str(e))
            
            # 处理分支
            self._process_step_branch(step, steps, cli_params, config, variable_map, module_name)
        
        return steps
    
    def _replace_step_variables(self, step: Dict[str, Any], variable_map: Dict[str, str]) -> None:
        """替换步骤中的变量"""
        if "position" in step and isinstance(step["position"], str):
            original_position = step["position"]
            for k, v in variable_map.items():
                step["position"] = step["position"].replace(f"{{{k}}}", v)
    
    def _process_step_branch(self, step: Dict[str, Any], steps: List[Tuple[str, Callable]], 
                           cli_params: Dict[str, Any], config: Dict[str, Any], 
                           variable_map: Dict[str, str], module_name: str) -> None:
        """处理步骤分支"""
        if BranchConfig.BRANCH_KEY not in step:
            return
        
        # 如果是recognize_action且step为continue或type为success，预解析分支并注入到RecognitionExecutor
        if (step.get("action") == ActionTypes.RECOGNIZE and
            (step.get("step") == BranchConfig.CONTINUE_STEP or step.get("type") == "success")):
            step_type = step.get("step", "") or step.get("type", "")
            logger.debug(f"recognize_action {step_type}，预解析success分支并注入到executor")
            
            # 预解析success分支步骤（确保cli_params正确传递）
            success_steps = self.parse_process_list(
                step[BranchConfig.BRANCH_KEY].get(BranchConfig.SUCCESS_BRANCH, []),
                cli_params, config, variable_map, module_name
            )
            
            # 将预解析的步骤注入到step中，供RecognitionExecutor使用
            step['_parsed_success_steps'] = success_steps
            return
        
        # 解析分支步骤
        success_steps = self.parse_process_list(
            step[BranchConfig.BRANCH_KEY].get(BranchConfig.SUCCESS_BRANCH, []), 
            cli_params, config, variable_map, module_name
        )
        error_steps = self.parse_process_list(
            step[BranchConfig.BRANCH_KEY].get(BranchConfig.ERROR_BRANCH, []), 
            cli_params, config, variable_map, module_name
        )
        success_res = step.get("success_res", "")
        
        # 添加分支执行器
        steps.append((
            "执行分支判断",
            BranchExecutor.make_branch_executor(
                success_steps, error_steps, success_res, config, module_name
            )
        ))
