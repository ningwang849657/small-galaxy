"""小银河 Small Galaxy —— 只跑在本机的科研时间仪表盘。"""
import sys
from pathlib import Path

__version__ = "0.2.0"


def asset_dir() -> Path:
    """CSS / JS / 图标的所在目录。

    三种运行方式都要能找到它：源码直接跑、pip 装进 site-packages、
    以及 PyInstaller 打包后解压到临时目录（那时路径在 sys._MEIPASS 下）。
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled) / "smallgalaxy" / "assets"
    return Path(__file__).resolve().parent / "assets"


DATA_DIR = Path.home() / ".lab_tracker"
