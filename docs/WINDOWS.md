# Windows 10/11 安装、运行与 EXE 打包

适用 DD HEX 0.1.2。目标为 Windows 10/11 x64 + Python 3.13 x64。当前提交的测试环境与未验证项见 [VERIFICATION.md](VERIFICATION.md)。本次提供 Windows x64 免安装便携包。完整解压 ZIP 到可写目录，双击 DD HEX.exe。内置 Python 3.13.13，无需安装 Python。遇到启动问题可双击 Self-Test.cmd 生成 self-test.json，或用 Start.cmd 查看报错。本包在 Mac 组装并做静态检查，Windows 实机尚待试用。下面的 Python 安装步骤仅供源码开发。

## 1. 安装依赖

安装 Python 3.13 x64（Python 官网），在解压后的 `DD HEX` 根目录打开 PowerShell。不要在压缩包预览里运行：

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

固定依赖版本沿用原仓库，没有新增运行依赖。OCR 只加载校验通过的随包模型，缺失或损坏时请重装依赖/完整安装包，不会自动下载。无需激活虚拟环境，无需更改 PowerShell 执行策略。若 `py` 不存在，安装 Python 启动器或将命令改成已安装的 Python 3.13 完整路径；避免误用 Windows Store 别名或 32 位 Python。

## 2. 先验证离线流程

```powershell
.\.venv\Scripts\python.exe -m lolhex --demo --hero 提莫
.\.venv\Scripts\python.exe -m lolhex --demo --hero 提莫 --augments 1029,2128,1373
```

第一条自动挑选这个英雄内置样本里场次较多的三项，第二条手工指定三张卡（支持中文名或 ID，也支持四张）。输出真实内置数据的推荐 JSON、样本数、理由与数据版本，不代表识别到了游戏画面。英雄或海克斯参数无效时返回错误码 2。

## 3. 正常使用

```powershell
.\.venv\Scripts\python.exe -m lolhex
```

1. 游戏设置成无边框或窗口化，启动助手。
2. 在搜索框选一个英雄，查看出装、加点和海克斯表，确认本地数据能显示。数据页上方可切换分段；统计没有该分段时会标明实际口径。
3. 设置页调整游戏语言、浮窗位置、三选一标签位置和详情快捷键（默认空，推荐先保持禁用）。
4. 新的推荐参数：显示胜率数字；平滑强度 0–10000 局，默认 300；首选样本门槛 100–100000 局，默认 1000。平滑越大越保守，门槛越高越重视样本。全部不足门槛时仍作比较，并显示仅供参考。降低门槛不会消除同屏相差十倍的样本保护。样本分档固定为 <250 / 250–999 / ≥1000，与可调的首选门槛分别表示不同信息。
5. 进入游戏，选英雄和海克斯时自动截图识别并显示浮窗。英雄未识别时手动搜索；全英雄数据回退会明确提示。推荐卡显示场次和胜率，鼠标悬停查看评分理由。
6. 修改立即生效并自动保存；重启保留偏好。关闭主窗口会缩到托盘，托盘菜单「退出」才会停止。

软件更新源未配置时，点「检查更新」会明确说明未检查软件版本。统计更新默认关闭，点此按钮不会绕过关闭设置。确实需要刷新公开统计时，先勾选「从公开 GitHub 更新统计（仅限非商业使用）」；数据线程会被唤醒，或点击检查更新立即尝试，下载失败继续用本地快照。没有独立官方资料服务器，因此不会在线刷新腾讯资料。

## 4. 配置与调试

安装/源码默认目录：`%APPDATA%\DD HEX`。便携版：`DD HEX.exe` 旁有 `portable.txt`，使用同目录 `userdata`。可覆盖目录（路径建议不带末尾反斜杠）：

```powershell
$env:DDHEX_HOME = "$PWD\my-userdata"
.\.venv\Scripts\python.exe -m lolhex
```

不会读取原版 `%APPDATA%\AramHex` 或 `ARAMHEX_HOME`，无需迁移旧配置。配置文件 `config.json` 支持 UTF-8/BOM；损坏时保留 `.broken` 备份。日志为 `ddhex.log`。

对一张本地游戏截图运行真实 OCR：

