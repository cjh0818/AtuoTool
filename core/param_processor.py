#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: param_processor.py
# @description: 参数处理器模块，负责处理命令行参数和配置参数的合并与转换

"""
参数处理器模块
负责处理命令行参数与配置文件参数的合并、转换和验证
"""

import os
from typing import Dict, Any, Optional, List
from utils.logger import logger
from config import FileConfig


class ParamProcessor:
    """参数处理器类"""
    
    @staticmethod
    def override_params(yaml_params: Dict[str, Any], cli_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        参数覆盖逻辑，命令行参数优先级高于YAML参数
        
        Args:
            yaml_params: YAML配置参数
            cli_params: 命令行参数
            
        Returns:
            合并后的参数字典
        """
        params = dict(yaml_params or {})
        
        # 命令行参数覆盖YAML参数
        for k in params.keys():
            if k in cli_params:
                params[k] = cli_params[k]
        
        # 处理文件路径参数
        params = ParamProcessor._process_file_path_params(params)
        
        return params
    
    @staticmethod
    def _process_file_path_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文件路径参数，读取文件内容
        
        Args:
            params: 参数字典
            
        Returns:
            处理后的参数字典
        """
        for k, v in params.items():
            if 'filepath' in k.lower() and isinstance(v, str):
                try:
                    if os.path.exists(v):
                        cleaned_path = ParamProcessor._clean_file_path(v)
                        logger.debug(f"读取文件: {cleaned_path}")
                        
                        with open(cleaned_path, 'r', encoding=FileConfig.DEFAULT_ENCODING) as f:
                            file_content = f.read()
                        
                        params[k] = file_content.strip()
                        logger.debug(f"已从文件 {cleaned_path} 读取内容并赋值给参数 {k}")
                    else:
                        logger.debug(f"参数 {k} 的值不是有效的文件路径，跳过文件读取")
                except Exception as e:
                    logger.error(f"读取文件 {v} 失败: {str(e)}，跳过文件读取")
        
        return params
    
    @staticmethod
    def _clean_file_path(file_path: str) -> str:
        """
        清理文件路径字符串
        
        Args:
            file_path: 原始文件路径
            
        Returns:
            清理后的文件路径
        """
        # 清理路径字符串，移除可能的不可见字符和引号
        cleaned_path = file_path.strip().strip('"\'')
        
        # 更彻底的清理：移除所有不可见字符
        cleaned_path = ''.join(char for char in cleaned_path if ord(char) >= 32 or char in '\n\r\t')
        
        return cleaned_path
    
    @staticmethod
    def process_dropdown_params(cli_params: Dict[str, Any], dropdown_options: Dict[str, Dict[str, str]], 
                               default_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理下拉框参数，将用户输入的选项转换为对应的图像路径
        
        Args:
            cli_params: 命令行参数字典
            dropdown_options: 下拉选项配置
            default_params: 默认参数配置
            
        Returns:
            处理后的参数字典
        """
        processed_params = dict(cli_params)
        
        for dropdown_key, options in dropdown_options.items():
            if dropdown_key in cli_params:
                # 用户直接指定了下拉选项值
                ParamProcessor._process_user_dropdown_option(
                    processed_params, dropdown_key, cli_params[dropdown_key], options
                )
            else:
                # 使用默认值
                ParamProcessor._process_default_dropdown_option(
                    processed_params, dropdown_key, options, default_params
                )
        
        return processed_params
    
    @staticmethod
    def _process_user_dropdown_option(processed_params: Dict[str, Any], dropdown_key: str, 
                                     user_value: str, options: Dict[str, str]) -> None:
        """处理用户指定的下拉选项"""
        if user_value in options:
            processed_params[f"{dropdown_key}_option"] = user_value
            processed_params[f"{dropdown_key}_option_image"] = options[user_value]
            logger.debug(f"用户指定下拉选项 {dropdown_key}={user_value}")
        else:
            logger.warning(f"下拉选项 {dropdown_key}={user_value} 无效，可用选项: {list(options.keys())}")
    
    @staticmethod
    def _process_default_dropdown_option(processed_params: Dict[str, Any], dropdown_key: str, 
                                        options: Dict[str, str], default_params: Optional[Dict[str, Any]]) -> None:
        """处理默认下拉选项"""
        if not default_params:
            return
        
        default_option_key = f"{dropdown_key}_option"
        default_value = None
        
        # 尝试获取默认值
        if default_option_key in default_params:
            default_value = default_params[default_option_key]
        elif dropdown_key in default_params:
            # 兼容处理：如果default_params中直接是dropdown_key而不是dropdown_key_option
            default_value = default_params[dropdown_key]
        
        if default_value and default_value in options:
            processed_params[default_option_key] = default_value
            processed_params[f"{dropdown_key}_option_image"] = options[default_value]
            logger.debug(f"使用默认下拉选项 {dropdown_key}={default_value}")
        elif default_value:
            logger.warning(f"默认下拉选项 {dropdown_key}={default_value} 无效，可用选项: {list(options.keys())}")
    
    @staticmethod
    def apply_dropdown_dependencies(final_params: Dict[str, Any], dropdown_dependencies: List[Dict[str, Any]], 
                                   dropdown_options: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        应用下拉框依赖关系处理
        
        Args:
            final_params: 最终参数字典
            dropdown_dependencies: 下拉框依赖配置列表
            dropdown_options: 下拉选项配置
            
        Returns:
            处理后的参数字典
        """
        params = dict(final_params)
        
        if not dropdown_dependencies:
            return params
        
        for dependency in dropdown_dependencies:
            ParamProcessor._apply_single_dependency(params, dependency, dropdown_options)
        
        return params
    
    @staticmethod
    def _apply_single_dependency(params: Dict[str, Any], dependency: Dict[str, Any], 
                                dropdown_options: Dict[str, Dict[str, str]]) -> None:
        """应用单个依赖关系"""
        source_key = dependency.get("source_key")
        target_key = dependency.get("target_key")
        mapping = dependency.get("mapping", {})
        
        if not source_key or not target_key or not mapping:
            return
        
        # 获取源参数的当前值
        source_value = params.get(f"{source_key}_option")
        
        if source_value and source_value in mapping:
            allowed_values = mapping[source_value]
            target_value = params.get(f"{target_key}_option")
            
            # 检查目标参数的值是否在允许的列表中
            if target_value not in allowed_values and allowed_values:
                target_options = dropdown_options.get(target_key, {})
                
                if allowed_values[0] in target_options:
                    old_value = target_value
                    new_value = allowed_values[0]
                    params[f"{target_key}_option"] = new_value
                    
                    # 同时更新对应的图像路径
                    if new_value in target_options:
                        params[f"{target_key}_option_image"] = target_options[new_value]
                    
                    logger.debug(f"依赖关系调整: {target_key}_option 从 {old_value} 调整为 {new_value}")
