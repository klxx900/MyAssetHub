# main_window.py

import os
import sys
import tempfile

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QTextEdit,
    QToolBar,
    QStatusBar,
    QFileDialog,
    QPushButton,
    QSizePolicy,
    QCheckBox,
    QToolButton,
)
from PySide6.QtGui import QClipboard, QIcon
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter, QPolygonF
from PySide6.QtCore import QPointF

from tree_view import AssetTreeWidget
from assets_grid import AssetGridWidget
from db_manager import DatabaseManager, AssetRecord
from watcher import scan_folder


# ══════════════════════════════════════════════════════════════════
#  配色方案 - 深邃暗黑风格
# ══════════════════════════════════════════════════════════════════

C_BG_DARK = "#1e1e1e"        # 主背景
C_BG_PANEL = "#2a2a2a"       # 面板背景
C_BG_INPUT = "#141414"       # 输入框背景（深黑）
C_BG_CARD = "#252525"        # 卡片背景
C_BORDER = "#3f3f3f"         # 边框色
C_BORDER_LIGHT = "#4a4a4a"   # 浅边框
C_TEXT = "#d4d4d4"           # 主文字
C_TEXT_BRIGHT = "#ffffff"    # 高亮文字
C_TEXT_DIM = "#808080"       # 暗淡文字
C_TEXT_MUTED = "#5a5a5a"     # 更暗淡文字
C_ACCENT = "#0078d4"         # 强调色（蓝色）
C_ACCENT_HOVER = "#1a8cff"   # 悬停蓝色
C_ACCENT_PRESSED = "#005a9e" # 按下蓝色
C_HEADER = "#252526"         # 工具栏背景
C_BUTTON = "#3c3c3c"         # 按钮背景
C_BUTTON_HOVER = "#4a4a4a"   # 按钮悬停背景
C_SPLITTER = "#2d2d2d"       # 分割线颜色


# ══════════════════════════════════════════════════════════════════
#  生成树形箭头图标
# ══════════════════════════════════════════════════════════════════

