#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: main.py
# @description: AutoTool自动化执行引擎的主程序入口

"""
AutoTool自动化执行引擎主程序
负责解析命令行参数，加载配置文件，执行自动化操作流程
"""

import yaml
import argparse
import os
import sys
import time
from typing import Dict, Any, Optional

from utils.logger import logger, set_log_level
from utils.help_info import show_all_modules_help, show_main_help, show_module_help
from utils.exception_handler import ExceptionHandler, ToolCrash
from utils.util import get_config_file_path
from config import CLIConfig, ConfigStructure, Timing
from core.step_parser import StepParser
from core.step_executor import StepExecutor


class AutoToolApp:
    """AutoTool自动化执行引擎主应用类"""
    
    def __init__(self):
        """初始化应用"""
        self.parser = StepParser()
        self.executor = StepExecutor()
    
    def run(self) -> None:
        """运行主程序"""
        if self._should_show_help():
            return
        
        args = self._parse_arguments()
        if not args:
            return
        
        if self._handle_help_requests(args):
            return
        
        if not self._validate_required_args(args):
            return
        
        self._apply_log_level(args)
        cli_params = self._parse_cli_params(args)
        config = self._load_config(args)
        config = self._apply_launch_overrides(config, args)
        
        # 解析并执行步骤
        logger.info(f"Autotool 工具开始执行 - 工具: {args.tool}, 版本: {args.version}, 模块: {args.module}")
        
        # 获取当前运行模块的重试配置
        retry_enabled = False
        max_retries = 0
        
        if ConfigStructure.MODEL_KEY in config:
            for model in config[ConfigStructure.MODEL_KEY]:
                if model.get(ConfigStructure.NAME_KEY) == args.module:
                    retry_enabled = model.get("retry", False)
                    max_retries = model.get("max_retry_count", 0)
                    break
        
        steps = self.parser.parse_yaml_steps(config, args.module, cli_params)
        
        retry_count = 0
        while True:
            if retry_count > 0:
                logger.info(f"正在进行第 {retry_count}/{max_retries} 次重试...")
                
            result = self.executor.execute_steps(steps, config, args.module, cli_params)
            
            if result:
                break
                
            if retry_enabled and retry_count < max_retries:
                retry_count += 1
                logger.warning(f"模块执行失败，将在 {Timing.DEFAULT_PAUSE} 秒后重试...")
                time.sleep(Timing.DEFAULT_PAUSE)
            else:
                break
    
    def _should_show_help(self) -> bool:
        """检查是否应该显示帮助信息"""
        if "-h" in sys.argv or "--help" in sys.argv:
            show_main_help()
            return True
        return False
    
    def _parse_arguments(self) -> Optional[argparse.Namespace]:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="AutoTool自动化执行引擎 - 支持多种工具的自动化操作",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False
        )
        
        parser.add_argument(f"-{CLIConfig.TOOL_ARG[0]}", f"--{CLIConfig.TOOL_ARG}", 
                          required=True, help="工具名称")
        parser.add_argument(f"-{CLIConfig.VERSION_ARG[0]}", f"--{CLIConfig.VERSION_ARG}", 
                          required=True, help="工具版本")
        parser.add_argument(f"-{CLIConfig.MODULE_ARG[0]}", f"--{CLIConfig.MODULE_ARG}", 
                          help="模块名称")
        parser.add_argument(f"--{CLIConfig.PARAMS_ARG}", nargs="*", 
                          help="自定义参数，格式: key=value")
        parser.add_argument(f"--{CLIConfig.LAUNCH_CMD_ARG.replace('_', '-')}", 
                          help="自定义启动命令")
        parser.add_argument(f"--{CLIConfig.LAUNCH_PAUSE_ARG.replace('_', '-')}", 
                          type=int, help="Action操作间隔时间")
        parser.add_argument(f"--{CLIConfig.HELP_MODULE_ARG.replace('_', '-')}", 
                          action="store_true", help="显示指定模块的帮助信息")
        parser.add_argument(f"-{CLIConfig.LOG_ARG[0]}", f"--{CLIConfig.LOG_ARG}", 
                          choices=CLIConfig.LOG_LEVELS, help="日志级别 (debug/info)")
        
        try:
            return parser.parse_args()
        except SystemExit:
            show_main_help()
            return None

    def _handle_help_requests(self, args: argparse.Namespace) -> bool:
        """处理帮助请求"""
        if args.help_module:
            if not args.module:
                show_all_modules_help(args.tool, args.version)
            else:
                show_module_help(args.tool, args.version, args.module)
            return True
        return False
    
    def _validate_required_args(self, args: argparse.Namespace) -> bool:
        """验证必需参数"""
        if not args.module:
            print("错误：参数 -m/--module 是必需的")
            show_main_help()
            return False
        return True
    
    def _parse_cli_params(self, args: argparse.Namespace) -> Dict[str, str]:
        """解析命令行自定义参数"""
        cli_params = {}
        if args.params:
            for param in args.params:
                if CLIConfig.PARAM_SEPARATOR in param:
                    key, value = param.split(CLIConfig.PARAM_SEPARATOR, 1)
                    cli_params[key] = value
        return cli_params
    
    def _load_config(self, args: argparse.Namespace) -> Dict[str, Any]:
        """加载配置文件"""
        config_file = get_config_file_path(args.tool, args.version)

        if not os.path.exists(config_file):
            raise ToolCrash(
                component="配置文件加载", 
                message=f"配置文件不存在: {config_file}"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ToolCrash(
                component="配置文件解析", 
                message=f"配置文件解析失败: {str(e)}"
            )

    def _apply_launch_overrides(self, config: Dict[str, Any], 
                               args: argparse.Namespace) -> Dict[str, Any]:
        """应用启动参数覆盖"""
        if args.launch_cmd:
            logger.debug(f"使用自定义启动命令: {args.launch_cmd}")
            if ConfigStructure.LAUNCH_KEY not in config:
                config[ConfigStructure.LAUNCH_KEY] = {}
            config[ConfigStructure.LAUNCH_KEY][ConfigStructure.CMD_KEY] = args.launch_cmd
        
        if args.launch_pause is not None:
            logger.debug(f"使用自定义Action操作暂停时间: {args.launch_pause}秒")
            if ConfigStructure.LAUNCH_KEY not in config:
                config[ConfigStructure.LAUNCH_KEY] = {}
            config[ConfigStructure.LAUNCH_KEY][ConfigStructure.PAUSE_KEY] = args.launch_pause
        
        return config
    
    def _apply_log_level(self, args):
        """应用日志级别设置"""
        if hasattr(args, 'log') and args.log:
            set_log_level(args.log)


@ExceptionHandler.handle_general_exception
def main() -> None:
    """程序入口函数"""
    app = AutoToolApp()
    app.run()

if __name__ == "__main__":
    main()
