#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: util.py
# @description: 通用工具函数模块，提供各种辅助功能

"""
通用工具函数模块
提供截图装饰器、缓存清理、参数处理等各种辅助功能
"""

import os
import time
import cv2
import functools
import pyautogui
import sys
import zipfile
import urllib.parse
import py7zr
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from utils.logger import logger
from core.process_manager import ProcessManager
from utils.exception_handler import ExceptionHandler, ElementNotFound, ProcessExecutionError
from config import (
    Paths, FileConfig, ProcessConfig, LogConfig, ConfigStructure, 
    Timing, ModuleConfig
)


def _extract_tool_directory(cmd_str: str) -> str:
    """
    从命令字符串中提取工具目录
    
    Args:
        cmd_str: 命令字符串
        
    Returns:
        工具目录路径
    """
    tool_dir = ''
    if cmd_str:
        segments = [seg.strip() for seg in cmd_str.split('&&')]
        for seg in reversed(segments):
            seg_stripped = seg.strip()
            lower = seg_stripped.lower()
            if lower.startswith('cd '):
                after_cd = seg_stripped[2:].strip()
                if after_cd.lower().startswith('/d '):
                    after_cd = after_cd[2:].strip()
                tool_dir = after_cd.strip('"').strip("'")
                break
    
    # 统一路径分隔符为当前系统的标准格式
    if tool_dir:
        tool_dir = os.path.normpath(tool_dir)
    
    return tool_dir


def _should_skip_database_deletion(tool_name: str, version_str: str) -> bool:
    """
    检查是否应该跳过数据库文件删除
    
    Args:
        tool_name: 工具名称
        version_str: 版本字符串
        
    Returns:
        是否跳过删除
    """
    # 检查是否在跳过删除的工具列表中
    if tool_name in ProcessConfig.SKIP_DB_DELETION_TOOLS:
        return True
    
    # 检查是否在特定版本的跳过列表中
    skip_versions = ProcessConfig.SKIP_DB_DELETION_VERSIONS.get(tool_name, [])
    return version_str in skip_versions


