"""
Asset Tree View - 合并了 core/tree_view.py 的高级逻辑
提供文件夹树状浏览、右键菜单（新建/重命名/删除）、快捷键支持
"""

import os
import shutil
import logging

from PySide6.QtWidgets import (
    QTreeView, QAbstractItemView, QStyledItemDelegate,
    QStyle, QMenu, QInputDialog, QMessageBox, QFileSystemModel
)
from PySide6.QtCore import (
    Qt, QDir, QSize, QRect, QModelIndex, Signal
)
from PySide6.QtGui import (
    QPixmap, QPainter, QIcon,
    QDrag, QAction, QKeySequence, QShortcut
)

logger = logging.getLogger(__name__)


class ThumbnailDelegate(QStyledItemDelegate):
    """为树状视图中的项目显示缩略图图标"""
    ICON_SIZE = 20

    def paint(self, painter, option, index):
        # 1. 初始化样式选项以包含模型数据（如文字、图标等）
        self.initStyleOption(option, index)
        
        # 2. 调用基类绘制（处理背景、文字颜色、高亮等）
        # 这会自动应用 QTreeView 的样式表设置
        super().paint(painter, option, index)

        # 3. 尝试加载并覆盖缩略图
        path = index.model().filePath(index) if hasattr(index.model(), 'filePath') else ""
        if path and os.path.isdir(path):
            thumb = os.path.join(path, ".thumbnail.png")
            if os.path.isfile(thumb):
                pix = QPixmap(thumb).scaled(
                    self.ICON_SIZE, self.ICON_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                if not pix.isNull():
                    # 获取图标应该出现的位置
                    icon_rect = self.parent().style().subElementRect(
                        QStyle.SE_ItemViewItemIcon, option, self.parent()
                    )
                    
                    if not icon_rect.isValid():
                        icon_rect = QRect(
                            option.rect.x() + 2,
                            option.rect.y() + (option.rect.height() - self.ICON_SIZE) // 2,
                            self.ICON_SIZE, self.ICON_SIZE
                        )

                    painter.save()
                    # 根据是否选中选择背景色覆盖原图标
                    bg_color = option.palette.highlight().color() if option.state & QStyle.State_Selected else option.palette.base().color()
                    painter.fillRect(icon_rect, bg_color)
                    painter.drawPixmap(icon_rect, pix)
                    painter.restore()

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width(), max(s.height(), self.ICON_SIZE + 4))


class CustomFileSystemModel(QFileSystemModel):
    """自定义文件系统模型，确保 hasChildren 逻辑只针对文件夹"""
    def hasChildren(self, parent):
        if not parent.isValid():
            return super().hasChildren(parent)
        
        # 如果不是文件夹，肯定没有子节点
        if not self.isDir(parent):
            return False
            
        # 检查文件夹下是否有符合过滤条件的子项（即是否有子文件夹）
        path = self.filePath(parent)
        try:
            # 这里的逻辑要和 setFilter 保持一致
            # 我们只关心是否有子文件夹
            it = QDir(path).entryInfoList(QDir.Dirs | QDir.NoDotAndDotDot)
            return len(it) > 0
        except:
            return False

