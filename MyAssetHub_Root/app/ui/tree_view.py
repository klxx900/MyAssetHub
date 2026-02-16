"""
Asset Tree View - 合并了 core/tree_view.py 的高级逻辑
提供文件夹树状浏览、右键菜单（新建/重命名/删除）、快捷键支持
【新增】支持接收从网格拖入的文件（移动/复制到目标文件夹）
【新增】支持接收从外部拖入的文件
"""
import os
import shutil
import logging
from pathlib import Path

from core.db_manager import DatabaseManager
from core.watcher import move_asset

from PySide6.QtWidgets import (
    QTreeView, QAbstractItemView, QStyledItemDelegate,
    QStyle, QMenu, QInputDialog, QMessageBox, QFileSystemModel
)
from PySide6.QtCore import (
    Qt, QDir, QSize, QRect, QModelIndex, Signal, QUrl
)
from PySide6.QtGui import (
    QPixmap, QPainter, QIcon,
    QDrag, QAction, QKeySequence, QShortcut
)

logger = logging.getLogger(__name__)

# 【新增】树可接收的文件格式
TREE_DROP_ALLOWED = {
    ".fbx", ".obj", ".abc", ".gltf", ".glb", ".max",
    ".jpg", ".jpeg", ".png", ".tga",
}


