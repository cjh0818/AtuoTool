#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-18 
# @filename: config.py
# @description: 配置常量模块，集中管理所有硬编码值、魔法数字和路径

"""
配置常量模块
包含项目中所有硬编码的常量、路径、阈值等配置信息
"""

import os
from typing import Dict, List, Tuple

# ==== 文件路径配置 ====
class Paths:
    """路径相关常量"""
    # 目录名称
    CONFIG_DIR = "config"
    IMAGES_DIR = "images"
    LOGS_DIR = "logs"
    SCREENSHOTS_DIR = "screenshots"
    
    # 子目录
    PROCESS_IMAGE_DIR = "screenshots/process_image"
    RES_IMAGE_DIR = "screenshots/res_image"
    SCREENSHOT_ACTION_DIR = "screenshots/screenshot_action"
    
    # 文件名
    DATA_DB_FILE = "data.db"
    
    @staticmethod
    def get_config_file_path(tool: str, version: str) -> str:
        """获取配置文件路径"""
        from utils.util import get_program_directory
        program_dir = get_program_directory()
        config_dir = os.path.join(program_dir, Paths.CONFIG_DIR)
        return os.path.join(config_dir, f"{tool}_{version}.yml")


# ==== 时间配置 ====
class Timing:
    """时间相关常量（秒）"""
    # 默认等待时间
    DEFAULT_PAUSE = 3
    DEFAULT_APP_LAUNCH_PAUSE = 3
    
    # 特定操作等待时间
    CONTROL_INTERFACE_WAIT = 15
    SCAN_BUTTON_WAIT = 30
    REMOTE_HOST_CONNECT_WAIT = 20
    INPUT_MEMORY_WAIT = 5
    DOWN_SAMPLE_WAIT = 20
    INSTALL_CLICK_WAIT = 1.5
    
    # 进程操作等待时间
    PROCESS_TERMINATE_TIMEOUT = 5
    PROCESS_CLOSE_WAIT = 2
    PROCESS_KILL_WAIT = 1
    
    # UI操作间隔
    MOVE_KEY_PRESS_INTERVAL = 0.02
    DELETE_KEY_PRESS_INTERVAL = 0.02
    INPUT_CHAR_INTERVAL = 0.01
    TYPE_WRITE_INTERVAL = 0.03
    
    # 窗口操作等待
    WINDOW_OPERATION_DELAY = 0.5
    WINDOW_MAXIMIZE_WAIT = 1
    CLIPBOARD_OPERATION_DELAY = 0.5
    HOTKEY_OPERATION_DELAY = 1


# ==== 图像识别配置 ====
class ImageRecognition:
    """图像识别相关常量"""
    DEFAULT_CONFIDENCE = 0.8
    MOUSE_MOVE_DURATION = 0.5
    
    # 默认截图尺寸
    DEFAULT_SCREENSHOT_WIDTH = 100
    DEFAULT_SCREENSHOT_HEIGHT = 100


