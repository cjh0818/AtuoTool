#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: help_info.py
# @description: 帮助信息显示模块，提供各种帮助信息展示功能

"""
帮助信息显示模块
提供各种帮助信息展示功能，包括主帮助、模块帮助和参数说明
"""

import os
import yaml
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

from utils.util import get_program_directory
from config import HelpConfig


@dataclass
class ModuleInfo:
    """模块信息数据类"""
    name: str
    description: str
    dropdown_options: Dict[str, Dict[str, str]]
    default_params: Dict[str, Any]
    dropdown_dependencies: List[Dict[str, Any]]
    process: List[Dict[str, Any]]
    res_process: List[Dict[str, Any]]


@dataclass
class ToolInfo:
    """工具信息数据类"""
    name: str
    versions: List[str]


class ConfigScanner:
    """配置文件扫描器类"""
    
    @staticmethod
    def get_config_directory() -> str:
        """
        获取配置文件目录路径
        
        Returns:
            配置文件目录的绝对路径
        """
        program_dir = get_program_directory()
        return os.path.join(program_dir, 'config')
    
    @staticmethod
    def scan_config_files() -> List[ToolInfo]:
        """
        扫描配置文件并提取工具和版本信息
        
        Returns:
            工具信息列表
            
        Raises:
            FileNotFoundError: 配置目录不存在
        """
        config_dir = ConfigScanner.get_config_directory()
        
        if not os.path.exists(config_dir):
            raise FileNotFoundError(HelpConfig.ERROR_CONFIG_DIR_NOT_EXIST.format(path=config_dir))
        
        config_files = [f for f in os.listdir(config_dir) if f.endswith(HelpConfig.CONFIG_FILE_EXTENSION)]
        tools = {}
        
        for config_file in config_files:
            if '_' in config_file:
                tool, version = config_file.rsplit('_', 1)
                version = version[:-len(HelpConfig.CONFIG_FILE_EXTENSION)]  # 去掉 .yml 后缀
                if tool not in tools:
                    tools[tool] = []
                tools[tool].append(version)
        
        return [ToolInfo(name=tool, versions=sorted(versions)) for tool, versions in sorted(tools.items())]
    
    @staticmethod
    def load_config_file(tool: str, version: str) -> Dict[str, Any]:
        """
        加载指定工具和版本的配置文件
        
        Args:
            tool: 工具名称
            version: 工具版本
            
        Returns:
            配置文件内容字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
        """
        config_dir = ConfigScanner.get_config_directory()
        config_file = os.path.join(config_dir, f"{tool}_{version}{HelpConfig.CONFIG_FILE_EXTENSION}")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(HelpConfig.ERROR_CONFIG_FILE_NOT_EXIST.format(path=config_file))
        
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


class ModuleExtractor:
    """模块信息提取器类"""
    
    @staticmethod
    def extract_modules_from_config(config: Dict[str, Any]) -> List[ModuleInfo]:
        """
        从配置文件中提取模块信息
        
        Args:
            config: 配置文件内容
            
        Returns:
            模块信息列表
        """
        modules = []
        for model in config.get("model", []):
            module_info = ModuleInfo(
                name=model.get("name", HelpConfig.DEFAULT_MODULE_NAME),
                description=model.get("description", HelpConfig.DEFAULT_DESCRIPTION),
                dropdown_options=model.get("dropdown_options", {}),
                default_params=model.get("default_params", {}),
                dropdown_dependencies=model.get("dropdown_dependencies", []),
                process=model.get("process", []),
                res_process=model.get("res_process", [])
            )
            modules.append(module_info)
        
        return modules
    
    @staticmethod
    def find_module_by_name(modules: List[ModuleInfo], module_name: str) -> Optional[ModuleInfo]:
        """
        根据名称查找模块
        
        Args:
            modules: 模块信息列表
            module_name: 要查找的模块名称
            
        Returns:
            找到的模块信息，未找到则返回None
        """
        for module in modules:
            if module.name == module_name:
                return module
        return None


