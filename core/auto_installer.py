#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-11-24
# @filename: auto_installer.py
# @description: 自动化安装器模块

import time
import logging
import ctypes
from ctypes import POINTER, WINFUNCTYPE, byref, c_bool, c_int, create_unicode_buffer, wintypes
from typing import List, Optional, Set

from utils.logger import logger
from config import AutoInstallConfig

# Windows API 常量定义
BM_CLICK = 0x00F5
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_CHECKED = 0x0001
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_CLOSE = 0x0010

# 加载 DLL
try:
    USER32 = ctypes.windll.user32
    KERNEL32 = ctypes.windll.kernel32
except AttributeError:
    # 非 Windows 环境下的 Mock，防止导入报错
    USER32 = None
    KERNEL32 = None
    logger.warning("当前非Windows环境，AutoInstaller模块无法正常工作")

# 回调函数类型定义
EnumWindowsProc = WINFUNCTYPE(c_bool, POINTER(c_int), POINTER(c_int))
EnumChildProc = WINFUNCTYPE(c_bool, POINTER(c_int), POINTER(c_int))

class AutoInstaller:
    """
    自动化安装器
    通过遍历窗口控件，匹配按钮文本并自动点击，实现非顺序依赖的自动化安装
    """

    def __init__(self, keywords: Optional[List[str]] = None, 
                 finish_keywords: Optional[List[str]] = None,
                 max_retries: int = 30,
                 interval: float = 2.0):
        """
        初始化安装器
        :param keywords: 需要点击的按钮关键词列表
        :param finish_keywords: 结束安装的关键词列表（点击后退出循环）
        :param max_retries: 最大重试次数（循环检测次数）
        :param interval: 每次检测的间隔时间（秒）
        """
        self.keywords = [k.lower() for k in (keywords or AutoInstallConfig.DEFAULT_CLICK_KEYWORDS)]
        self.finish_keywords = [k.lower() for k in (finish_keywords or AutoInstallConfig.DEFAULT_FINISH_KEYWORDS)]
        self.max_retries = max_retries
        self.interval = interval
        self.clicked_buttons = set()  # 记录已点击的按钮，避免重复点击同一状态
        self.is_finished = False

    def start(self):
        """开始自动化安装流程"""
        if not USER32:
            logger.error("无法在非Windows环境下运行AutoInstaller")
            return False

        logger.debug(f"开始自动化安装流程，监控关键词: {self.keywords}")
        
        for i in range(self.max_retries):
            if self.is_finished:
                logger.info("检测到结束标志，自动化安装流程完成")
                return True
            
            logger.debug(f"自动化安装扫描中... ({i+1}/{self.max_retries})")
            # 枚举所有顶层窗口
            USER32.EnumWindows(EnumWindowsProc(self._enum_window_callback), 0)
            
            time.sleep(self.interval)
        
        logger.debug("自动化安装流程循环结束，未检测到结束标志，视为完成")
        return True

    def _enum_window_callback(self, hwnd, lparam):
        """枚举顶层窗口的回调"""
        if not USER32.IsWindowVisible(hwnd):
            return True

        # 获取窗口标题
        length = USER32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
            
        buff = create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # 这里可以加一个逻辑：只处理特定标题的窗口，或者处理所有可见窗口
        # 目前策略：处理所有可见窗口中的子控件，因为安装弹窗标题可能变化
        
        # 枚举子窗口（控件）
        USER32.EnumChildWindows(hwnd, EnumChildProc(self._enum_child_callback), 0)
        return True

    def _enum_child_callback(self, hwnd, lparam):
        """枚举子窗口（控件）的回调"""
        if not USER32.IsWindowVisible(hwnd):
            return True
            
        # 获取控件文本
        text = self._get_window_text(hwnd)
        if not text:
            return True
            
        text_lower = text.lower()
        
        # 检查是否是需要点击的按钮
        for keyword in self.keywords:
            if keyword in text_lower:
                # 检查是否在黑名单中
                if any(ignore in text_lower for ignore in AutoInstallConfig.DONT_CLICK_KEYWORDS):
                    continue
                
                # 检查是否是结束关键词
                is_finish = any(f in text_lower for f in self.finish_keywords)
                
                # 执行点击
                self._click_button(hwnd, text, is_finish)
                
                # 如果点击了按钮，通常需要等待界面响应，所以这里可以返回False停止当前窗口的枚举
                # 但为了稳健，我们继续枚举其他可能并存的按钮（虽然少见）
                return True
                
        return True

    def _get_window_text(self, hwnd):
        """获取窗口/控件文本"""
        length = USER32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
        if length == 0:
            return ""
        text = create_unicode_buffer(length + 1)
        USER32.SendMessageW(hwnd, WM_GETTEXT, length + 1, text)
        return text.value.replace("&", "")  # 去除快捷键标记

    def _click_button(self, hwnd, text, is_finish=False):
        """点击按钮"""
        # 简单的去重逻辑：如果短时间内已经点击过完全相同的句柄和文本，可以跳过
        # 但考虑到安装步骤可能需要多次点击"Next"，这里不做严格去重，而是依赖循环间隔
        
        if not USER32.IsWindowEnabled(hwnd):
            return

        logger.debug(f"自动点击按钮: [{text}]")
        
        # 激活窗口
        # USER32.SetForegroundWindow(hwnd) # 慎用，可能会抢焦点
        
        # 发送点击消息
        USER32.SendMessageW(hwnd, BM_CLICK, 0, 0)
        
        if is_finish:
            self.is_finished = True

    def check_window_exists(self) -> bool:
        """
        检测是否存在符合条件的安装窗口（不点击）
        :return: 是否存在
        """
        if not USER32:
            return False
            
        self._found_target = False
        self._current_window_title = ""
        USER32.EnumWindows(EnumWindowsProc(self._enum_window_check_callback), 0)
        return self._found_target

    def _get_window_class(self, hwnd):
        """获取窗口类名"""
        buff = create_unicode_buffer(256)
        USER32.GetClassNameW(hwnd, buff, 256)
        return buff.value

    def _enum_window_check_callback(self, hwnd, lparam):
        """检测窗口的回调"""
        if not USER32.IsWindowVisible(hwnd):
            return True
            
        # 获取窗口标题
        length = USER32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
            
        buff = create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # 获取类名
        class_name = self._get_window_class(hwnd)
        
        # 过滤掉一些系统窗口或明显无关的窗口
        # Program Manager: 桌面
        # Shell_TrayWnd: 任务栏
        if not title or title == "Program Manager" or class_name == "Shell_TrayWnd":
            return True
            
        self._current_window_title = title
            
        # 枚举子窗口查找按钮
        USER32.EnumChildWindows(hwnd, EnumChildProc(self._enum_child_check_callback), 0)
        
        if self._found_target:
            return False # Stop enumeration
        return True

    def _enum_child_check_callback(self, hwnd, lparam):
        """检测子窗口（控件）的回调"""
        if not USER32.IsWindowVisible(hwnd):
            return True
            
        text = self._get_window_text(hwnd)
        if not text:
            return True
            
        text_lower = text.lower()
        
        for keyword in self.keywords:
            if keyword in text_lower:
                if any(ignore in text_lower for ignore in AutoInstallConfig.DONT_CLICK_KEYWORDS):
                    continue
                
                logger.debug(f"检测到潜在安装窗口: '{self._current_window_title}'，匹配控件: '{text}'，关键词: '{keyword}'")
                self._found_target = True
                return False
        return True