# ==== 图像匹配配置 ====
class ImageMatching:
    """图像匹配相关常量"""
    # 匹配算法可靠性权重
    METHOD_RELIABILITY = {
        ('灰度图像', 'TM_CCOEFF_NORMED'): 1.0,      # 最高可靠性
        ('灰度图像', 'TM_CCORR_NORMED'): 0.9,
        ('灰度图像', 'TM_SQDIFF_NORMED'): 0.8,
        ('边缘检测', 'TM_CCOEFF_NORMED'): 0.85,
        ('边缘检测', 'TM_CCORR_NORMED'): 0.75,
        ('边缘检测', 'TM_SQDIFF_NORMED'): 0.7,
        ('直方图均衡化', 'TM_CCOEFF_NORMED'): 0.7,
        ('直方图均衡化', 'TM_CCORR_NORMED'): 0.6,
        ('直方图均衡化', 'TM_SQDIFF_NORMED'): 0.4   # 最低可靠性，容易产生异常
    }
    
    # 边缘检测参数
    CANNY_THRESHOLD1 = 50
    CANNY_THRESHOLD2 = 150
    
    # 一致性检查参数
    CONSISTENCY_THRESHOLD_FACTOR = 0.8  # 高置信度匹配筛选因子
    MIN_HIGH_CONFIDENCE_MATCHES = 2     # 最少高置信度匹配数量
    OUTLIER_DISTANCE_FACTOR = 2         # 异常值距离因子
    MAX_DISTANCE_FACTOR = 1.5           # 最大允许距离因子
    
    # 二次验证参数
    VERIFICATION_THRESHOLD_FACTOR = 0.8  # 二次验证阈值因子
    SINGLE_MATCH_BONUS_THRESHOLD = 0.05  # 单一匹配额外阈值
    
    # 图像处理方法名称
    GRAY_METHOD_NAME = "灰度图像"
    EDGE_METHOD_NAME = "边缘检测"
    HISTOGRAM_METHOD_NAME = "直方图均衡化"
    
    # 匹配算法名称
    CCOEFF_NORMED_NAME = "TM_CCOEFF_NORMED"
    CCORR_NORMED_NAME = "TM_CCORR_NORMED"
    SQDIFF_NORMED_NAME = "TM_SQDIFF_NORMED"


# ==== 帮助信息配置 ====
class HelpConfig:
    """帮助信息相关常量"""
    # 帮助信息标题和分隔符
    MAIN_HELP_TITLE = "图形工具自动化帮助信息"
    SEPARATOR_LENGTH = 10
    MODULE_HELP_TITLE_FORMAT = "{tool} {version} - {module} 模块帮助信息"
    ALL_MODULES_TITLE_FORMAT = "{tool} {version} - 可用模块列表"
    
    # 显示格式配置
    DESCRIPTION_WIDTH_CALCULATION = 20  # 描述对齐宽度
    MIN_SPACES = 1  # 最小空格数
    PARAM_NAME_WIDTH = 15  # 参数名称显示宽度
    SOURCE_VALUE_WIDTH = 10  # 源值显示宽度
    
    # 文件扩展名
    CONFIG_FILE_EXTENSION = ".yml"
    
    # 默认值显示
    DEFAULT_VALUE_NONE = "无"
    DEFAULT_MODULE_NAME = "未知模块"
    DEFAULT_DESCRIPTION = "无描述"
    
    # 帮助文本
    REQUIRED_PARAMS_TITLE = "必需参数:"
    OPTIONAL_PARAMS_TITLE = "可选参数:"
    AVAILABLE_MODULES_TITLE = "可用模块:"
    OTHER_PARAMS_TITLE = "其他参数:"
    PARAM_DEPENDENCIES_TITLE = "参数依赖关系:"
    USAGE_EXAMPLES_TITLE = "使用示例:"
    
    # 参数描述
    TOOL_PARAM_DESC = "工具名称"
    VERSION_PARAM_DESC = "工具版本"
    MODULE_PARAM_DESC = "自动化操作模块名称"
    PARAMS_PARAM_DESC = "自定义参数 key=value"
    LAUNCH_CMD_PARAM_DESC = "自定义启动命令"
    LAUNCH_PAUSE_PARAM_DESC = "自定义操作间隔时间"
    HELP_MODULE_PARAM_DESC = "显示指定模块的帮助信息（自定义参数）"
    LOG_PARAM_DESC = "日志级别 (debug/info)"
    
    # 示例文本
    PARAMS_FORMAT_DESC = "格式          key=value，多个参数用空格分隔"
    PARAMS_EXAMPLE = "示例          url=https://127.0.0.1/shell.jsp password=123456"
    LAUNCH_CMD_OVERRIDE_DESC = "覆盖配置文件中的 launch.cmd 配置"
    LAUNCH_CMD_EXAMPLE = '示例          --launch-cmd "cd C:\\\\tools_path && java -jar tool.jar"'
    LAUNCH_PAUSE_OVERRIDE_DESC = "覆盖配置文件中的 launch.pause 配置"
    LAUNCH_PAUSE_EXAMPLE = "示例          --launch-pause 3"
    MAIN_USAGE_EXAMPLE = "python main.py -t godzilla -v hw -m add_webshell --help-module"
    MODULE_HELP_EXAMPLE_FORMAT = "python main.py -t {tool} -v {version} -m <模块名称> --help-module"
    USAGE_EXAMPLE_FORMAT = "python main.py -t {tool} -v {version} -m {module}"
    
    # 错误消息
    ERROR_CONFIG_DIR_NOT_EXIST = "错误：配置目录不存在: {path}"
    ERROR_CONFIG_FILE_NOT_EXIST = "错误：配置文件不存在: {path}"
    ERROR_NO_MODULES_FOUND = "错误：配置文件中没有找到任何模块"
    ERROR_MODULE_NOT_FOUND = "错误：未找到模块: {module}"
    ERROR_NO_AVAILABLE_CONFIGS = "未找到可用的配置文件"


