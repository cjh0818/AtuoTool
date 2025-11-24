from cx_Freeze import setup, Executable
import sys

# 根据操作系统设置基础目录
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="AutoTool",
    version="1.0",
    description="自动化执行工具",
    executables=[Executable("main.py")],
    options={
        "build_exe": {
            "packages": [
                "os",
                "sys",
                "time",
                "yaml",
                "argparse",
                "logging",
                "pyautogui",
                "ctypes",
                "py7zr",
                "pyperclip",
                "cv2",
                "numpy",
                "psutil",
                "pygetwindow",
                "win32gui",
                "win32api",
                "win32con",
                "win32process",
                "subprocess",
                "re",
                "functools",
                "datetime"
            ],
            "include_files": [
                ("config", "config"),
                ("images", "images"),
            ]
        }
    }
)