def _create_branch_arrow(direction: str, size: int = 18, color: str = "#909090") -> QPixmap:
    """生成树形展开/折叠箭头图标。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))

    margin = size * 0.25
    s = size

    if direction == "right":
        triangle = QPolygonF([
            QPointF(margin + 2, margin),
            QPointF(s - margin, s / 2),
            QPointF(margin + 2, s - margin),
        ])
    else:  # down
        triangle = QPolygonF([
            QPointF(margin, margin + 2),
            QPointF(s - margin, margin + 2),
            QPointF(s / 2, s - margin),
        ])

    painter.drawPolygon(triangle)
    painter.end()
    return pixmap


def _save_arrows() -> tuple[str, str]:
    """保存箭头图标到临时目录。"""
    tmp = tempfile.mkdtemp(prefix="myassethub_arrows_")
    closed_path = os.path.join(tmp, "arrow_right.png")
    open_path = os.path.join(tmp, "arrow_down.png")
    _create_branch_arrow("right", 18, "#909090").save(closed_path)
    _create_branch_arrow("down", 18, "#909090").save(open_path)
    return closed_path, open_path


_ARROW_CLOSED, _ARROW_OPEN = _save_arrows()
_ARROW_CLOSED_CSS = _ARROW_CLOSED.replace("\\", "/")
_ARROW_OPEN_CSS = _ARROW_OPEN.replace("\\", "/")


# ══════════════════════════════════════════════════════════════════
#  全局样式表
# ══════════════════════════════════════════════════════════════════

GLOBAL_STYLESHEET = f"""
    /* ═══════════════════════════════════════════════════════
       全局字体设置
       ═══════════════════════════════════════════════════════ */
    * {{
        font-family: "Segoe UI", "Microsoft YaHei", "SF Pro Display", sans-serif;
        font-size: 10pt;
    }}

    QMainWindow {{
        background-color: {C_BG_DARK};
    }}

    /* ═══════════════════════════════════════════════════════
       顶部工具栏
       ═══════════════════════════════════════════════════════ */
    QToolBar {{
        background-color: {C_HEADER};
        border: none;
        border-bottom: 1px solid {C_BORDER};
        padding: 6px 12px;
        spacing: 10px;
    }}

    /* 工具栏按钮 - "打开目录" */
    QToolBar QPushButton {{
        background-color: {C_BUTTON};
        color: {C_TEXT_BRIGHT};
        border: 1px solid {C_BORDER_LIGHT};
        border-radius: 4px;
        padding: 7px 18px;
        font-size: 10pt;
        font-weight: 500;
    }}
    QToolBar QPushButton:hover {{
        background-color: {C_ACCENT};
        border: 1px solid {C_ACCENT};
        color: {C_TEXT_BRIGHT};
    }}
    QToolBar QPushButton:pressed {{
        background-color: {C_ACCENT_PRESSED};
        border: 1px solid {C_ACCENT_PRESSED};
    }}

    /* 工具栏标签 */
    QToolBar QLabel {{
        color: {C_TEXT};
        font-size: 10pt;
        background: transparent;
        border: none;
        padding: 0 4px;
    }}

    /* 工具栏 QToolButton */
    QToolButton {{
        background-color: {C_BUTTON};
        color: {C_TEXT_BRIGHT};
        border: 1px solid {C_BORDER_LIGHT};
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 10pt;
    }}
    QToolButton:hover {{
        background-color: {C_ACCENT};
        border: 1px solid {C_ACCENT};
    }}
    QToolButton:pressed {{
        background-color: {C_ACCENT_PRESSED};
    }}

    /* ═══════════════════════════════════════════════════════
       状态栏
       ═══════════════════════════════════════════════════════ */
    QStatusBar {{
        background-color: {C_HEADER};
        color: {C_TEXT_DIM};
        border-top: 1px solid {C_BORDER};
        font-size: 9pt;
        padding: 4px 12px;
    }}
    QStatusBar QLabel {{
        color: {C_TEXT_DIM};
    }}

    /* ═══════════════════════════════════════════════════════
       分割线 - 细且融入背景
       ═══════════════════════════════════════════════════════ */
    QSplitter {{
        background-color: {C_BG_DARK};
    }}
    QSplitter::handle {{
        background-color: {C_SPLITTER};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    QSplitter::handle:hover {{
        background-color: {C_ACCENT};
    }}

    /* ═══════════════════════════════════════════════════════
       树形视图
       ═══════════════════════════════════════════════════════ */
    QTreeView {{
        background-color: {C_BG_DARK};
        color: {C_TEXT};
        border: none;
        outline: none;
        font-size: 10pt;
        padding: 4px;
    }}
    QTreeView::item {{
        padding: 5px 8px;
        border-radius: 3px;
        margin: 1px 4px;
    }}
    QTreeView::item:hover {{
        background-color: #2a2d2e;
    }}
    QTreeView::item:selected {{
        background-color: #37373d;
        color: {C_TEXT_BRIGHT};
    }}
    QTreeView::branch {{
        background-color: {C_BG_DARK};
    }}
    QTreeView::branch:has-children:!has-siblings:closed,
    QTreeView::branch:closed:has-children:has-siblings {{
        image: url("{_ARROW_CLOSED_CSS}");
    }}
    QTreeView::branch:open:has-children:!has-siblings,
    QTreeView::branch:open:has-children:has-siblings {{
        image: url("{_ARROW_OPEN_CSS}");
    }}
    QTreeView::branch:has-siblings:!adjoins-item,
    QTreeView::branch:has-siblings:adjoins-item,
    QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
        border-image: none;
        image: none;
    }}

    /* ═══════════════════════════════════════════════════════
       输入框 - 质感设计
       ═══════════════════════════════════════════════════════ */
    QLineEdit {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 10pt;
        selection-background-color: {C_ACCENT};
        selection-color: {C_TEXT_BRIGHT};
    }}
    QLineEdit:hover {{
        border: 1px solid {C_BORDER_LIGHT};
    }}
    QLineEdit:focus {{
        border: 1px solid {C_ACCENT};
        background-color: #1a1a1a;
    }}
    QLineEdit:read-only {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT_DIM};
    }}
    QLineEdit::placeholder {{
        color: {C_TEXT_MUTED};
    }}

    /* ═══════════════════════════════════════════════════════
       对话框 (QDialog) - 修复文字不可见问题
       ═══════════════════════════════════════════════════════ */
    QDialog {{
        background-color: #2d2d2d;
        color: #e0e0e0;
    }}
    QDialog QLabel {{
        color: #e0e0e0;
        background: transparent;
    }}
    QDialog QPushButton {{
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #4a4a4a;
        border-radius: 4px;
        padding: 6px 15px;
        min-width: 80px;
    }}
    QDialog QPushButton:hover {{
        background-color: #0078d4;
        border: 1px solid #0078d4;
    }}
    QDialog QLineEdit {{
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #3f3f3f;
    }}
    QMessageBox {{
        background-color: #2d2d2d;
    }}
    QMessageBox QLabel {{
        color: #e0e0e0;
    }}

    /* ═══════════════════════════════════════════════════════
       文本编辑框
       ═══════════════════════════════════════════════════════ */
    QTextEdit {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 10px 12px;
        font-size: 10pt;
        selection-background-color: {C_ACCENT};
    }}
    QTextEdit:hover {{
        border: 1px solid {C_BORDER_LIGHT};
    }}
    QTextEdit:focus {{
        border: 1px solid {C_ACCENT};
        background-color: #1a1a1a;
    }}

    /* ═══════════════════════════════════════════════════════
       标签
       ═══════════════════════════════════════════════════════ */
    QLabel {{
        color: {C_TEXT};
        background: transparent;
    }}

    /* ═══════════════════════════════════════════════════════
       按钮（通用）
       ═══════════════════════════════════════════════════════ */
    QPushButton {{
        background-color: {C_BUTTON};
        color: {C_TEXT_BRIGHT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 8px 20px;
        font-size: 10pt;
    }}
    QPushButton:hover {{
        background-color: {C_BUTTON_HOVER};
        border: 1px solid {C_BORDER_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {C_ACCENT};
        border: 1px solid {C_ACCENT};
    }}
    QPushButton:disabled {{
        background-color: #2a2a2a;
        color: {C_TEXT_MUTED};
        border: 1px solid #333333;
    }}

    /* ═══════════════════════════════════════════════════════
       属性面板
       ═══════════════════════════════════════════════════════ */
    QFrame#PropertiesPanel {{
        background-color: {C_BG_PANEL};
        border: none;
        border-left: 1px solid {C_BORDER};
    }}

    /* ═══════════════════════════════════════════════════════
       滚动条
       ═══════════════════════════════════════════════════════ */
    QScrollBar:vertical {{
        background: {C_BG_DARK};
        width: 10px;
        margin: 0;
        border: none;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: #404040;
        min-height: 40px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #505050;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: {C_BG_DARK};
        height: 10px;
        margin: 0;
        border: none;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: #404040;
        min-width: 40px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #505050;
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
"""


# ══════════════════════════════════════════════════════════════════
#  属性面板组件
# ══════════════════════════════════════════════════════════════════

class _SectionHeader(QLabel):
    """面板内的分节标题。"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {C_TEXT_DIM};
                font-size: 9pt;
                font-weight: 600;
                letter-spacing: 0.5px;
                padding: 4px 0;
                margin-top: 8px;
                border-bottom: 1px solid {C_BORDER};
            }}
            """
        )


class _PropertyRow(QWidget):
    """属性行：标签 + 值控件。"""

    def __init__(self, label_text: str, value_widget: QWidget, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        label = QLabel(label_text)
        label.setFixedWidth(50)
        label.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 9pt;")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(label)
        layout.addWidget(value_widget, 1)


class PropertiesPanel(QFrame):
    """右侧属性面板。"""

    def __init__(self, parent=None, db: DatabaseManager = None):
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        self._db = db
        self._current_asset_path = ""
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)

        # ── 标题 ──────────────────────────────────────────────────
        title = QLabel("属性")
        title.setStyleSheet(
            f"""
            font-size: 13pt;
            font-weight: 600;
            color: {C_TEXT_BRIGHT};
            padding-bottom: 8px;
            """
        )
        layout.addWidget(title)

        # ── 分隔线 ────────────────────────────────────────────────
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {C_BORDER}; max-height: 1px;")
        layout.addWidget(separator)

        layout.addSpacing(8)

        # ── 缩略图预览区 ──────────────────────────────────────────
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(240, 240)
        self._thumb_label.setAlignment(Qt.AlignCenter)
        self._thumb_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {C_BG_INPUT};
                border: 2px dashed {C_BORDER};
                border-radius: 8px;
                color: {C_TEXT_MUTED};
                font-size: 10pt;
            }}
            """
        )
        self._thumb_label.setText("无预览")

        thumb_container = QHBoxLayout()
        thumb_container.setContentsMargins(0, 0, 0, 0)
        thumb_container.addStretch()
        thumb_container.addWidget(self._thumb_label)
        thumb_container.addStretch()
        layout.addLayout(thumb_container)

        layout.addSpacing(4)

        # ── 基本信息 ──────────────────────────────────────────────
        layout.addWidget(_SectionHeader("基本信息"))

        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        self._name_edit.setPlaceholderText("选择资产...")
        layout.addWidget(_PropertyRow("名称", self._name_edit))

        self._type_edit = QLineEdit()
        self._type_edit.setReadOnly(True)
        self._type_edit.setPlaceholderText("—")
        layout.addWidget(_PropertyRow("类型", self._type_edit))

        self._size_edit = QLineEdit()
        self._size_edit.setReadOnly(True)
        self._size_edit.setPlaceholderText("—")
        layout.addWidget(_PropertyRow("大小", self._size_edit))

        # ── 路径 ──────────────────────────────────────────────────
        layout.addWidget(_SectionHeader("文件路径"))

        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)

        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("—")
        self._path_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {C_BG_INPUT};
                color: {C_TEXT_DIM};
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 9pt;
            }}
            """
        )
        path_layout.addWidget(self._path_edit, 1)

        # 路径复制按钮
        copy_btn = QToolButton()
        copy_btn.setText("📋")
        copy_btn.setToolTip("复制文件路径")
        copy_btn.clicked.connect(self.copy_path_to_clipboard)
        path_layout.addWidget(copy_btn)

        layout.addLayout(path_layout)

        # ── 备注 ──────────────────────────────────────────────────
        layout.addWidget(_SectionHeader("备注"))

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("添加备注...")
        self._notes_edit.setMinimumHeight(80)
        self._notes_edit.setMaximumHeight(120)
        self._notes_edit.textChanged.connect(self._on_notes_changed)
        layout.addWidget(self._notes_edit)

        layout.addStretch()

    # ── 公共 API ──────────────────────────────────────────────────

    def set_asset(self, file_path: str) -> None:
        """更新面板显示指定资产的信息。"""
        if not file_path or not os.path.isfile(file_path):
            self.clear_panel()
            return

        self._current_asset_path = file_path
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
        size_bytes = os.path.getsize(file_path)

        self._name_edit.setText(name)
        self._type_edit.setText(ext.upper().lstrip("."))
        self._size_edit.setText(self._format_size(size_bytes))
        self._path_edit.setText(file_path)
        self._path_edit.setToolTip(file_path)

        # 加载数据库中的信息 (备注 & 缩略图路径)
        asset = None
        if self._db:
            asset = self._db.get_asset_by_path(file_path)
            self._notes_edit.blockSignals(True)
            if asset:
                self._notes_edit.setPlainText(asset.comment)
            else:
                self._notes_edit.clear()
            self._notes_edit.blockSignals(False)

        # 缩略图显示逻辑
        thumb_file = ""
        
        # 1. 优先尝试从数据库获取缩略图路径
        if asset and asset.thumb_path and os.path.isfile(asset.thumb_path):
            thumb_file = asset.thumb_path
        
        # 2. 如果数据库没有缩略图，且文件本身是图片，则使用文件本身
        if not thumb_file and ext in (".png", ".jpg", ".jpeg", ".tga"):
            thumb_file = file_path

        if thumb_file:
            pm = QPixmap(thumb_file)
            if not pm.isNull():
                pm = pm.scaled(
                    self._thumb_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._thumb_label.setPixmap(pm)
                self._thumb_label.setText("")
                # 有图片时改为实线边框
                self._thumb_label.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: {C_BG_INPUT};
                        border: 1px solid {C_BORDER};
                        border-radius: 8px;
                    }}
                    """
                )
            else:
                self._set_placeholder_thumb(ext)
        else:
            self._set_placeholder_thumb(ext)

    def _set_placeholder_thumb(self, ext: str) -> None:
        """设置占位缩略图。"""
        self._thumb_label.setPixmap(QPixmap())
        self._thumb_label.setText(ext.upper().lstrip(".") if ext else "无预览")
        self._thumb_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {C_BG_INPUT};
                border: 2px dashed {C_BORDER};
                border-radius: 8px;
                color: {C_TEXT_MUTED};
                font-size: 11pt;
                font-weight: 500;
            }}
            """
        )

    def clear_panel(self) -> None:
        """清空面板。"""
        self._current_asset_path = ""
        self._name_edit.clear()
        self._type_edit.clear()
        self._size_edit.clear()
        self._path_edit.clear()
        self._notes_edit.clear()
        self._thumb_label.setPixmap(QPixmap())
        self._thumb_label.setText("无预览")
        self._thumb_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {C_BG_INPUT};
                border: 2px dashed {C_BORDER};
                border-radius: 8px;
                color: {C_TEXT_MUTED};
                font-size: 10pt;
            }}
            """
        )

    def copy_path_to_clipboard(self):
        """复制文件路径到剪贴板。"""
        if self._current_asset_path:
            QApplication.clipboard().setText(self._current_asset_path)
            # 显示状态消息（如果有父窗口的状态栏）
            if self.parent() and hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage("文件路径已复制到剪贴板", 2000)

    def _on_notes_changed(self) -> None:
        """当备注内容改变时，自动保存到数据库。"""
        if not self._db or not self._current_asset_path:
            return
        
        comment = self._notes_edit.toPlainText()
        # 自动保存
        self._db.update_metadata(self._current_asset_path, comment=comment)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# ══════════════════════════════════════════════════════════════════
