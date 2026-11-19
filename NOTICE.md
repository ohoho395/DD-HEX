# 第三方组件与数据

安装包和便携版里带了下面这些组件，各自遵循自己的协议：

| 组件 | 用途 | 协议 |
|---|---|---|
| [Qt for Python (PySide6)](https://www.qt.io/qt-for-python) | 界面 | LGPL-3.0（以独立的动态库形式随程序分发，可自行替换） |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) 及其 PaddleOCR 模型 | 文字识别 | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | 运行识别模型 | MIT |
| [OpenCV](https://opencv.org/) | 图像处理 | Apache-2.0 |
| [NumPy](https://numpy.org/) | 计算 | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) | 图像处理 | MIT-CMU |
| [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 名称模糊匹配 | MIT |
| [python-mss](https://github.com/BoboTiG/python-mss) | 截屏 | MIT |
| [Requests](https://requests.readthedocs.io/) | 网络请求 | Apache-2.0 |
| [PyInstaller](https://pyinstaller.org/) | 打包 | GPL-2.0（带 bootloader 例外，不影响本程序的协议） |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | 安装程序 | Inno Setup License |

数据：
- `lolhex/data/bundled/`：统计数据，来自 [czgreat/aramhex-data](https://github.com/czgreat/aramhex-data)，协议为 CC BY-NC 4.0。
- `lolhex/data/hero_aliases.json`：英雄别名，整理自 Hexdata（hexdata.com.cn）。
- `lolhex/data/hero_nicknames.json`：网上常见的英雄外号，人工整理。
- `lolhex/data/static_bundled.json`、`hero_bundled.json` 及内置图标包含来自腾讯官方公开接口（game.gtimg.cn、mlol.qt.qq.com）的英雄、海克斯、装备、出装和加点资料，个别海克斯中文名由 CommunityDragon 补全；这些资料和图像随程序分发，版权归原权利人所有。玩家模式从内置快照读取，并可通过自有资料源更新，不直接向上述第三方接口回源；显式资料获取工具仍可访问第三方接口。

## DD HEX 独立衍生版本（0.1.0）

- 原代码作者：czgreat；来源 https://github.com/czgreat/aramhex ，基线提交 `5b5d37da1c555c29d8a91499b13fc4f56ca6db14`。完整 MIT 文本和原有版权保留在 `LICENSE`。DD HEX 为独立衍生版本，不暗示原作者背书。
- 改动：独立品牌和安装标识、默认离线/禁用遥测及原版服务、推荐参数设置、离线演示、独立构建和文档。内置统计文件未修改。
- 统计数据署名：czgreat / aramhex-data，https://github.com/czgreat/aramhex-data 。许可 CC BY-NC 4.0，全文随包 `DATA-LICENSE-CC-BY-NC-4.0.txt`，许可链接 https://creativecommons.org/licenses/by-nc/4.0/ 。仅限非商业使用，后续修改统计应标明改动，不增加额外限制、不暗示认可。代码 MIT 许可不覆盖或解除数据的非商业条件。
- 所有新 DD 品牌图标由本版本本地绘制，替换原版应用图标。游戏内英雄、装备和海克斯素材仍归原权利人，不因换品牌改变权利。
- 本版不连接原作者官网服务，不进行匿名统计或上传日志。`PRIVACY.md` 描述独立版实际行为。
- 第三方完整通知、版本与来源索引位于 `THIRD_PARTY_LICENSES/`。打包脚本会从构建环境收集实际依赖的许可证，保留 Qt 动态链接和替换能力。公开二进制分发前需按实际 Windows 组件及相应许可核对源码获取/替换要求。