class AssetTreeWidget(QTreeView):
    """
    资产树状视图 - 显示文件夹结构
    功能：
    - QFileSystemModel 驱动的文件夹浏览
    - 右键菜单：新建文件夹、重命名、删除
    - 快捷键：F2(重命名)、Delete(删除)、Ctrl+N(新建文件夹)
    - 拖放支持
    - 缩略图委托
    """

    # 自定义信号：当文件夹结构发生变化时发出
    folder_created = Signal(str)    # 参数: 新文件夹路径
    folder_renamed = Signal(str, str)  # 参数: 旧路径, 新路径
    folder_deleted = Signal(str)    # 参数: 被删除的文件夹路径
    folder_changed = Signal()       # 通用变化信号
    folderSelected = Signal(str)    # 参数: 选中文件夹的绝对路径

    def __init__(self, root_path="", parent=None):
        super().__init__(parent)
        self._root_path = ""

        # ── 文件系统模型 ──
        self._fs_model = CustomFileSystemModel(self)
        # 恢复为只显示文件夹，不显示文件
        self._fs_model.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
        self._fs_model.setNameFilterDisables(False)
        self.setModel(self._fs_model)

        # 只显示名称列
        for col in range(1, self._fs_model.columnCount()):
            self.setColumnHidden(col, True)

        # ── 基本视图设置 ──
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setIndentation(20)
        self.setExpandsOnDoubleClick(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止直接编辑，用对话框代替

        # ── 右键菜单 ──
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # ── 拖放 ──
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        # ── 缩略图委托 ──
        self._thumb_delegate = ThumbnailDelegate(self)
        self.setItemDelegate(self._thumb_delegate)

        # ── 选择行为 ──
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

        if root_path:
            self.set_root_path(root_path)

        logger.info("AssetTreeWidget initialized")

    def _on_selection_changed(self, selected, deselected):
        """当选择项发生变化时触发"""
        index = self.currentIndex()
        if index.isValid():
            path = self._fs_model.filePath(index)
            self.folderSelected.emit(path)


    # ================================================================
    #  公共接口
    # ================================================================

    def set_root_path(self, path: str):
        """设置根目录路径"""
        if not os.path.isdir(path):
            logger.warning(f"Root path does not exist: {path}")
            return

        self._root_path = path
        root_index = self._fs_model.setRootPath(path)
        self.setRootIndex(root_index)
        logger.info(f"Root path set to: {path}")

    def get_root_path(self) -> str:
        return self._root_path

    def current_folder_path(self) -> str:
        """获取当前选中项的文件夹路径，未选中则返回根路径"""
        index = self.currentIndex()
        if index.isValid():
            return self._fs_model.filePath(index)
        return self._root_path

    def refresh(self):
        """刷新文件系统模型"""
        if self._root_path:
            # QFileSystemModel 使用文件系统监视器自动刷新，
            # 但我们可以通过重新设置根路径来强制刷新
            current = self.currentIndex()
            root_index = self._fs_model.setRootPath("")
            root_index = self._fs_model.setRootPath(self._root_path)
            self.setRootIndex(root_index)
            if current.isValid():
                self.setCurrentIndex(current)
            logger.debug("Tree view refreshed")

    # ================================================================
    #  右键菜单
    # ================================================================

    def _show_context_menu(self, position):
        """显示右键上下文菜单"""
        menu = QMenu(self)

        index = self.indexAt(position)

        # 新建文件夹 - 始终可用
        action_new = QAction("📁 新建文件夹", self)
        action_new.setShortcut(QKeySequence("Ctrl+N"))
        action_new.triggered.connect(lambda: self._create_folder(index))
        menu.addAction(action_new)

        # 以下操作仅在选中了有效项时可用
        if index.isValid():
            menu.addSeparator()

            action_rename = QAction("✏️ 重命名", self)
            action_rename.setShortcut(QKeySequence(Qt.Key_F2))
            action_rename.triggered.connect(lambda: self._rename_folder(index))
            menu.addAction(action_rename)

            action_delete = QAction("🗑️ 删除", self)
            action_delete.setShortcut(QKeySequence(Qt.Key_Delete))
            action_delete.triggered.connect(lambda: self._delete_folder(index))
            menu.addAction(action_delete)

            menu.addSeparator()

            action_open_explorer = QAction("📂 在资源管理器中打开", self)
            action_open_explorer.triggered.connect(
                lambda: self._open_in_explorer(index)
            )
            menu.addAction(action_open_explorer)

        menu.exec_(self.viewport().mapToGlobal(position))

    # ================================================================
    #  文件夹操作
    # ================================================================

    def _create_folder(self, parent_index: QModelIndex = QModelIndex()):
        """在选中的文件夹下（或根目录下）新建子文件夹"""
        if parent_index.isValid():
            parent_path = self._fs_model.filePath(parent_index)
        else:
            parent_path = self._root_path

        if not parent_path or not os.path.isdir(parent_path):
            QMessageBox.warning(self, "错误", "请先设置有效的根目录。")
            return

        name, ok = QInputDialog.getText(
            self, "新建文件夹", "文件夹名称:", text="新建文件夹"
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        new_path = os.path.join(parent_path, name)

        # 检查是否已存在
        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "错误",
                f"文件夹 \"{name}\" 已存在于:\n{parent_path}"
            )
            return

        try:
            os.makedirs(new_path, exist_ok=False)
            logger.info(f"Created folder: {new_path}")

            # 展开父节点以显示新文件夹
            if parent_index.isValid():
                self.expand(parent_index)

            # 选中新创建的文件夹
            self._select_path(new_path)

            # 发出信号
            self.folder_created.emit(new_path)
            self.folder_changed.emit()

        except OSError as e:
            logger.error(f"Failed to create folder: {e}")
            QMessageBox.critical(
                self, "创建失败",
                f"无法创建文件夹:\n{e}"
            )

    def _rename_folder(self, index: QModelIndex):
        """重命名选中的文件夹"""
        if not index.isValid():
            return

        old_path = self._fs_model.filePath(index)
        old_name = self._fs_model.fileName(index)
        parent_path = os.path.dirname(old_path)

        # 不允许重命名根目录
        if old_path == self._root_path:
            QMessageBox.warning(self, "错误", "不能重命名根目录。")
            return

        new_name, ok = QInputDialog.getText(
            self, "重命名", "新名称:", text=old_name
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()
        if new_name == old_name:
            return  # 没有变化

        new_path = os.path.join(parent_path, new_name)

        # 检查是否已存在
        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "错误",
                f"文件夹 \"{new_name}\" 已存在于:\n{parent_path}"
            )
            return

        try:
            os.rename(old_path, new_path)
            logger.info(f"Renamed folder: {old_path} -> {new_path}")

            # 选中重命名后的文件夹
            self._select_path(new_path)

            # 发出信号
            self.folder_renamed.emit(old_path, new_path)
            self.folder_changed.emit()

        except OSError as e:
            logger.error(f"Failed to rename folder: {e}")
            QMessageBox.critical(
                self, "重命名失败",
                f"无法重命名文件夹:\n{e}"
            )

    def _delete_folder(self, index: QModelIndex):
        """删除选中的文件夹"""
        if not index.isValid():
            return

        folder_path = self._fs_model.filePath(index)
        folder_name = self._fs_model.fileName(index)

        # 不允许删除根目录
        if folder_path == self._root_path:
            QMessageBox.warning(self, "错误", "不能删除根目录。")
            return

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件夹 \"{folder_name}\" 及其所有内容吗？\n\n"
            f"路径: {folder_path}\n\n"
            f"⚠️ 此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(folder_path)
            logger.info(f"Deleted folder: {folder_path}")

            # 发出信号
            self.folder_deleted.emit(folder_path)
            self.folder_changed.emit()

        except OSError as e:
            logger.error(f"Failed to delete folder: {e}")
            QMessageBox.critical(
                self, "删除失败",
                f"无法删除文件夹:\n{e}"
            )

    def _open_in_explorer(self, index: QModelIndex):
        """在系统资源管理器中打开文件夹"""
        if not index.isValid():
            return

        folder_path = self._fs_model.filePath(index)
        if not os.path.isdir(folder_path):
            return

        import subprocess
        import sys

        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder_path])
            else:
                subprocess.Popen(['xdg-open', folder_path])
            logger.info(f"Opened in explorer: {folder_path}")
        except Exception as e:
            logger.error(f"Failed to open in explorer: {e}")

    # ================================================================
    #  快捷键
    # ================================================================

    def keyPressEvent(self, event):
        """处理快捷键"""
        key = event.key()
        modifiers = event.modifiers()
        index = self.currentIndex()

        # F2 → 重命名
        if key == Qt.Key_F2 and index.isValid():
            self._rename_folder(index)
            event.accept()
            return

        # Delete → 删除
        if key == Qt.Key_Delete and index.isValid():
            self._delete_folder(index)
            event.accept()
            return

        # Ctrl+N → 新建文件夹
        if key == Qt.Key_N and (modifiers & Qt.ControlModifier):
            self._create_folder(index)
            event.accept()
            return

        # 其余键交给基类处理（方向键展开/折叠等）
        super().keyPressEvent(event)

    # ================================================================
    #  拖放
    # ================================================================

    def startDrag(self, supportedActions):
        """开始拖动"""
        index = self.currentIndex()
        if not index.isValid():
            return

        path = self._fs_model.filePath(index)
        drag = QDrag(self)
        from PySide6.QtCore import QMimeData, QUrl
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        mime.setText(path)
        drag.setMimeData(mime)

        # 拖动时显示的图标
        icon = self._fs_model.fileIcon(index)
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(32, 32))

        drag.exec_(Qt.MoveAction | Qt.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """处理放下事件 - 移动文件夹"""
        target_index = self.indexAt(event.position().toPoint())
        if not target_index.isValid():
            target_path = self._root_path
        else:
            target_path = self._fs_model.filePath(target_index)

        if not os.path.isdir(target_path):
            event.ignore()
            return

        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                src = url.toLocalFile()
                if os.path.exists(src) and src != target_path:
                    dest = os.path.join(target_path, os.path.basename(src))
                    if not os.path.exists(dest):
                        try:
                            shutil.move(src, dest)
                            logger.info(f"Moved: {src} -> {dest}")
                            self.folder_changed.emit()
                        except Exception as e:
                            logger.error(f"Move failed: {e}")
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ================================================================
    #  辅助方法
    # ================================================================

    def _select_path(self, path: str):
        """选中指定路径的项"""
        index = self._fs_model.index(path)
        if index.isValid():
            self.setCurrentIndex(index)
            self.scrollTo(index)