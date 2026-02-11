# app/core/db_manager.py

"""
数据库管理模块 - 管理3D资产的SQLite数据库。

提供资产元数据的持久化存储，包括文件路径、缩略图路径、
文件大小、修改时间等信息。
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Generator


# ══════════════════════════════════════════════════════════════════
#  数据模型
# ══════════════════════════════════════════════════════════════════

@dataclass
class AssetRecord:
    """资产记录数据类。"""
    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    thumb_path: str = ""
    file_size: str = ""
    mtime: float = 0.0
    comment: str = ""  # 新增：备注
    tags: str = ""     # 新增：标签（以逗号分隔的字符串）

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "thumb_path": self.thumb_path,
            "file_size": self.file_size,
            "mtime": self.mtime,
            "comment": self.comment,
            "tags": self.tags,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "AssetRecord":
        """从数据库行创建记录。"""
        return cls(
            id=row[0],
            file_path=row[1],
            file_name=row[2],
            thumb_path=row[3],
            file_size=row[4],
            mtime=row[5],
            comment=row[6] if len(row) > 6 else "",
            tags=row[7] if len(row) > 7 else "",
        )


# ══════════════════════════════════════════════════════════════════
#  数据库管理器
# ══════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    SQLite 数据库管理器。
    
    线程安全，支持连接池和事务管理。
    
    使用示例：
        db = DatabaseManager("assets.db")
        db.initialize()
        
        # 插入或更新资产
        db.upsert_asset(AssetRecord(
            file_path="/path/to/model.fbx",
            file_name="model.fbx",
            thumb_path="/path/to/model.png",
            file_size="2.4 MB",
            mtime=1234567890.0
        ))
        
        # 查询资产
        asset = db.get_asset_by_path("/path/to/model.fbx")
        
        # 搜索资产
        results = db.search_assets("model")
    """

    # 建表 SQL
    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT UNIQUE NOT NULL,
            file_name   TEXT NOT NULL,
            thumb_path  TEXT DEFAULT '',
            file_size   TEXT DEFAULT '',
            mtime       REAL DEFAULT 0.0,
            comment     TEXT DEFAULT '',
            tags        TEXT DEFAULT ''
        )
    """

    # 配置表 SQL
    _CREATE_CONFIG_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS config (
            key         TEXT PRIMARY KEY,
            value       TEXT
        )
    """

    # 索引 SQL
    _CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_file_path ON assets(file_path)",
        "CREATE INDEX IF NOT EXISTS idx_file_name ON assets(file_name)",
        "CREATE INDEX IF NOT EXISTS idx_mtime ON assets(mtime)",
    ]

    def __init__(self, db_path: str = "assets.db"):
        """
        初始化数据库管理器。
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的 assets.db
        """
        self._db_path = os.path.abspath(db_path)
        self._local = threading.local()
        self._lock = threading.RLock()

    @property
    def db_path(self) -> str:
        """数据库文件路径。"""
        return self._db_path

    # ================================================================
    #  连接管理
    # ================================================================

    def _get_connection(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（线程安全）。"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0,
            )
            # 启用外键约束
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # 优化写入性能
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            self._local.connection.execute("PRAGMA synchronous = NORMAL")
        return self._local.connection

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """获取游标的上下文管理器。"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """事务上下文管理器，用于批量操作。"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def close(self) -> None:
        """关闭当前线程的数据库连接。"""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    # ================================================================
    #  初始化
    # ================================================================

    def initialize(self) -> None:
        """
        初始化数据库：创建表和索引。
        
        如果表已存在，此操作是安全的（使用 IF NOT EXISTS）。
        """
        # 确保目录存在
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with self._cursor() as cursor:
            # 创建表
            cursor.execute(self._CREATE_TABLE_SQL)
            cursor.execute(self._CREATE_CONFIG_TABLE_SQL)
            
            # 检查 assets 表是否需要迁移（如果之前已经存在但没有 comment/tags 字段）
            cursor.execute("PRAGMA table_info(assets)")
            columns = [col[1] for col in cursor.fetchall()]
            if "comment" not in columns:
                cursor.execute("ALTER TABLE assets ADD COLUMN comment TEXT DEFAULT ''")
            if "tags" not in columns:
                cursor.execute("ALTER TABLE assets ADD COLUMN tags TEXT DEFAULT ''")

            # 创建索引
            for index_sql in self._CREATE_INDEXES_SQL:
                cursor.execute(index_sql)

        print(f"[DatabaseManager] 数据库已初始化: {self._db_path}")

    def reset(self) -> None:
        """重置数据库：删除所有数据并重新创建表。"""
        with self._cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS assets")
            cursor.execute(self._CREATE_TABLE_SQL)
            for index_sql in self._CREATE_INDEXES_SQL:
                cursor.execute(index_sql)

        print("[DatabaseManager] 数据库已重置")

    # ================================================================
    #  插入 / 更新操作
    # ================================================================

    def upsert_asset(self, asset: AssetRecord) -> int:
        """
        插入或更新资产记录。
        
        如果 file_path 已存在，则更新记录；否则插入新记录。
        
        Args:
            asset: 资产记录
            
        Returns:
            资产的 ID
        """
        sql = """
            INSERT INTO assets (file_path, file_name, thumb_path, file_size, mtime, comment, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_name = excluded.file_name,
                thumb_path = excluded.thumb_path,
                file_size = excluded.file_size,
                mtime = excluded.mtime,
                comment = CASE WHEN excluded.comment != '' THEN excluded.comment ELSE assets.comment END,
                tags = CASE WHEN excluded.tags != '' THEN excluded.tags ELSE assets.tags END
        """
        with self._cursor() as cursor:
            cursor.execute(sql, (
                asset.file_path,
                asset.file_name,
                asset.thumb_path,
                asset.file_size,
                asset.mtime,
                asset.comment,
                asset.tags,
            ))
            # 获取 ID
            cursor.execute(
                "SELECT id FROM assets WHERE file_path = ?",
                (asset.file_path,)
            )
            row = cursor.fetchone()
            return row[0] if row else -1

    def upsert_assets_batch(self, assets: list[AssetRecord]) -> int:
        """
        批量插入或更新资产记录。
        
        Args:
            assets: 资产记录列表
            
        Returns:
            成功处理的记录数
        """
        if not assets:
            return 0

        sql = """
            INSERT INTO assets (file_path, file_name, thumb_path, file_size, mtime, comment, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_name = excluded.file_name,
                thumb_path = excluded.thumb_path,
                file_size = excluded.file_size,
                mtime = excluded.mtime,
                comment = CASE WHEN excluded.comment != '' THEN excluded.comment ELSE assets.comment END,
                tags = CASE WHEN excluded.tags != '' THEN excluded.tags ELSE assets.tags END
        """
        data = [
            (a.file_path, a.file_name, a.thumb_path, a.file_size, a.mtime, a.comment, a.tags)
            for a in assets
        ]

        with self.transaction() as cursor:
            cursor.executemany(sql, data)
            return cursor.rowcount if cursor.rowcount > 0 else len(assets)

    def insert_asset(self, asset: AssetRecord) -> Optional[int]:
        """
        插入新资产记录（不更新已存在的）。
        
        Args:
            asset: 资产记录
            
        Returns:
            资产 ID，如果记录已存在返回 None
        """
        sql = """
            INSERT OR IGNORE INTO assets (file_path, file_name, thumb_path, file_size, mtime)
            VALUES (?, ?, ?, ?, ?)
        """
        with self._cursor() as cursor:
            cursor.execute(sql, (
                asset.file_path,
                asset.file_name,
                asset.thumb_path,
                asset.file_size,
                asset.mtime,
            ))
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None

    def update_asset(self, asset: AssetRecord) -> bool:
        """
        更新现有资产记录。
        
        Args:
            asset: 资产记录（需要包含 file_path）
            
        Returns:
            是否成功更新
        """
        sql = """
            UPDATE assets SET
                file_name = ?,
                thumb_path = ?,
                file_size = ?,
                mtime = ?
            WHERE file_path = ?
        """
        with self._cursor() as cursor:
            cursor.execute(sql, (
                asset.file_name,
                asset.thumb_path,
                asset.file_size,
                asset.mtime,
                asset.file_path,
            ))
            return cursor.rowcount > 0

    def update_thumb_path(self, file_path: str, thumb_path: str) -> bool:
        """
        仅更新资产的缩略图路径。
        
        Args:
            file_path: 资产文件路径
            thumb_path: 新的缩略图路径
            
        Returns:
            是否成功更新
        """
        sql = "UPDATE assets SET thumb_path = ? WHERE file_path = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (thumb_path, file_path))
            return cursor.rowcount > 0

    def update_metadata(self, file_path: str, comment: str = None, tags: str = None) -> bool:
        """
        更新资产的元数据（备注和标签）。
        
        Args:
            file_path: 资产文件路径
            comment: 备注内容
            tags: 标签内容（字符串）
            
        Returns:
            是否成功更新
        """
        updates = []
        params = []
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        
        if not updates:
            return False
            
        params.append(file_path)
        sql = f"UPDATE assets SET {', '.join(updates)} WHERE file_path = ?"
        
        with self._cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # ================================================================
    #  配置操作
    # ================================================================

    def set_config(self, key: str, value: str) -> None:
        """设置配置项。"""
        sql = "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)"
        with self._cursor() as cursor:
            cursor.execute(sql, (key, value))

    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """获取配置项。"""
        sql = "SELECT value FROM config WHERE key = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def save_last_project(self, project_path: str) -> None:
        """保存最后打开的项目路径。"""
        if project_path:
            self.set_config("last_project_path", os.path.abspath(project_path))

    def get_last_project(self) -> Optional[str]:
        """获取最后一次打开的项目路径。"""
        path = self.get_config("last_project_path")
        if path and os.path.exists(path):
            return path
        return None

    # ================================================================
    #  查询操作
    # ================================================================

    def get_asset_by_id(self, asset_id: int) -> Optional[AssetRecord]:
        """根据 ID 获取资产记录。"""
        sql = "SELECT id, file_path, file_name, thumb_path, file_size, mtime FROM assets WHERE id = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (asset_id,))
            row = cursor.fetchone()
            return AssetRecord.from_row(row) if row else None

    def get_asset_by_path(self, file_path: str) -> Optional[AssetRecord]:
        """根据文件路径获取资产记录。"""
        sql = "SELECT id, file_path, file_name, thumb_path, file_size, mtime FROM assets WHERE file_path = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (file_path,))
            row = cursor.fetchone()
            return AssetRecord.from_row(row) if row else None

    def get_all_assets(self, limit: int = 0, offset: int = 0) -> list[AssetRecord]:
        """
        获取所有资产记录。
        
        Args:
            limit: 限制返回数量，0 表示不限制
            offset: 偏移量
            
        Returns:
            资产记录列表
        """
        sql = "SELECT id, file_path, file_name, thumb_path, file_size, mtime FROM assets ORDER BY mtime DESC"
        if limit > 0:
            sql += f" LIMIT {limit} OFFSET {offset}"

        with self._cursor() as cursor:
            cursor.execute(sql)
            return [AssetRecord.from_row(row) for row in cursor.fetchall()]

    def get_assets_by_folder(self, folder_path: str) -> list[AssetRecord]:
        """
        获取指定文件夹下的所有资产。
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            资产记录列表
        """
        # 确保路径以分隔符结尾，避免匹配到同名前缀的其他文件夹
        folder_path = os.path.abspath(folder_path)
        if not folder_path.endswith(os.sep):
            folder_path += os.sep

        sql = """
            SELECT id, file_path, file_name, thumb_path, file_size, mtime, comment, tags 
            FROM assets 
            WHERE file_path LIKE ? 
            ORDER BY file_name
        """
        with self._cursor() as cursor:
            cursor.execute(sql, (folder_path + "%",))
            return [AssetRecord.from_row(row) for row in cursor.fetchall()]

    def get_assets_recursive(self, parent_path: str) -> list[AssetRecord]:
        """
        递归获取父文件夹及其所有子文件夹下的资产。
        
        Args:
            parent_path: 父文件夹路径
            
        Returns:
            资产记录列表
        """
        # 与 get_assets_by_folder 逻辑一致，因为 LIKE 'path/%' 本身就是递归的
        return self.get_assets_by_folder(parent_path)

    def search_assets(
        self,
        keyword: str,
        limit: int = 100,
    ) -> list[AssetRecord]:
        """
        搜索资产（按文件名模糊匹配）。
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果上限
            
        Returns:
            匹配的资产记录列表
        """
        sql = """
            SELECT id, file_path, file_name, thumb_path, file_size, mtime 
            FROM assets 
            WHERE file_name LIKE ? 
            ORDER BY mtime DESC
            LIMIT ?
        """
        with self._cursor() as cursor:
            cursor.execute(sql, (f"%{keyword}%", limit))
            return [AssetRecord.from_row(row) for row in cursor.fetchall()]

    def asset_exists(self, file_path: str) -> bool:
        """检查资产是否存在于数据库中。"""
        sql = "SELECT 1 FROM assets WHERE file_path = ? LIMIT 1"
        with self._cursor() as cursor:
            cursor.execute(sql, (file_path,))
            return cursor.fetchone() is not None

    def get_asset_mtime(self, file_path: str) -> Optional[float]:
        """获取资产的修改时间。"""
        sql = "SELECT mtime FROM assets WHERE file_path = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (file_path,))
            row = cursor.fetchone()
            return row[0] if row else None

    # ================================================================
    #  删除操作
    # ================================================================

    def delete_asset_by_id(self, asset_id: int) -> bool:
        """根据 ID 删除资产记录。"""
        sql = "DELETE FROM assets WHERE id = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (asset_id,))
            return cursor.rowcount > 0

    def delete_asset_by_path(self, file_path: str) -> bool:
        """根据文件路径删除资产记录。"""
        sql = "DELETE FROM assets WHERE file_path = ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (file_path,))
            return cursor.rowcount > 0

    def delete_assets_by_folder(self, folder_path: str) -> int:
        """
        删除指定文件夹下的所有资产记录。
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            删除的记录数
        """
        folder_path = os.path.abspath(folder_path)
        if not folder_path.endswith(os.sep):
            folder_path += os.sep

        sql = "DELETE FROM assets WHERE file_path LIKE ?"
        with self._cursor() as cursor:
            cursor.execute(sql, (folder_path + "%",))
            return cursor.rowcount

    def delete_missing_assets(self) -> int:
        """
        删除所有文件不存在的资产记录。
        
        Returns:
            删除的记录数
        """
        assets = self.get_all_assets()
        missing_ids = [a.id for a in assets if not os.path.exists(a.file_path)]

        if not missing_ids:
            return 0

        placeholders = ",".join("?" * len(missing_ids))
        sql = f"DELETE FROM assets WHERE id IN ({placeholders})"

        with self._cursor() as cursor:
            cursor.execute(sql, missing_ids)
            return cursor.rowcount

    # ================================================================
    #  统计信息
    # ================================================================

    def count_assets(self) -> int:
        """获取资产总数。"""
        sql = "SELECT COUNT(*) FROM assets"
        with self._cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_statistics(self) -> dict:
        """
        获取数据库统计信息。
        
        Returns:
            统计信息字典，包含资产总数、各类型数量等
        """
        stats = {
            "total_assets": 0,
            "assets_with_thumb": 0,
            "assets_by_type": {},
        }

        with self._cursor() as cursor:
            # 总数
            cursor.execute("SELECT COUNT(*) FROM assets")
            stats["total_assets"] = cursor.fetchone()[0]

            # 有缩略图的资产数
            cursor.execute("SELECT COUNT(*) FROM assets WHERE thumb_path != ''")
            stats["assets_with_thumb"] = cursor.fetchone()[0]

            # 按类型统计
            cursor.execute("""
                SELECT 
                    LOWER(SUBSTR(file_name, INSTR(file_name, '.'), LENGTH(file_name))) as ext,
                    COUNT(*) as count
                FROM assets
                GROUP BY ext
                ORDER BY count DESC
            """)
            for row in cursor.fetchall():
                ext = row[0] if row[0] else "unknown"
                stats["assets_by_type"][ext] = row[1]

        return stats


