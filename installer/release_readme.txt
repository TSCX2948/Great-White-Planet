Great White Planet 安装包
=========================

本地知识管理与 AI 辅助学习 · v1.0.0 · 适用于 Windows 11


【怎么装】
----------
1. 把本压缩包完整解压到任意文件夹（不要只解出 exe，_internal 目录必须一起解压）；
2. 双击「安装 Great White Planet.exe」；
3. 选择安装位置（默认 %LOCALAPPDATA%\Programs\Great White Planet），
   勾选是否创建桌面 / 开始菜单快捷方式，点「开始安装」；
4. 安装完成后可直接启动。


【安装包里有什么】
------------------
1. 安装 Great White Planet.exe   图形安装程序
2. payload.zip                   软件本体（安装时解压到目标目录）
3. _internal\                    安装程序自身的运行库
4. 本说明文件

安装包内**不含任何用户数据**：没有账号、没有 API Key、没有科目与书目。
首次启动软件时会在安装目录下自动创建空的 data 目录。

安装完成后，目标目录里会有：

    Great White Planet\
    ├─ Great White Planet.exe          主程序
    ├─ gwp\                            程序文件
    ├─ _internal\                      运行库
    ├─ Document\                       功能说明 / 设计思想 / 使用说明 / 简要说明书(PDF)
    ├─ data\                           你的数据（首次启动后出现）
    ├─ uninstall.json                  安装记录（卸载用）
    └─ 卸载 Great White Planet.exe     卸载程序


【卸载】
--------
开始菜单 → Great White Planet →「卸载 Great White Planet」。

卸载会删除程序文件，**但不会动 data 目录** —— 你的资料不会被删。
要彻底清理请手动删除整个安装文件夹。


【常见问题】
------------
Q: 需要先装 Python 吗？
A: 不需要。软件自带完整的 Python 运行时和全部依赖库，
   目标电脑上**没有安装过 Python 也能直接运行**，也不需要配置任何环境变量。

Q: 需要联网吗？
A: 不需要。完全离线可用。AI 功能是可选的，要用才需要联网并配置 API Key。

Q: 需要管理员权限吗？
A: 不需要。默认装到 %LOCALAPPDATA%\Programs 下，普通用户即可安装。
   若你选择装到 C:\Program Files，则需要管理员权限（软件要把数据写在安装目录下）。

Q: 装到 C:\Program Files 可以吗？
A: 可以，但软件要把数据写在安装目录下，需要管理员权限；推荐使用默认位置，
   或装到 D:\ 等用户可写的位置。

Q: 提示"操作已被取消"或双击没反应？
A: 多半是安全软件拦截。请把安装包所在文件夹加入白名单后再试。

Q: 换电脑怎么带走资料？
A: 整个 data 目录复制到新机器的安装目录下覆盖即可。


【随包文档】
------------
安装后在安装目录的 Document 文件夹里：

  · Great White Planet 简要说明书.pdf    装机必读，五分钟上手
  · Great White Planet 功能说明.md       逐项功能细节
  · Great White Planet 设计思想.md       目录结构与分层设计
  · Great White Planet 使用说明.md       按场景的操作步骤

也可以在软件菜单「帮助」里直接阅读。