```powershell
.\.venv\Scripts\python.exe -m lolhex --scan-image "C:\Screenshots\offer.png" --hero 提莫
```

返回码 0 表示识别到选择画面；1 表示未识别；2 表示无法读取图片。该入口与实时截屏共用 OCR 和推荐模块，但截图文件结果不能替代真实对局验证。

```powershell
.\.venv\Scripts\python.exe -m lolhex --debug
```

或在程序/数据目录放空的 `debug.txt`，退出并重启。调试会保存截图，分享前检查隐私；删标记并重启可关闭。不要为了运行应用而关闭杀毒或系统安全功能，未知来源的 EXE 应先核对来源、校验和与安全扫描结果。

## 5. 测试

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q lolhex scripts packaging
Remove-Item Env:\QT_QPA_PLATFORM
```

部分更新测试会启动仅绑定 `127.0.0.1` 的临时 HTTP 服务，需要允许本地监听。正常游戏测试和打包自检前移除 `QT_QPA_PLATFORM=offscreen`，否则无法验证真实 Windows 窗口插件。

## 6. 打包便携 EXE

必须在 Windows x64 上打包 Windows EXE，不能用 macOS 构建结果冒充 Windows 产物。构建先使用已提交的内置数据，不需要运行任何联网资料刷新脚本。

安装 PowerShell 7（`pwsh`），然后：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts\check_release_data.py
Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
pwsh -NoProfile -File packaging\build.ps1 -PortableOnly
```

输出：`build\release\DDHEX-Portable-0.1.0.zip`、`SHA256SUMS.txt`。解压整个文件夹，运行 `DD HEX.exe`。必须保留 `_internal`、OCR 模型、Qt 动态库、证书和许可证文件；不能只复制 EXE。目标机器无需另装 Python。

## 7. 打包安装版

安装 Inno Setup 6：

```powershell
winget install --id JRSoftware.InnoSetup -e
pwsh -NoProfile -File packaging\build.ps1
```

若未自动找到编译器，用 `-InnoCompiler "C:\实际路径\ISCC.exe"`。脚本输出 `DDHEX-Setup-0.1.0.exe`、便携版 ZIP 和校验和。默认安装到当前用户 `%LOCALAPPDATA%\Programs\DD HEX`，独立 GUID，不覆盖 AramHex。

构建过程检查内置资料、收集已安装组件许可证、构建 PyInstaller onedir，随后运行真实 Windows Qt/OpenCV/OCR 自检。自检失败或超时会停止，不生成发布安装包。检查 `build\gui-smoke.json` 的 `success`、`platform=windows`、`ocr_ok`、版本号。自检并不验证真实游戏、DPI、多屏、杀毒行为或更新回滚。

打包未签名，公开分发前应评估代码签名，并实际验证 Windows 10/11。发布前核对根目录 MIT、NOTICE、CC BY-NC 全文和 `THIRD_PARTY_LICENSES`；Qt 保留动态库替换能力及相应源码访问说明。详细第三方分发事项见许可证目录 README。

## 8. 日后启用自己的更新源

由维护者编辑 `lolhex/distribution.py`：将 `UPDATE_REPO = ""` 改成自己实际控制的 `owner/repository`，重新测试和打包。不要写原作者的程序或数据仓库；程序会拒绝它们。该版本没有默认官网、备用站和远程云控。

独立 Releases 使用 tag `v0.1.1` 等，发布资产 `DDHEX-Setup-0.1.1.exe` 和 `SHA256SUMS.txt`（或 GitHub asset SHA-256 digest）；便携版可附 `DDHEX-Portable-0.1.1.zip`。保留的增量更新工具使用自己的 `updates-v<版本>` tag、manifest 和 gzip 文件，最低客户端与依赖变化必须核对，第三方依赖变化应完整安装。发布器继承了上游 1.1.9 的资料能力，独立官方资料最低客户端版本为 0.1.0。

`.github/workflows/release.yml` 仅手动 Windows 构建并保存 artifact，不自动发布 Release、不推送标签、不触碰上游仓库。当前交付未创建远端 Fork、未上传源码、未发布安装包。

在「设置 → 本地存储 → 清理截图」可删除助手保存的选卡和调试截图。确认后显示删除数量。清理后仍按原规则保存新截图。
