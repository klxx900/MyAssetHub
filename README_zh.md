# AssetHub

一个基于PySide6的资产管理应用程序，具有简洁直观的界面，支持3D资产的发现、预览和管理。

## 项目结构

```
MyAssetHub/
├── MyAssetHub_Root/
│   ├── app/
│   │   ├── core (核心逻辑)/
│   │   │   ├── db_manager.py    # 数据库管理
│   │   │   ├── tree_view.py      # 树视图数据模型
│   │   │   └── watcher.py        # 文件扫描与缩略图生成
│   │   ├── data (便携数据)/
│   │   │   ├── .cache (缩略图)/   # 缩略图缓存目录
│   │   │   ├── config.json       # 配置文件
│   │   │   └── library.db        # SQLite数据库
│   │   ├── ui/
│   │   │   ├── assets_grid.py    # 资产网格视图
│   │   │   ├── main_window.py    # 主应用窗口
│   │   │   └── tree_view.py      # 树视图组件
│   │   ├── hot_reloader.py       # 热重载工具
│   │   └── main.py               # 应用入口
│   └── run_hub.exe               # 打包的可执行文件
├── README_zh.md                  # 中文文档
└── 启动程序.ps1                   # 启动脚本
```

## 核心功能

- 自动扫描文件夹，发现3D资产文件
- 为资产生成缩略图（支持与模型同名的图片匹配）
- 为无配对图片的3D文件生成占位缩略图
- 支持资产的分类和层次结构管理
- 快速预览和访问资产文件
- 数据库存储资产信息，提高加载速度

## 支持的文件格式

- **3D模型**：.fbx, .obj, .max, .abc, .blend, .gltf, .glb
- **图片**：.jpg, .jpeg, .png, .tga, .bmp

## 系统要求

- Python 3.8+
- PySide6
- Pillow (可选，用于缩略图生成)

## 安装

```bash
# 安装核心依赖
pip install PySide6

# 安装可选依赖（用于缩略图生成）
pip install Pillow
```

## 使用方法

### 方式一：直接运行

```bash
cd MyAssetHub_Root/app
python main.py
```

### 方式二：双击启动

双击运行 `启动程序.ps1` 脚本文件即可启动应用程序。

### 方式三：使用可执行文件

双击 `MyAssetHub_Root/run_hub.exe` 可执行文件启动应用程序。

## 依赖说明

- **PySide6**：必需，用于GUI界面
- **Pillow**：可选，用于缩略图生成。如果未安装，模块仍可运行，但缩略图功能不可用

## 开发

该项目使用PySide6实现GUI，使用SQLite存储数据，遵循现代Python编码实践。

### 核心模块说明

- **watcher.py**：文件扫描与缩略图生成模块
- **db_manager.py**：数据库管理模块
- **assets_grid.py**：资产网格视图组件
- **tree_view.py**：资产层次树视图组件
- **main_window.py**：主应用窗口实现

## 许可证

MIT License