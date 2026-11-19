# DD HEX Windows 便携版验证

本包在 macOS 上组装，使用 CPython 3.13.13 官方 Windows x64 嵌入版及目标平台 wheel。构建期间检查了 29 个分发包的运行依赖、68 个原生 Python 扩展、启动器与 Qt Windows 插件的 PE 架构，并校验随包 OCR 模型。

改名后在 Mac 运行回归测试。1078 项通过，29 项跳过，34 项因当前环境禁止监听本机 HTTP 端口未完成。此前源码基线测试记录保存在 verification 目录，仅代表改名前版本。当前没有 Windows 实机或游戏，未验证 Windows 启动、游戏浮窗和每台电脑的系统组件兼容性。使用 Self-Test.cmd 可以在目标机执行 Qt、OpenCV 和真实 OCR 检查并生成报告。

改名后的应用、推荐、界面、OCR 和打包专项测试 18 项通过。便携包没有代码签名。

0.1.1 截图清理及相关界面、截图保存测试共 31 项通过。已校验 Windows ZIP 完整性，未做 Windows 实机验收。
