# Great White Planet（太白金星）

> 本地知识管理与 AI 辅助学习软件。管理课程、教材、笔记、错题，
> 把散落的资料**合并成一份可以直接用来复习的 PDF**。

* **开发**：Python 3.10 + PyQt6（Windows 11 桌面端）
* **数据形态**：**普通文件夹 + Markdown**。没有数据库 ——
  随时可以用任何编辑器改、直接拷走备份、换台电脑接着用
* **AI**：可插拔（DeepSeek API / GPT API / DeepSeek 网页版 / GPT 网页版 /
  本地 AI / 自定义 OpenAI 兼容接口），**不联网也能用**（AI 功能全部可选）

---

## 一、装哪个？

### 方案 A：直接用安装包（推荐给只想用的人）

到 **[Releases](../../releases)** 下载：

| 文件 | 说明 |
| --- | --- |
| `Great White Planet 安装包.zip` | **安装程序**。解压后双击 `安装 Great White Planet.exe` |
| `Great White Planet v1.0 win11-bit64.zip` | **免安装绿色版** + 说明文档。解压即用 |

安装包**自带 Python 运行时** —— 你的电脑**不需要**预装 Python。

### 方案 B：从源码运行（推荐给想改代码的人）

```bash
git clone https://github.com/<你的账号>/Great-White-Planet.git
cd Great-White-Planet

python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe run.pyw
```

Windows 上也可以直接双击 `安装依赖.bat`，然后双击 `启动 Great White Planet.bat`。

---

## 二、它解决什么问题

平时学习会遇到这些事：

* 课件是 PPT、讲义是扫描 PDF、笔记是 Markdown、错题是截图 —— **四种格式四套工具**
* 「这学期到底学了什么」要翻十几个文件夹才能想起来
* 想要一份**能打印出来复习**的东西，但手动拼一份要花一晚上

这个软件的做法是：

1. 按 **科目 → 书目** 建目录（一个文件夹就是一个科目，看得见、摸得着）
2. 资料按用途分栏目：**笔记 / 易错题 / 教材 / 作业 / 其它文件**
3. 点「**生成总结 PDF**」→ 把「笔记 + 易错题 + 简介」全部资料
   **合并成一个 PDF**（PDF 每页转图、Word/PPT/Excel 排版后转图）
4. 可选让 AI 按主题**重排页序**（跨文件夹混排），
   以及文末追加一段「**长庚知道**」知识点补充

> 设计上的一个选择：**AI 不改写你的资料**。
> 总结正文永远是原始资料本身，AI 只做「排序」和「文末补充」，
> 而且补充明确标注、单独排在最后。理由很实际：
> 复习材料被 AI 改写错了，比没有总结更糟。

---

## 三、主要功能

| 功能 | 说明 |
| --- | --- |
| **科目 / 书目管理** | 科目分「日记 / 校修课 / 自学课」三种类型，标签与目录随类型变化 |
| **笔记 / 易错题** | 内置 Markdown 编辑器，公式（LaTeX）渲染成图片显示 |
| **生成总结 PDF** | 全部资料合并成一个 PDF；**只留这一个产物**，中间文件自动清理 |
| **AI 重排页序** | 跨文件夹按主题混排；校验不过就整条退回原顺序（不丢页） |
| **「长庚知道」** | 文末 AI 知识点补充，每页左上角带标记 |
| **作业管理** | DDL、提交网址、完成状态（绿=已完成 / 红=未完成，临近截止整行染色） |
| **日程栏** | 作业与日程统一排序（未完成在前 → DDL 早的在前），一键完成 |
| **版本管理** | 每次生成总结前自动备份，可一键退回历史版本 |
| **收纳箱** | 首页把不常用的科目收起来，支持拖拽排序 |
| **单词书** | 一张卡一个 JSON 文件，方便单独改、单独分享 |
| **导入 / 拖拽上传** | 从资源管理器直接拖文件进栏目；图片可让 AI 提取成 Markdown |
| **后台监听** | 外部改了文件软件会自动发现（2 秒一次，空闲 CPU 占用约 0.5% 单核） |

---

## 四、目录结构

