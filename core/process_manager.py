#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18
# @filename: process_manager.py
# @description: 进程管理模块，提供进程检测、关闭和终止功能

"""
进程管理模块
提供进程检测、关闭和终止功能，支持多种工具的进程管理
"""

import os
import time
import psutil
import pygetwindow as gw
import win32process
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass

from utils.logger import logger
from utils.exception_handler import ExceptionHandler, ProcessExecutionError, ToolCrash
from config import ProcessConfig, Timing, LogConfig, ModuleConfig


@dataclass
class ProcessInfo:
    """进程信息数据类"""
    pid: int
    name: str
    cmdline: str


@dataclass
class MatchCriteria:
    """匹配条件数据类"""
    tool_name: str
    version_str: str
    process_name: str
    keywords: List[str]
    jar_keywords: List[str]
    use_java: bool


class ProcessMatcher:
    """进程匹配器类"""
    
    @staticmethod
    def extract_jar_keywords(cmd: str) -> List[str]:
        """
        从启动命令中提取JAR关键字
        
        Args:
            cmd: 启动命令字符串
            
        Returns:
            JAR关键字列表
        """
        jar_keywords = []
        try:
            # 提取所有形如 -jar xxx.jar 的片段
            parts = cmd.split()
            for idx, token in enumerate(parts):
                if token == '-jar' and idx + 1 < len(parts):
                    jar_path = parts[idx + 1]
                    if jar_path.endswith('.jar'):
                        jar_keywords.append(os.path.basename(jar_path))
        except Exception:
            pass
        return jar_keywords
    
    @staticmethod
    def build_match_keywords(criteria: MatchCriteria) -> Set[str]:
        """
        构建匹配关键字集合
        
        Args:
            criteria: 匹配条件
            
        Returns:
            匹配关键字集合
        """
        tool_alias = ProcessConfig.TOOL_NAME_MAPPING.get(criteria.tool_name, criteria.tool_name)
        
        match_keywords = set()
        for k in [criteria.tool_name, tool_alias, criteria.version_str] + criteria.keywords + criteria.jar_keywords:
            if k:
                match_keywords.add(str(k).lower())
        
        return match_keywords
    
    @staticmethod
    def is_java_process_match(proc_info: ProcessInfo, match_keywords: Set[str]) -> bool:
        """
        检查是否为匹配的Java进程
        
        Args:
            proc_info: 进程信息
            match_keywords: 匹配关键字集合
            
        Returns:
            是否匹配
        """
        if proc_info.name.lower() in ProcessConfig.JAVA_PROCESS_NAMES:
            return any(k in proc_info.cmdline.lower() for k in match_keywords)
        return False
    
    @staticmethod
    def is_non_java_process_match(proc_info: ProcessInfo, process_name: str, match_keywords: Set[str]) -> bool:
        """
        检查是否为匹配的非Java进程
        
        Args:
            proc_info: 进程信息
            process_name: 进程名称
            match_keywords: 匹配关键字集合
            
        Returns:
            是否匹配
        """
        if not process_name or not proc_info.name:
            return False
        
        proc_name_lower = proc_info.name.lower()
        process_name_lower = process_name.lower()
        
        if proc_name_lower == process_name_lower or process_name_lower in proc_name_lower:
            # 如果提供了额外关键字，则需要命令行至少命中一个
            if match_keywords:
                return any(k in proc_info.cmdline.lower() for k in match_keywords) or not proc_info.cmdline
            else:
                return True
        return False


