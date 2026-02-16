# MyAssetHub 依赖库清单

## 必需依赖

### 1. PySide6
- **用途**: Qt GUI 框架，用于构建用户界面
- **安装**: `pip install PySide6`
- **打包**: 必须包含，PyInstaller 会自动检测

### 2. Pillow (PIL)
- **用途**: 图像处理，用于生成缩略图
- **安装**: `pip install Pillow`
- **打包**: 必须包含，PyInstaller 会自动检测
- **注意**: 可能需要添加 `--hidden-import PIL._tkinter_finder`（已在 .spec 文件中包含）

### 3. watchdog
- **用途**: 文件系统监控（仅在开发模式的热重载功能中使用）
- **安装**: `pip install watchdog`
- **打包**: 可选，如果不需要热重载功能可以排除
- **注意**: 生产环境可以排除，但建议保留以防需要文件监控功能

## Python 标准库（无需安装）

以下库是 Python 标准库的一部分，无需额外安装：

- `os` - 操作系统接口
- `sys` - 系统相关参数和函数
- `sqlite3` - SQLite 数据库接口
- `threading` - 线程支持
- `contextlib` - 上下文管理器工具
- `dataclasses` - 数据类（Python 3.7+）
- `typing` - 类型提示支持
- `pathlib` - 面向对象的文件系统路径
- `hashlib` - 安全哈希和消息摘要
- `time` - 时间相关函数
- `shutil` - 高级文件操作
- `tempfile` - 临时文件和目录
- `logging` - 日志记录工具
- `subprocess` - 子进程管理

## 安装所有依赖

```bash
pip install PySide6 Pillow watchdog pyinstaller
```

## 打包时的依赖处理

PyInstaller 会自动检测并打包以下依赖：
- PySide6 及其所有子模块
- Pillow 及其所有子模块
- watchdog（如果使用）

### 已排除的模块（减少打包体积）

在 `.spec` 文件中已排除以下不需要的模块：
- `tkinter` - GUI 框架（使用 PySide6 替代）
- `matplotlib` - 绘图库（不需要）
- `numpy` - 数值计算（不需要）
- `pandas` - 数据分析（不需要）
- `scipy` - 科学计算（不需要）
- `IPython` - 交互式 Python（不需要）
- `jupyter` - Jupyter 笔记本（不需要）

## 离线环境说明

所有依赖库都会被 PyInstaller 打包到 EXE 中，因此：
- ✅ 可以在无网环境下运行
- ✅ 不需要目标机器安装 Python
- ✅ 不需要目标机器安装任何依赖库

## 版本建议

- **Python**: 3.8 或更高版本（推荐 3.9+）
- **PySide6**: 最新稳定版
- **Pillow**: 最新稳定版
- **watchdog**: 最新稳定版
- **PyInstaller**: 5.0 或更高版本
