"""帮助文档：菜单里的「设计思想」「功能说明」以及使用说明。

优先打开 ``D:\\Great White Planet\\Document`` 下的同名文档（需求文档第九节）；
文件不存在时回退到本模块内置的内容，保证菜单永远有东西可看。
"""

from __future__ import annotations

from pathlib import Path

from gwp.core.paths import document_dir

DESIGN_DOC = """# Great White Planet 设计思想

> **完整版**：`D:\Great White Planet\Document\Great_White_Planet_设计思想.md`
> 「帮助 → 设计思想」会优先打开它；下面只是内置摘要。

## 一句话

软件的职责是**把零散的学习资料整理成一条可复习的主线**，而不是替用户学习。

## 三条基本原则

1. **磁盘就是数据库**：科目 = 文件夹，书目 = 子文件夹，内容 = Markdown。
   没有数据库，因此可以用任何编辑器改、可以网盘同步、软件换了也不丢资料。
2. **界面由扫描结果生成**：代码里不写死课程名与文件类型；
   新格式只需注册一个读取器，新 AI 只需加一个 provider 文件。
3. **整合而不是概括**：`<书名>_summary.md` 是把简介 + 笔记 + 易错题
   合并、补全、扩展成一份完整学习文档；无法确认的内容宁可列为
   「待确认问题」也不编造（准确性优先）。

## 分层

`core`（配置/路径/事件/日志）→ `data_manager`（扫描与增删改）→
`ai`（提供方/总结/会话）→ `services`（解析/渲染/导出/剪贴板/背景）→ `ui`（PyQt6）。

数据层、AI 层、服务层都不依赖 Qt，因此核心逻辑可以脱离界面单独测试。

## 可回退设计

重新生成总结前先备份上一版；恢复上一版前又先备份当前版本；
删除进回收站；剪切先复制成功再删源；粘贴同名自动改序号；更换背景保留旧图。
"""

FEATURE_DOC = """# Great White Planet 功能说明

> **完整版**：`D:\Great White Planet\Document\Great_White_Planet_功能说明.md`
> 「帮助 → 功能说明」会优先打开它；下面只是内置摘要。

* **科目**：首页彩色卡片，右键可重命名 / 换图 / 换色 / 置顶 / 删除。
  每个科目 = `user data\subjects` 下的一个文件夹，完全由扫描生成。
  **新建时要选类型**：日记（`AI summary`/`AI diary`/`my diary`/`else diary`）、
  校修课、自学课（后两者的标签差别是「作业」/「练习」，目录都是 `homework`）。
  日记类型会自动建好默认书目 `MyBook`。
* **书目**：自动生成 `Introduct.md`、`<书名>_summary.md`、`book`、
  `error-prone`、`notebook`、`homework`；`book`（教材）与 `homework`（作业）
  都不参与 AI 总结。
* **资料管理**：导入（按钮或拖拽）、剪切 / 复制 / 粘贴（`Ctrl+C/X/V`，
  与系统剪贴板互通，同名自动改序号，结构目录受保护）。
* **AI 总结**：整合简介 + 笔记 + 易错题，长资料自动分块提炼再合并；
  扫描件 PDF 按「准确性优先」转为图片插入；生成前备份上一版。
* **版本管理**：查看、对比、恢复上一版总结。
* **Markdown**：查看模式（渲染预览）与编辑模式（源码 + 实时预览、行号、
  高亮、快捷插入、查找、自动保存）。
* **AI 对话**：文档内「AI 双栏」针对当前文件；菜单栏右上角「AI 对话」
  是不读文件的日常对话；AI 不确定时会弹窗提问；回答可一键插入文档。
* **AI 提供方**：DeepSeek API / GPT API / 网页版 / 本地命令 / 自定义 API，
  支持兜底链与连通性诊断；Key 存在 `else data\secrets.json`。
* **导出 PDF**：本地生成，可选纸张 / 边距 / 是否嵌图；导出前弹窗确认
  是否加页码与导出哪些页（支持 `1-3, 5`、`e`、`e-1`、`3-e`）；后台执行可取消。
* **主界面背景**：图片放在 `else data\background`，更换时**保留旧图**，
  文件名只递增后半部分数字；入口在「查看 → 更改背景」（设置菜单里也有）；
  可调显示方式与蒙层深浅，背景铺满工作区、内容块保留自己的底色。
* **系统集成**：开机自启、桌面快捷方式、启动预扫描、**单实例保护**、依赖自检、命令行工具。
"""