class ProcessTerminator:
    """进程终止器类"""
    
    @staticmethod
    def terminate_process_gracefully(proc: psutil.Process) -> bool:
        """
        优雅地终止进程
        
        Args:
            proc: 进程对象
            
        Returns:
            是否成功终止
        """
        try:
            # 优雅关闭
            proc.terminate()
        except psutil.AccessDenied:
            logger.warning(f"无权限 terminate 进程: PID {proc.pid}")
            return False
        except psutil.NoSuchProcess:
            return True  # 进程已不存在，视为成功
        
        # 等待退出，超时则强制终止
        try:
            proc.wait(timeout=Timing.PROCESS_TERMINATE_TIMEOUT)
            logger.debug(f"已终止进程: {proc.name()} (PID: {proc.pid})")
            return True
        except (psutil.TimeoutExpired, psutil.NoSuchProcess):
            try:
                proc.kill()
                logger.debug(f"已强制终止进程: {proc.name()} (PID: {proc.pid})")
                return True
            except Exception as e:
                logger.warning(f"强制终止进程失败: PID {proc.pid}, 错误: {e}")
                return False


class WindowManager:
    """窗口管理器类"""
    
    @staticmethod
    def find_window_by_pid(target_pid: int) -> Optional[Any]:
        """
        通过PID查找窗口
        
        Args:
            target_pid: 目标进程ID
            
        Returns:
            找到的窗口对象或None
        """
        windows = gw.getAllWindows()
        
        for win in windows:
            try:
                hwnd = win._hWnd if hasattr(win, '_hWnd') else win._getWindowHandle()
                pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                
                # 检查是否是匹配进程的窗口
                if pid == target_pid and win.title:
                    logger.debug(f"通过PID找到匹配窗口: {win.title}, PID={pid}")
                    return win
            except Exception as e:
                logger.error(f"检查PID窗口失败: {e}")
        
        return None
    
    @staticmethod
    def find_window_by_title(tool_name: str, version_str: str, require_version_match: bool) -> Optional[Any]:
        """
        通过标题查找窗口
        
        Args:
            tool_name: 工具名称
            version_str: 版本字符串
            require_version_match: 是否需要版本匹配
            
        Returns:
            找到的窗口对象或None
        """
        tool_alias = ProcessConfig.TOOL_NAME_MAPPING.get(tool_name, tool_name)
        false_positive_processes = ProcessConfig.FALSE_POSITIVE_PROCESSES
        false_positive_patterns = ProcessConfig.FALSE_POSITIVE_PATTERNS
        
        # 添加工具特定的误判模式（防止配置文件窗口被误识别）
        tool_false_patterns = [f"{tool_name}.yml", f"{tool_name}_{version_str}.yml"]
        
        windows = gw.getAllWindows()
        for win in windows:
            try:
                if not win.title:
                    continue
                
                # 排除常见误判窗口
                if WindowManager._should_skip_window(win, false_positive_patterns, tool_false_patterns, false_positive_processes):
                    continue
                
                # 进行工具名和版本匹配
                title_lower = win.title.lower()
                tool_match = (tool_name in title_lower) or (str(tool_alias).lower() in title_lower)
                version_match = not require_version_match or (str(version_str) in title_lower)
                
                if tool_match and version_match:
                    hwnd = win._hWnd if hasattr(win, '_hWnd') else win._getWindowHandle()
                    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                    logger.debug(f"通过标题找到匹配窗口: {win.title}, PID={pid}")
                    return win
                    
            except Exception as e:
                logger.error(f"检查标题窗口失败: {e}")
        
        return None
    
    @staticmethod
    def _should_skip_window(win: Any, false_positive_patterns: List[str], 
                          tool_false_patterns: List[str], false_positive_processes: Set[str]) -> bool:
        """
        检查是否应该跳过该窗口
        
        Args:
            win: 窗口对象
            false_positive_patterns: 常见误判模式
            tool_false_patterns: 工具特定误判模式
            false_positive_processes: 误判进程集合
            
        Returns:
            是否应该跳过
        """
        title_lower = win.title.lower()
        
        # 检查是否包含常见误判模式
        for pattern in false_positive_patterns:
            if pattern in title_lower:
                logger.debug(f"跳过包含常见误判模式的窗口: {win.title}")
                return True
        
        # 检查是否包含工具特定的误判模式
        for pattern in tool_false_patterns:
            if pattern in title_lower:
                logger.debug(f"跳过工具特定误判窗口: {win.title}")
                return True
        
        # 检查窗口进程是否在误判名单中
        try:
            hwnd = win._hWnd if hasattr(win, '_hWnd') else win._getWindowHandle()
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            proc = psutil.Process(pid)
            proc_name = proc.name().lower()
            if proc_name in false_positive_processes:
                logger.debug(f"跳过常见进程窗口: {win.title} ({proc_name})")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return False
    
    @staticmethod
    def activate_and_maximize_window(win: Any) -> None:
        """
        激活并最大化窗口
        
        Args:
            win: 窗口对象
        """
        win.restore()
        win.activate()
        time.sleep(0.5)