# ══════════════════════════════════════════════════════════════════
#  全局单例
# ══════════════════════════════════════════════════════════════════

_db_instance: Optional[DatabaseManager] = None
_db_lock = threading.Lock()


def get_database(db_path: str = "assets.db") -> DatabaseManager:
    """
    获取数据库管理器单例。
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        DatabaseManager 实例
    """
    global _db_instance
    with _db_lock:
        if _db_instance is None:
            _db_instance = DatabaseManager(db_path)
            _db_instance.initialize()
        return _db_instance


def close_database() -> None:
    """关闭全局数据库连接。"""
    global _db_instance
    with _db_lock:
        if _db_instance:
            _db_instance.close()
            _db_instance = None


# ══════════════════════════════════════════════════════════════════
#  命令行测试
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time

    print("=" * 60)
    print("  DatabaseManager 测试")
    print("=" * 60)

    # 创建测试数据库
    test_db_path = "_test_assets.db"
    db = DatabaseManager(test_db_path)
    db.initialize()

    # 测试插入
    print("\n[测试] 插入资产记录...")
    test_assets = [
        AssetRecord(
            file_path="/models/hero.fbx",
            file_name="hero.fbx",
            thumb_path="/models/hero.png",
            file_size="2.4 MB",
            mtime=time.time(),
        ),
        AssetRecord(
            file_path="/models/weapon.obj",
            file_name="weapon.obj",
            thumb_path="/models/weapon.jpg",
            file_size="1.2 MB",
            mtime=time.time() - 3600,
        ),
        AssetRecord(
            file_path="/models/vehicle.fbx",
            file_name="vehicle.fbx",
            thumb_path="",
            file_size="5.8 MB",
            mtime=time.time() - 7200,
        ),
    ]

    for asset in test_assets:
        asset_id = db.upsert_asset(asset)
        print(f"  ✓ 已插入: {asset.file_name} (ID: {asset_id})")

    # 测试查询
    print("\n[测试] 查询资产...")
    all_assets = db.get_all_assets()
    print(f"  总资产数: {len(all_assets)}")

    # 测试按路径查询
    print("\n[测试] 按路径查询...")
    asset = db.get_asset_by_path("/models/hero.fbx")
    if asset:
        print(f"  找到资产: {asset.file_name}, 大小: {asset.file_size}")

    # 测试搜索
    print("\n[测试] 搜索资产...")
    results = db.search_assets("hero")
    print(f"  搜索 'hero' 结果: {len(results)} 条")

    # 测试统计
    print("\n[测试] 获取统计信息...")
    stats = db.get_statistics()
    print(f"  总资产: {stats['total_assets']}")
    print(f"  有缩略图: {stats['assets_with_thumb']}")
    print(f"  类型分布: {stats['assets_by_type']}")

    # 测试更新
    print("\n[测试] 更新缩略图路径...")
    success = db.update_thumb_path("/models/vehicle.fbx", "/models/vehicle_thumb.png")
    print(f"  更新结果: {'成功' if success else '失败'}")

    # 测试删除
    print("\n[测试] 删除资产...")
    deleted = db.delete_asset_by_path("/models/weapon.obj")
    print(f"  删除结果: {'成功' if deleted else '失败'}")
    print(f"  剩余资产: {db.count_assets()}")

    # 清理
    db.close()
    os.remove(test_db_path)
    print("\n[完成] 测试数据库已删除")
    print("=" * 60)