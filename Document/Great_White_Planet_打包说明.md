# Great White Planet 打包与发布说明

面向需要**重新出安装包**的人。整条流水线都在 `code\installer\` 下，
不依赖 Inno Setup / NSIS / WiX 等第三方安装器制作工具。

---

## 一、一键出包

```bat
cd /d "D:\Great White Planet\code"
venv\Scripts\python.exe installer\make_manual_pdf.py     :: 先生成简要说明书 PDF
venv\Scripts\python.exe installer\build_installer.py      :: 再出安装包
venv\Scripts\python.exe installer\acceptance.py           :: 可选：完整验收
```

产物：

| 文件 | 说明 |
| --- | --- |
| `DeepseekData\build\out\installer_stage\` | 安装器目录（发布用） |
| `DeepseekData\build\out\Great White Planet 安装包.zip` | 最终交付的压缩包（约 70 MB） |

---

## 二、流水线做了什么

`installer/build_installer.py` 分五步：

1. **构建软件本体** —— PyInstaller + `code\gwp.spec`，产出 `onedir` 形式的
   `Great White Planet\`（约 135 MB）；
2. **校验产物干净** —— 扫描产物里是否混入 `data`、`secrets.json`、`config.json`、
   `boxes.json`、`instance.lock`、`chats`、`summary_backup` 等**用户数据**；
   一旦发现立刻中止，绝不让用户数据进安装包；
3. **压缩本体** —— 打成 `payload.zip`（约 61 MB）；
4. **构建安装器** —— PyInstaller `--onedir --windowed` 打出图形安装器，
   与 `payload.zip`、说明文件一起放进 `installer_stage`；
5. **尝试单文件自解压** —— 用 Windows 自带的 IExpress 合并成单文件
   （本机 IExpress 不可用时自动跳过，直接发布目录）。

---

## 三、关键设计决定（都是踩过坑才定下来的）

### 1. 安装包不含用户数据

软件首次运行时才创建 `data`，安装包本身是干净的。这不是"顺手做对"，
而是第 2 步会**主动校验并中止**的硬性约束。

### 2. 打包后路径要重新解析

源码模式下 `paths.project_root()` 靠 `__file__` 向上推 4 层；打包后
`__file__` 指向 PyInstaller 的解包临时目录，照旧推导会把数据写进临时目录、
退出即丢。因此：

* `is_frozen()` 判断是否打包运行；
* 打包时 `project_root()` = **可执行文件所在目录**；
* `resources_dir()` / `document_dir()` 用 `sys._MEIPASS` 定位随包资源。

### 3. 数据根目录可重定位

`config.json` 里如果存的是旧机器的绝对路径，软件会往一个不存在的地方写数据。
`DataPaths._resolve_data_root()` 的规则：

| 配置值 | 结果 |
| --- | --- |
| 空 | `<软件根>/data` |
| 相对路径 | 相对软件根解析 |
| 绝对路径 | **照用，即使还不存在**（首次运行本来就还没建） |
| 绝对路径但被同名文件占住 | 回退到 `<软件根>/data` |

### 4. 安装器用 onedir，不用 onefile

实测：本机（装实时防护）会**直接拦掉 PyInstaller onefile 的自解压引导** ——
进程根本不启动，也不给任何提示。改为 `onedir` 后一切正常。
发布时用一个 zip 承载安装器目录，用户在资源管理器里解压即可。

### 5. 窗口化程序里不要 `print()`

安装器是 `console=False`，此时 `sys.stdout` / `sys.stderr` 可能是 `None`，
`print()` 会抛 `AttributeError`，而异常又没地方输出 —— 表现就是
"双击了一下，什么也没发生"。所有输出走 `installer.say()` / `installer.warn()`。

### 6. Python 3.10.0 的 `dis` 有越界 bug

本机 `D:\Python\Python310` 是 3.10.0，其 `dis._get_const_info` 在常量索引越界时
抛 `IndexError`，PyInstaller 扫描字节码必然踩到，构建直接崩。
用 `installer\build_shim\sitecustomize.py` 打了补丁，**只在构建期生效**
（通过 `PYTHONPATH` 注入），不进最终产物。

### 7. 哪些东西被排除，为什么

| 排除项 | 原因 |
| --- | --- |
| `numpy` | 只在"现场绘制图标"（CLI 的 icon 子命令）时才需要；随包已带 `icons/planet.ico` |
| `opengl32sw.dll`（20 MB） | Qt 的软件 OpenGL 回退实现，本软件用不到 |
| Qt WebEngine / Qml / Quick / 3D / Multimedia / Sql / Test … | 完全未使用 |
| `tkinter`（软件本体里） | 只有安装器需要它 |

---

## 四、安装器的行为

`installer/installer.py`，三种运行方式：

| 命令 | 行为 |
| --- | --- |
| 双击 | 图形界面：选目录、选快捷方式、进度条、装完可一键启动 |
| `--uninstall` | 按 `uninstall.json` 记录删除文件，并清理快捷方式 |
| `--silent --dir <路径> [--no-shortcut]` | 静默安装（自动化测试用） |

**卸载刻意不动 `data` 目录** —— 用户资料不能因为卸载就没了。
卸载后目录里只剩 `data`，要彻底清理由用户手动删。

---

## 五、验收脚本做什么

`installer/acceptance.py` 会完整走一遍用户路径：

1. 解压发布包 → 2. 静默安装 → 3. **启动装好的程序并确认日志正常**
→ 4. 静默卸载 → 5. 断言：

* 主程序 / 卸载器 / 安装记录都在；
* `Document` 里有说明书 PDF + 三份说明文档，**且不含需求设计文档**；
* 安装目录里**没有** `data`、`secrets.json`、`boxes.json`、`instance.lock`；
* 程序启动后 `startup_error.log` **不存在**；
* 卸载后主程序被删、`data` 保留。

---

## 六、随包文档

`Document` 目录里会带上这几份（需求设计文档**不**随包分发）：

* `Great White Planet 安装步骤说明.pdf` —— 装之前看，含安装界面真实截图
* `Great White Planet 简要说明书.pdf` —— 装机必读，五分钟上手
* `Great_White_Planet_功能说明.md`
* `Great_White_Planet_设计思想.md`
* `Great_White_Planet_使用说明.md`

这些 md 与 PDF 同时保留在项目的 `D:\Great White Planet\Document` 作为备份。

安装说明里的界面截图放在 `Document\installer_shots\`，由
`installer\make_shots.py` 抓取真实安装器窗口得到（再用 PIL 裁掉窗口外的黑边）。

### 生成 PDF 时的一个坑

Markdown 里的图片用**相对路径**即可，但排版时必须把文档目录交给
`pymupdf.Archive`：

```python
story = pymupdf.Story(html=html_text, archive=pymupdf.Archive(str(DOCUMENT)))
```

只把 `<img src>` 改写成绝对路径**不生效** —— 实测图片数仍为 0，
必须走 Archive。`make_manual_pdf.py` 会在生成后统计 PDF 里的图片张数，
并与 Markdown 里 `![` 的数量比对，不一致会直接打印警告。

---

## 七、改了代码之后要做什么

1. 跑测试：`tests\lint_report.py` → `tests\smoke_core.py` → `tests\smoke_gui.py`
   （GUI 用例建议连跑两次，它有过偶发竞态）；
2. **界面变了就重抓安装器截图**：先出包（第 3 步）生成 `installer_stage`，
   再跑 `python installer\make_shots.py`，它会把截图直接写进
   `Document\installer_shots\`；然后重新生成 PDF；
3. 重新出包：`installer\build_installer.py`；
4. 验收：`installer\acceptance.py`。

完整顺序（改了界面时）：

```bat
cd /d "D:\Great White Planet\code"
venv\Scripts\python.exe installer\build_installer.py       :: 1. 出包（生成 installer_stage）
venv\Scripts\python.exe installer\make_shots.py            :: 2. 重抓界面截图
venv\Scripts\python.exe installer\make_manual_pdf.py       :: 3. 重生成 PDF
venv\Scripts\python.exe installer\build_installer.py       :: 4. 再出包（把新 PDF 打进去）
venv\Scripts\python.exe installer\acceptance.py            :: 5. 验收
```

只改了逻辑、没动界面时，跳过第 2、3 步即可。

版本号在 `gwp\__init__.py` 的 `__version__`（**唯一来源**），
改它会同步到窗口标题、关于框、日志与安装包信息。

> 这里原先写的是 `gwp\core\constants.py` 的 `APP_VERSION` —— 那是旧版本的位置，
> 早就搬到 `gwp\__init__.py` 了。按旧说明去找会找不到，所以更正一下。

## 附：开发实践书稿的排版

书稿《开发实践——Great White Planet》的 Markdown 源在
`Document/开发实践——Great White Planet.md`，用一条命令排版：

`powershell
code\venv\Scripts\python.exe code\installer\make_dev_book.py
`

它会：

1. 从 Markdown 里抽出标题，生成**目录页**（不含页码，因为书会持续增补）；
2. 用软件自己的 Markdown→HTML 管线 + PyMuPDF Story 排正文，**带页码**；
3. 把目录页插到正文前面，**重编页码**（目录页不编号）；
4. 写出到三个位置：`Document`、项目根目录、`DeepseekData`。

改代码后请同步补充书稿（见书稿附录 C 的模板）。