class ThumbnailDelegate(QStyledItemDelegate):
    """为树状视图中的项目显示缩略图图标"""
    ICON_SIZE = 20

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        super().paint(painter, option, index)

        path = index.model().filePath(index) if hasattr(index.model(), 'filePath') else ""
        if path and os.path.isdir(path):
            thumb = os.path.join(path, ".thumbnail.png")
            if os.path.isfile(thumb):
                pix = QPixmap(thumb).scaled(
                    self.ICON_SIZE, self.ICON_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                if not pix.isNull():
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
        if not self.isDir(parent):
            return False
        path = self.filePath(parent)
        try:
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
    - 拖放支持（文件夹之间移动）
    - 【新增】接收从网格拖入的文件（移动到目标文件夹）
    - 【新增】接收从外部拖入的文件（复制到目标文件夹）
    - 缩略图委托
    """

    # 自定义信号
    folder_created = Signal(str)
    folder_renamed = Signal(str, str)
    folder_deleted = Signal(str)
    folder_changed = Signal()
    folderSelected = Signal(str)

    # 【新增】文件被移动/复制到文件夹的信号
    filesDropped = Signal(str)  # 参数: 目标文件夹路径

    def __init__(self, root_path="", parent=None):
        super().__init__(parent)
        self._root_path = ""

        # ── 文件系统模型 ──
        self._fs_model = CustomFileSystemModel(self)
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
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # ── 右键菜单 ──
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # ── 【修改】拖放配置 — 支持接收文件 ──
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)  # 改为 DragDrop 以支持外部拖入
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
    # 公共接口
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
            current = self.currentIndex()
            root_index = self._fs_model.setRootPath("")
            root_index = self._fs_model.setRootPath(self._root_path)
            self.setRootIndex(root_index)
            if current.isValid():
                self.setCurrentIndex(current)
            logger.debug("Tree view refreshed")

    # ================================================================
    # 右键菜单
    # ================================================================

    def _show_context_menu(self, position):
        """显示右键上下文菜单"""
        menu = QMenu(self)
        index = self.indexAt(position)

        action_new = QAction("📁 新建文件夹", self)
        action_new.setShortcut(QKeySequence("Ctrl+N"))
        action_new.triggered.connect(lambda: self._create_folder(index))
        menu.addAction(action_new)

        if index.isValid():
            menu.addSeparator()

            action_rename = QAction("✏️ 重命名", self)
            action_rename.setShortcut(QKeySequence(Qt.Key_F2))
            action_rename.triggered.connect(lambda: self._rename_folder(index))
            menu.addAction(action_rename)

            action_delete = QAction("🗑 删除", self)
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
    # 文件夹操作
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

        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "错误",
                f"文件夹 \"{name}\" 已存在于:\n{parent_path}"
            )
            return

        try:
            os.makedirs(new_path, exist_ok=False)
            logger.info(f"Created folder: {new_path}")

            if parent_index.isValid():
                self.expand(parent_index)

            self._select_path(new_path)

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
            return

        new_path = os.path.join(parent_path, new_name)

        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "错误",
                f"文件夹 \"{new_name}\" 已存在于:\n{parent_path}"
            )
            return

        try:
            os.rename(old_path, new_path)
            logger.info(f"Renamed folder: {old_path} -> {new_path}")

            self._select_path(new_path)

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

        if folder_path == self._root_path:
            QMessageBox.warning(self, "错误", "不能删除根目录。")
            return

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
            db = DatabaseManager()
            db.delete_assets_by_folder(folder_path)  # 删除数据库中整个文件夹的记录
            logger.info(f"Deleted folder: {folder_path}")

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
    # 快捷键
    # ================================================================

    def keyPressEvent(self, event):
        """处理快捷键"""
        key = event.key()
        modifiers = event.modifiers()
        index = self.currentIndex()

        if key == Qt.Key_F2 and index.isValid():
            self._rename_folder(index)
            event.accept()
            return

        if key == Qt.Key_Delete and index.isValid():
            self._delete_folder(index)
            event.accept()
            return

        if key == Qt.Key_N and (modifiers & Qt.ControlModifier):
            self._create_folder(index)
            event.accept()
            return

        super().keyPressEvent(event)

    # ================================================================
    # 拖放 — 从树中拖出文件夹
    # ================================================================

    def startDrag(self, supportedActions):
        """开始拖动文件夹"""
        index = self.currentIndex()
        if not index.isValid():
            return

        path = self._fs_model.filePath(index)

        drag = QDrag(self)
        from PySide6.QtCore import QMimeData
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        mime.setText(path)
        drag.setMimeData(mime)

        icon = self._fs_model.fileIcon(index)
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(32, 32))

        drag.exec_(Qt.MoveAction | Qt.CopyAction)

    # ================================================================
    # 【修改】拖放 — 接收拖入（文件夹移动 + 文件移动/复制）
    # ================================================================

    def dragEnterEvent(self, event):
        """接受包含文件URL的拖拽"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """拖拽移动时高亮目标文件夹"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            # 获取鼠标下方的文件夹索引
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                # 自动展开悬停的文件夹（方便拖入子文件夹）
                self.setCurrentIndex(index)
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """
        【增强】处理放下事件：
        1. 文件夹拖到文件夹上 → 移动文件夹（原有功能）
        2. 文件拖到文件夹上 → 移动文件（从复制改为移动）
        3. 外部文件拖到文件夹上 → 移动文件（从复制改为移动）
        """
        # 确定目标文件夹
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
            moved_count = 0
            copied_count = 0
            error_list = []

            for url in mime.urls():
                src = url.toLocalFile()

                if not os.path.exists(src):
                    continue

                # 不能拖到自己所在的目录
                if os.path.abspath(os.path.dirname(src)) == os.path.abspath(target_path):
                    continue

                # 不能拖到自己（文件夹拖到自己）
                if os.path.abspath(src) == os.path.abspath(target_path):
                    continue

                file_name = os.path.basename(src)
                dest = os.path.join(target_path, file_name)

                # ── 判断是文件夹还是文件 ──
                if os.path.isdir(src):
                    # 文件夹 → 移动
                    if not os.path.exists(dest):
                        try:
                            shutil.move(src, dest)
                            # === 新增：数据库同步 ===
                            db = DatabaseManager()
                            db.move_folder_assets(src, dest)  # 文件夹移动，递归更新路径
                            # === 结束 ===
                            moved_count += 1
                            logger.info(f"Moved folder: {src} -> {dest}")
                        except Exception as e:
                            error_list.append(f"{file_name}（{e}）")
                            logger.error(f"Move folder failed: {e}")
                    else:
                        error_list.append(f"{file_name}（目标已存在）")

                elif os.path.isfile(src):
                    # 文件 → 判断是内部移动还是外部复制
                    # 检查源文件是否在我们的根目录下（内部操作 → 移动）
                    is_internal = os.path.abspath(src).startswith(
                        os.path.abspath(self._root_path)
                    )

                    # 同名文件处理
                    if os.path.exists(dest):
                        reply = QMessageBox.question(
                            self, "文件已存在",
                            f"文件 \"{file_name}\" 在目标文件夹中已存在。\n\n是否覆盖？",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if reply == QMessageBox.No:
                            continue
                        # 删除已存在的文件以便覆盖
                        try:
                            os.remove(dest)
                        except Exception as e:
                            error_list.append(f"{file_name}（无法覆盖: {e}）")
                            continue

                    try:
                        # 无论是内部还是外部文件，统一改为移动
                        if Path(src).suffix.lower() in [".fbx", ".obj"]:  # 只对模型文件用绑定移动
                            success = move_asset(src, os.path.dirname(dest))  # dest是完整路径，取文件夹
                        else:
                            shutil.move(src, dest)  # 其他文件正常移动
                        # === 新增：数据库同步 ===
                        db = DatabaseManager()
                        db.move_file_asset(src, dest)      # 单个文件移动，保留元数据
                        # === 结束 ===
                        moved_count += 1
                        logger.info(f"Moved file: {src} -> {dest}")
                    except PermissionError:
                        error_list.append(f"{file_name}（权限不足）")
                    except Exception as e:
                        error_list.append(f"{file_name}（{e}）")

            # 显示结果
            if moved_count > 0 or error_list:
                msg_parts = []
                if moved_count > 0:
                    msg_parts.append(f"✅ 移动了 {moved_count} 个项目")
                if error_list:
                    msg_parts.append(f"❌ 失败 {len(error_list)} 个：")
                    for err in error_list:
                        msg_parts.append(f"    • {err}")

                QMessageBox.information(
                    self, "拖拽操作完成",
                    "\n".join(msg_parts)
                )

            # 发出信号通知刷新
            if moved_count > 0:
                # === 新增：全局清理 ===
                db = DatabaseManager()
                db.delete_missing_assets()  # 保险清理
                # === 结束 ===
                self.folder_changed.emit()
                self.filesDropped.emit(target_path)

            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ================================================================
    # 辅助方法
    # ================================================================

    def _select_path(self, path: str):
        """选中指定路径的项"""
        index = self._fs_model.index(path)
        if index.isValid():
            self.setCurrentIndex(index)
            self.scrollTo(index)