def screenshot_decorator(screenshot_dir: str = Paths.PROCESS_IMAGE_DIR) -> Callable:
    """
    截图装饰器，在函数执行前后进行截图并保存到指定文件夹
    
    :param screenshot_dir: 截图保存目录，默认为"screenshots"
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取程序所在目录
            program_dir = get_program_directory()
            
            # 构建完整的截图目录路径
            full_screenshot_dir = os.path.join(program_dir, screenshot_dir)
            
            # 确保截图目录存在
            if not os.path.exists(full_screenshot_dir):
                os.makedirs(full_screenshot_dir)
                logger.debug(f"创建截图目录: {full_screenshot_dir}")
            
            # 生成时间戳
            timestamp = datetime.now().strftime(FileConfig.TIMESTAMP_FORMAT)
            
            # 根据函数名和参数生成有意义的描述
            description = get_function_description(func.__name__, args, kwargs)
            
            # 函数执行前截图
            pre_screenshot_path = os.path.join(full_screenshot_dir, f"{timestamp}_{description}_执行前.png")
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save(pre_screenshot_path)
                logger.debug(f"函数 {func.__name__} 执行前截图已保存: {pre_screenshot_path}")
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行前截图失败: {str(e)}")
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 函数执行后截图
            post_screenshot_path = os.path.join(full_screenshot_dir, f"{timestamp}_{description}_执行后.png")
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save(post_screenshot_path)
                logger.debug(f"函数 {func.__name__} 执行后截图已保存: {post_screenshot_path}")
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行后截图失败: {str(e)}")
            
            return result
        return wrapper
    return decorator


def get_function_description(func_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
    """
    根据函数名和参数生成有意义的描述
    
    Args:
        func_name: 函数名
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        描述字符串
    """
    if func_name == "locate_image_and_click":
        # 对于图像定位点击函数，提取图像路径
        image_path = args[0] if args else kwargs.get("image_path", "")
        # 从图像路径中提取文件名（不包含扩展名）
        image_name = os.path.basename(image_path).split(".")[0] if image_path else "未知图像"
        click_flag = kwargs.get("click_flag", "left")
        return f"点击_{image_name}_{click_flag}"
    
    elif func_name == "input_action":
        # 对于输入命令函数，提取命令内容
        command = args[0] if args else kwargs.get("command", "")
        # 如果命令太长，截取前20个字符
        short_command = command[:20] + "..." if len(command) > 20 else command
        # 替换特殊字符，避免文件名问题
        short_command = "".join(c for c in short_command if c.isalnum() or c in " _-")
        return f"输入命令_{short_command}"
    
    elif func_name == "openAPP_action":
        # 对于打开应用函数，提取模块名或配置信息
        module_name = args[1] if len(args) > 1 else kwargs.get("module_name", "")
        if module_name:
            return f"打开应用_{module_name}"
        else:
            return "打开应用_未知模块"
    
    else:
        # 默认情况，只返回函数名
        return func_name


def clear_tool_cache(config: Dict[str, Any]) -> bool:
    """
    通用工具缓存清理
    
    1. 检查工具进程是否运行，如果运行则关闭
    2. 删除工具目录下的缓存文件（如data.db、cache目录等）
    
    Args:
        config: 配置对象
        
    Returns:
        清理结果
    """
    launch_config = config.get(ConfigStructure.LAUNCH_KEY, {})
    process_check = launch_config.get(ConfigStructure.PROCESS_CHECK_KEY, {})
    process_name = process_check.get(ConfigStructure.NAME_KEY, '')
    cmd_str = launch_config.get(ConfigStructure.CMD_KEY, '')
    
    tool_dir = _extract_tool_directory(cmd_str)
    
    # 检查工具进程是否运行
    logger.debug(f"检查工具进程状态: {process_name}")
    try:
        if ProcessManager.is_application_running(config):
            logger.debug("检测到工具进程正在运行，尝试关闭...")
            if ProcessManager.close_tool_process(config):
                logger.debug("工具进程已成功关闭")
            else:
                logger.warning("工具进程关闭失败，尝试强制终止")
                ProcessManager.kill_process_by_name(process_name)
            time.sleep(2)
        else:
            logger.debug("工具进程未运行，直接进行缓存清理")
    except Exception as e:
        logger.warning(f"检查或关闭工具进程时发生异常，继续执行缓存清理: {e}")
    
    # 删除缓存文件和目录
    if tool_dir and os.path.isdir(tool_dir):
        data_db = os.path.join(tool_dir, Paths.DATA_DB_FILE)

        # 检查是否需要保留data.db文件，某些工具不需要删除数据库文件
        tool_name = str(config.get('tool', '')).lower()
        version_str = str(config.get('version', '')).lower()
        should_skip_db_deletion = _should_skip_database_deletion(tool_name, version_str)
        
        if should_skip_db_deletion:
            logger.debug("检测到需要保留数据库文件的工具，跳过删除data.db文件")
        elif os.path.isfile(data_db):
            logger.debug(f"开始清理工具目录缓存: {tool_dir}")
            try:
                os.remove(data_db)
                logger.debug(f"已删除缓存文件: {data_db}")
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {e}")
                # 如果删除失败，尝试关闭占用文件的进程
                logger.debug("尝试关闭占用文件的进程...")
                if ProcessManager.close_processes_using_file(data_db):
                    logger.debug("已关闭占用文件的进程，尝试重新删除文件")
                    try:
                        os.remove(data_db)
                        logger.debug(f"成功删除缓存文件: {data_db}")
                    except Exception as e2:
                        logger.error(f"重试删除缓存文件仍然失败: {e2}")
                else:
                    logger.error("未能找到或关闭占用文件的进程")
    else:
        logger.warning("未找到工具目录，跳过缓存清理")
    return True


# ==== 用户输入的下拉框选项转换为对应的图像路径 ====
def process_dropdown_params(cli_params: Dict[str, Any], 
                           dropdown_options: Dict[str, Dict[str, str]], 
                           default_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    处理命令行中的下拉框参数，将用户输入的选项转换为对应的图像路径
    如果用户没有在命令行输入信息，则使用配置文件中的默认参数
    
    :param cli_params: 命令行参数字典
    :param dropdown_options: 下拉选项配置
    :param default_params: 默认参数配置
    :return: 处理后的参数字典，包含选项对应的图像路径
    """
    processed_params = dict(cli_params)
    
    # 遍历所有下拉选项类型
    for dropdown_key, options in dropdown_options.items():
        # 检查用户是否直接指定了下拉选项值（如 payload=java）
        if dropdown_key in cli_params:
            user_value = cli_params[dropdown_key]
            # 检查该值是否在选项配置中存在
            if user_value in options:
                # 设置选项值和对应的图像路径
                processed_params[f"{dropdown_key}_option"] = user_value
                processed_params[f"{dropdown_key}_option_image"] = options[user_value]
                logger.debug(f"用户指定下拉选项 {dropdown_key}={user_value}")
            else:
                logger.warning(f"下拉选项 {dropdown_key}={user_value} 无效，可用选项: {list(options.keys())}")
        else:
            # 用户没有指定该下拉选项，检查是否有默认值
            default_option_key = f"{dropdown_key}_option"
            if default_params and default_option_key in default_params:
                default_value = default_params[default_option_key]
                
                # 直接使用默认值进行匹配
                if default_value in options:
                    # 使用默认值
                    processed_params[default_option_key] = default_value
                    processed_params[f"{dropdown_key}_option_image"] = options[default_value]
                    # 只在最终确定使用默认值时输出日志
                    logger.debug(f"使用默认下拉选项 {dropdown_key}={default_value}")
                else:
                    logger.warning(f"默认下拉选项 {dropdown_key}={default_value} 无效，可用选项: {list(options.keys())}")
            elif default_params and dropdown_key in default_params:
                # 兼容处理：如果default_params中直接是dropdown_key而不是dropdown_key_option
                default_value = default_params[dropdown_key]
                
                # 直接使用默认值进行匹配
                if default_value in options:
                    # 使用默认值
                    processed_params[default_option_key] = default_value
                    processed_params[f"{dropdown_key}_option_image"] = options[default_value]
                    # 只在最终确定使用默认值时输出日志
                    logger.debug(f"使用默认下拉选项 {dropdown_key}={default_value}")
                else:
                    logger.warning(f"默认下拉选项 {dropdown_key}={default_value} 无效，可用选项: {list(options.keys())}")
    
    return processed_params


