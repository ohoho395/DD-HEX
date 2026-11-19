"""DD HEX 海克斯助手：独立衍生版，保留截图识别和本地统计推荐。"""

import os as _os
from pathlib import Path as _Path

__version__ = "0.1.2"
# 测试包：packaging/build.ps1 -TestTag test.1 打包时临时生成 _build.py，版本号变成「1.1.3-test.1」。
# 发出去的测试包比正式版 1.1.3 旧，正式版一发就会提示更新；正式发布（GitHub Actions）不生成这个文件
try:
    from ._build import TEST_TAG as _TEST_TAG
    __version__ += f"-{_TEST_TAG}"
except ImportError:
    pass

# 根证书：用 lolhex/data/cacert.pem（certifi 的去掉 eMudhra，见 scripts/make_cacert.py）。
# 放在这里，所有入口（界面、增量更新、命令行）联网前都已生效；用户自己设了 REQUESTS_CA_BUNDLE（公司代理等）就不动
_CA = _Path(__file__).resolve().parent / "data" / "cacert.pem"
if _CA.is_file():
    _os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_CA))
# 测试版：调试模式（详细日志、三选一和选英雄时自动截图），方便事后查问题。正式版为 False
BETA = False

from .distribution import APP_ID, APP_NAME, DATA_REPO, update_repo

GITHUB_REPO = update_repo()
# Service roots intentionally empty. Attribution is not a runtime service.
WEBSITE = ""
BACKUP_SITES = ()
HELP_PAGE = ""
MIRROR = ""
HOMEPAGE = ""
RELEASES_PAGE = ""
DATA_HOMEPAGE = f"https://github.com/{DATA_REPO}"
