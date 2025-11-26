#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: action.py
# @description: 预定义动作函数模块，提供各种自动化操作功能

import re
import pyautogui
import pyperclip
import subprocess
import time
import cv2
import pygetwindow as gw
import os
from typing import Tuple, Optional, List, Union, Dict, Any
from core.match_image import match_image
from utils.logger import logger
from core.process_manager import ProcessManager
from core.auto_installer import AutoInstaller
from utils.util import clear_tool_cache, screenshot_decorator, get_program_directory
from utils.exception_handler import ExceptionHandler, ElementNotFound, ProcessExecutionError, ResultParseError
from config import (
    ImageRecognition, Timing, UIConfig, NetworkConfig, FileConfig,
    Paths, LogConfig, ModuleConfig
)

# ==== 预定义执行函数 ====
@screenshot_decorator(screenshot_dir="screenshots/process_image")
@ExceptionHandler.handle_element_not_found_with_context("图像定位点击")
def click_action(image_path, confidence=0.8, click_offset=(0, 0), click_flag="left"):
    """
    通用图像定位并点击，匹配成功并点击返回True，未找到返回False。
    :param image_path: 模板截图路径
    :param confidence: 匹配置信度
    :param click_offset: 点击点相对左上角偏移
    :param click_flag: 点击类型，可选值：left, right, double
    :return: True 表示成功匹配并点击，False 表示未找到或匹配失败
    """
    # 如果image_path是相对路径，转换为基于程序所在目录的绝对路径
    if not os.path.isabs(image_path):
        # 获取程序所在目录
        program_dir = get_program_directory()
        
        # 检查路径是否已经包含 'images' 前缀
        if image_path.startswith('images/'):
            # 如果路径已经包含 images 前缀，直接使用程序目录作为基础
            image_path = os.path.join(program_dir, image_path)
        else:
            # 如果路径不包含 images 前缀，添加 images 目录
            images_dir = os.path.join(program_dir, 'images')
            image_path = os.path.join(images_dir, image_path)
    
    # 统一路径分隔符为当前系统的标准格式
    image_path = os.path.normpath(image_path)
    
    match_result = match_image(image_path)
    if match_result is None:
        raise ElementNotFound(element_name=image_path, message=f"无法加载图像模板: {image_path}")
    
    res, template = match_result
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= confidence:
        x, y = max_loc
        h, w = template.shape[:2]
        click_x = x + click_offset[0] + w // 2
        click_y = y + click_offset[1] + h // 2
        pyautogui.moveTo(click_x, click_y, duration=0.5)
        # 根据click_flag参数执行不同操作
        if click_flag == "left":
            pyautogui.click()
        elif click_flag == "right":
            pyautogui.rightClick()
        elif click_flag == "double":
            pyautogui.doubleClick()
        logger.debug(f"已点击 {image_path}，位置: ({click_x}, {click_y})，匹配度: {max_val:.2f}")
        
        # 记录点击位置，供后续截图操作使用
        set_last_click_position(click_x, click_y)
        
        return True
    else:
        raise ElementNotFound(element_name=image_path, message=f"未找到 {image_path}，最大匹配度: {max_val:.2f}")


@screenshot_decorator(screenshot_dir="screenshots/process_image")
def input_action(command, clear=True, enter=True, param_name=None):
    """
    模拟键盘输入命令
    :param command: 输入的命令字符串
    :param clear: 是否先清空输入框
    :param enter: 是否在输入后按回车键，默认为True
    :param param_name: 参数名称，用于识别是否为down_url参数
    :return: 成功返回(True, download_url)，失败返回(False, None)
    """
    try:
        # 检查是否为down_url参数，并且文件扩展名为zip
        is_down_url = param_name == "down_url"
        is_zip_file = is_down_url and (command.lower().endswith('.zip') or command.lower().endswith('.7z'))
        
        # 保存下载URL信息，用于后续可能的解压操作
        download_url = None
        if is_down_url:
            download_url = command
            logger.debug(f"检测到down_url参数: {download_url}")
        
        if clear:
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
        
        # 导入pyperclip模块，用于复制粘贴
        try:
            import pyperclip
        except ImportError:
            pyperclip = None
        
        # 处理长文本中的换行符问题
        # 如果命令中包含换行符，需要特殊处理以避免意外的回车行为
        if '\n' in command:
            logger.debug("检测到命令中包含换行符，使用逐字符输入模式避免意外回车")
            # 对于包含换行符的长文本，使用逐字符输入模式
            # 将换行符转换为实际的换行操作，但只在需要时才按回车
            for char in command:
                if char == '\n':
                    # 如果是换行符，按下回车键
                    pyautogui.press('enter')
                else:
                    # 普通字符直接输入
                    pyautogui.typewrite(char, interval=0.01)
                # 短暂延迟以确保输入稳定
                time.sleep(0.01)
        else:
            # 使用剪贴板输入命令（适用于不包含换行符的普通文本）
            if pyperclip:
                pyperclip.copy(command)
                pyautogui.hotkey('ctrl', 'v')
            else:
                # 如果没有pyperclip，则直接输入命令
                pyautogui.typewrite(command, interval=0.03)
        
        # 根据enter参数决定是否按回车键
        if enter:
            pyautogui.press('enter')
            logger.debug(f"已输入并执行命令: {command[:100]}{'...' if len(command) > 100 else ''}")
        else:
            logger.debug(f"已输入命令（未按回车）: {command[:100]}{'...' if len(command) > 100 else ''}")
        
        # 返回执行结果和下载URL（如果需要解压）
        return True, download_url if is_zip_file else None
    except Exception as e:
        logger.error(f"输入命令失败: {str(e)}")
        return False, None