def get_program_directory() -> str:
    """
    获取程序所在目录，兼容打包的可执行文件和Python脚本
    
    Returns:
        程序所在目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 如果是Python脚本
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    
def get_config_file_path(tool: str, version: str) -> str:
    """
    获取配置文件的完整路径
    
    Args:
        tool: 工具名称
        version: 工具版本
        
    Returns:
        配置文件的完整路径
    """
    program_dir = get_program_directory()
    config_dir = os.path.join(program_dir, Paths.CONFIG_DIR)
    return os.path.join(config_dir, f"{tool}_{version}.yml")
    
    
# ==== 下拉框依赖限制处理逻辑 ====
def apply_dropdown_dependencies(final_params: Dict[str, Any], 
                               dropdown_dependencies: List[Dict[str, Any]], 
                               dropdown_options: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """
    通用下拉框依赖处理函数
    根据配置的依赖关系自动调整相关参数
    
    :param final_params: 最终参数字典（包含default_params和cli_params）
    :param dropdown_dependencies: 下拉框依赖配置列表
    :param dropdown_options: 下拉选项配置
    :return: 处理后的参数字典
    """
    params = dict(final_params)
    
    if not dropdown_dependencies:
        return params
    
    for dependency in dropdown_dependencies:
        source_key = dependency.get("source_key")
        target_key = dependency.get("target_key")
        mapping = dependency.get("mapping", {})
        
        if not source_key or not target_key or not mapping:
            continue
            
        # 获取源参数的当前值
        source_value = params.get(f"{source_key}_option")
        
        # 如果源参数有值且在映射中存在
        if source_value and source_value in mapping:
            allowed_values = mapping[source_value]
            target_value = params.get(f"{target_key}_option")
        
        
            # 检查目标参数的值是否在允许的列表中
            if target_value not in allowed_values and allowed_values:
                # 获取目标选项的配置
                target_options = dropdown_options.get(target_key, {})
                
                # 如果允许值中的第一个选项在目标选项中存在，则使用它
                if allowed_values[0] in target_options:
                    old_value = target_value
                    new_value = allowed_values[0]
                    params[f"{target_key}_option"] = new_value
                    # 同时更新对应的图像路径
                    if new_value in target_options:
                        params[f"{target_key}_option_image"] = target_options[new_value]
                    logger.debug(f"依赖关系调整: {target_key}_option 从 {old_value} 调整为 {new_value}")

    return params


# ==== 功能完成日志输出器 ====
def log_module_completion(module_name: Optional[str], cli_params: Optional[Dict[str, Any]]) -> None:
    """
    根据模块名称和参数信息，生成并输出功能完成日志
    """
    if not module_name:
        return
    
    # 生成模块完成日志
    completion_message = f"{module_name}功能模块自动化执行完毕"
    
    # 根据模块名称和参数信息，添加具体的参数信息
    if cli_params:
        param_info = []
        
        # 根据不同模块类型，选择性打印相关参数
        if "add_webshell" in module_name:
            if "url" in cli_params:
                param_info.append(f"已添加url={cli_params['url']}")
        elif "upload_file" in module_name:
            if "filepath" in cli_params:
                param_info.append(f"上传文件路径={cli_params['filepath']}")
            if "filename" in cli_params:
                param_info.append(f"上传文件名={cli_params['filename']}")
        elif "download_file" in module_name:
            if "filepath" in cli_params:
                param_info.append(f"已下载文件至={cli_params['filepath']}")
            if "filename" in cli_params:
                param_info.append(f"已下载文件名={cli_params['filename']}")
        elif "execute_commands" in module_name or "badpotato" in module_name:
            # 收集所有命令参数
            commands = []
            for i in range(1, 6):  # 支持command1到command5
                cmd_key = f"command{i}"
                if cmd_key in cli_params and cli_params[cmd_key].strip():
                    commands.append(cli_params[cmd_key].strip())
            if "command" in cli_params and cli_params["command"].strip():
                commands.append(cli_params["command"].strip())
            if commands:
                param_info.append(f"已执行命令={commands[0]}")  # 只显示第一个命令
        elif "scan_port" in module_name:
            if "host" in cli_params:
                param_info.append(f"已扫描主机={cli_params['host']}")
            if "ports" in cli_params:
                ports = cli_params.get("ports", "")
                if ports:
                    param_info.append(f"端口={ports}")
        elif "socks_proxy" in module_name or "open_proxy" in module_name or "close_proxy" in module_name:
            if "host" in cli_params:
                param_info.append(f"代理主机={cli_params['host']}")
            if "port" in cli_params or "ports" in cli_params:
                ports = cli_params.get("port", cli_params.get("ports", ""))
                if ports:
                    param_info.append(f"代理端口={ports}")
        elif "file_manger" in module_name:
            if "file_name" in cli_params:
                param_info.append(f"文件名={cli_params['file_name']}")
            if "file_path" in cli_params:
                param_info.append(f"文件路径={cli_params['file_path']}")
        elif "delete_webshell" in module_name:
            param_info.append("已删除webshell")
        elif "delete_memory" in module_name:
            param_info.append("已删除内存")
        elif "upload_memory" in module_name or "lanjun_memory" in module_name:
            param_info.append("已上传内存马")
        elif "add_url" in module_name:
            if "host" in cli_params:
                param_info.append(f"已添加数据库连接={cli_params['host']}")
            if "database" in cli_params:
                param_info.append(f"数据库类型={cli_params['database']}")
        elif "replace_key" in module_name:
            if "key_filepath" in cli_params:
                param_info.append(f"已替换公钥文件={cli_params['key_filepath']}")
            if "host" in cli_params:
                param_info.append(f"目标主机={cli_params['host']}")
        else:
            # 其他模块，打印所有非敏感参数
            for key, value in cli_params.items():
                # 跳过可能包含敏感信息的参数
                if key.lower() not in ["password", "pass", "pwd", "secret", "token", "key"]:
                    param_info.append(f"{key}={value}")
        
        # 如果有参数信息，添加到完成消息中
        if param_info:
            completion_message += "，" + "，".join(param_info)
    
    logger.info(completion_message)



def unzip_and_find_executable(file_path: str) -> str:
    """
    解压文件并查找可执行文件
    :param file_path: 压缩文件路径
    :return: 可执行文件路径，如果未找到或不是压缩文件则返回原路径
    """
    if not file_path or not os.path.exists(file_path):
        return file_path
        
    lower_path = file_path.lower()
    if not (lower_path.endswith('.zip') or lower_path.endswith('.7z')):
        return file_path
        
    # 获取文件名（不含扩展名）作为解压目录名
    file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
    # 获取父目录
    parent_dir = os.path.dirname(file_path)
    # 拼接解压目录路径：C:/Users/admin/Downloads/zip解压后目录/
    extract_dir = os.path.join(parent_dir, file_name_no_ext)
    
    # 确保解压目录存在
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    
    logger.info(f"开始解压样本文件: {file_path} 到 {extract_dir}")
    
    try:
        # 优先尝试使用 7-Zip 命令行解压（性能最佳）
        if not _try_unzip_with_command(file_path, extract_dir):
            # 回退到 Python 库解压
            if lower_path.endswith('.zip'):
                _unzip_zip_file(file_path, extract_dir)
            else:
                _unzip_7z_file(file_path, extract_dir)
            
        return find_executable_in_directory(extract_dir, file_path)
            
    except Exception as e:
        logger.error(f"解压或查找可执行文件失败: {e}")
        return file_path


def find_executable_in_directory(extract_dir: str, original_file_path: str) -> str:
    """
    在指定目录中查找可执行文件
    :param extract_dir: 查找目录
    :param original_file_path: 原始文件路径（用于未找到时返回）
    :return: 可执行文件路径
    """
    try:
        # 查找可执行文件
        executable_extensions = ['.exe', '.msi', '.lnk']
        found_executable = None
        candidates = []
        
        # 遍历解压目录查找所有候选文件
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in executable_extensions:
                    candidates.append(os.path.join(root, file))
        
        # 优先选择 .lnk 文件
        if candidates:
            lnk_files = [f for f in candidates if f.lower().endswith('.lnk')]
            if lnk_files:
                found_executable = lnk_files[0]
            else:
                found_executable = candidates[0]
                
        if found_executable:
            # 规范化路径分隔符
            found_executable = os.path.normpath(found_executable)
            logger.info(f"找到可执行文件: {found_executable}")
            return found_executable
        else:
            logger.warning("在压缩包中未找到可执行文件(.exe/.msi/.lnk)")
            return original_file_path
    except Exception as e:
        logger.error(f"查找可执行文件失败: {e}")
        return original_file_path


def _try_unzip_with_command(file_path: str, extract_dir: str) -> bool:
    """
    尝试使用系统安装的 7-Zip 命令行进行解压（速度远快于 Python 库）
    :param file_path: 压缩文件路径
    :param extract_dir: 解压目标目录
    :return: 是否成功
    """
    # 常见 7-Zip 安装路径
    seven_zip_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    
    seven_zip_exe = None
    # 检查环境变量
    if shutil.which("7z"):
        seven_zip_exe = "7z"
    else:
        # 检查常见安装路径
        for path in seven_zip_paths:
            if os.path.exists(path):
                seven_zip_exe = path
                break
    
    if not seven_zip_exe:
        return False
        
    try:
        logger.debug(f"尝试使用 7-Zip 命令行解压: {seven_zip_exe}")
        # 7z x "archive.zip" -o"C:\out" -y -aoa
        # -x: 完整路径解压
        # -o: 输出目录 (注意-o后面紧跟路径，无空格)
        # -y: 自动确认所有提示
        # -aoa: 覆盖所有文件
        cmd = [seven_zip_exe, "x", file_path, f"-o{extract_dir}", "-y", "-aoa"]
        
        # 隐藏命令行窗口
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        subprocess.check_call(cmd, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"使用 7-Zip 命令行成功解压: {file_path}")
        return True
    except Exception as e:
        logger.warning(f"7-Zip 命令行解压尝试失败，将回退到 Python 库: {e}")
        return False


def _unzip_zip_file(zip_file_path, downloads_dir):
    """
    解压zip文件到指定目录，保留压缩包原有的目录结构
    :param zip_file_path: zip文件路径
    :param downloads_dir: 目标目录
    """
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # 遍历zip文件中的所有文件和目录
        for file_info in zip_ref.infolist():
            # 处理文件名编码，解决中文乱码问题
            decoded_filename = _decode_filename(file_info.filename)
            
            # 构建完整的目标路径，保留目录结构
            target_path = os.path.join(downloads_dir, decoded_filename)
            
            # 如果是目录，创建目录
            if file_info.filename.endswith('/'):
                _prepare_target_path(target_path, is_dir=True)
            else:
                if _prepare_target_path(target_path, is_dir=False):
                    # 提取文件（使用流式复制，避免大文件占用过多内存）
                    with zip_ref.open(file_info) as source_file, open(target_path, 'wb') as target_file:
                        shutil.copyfileobj(source_file, target_file)
                    logger.debug(f"已提取文件: {target_path}")


def _unzip_7z_file(archive_file_path, downloads_dir):
    """
    解压7z文件到指定目录，保留压缩包原有的目录结构
    :param archive_file_path: 7z文件路径
    :param downloads_dir: 目标目录
    """
    try:
        # 使用py7zr库的正确方法：直接解压所有文件到目标目录
        with py7zr.SevenZipFile(archive_file_path, mode='r') as archive:
            # 首先解压到一个临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"创建临时解压目录: {temp_dir}")
                
                # 解压所有文件到临时目录
                archive.extractall(temp_dir)
                logger.debug(f"已解压文件到临时目录: {temp_dir}")
                
                # 遍历临时目录中的所有文件
                for root, dirs, files in os.walk(temp_dir):
                    # 处理所有目录，确保目录结构存在
                    for dir_name in dirs:
                        relative_path = os.path.relpath(os.path.join(root, dir_name), temp_dir)
                        target_path = os.path.join(downloads_dir, relative_path)
                        if not os.path.exists(target_path):
                            os.makedirs(target_path, exist_ok=True)
                            logger.debug(f"已创建目录: {target_path}")

                    # 处理所有文件
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        
                        # 处理文件名编码，解决中文乱码问题
                        decoded_filename = _decode_filename(file_name)
                        
                        # 获取相对路径
                        relative_dir_path = os.path.relpath(root, temp_dir)
                        if relative_dir_path == '.':
                            relative_dir_path = ''
                        
                        # 构建目标路径
                        target_path = os.path.join(downloads_dir, relative_dir_path, decoded_filename)
                        
                        if _prepare_target_path(target_path, is_dir=False):
                            # 移动文件到目标位置（比复制更快，尤其是在同一分区）
                            shutil.move(file_path, target_path)
                            logger.debug(f"已提取文件: {target_path}")

    except ImportError:
        logger.error("缺少py7zr库，无法解压7z文件。请运行: pip install py7zr")
        raise


def _decode_filename(filename: str) -> str:
    """
    尝试修复乱码文件名
    ZIP文件中的文件名通常是cp437编码，但对于中文系统，需要转换为GBK
    """
    try:
        # 尝试使用cp437解码再编码为GBK，解决中文乱码问题
        return filename.encode('cp437').decode('gbk')
    except (UnicodeEncodeError, UnicodeDecodeError):
        try:
            # 如果上述方法失败，尝试使用UTF-8解码
            return filename.encode('cp437').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                # 如果仍然失败，尝试直接使用GBK解码
                return filename.encode('cp437').decode('gbk', errors='replace')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果所有方法都失败，使用原始文件名
                return filename


def _prepare_target_path(target_path: str, is_dir: bool = False) -> bool:
    """
    准备目标路径：创建父目录，如果目标已存在则删除
    """
    try:
        if is_dir:
            if not os.path.exists(target_path):
                os.makedirs(target_path, exist_ok=True)
                logger.debug(f"已创建目录: {target_path}")
            return True

        # 确保文件的父目录存在
        parent_dir = os.path.dirname(target_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # 如果文件已存在，先删除（强制覆盖）
        if os.path.exists(target_path):
            try:
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
                logger.debug(f"已删除已存在文件: {target_path}")
            except Exception as e:
                logger.warning(f"删除文件失败: {target_path}, 错误: {str(e)}")
                return False
        return True
    except Exception as e:
        logger.error(f"准备目标路径失败: {target_path}, {e}")
        return False