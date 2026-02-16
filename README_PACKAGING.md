# MyAssetHub 打包说明

## 打包要求

### 1. 安装依赖

```bash
pip install PySide6 Pillow watchdog pyinstaller
```

### 2. 图标文件

- 如果使用自定义图标，请将 `logo/logo.png` 转换为 `logo/logo.ico`
- 可以使用在线工具或 ImageMagick 进行转换：
  ```bash
  # 使用 ImageMagick（如果已安装）
  magick logo\logo.png logo\logo.ico
  ```

## 打包方法

### 方法一：使用批处理脚本（推荐）

直接运行：
```bash
build_exe.bat
```

### 方法二：使用 PyInstaller 命令

```bash
pyinstaller --noconsole --onedir --name "MyAssetHub" --icon="logo\logo.ico" --add-data "MyAssetHub_Root\app;app" --hidden-import "core.path_utils" --hidden-import "core.db_manager" --hidden-import "core.watcher" --hidden-import "ui.main_window" --hidden-import "ui.assets_grid" --hidden-import "ui.tree_view" --exclude-module "tkinter" --exclude-module "matplotlib" --exclude-module "numpy" --exclude-module "pandas" MyAssetHub_Root\app\main.py
```

### 方法三：使用 .spec 文件

```bash
pyinstaller MyAssetHub.spec
```

## 打包后的目录结构

```
dist/
└── MyAssetHub/
    ├── MyAssetHub.exe          # 主程序
    ├── app/                    # 应用代码
    │   ├── core/
    │   ├── ui/
    │   └── ...
    ├── _internal/              # PyInstaller 内部文件
    └── [其他依赖文件]
```

## 运行说明

1. **首次运行**：EXE 会在同级目录自动创建 `data` 和 `data\.cache` 文件夹
2. **数据库位置**：`data\library.db`
3. **配置文件位置**：`data\config.json`
4. **缓存目录**：`data\.cache\`

## 依赖库清单

### 必需库
- **PySide6**: Qt GUI 框架
- **Pillow**: 图像处理（缩略图生成）
- **watchdog**: 文件监控（可选，如果使用文件监控功能）
- **sqlite3**: Python 标准库，无需额外安装

### 可选库
- **hot_reloader**: 仅开发模式需要，打包时会被排除

## 注意事项

1. **路径兼容性**：所有路径都已修复，使用 `core/path_utils.py` 中的工具函数确保 EXE 环境下路径正确
2. **数据目录**：程序会在 EXE 同级目录创建 `data` 文件夹，确保有写入权限
3. **离线运行**：所有依赖都已打包，可以在无网环境下运行
4. **更新代码**：使用 `--onedir` 模式便于后续更新，只需替换 `app` 文件夹即可

## 故障排除

### 问题：找不到模块
**解决**：在 `hiddenimports` 中添加缺失的模块

### 问题：图标不显示
**解决**：确保图标文件是 `.ico` 格式，或使用 PNG（PyInstaller 会自动转换）

### 问题：运行时找不到数据文件
**解决**：检查 `--add-data` 参数是否正确，确保 `app` 目录被正确包含
