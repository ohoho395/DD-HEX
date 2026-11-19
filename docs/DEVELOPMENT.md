# DD HEX 开发说明

目标：Windows 10/11 x64、Python 3.13。保留原有 `lolhex` 包名以减少导入和 PyInstaller 改动，用户品牌为 DD HEX。源码与包名不是运行数据目录；目录和应用标识均已独立。

## 目录与边界

- `lolhex/__main__.py`：GUI、headless、截图 OCR、离线推荐 demo 入口。
- `lolhex/distribution.py`：独立应用标识和维护者自己的更新仓库；默认留空，拒绝原作者软件/数据仓库更新程序。
- `lolhex/config.py`：`DDHEX_HOME`、独立数据目录、类型检查、推荐参数持久化。
- `lolhex/engine.py`：保留截图/识别调度和并发保护，推荐参数变化重算，平滑强度纳入面板缓存。
- `lolhex/vision/`：原截图、窗口定位、OCR、匹配和三/四选一模块保留。显式禁用 ONNX 遥测；校验固定版本本地模型 SHA-256 后指定路径，缺失/损坏时提示重装，不自动联网下载。
- `lolhex/recommend.py`：保留原评分和回退，新增可传入的首选样本门槛，默认仍为 1000。原统计和固定样本分档不变。
- `lolhex/cloud.py`：保留本地默认值及解析工具，读取和刷新均不接受旧云缓存、不请求原服务。`sites=[]`、`own=False`，永久关闭远程遥测。
- `lolhex/logupload.py`、`rank.py`：远程动作禁用，保留本地脱敏/格式化工具。
- `lolhex/data/public.py`：内置统计、结构/哈希验证、对局外切换；运行默认源仅在用户主动开启统计更新时使用公开 GitHub 数据仓库。
- `lolhex/update.py`、`patch.py`：独立仓库更新与原 SHA-256/替换/回滚实现；更新资产名、安装 GUID、临时路径、重启 EXE 均独立。
- `packaging/`：原 PyInstaller onedir/Inno 流程、自检和二进制来源校验，新增分发许可证收集。

## 验证

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q lolhex scripts packaging
.\.venv\Scripts\python.exe scripts\check_release_data.py
.\.venv\Scripts\python.exe -m pip check
```

测试用合成数据、禁网夹具和本机临时 HTTP 服务。没有新增 lint/typecheck 依赖或声称执行不存在的配置；使用现有测试、编译检查、数据校验和差异检查。独立源策略、默认/旧缓存隔离、推荐参数重启持久化、面板缓存、CLI 和真实 Qt 控件均有针对测试。

推荐参数新增字段不改统计 schema。默认门槛 1000 和平滑 300 保持上游语义；不得为了提高显示效果删除缺数据或小样本提示。原官方资料发布器的最低兼容版本已改成独立版 0.1.0，因为继承的能力覆盖上游 1.1.9；未来修改格式仍需升级/校验兼容版本。

Windows 安装、打包、独立更新发布约定和第一版实测项见 [WINDOWS.md](WINDOWS.md)、[VERIFICATION.md](VERIFICATION.md)。原版历史文档只作为审查资料保存在 [UPSTREAM-DEVELOPMENT.md](UPSTREAM-DEVELOPMENT.md)，其中云控、官网地址和原版发版步骤不适用于独立版本。