@screenshot_decorator(screenshot_dir="screenshots/process_image")
@ExceptionHandler.handle_process_execution
def openAPP_action(config, module_name=None, skip_process_check=None):
    """
    从配置对象的launch部分获取命令并执行。
    针对add_webshell模块，先清理缓存再重启工具。
    """
    if not config:
        raise ProcessExecutionError(process_name="未知进程", message="配置对象为空")

    launch_config = config.get('launch', {})
    if not launch_config:
        raise ProcessExecutionError(process_name="未知进程", message="配置文件中缺少launch配置")

    # 判断是否为add_webshell模块
    if module_name == "add_webshell":
        logger.debug("检测到add_webshell模块，执行缓存清理与重启流程")
        # 清理缓存data.db文件，然后继续执行启动流程
        try:
            clear_tool_cache(config)
        except Exception as e:
            logger.warning(f"清理缓存时发生异常，但继续执行启动流程: {e}")

    # 普通流程
    # 如果skip_process_check为True，则跳过程序运行检测
    if not skip_process_check and ProcessManager.is_application_running(config):
        logger.debug("应用程序已在运行")
        return True

    cmd = launch_config.get('cmd', '')
    pause_time = launch_config.get('pause', 3)
    if not cmd:
        raise ProcessExecutionError(process_name="未知进程", message="launch配置中缺少cmd命令")

    logger.debug(f"执行命令: {cmd}")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.Popen(
        cmd,
        startupinfo=startupinfo,
        shell=True
    )
    time.sleep(pause_time)
    time.sleep(8)
    return True


def window_maximize():
    """
    最大化当前活动窗口
    :return: 操作成功返回True，失败返回False
    """
    try:
        # 获取当前活动窗口
        active_window = gw.getActiveWindow()
        if active_window is None:
            logger.warning("未找到活动窗口，无法最大化")
            return False
            
        window_title = active_window.title
        
        # 最大化窗口
        active_window.maximize()
        logger.debug(f"已最大化窗口: {window_title}")
        
        # 操作后延时
        time.sleep(0.5)
        return True
        
    except Exception as e:
        logger.error(f"最大化当前活动窗口失败: {str(e)}")
        return False


def window_minimize():
    """
    最小化当前活动窗口
    :return: 操作成功返回True，失败返回False
    """
    try:
        # 获取当前活动窗口
        active_window = gw.getActiveWindow()
        if active_window is None:
            logger.warning("未找到活动窗口，无法最小化")
            return False
            
        window_title = active_window.title
        
        # 最小化窗口
        active_window.minimize()
        logger.debug(f"已最小化窗口: {window_title}")
        
        # 操作后延时
        time.sleep(0.5)
        return True
        
    except Exception as e:
        logger.error(f"最小化当前活动窗口失败: {str(e)}")
        return False