#  后台扫描线程
# ══════════════════════════════════════════════════════════════════

class ScanThread(QThread):
    """后台扫描线程，防止 UI 卡顿。"""
    finished = Signal(str, int)  # folder_path, asset_count

    def __init__(self, folder_path: str, db: DatabaseManager):
        super().__init__()
        self.folder_path = folder_path
        self.db = db
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        # 执行扫描
        scan_folder(
            self.folder_path, 
            self.db, 
            recursive=True,
            should_stop=lambda: self._stop_requested
        )
        
        if self._stop_requested:
            return
            
        # 扫描完成后查询总数
        assets = self.db.get_assets_recursive(self.folder_path)
        self.finished.emit(self.folder_path, len(assets))


# ══════════════════════════════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    主窗口 — 三栏布局的资产浏览器。
    
    布局：
      • 左侧：文件夹树 (AssetTreeWidget)
      • 中间：资产网格 (AssetGridWidget)
      • 右侧：属性面板 (PropertiesPanel)
    """

    def __init__(self, root_path: str = ""):
        super().__init__()

        self.setWindowTitle("MyAssetHub")
        self.resize(1500, 900)
        self.setMinimumSize(1000, 600)

        # ── 初始化数据库 ──────────────────────────────────────────
        self._db = DatabaseManager()
        self._db.initialize()
        self._db.delete_non_supported_assets()  # 启动时自动清理一次
        
        # 程序启动时自动清理一次缩略图垃圾（数据库已初始化，可以安全调用）
        try:
            from core.watcher import clean_orphan_thumbnails
            clean_orphan_thumbnails()
        except Exception as e:
            print(f"[Warning] 清理缩略图失败: {e}")
        
        self._scan_thread = None  # 扫描线程句柄
        
        # 添加成员变量
        self.search_edit = None
        self.current_folder = ""

        # 如果没有传入路径，则尝试从数据库加载上次的路径
        if not root_path:
            root_path = self._db.get_last_project()

        self._current_root = root_path or os.path.expanduser("~")
        if self._current_root:
            self._db.save_last_project(self._current_root)

        # ── 应用全局样式 ──────────────────────────────────────────
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # ── 中心部件 ──────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 工具栏 ────────────────────────────────────────────────
        self._build_toolbar()

        # ── 三栏分割器 ────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # 左侧：树
        self._tree = AssetTreeWidget(root_path=self._current_root)
        self._tree.setMinimumWidth(220)
        self._tree.setMaximumWidth(400)
        self._tree.setStyleSheet("")  # 使用全局样式

        # 中间：网格
        self._grid = AssetGridWidget()
        self._grid.setMinimumWidth(400)

        # 右侧：属性
        self._props = PropertiesPanel(db=self._db)

        splitter.addWidget(self._tree)
        splitter.addWidget(self._grid)
        splitter.addWidget(self._props)

        # 初始比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([280, 900, 320])

        main_layout.addWidget(splitter)

        # ── 状态栏 ────────────────────────────────────────────────
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = QLabel("就绪")
        status.addWidget(self._status_label, 1)

        # ── 信号连接 ──────────────────────────────────────────────
        self._tree.folderSelected.connect(self._on_folder_selected)
        self._grid.assetSelected.connect(self._on_asset_selected)

        # 【新增】拖拽相关信号连接
        self._grid.filesImported.connect(self._on_files_imported)
        self._tree.filesDropped.connect(self._on_files_dropped_to_tree)

    # ================================================================
    #  工具栏
    # ================================================================

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # ── 打开目录按钮 ──────────────────────────────────────────
        self._open_btn = QPushButton("📂  打开目录")
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.setToolTip("选择资产根目录 (Ctrl+O)")
        self._open_btn.clicked.connect(self._on_open_folder)
        toolbar.addWidget(self._open_btn)

        # ── 新建/重命名/删除按钮 ──────────────────────────────────
        toolbar.addSeparator()
        
        self._new_folder_btn = QPushButton("➕ 新建")
        self._new_folder_btn.setToolTip("在当前目录新建文件夹")
        self._new_folder_btn.clicked.connect(lambda: self._tree._create_folder(self._tree.currentIndex()))
        toolbar.addWidget(self._new_folder_btn)

        self._rename_folder_btn = QPushButton("✏️ 重命名")
        self._rename_folder_btn.setToolTip("重命名选中的文件夹")
        self._rename_folder_btn.clicked.connect(lambda: self._tree._rename_folder(self._tree.currentIndex()))
        toolbar.addWidget(self._rename_folder_btn)

        self._delete_folder_btn = QPushButton("🗑️ 删除")
        self._delete_folder_btn.setToolTip("删除选中的文件夹")
        self._delete_folder_btn.clicked.connect(lambda: self._tree._delete_folder(self._tree.currentIndex()))
        toolbar.addWidget(self._delete_folder_btn)

        # ── 间隔 ──────────────────────────────────────────────────
        toolbar.addSeparator()

        # ── 路径标签 ──────────────────────────────────────────────
        path_label = QLabel("路径")
        toolbar.addWidget(path_label)

        # ── 路径显示框 ────────────────────────────────────────────
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        
        self._path_display = QLineEdit(self._current_root)
        self._path_display.setReadOnly(True)
        self._path_display.setMinimumWidth(350)
        self._path_display.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {C_BG_INPUT};
                color: {C_TEXT_DIM};
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
                font-family: "Consolas", "SF Mono", monospace;
            }}
            QLineEdit:hover {{
                border: 1px solid {C_BORDER_LIGHT};
            }}
            """
        )
        path_layout.addWidget(self._path_display, 1)
        
        # 路径复制按钮
        copy_path_btn = QToolButton()
        copy_path_btn.setText("📋")
        copy_path_btn.setToolTip("复制路径到剪贴板")
        copy_path_btn.clicked.connect(self.copy_path_to_clipboard)
        path_layout.addWidget(copy_path_btn)
        
        # 将布局添加到工具栏
        path_widget = QWidget()
        path_widget.setLayout(path_layout)
        toolbar.addWidget(path_widget)

        # ── 弹性空间 ──────────────────────────────────────────────
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        toolbar.addWidget(spacer)

        # ── 全局搜索框 ────────────────────────────────────────────────
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 13pt; padding-right: 4px;")
        toolbar.addWidget(search_icon)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("全局搜索资产（文件名模糊匹配）")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(300)
        self.search_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {C_BG_INPUT};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }}
            QLineEdit:hover {{
                border: 1px solid {C_BORDER_LIGHT};
            }}
            QLineEdit:focus {{
                border: 1px solid {C_ACCENT};
            }}
            QLineEdit::placeholder {{
                color: {C_TEXT_MUTED};
            }}
            """
        )
        self.search_edit.textChanged.connect(self.on_global_search)
        toolbar.addWidget(self.search_edit)

    # ================================================================
    #  槽函数
    # ================================================================

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "选择资产根目录", self._current_root
        )
        if folder:
            self._current_root = folder
            self._db.save_last_project(folder)  # 保存到数据库
            self._path_display.setText(folder)
            self._tree.set_root_path(folder)
            self._grid.clear()
            self._props.clear_panel()
            self._status_label.setText(f"已加载: {folder}")

    def _on_folder_selected(self, folder_path: str) -> None:
        self._path_display.setText(folder_path)
        self._props.clear_panel()
        
        # ── 1. 立即显示缓存 ──────────────────────────────────
        assets = self._db.get_assets_recursive(folder_path)
        self._grid.load_assets(assets)
        self._status_label.setText(f"正在加载缓存: {len(assets)} 个资产")
        
        # ── 2. 异步扫描更新 ──────────────────────────────────
        # 停止之前的扫描
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.stop()
            self._scan_thread.wait()
            
        self._status_label.setText(f"正在后台扫描: {folder_path}...")
        self._scan_thread = ScanThread(folder_path, self._db)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()

    def _on_scan_finished(self, folder_path: str, count: int) -> None:
        """扫描完成后刷新网格。"""
        # 确保当前选中的还是那个文件夹
        if self._path_display.text() == folder_path:
            assets = self._db.get_assets_recursive(folder_path)
            self._grid.load_assets(assets)
            self._status_label.setText(f"{folder_path}  ·  {len(assets)} 个资产 (已同步)")

    def _on_asset_selected(self, file_path: str) -> None:
        self._props.set_asset(file_path)
        self._status_label.setText(f"已选择: {os.path.basename(file_path)}")

    def _on_search_changed(self, text: str) -> None:
        search = text.strip().lower()
        for i in range(self._grid.count()):
            item = self._grid.item(i)
            if not search:
                item.setHidden(False)
            else:
                item.setHidden(search not in item.text().lower())

        visible = sum(
            1 for i in range(self._grid.count())
            if not self._grid.item(i).isHidden()
        )
        if search:
            self._status_label.setText(f"搜索 \"{text}\"  ·  {visible} 个结果")
        else:
            self._status_label.setText("就绪")

    def _on_files_imported(self, folder_path: str) -> None:
        """网格区域有文件被拖入后，重新扫描并刷新。"""
        self._status_label.setText(f"文件已导入到: {folder_path}")
        # 重新触发扫描
        self._on_folder_selected(folder_path)

    def _on_files_dropped_to_tree(self, target_folder: str) -> None:
        """文件被拖到树的某个文件夹后，刷新网格（如果当前正在显示源目录）。"""
        self._status_label.setText(f"文件已移动到: {target_folder}")
        # 刷新当前网格显示
        current_display = self._path_display.text()
        if current_display:
            self._on_folder_selected(current_display)

    def copy_path_to_clipboard(self) -> None:
        """复制当前路径到剪贴板。"""
        current_path = self._path_display.text()
        if current_path:
            QApplication.clipboard().setText(current_path)
            self.statusBar().showMessage("路径已复制到剪贴板", 2000)

    def on_global_search(self, text: str) -> None:
        """全局搜索资产"""
        if not text.strip():
            # 如果搜索框为空，显示当前文件夹的资产
            current_folder = self._path_display.text()
            if current_folder:
                self._on_folder_selected(current_folder)
            return
        
        # 执行全局搜索
        assets = self._db.search_assets(text.strip())
        self._grid.load_assets(assets)
        self._status_label.setText(f"搜索结果: {len(assets)} 个资产")


# ══════════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置全局字体
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    root = sys.argv[1] if len(sys.argv) > 1 else ""
    window = MainWindow(root_path=root)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()