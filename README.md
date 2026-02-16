# MyAssetHub

A professional asset management application based on PySide6, designed specifically for 3D artists and developers, providing a clean and intuitive interface that supports the discovery, preview, and management of 3D assets.

## Project Structure

```
MyAssetHub/
├── MyAssetHub_Root/
│   ├── app/                    # Application main directory
│   │   ├── core/               # Core functionality modules
│   │   │   ├── db_manager.py   # Database management (supports SQLite)
│   │   │   ├── path_utils.py   # Path utility functions
│   │   │   └── watcher.py      # File scanning and thumbnail generation
│   │   ├── data/               # Data storage directory
│   │   │   ├── .cache/          # Thumbnail cache
│   │   │   │   └── .gitkeep    # Ensure cache directory is tracked by git
│   │   │   ├── config.json     # Configuration file
│   │   │   └── library.db      # SQLite database file
│   │   ├── ui/                 # User interface components
│   │   │   ├── assets_grid.py  # Asset grid view (supports 3D model display)
│   │   │   ├── main_window.py  # Main application window (three-column layout)
│   │   │   └── tree_view.py    # Tree view component (folder navigation)
│   │   ├── hot_reloader.py     # Development mode hot reload tool
│   │   ├── main.py             # Application entry point
│   │   ├── debug.log           # Debug log
│   │   └── error_log.txt       # Error log
│   └── build/                  # Build output directory
├── README.md                   # English documentation
├── README_zh.md                # Chinese documentation
├── README_PACKAGING.md         # Packaging instructions
├── DEPENDENCIES.md             # Dependencies documentation
├── run_app.bat                 # Run application script
├── run_dev.bat                 # Development mode run script
├── build_exe.bat               # Build executable script
├── logo/                       # Logo directory
│   └── logo.png                # Project logo
└── run_hub.exe                 # Packaged executable file
```

## Core Features

### 🔍 Asset Discovery and Management
- **Intelligent File Scanning**: Automatically discovers 3D asset files in specified directories
- **Hierarchical Management**: Displays folder structure through tree view, supports creating, renaming, and deleting folders
- **Quick Search**: Real-time search for asset names, quickly locate required resources

### 🖼️ Thumbnail System
- **Automatic Matching**: Intelligently identifies image files with the same name as models as thumbnails
- **Placeholder Thumbnails**: Generates placeholder thumbnails with format labels for 3D files without paired images
- **Cache Mechanism**: Generated thumbnails are cached to improve subsequent loading speed

### 📊 Intuitive Interface
- **Three-Column Layout**: Left tree navigation, middle grid preview, right property panel
- **Dark Theme**: Professional dark interface to reduce visual fatigue
- **Responsive Design**: Supports window size adjustment, adapts to different screen sizes

### 🗃️ Data Management
- **SQLite Database**: Uses local database to store asset information, improving loading speed
- **Metadata Management**: Stores asset file paths, sizes, modification times, and other information
- **Batch Operations**: Supports batch management and organization of assets

### ⚡ Development Tools
- **Hot Reload Support**: Automatically detects file changes and restarts the application in development mode
- **Detailed Logs**: Records application running status and error information

## Supported File Formats

### 3D Model Formats
- **Main Support**: .fbx, .obj, .abc, .gltf, .glb
- **Other Formats**: .max, .blend

### Image Formats (for thumbnails)
- .jpg, .jpeg, .png, .tga, .bmp

## System Requirements

- **Operating System**: Windows 10+
- **Python**: 3.8+ (only required for development mode)
- **Dependency Libraries**:
  - PySide6 (required, for GUI interface)
  - Pillow (optional, for thumbnail generation)
  - watchdog (optional, for hot reload functionality)

## Installation and Running

### Method 1: Run Executable File Directly
1. Double-click `run_hub.exe` file to start the application
2. The database will be automatically initialized on first startup

### Method 2: Use Batch Scripts
- **Normal Run**: Double-click `run_app.bat` script
- **Development Mode**: Double-click `run_dev.bat` script (supports hot reload)

### Method 3: Run from Source Code