class ParameterExtractor:
    """参数提取器类"""
    
    @staticmethod
    def extract_params_from_process(process_list: List[Dict[str, Any]]) -> List[str]:
        """
        从步骤列表中提取参数名称
        
        Args:
            process_list: 步骤列表
            
        Returns:
            参数名称列表
        """
        extracted_params = []
        
        def extract_recursive(steps: List[Dict[str, Any]]) -> None:
            for step in steps:
                if "param" in step:
                    for param_name in step["param"].keys():
                        if param_name not in extracted_params:
                            extracted_params.append(param_name)
                # 递归提取branch分支中的参数
                if "branch" in step:
                    for branch_name, branch_steps in step["branch"].items():
                        extract_recursive(branch_steps)
        
        extract_recursive(process_list)
        return extracted_params
    
    @staticmethod
    def find_all_steps_with_params(process_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        查找所有包含参数的步骤
        
        Args:
            process_list: 步骤列表
            
        Returns:
            包含参数的步骤列表
        """
        steps_with_params = []
        
        def find_recursive(steps: List[Dict[str, Any]]) -> None:
            for step in steps:
                if "param" in step:
                    steps_with_params.append(step)
                # 递归查找branch分支中的步骤
                if "branch" in step:
                    for branch_name, branch_steps in step["branch"].items():
                        find_recursive(branch_steps)
        
        find_recursive(process_list)
        return steps_with_params
    
    @staticmethod
    def extract_default_params_from_process(process_list: List[Dict[str, Any]], 
                                          exclude_params: Dict[str, Any]) -> List[str]:
        """
        从步骤列表中提取默认参数
        
        Args:
            process_list: 步骤列表
            exclude_params: 要排除的参数字典
            
        Returns:
            参数=值格式的字符串列表
        """
        example_params = []
        
        def extract_recursive(steps: List[Dict[str, Any]]) -> None:
            for step in steps:
                if "param" in step:
                    for param_name, param_value in step["param"].items():
                        # 只添加不在exclude_params中的参数
                        if param_name not in exclude_params:
                            example_params.append(f"{param_name}={param_value}")
                # 递归提取branch分支中的默认参数
                if "branch" in step:
                    for branch_name, branch_steps in step["branch"].items():
                        extract_recursive(branch_steps)
        
        extract_recursive(process_list)
        return example_params


class HelpFormatter:
    """帮助信息格式化器类"""
    
    @staticmethod
    def format_title(title: str) -> str:
        """
        格式化标题
        
        Args:
            title: 标题文本
            
        Returns:
            格式化后的标题字符串
        """
        separator = "=" * HelpConfig.SEPARATOR_LENGTH
        return f"{separator} {title} {separator}"
    
    @staticmethod
    def format_tool_versions(tools: List[ToolInfo]) -> str:
        """
        格式化工具版本信息
        
        Args:
            tools: 工具信息列表
            
        Returns:
            格式化后的版本信息字符串
        """
        version_parts = []
        for tool in tools:
            versions_str = ', '.join(tool.versions)
            version_parts.append(f"{tool.name}: {versions_str}")
        return "; ".join(version_parts)
    
    @staticmethod
    def format_module_description(description: str, module_name: str) -> str:
        """
        格式化模块描述信息
        
        Args:
            description: 模块描述
            module_name: 模块名称
            
        Returns:
            格式化后的模块描述字符串
        """
        # 中文描述每个字符按2个宽度计算，英文按1个
        desc_width = len(description.encode('gbk')) - len(description) + len(description)
        # 总宽度为20个字符，减去描述宽度，再加上一些额外空格
        spaces = max(HelpConfig.MIN_SPACES, HelpConfig.DESCRIPTION_WIDTH_CALCULATION - desc_width)
        return f"  - {description}{' ' * spaces}: {module_name}"
    
    @staticmethod
    def format_parameter_info(param_name: str, info: str) -> str:
        """
        格式化参数信息
        
        Args:
            param_name: 参数名称
            info: 参数信息
            
        Returns:
            格式化后的参数信息字符串
        """
        return f"  --{param_name:<{HelpConfig.PARAM_NAME_WIDTH}}: {info}"
    
    @staticmethod
    def format_dependency_mapping(source_key: str, src_val: str, target_key: str, targets: List[str]) -> str:
        """
        格式化依赖关系映射信息
        
        Args:
            source_key: 源参数键
            src_val: 源参数值
            target_key: 目标参数键
            targets: 目标参数可选值列表
            
        Returns:
            格式化后的依赖关系字符串
        """
        return f"    {source_key}={src_val:<{HelpConfig.SOURCE_VALUE_WIDTH}} -> {target_key} 可选: {', '.join(targets)}"


class MainHelpDisplay:
    """主帮助信息显示器类"""
    
    def __init__(self):
        """初始化主帮助显示器"""
        self.scanner = ConfigScanner()
        self.formatter = HelpFormatter()
    
    def show_main_help(self) -> None:
        """显示主帮助信息，包括所有参数的可选值"""
        try:
            tools = self.scanner.scan_config_files()
        except FileNotFoundError as e:
            print(str(e))
            return
        
        # 显示标题
        print(self.formatter.format_title(HelpConfig.MAIN_HELP_TITLE))
        
        # 显示必需参数
        self._show_required_params(tools)
        
        # 显示模块信息
        self._show_module_info()
        
        # 显示可选参数
        self._show_optional_params()
        
        # 显示使用示例
        self._show_usage_examples()
    
    def _show_required_params(self, tools: List[ToolInfo]) -> None:
        """显示必需参数信息"""
        print(f"\n{HelpConfig.REQUIRED_PARAMS_TITLE}")
        print("  -t, --tool      " + HelpConfig.TOOL_PARAM_DESC)
        print("    可选值       ", end=" ")
        
        if tools:
            tool_names = [tool.name for tool in tools]
            print(", ".join(tool_names))
        else:
            print(HelpConfig.ERROR_NO_AVAILABLE_CONFIGS)
        
        print("  -v, --version   " + HelpConfig.VERSION_PARAM_DESC)
        print("    可选值       ", end=" ")
        print(self.formatter.format_tool_versions(tools))
        print()
    
    def _show_module_info(self) -> None:
        """显示模块信息"""
        print("  -m, --module    " + HelpConfig.MODULE_PARAM_DESC)
        print("    可选值       ")
        
        config_dir = self.scanner.get_config_directory()
        config_files = [f for f in os.listdir(config_dir) if f.endswith(HelpConfig.CONFIG_FILE_EXTENSION)]
        
        for config_file in config_files:
            try:
                tool, version = config_file.rsplit('_', 1)
                version = version[:-len(HelpConfig.CONFIG_FILE_EXTENSION)]
                config = self.scanner.load_config_file(tool, version)
                
                modules = ModuleExtractor.extract_modules_from_config(config)
                module_descriptions = [f"{module.description}: {module.name}" for module in modules]
                
                if module_descriptions:
                    print(f"      工具 {tool} 版本 {version}:    {', '.join(module_descriptions)}")
            except Exception:
                continue
    
    def _show_optional_params(self) -> None:
        """显示可选参数"""
        print(f"\n{HelpConfig.OPTIONAL_PARAMS_TITLE}")
        print("  --params        " + HelpConfig.PARAMS_PARAM_DESC)
        print("    " + HelpConfig.PARAMS_FORMAT_DESC)
        print("    " + HelpConfig.PARAMS_EXAMPLE)
        
        print("  --launch-cmd    " + HelpConfig.LAUNCH_CMD_PARAM_DESC)
        print("    " + HelpConfig.LAUNCH_CMD_OVERRIDE_DESC)
        print("    " + HelpConfig.LAUNCH_CMD_EXAMPLE)
        
        print("  --launch-pause  " + HelpConfig.LAUNCH_PAUSE_PARAM_DESC)
        print("    " + HelpConfig.LAUNCH_PAUSE_OVERRIDE_DESC)
        print("    " + HelpConfig.LAUNCH_PAUSE_EXAMPLE)
        
        print("  -l, --log       " + HelpConfig.LOG_PARAM_DESC)
        print("    可选值        debug, info")
        
        print("  --help-module   " + HelpConfig.HELP_MODULE_PARAM_DESC)
        
    
    def _show_usage_examples(self) -> None:
        """显示使用示例"""
        print(f"\n{HelpConfig.USAGE_EXAMPLES_TITLE}")
        
        print(f"  {HelpConfig.MAIN_USAGE_EXAMPLE}")


class AllModulesHelpDisplay:
    """所有模块帮助信息显示器类"""
    
    def __init__(self):
        """初始化所有模块帮助显示器"""
        self.scanner = ConfigScanner()
        self.formatter = HelpFormatter()
    
    def show_all_modules_help(self, tool: str, version: str) -> None:
        """
        显示所有可用模块的帮助信息
        
        Args:
            tool: 工具名称
            version: 工具版本
        """
        try:
            config = self.scanner.load_config_file(tool, version)
        except FileNotFoundError as e:
            print(str(e))
            return
        
        modules = ModuleExtractor.extract_modules_from_config(config)
        if not modules:
            print(HelpConfig.ERROR_NO_MODULES_FOUND)
            return
        
        # 显示标题
        title = HelpConfig.ALL_MODULES_TITLE_FORMAT.format(tool=tool, version=version)
        print(f"\n{self.formatter.format_title(title)}")
        
        # 显示所有可用模块
        print(f"\n{HelpConfig.AVAILABLE_MODULES_TITLE}")
        for module in modules:
            print(self.formatter.format_module_description(module.description, module.name))
        
        # 显示查看详细帮助的提示
        example = HelpConfig.MODULE_HELP_EXAMPLE_FORMAT.format(tool=tool, version=version)
        print(f"\n要查看特定模块的详细帮助信息，请使用:")
        print(f"  {example}")


class ModuleHelpDisplay:
    """模块帮助信息显示器类"""
    
    def __init__(self):
        """初始化模块帮助显示器"""
        self.scanner = ConfigScanner()
        self.formatter = HelpFormatter()
        self.param_extractor = ParameterExtractor()
    
    def show_module_help(self, tool: str, version: str, module_name: str) -> None:
        """
        显示指定模块的帮助信息
        
        Args:
            tool: 工具名称
            version: 工具版本
            module_name: 模块名称
        """
        try:
            config = self.scanner.load_config_file(tool, version)
        except FileNotFoundError as e:
            print(str(e))
            return
        
        modules = ModuleExtractor.extract_modules_from_config(config)
        module_info = ModuleExtractor.find_module_by_name(modules, module_name)
        
        if not module_info:
            print(HelpConfig.ERROR_MODULE_NOT_FOUND.format(module=module_name))
            return
        
        # 显示模块帮助信息
        title = HelpConfig.MODULE_HELP_TITLE_FORMAT.format(tool=tool, version=version, module=module_name)
        print(f"\n{self.formatter.format_title(title)}")
        
        # 显示模块描述
        print(f"描述: {module_info.description}")
        
        # 显示下拉选项参数
        self._show_dropdown_options(module_info)
        
        # 显示依赖关系
        self._show_dependencies(module_info)
        
        # 显示普通参数
        self._show_other_params(module_info)
        
        # 显示使用示例
        self._show_usage_example(tool, version, module_name, module_info)
    
    def _show_dropdown_options(self, module_info: ModuleInfo) -> None:
        """显示下拉选项参数"""
        if not module_info.dropdown_options:
            return
        
        print(f"\n可选参数:")
        for param_name, options in module_info.dropdown_options.items():
            default_key = f"{param_name}_option"
            default_value = module_info.default_params.get(default_key, HelpConfig.DEFAULT_VALUE_NONE)
            option_values = ', '.join(options.keys())
            info = f"可选值 {option_values}; 默认值: {default_value}"
            print(self.formatter.format_parameter_info(param_name, info))
    
    def _show_dependencies(self, module_info: ModuleInfo) -> None:
        """显示参数依赖关系"""
        if not module_info.dropdown_dependencies:
            return
        
        print(f"\n{HelpConfig.PARAM_DEPENDENCIES_TITLE}")
        for dep in module_info.dropdown_dependencies:
            source_key = dep.get("source_key")
            target_key = dep.get("target_key")
            mapping = dep.get("mapping", {})
            
            print(f"  {source_key} 选择不同值时，{target_key} 的可选值:")
            for src_val, allowed_targets in mapping.items():
                print(self.formatter.format_dependency_mapping(source_key, src_val, target_key, allowed_targets))
    
    def _show_other_params(self, module_info: ModuleInfo) -> None:
        """显示其他参数"""
        # 提取所有参数
        extracted_params = []
        extracted_params.extend(self.param_extractor.extract_params_from_process(module_info.process))
        extracted_params.extend(self.param_extractor.extract_params_from_process(module_info.res_process))
        
        if not extracted_params:
            return
        
        print(f"\n{HelpConfig.OTHER_PARAMS_TITLE}")
        
        # 获取所有包含参数的步骤
        all_steps_with_params = []
        all_steps_with_params.extend(self.param_extractor.find_all_steps_with_params(module_info.process))
        all_steps_with_params.extend(self.param_extractor.find_all_steps_with_params(module_info.res_process))
        
        # 显示参数
        for step in all_steps_with_params:
            if "param" in step:
                for param_name, default_value in step["param"].items():
                    if param_name in extracted_params:
                        print(self.formatter.format_parameter_info(param_name, f"默认值 {default_value}"))
                        extracted_params.remove(param_name)
    
    def _show_usage_example(self, tool: str, version: str, module_name: str, module_info: ModuleInfo) -> None:
        """显示使用示例"""
        print(f"\n{HelpConfig.USAGE_EXAMPLES_TITLE}")
        
        # 构建动态使用示例
        example_params = []
        
        # 从模块的default_params中获取默认参数
        for param_name, param_value in module_info.default_params.items():
            # 跳过选项参数（以_option结尾的）
            if not param_name.endswith("_option"):
                example_params.append(f"{param_name}={param_value}")
        
        # 从模块的process中提取参数默认值
        example_params.extend(self.param_extractor.extract_default_params_from_process(
            module_info.process, module_info.default_params))
        example_params.extend(self.param_extractor.extract_default_params_from_process(
            module_info.res_process, module_info.default_params))
        
        # 构建示例命令
        example_cmd = HelpConfig.USAGE_EXAMPLE_FORMAT.format(tool=tool, version=version, module=module_name)
        if example_params:
            example_cmd += f" --params {' '.join(example_params)}"
        
        print(f"  {example_cmd}")


# 创建全局显示器实例
_main_help_display = MainHelpDisplay()
_all_modules_help_display = AllModulesHelpDisplay()
_module_help_display = ModuleHelpDisplay()


def show_main_help() -> None:
    """显示主帮助信息，包括所有参数的可选值"""
    _main_help_display.show_main_help()


def show_all_modules_help(tool: str, version: str) -> None:
    """
    显示所有可用模块的帮助信息
    
    Args:
        tool: 工具名称
        version: 工具版本
    """
    _all_modules_help_display.show_all_modules_help(tool, version)


def show_module_help(tool: str, version: str, module_name: str) -> None:
    """
    显示指定模块的帮助信息
    
    Args:
        tool: 工具名称
        version: 工具版本
        module_name: 模块名称
    """
    _module_help_display.show_module_help(tool, version, module_name)