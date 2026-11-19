"""Frozen DD HEX entry point; startup failures stay local, without service links."""

import os
import sys
import time
import traceback


def _crash_log(text: str) -> str:
    base = os.environ.get("DDHEX_HOME")
    if not base:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.basename(exe_dir).lower() == "runtime":
            exe_dir = os.path.dirname(exe_dir)
        if os.path.isfile(os.path.join(exe_dir, "portable.txt")):
            base = os.path.join(exe_dir, "userdata")
        else:
            base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DD HEX")
    try:
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, "crash.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n{text}\n")
        return path
    except OSError:
        return ""


def _crash(text: str) -> None:
    path = _crash_log(text)
    msg = ("DD HEX 海克斯助手打不开了。\n\n"
           "请从此独立版本的维护者处获取完整安装包，覆盖安装后重试。\n"
           "程序不会自动上传错误记录。")
    if path:
        msg += f"\n\n错误记录：{path}"
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, "DD HEX 海克斯助手", 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from lolhex.__main__ import main
        code = main()
    except SystemExit:
        raise
    except BaseException:
        _crash(traceback.format_exc())
        code = 1
    sys.exit(code)
