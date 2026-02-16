# app/core/watcher.py

"""
文件扫描与缩略图生成模块。

提供文件夹扫描、3D资产发现、同名图片匹配、
缩略图生成等功能。
"""

import os
import hashlib
import time
import shutil
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[Warning] Pillow 未安装，缩略图功能将不可用")
    print("         请运行: pip install Pillow")

from db_manager import DatabaseManager, AssetRecord, get_database


# ══════════════════════════════════════════════════════════════════
#  配置常量
# ══════════════════════════════════════════════════════════════════

# 支持的 3D 模型格式
MODEL_EXTENSIONS = {".fbx", ".obj", ".abc", ".gltf", ".glb", ".max"}

# 用于查找配对缩略图的图片格式
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tga", ".bmp"}

# 缩略图尺寸
THUMBNAIL_SIZE = (256, 256)

# 缩略图缓存目录（将使用 path_utils 获取绝对路径）
CACHE_DIR = os.path.join("data", ".cache")

# 隐藏文件夹（扫描时跳过）
HIDDEN_FOLDERS = {
    ".git", ".svn", ".hg",
    "__pycache__", ".mypy_cache", ".pytest_cache",
    ".vscode", ".idea", ".vs",
    ".mayaSwatches", "incrementalSave",
    "node_modules", ".next",
    "build", "dist", ".cache",
    "$RECYCLE.BIN", "System Volume Information",
}


# ══════════════════════════════════════════════════════════════════
#  扫描结果数据类
# ══════════════════════════════════════════════════════════════════

@dataclass
class ScanResult:
    """扫描结果统计。"""
    total_files: int = 0
    new_assets: int = 0
    updated_assets: int = 0
    skipped_assets: int = 0
    thumbnails_generated: int = 0
    deleted_assets: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def __str__(self) -> str:
        return (
            f"扫描完成: 共 {self.total_files} 个文件, "
            f"新增 {self.new_assets}, 更新 {self.updated_assets}, "
            f"跳过 {self.skipped_assets}, "
            f"生成缩略图 {self.thumbnails_generated}, "
            f"清理幽灵 {self.deleted_assets}, "
            f"错误 {len(self.errors)}"
        )


# ══════════════════════════════════════════════════════════════════
#  缩略图生成
# ══════════════════════════════════════════════════════════════════

def get_cache_dir() -> str:
    """
    获取缓存目录的绝对路径。
    
    如果目录不存在，会自动创建。
    
    Returns:
        缓存目录的绝对路径
    """
    # 使用 path_utils 获取缓存目录路径（兼容 EXE 打包）
    try:
        from path_utils import get_cache_dir as _get_cache_dir_from_utils
        cache_path = _get_cache_dir_from_utils()
    except ImportError:
        # 如果导入失败（可能是循环导入），使用备用方案
        # 获取 app 目录的路径 (MyAssetHub_Root/app)
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_path = os.path.join(app_dir, CACHE_DIR)

    # 确保目录存在
    os.makedirs(cache_path, exist_ok=True)

    return cache_path


def generate_thumbnail(
    image_path: str,
    size: tuple[int, int] = THUMBNAIL_SIZE,
    force: bool = False,
) -> Optional[str]:
    """
    将图片等比压缩生成缩略图。
    
    Args:
        image_path: 原始图片的绝对路径
        size: 缩略图尺寸，默认 (256, 256)
        force: 是否强制重新生成（即使缓存存在）
        
    Returns:
        缩略图的绝对路径，失败返回 None
        
    Example:
        >>> thumb = generate_thumbnail("/path/to/image.png")
        >>> print(thumb)
        '/project/data/.cache/a1b2c3d4e5f6.jpg'
    """
    if not HAS_PIL:
        print("[Error] Pillow 未安装，无法生成缩略图")
        return None

    if not os.path.isfile(image_path):
        print(f"[Error] 图片不存在: {image_path}")
        return None

    # 生成基于路径的 MD5 哈希文件名
    path_hash = hashlib.md5(image_path.encode("utf-8")).hexdigest()
    thumb_filename = f"{path_hash}.jpg"
    thumb_path = os.path.join(get_cache_dir(), thumb_filename)

    # 如果缓存存在且不强制刷新，直接返回
    if not force and os.path.exists(thumb_path):
        # 检查缓存是否比原图新
        if os.path.getmtime(thumb_path) >= os.path.getmtime(image_path):
            return thumb_path

    try:
        with Image.open(image_path) as img:
            # 处理 RGBA 模式（PNG 透明通道）
            if img.mode in ("RGBA", "LA", "P"):
                # 创建白色背景
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # 等比缩放（保持宽高比）
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # 保存为 JPEG（体积小，加载快）
            img.save(thumb_path, "JPEG", quality=85, optimize=True)

            return thumb_path

    except Exception as e:
        print(f"[Error] 生成缩略图失败 [{image_path}]: {e}")
        return None