# ==== 进程管理配置 ====
class ProcessConfig:
    """进程管理相关常量"""
    # Java进程名称
    JAVA_PROCESS_NAMES = {'java.exe', 'javaw.exe', 'java'}
    
    # 工具名映射
    TOOL_NAME_MAPPING = {
        "godzilla": "哥斯拉",
        "behinder": "冰蝎", 
        "lanjun": "蓝军",
        "mdut": "Multiple Database Utilization Tools"
    }
    
    # 常见误判进程名单
    FALSE_POSITIVE_PROCESSES = [
        "explorer.exe", "notepad++.exe", "notepad.exe", "code.exe",
        "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "iexplore.exe",
        "cmd.exe", "powershell.exe", "pwsh.exe", "conhost.exe"
    ]
    
    # 常见误判标题模式
    FALSE_POSITIVE_PATTERNS = [
        ".yml", ".yaml", ".txt", ".md", ".py", ".js", ".html", ".css",
        "记事本", "notepad", "vs code", "visual studio code", "配置文件",
        "命令提示符", "cmd", "command prompt", "administrator: ", "管理员: ",
        "c:\\windows\\system32\\cmd.exe", "powershell", "pwsh"
    ]
    
    # 需要保留数据库文件的工具
    SKIP_DB_DELETION_TOOLS = ['mdut']
    SKIP_DB_DELETION_VERSIONS = {'godzilla': ['lanjun']}


# ==== UI操作配置 ====
class UIConfig:
    """UI操作相关常量"""
    # 点击类型
    CLICK_LEFT = "left"
    CLICK_RIGHT = "right" 
    CLICK_DOUBLE = "double"
    
    # 移动方向
    MOVE_DIRECTIONS = {
        "left": "left",
        "right": "right", 
        "up": "up",
        "down": "down"
    }
    
    # 热键组合
    DEFAULT_HOTKEY = ['win', 'r']


# ==== 日志配置 ====
class LogConfig:
    """日志相关常量"""
    # 日志消息长度限制
    COMMAND_DISPLAY_LENGTH = 100
    CMDLINE_DISPLAY_LENGTH = 160
    CMDLINE_TITLE_DISPLAY_LENGTH = 100
    
    # 敏感参数过滤
    SENSITIVE_PARAMS = ["password", "pass", "pwd", "secret", "token", "key"]


# ==== 网络配置 ====
class NetworkConfig:
    """网络相关常量"""
    # IP地址验证
    INVALID_IPS = ['0.0.0.0', '255.255.255.255']
    IP_OCTET_MIN = 0
    IP_OCTET_MAX = 255


# ==== 文件操作配置 ====
class FileConfig:
    """文件操作相关常量"""
    # 编码格式
    DEFAULT_ENCODING = 'utf-8'
    
    # 文件扩展名
    YAML_EXTENSIONS = ['.yml', '.yaml']
    IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
    
    # 时间戳格式
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    DATETIME_FORMAT = "%Y%m%d_%H%M%S"


# ==== 特殊步骤描述 ====
class StepDescriptions:
    """特殊步骤描述常量"""
    CONTROL_INTERFACE = "进入控制界面"
    SCAN_BUTTON = "点击扫描按钮"
    REMOTE_HOST_CONNECT = "连接远程主机"
    INPUT_MEMORY = "注入内存马"
    DOWN_SAMPLE = "下载样本"
    INSTALL_CLICK = "点击Enter安装样本"