@ExceptionHandler.handle_result_parse_with_context("文本输出")
def text_output():
    """
    全选命令输出区域，复制输出信息，并使用正则表达式提取IP地址
    返回提取到的IP地址列表，如果没有找到则返回空列表
    """
    try:
        # 全选命令输出区域 (Ctrl+A)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        
        # 复制选中的内容 (Ctrl+C)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.5)
        
        # 从剪贴板获取复制的内容
        clipboard_content = pyperclip.paste()
        if not clipboard_content or len(clipboard_content.strip()) == 0:
            raise ResultParseError(result_type="剪贴板内容为空", message="无法从剪贴板获取有效内容")
        
        logger.info(f"输出内容: {clipboard_content}")
        
        # 使用正则表达式提取IP地址
        # 匹配IPv4地址格式
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ip_addresses = re.findall(ip_pattern, clipboard_content)
        
        # 如果没有找到IP地址格式，直接返回空列表
        if not ip_addresses:
            logger.debug("未在输出内容中找到IP地址格式，返回空列表")
            return []
        
        # 过滤掉无效的IP地址（如255.255.255.255, 0.0.0.0等）
        valid_ips = []
        for ip in ip_addresses:
            parts = ip.split('.')
            if len(parts) == 4:
                valid = True
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        valid = False
                        break
                if valid and ip not in ['0.0.0.0', '255.255.255.255']:
                    valid_ips.append(ip)
        
        # 如果没有有效的IP地址，返回空列表
        if not valid_ips:
            logger.debug("未找到有效的IP地址，返回空列表")
            return []
        
        logger.info(f"成功提取到IP地址: {valid_ips}")
        return valid_ips
        
    except ResultParseError:
        raise  # 重新抛出结果解析异常，让上层处理
    except Exception as e:
        error_msg = f"文本输出解析过程中发生错误: {str(e)}"
        logger.error(error_msg)
        raise ResultParseError(result_type="文本输出", message=error_msg) from e


@ExceptionHandler.handle_result_parse_with_context("图像输出")
def image_output():
    """
    放大当前活动窗口并截取屏幕图片保存在screenshots文件夹下的res_image文件夹下
    :return: 成功返回True，失败返回False
    """
    try:
        # 截取屏幕图片
        screenshot = pyautogui.screenshot()
        
        if screenshot is None:
            raise ResultParseError(result_type="截图获取", message="无法获取屏幕截图")
        
        # 创建保存目录路径
        # 获取程序所在目录
        program_dir = get_program_directory()
        
        save_dir = os.path.join(program_dir, "screenshots/res_image")
        
        # 如果目录不存在，则创建目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            logger.debug(f"已创建目录: {save_dir}")
        
        # 生成带时间戳的文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)
        
        # 保存截图
        try:
            screenshot.save(filepath)
        except Exception as save_error:
            raise ResultParseError(result_type="截图保存", message=f"保存截图失败: {str(save_error)}")
        
        # 验证文件是否成功保存
        if not os.path.exists(filepath):
            raise ResultParseError(result_type="文件验证", message=f"截图文件未成功保存到: {filepath}")
        
        logger.info(f"输出结果截图已保存到: {filepath}")
        
        return True
        
    except ResultParseError:
        raise  # 重新抛出结果解析异常，让上层处理
    except Exception as e:
        error_msg = f"图像输出过程中发生错误: {str(e)}"
        logger.error(error_msg)
        raise ResultParseError(result_type="图像输出", message=error_msg) from e

# 全局变量，用于存储上一次点击的位置
_last_click_position = None


def set_last_click_position(x, y):
    """
    设置上一次点击的位置坐标
    :param x: x坐标
    :param y: y坐标
    """
    global _last_click_position
    _last_click_position = (x, y)
    logger.debug(f"已记录上一次点击位置: ({x}, {y})")


def get_last_click_position():
    """
    获取上一次点击的位置坐标
    :return: (x, y) 坐标元组，如果没有记录则返回None
    """
    global _last_click_position
    return _last_click_position