```
Great-White-Planet/
├── gwp/                    软件本体（分层：core → data_manager → ai → services → ui）
│   ├── core/               配置、路径、日志、事件总线、线程管理、写保护
│   ├── data_manager/       科目/书目/作业/日程/单词书的读写（没有数据库，直接读写磁盘）
│   ├── ai/                 可插拔 AI：适配器注册表 + 多提供方回退
│   ├── services/           文档读取、Markdown 渲染、公式渲染、PDF 合并/导出
│   └── ui/                 界面（视图 / 对话框 / 控件 / 主题）
├── installer/              打包与安装程序
│   ├── build_installer.py  用 PyInstaller 打包成安装包
│   ├── make_dev_book.py    书稿同步
│   └── acceptance.py       安装包验收（检查不含用户数据）
├── tests/                  自检脚本（core / gui 两套，共 1500+ 条断言）
├── Document/               设计文档、使用说明、打包说明、开发实践书稿
├── run.py / run.pyw        启动入口
├── requirements.txt        依赖清单
└── gwp.spec                PyInstaller 配置
```

**运行时的数据**（**不在这个仓库里**）默认在软件根目录的 `data/` 下：

```
data/
├── user data/
│   ├── subjects/<科目>/<书目>/     ← 你的全部内容
│   │   ├── book.json               书目信息
│   │   ├── Introduct.md            简介
│   │   ├── notebook/               笔记
│   │   ├── error-prone/            易错题
│   │   ├── homework/               作业（每个作业一个文件夹）
│   │   ├── book/                   教材（不参与总结）
│   │   └── others/                 其它文件
│   └── wordbook/                   单词书卡片
├── else data/                      配置、密钥、缓存、备份、日志
└── boxes.json / schedule.json      收纳箱 / 日程
```

> **换电脑只需要拷 `data/user data`**，软件本身可以重装。

---

## 五、开发

```bash
# 依赖
venv\Scripts\python.exe -m pip install -r requirements.txt

# 语法 + 风格检查（105 个文件，应为 0 处提示）
venv\Scripts\python.exe tests\lint_report.py

# 核心自检（不需要界面）
venv\Scripts\python.exe tests\smoke_core.py

# 界面自检（离屏运行）
set QT_QPA_PLATFORM=offscreen
venv\Scripts\python.exe tests\smoke_gui.py
```

两套自检合计 **1500+ 条断言**，改完代码跑一遍基本能挡住回归。

**分层约定**（很重要，破坏它会很难查）：

* 依赖方向只能 `core → data_manager → ai → services → ui`，**不能反向**
* `data_manager` / `ai` / `services` **不许 import Qt**（少数例外有注释说明）
* 磁盘就是数据库：写入一律"临时文件 + 原子替换"

打包成安装包：

```bash
python installer/build_installer.py      # 产物在 DeepseekData/安装包/
python installer/acceptance.py           # 验收：必须"未发现用户数据"
```

---

## 六、文档

| 文件 | 内容 |
| --- | --- |
| [`Document/Great_White_Planet_使用说明.md`](Document/Great_White_Planet_使用说明.md) | **给用户看的**：怎么用、常见问题 |
| [`Document/Great_White_Planet_功能说明.md`](Document/Great_White_Planet_功能说明.md) | 每个功能的边界与行为细节 |
| [`Document/Great_White_Planet_设计思想.md`](Document/Great_White_Planet_设计思想.md) | 为什么这么设计 |
| [`Document/Great_White_Planet_需求设计文档.md`](Document/Great_White_Planet_需求设计文档.md) | 最初的需求 |
| [`Document/Great_White_Planet_打包说明.md`](Document/Great_White_Planet_打包说明.md) | 怎么打出安装包、怎么发布 |
| [`Document/开发实践——Great White Planet.md`](Document/) | **开发实录**：49 章，每章一个真实问题（含踩坑与复盘） |
| [`Document/Great White Planet 简要说明书.pdf`](Document/) | 一页纸速查 |

《开发实践》那本不是 API 手册，而是**按"当时遇到什么问题"组织的**
—— 包括几次自己写错、把用户真实数据改坏、以及后来怎么加保护的过程。
想了解"为什么代码长这样"，看它会比看代码快。

---

## 七、已知限制

* **只支持 Windows**（依赖 Windows 的证书库、快捷方式、多桌面接口）
* 扫描件 PDF 生成总结时是**图片**（没有文字层，无法变成可搜索文字）
* AI 功能需要自己填 API Key（在「设置」里）；不填也能用非 AI 功能
* 单个书目资料过多时生成 PDF 较慢（每页都要转成图片）

---

## 八、许可

暂未选择开源许可。如需使用请先联系作者。
