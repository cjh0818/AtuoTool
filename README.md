# AutoTool - 图形工具自动化执行引擎

AutoTool 是一个基于图像识别和自动化操作的图形界面工具自动化执行引擎，支持通过YAML配置文件定义自动化流程。


## 目录结构说明

```
AutoTool
|-- main.py                 # 程序主入口
|-- config.py               # 常量配置模块
|-- requirements.txt        # Python依赖包列表
|-- config/                 # 配置文件目录
|   |-- behinder_2.0.yml    # 冰蝎2.0版本配置
|   |-- behinder_3.0.yml    # 冰蝎3.0版本配置
|   |-- behinder_lanjun.yml # 冰蝎蓝军版本配置
|   |-- godzilla_hw.yml     # Godzilla HW版本配置
|   |-- godzilla_lanjun.yml # Godzilla蓝军版本配置
|   |-- mdut_2.0.6.yml      # mdut2.0.6版本配置
|   |-- win_10.yml          # Windows 10相关配置
|-- core/                   # 核心功能模块
|   |-- __init__.py         # 包初始化文件
|   |-- action.py           # 自动化操作函数定义
|   |-- action_mapper.py    # 操作映射器
|   |-- branch_executor.py  # 分支执行器
|   |-- match_image.py      # 图像匹配模块
|   |-- param_processor.py  # 参数处理器
|   |-- process_manager.py  # 进程管理模块
|   |-- recognizer.py       # 识别器
|   |-- step_executor.py    # 步骤执行器
|   |-- step_parser.py      # 步骤解析器
|-- images/                 # 图像模板目录
|   |-- behinder_2.0/       # 冰蝎2.0版本图像模板
|   |-- behinder_3.0/       # 冰蝎3.0版本图像模板
|   |-- behinder_lanjun/    # 冰蝎蓝军版本图像模板
|   |-- godzilla_hw/        # Godzilla HW版本图像模板
|   |-- godzilla_lanjun/    # Godzilla蓝军版本图像模板
|   |-- mdut_2.0.6/         # mdut2.0.6版本图像模板
|   |-- win_10/             # Windows 10相关图像模板
|-- utils/                  # 工具模块
|   |-- util.py             # 通用工具函数
|   |-- logger.py           # 日志处理
|   |-- exception_handler.py # 异常处理
|   |-- help_info.py        # 帮助信息显示
|-- screenshots/            # 截图保存目录
|   |-- process_image/      # 操作过程截图
|   |-- res_image/          # 输出结果截图
|-- logs/                   # 日志文件目录
```

## 环境要求

### Python版本
- Python 3.10.11（当前环境，已测试可用）

### 依赖包
- pyautogui==0.9.54 
- pyperclip==1.9.0 
- opencv-python==4.12.0.88 
- numpy==2.2.6 
- pyyaml==6.0.2 
- psutil==7.0.0 
- pygetwindow==0.0.9 
- pywin32==311 

## Windows环境部署
1.更新`pip`
```cmd
python -m pip install -i http://mirrors.sangfor.org/pypi/simple --trusted-host mirrors.sangfor.org --upgrade pip
```
2.安装python依赖
```cmd
pip install -i http://mirrors.sangfor.org/pypi/simple --trusted-host mirrors.sangfor.org -r requirements.txt
```
3.编译为exe文件
```cmd
python setup.py build
```
执行上述命令行，会在`AutoTool`目录下，生成`build`文件夹

4.进入`build`目录，将 `build` 文件夹里面的内容直接压缩成`auto_tool.zip`

5.删除`build`文件夹


## 配置文件说明
配置文件位于`config/`目录下，使用YAML格式定义工具、版本和模块信息。

主要配置结构：
```yaml
tool: 工具名称
version: 版本标识
launch:
  cmd: "启动命令"
  pause: 等待时间
  process_check:
    name: "进程名称"
    keywords: ["关键词1", "关键词2"]
model:
  - name: 模块名称
    description: 模块描述
    dropdown_options: 下拉框选项
      参数名:
        选项值: "图像路径"
    dropdown_dependencies:
      - source_key: "源参数"
        target_key: "目标参数"
        mapping:
          源值: ["目标可选值1", "目标可选值2"]
    default_params:
      参数_option: "默认值"
    process:
      - position: "图像路径"
        description: 操作描述
        action: 操作类型
        # 其他操作参数...
    res_process:
      - position: ""
        action: res
        type: "text/image"
```

