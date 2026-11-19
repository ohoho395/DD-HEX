"""Independent distribution identity and opt-in update policy.

Set UPDATE_REPO to a repository you control before publishing updates. An empty
value deliberately disables application update networking; there is no fallback.
Statistics remain separately attributed to their original noncommercial source.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

APP_NAME = "DD HEX 海克斯助手"
APP_ID = "DDHEX.Desktop"
UPDATE_REPO = ""
UPSTREAM_REPO = "czgreat/aramhex"
DATA_REPO = "czgreat/aramhex-data"
DATA_RAW_URL = f"https://raw.githubusercontent.com/{DATA_REPO}/main"


def update_repo() -> str:
    value = UPDATE_REPO.strip()
    if not value:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("UPDATE_REPO 必须是自己维护的 owner/repository")
    if value.casefold() in (UPSTREAM_REPO.casefold(), DATA_REPO.casefold()):
        raise ValueError("独立版本不能使用原作者的程序或数据仓库作为程序更新源")
    return value


def update_api() -> str:
    repo = update_repo()
    return f"https://api.github.com/repos/{repo}/releases/latest" if repo else ""


def releases_page() -> str:
    repo = update_repo()
    return f"https://github.com/{repo}/releases" if repo else ""


def reject_upstream_update(url: str) -> None:
    """Guard explicit developer URLs too; loopback test servers remain usable."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold()
    path = unquote(parsed.path).casefold()
    if (host in {"aramhex.com", "aramhex.cn"} or host.endswith((".aramhex.com", ".aramhex.cn"))
            or re.search(r"/(?:repos/|gh/)?czgreat/aramhex(?:-data)?(?:/|@|$)", path)):
        raise ValueError("不能从原作者服务更新 DD HEX 程序")