@screenshot_decorator(screenshot_dir="screenshots/process_image")
@ExceptionHandler.handle_result_parse_with_context("截图操作")
def screenshot_action(size=None, use_last_click_position=True, screenshot_path=None):
    """
    从指定位置截取指定大小的图片
    :param size: 截图大小 [width, height]
    :param use_last_click_position: 是否使用上一次点击的位置作为起始位置
    :param screenshot_path: 截图保存路径
    :return: 成功返回保存的图片路径，失败返回False
    """
    try:
        # 处理size参数
        if size is None:
            size = [100, 100]  # 默认大小
        elif isinstance(size, str):
            # 如果是字符串，尝试解析为列表
            try:
                import ast
                size = ast.literal_eval(size)
            except:
                size = [100, 100]
        
        if len(size) != 2:
            raise ResultParseError(result_type="参数解析", message=f"size参数格式错误，应为[width, height]，实际为: {size}")
        
        width, height = int(size[0]), int(size[1])
        
        # 确定起始位置
        if use_last_click_position:
            start_pos = get_last_click_position()
            if start_pos is None:
                raise ResultParseError(result_type="位置获取", message="use_last_click_position为True，但没有记录上一次点击位置")
            start_x, start_y = start_pos
        else:
            # 如果不使用上一次点击位置，则使用屏幕中心作为起始位置
            screen_width, screen_height = pyautogui.size()
            start_x = (screen_width - width) // 2
            start_y = (screen_height - height) // 2
        
        # 截取指定区域的屏幕
        screenshot = pyautogui.screenshot(region=(start_x, start_y, width, height))
        
        if screenshot is None:
            raise ResultParseError(result_type="截图获取", message="无法获取屏幕截图")
        
        # 处理保存路径
        if screenshot_path is None:
            # 如果没有指定保存路径，使用默认路径
            program_dir = get_program_directory()
            
            save_dir = os.path.join(program_dir, "screenshots/screenshot_action")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(save_dir, filename)
        else:
            # 处理相对路径
            if not os.path.isabs(screenshot_path):
                program_dir = get_program_directory()
                
                # 检查路径是否已经包含 'images' 前缀
                if screenshot_path.startswith('images/'):
                    filepath = os.path.join(program_dir, screenshot_path)
                else:
                    images_dir = os.path.join(program_dir, 'images')
                    filepath = os.path.join(images_dir, screenshot_path)
            else:
                filepath = screenshot_path
            
            # 确保目录存在
            dir_path = os.path.dirname(filepath)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # 统一路径分隔符
        filepath = os.path.normpath(filepath)
        
        # 保存截图
        try:
            screenshot.save(filepath)
        except Exception as save_error:
            raise ResultParseError(result_type="截图保存", message=f"保存截图失败: {str(save_error)}")
        
        # 验证文件是否成功保存
        if not os.path.exists(filepath):
            raise ResultParseError(result_type="文件验证", message=f"截图文件未成功保存到: {filepath}")
        
        logger.debug(f"截图已保存到: {filepath}")
        
        # 返回保存的路径，供后续步骤使用
        return filepath
        
    except ResultParseError:
        raise  # 重新抛出结果解析异常，让上层处理
    except Exception as e:
        error_msg = f"截图操作过程中发生错误: {str(e)}"
        logger.error(error_msg)
        raise ResultParseError(result_type="截图操作", message=error_msg) from e



@ExceptionHandler.handle_element_not_found_with_context("图像识别")
def recognize_template(image_path, confidence=0.8, silent=False):
    """
    识别图像模板，返回True表示找到，False表示未找到
    :param image_path: 图像路径
    :param confidence: 匹配置信度
    :param silent: 静默模式，失败时返回False而不是抛出异常
    :return: True表示找到，False表示未找到
    """
    # 如果image_path是相对路径，转换为基于程序所在目录的绝对路径
    if not os.path.isabs(image_path):
        # 获取程序所在目录
        program_dir = get_program_directory()
        
        # 检查路径是否已经包含 'images' 前缀
        if image_path.startswith('images/'):
            # 如果路径已经包含 images 前缀，直接使用程序目录作为基础
            image_path = os.path.join(program_dir, image_path)
        else:
            # 如果路径不包含 images 前缀，添加 images 目录
            images_dir = os.path.join(program_dir, 'images')
            image_path = os.path.join(images_dir, image_path)
    
    # 统一路径分隔符为当前系统的标准格式
    image_path = os.path.normpath(image_path)
    
    match_result = match_image(image_path, silent=silent)
    if match_result is None:
        if silent:
            logger.debug(f"无法加载或匹配图像模板: {image_path}")
            return False
        raise ElementNotFound(element_name=image_path, message=f"无法加载图像模板: {image_path}")
    
    res, template = match_result
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= confidence:
        logger.debug(f"识别到图像 {image_path}，匹配度: {max_val:.2f}")
        return True
    else:
        if silent:
            logger.debug(f"未识别到图像 {image_path}，最大匹配度: {max_val:.2f}")
            return False
        raise ElementNotFound(element_name=image_path, message=f"未识别到图像 {image_path}，最大匹配度: {max_val:.2f}")