USAGE_DOC = """# Great White Planet 使用说明

> 说明：完整版在 `Document\Great_White_Planet_使用说明.md`，「帮助 → 使用说明」会优先打开它；下面是内置的简版。

## 第一次使用

1. 双击 `code\\run.pyw`（或桌面快捷方式）启动软件。
2. 首页点「＋ 新建科目」，例如"高等代数"。
3. 进入科目后点「＋ 新建书目」，例如"数学分析"——软件会自动建好
   `Introduct.md`、`book`、`error-prone`、`notebook`。
4. 打开书目的「笔记」标签，点「导入文件」或把文件拖进来。
5. 在 `Introduct.md` 里写下学习目标（双击即可打开编辑）。
6. 点「生成总结」——AI 会整合简介 + 笔记 + 易错题，生成 `书名_summary.md`。

## 配置 AI

菜单「AI → AI 设置」：

* **DeepSeek API**：填 API Key（在 platform.deepseek.com 获取），模型默认 `deepseek-chat`。
* **GPT API**：填 OpenAI 的 Key，模型默认 `gpt-4o-mini`。
* **本地天禧 AI**：填本机可用的命令行程序，例如 `tianxi --chat`（需能从 stdin 读提示词、
  往 stdout 写回答）。
* **网页版**：不需要 Key，点开会把提示词复制到剪贴板并打开官网。

填完可以点「测试连接」验证。

## 常见问题

**Q：软件里看不到我手工放进 data 的科目？**
点首页「刷新」；确认文件夹直接位于 `data\\user data\\subjects` 下。

**Q：AI 报"未配置 API Key"？**
在「AI 设置」里填写并保存；或设置环境变量 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY`。

**Q：生成失败怎么办？**
上一版总结不会被破坏（生成失败不会写入文件）。可以换一个 AI 重试，
或在「AI 设置」里调大"单次送入字符数"减少分块次数。

**Q：想恢复上一版总结？**
书目页点「版本管理…」，选中历史版本→「恢复此版本」；也可以先「与当前版本对比」。

**Q：网盘同步会不会出错？**
不会。所有内容都是普通文件；只是不要在两台机器上同时生成同一本书的总结。

**Q：数据都在哪？**
用户内容在 `D:\\Great White Planet\\data\\user data`；
配置、密钥、备份、聊天记录、日志在 `D:\\Great White Planet\\data\\else data`。
"""

CHANGELOG_DOC = """# Great White Planet 更新记录

## v1.0.0

首个完整版本：

* 科目 / 书目：扫描生成界面，支持新建、重命名、换图换色、置顶、移动、回收站删除
* 科目类型：日记 / 校修课 / 自学课（自学课的「作业」显示为「练习」，目录与功能不变）
* 收纳箱：把若干科目收在一起，卡片样式与科目一致但带边框；只记分组、不动文件
* Book 标准结构：`Introduct.md`、`<书名>_summary.md`、`book`、`error-prone`、`notebook`
* 资料导入：md / txt / pdf / docx / pptx / xlsx / csv / 图片，支持拖拽
* 文件剪贴板：Ctrl+C / X / V，与系统剪贴板互通，同名自动改序号，结构目录受保护
* AI 学习总结：整合简介 + 笔记 + 易错题，分块提炼 + 合并，生成 `<书名>_summary.md`
* 版本管理：自动保留上一版，可查看、行级对比、恢复（恢复前再备份）
* Markdown 查看与编辑：源码 + 实时预览、行号、语法高亮、快捷插入、查找、自动保存
* AI 对话：文档内双栏（自动发送当前文件、回答可插入文档）+ 日常对话窗口
* AI 不确定性提问：AI 弹窗询问用户，回答后自动继续
* 可插拔 AI：DeepSeek API / GPT API / DeepSeek 网页版 / GPT 网页版 / 本地命令 / 自定义 API
* 兜底链与连通性诊断（含 API Key 排查清单）
* 导出 PDF：本地生成，可切页（`1-3, 5`、`e`、`e-1`、`3-e`）、可选页码、后台执行可取消
* 主界面背景：图库式管理，更换保留旧图，文件名递增数字，可调蒙层与显示方式
* 程序图标：内置「太白金星」多分辨率图标，可换成自己的图片
* 系统集成：开机自启、桌面快捷方式、启动预扫描、扫描缓存
* 帮助菜单：设计思想 / 功能说明 / 使用说明 / 更新记录（优先读取 Document 目录）
* 测试：核心层与界面层自检脚本、代码整洁度报告、命令行工具
"""


def help_documents() -> dict[str, str]:
    """返回 {菜单名: 文本}。"""
    return {
        "设计思想": DESIGN_DOC,
        "功能说明": FEATURE_DOC,
        "使用说明": USAGE_DOC,
        "更新记录": CHANGELOG_DOC,
    }


def find_external_document(name: str) -> Path | None:
    """在软件的 Document 目录里找同名文档。"""
    directory = document_dir()
    if not directory.is_dir():
        return None
    candidates = [
        directory / f"{name}.md",
        directory / f"Great_White_Planet_{name}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    keyword = name.replace(" ", "")
    for candidate in sorted(directory.glob("*.md")):
        if keyword in candidate.stem.replace("_", "").replace(" ", ""):
            return candidate
    return None


def document_text(name: str) -> tuple[str, Path | None]:
    """取帮助文档：优先磁盘上的文档，否则用内置内容。返回 (文本, 来源路径)。"""
    external = find_external_document(name)
    if external is not None:
        try:
            return external.read_text(encoding="utf-8", errors="replace"), external
        except OSError:
            pass
    return help_documents().get(name, f"# {name}\n\n（没有找到内容）"), None


__all__ = [
    "CHANGELOG_DOC",
    "DESIGN_DOC",
    "FEATURE_DOC",
    "USAGE_DOC",
    "document_text",
    "find_external_document",
    "help_documents",
]
