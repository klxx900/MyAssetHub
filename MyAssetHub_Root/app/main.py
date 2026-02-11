# app/main.py

import sys
import os

# ── 关键：确保程序能找到 ui 模块 ──────────────────────────────────
# 获取 main.py 的绝对路径 (MyAssetHub_Root/app/main.py)
current_file = os.path.abspath(__file__)
# 获取 app 文件夹的路径 (MyAssetHub_Root/app/)
app_dir = os.path.dirname(current_file)
# 将工作目录切换到 app 目录
os.chdir(app_dir)
# 将 app 目录加入 Python 搜索路径
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# 将 ui 目录也加入搜索路径，解决 ui 文件内部的直接导入问题
ui_dir = os.path.join(app_dir, 'ui')
if ui_dir not in sys.path:
    sys.path.insert(0, ui_dir)

# 将 core 目录也加入搜索路径，方便直接导入核心模块
core_dir = os.path.join(app_dir, 'core')
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

def main():
    app = QApplication(sys.argv)
    
    # ── 导入 UI ─────
    # 必须在 QApplication 创建之后导入，因为 ui 模块中有初始化 QPixmap 的代码
    try:
        from ui.main_window import MainWindow
    except ImportError as e:
        print(f"导入失败: {e}")
        # 尝试备用导入方式
        from ui.main_window import MainWindow

    app.setStyle("Fusion")

    # 设置中文字体支持，防止界面乱码
    font = QFont("Microsoft YaHei", 10) 
    app.setFont(font)

    # root_path 处理
    root_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else None

    # 启动
    try:
        window = MainWindow(root_path=root_path)
        window.show()

        # ── 开发模式热重载支持 ─────────────────────────────
        # 检查是否开启开发模式（通过环境变量或命令行参数）
        if "--dev" in sys.argv or os.environ.get("MYASSETHUB_DEV") == "1":
            try:
                from hot_reloader import HotReloader
                # 保持 reloader 引用防止被垃圾回收
                app.reloader = HotReloader(window)
            except ImportError as e:
                print(f"无法加载热重载模块: {e}")

        sys.exit(app.exec())
    except Exception as e:
        # 捕获运行时的错误并记录
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n运行时崩溃: {str(e)}")
        raise e

if __name__ == "__main__":
    main()