"""开机自启：写入 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run（当前用户，不需要管理员）。"""

from __future__ import annotations

import sys
import subprocess

from ..config import program_dir

KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "DD HEX"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    launcher = program_dir() / "DD HEX.exe"
    if (program_dir() / "portable.txt").is_file() and launcher.is_file():
        return subprocess.list2cmdline([str(launcher), "--minimized"])
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    # Windows 登录时工作目录不在源码仓库，显式定位本版本，避免导入失败或误载别的 lolhex。
    script = f"import sys; sys.path.insert(0, {str(program_dir())!r}); from lolhex.__main__ import main; main()"
    return subprocess.list2cmdline([exe, "-c", script, "--minimized"])


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            winreg.QueryValueEx(k, NAME)
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg
    if on:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, _command())
    else:
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            return  # 全新账号连 Run 键都没有：本来就没开自启，无需创建或报错
        with k:
            try:
                winreg.DeleteValue(k, NAME)
            except FileNotFoundError:
                pass