@screenshot_decorator(screenshot_dir=Paths.PROCESS_IMAGE_DIR)
def keyboard_action(keys: Union[str, List[str]], 
                   duration: Optional[float] = None,
                   action_type: str = "hotkey") -> bool:
    """
    通用键盘操作函数，支持快捷键、长按单键等操作
    
    Args:
        keys: 按键或按键组合
            - 单个按键: "backspace", "left", "right", "up", "down", "enter" 等
            - 快捷键组合: ["win", "r"] 或 "win,r"
        duration: 长按持续时间（秒），仅在action_type为"press"时有效
        action_type: 操作类型
            - "hotkey": 快捷键组合（默认）
            - "press": 长按单键
            
    Returns:
        操作成功返回True，失败返回False
        
    Examples:
        # 快捷键组合
        keyboard_action(["win", "r"])  # Win+R
        keyboard_action("ctrl,c")      # Ctrl+C
        
        # 长按单键
        keyboard_action("backspace", duration=3, action_type="press")  # 长按backspace 3秒
        keyboard_action("right", duration=5, action_type="press")      # 长按右键 5秒
    """
    try:
        # 参数处理
        if isinstance(keys, str):
            if action_type == "hotkey" and "," in keys:
                # 快捷键字符串解析
                keys = [k.strip() for k in keys.split(',')]
            elif action_type == "press":
                # 单键长按
                keys = keys.strip()
            else:
                # 默认为单个按键
                keys = keys.strip()
        
        if action_type == "hotkey":
            return _execute_hotkey(keys)
        elif action_type == "press":
            return _execute_long_press(keys, duration or 1)
        else:
            logger.error(f"不支持的操作类型: {action_type}")
            return False
            
    except Exception as e:
        logger.error(f"键盘操作失败: {str(e)}")
        return False


def _execute_hotkey(keys: Union[str, List[str]]) -> bool:
    """执行快捷键操作"""
    if isinstance(keys, str):
        keys = [keys]
    
    pyautogui.hotkey(*keys)
    time.sleep(Timing.HOTKEY_OPERATION_DELAY)
    logger.debug(f"快捷键操作完成: {'+'.join(keys)}")
    return True


def _execute_long_press(key: str, duration: float) -> bool:
    """执行长按操作"""
    # 验证按键是否支持
    supported_keys = {
        "backspace", "left", "right", "up", "down", 
        "enter", "space", "tab", "delete", "home", "end"
    }
    
    if key not in supported_keys:
        logger.warning(f"按键 {key} 可能不被支持，但仍尝试执行")
    
    # 使用多次按键模拟长按效果
    end_time = time.time() + duration
    press_interval = Timing.MOVE_KEY_PRESS_INTERVAL
    
    while time.time() < end_time:
        pyautogui.press(key)
        time.sleep(press_interval)
    
    logger.debug(f"长按操作完成: {key}, 持续时间: {duration}秒")
    return True


@ExceptionHandler.handle_result_parse_with_context("输出反馈")
def output_action(text: str, cli_params: Dict[str, Any] = None) -> bool:
    """
    输出反馈信息，支持参数替换
    :param text: 要输出的文本，可包含 {参数名} 形式的占位符
    :param cli_params: 命令行参数字典，用于参数替换
    :return: 成功返回True，失败返回False
    """
    try:
        if cli_params is None:
            cli_params = {}
        
        # 处理文本中的参数占位符
        # 使用正则表达式找到所有 {参数名} 形式的占位符
        import re
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, text)
        
        # 替换占位符
        for param_name in matches:
            # 优先使用cli_params中的值
            if param_name in cli_params:
                param_value = cli_params[param_name]
            else:
                # 如果cli_params中没有，保留原始占位符
                param_value = f"{{{param_name}}}"
            
            # 替换文本中的占位符
            text = text.replace(f"{{{param_name}}}", str(param_value))
        
        # 输出处理后的文本
        logger.info(f"输出反馈: {text}")
        
        return True
        
    except Exception as e:
        error_msg = f"输出反馈过程中发生错误: {str(e)}"
        logger.error(error_msg)
        raise ResultParseError(result_type="输出反馈", message=error_msg) from e


@ExceptionHandler.handle_process_execution
def auto_install_action(keywords=None, finish_keywords=None, max_retries=30, interval=2.0):
    """
    执行自动化安装操作
    :param keywords: 点击关键词列表
    :param finish_keywords: 结束关键词列表
    :param max_retries: 最大重试次数
    :param interval: 检测间隔
    :return: 成功返回True，失败返回False
    """
    installer = AutoInstaller(
        keywords=keywords,
        finish_keywords=finish_keywords,
        max_retries=max_retries,
        interval=interval
    )
    return installer.start()


def wait_action(duration: float) -> bool:
    """
    等待指定时间
    :param duration: 等待时间（秒）
    :return: True
    """
    logger.info(f"等待 {duration} 秒...")
    time.sleep(duration)
    return True