class ProcessDetector:
    """进程检测器类"""
    
    @staticmethod
    def find_matching_process(criteria: MatchCriteria) -> Optional[Tuple[int, str]]:
        """
        查找匹配的进程
        
        Args:
            criteria: 匹配条件
            
        Returns:
            匹配的进程信息元组(PID, 进程名)或None
        """
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = ProcessInfo(
                    pid=proc.info['pid'],
                    name=proc.info['name'],
                    cmdline=' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                )
                
                match_keywords = ProcessMatcher.build_match_keywords(criteria)
                
                # 检查是否匹配
                if ProcessDetector._is_process_match(proc_info, criteria, match_keywords):
                    logger.debug(f"找到匹配进程: {proc_info.name}, PID={proc_info.pid}, "
                               f"命令行: {proc_info.cmdline[:LogConfig.CMDLINE_TITLE_DISPLAY_LENGTH]}...")
                    return proc_info.pid, proc_info.name
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return None
    
    @staticmethod
    def _is_process_match(proc_info: ProcessInfo, criteria: MatchCriteria, match_keywords: Set[str]) -> bool:
        """
        检查进程是否匹配条件
        
        Args:
            proc_info: 进程信息
            criteria: 匹配条件
            match_keywords: 匹配关键字集合
            
        Returns:
            是否匹配
        """
        # 如果使用Java启动，检查java.exe进程
        if criteria.use_java:
            return ProcessMatcher.is_java_process_match(proc_info, match_keywords)
        
        # 如果配置了进程检查，使用进程名称和关键字匹配
        elif criteria.process_name:
            return ProcessMatcher.is_non_java_process_match(proc_info, criteria.process_name, match_keywords)
        
        # 如果没有配置进程检查，使用工具名匹配
        else:
            tool_alias = ProcessConfig.TOOL_NAME_MAPPING.get(criteria.tool_name, criteria.tool_name)
            proc_name_lower = proc_info.name.lower()
            return (criteria.tool_name in proc_name_lower or 
                   (tool_alias and str(tool_alias).lower() in proc_name_lower))


class ProcessManager:
    """进程管理类，提供进程检测、关闭和终止功能"""
    
    def __init__(self):
        """初始化进程管理器"""
        self.matcher = ProcessMatcher()
        self.terminator = ProcessTerminator()
        self.window_manager = WindowManager()
        self.detector = ProcessDetector()
    
    @staticmethod
    @ExceptionHandler.handle_process_execution
    def close_tool_process(config: Dict[str, Any]) -> bool:
        """
        通用工具进程关闭函数：
        - 若进程为 java/javaw，则基于命令行中的 JAR 名称与关键字匹配
        - 否则按配置的进程名精确匹配
        优先 terminate，超时则 kill。
        
        Args:
            config: 工具配置字典
            
        Returns:
            是否成功关闭进程
        """
        manager = ProcessManager()
        return manager._close_tool_process_impl(config)
    
    def _close_tool_process_impl(self, config: Dict[str, Any]) -> bool:
        """关闭工具进程的具体实现"""
        # 解析配置参数
        criteria = self._parse_close_criteria(config)
        
        if not criteria.process_name and not criteria.use_java:
            raise ProcessExecutionError(
                process_name="未知进程", 
                message="缺少进程名，且启动命令不包含java，无法匹配进程"
            )
        
        # 构建匹配关键字
        match_keywords = ProcessMatcher.build_match_keywords(criteria)
        
        # 查找并终止匹配的进程
        return self._terminate_matching_processes(criteria, match_keywords)
    
    def _parse_close_criteria(self, config: Dict[str, Any]) -> MatchCriteria:
        """解析关闭进程的条件"""
        launch_config = config.get('launch', {})
        process_check = launch_config.get('process_check', {})
        
        tool_name = str(config.get('tool') or '').lower()
        version_str = str(config.get('version') or '').lower()
        process_name = str(process_check.get('name') or '').lower()
        keywords_from_cfg = [str(k).lower() for k in process_check.get('keywords', [])]
        cmd = str(launch_config.get('cmd') or '').lower()
        
        # 从启动命令中提取JAR关键字
        jar_keywords = ProcessMatcher.extract_jar_keywords(cmd)
        
        return MatchCriteria(
            tool_name=tool_name,
            version_str=version_str,
            process_name=process_name,
            keywords=keywords_from_cfg,
            jar_keywords=jar_keywords,
            use_java='java' in cmd
        )
    
    def _terminate_matching_processes(self, criteria: MatchCriteria, match_keywords: Set[str]) -> bool:
        """终止匹配的进程"""
        terminated_any = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = ProcessInfo(
                    pid=proc.info['pid'],
                    name=proc.info['name'].lower(),
                    cmdline=' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                )
                
                # 检查是否为候选进程
                if not self._is_candidate_process(proc_info, criteria, match_keywords):
                    continue
                
                logger.debug(f"匹配到候选进程: {proc_info.name} (PID: {proc_info.pid}), "
                           f"cmd: {proc_info.cmdline[:LogConfig.CMDLINE_DISPLAY_LENGTH]}...")
                
                # 终止进程
                if ProcessTerminator.terminate_process_gracefully(proc):
                    terminated_any = True
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if terminated_any:
            time.sleep(Timing.PROCESS_CLOSE_WAIT)
            return True
        else:
            logger.warning("未匹配到需要关闭的目标进程")
            return False
    
    def _is_candidate_process(self, proc_info: ProcessInfo, criteria: MatchCriteria, match_keywords: Set[str]) -> bool:
        """检查是否为候选进程"""
        # Java进程匹配：依赖jar名称或关键字
        if ProcessMatcher.is_java_process_match(proc_info, match_keywords):
            return True
        
        # 非Java进程：按进程名匹配
        if ProcessMatcher.is_non_java_process_match(proc_info, criteria.process_name, match_keywords):
            return True
        
        return False
    
    @staticmethod
    @ExceptionHandler.handle_process_execution
    def kill_process_by_name(process_name: str) -> bool:
        """
        通过进程名强制终止进程
        
        Args:
            process_name: 进程名
            
        Returns:
            操作成功返回True，失败返回False
        """
        if not process_name:
            raise ProcessExecutionError(process_name="未知进程", message="进程名为空，跳过进程终止")
            
        logger.debug(f"尝试强制终止进程: {process_name}")
        
        terminated = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    proc.kill()  # 强制终止
                    logger.debug(f"已强制终止进程: {proc.info['name']} (PID: {proc.pid})")
                    terminated = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if terminated:
            time.sleep(Timing.PROCESS_KILL_WAIT)  # 等待进程完全关闭
            return True
        else:
            raise ProcessExecutionError(process_name=process_name, message=f"未找到进程: {process_name}")
    
    @staticmethod
    @ExceptionHandler.handle_process_execution
    def is_application_running(launch_config: Dict[str, Any]) -> bool:
        """
        通用应用程序检测函数，根据配置文件参数进行精确进程匹配
        适用于任何工具配置，不仅限于特定应用
        
        Args:
            launch_config: 启动配置字典
            
        Returns:
            应用程序是否正在运行
        """
        manager = ProcessManager()
        return manager._is_application_running_impl(launch_config)
    
    def _is_application_running_impl(self, launch_config: Dict[str, Any]) -> bool:
        """应用程序运行检测的具体实现"""
        # 解析检测条件
        criteria = self._parse_detection_criteria(launch_config)
        
        if not criteria.tool_name:
            raise ProcessExecutionError(process_name="应用检测", message="缺少 tool_name 配置")
        
        # 对于lanjun版本，不需要匹配版本号
        require_version_match = criteria.version_str != ModuleConfig.LANJUN_VERSION
        
        # 1. 首先尝试通过进程匹配获取PID
        process_result = ProcessDetector.find_matching_process(criteria)
        if process_result:
            app_pid, app_proc_name = process_result
            
            # 2. 如果找到匹配进程，尝试通过PID查找对应窗口
            win = WindowManager.find_window_by_pid(app_pid)
            if win:
                WindowManager.activate_and_maximize_window(win)
                return True
        
        # 3. 如果通过PID没找到，尝试通过窗口标题匹配
        win = WindowManager.find_window_by_title(criteria.tool_name, criteria.version_str, require_version_match)
        if win:
            WindowManager.activate_and_maximize_window(win)
            return True
        
        logger.debug(f"未找到 {criteria.tool_name}({criteria.version_str}) 的运行实例")
        return False
    
    def _parse_detection_criteria(self, launch_config: Dict[str, Any]) -> MatchCriteria:
        """解析检测条件"""
        tool_name = str(launch_config.get("tool", "")).lower()
        version_str = str(launch_config.get("version", "")).lower()
        executable = launch_config.get('executable', '')
        process_check = launch_config.get('process_check', {})
        process_name = process_check.get('name', '')
        keywords = process_check.get('keywords', [])
        
        # 从命令中提取路径，用于Java应用检测
        cmd = launch_config.get('cmd', '')
        use_java = 'java' in str(cmd).lower()
        
        # 构建关键字列表
        all_keywords = [str(k).lower() for k in keywords]
        if executable:
            all_keywords.append(str(executable).lower())
        
        return MatchCriteria(
            tool_name=tool_name,
            version_str=version_str,
            process_name=process_name,
            keywords=all_keywords,
            jar_keywords=[],  # 检测时不需要JAR关键字
            use_java=use_java
        )
    
    @staticmethod
    @ExceptionHandler.handle_process_execution
    def close_processes_using_file(file_path: str) -> bool:
        """
        关闭占用指定文件的所有进程
        
        Args:
            file_path: 文件路径
            
        Returns:
            成功关闭进程返回True，否则返回False
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return True
            
        logger.debug(f"尝试关闭占用文件的进程: {file_path}")
        
        # 使用备选方法：遍历所有进程检查文件句柄
        logger.debug("使用进程文件句柄检测方法查找占用文件的进程")
        return ProcessManager._close_processes_using_file_alternative(file_path)
    
    @staticmethod
    def _close_processes_using_file_alternative(file_path: str) -> bool:
        """
        通过遍历进程句柄来检测和关闭占用文件的进程
        
        Args:
            file_path: 文件路径
            
        Returns:
            成功关闭进程返回True，否则返回False
        """
        file_path_lower = file_path.lower()
        terminated_any = False
        
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                open_files = proc.info.get('open_files') or []
                
                for open_file in open_files:
                    if open_file.path.lower() == file_path_lower:
                        logger.debug(f"找到占用文件的进程: {proc.info['name']} (PID: {proc.pid})")
                        
                        # 尝试终止进程
                        if ProcessTerminator.terminate_process_gracefully(proc):
                            terminated_any = True
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        if terminated_any:
            time.sleep(Timing.PROCESS_CLOSE_WAIT)  # 等待进程完全关闭
            
        return terminated_any