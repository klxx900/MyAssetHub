@echo off
REM PyInstaller 打包脚本 - MyAssetHub
REM 使用 --onedir 模式（单一文件夹模式）

echo ========================================
echo MyAssetHub 打包脚本
echo ========================================
echo.

REM 检查 PyInstaller 是否安装
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] PyInstaller 未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败，请手动运行: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo [信息] 开始打包...
echo.

REM 检查图标文件
if not exist "logo\logo.ico" (
    echo [警告] 未找到 logo.ico 文件，将使用默认图标
    echo [提示] 如需使用自定义图标，请将 logo.png 转换为 logo.ico
    set ICON_ARG=
) else (
    set ICON_ARG=--icon=logo\logo.ico
)

REM 执行打包命令
pyinstaller ^
    --noconsole ^
    --onedir ^
    --name "MyAssetHub" ^
    %ICON_ARG% ^
    --add-data "MyAssetHub_Root\app;app" ^
    --hidden-import "core.path_utils" ^
    --hidden-import "core.db_manager" ^
    --hidden-import "core.watcher" ^
    --hidden-import "ui.main_window" ^
    --hidden-import "ui.assets_grid" ^
    --hidden-import "ui.tree_view" ^
    --exclude-module "tkinter" ^
    --exclude-module "matplotlib" ^
    --exclude-module "numpy" ^
    --exclude-module "pandas" ^
    MyAssetHub_Root\app\main.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo EXE 文件位置: dist\MyAssetHub\MyAssetHub.exe
echo.
echo 注意：
echo 1. 首次运行 EXE 时，会在 EXE 同级目录自动创建 data 和 data\.cache 文件夹
echo 2. 数据库文件将保存在 data\library.db
echo 3. 配置文件将保存在 data\config.json
echo 4. 缩略图缓存将保存在 data\.cache\
echo.
pause
