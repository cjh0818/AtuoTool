#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: action_mapper.py
# @description: 动作映射器模块，负责将配置中的动作映射到具体的执行函数

"""
动作映射器模块
负责将YAML配置中的动作类型映射到具体的执行函数
"""

from typing import Dict, Any, List, Tuple, Callable, Optional, Union
from config import ActionTypes, WindowOperations, ResultTypes
from core.recognizer import RecognitionExecutor
from core.param_processor import ParamProcessor
from core.action import (
    click_action, input_action, openAPP_action, window_minimize,
    window_maximize, text_output, image_output, screenshot_action,
    keyboard_action, output_action
)


class ActionMapper:
    """动作映射器类"""
    
    def __init__(self):
        """初始化动作映射表"""
        self._action_map = {
            ActionTypes.OPEN: self._map_open_action,
            ActionTypes.CLICK: self._map_click_action,
            ActionTypes.INPUT: self._map_input_action,
            ActionTypes.RES: self._map_res_action,
            ActionTypes.WINDOW: self._map_window_action,
            ActionTypes.RECOGNIZE: self._map_recognize_action,
            ActionTypes.KEYBOARD: self._map_keyboard_action,
            ActionTypes.SCREENSHOT: self._map_screenshot_action,
            ActionTypes.OUTPUT: self._map_output_action,
        }
    
    def map_action(self, step: Dict[str, Any], cli_params: Dict[str, Any], 
                   config: Optional[Dict[str, Any]] = None, 
                   module_name: Optional[str] = None) -> Union[Tuple[str, Callable], List[Tuple[str, Callable]]]:
        """
        映射动作到执行函数
        
        Args:
            step: 步骤配置
            cli_params: 命令行参数
            config: 配置对象
            module_name: 模块名称
            
        Returns:
            单个或多个(描述, 执行函数)元组
        """
        action = step.get("action", "")
        if action not in self._action_map:
            raise ValueError(f"未识别的 action: {action}")
        
        mapper_func = self._action_map[action]
        
        # 检查是否需要传递额外参数
        if action in [ActionTypes.OPEN, ActionTypes.WINDOW, ActionTypes.RECOGNIZE]:
            return mapper_func(step, cli_params, config, module_name)
        else:
            return mapper_func(step, cli_params)
    
    def _map_open_action(self, step: Dict[str, Any], cli_params: Dict[str, Any], 
                        config: Dict[str, Any], module_name: str) -> Tuple[str, Callable]:
        """映射打开应用动作"""
        # 读取skip_process_check参数，如果未设置则默认为None
        skip_process_check = step.get("skip_process_check", None)
        return (
            "打开应用",
            lambda: openAPP_action(config, module_name, skip_process_check)
        )
    
    def _map_click_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> Tuple[str, Callable]:
        """映射点击动作"""
        return (
            step.get("description", f"点击 {step.get('position')}"),
            lambda: click_action(
                step.get("position"),
                click_offset=tuple(step.get("click_offset", (0, 0))),
                click_flag=step.get("click_button", "left"),
                uac=step.get("uac", False)
            )
        )
    
    def _map_input_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> List[Tuple[str, Callable]]:
        """映射输入动作"""
        processor = ParamProcessor()
        
        return [
            (
                step.get("description", f"输入 {k}"),
                lambda v=v, k=k, clear=step.get("clear", True), enter=step.get("enter", True):
                    input_action(v, clear, enter, k)
            )
            for k, v in processor.override_params(step.get("param", {}), cli_params).items()
        ]
    
    def _map_res_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> Tuple[str, Callable]:
        """映射结果输出动作"""
        op = step.get("res_op") or step.get("res_type") or step.get("type") or ResultTypes.TEXT
        op = str(op).lower()
        
        if op == ResultTypes.IMAGE:
            return ("识别结果图像", lambda: image_output())
        else:
            return ("解析命令输出结果", lambda: text_output())
    
    def _map_window_action(self, step: Dict[str, Any], cli_params: Dict[str, Any], 
                          config: Dict[str, Any], module_name: str) -> Tuple[str, Callable]:
        """映射窗口操作动作"""
        from core.process_manager import ProcessManager
        
        # 优先使用命令行参数，其次使用step配置
        op = WindowOperations.EXIT  # 默认值
        if cli_params and "window_action" in cli_params:
            op = cli_params["window_action"]
        else:
            op = step.get("window_op") or step.get("type") or WindowOperations.EXIT
        
        op = str(op).lower()
        if op == WindowOperations.MINIMIZE:
            return ("最小化窗口", lambda: window_minimize())
        elif op == WindowOperations.MAXIMIZE:
            return ("最大化窗口", lambda: window_maximize())
        else:
            return ("关闭工具进程", lambda: ProcessManager.close_tool_process(config))
    
    def _map_recognize_action(self, step: Dict[str, Any], cli_params: Dict[str, Any], 
                             config: Dict[str, Any], module_name: str) -> Tuple[str, Callable]:
        """映射识别动作"""
        parsed_success_steps = step.get('_parsed_success_steps', None)
        executor = RecognitionExecutor(step, config, module_name, cli_params, parsed_success_steps)
        return ("识别模板图片", executor.execute)
    
    
    def _map_screenshot_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> Tuple[str, Callable]:
        """映射截图动作"""
        return (
            step.get("description", f"截取屏幕图片 {step.get('screenshot_path', '')}"),
            lambda: screenshot_action(
                size=step.get("size"),
                use_last_click_position=step.get("use_last_click_position", True),
                screenshot_path=step.get("screenshot_path")
            )
        )
    
    def _map_keyboard_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> Tuple[str, Callable]:
        """映射统一键盘操作"""
        keys = step.get("keys", "")
        duration = step.get("duration")
        action_type = step.get("action_type", "hotkey")
        
        # 生成描述
        if action_type == "press":
            description = step.get("description", f"长按 {keys} 键 {duration}秒")
        else:
            description = step.get("description", f"按下快捷键 {keys}")
        
        return (
            description,
            lambda: keyboard_action(keys, duration=duration, action_type=action_type)
        )
    
    def _map_output_action(self, step: Dict[str, Any], cli_params: Dict[str, Any]) -> Tuple[str, Callable]:
        """映射输出反馈动作"""
        text = step.get("text", "")
        
        # 生成描述
        description = step.get("description", f"输出反馈信息")
        
        return (
            description,
            lambda: output_action(text, cli_params)
        )
    