# ==== 动作映射相关 ====
class ActionTypes:
    """动作类型常量"""
    OPEN = "open"
    CLICK = "click"
    INPUT = "input"
    RES = "res"
    WINDOW = "window"
    RECOGNIZE = "recognize"
    KEYBOARD = "keyboard"
    SCREENSHOT = "screenshot"
    OUTPUT = "output"
    AUTO_INSTALL = "auto_install"


# ==== 窗口操作类型 ====
class WindowOperations:
    """窗口操作类型常量"""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    EXIT = "exit"


# ==== 结果输出类型 ====
class ResultTypes:
    """结果输出类型常量"""
    TEXT = "text"
    IMAGE = "image"


# ==== 分支处理相关 ====
class BranchConfig:
    """分支处理相关常量"""
    SUCCESS_BRANCH = "success"
    ERROR_BRANCH = "error"
    CONTINUE_STEP = "continue"
    BRANCH_KEY = "branch"
    
    # recognize_action的type参数值
    TYPE_SUCCESS = "success"
    TYPE_ERROR = "error"


# ==== 命令行参数 ====
class CLIConfig:
    """命令行参数相关常量"""
    # 参数名称
    TOOL_ARG = "tool"
    VERSION_ARG = "version"
    MODULE_ARG = "module"
    PARAMS_ARG = "params"
    LAUNCH_CMD_ARG = "launch_cmd"
    LAUNCH_PAUSE_ARG = "launch_pause"
    HELP_MODULE_ARG = "help_module"
    LOG_ARG = "log"
    
    # 参数分隔符
    PARAM_SEPARATOR = "="
    COMMAND_SEPARATOR = "&&"
    
    # 日志级别选项
    LOG_LEVELS = ["debug", "info"]


# ==== 配置文件结构 ====
class ConfigStructure:
    """配置文件结构相关常量"""
    LAUNCH_KEY = "launch"
    MODEL_KEY = "model"
    PROCESS_KEY = "process"
    RES_PROCESS_KEY = "res_process"
    
    # launch配置
    CMD_KEY = "cmd"
    PAUSE_KEY = "pause"
    PROCESS_CHECK_KEY = "process_check"
    EXECUTABLE_KEY = "executable"
    
    # 进程检查配置
    NAME_KEY = "name"
    KEYWORDS_KEY = "keywords"
    
    # 模块配置
    DROPDOWN_OPTIONS_KEY = "dropdown_options"
    DROPDOWN_DEPENDENCIES_KEY = "dropdown_dependencies"
    DEFAULT_PARAMS_KEY = "default_params"


# ==== 模块特定配置 ====
class ModuleConfig:
    """模块特定配置"""
    ADD_WEBSHELL_MODULE = "add_webshell"
    
    # 特殊版本标识
    LANJUN_VERSION = "lanjun"


# ==== 自动化安装配置 ====
class AutoInstallConfig:
    """自动化安装相关常量"""
    # 默认点击关键词列表
    DEFAULT_CLICK_KEYWORDS = [
        "yes", "ok", "accept", "next", "install", "run", "agree", 
        "enable", "retry", "continue", "connect", "unzip", "open", 
        "finish", "end", "allow access", "ja", "weiter", "akzeptieren", 
        "starten", "fertig", "zustimmen", "ausfuehren", "einverstanden",
        "是", "确定", "接受", "下一步", "安装", "运行", "同意", 
        "启用", "重试", "继续", "连接", "解压", "打开", 
        "完成", "结束", "允许访问"
    ]
    
    # 默认结束关键词列表（点击这些按钮后认为安装结束）
    DEFAULT_FINISH_KEYWORDS = [
        "finish", "fertig", "close the program", "complete",
        "完成", "结束", "关闭程序"
    ]
    
    # 不点击的关键词列表（黑名单）
    DONT_CLICK_KEYWORDS = [
        "cancel", "don't", "do not", "abbrechen", "abbruch", "nicht"
    ]
