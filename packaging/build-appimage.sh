#!/usr/bin/env bash
# 打一个 Linux AppImage：用户下载、chmod +x、双击即用，不需要装 Python，
# 也不需要装 xprintidle（采样走 ctypes 直接调 libX11/libXss）。
#
#   ./packaging/build-appimage.sh
#
# 需要：python3、wget。首次运行会下载 appimagetool（约 10 MB）到 build/。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
APPDIR="$BUILD/SmallGalaxy.AppDir"
ARCH="$(uname -m)"
TOOL="$BUILD/appimagetool-$ARCH.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/scalable/apps" "$BUILD"

# 1. 把包和它的资源装进 AppDir。--target 装成扁平目录，AppRun 再把它加进 PYTHONPATH。
python3 -m pip install --quiet --no-compile --target "$APPDIR/usr/lib" "$ROOT"

# 2. AppRun：AppImage 被双击时执行的入口。
cat > "$APPDIR/AppRun" <<'LAUNCHER'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$HERE/usr/lib:${PYTHONPATH:-}"
# 没有参数就打开仪表盘；传 --daemon 则跑后台采样。
if [ "${1:-}" = "--daemon" ]; then
  shift
  exec python3 -m smallgalaxy.lab_tracker "$@"
fi
exec python3 -m smallgalaxy.dashboard "$@"
LAUNCHER
chmod +x "$APPDIR/AppRun"

# 3. 桌面环境要靠这两个文件认出图标和名字。
cat > "$APPDIR/small-galaxy.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=小银河
Name[en]=Small Galaxy
Comment=查看最近 14 天的科研时间仪表盘
Exec=AppRun
Icon=small-galaxy
Terminal=false
Categories=Utility;
ENTRY
cp "$ROOT/smallgalaxy/assets/icons/galaxy.svg" "$APPDIR/small-galaxy.svg"
cp "$ROOT/smallgalaxy/assets/icons/galaxy.svg" \
   "$APPDIR/usr/share/icons/hicolor/scalable/apps/small-galaxy.svg"

# 4. 打包。appimagetool 自己也是个 AppImage。
if [ ! -x "$TOOL" ]; then
  wget -q -O "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
  chmod +x "$TOOL"
fi
ARCH="$ARCH" "$TOOL" --no-appstream "$APPDIR" "$BUILD/SmallGalaxy-$ARCH.AppImage"

echo
echo "打好了: $BUILD/SmallGalaxy-$ARCH.AppImage"
echo "试跑:   $BUILD/SmallGalaxy-$ARCH.AppImage"
echo "后台:   $BUILD/SmallGalaxy-$ARCH.AppImage --daemon"
