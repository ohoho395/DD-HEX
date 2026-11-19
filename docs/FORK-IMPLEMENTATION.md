# 第一版实施记录

## 目标与审查结论

基于公开 `czgreat/aramhex`，提交 `5b5d37da1c555c29d8a91499b13fc4f56ca6db14`（上游 1.1.9），建立独立 Windows 桌面助手 0.1.0；没有发现用户已有本地仓库，因此克隆公开源码。暂定名称 DD HEX，可后续重命名，当前所有标识必须一致更改。

先审阅 README、DEVELOPMENT、LICENSE、NOTICE、PRIVACY、requirements、Python/PySide6/OCR/推荐模块、测试、打包与发布工作流。原项目已经具备完整截图识别流水线和并发回归测试，故保留 `lolhex` 包结构、浮窗和评分规则，避免重写。统计与程序不是同一许可：MIT 保留原版权；CC BY-NC 数据原样分发并署名，非商业限制继续适用。

发现原版的云配置、匿名标识、诊断日志、账号查分、更新、数据镜像等共用原作者服务；单独把 `check_data_updates` 设成 false 仍会检查远端清单，单独改网站常量也会受旧 cloud.json 影响。独立版需在入口和默认源两层隔离。

## 实施顺序与实际结果

1. 留存上游提交和文档，隔离上游基线运行测试。基线结果见验证报告。
2. 建立独立版本、数据目录、环境变量、单实例、自启、Qt/AppUserModelID、EXE 名和 Inno GUID；重新绘制 DD 图标。没有迁移原版用户目录。
3. 默认关闭所有运行联网；彻底禁用云缓存/遥测/账号查分。统计通过显式勾选从公开 GitHub 数据源更新；软件更新由维护者配置自己的仓库，保留校验、增量替换与回滚，不回退原作者服务。未配置时界面如实说明未查版本。
4. 先新增推荐参数回归测试（记录到 6 个预期失败），再接入胜率显示、平滑、候选样本门槛。保留原始统计、评分原因和小样本/测试服提示；面板缓存包含平滑参数，修改时重算。
5. 设置沿用现有布局，移除可用的遥测和账号查询入口；保留语言、位置、热键、自启与分段。新增卡片场次和理由提示。修正装备提示文本宽度舍入造成的尾数省略。
6. 增加 `--demo`（无游戏、无截图、无网络）与手工 3/4 项输入，保留 `--scan-image` 实际 OCR；保持运行入口 `python -m lolhex`。真实自检后增加 ONNX 遥测禁用和本地模型校验，杜绝模型缺失时隐式下载。
7. 保留 PyInstaller onedir、Inno 和 Windows Qt/OCR 自检；更名产物、独立安装 AppId，把版权/统计许可和第三方通知打进分发。发布工作流仅手动构建 artifact，没有上传、推送或发行。
8. 完成测试、Qt 离屏截图检查、真实 OCR 自检和文档。具体证据与未验证项见 [VERIFICATION.md](VERIFICATION.md)。

## 关键文件

| 范围 | 文件 | 简化与理由 |
|---|---|---|
| 身份与配置 | `distribution.py`、`__init__.py`、`config.py`、`ui/autostart.py`、`ui/overlay.py` | 一个发行配置入口；不更名 Python 包 |
| 原服务隔离 | `cloud.py`、`logupload.py`、`rank.py`、`data/public.py` | 删除远程日志/调试动作；空默认源不构造假网址 |
| 软件更新 | `update.py`、`patch.py` | 保留原验证/回滚，换独立资产和 GUID |
| 推荐与设置 | `recommend.py`、`engine.py`、`__main__.py`、`ui/mainwindow.py` | 默认评分保持一致，复用现有控件和数据流 |
| 构建 | `packaging/*`、`.github/workflows/release.yml`、`scripts/official_data.py` | 移除上游发布副作用；继承资料能力的最低兼容版本改为 0.1.0 |
| 回归 | `tests/test_ddhex_*` 及相关原测试 | 旧遥测预期改成无联网，保留 OCR/并发/数据/更新回归 |

## 第一版范围外

当前提供内置 Windows 运行时和启动 EXE 的便携包，未在真实 Windows 10/11 游戏环境验证识别率、性能、多屏/DPI、快捷键、自启、安装卸载或回滚。未部署独立更新服务器、未配置 GitHub 发行仓库、未发布 Release。无代码签名或游戏规则许可结论。已提供 Windows CI 和手工验收命令，不能把 Mac 上测试通过当成 Windows 发布验收。