```bash
# Enter the application directory
cd MyAssetHub_Root/app

# Install dependencies
pip install PySide6 Pillow watchdog

# Run application
python main.py

# Run in development mode (supports hot reload)
python main.py --dev
```

## Usage Guide

### Basic Operations
1. **Open Asset Directory**: Click the "📂 Open Directory" button on the toolbar, select the folder containing 3D assets
2. **Browse Assets**: Navigate folders through the left tree view, the middle grid will display 3D assets in the current folder
3. **View Asset Information**: Click on an asset in the grid, the right property panel will display detailed information
4. **Search Assets**: Enter keywords in the toolbar search box to filter assets in real-time

### Folder Operations
- **Create New Folder**: Right-click on the tree view, select "📁 New Folder"
- **Rename Folder**: Select a folder and press F2 or right-click and select "✏️ Rename"
- **Delete Folder**: Select a folder and press Delete or right-click and select "🗑️ Delete"
- **Open in Explorer**: Right-click on a folder, select "📂 Open in Explorer"

### Asset Preview
- **Thumbnail Preview**: Thumbnails of assets are displayed in the grid view
- **Detailed Information**: The right property panel displays the asset's name, type, size, and full path
- **Image Preview**: For supported image formats, a preview will be displayed in the property panel

## Advanced Features

### Development Mode
- **Hot Reload**: Automatically restarts the application after code changes, speeding up development iteration
- **Detailed Logs**: Console outputs detailed running information and error prompts

### Database Management
- **Automatic Initialization**: Automatically creates database structure on first run
- **Intelligent Updates**: Automatically updates information in the database after file modifications
- **Performance Optimization**: Uses indexes to speed up queries, supports management of large numbers of assets

### Thumbnail System
- **Intelligent Matching**: Automatically finds images with the same name as model files as thumbnails
- **Format Recognition**: Generates different color format labels based on file extensions
- **Cache Management**: Automatically manages thumbnail cache to avoid duplicate generation

## Dependencies

| Dependency | Version Requirement | Purpose | Required |
|-----------|-------------------|---------|----------|
| PySide6 | >= 6.0.0 | GUI interface implementation | Required |
| Pillow | >= 8.0.0 | Thumbnail generation | Optional |
| watchdog | >= 2.0.0 | File change monitoring (hot reload) | Optional |

## Development Guide

### Core Module Description

- **main.py**: Application entry point, responsible for initializing the environment and starting the main window
- **main_window.py**: Main application window, implements three-column layout and overall interface
- **tree_view.py**: Tree view component, provides folder navigation and management functions
- **assets_grid.py**: Asset grid view, displays 3D assets and thumbnails
- **db_manager.py**: Database management module, responsible for storage and query of asset information
- **watcher.py**: File scanning and thumbnail generation module
- **path_utils.py**: Path utility functions for handling file paths
- **hot_reloader.py**: Development mode hot reload functionality

### Code Style
- Follows PEP 8 coding standards
- Uses type annotations to improve code readability
- Modular design for easy maintenance and extension

## Troubleshooting

### Common Issues

1. **Cannot Generate Thumbnails**
   - Check if Pillow library is installed
   - Confirm if image file format is supported

2. **Application Startup Failure**
   - Check if Python environment is correct
   - View error_log.txt file for detailed error information

3. **Hot Reload Not Working**
   - Confirm watchdog library is installed
   - Ensure application is started with `--dev` parameter

4. **Database Connection Failure**
   - Check if library.db file exists and is writable
   - Try deleting library.db file, the application will automatically recreate it

### Log Files
- **debug.log**: Application running debug information
- **error_log.txt**: Application running error information

## License

MIT License

## Changelog

### Latest Version
- Implemented three-column layout professional interface
- Supported intelligent scanning and management of 3D assets
- Provided thumbnail generation and caching system
- Integrated SQLite database to improve performance
- Supported development mode hot reload

## Contribution

Welcome to submit Issues and Pull Requests to help improve MyAssetHub!

## Contact

If you have any questions or suggestions, please feel free to contact us.
