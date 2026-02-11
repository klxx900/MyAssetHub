# assets_grid.py

import os
import sys

from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QApplication,
    QWidget,
    QVBoxLayout,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QBrush, QPen


# ══════════════════════════════════════════════════════════════════
#  配置常量
# ══════════════════════════════════════════════════════════════════

# 仅支持的3D模型格式（严格限制）
MODEL_EXTENSIONS = {".fbx", ".obj", ".abc", ".gltf", ".glb"}

# 用于查找配对缩略图的图片格式
THUMB_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tga")

# 布局尺寸
THUMB_SIZE = 140
ICON_SIZE = THUMB_SIZE
GRID_CELL_W = THUMB_SIZE + 52
GRID_CELL_H = THUMB_SIZE + 56
ITEM_SPACING = 18

# 颜色配置
COLOR_BG = "#1e1e1e"
COLOR_CARD = "#2a2a2a"
COLOR_CARD_INNER = "#323232"
COLOR_BORDER = "#3a3a3a"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#888888"
COLOR_ACCENT = "#3a6ea5"
COLOR_HOVER = "#383838"

# 格式标签颜色
EXT_COLORS = {
    ".fbx": "#e06c75",
    ".obj": "#e5c07b",
    ".abc": "#c678dd",
    ".gltf": "#61afef",
    ".glb": "#56b6c2",
}


# ══════════════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════════════

def _generate_placeholder(width: int, height: int, ext: str) -> QPixmap:
    """
    生成带有格式标签的占位缩略图。
    当找不到配对图片时使用。
    """
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(COLOR_CARD))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # ── 背景卡片 ──────────────────────────────────────────────────
    margin = 4
    painter.setPen(QPen(QColor(COLOR_BORDER), 1))
    painter.setBrush(QBrush(QColor(COLOR_CARD_INNER)))
    painter.drawRoundedRect(
        margin, margin,
        width - 2 * margin, height - 2 * margin,
        10, 10
    )

    # ── 3D立方体图标暗示 ──────────────────────────────────────────
    cx, cy = width // 2, height // 2 - 10
    s = 24
    cube_color = QColor("#555555")
    painter.setPen(QPen(cube_color, 2))
    painter.setBrush(Qt.NoBrush)

    # 前面矩形
    painter.drawRect(cx - s, cy - s + 8, s * 2 - 8, s * 2 - 8)
    # 顶部连接线
    painter.drawLine(cx - s, cy - s + 8, cx - s + 8, cy - s)
    painter.drawLine(cx + s - 8, cy - s + 8, cx + s, cy - s)
    painter.drawLine(cx - s + 8, cy - s, cx + s, cy - s)
    # 右侧线
    painter.drawLine(cx + s, cy - s, cx + s, cy + s)
    painter.drawLine(cx + s - 8, cy + s, cx + s, cy + s)

    # ── 格式标签 ──────────────────────────────────────────────────
    badge_text = ext.upper().lstrip(".")
    badge_color = QColor(EXT_COLORS.get(ext, "#666666"))

    font = QFont("Segoe UI", 11, QFont.Bold)
    painter.setFont(font)
    fm = painter.fontMetrics()
    text_w = fm.horizontalAdvance(badge_text) + 20
    text_h = fm.height() + 10

    badge_x = (width - text_w) // 2
    badge_y = height - text_h - 14

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(badge_color))
    painter.drawRoundedRect(badge_x, badge_y, text_w, text_h, 6, 6)

    painter.setPen(QColor("#ffffff"))
    painter.drawText(badge_x, badge_y, text_w, text_h, Qt.AlignCenter, badge_text)

    painter.end()
    return pixmap


def _load_thumbnail(path: str, size: int) -> QPixmap:
    """
    加载图片并按比例缩放到指定尺寸。
    保持宽高比，不拉伸变形。
    """
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _find_paired_thumbnail(model_path: str) -> str | None:
    """
    查找与模型文件同名的图片文件。
    
    例如：
      Hero_Player.fbx → 查找 Hero_Player.jpg / Hero_Player.png / Hero_Player.tga
    
    返回找到的第一个匹配图片路径，或 None。
    """
    directory = os.path.dirname(model_path)
    model_stem = os.path.splitext(os.path.basename(model_path))[0].lower()

    try:
        siblings = os.listdir(directory)
    except PermissionError:
        return None

    for sibling in siblings:
        sibling_stem, sibling_ext = os.path.splitext(sibling)
        if sibling_stem.lower() == model_stem and sibling_ext.lower() in THUMB_EXTENSIONS:
            return os.path.join(directory, sibling)

    return None


