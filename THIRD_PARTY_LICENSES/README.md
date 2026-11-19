# 第三方许可证与构建清单

DD HEX 使用 Qt for Python / PySide6、Shiboken6、RapidOCR / PaddleOCR 模型、ONNX Runtime、OpenCV、NumPy 等第三方组件。它们各自保留自己的版权与许可；根目录的 MIT 不替代这些许可，也不替代统计数据的 CC BY-NC 4.0。

## 这些文件来自哪里

`packaging/collect_licenses.py` 只读本机安装的分发包元数据及 `LICENSE`、`COPYING`、`NOTICE`、第三方声明文件，不导入这些包、不联网。它保留已有文件，把当前环境的文件复制到 `<包名>/<版本>/<安装时相对路径>`，并写入版本、文件 SHA-256、Python、系统及架构清单。CPython 的运行时许可证也会复制。OCR 模型不重复复制到本目录，其文件名、大小和 SHA-256 记录在 RapidOCR 清单中。

- `manifest-darwin-arm64.json` 是本次 macOS Python 3.13 开发环境的种子清单，不能用来证明 Windows 产物的组件组成。
- `manifest.json` 是最近一次运行收集器的环境清单。Windows 的 `packaging/build.ps1` 会在 PyInstaller 之前重新收集，并生成例如 `manifest-win32-AMD64.json`。
- 清单列的是整个安装环境，可能包含测试、构建工具和没有装进最终 EXE 的依赖。最终分发范围须同时核对 PyInstaller 的分析结果。
- 原来存在的许可证不删除，因此不同系统或版本的文件可能共存。以本次构建清单为准。
- 部分 wheel 没有附带许可证文本：`pyside6-essentials/` 中附加了 LGPL-3.0 与 GPL-3.0 正文，`rapidocr/`、`paddleocr/`、`flatbuffers/` 中附加了官方源码仓库的 Apache-2.0 文本。下载来源和文本校验和见 `supplements.json`。Shiboken6 与 PySide6 的许可证正文共用 `pyside6-essentials/` 中两份文件。

## 源码与 Qt 动态库替换

本版采用 PyInstaller **onedir**，PySide6 / Qt / Shiboken 作为独立动态库分发。未对这些库或 OCR 模型进行修改。Qt for Python / Shiboken 的使用按 LGPL-3.0 条款，完整条文见 `pyside6-essentials/LGPL-3.0-only.txt` 及其引用的 `GPL-3.0-only.txt`。不得限制为调试这些库的修改而进行的逆向工程。

接收者可使用接口兼容、相同架构、相同 Python ABI 的修改版库。退出 DD HEX，备份整个程序目录，在嵌入式便携包的 `runtime/Lib/site-packages`（PyInstaller 版为 `_internal`）中找到 PySide6 / Qt DLL、Qt `plugins` 与 `shiboken6` 文件，按原目录结构替换相应文件，然后运行 `DD HEX.exe --self-test-gui <报告文件路径>` 验证。没有签名校验或加密机制阻止替换；可随时用备份还原。不要仅替换任意一个不兼容的 Qt DLL。源码运行也可在虚拟环境中安装自己的兼容构建。

官方源码入口（匹配本次清单中的版本与实际 Qt 版本）：

- [Qt for Python / Shiboken 源码](https://code.qt.io/cgit/pyside/pyside-setup.git/)；[官方源码发行目录](https://download.qt.io/official_releases/QtForPython/)。
- [Qt 模块源码](https://code.qt.io/cgit/qt/)；[Qt 官方源代码包目录](https://download.qt.io/official_releases/qt/)。
- [RapidOCR](https://github.com/RapidAI/RapidOCR)、[RapidOCR 模型目录](https://github.com/RapidAI/RapidOCR/tree/main/python/rapidocr)、[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。
- [ONNX Runtime](https://github.com/microsoft/onnxruntime)、[OpenCV](https://github.com/opencv/opencv)、[opencv-python](https://github.com/opencv/opencv-python)、[NumPy](https://github.com/numpy/numpy)、[CPython](https://www.python.org/downloads/source/)。其他组件源码链接见清单的 `project_urls`。

公开分发 Windows 二进制前，维护者须依据实际装入的 Qt/第三方库版本核对声明、对应源码获取方式与必要的源码提供义务，将可获取对应源码的链接或合法的提供方式与二进制一同发布。此目录中的链接与自动清单本身不构成完整合规保证；本次交付没有运行 Windows 打包，也未发布公共二进制。

## OCR 模型

RapidOCR 的软件许可证为 Apache-2.0；其 wheel 内的 ONNX 模型来自 RapidOCR / PaddleOCR 的公开模型系列，PaddleOCR 项目的 Apache-2.0 正文一并保留。具体安装的模型列表和哈希见清单的 `rapidocr.models`。更换模型时须核验该模型自身来源与许可，不把软件许可自动推定为所有第三方模型许可。
