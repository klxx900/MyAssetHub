# app/hot_reloader.py

import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtCore import QObject, Signal

class ReloadEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.last_trigger = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.py'):
            # 防止短时间内多次触发
            now = time.time()
            if now - self.last_trigger > 1.0:
                print(f"[HotReloader] 检测到文件修改: {event.src_path}")
                self.last_trigger = now
                self.callback()

class HotReloader(QObject):
    """
    开发模式下的热重载器。
    监视文件变化并重启程序。
    """
    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.observer = Observer()
        
        # 获取 app 目录
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
        event_handler = ReloadEventHandler(self.restart_app)
        self.observer.schedule(event_handler, app_dir, recursive=True)
        self.observer.start()
        print(f"[HotReloader] 已启动，正在监视目录: {app_dir}")

    def restart_app(self):
        """重启当前进程"""
        print("[HotReloader] 正在重启应用...")
        
        # 获取当前运行的 python 解释器路径
        python = sys.executable
        
        # 获取 main.py 的绝对路径
        # main.py 与 hot_reloader.py 在同一目录下
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(app_dir, "main.py")
        
        # 获取除了脚本路径以外的原始参数
        # 注意：如果原始是通过 python main.py 启动的，sys.argv[0] 是脚本名
        args = sys.argv[1:]
        
        # 如果参数中没有 --dev，确保重启后依然有
        if "--dev" not in args:
            args.append("--dev")

        # 启动新进程
        # 不再依赖当前工作目录，直接用绝对路径
        subprocess.Popen([python, main_script] + args)
        
        # 强制退出当前进程
        os._exit(0)

    def stop(self):
        self.observer.stop()
        self.observer.join()