# ══════════════════════════════════════════════════════════════════
#  主组件类
# ══════════════════════════════════════════════════════════════════

class AssetGridWidget(QListWidget):
    """
    3D资产网格视图组件。
    
    特性：
      • 仅显示3D模型格式 (.fbx, .obj, .abc, .gltf, .glb)
      • 绝不显示 .png/.jpg/.tga 等图片作为独立资产
      • 自动查找同名图片作为模型缩略图
      • 找不到配对图片时显示带格式标签的占位图
      • 标签只显示文件名（不含后缀）
      • 深色主题，选中时蓝色高亮边框
    """

    assetSelected = Signal(str)

    def __init__(self, folder_path: str = "", parent=None):
        super().__init__(parent)

        # ── 视图配置 ──────────────────────────────────────────────
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setWordWrap(True)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setSpacing(ITEM_SPACING)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setGridSize(QSize(GRID_CELL_W, GRID_CELL_H))
        self.setTextElideMode(Qt.ElideMiddle)

        # ── 连接信号 ──────────────────────────────────────────────
        self.itemClicked.connect(self._on_item_clicked)

        # ── 应用样式 ──────────────────────────────────────────────
        self._apply_dark_style()

        # ── 初始加载 ──────────────────────────────────────────────
        if folder_path:
            self.set_folder(folder_path)

    # ================================================================
    #  公共 API
    # ================================================================

    def set_folder(self, folder_path: str) -> None:
        """
        清空网格并从指定目录加载3D模型资产。
        
        规则：
          1. 只扫描 .fbx, .obj, .abc, .gltf, .glb 格式
          2. 图片文件永远不会作为独立项显示
          3. 为每个模型查找同名图片作为缩略图
        """
        self.clear()
        folder_path = os.path.abspath(folder_path)

        if not os.path.isdir(folder_path):
            return

        try:
            entries = sorted(os.listdir(folder_path), key=str.lower)
        except PermissionError:
            return

        for entry in entries:
            full_path = os.path.join(folder_path, entry)

            # 跳过非文件
            if not os.path.isfile(full_path):
                continue

            # 获取扩展名
            stem, ext = os.path.splitext(entry)
            ext_lower = ext.lower()

            # ═══ 核心过滤：仅处理3D模型格式 ═══
            if ext_lower not in MODEL_EXTENSIONS:
                continue

            # 查找配对的缩略图
            thumb_path = _find_paired_thumbnail(full_path)

            if thumb_path:
                thumbnail = _load_thumbnail(thumb_path, THUMB_SIZE)
                # 如果图片加载失败，回退到占位图
                if thumbnail.isNull():
                    thumbnail = _generate_placeholder(THUMB_SIZE, THUMB_SIZE, ext_lower)
            else:
                # 没有配对图片，使用占位图
                thumbnail = _generate_placeholder(THUMB_SIZE, THUMB_SIZE, ext_lower)

            # 创建列表项（标签只显示文件名，不含后缀）
            self._add_item(
                display_name=stem,
                full_path=full_path,
                thumbnail=thumbnail,
            )

    # ================================================================
    #  内部方法
    # ================================================================

    def _add_item(self, display_name: str, full_path: str, thumbnail: QPixmap) -> None:
        """创建并添加一个网格项。"""
        item = QListWidgetItem()

        # 文件名省略处理（保持界面整洁）
        max_chars = 16
        if len(display_name) > max_chars:
            elided = display_name[: max_chars - 1] + "…"
        else:
            elided = display_name

        item.setText(elided)
        item.setIcon(QIcon(thumbnail))
        item.setData(Qt.UserRole, full_path)
        item.setToolTip(full_path)  # 悬停显示完整路径
        item.setSizeHint(QSize(GRID_CELL_W, GRID_CELL_H))

        self.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.assetSelected.emit(path)

    def load_assets(self, assets: list) -> None:
        """
        根据传入的资产对象列表加载网格内容。
        支持从数据库记录加载。
        """
        self.clear()
        for asset in assets:
            # asset 可能是 AssetRecord (来自 db_manager)
            file_path = asset.file_path
            display_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 缩略图处理
            if asset.thumb_path and os.path.exists(asset.thumb_path):
                thumbnail = _load_thumbnail(asset.thumb_path, THUMB_SIZE)
                if thumbnail.isNull():
                    ext = os.path.splitext(file_path)[1].lower()
                    thumbnail = _generate_placeholder(THUMB_SIZE, THUMB_SIZE, ext)
            else:
                ext = os.path.splitext(file_path)[1].lower()
                thumbnail = _generate_placeholder(THUMB_SIZE, THUMB_SIZE, ext)

            self._add_item(
                display_name=display_name,
                full_path=file_path,
                thumbnail=thumbnail,
            )

    # ── 样式 ──────────────────────────────────────────────────────

    def _apply_dark_style(self) -> None:
        self.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_TEXT};
                border: none;
                outline: none;
                font-size: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }}

            QListWidget::item {{
                background-color: {COLOR_CARD};
                color: {COLOR_TEXT};
                border: 2px solid transparent;
                border-radius: 10px;
                padding: 8px;
            }}

            QListWidget::item:hover {{
                background-color: {COLOR_HOVER};
                border: 2px solid #555555;
            }}

            QListWidget::item:selected {{
                background-color: #2c3e50;
                border: 2px solid {COLOR_ACCENT};
                color: #ffffff;
            }}

            QListWidget::item:selected:hover {{
                background-color: #34495e;
                border: 2px solid {COLOR_ACCENT};
            }}

            /* ── 滚动条 ──────────────────────────────────────── */
            QScrollBar:vertical {{
                background: {COLOR_BG};
                width: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3a3a;
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #4a4a4a;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            QScrollBar:horizontal {{
                background: {COLOR_BG};
                height: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: #3a3a3a;
                min-width: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #4a4a4a;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            """
        )


# ══════════════════════════════════════════════════════════════════
#  演示 / 独立运行
# ══════════════════════════════════════════════════════════════════

def _create_demo_files(demo_dir: str) -> None:
    """创建演示用的模型和配对图片文件。"""
    os.makedirs(demo_dir, exist_ok=True)

    # 带配对缩略图的模型
    paired_models = [
        ("Hero_Player", ".fbx"),
        ("Environment_Rock", ".obj"),
        ("Weapon_Sword", ".fbx"),
        ("Animation_Walk", ".abc"),
        ("Scene_Interior", ".gltf"),
        ("Helmet_Asset", ".glb"),
    ]

    # 无缩略图的模型（将显示占位图）
    unpaired_models = [
        ("Vehicle_Car", ".fbx"),
        ("Prop_Barrel", ".obj"),
        ("CrowdSim_Data", ".abc"),
        ("Building_Tower_Very_Long_Name", ".gltf"),
    ]

    # 创建带配对图片的模型
    for stem, ext in paired_models:
        model_path = os.path.join(demo_dir, f"{stem}{ext}")
        thumb_path = os.path.join(demo_dir, f"{stem}.png")

        if not os.path.exists(model_path):
            with open(model_path, "w") as f:
                f.write("")

        if not os.path.exists(thumb_path):
            px = QPixmap(THUMB_SIZE, THUMB_SIZE)
            badge_color = QColor(EXT_COLORS.get(ext, "#888888"))
            px.fill(badge_color.darker(150))
            p = QPainter(px)
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(px.rect(), Qt.AlignCenter, stem.replace("_", "\n"))
            p.end()
            px.save(thumb_path)

    # 创建无配对图片的模型
    for stem, ext in unpaired_models:
        model_path = os.path.join(demo_dir, f"{stem}{ext}")
        if not os.path.exists(model_path):
            with open(model_path, "w") as f:
                f.write("")

    # 创建一些独立图片（不应该显示在网格中）
    standalone_images = ["random_texture.png", "reference_photo.jpg", "concept_art.tga"]
    for img_name in standalone_images:
        img_path = os.path.join(demo_dir, img_name)
        if not os.path.exists(img_path):
            px = QPixmap(100, 100)
            px.fill(QColor("#336699"))
            px.save(img_path)

    print(f"[Demo] 注意：{len(standalone_images)} 个独立图片文件不会显示在网格中")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    if len(sys.argv) > 1:
        demo_folder = sys.argv[1]
    else:
        demo_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_demo_assets"
        )
        _create_demo_files(demo_folder)
        print(f"[Demo] 已创建演示文件: {demo_folder}")

    window = QWidget()
    window.setWindowTitle("Asset Grid Viewer")
    window.resize(900, 650)
    window.setStyleSheet(f"background-color: {COLOR_BG};")

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    grid = AssetGridWidget(folder_path=demo_folder)
    grid.assetSelected.connect(lambda p: print(f"[已选择] {p}"))

    layout.addWidget(grid)
    window.show()

    sys.exit(app.exec())