## 使用方法

### 1. 查看帮助信息
```cmd
# 显示主帮助信息
python main.py -h

# 显示所有可用模块
python main.py -t godzilla -v hw --help-module

# 显示特定模块的详细帮助
python main.py -t godzilla -v hw -m add_webshell --help-module
```

### 2. 执行自动化任务
```cmd
# 基本用法
python main.py -t 工具名称 -v 版本 -m 模块名称

# 带参数用法
python main.py -t godzilla -v hw -m add_webshell --params url=http://127.0.0.1/login.jsp password=pass key=key

# 示例：添加webshell
python main.py -t godzilla -v hw -m add_webshell --params url=https://127.0.0.1/shell.jsp password=F3Vx0Uj2ySlyxRCR key=BC8ONmUuxLQJ6rFx proxy=_no encode=utf-8 payload=asp encryptor=asp_eval_base64 profile=_404
```

### 3. 支持的操作类型

#### open - 打开应用
```yaml
- position: ""
  description: 打开应用
  action: open
```

#### click - 点击操作
```yaml
- position: "images/godzilla_hw/add_webshell/target_btn.png"
  description: 点击【目标】按钮
  action: click
  click_button: left    # 可选: left, right, double
  click_offset: [0, 0]  # 点击偏移量
```

#### input - 输入操作
```yaml
- position: ""
  description: 输入连接webshell的url
  action: input
  clear: true           # 是否清空输入框
  enter: true           # 是否按下回车键
  param:
    url: "https://127.0.0.1/shell.jsp"
```

#### res - 结果处理
```yaml
# 文本结果处理
- position: ""
  description: 提取命令输出中的IP地址
  action: res
  type: "text"

# 图像结果处理
- position: ""
  description: 保存结果截图
  action: res
  type: "image"
```

#### window - 窗口操作
```yaml
- position: ""
  action: window
  type: "exit"    # 可选: exit, minimize, maximize
```

#### recognize - 识别模板图片
```yaml
- position: "images/godzilla_hw/add_webshell/error_popup.png"
  description: 识别错误提示弹窗
  action: recognize
  step: "continue"    # 可选: continue（识别到则执行success分支，否则继续执行）
  branch:
    success:
      - position: "images/godzilla_hw/add_webshell/confirm_btn.png"
        description: 点击确定按钮关闭错误提示
        action: click
```

#### move - 键盘按键模拟
```yaml
- position: ""
  description: 点击win + D显示桌面
  action: keyboard
  keys: "win,d"
  action_type: "hotkey"
```

#### delete - 长按删除键
```yaml
- position: ""
  description: 长按【backspace键】删除
  action: keyboard
  keys: "backspace"
  duration: 3
  action_type: "press"
```

#### screenshot - 截取屏幕图片
```yaml
- position: ""
  description: 截取屏幕图片
  action: screenshot
  size: [800, 600]                    # 截图尺寸 [width, height]
  use_last_click_position: true       # 是否使用上次点击位置作为截图中心
  screenshot_path: "screenshots/res_image/result.png"  # 截图保存路径
```

#### branch - 分支执行（不是独立action，是其他action的属性）
```yaml
- position: "images/godzilla_hw/add_webshell/testconn_btn.png"
  description: 点击测试连接按钮
  action: click
  error_res: "images/godzilla_hw/add_webshell/fail_label.png"
  success_res: "images/godzilla_hw/add_webshell/success_label.png"
  branch:
    success:
      - position: "images/godzilla_hw/add_webshell/confirm_btn.png"
        description: 点击确定按钮
        action: click
    error:
      - position: "images/godzilla_hw/add_webshell/confirm_btn.png"
        description: 点击确定按钮关闭失败提示
        action: click
```