def generate_placeholder_thumbnail(
    extension: str,
    size: tuple[int, int] = THUMBNAIL_SIZE,
) -> Optional[str]:
    """
    为没有配对图片的 3D 文件生成占位缩略图。
    
    Args:
        extension: 文件扩展名（如 ".fbx"）
        size: 缩略图尺寸
        
    Returns:
        占位缩略图的路径
    """
    if not HAS_PIL:
        return None

    ext_clean = extension.lower().lstrip(".")
    thumb_filename = f"placeholder_{ext_clean}.jpg"
    thumb_path = os.path.join(get_cache_dir(), thumb_filename)

    # 如果已存在，直接返回
    if os.path.exists(thumb_path):
        return thumb_path

    # 格式对应的颜色
    ext_colors = {
        "fbx": (224, 108, 117),    # 红色
        "obj": (229, 192, 123),    # 黄色
        "max": (198, 120, 221),    # 紫色
        "abc": (152, 195, 121),    # 绿色
        "blend": (255, 165, 0),    # 橙色
        "gltf": (97, 175, 239),    # 蓝色
        "glb": (86, 182, 194),     # 青色
        "txt": (171, 178, 191),    # 灰色
        "pdf": (209, 73, 78),      # 红色 (PDF 典型色)
    }

    bg_color = ext_colors.get(ext_clean, (100, 100, 100))

    try:
        from PIL import ImageDraw, ImageFont

        img = Image.new("RGB", size, (42, 42, 42))
        draw = ImageDraw.Draw(img)

        # 绘制圆角矩形背景
        margin = 20
        draw.rounded_rectangle(
            [margin, margin, size[0] - margin, size[1] - margin],
            radius=15,
            fill=(50, 50, 50),
            outline=(60, 60, 60),
            width=2,
        )

        # 绘制格式标签
        label = ext_clean.upper()
        
        # 尝试加载字体
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            font = ImageFont.load_default()

        # 获取文本边界
        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 绘制标签背景
        label_padding = 10
        label_x = (size[0] - text_width - label_padding * 2) // 2
        label_y = (size[1] - text_height - label_padding * 2) // 2

        draw.rounded_rectangle(
            [label_x, label_y, label_x + text_width + label_padding * 2, label_y + text_height + label_padding * 2],
            radius=8,
            fill=bg_color,
        )

        # 绘制文本
        draw.text(
            (label_x + label_padding, label_y + label_padding),
            label,
            fill=(255, 255, 255),
            font=font,
        )

        img.save(thumb_path, "JPEG", quality=85)
        return thumb_path

    except Exception as e:
        print(f"[Error] 生成占位缩略图失败: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
#  同名图片匹配
# ══════════════════════════════════════════════════════════════════

def find_matching_image(model_path: str) -> Optional[str]:
    """
    查找与模型文件同名的图片文件。
    
    Args:
        model_path: 模型文件的绝对路径
        
    Returns:
        匹配的图片路径，未找到返回 None
        
    Example:
        >>> find_matching_image("/assets/hero.fbx")
        '/assets/hero.jpg'  # 或 '/assets/hero.png'
    """
    directory = os.path.dirname(model_path)
    model_stem = os.path.splitext(os.path.basename(model_path))[0].lower()

    try:
        siblings = os.listdir(directory)
    except PermissionError:
        return None

    # 按优先级排序的扩展名列表
    priority_order = [".png", ".jpg", ".jpeg", ".tga", ".bmp"]

    for ext in priority_order:
        for sibling in siblings:
            sibling_stem, sibling_ext = os.path.splitext(sibling)
            if sibling_stem.lower() == model_stem and sibling_ext.lower() == ext:
                return os.path.join(directory, sibling)

    return None


# ══════════════════════════════════════════════════════════════════
#  文件大小格式化
# ══════════════════════════════════════════════════════════════════

def format_file_size(size_bytes: int) -> str:
    """将字节数格式化为可读字符串。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ══════════════════════════════════════════════════════════════════
#  文件夹扫描
# ══════════════════════════════════════════════════════════════════

def is_hidden_folder(name: str) -> bool:
    """检查文件夹是否应该被跳过。"""
    if name.startswith(".") or name.startswith("__"):
        return True
    return name.lower() in {n.lower() for n in HIDDEN_FOLDERS}


def scan_folder(
    folder_path: str,
    db: DatabaseManager,
    recursive: bool = True,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> ScanResult:
    """
    扫描文件夹，发现 3D 资产并存入数据库。
    
    Args:
        folder_path: 要扫描的文件夹路径
        db: 数据库管理器实例
        recursive: 是否递归扫描子目录
        progress_callback: 进度回调函数 callback(current_file, current, total)
        should_stop: 可选的停止检查回调，返回 True 则中止扫描
        
    Returns:
        ScanResult 扫描结果统计
    """
    folder_path = os.path.abspath(folder_path)

    if not os.path.isdir(folder_path):
        return ScanResult(errors=[f"目录不存在: {folder_path}"])

    result = ScanResult()

    # ── 第一阶段：收集所有 3D 文件 ─────────────────────────────
    model_files: list[str] = []

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            if should_stop and should_stop():
                return result
                
            # 过滤隐藏文件夹
            dirs[:] = [d for d in dirs if not is_hidden_folder(d)]

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in MODEL_EXTENSIONS:
                    # 使用标准化路径
                    full_path = os.path.normpath(os.path.join(root, filename))
                    model_files.append(full_path)
    else:
        try:
            for entry in os.listdir(folder_path):
                full_path = os.path.normpath(os.path.join(folder_path, entry))
                if os.path.isfile(full_path):
                    ext = os.path.splitext(entry)[1].lower()
                    if ext in MODEL_EXTENSIONS:
                        model_files.append(full_path)
        except PermissionError:
            result.errors.append(f"权限错误: {folder_path}")
            return result

    result.total_files = len(model_files)

    if not model_files:
        return result

    # ── 第二阶段：处理文件并生成缩略图 ─────────────────────────
    assets_to_insert: list[AssetRecord] = []

    for index, model_path in enumerate(model_files):
        if should_stop and should_stop():
            break
            
        try:
            # 进度回调
            if progress_callback:
                progress_callback(model_path, index + 1, result.total_files)

            # 获取文件信息
            stat = os.stat(model_path)
            file_name = os.path.basename(model_path)
            file_size = format_file_size(stat.st_size)
            mtime = stat.st_mtime

            # 检查数据库中是否已存在
            existing = db.get_asset_by_path(model_path)

            if existing:
                # 检查是否需要更新（文件已修改，或者缩略图之前没有现在有了）
                has_thumbnail = existing.thumb_path and os.path.exists(existing.thumb_path)
                
                # 如果文件没变，且已经有缩略图了，才跳过
                if existing.mtime >= mtime and has_thumbnail:
                    result.skipped_assets += 1
                    continue

            # 查找同名图片
            image_path = find_matching_image(model_path)
            thumb_path = ""

            if image_path:
                # 生成缩略图
                generated_thumb = generate_thumbnail(image_path)
                if generated_thumb:
                    thumb_path = generated_thumb
                    result.thumbnails_generated += 1
            else:
                # 生成占位缩略图
                ext = os.path.splitext(model_path)[1].lower()
                placeholder = generate_placeholder_thumbnail(ext)
                if placeholder:
                    thumb_path = placeholder

            # 创建资产记录
            asset = AssetRecord(
                file_path=model_path,
                file_name=file_name,
                thumb_path=thumb_path,
                file_size=file_size,
                mtime=mtime,
            )
            assets_to_insert.append(asset)

            if existing:
                result.updated_assets += 1
            else:
                result.new_assets += 1

        except Exception as e:
            result.errors.append(f"处理失败 [{model_path}]: {e}")

    # ── 第三阶段：批量写入数据库 ───────────────────────────────
    if assets_to_insert:
        try:
            db.upsert_assets_batch(assets_to_insert)
        except Exception as e:
            result.errors.append(f"数据库写入失败: {e}")

    # ── 第四阶段：清理幽灵记录 ────────────────────────────────
    # 扫描结束后清理该文件夹下的幽灵记录
    deleted = 0
    for asset in db.get_assets_by_folder(folder_path):
        if not os.path.exists(asset.file_path):
            try:
                db.delete_asset_by_path(asset.file_path)
                deleted += 1
            except Exception as e:
                result.errors.append(f"清理幽灵记录失败 [{asset.file_path}]: {e}")

    result.deleted_assets = deleted

    return result


def scan_folder_quick(
    folder_path: str,
    db: Optional[DatabaseManager] = None,
) -> list[AssetRecord]:
    """
    快速扫描文件夹，返回资产列表（不写入数据库）。
    
    适用于 UI 实时显示场景。
    
    Args:
        folder_path: 文件夹路径
        db: 数据库管理器（用于检查缓存）
        
    Returns:
        资产记录列表
    """
    folder_path = os.path.abspath(folder_path)

    if not os.path.isdir(folder_path):
        return []

    if db is None:
        db = get_database()

    assets: list[AssetRecord] = []

    try:
        entries = sorted(os.listdir(folder_path), key=str.lower)
    except PermissionError:
        return []

    for entry in entries:
        full_path = os.path.join(folder_path, entry)

        if not os.path.isfile(full_path):
            continue

        ext = os.path.splitext(entry)[1].lower()

        if ext not in MODEL_EXTENSIONS:
            continue

        # 尝试从数据库获取
        existing = db.get_asset_by_path(full_path)

        if existing:
            assets.append(existing)
        else:
            # 快速创建记录（不生成缩略图）
            stat = os.stat(full_path)
            image_path = find_matching_image(full_path)

            asset = AssetRecord(
                file_path=full_path,
                file_name=entry,
                thumb_path=image_path or "",  # 暂时存原图路径
                file_size=format_file_size(stat.st_size),
                mtime=stat.st_mtime,
            )
            assets.append(asset)

    return assets


# ══════════════════════════════════════════════════════════════════
#  清理缓存
# ══════════════════════════════════════════════════════════════════

def clear_thumbnail_cache() -> int:
    """
    清空缩略图缓存目录。
    
    Returns:
        删除的文件数量
    """
    cache_dir = get_cache_dir()
    count = 0

    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
            except Exception as e:
                print(f"[Warning] 无法删除缓存文件 [{file_path}]: {e}")

    return count


def get_cache_size() -> tuple[int, str]:
    """
    获取缩略图缓存大小。
    
    Returns:
        (字节数, 格式化字符串)
    """
    cache_dir = get_cache_dir()
    total_size = 0

    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)

    return total_size, format_file_size(total_size)


# ══════════════════════════════════════════════════════════════════
#  命令行测试
# ══════════════════════════════════════════════════════════════════

def move_asset(source_path: str, target_folder: str):
    """移动模型文件，并自动带走同名的贴图文件（jpg/png等）"""
    if not os.path.exists(source_path):
        return False
    
    # 获取文件名（无后缀）和原目录
    source_dir = os.path.dirname(source_path)
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    
    # 1. 移动主模型文件（如果目标已有同名，覆盖）
    target_model_path = os.path.join(target_folder, os.path.basename(source_path))
    if os.path.exists(target_model_path):
        os.remove(target_model_path)  # 覆盖
    shutil.move(source_path, target_folder)
    
    # 2. 移动同名贴图（常见的5种格式）
    image_extensions = ['.jpg', '.jpeg', '.png', '.tga', '.bmp']
    moved_images = 0
    for ext in image_extensions:
        image_path = os.path.join(source_dir, base_name + ext)
        if os.path.exists(image_path):
            target_image_path = os.path.join(target_folder, base_name + ext)
            if os.path.exists(target_image_path):
                os.remove(target_image_path)  # 覆盖
            shutil.move(image_path, target_folder)
            moved_images += 1
    
    print(f"移动模型成功，并带走 {moved_images} 张同名贴图")
    return True


def clean_orphan_thumbnails():
    """清理 .cache 里无用的缩略图垃圾（保留正在使用的和 placeholder）"""
    valid_thumbs = set()
    
    try:
        db = DatabaseManager()
        # 确保数据库已初始化
        db.initialize()
        
        # 尝试获取数据库里所有正在使用的缩略图路径（白名单）
        # 如果表不存在，会抛出异常，我们捕获它
        try:
            assets = db.get_all_assets()
            valid_thumbs = {asset.thumb_path for asset in assets if asset.thumb_path}
        except Exception as db_error:
            # 如果表不存在或其他数据库错误，使用空白名单
            print(f"[Warning] 无法读取数据库，跳过缩略图清理: {db_error}")
            valid_thumbs = set()
    except Exception as e:
        # 如果数据库初始化失败，使用空白名单（清理所有非 placeholder 文件）
        print(f"[Warning] 数据库初始化失败，跳过缩略图清理: {e}")
        valid_thumbs = set()
    
    cache_dir = get_cache_dir()  # data/.cache
    if not os.path.exists(cache_dir):
        return
    
    deleted_count = 0
    for filename in os.listdir(cache_dir):
        file_path = os.path.join(cache_dir, filename)
        if not os.path.isfile(file_path):
            continue
            
        # 跳过 placeholder 开头的系统占位图
        if filename.startswith("placeholder"):
            continue
            
        # 如果不在白名单里，就是垃圾 → 删除
        if file_path not in valid_thumbs:
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f"已删除垃圾缩略图: {filename}")
            except Exception as e:
                print(f"删除失败 {filename}: {e}")
    
    print(f"缩略图大扫除完成！共删除 {deleted_count} 个垃圾文件")

def delete_asset(file_path: str):
    """彻底删除一个资产：缩略图 + 模型文件 + 数据库记录"""
    if not os.path.exists(file_path):
        return False
        
    db = DatabaseManager()
    
    # 1. 先查出这模型对应的缩略图路径
    asset = db.get_asset_by_path(file_path)
    if asset and asset.thumb_path and os.path.exists(asset.thumb_path):
        try:
            os.remove(asset.thumb_path)
            print(f"已删除缩略图: {asset.thumb_path}")
        except Exception as e:
            print(f"缩略图删除失败: {e}")
    
    # 2. 再删模型文件本身
    try:
        os.remove(file_path)
        print(f"已删除模型文件: {file_path}")
    except Exception as e:
        print(f"模型文件删除失败: {e}")
        return False
    
    # 3. 最后删数据库记录
    db.delete_asset_by_path(file_path)
    print(f"已从数据库移除记录: {file_path}")
    return True


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  文件扫描与缩略图生成模块测试")
    print("=" * 60)

    # 检查 Pillow
    if HAS_PIL:
        print(f"\n[✓] Pillow 已安装: {Image.__version__}")
    else:
        print("\n[✗] Pillow 未安装")

    # 测试缓存目录
    cache_dir = get_cache_dir()
    print(f"\n[信息] 缩略图缓存目录: {cache_dir}")

    # 创建测试目录和文件
    test_dir = os.path.join(os.path.dirname(__file__), "_test_scan")
    os.makedirs(test_dir, exist_ok=True)

    # 创建测试文件
    test_files = [
        ("hero_character.fbx", "hero_character.png"),
        ("weapon_sword.obj", "weapon_sword.jpg"),
        ("vehicle_car.fbx", None),  # 无配对图片
        ("animation_walk.abc", None),
        ("scene_interior.gltf", "scene_interior.png"),
    ]

    print(f"\n[测试] 创建测试文件于: {test_dir}")

    for model_name, image_name in test_files:
        # 创建空模型文件
        model_path = os.path.join(test_dir, model_name)
        with open(model_path, "w") as f:
            f.write("")
        print(f"  ✓ 创建模型: {model_name}")

        # 创建配对图片
        if image_name and HAS_PIL:
            image_path = os.path.join(test_dir, image_name)
            img = Image.new("RGB", (512, 512), color=(100, 150, 200))
            img.save(image_path)
            print(f"  ✓ 创建图片: {image_name}")

    # 测试同名匹配
    print("\n[测试] 同名图片匹配...")
    test_model = os.path.join(test_dir, "hero_character.fbx")
    matched = find_matching_image(test_model)
    print(f"  模型: hero_character.fbx")
    print(f"  匹配: {os.path.basename(matched) if matched else '无'}")

    # 测试缩略图生成
    if matched and HAS_PIL:
        print("\n[测试] 缩略图生成...")
        thumb = generate_thumbnail(matched)
        print(f"  原图: {matched}")
        print(f"  缩略图: {thumb}")

    # 测试占位缩略图
    if HAS_PIL:
        print("\n[测试] 占位缩略图生成...")
        placeholder = generate_placeholder_thumbnail(".fbx")
        print(f"  FBX 占位图: {placeholder}")

    # 测试文件夹扫描
    print("\n[测试] 扫描文件夹...")

    def progress(file_path, current, total):
        print(f"  [{current}/{total}] {os.path.basename(file_path)}")

    result = scan_folder(test_dir, recursive=False, progress_callback=progress)
    print(f"\n  {result}")

    # 显示缓存大小
    size_bytes, size_str = get_cache_size()
    print(f"\n[信息] 缓存大小: {size_str}")

    # 清理测试文件
    print("\n[清理] 删除测试文件...")
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    print("  ✓ 测试目录已删除")

    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)