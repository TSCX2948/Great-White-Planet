# 开发实践——Great White Planet

**一本用真实项目讲软件工程全流程的书**

---

## 这本书想解决什么问题

市面上的软件开发教程大多是两种：

1. **语言教程**：讲语法、讲 API，但学完不知道一个完整软件是怎么长出来的；
2. **架构书**：讲设计模式、讲分层，但例子都是被抽干净的玩具，看不到"真实项目里那些
   让人半夜爬起来的坑"。

这本书走第三条路：**拿一个真的能用的软件当标本，把它的每一层拆开给你看**。

标本是 **Great White Planet**——一个 Windows 桌面端的学习资料管理与 AI 辅助软件。
它在你的电脑上装着，菜单点得开，数据存得住，安装包能给别人用。
书里出现的每一段代码，都是它**此刻正在跑的代码**，不是事后补的示例。

### 为什么用"少 AI 辅助"当切入点

这个项目的开发过程里确实有 AI 参与，但**关键决策、架构取舍、调试方向、验收标准
都是人做的**。这不是巧合，而是我想教你的重点：

> AI 能把"敲代码"这一步加速十倍，但它不会替你决定**该敲什么代码**。
> 一个软件的成败，八成取决于那些 AI 帮不上忙的地方：
> 需求怎么澄清、边界怎么切、数据怎么落盘、状态怎么保持一致、
> 出了问题怎么定位、做完怎么证明它真的对。

所以这本书的每一章都在回答同一个问题：**如果我只能问 AI 一次，
我该问什么？剩下的我自己要怎么想？**

### 你会学到什么

读完并跟着做一遍，你应该能独立完成这样一件事：

| 能力 | 对应章节 |
| --- | --- |
| 把一段含糊的需求变成能实施的设计 | 第 2、3 章 |
| 给一个桌面软件划出可维护的分层 | 第 4 章 |
| 决定数据怎么存在磁盘上、怎么保证不丢 | 第 5 章 |
| 写 Qt 界面：布局、自定义控件、拖拽、信号槽 | 第 6、7、8 章 |
| 做文件管理类功能：导入导出、剪贴板、回收站 | 第 9、10 章 |
| 把 Markdown 排版成 PDF，还要页码和字体 | 第 11 章 |
| 接第三方 API（AI、天气），还要能优雅降级 | 第 12、18 章 |
| 做版本管理与备份/回退 | 第 13 章 |
| 做 Markdown 编辑器与 AI 双栏 | 第 14 章 |
| 加新功能而不改坏旧代码（需求变更实战） | 第 15、16、17 章 |
| 在没有调试器、只有日志的情况下定位崩溃 | 第 19 章 |
| 写真正有用的测试（断言 900+ 条是怎么来的） | 第 20 章 |
| 打包成"别人电脑上没有 Python 也能装"的安装包 | 第 21 章 |
| 保持代码整洁：静态检查与自动化 | 第 22 章 |
| 踩过的坑与对应的心法 | 第 23 章 |
| 交付后追加的需求怎么接（人设一致性、配置升级、输入体验） | 第 24 章 |
| 拖拽上传为什么放错目录（用户视角 vs 数据视角） | 第 25 章 |
| 标签计数为什么对不上（同一个数字两种算法） | 第 26 章 |
| AI 读图功能怎么做才安全（不可靠时宁可缺不可编） | 第 27 章 |
| 本地有内容但界面不显示（列表的层级问题） | 第 28 章 |
| 需求里的名词实现不了时怎么办（AI 附件） | 第 29 章 |
| "关闭"不等于"退出"引出的新问题（后台驻留） | 第 30 章 |
| 交互需求如何规定数据结构（单词书） | 第 31 章 |
| 两个只在特定环境出现的 bug（VSCode 启动 / 刷新层级） | 第 32 章 |
| 把自由度收掉（固定宽度 / 就近跳转） | 第 33 章 |
| "白色竖条要靠右"：位置 bug 的推理 | 第 34 章 |
| 全黑窗口与必崩的 nativeEvent（唤回窗口） | 第 35 章 |
| 改数据的归属（单词书改成全局共用） | 第 36 章 |
| 互相依赖的尺寸锁死（科目卡不换行） | 第 37 章 |
| 任务栏图标与应用标识（返回成功却查不回来） | 第 38 章 |
| 功能异常背后的两个缺陷（作业改名） | 第 39 章 |
| 公式渲染、缓存失效与文档合并 | 第 40 章 |
| 排版器不收敛：一次 12 GB 的清理 | 第 41 章 |
| 把 AI 从主流程里拿出来（改职责，不是加功能） | 第 42 章 |
| 闪退：Qt 在"线程还在跑"时会直接中止进程 | 第 43 章 |
| 后台监听数据变化，同时把 CPU 压到 0.16% | 第 44 章 |
| 技术路线变更：产物改成合并 PDF | 第 45 章 |
| 让 AI 只在文末写一小段知识点补充 | 第 46 章 |
| 同一个错误犯两次后，把保护放到解释器那一层 | 第 47 章 |
| 作业完成状态：先分清「取消哪一类颜色」 | 第 48 章 |
| 文件夹层级与右键新建的两个 bug | 第 49 章 |
| 论坛列表：从写死到用户自己维护 | 第 50 章 |
| 日程栏只留「还要动手的事」 | 第 51 章 |
| AI 让软件去问：一条被只管图片卡住的岔路 | 第 52 章 |
| 把阻塞调用挪到后台：单词补齐卡死 | 第 53 章 |

### 怎么读这本书

**别一次读完。** 这本书是按"做一遍"的节奏写的：

* **Part 1（第 1–5 章）**：项目从想法到架构与数据层。
  读完你应该能自己画出分层图，并知道数据该怎么落盘。
* **Part 2（第 6–14 章）**：界面与核心功能逐个实现。
  每章开头都写清"问题是什么"，然后是"怎么想"，最后才是"代码长什么样"。
* **Part 3（第 15–18 章）**：**需求变更实战**。
  这部分专门讲"需求变了怎么办"，因为真实项目里需求一定会变，
  而教科书从不教你这件事。
* **Part 4（第 19–53 章）**：工程质量与收尾。调试、测试、打包、整洁、踩坑，
  **交付之后需求还在来时怎么接**（第 24 章），
  五个真实问题的完整解剖：语义错误（第 25 章）、一致性错误（第 26 章）、
  层级错误（第 28 章）、"需求名词实现不了"（第 29 章）、
  一个优化引出的新问题（第 30 章），
  交互需求怎么落到数据结构上（第 31 章），
  两个只在特定环境才出现的 bug（第 32 章），
  把过度自由的设计收回来（第 33 章），
  一个位置 bug 怎么查到真凶（第 34 章），
  用错机制导致的两个真机故障（第 35 章），
  改数据结构时怎么不丢用户的数据（第 36 章），
  布局里两个尺寸互相锁死怎么打破（第 37 章），
  一个设置成功却查不回来的弯路（第 38 章），
  一句功能异常背后的两个缺陷（第 39 章），
  公式渲染与文档合并（第 40 章），
  一次修不好但限制住了的排版事故（第 41 章），
  把 AI 从主流程里拿出来（第 42 章），
  以及**一次窗口突然消失的排查**（第 43 章），
  最后是**怎么在后台盯着文件变化却不烧 CPU**（第 44 章），
  以及**一次"把功能做减法"的技术路线变更**（第 45 章），
  加上**一个 AI 功能怎么做到"不可靠也安全"**（第 27 章）。

每一章末尾都有一节 **「自己动手」**，给你一个小练习。
**请务必真的动手**——看懂代码和写出代码之间的距离，比你想的大得多。

### 关于代码的约定

* 代码块都标了文件路径，例如 `gwp/data_manager/store.py`。
  以 `code/` 为根目录（即项目里 `code/gwp/...`）。
* 为了篇幅，长函数会**省略无关部分**，用 `…` 标记。省略的地方都会说明。
* 涉及"当时写错了、后来改对了"的地方，我会**保留错误版本并说明为什么错**。
  只看正确版本学不到东西——**真正的经验藏在失败里**。

### 项目规模（供你对照自己的进度）

| 部分 | 文件数 | 行数 |
| --- | --- | --- |
| 主程序 `gwp/` | 88 | ≈ 21,500 |
| ├─ `core/` 基础层 | 8 | ≈ 1,400 |
| ├─ `data_manager/` 数据层 | 9 | ≈ 2,400 |
| ├─ `ai/` AI 层 | 12 | ≈ 2,500 |
| ├─ `services/` 服务层 | 12 | ≈ 3,200 |
| └─ `ui/` 界面层 | 40 | ≈ 10,600 |
| 测试 `tests/` | 3 | ≈ 4,900（含 900+ 条断言）|
| 打包与安装器 `installer/` | 8 | ≈ 1,800 |

一个中等规模桌面软件。**不是玩具，但也不是大到看不完**——
这个体量刚好够让你看清所有真实问题。

---

## 需求文档 → 本书章节 对照表

本项目有一份需求文档（`Document/Great_White_Planet_需求设计文档.md`），
它决定了软件要做成什么样。下表告诉你"需求的每一部分，在书里对应哪一章"：

| 需求文档章节 | 内容 | 本书章节 |
| --- | --- | --- |
| 一、软件定位 | 做什么、给谁用 | 第 3 章 |
| 二、整体层级结构 | 首页/科目/书目三层 | 第 4、6 章 |
| 三、Subject 设计 | 卡片、右键、存储 | 第 7、8 章 |
| 四、Book 设计 | 目录结构、各文件夹用途 | 第 5、9 章 |
| 五、Summary 生成规则 | 总结原则、PDF 处理 | 第 11、13 章 |
| 六、Summary 版本管理 | 备份与恢复 | 第 14 章 |
| 七、AI 系统设计 | 多提供方、AI 规则、双栏 | 第 13、15 章 |
| 八、界面设计 | 主界面、文件打开、AI 双栏 | 第 6、16 章 |
| 九、菜单栏设计 | 各菜单项 | 第 12 章 |
| 十、文件存储规则 | 数据放哪 | 第 5 章 |
| 十一、开发要求 | 不许写死、可扩展 | 第 4 章 |
| 十二、AI 扩展规划 | 预留扩展点 | 第 13 章 |
| 十三、启动优化 | 预扫描、缓存 | 第 5 章 |
| 十四、当前技术方案 | 技术选型 | 第 4 章 |
| *（开发过程中陆续追加的需求）* | 收纳箱、日记、作业、日程、论坛… | 第 17–19 章 |

> **注意最后一行。** 需求文档只写了初版需求，而软件最终有 20 多个功能。
> 多出来的那些是怎么来的、怎么融进已有架构而没把代码搞烂——
> 这是第 17–19 章的主题，也是**真实开发与教科书最大的差别**。

---

# 第一部分　从想法到能动手

> 这一部分的目标只有一个：**让你在写第一行代码之前，知道自己在写什么。**
>
> 很多人卡在"不知道从哪开始"，本质不是不会写代码，
> 而是**没把问题想清楚**。想清楚了，写代码是最快的一步。

---

## 第 1 章　开发全流程总览

### 1.1 先说结论：一个软件是怎么长出来的

不管你用什么语言、什么框架，做一个能交付的软件，都要走完这条链：

```
想法
 └─→ 需求（要解决什么问题、给谁用、做到什么算完成）
      └─→ 设计（分成几块、每块负责什么、数据怎么存）
           └─→ 实现（写代码，一块一块做）
                └─→ 验证（怎么证明它真的对）
                     └─→ 交付（别人怎么装上、怎么用）
                          └─→ 维护（需求变了怎么办、出问题怎么查）
```

听起来像废话。但**真实项目里翻车，九成是因为跳过了其中一环**：

| 跳过了什么 | 会怎么翻车 | 本书对应章节 |
| --- | --- | --- |
| 需求 | 做到一半发现方向错了，返工 | 第 2 章 |
| 设计 | 代码越写越乱，改一个功能崩三个 | 第 3、4 章 |
| 数据设计 | 用户数据丢了、或状态对不上 | 第 5 章 |
| 验证 | 交付后用户一用就是 bug | 第 21 章 |
| 交付 | 用户电脑上跑不起来 | 第 22 章 |
| 维护准备 | 加一个功能要改十处，最后不敢改 | 第 17–19 章 |

### 1.2 一条重要的经验：把"能不能改"当第一优先级

初学者最容易犯的错，是**把"现在能跑"当成目标**。
但软件的生命周期里，**写代码只占 20%，剩下 80% 是改它**。

所以真正的目标应该是：

> **让下一次修改尽可能便宜。**

这个项目有个很硬的例子。看两段代码，都是"给科目加一个类型"这件事：

```python
# ❌ 写法一：把类型判断散落到各处
if subject_type == "diary":
    tabs = ["AI 思想总结", "AI 日记", "我的日记", "其它日记", "全部条目"]
    dirs = ["AI summary", "AI diary", "my diary", "else diary"]
elif subject_type == "school":
    tabs = ["AI 总结", "简介", "笔记", "作业", "易错题", "教材", "全部条目"]
    ...
```

```python
# ✅ 写法二：把差异收进一张声明表（gwp/core/constants.py）
BOOK_TABS_SCHOOL = (
    ("summary", "AI 总结", None),
    ("intro", "简介", None),
    ("notebook", "笔记", NOTEBOOK_FOLDER),
    ("homework", "作业", HOMEWORK_FOLDER),
    ...
)
BOOK_TABS_BY_TYPE = {
    SUBJECT_SELF_STUDY: BOOK_TABS_SELF_STUDY,
    SUBJECT_SCHOOL: BOOK_TABS_SCHOOL,
    SUBJECT_DIARY: BOOK_TABS_DIARY,
}

def tabs_for_type(subject_type: str) -> tuple:
    return BOOK_TABS_BY_TYPE.get(subject_type or DEFAULT_SUBJECT_TYPE,
                                 BOOK_TABS_SELF_STUDY)
```

写法二的好处，在"加一个栏目"时立刻兑现：

```python
# 需求：给自学课和校修课加一个「其它文件」栏目
# 改动量：一个常量 + 两行表数据
OTHERS_FOLDER = "others"

BOOK_TABS_SELF_STUDY = (..., ("others", "其它文件", OTHERS_FOLDER), ...)
BOOK_TABS_SCHOOL     = (..., ("others", "其它文件", OTHERS_FOLDER), ...)
```

**界面、数据层、AI 层一行都不用改。** 这就是"让下一次修改便宜"的具体样子。

> **判断一段代码好坏的最快方法**：
> 问自己"如果这个需求变了（多加一个类型、多一个栏目、换一种格式），
> 我需要改几个文件？"
> ——改 1 个文件是设计得好，改 5 个是设计得凑合，改 10 个是**该重构了**。

### 1.3 技术选型的思路

这个项目选了 **Python + PyQt6**。为什么？不是因为它最好，而是因为**它匹配约束**：

| 约束 | 影响选型 |
| --- | --- |
| 要做 Windows 桌面软件，有窗口、菜单、拖拽 | 需要成熟 GUI 框架 → Qt |
| 开发者熟悉 Python，且要处理大量文本/Markdown/Office 文件 | Python 生态最省事 |
| 需要打包成"别人电脑不装 Python 也能用" | Python 有 PyInstaller |
| 要调 AI API、解析 PDF/docx/pptx/xlsx | Python 库齐全 |

**选型的正确姿势不是"哪个技术最好"，而是"哪个技术最贴合我的约束"。**

具体到关键决策：

| 决策 | 选择 | 为什么 |
| --- | --- | --- |
| GUI 框架 | PyQt6（Qt 官方绑定） | Qt 组件全、拖拽/自定义绘制成熟、跨平台 |
| 数据存储 | **直接用文件夹和文件**，不用数据库 | 见 1.4 |
| 配置格式 | JSON | 人能直接读改，出问题好查 |
| AI 接入 | 可插拔适配器 + 兜底链 | 见第 13 章 |

### 1.4 一个贯穿全书的决策：用文件夹当数据库

这个软件**没有数据库**。所有数据就是磁盘上的文件夹和文件：

```
data/
├── boxes.json              收纳箱
├── schedule.json           其它日程
└── user data/
    └── subjects/
        └── 高等代数/
            ├── subject.json
            └── 高等代数/
                ├── Introduct.md
                ├── notebook/
                ├── error-prone/
                ├── book/
                ├── homework/
                └── others/
```

为什么？因为它带来三个**对这个项目至关重要**的好处：

1. **用户的数据永远是用户的。** 用记事本就能看懂，能直接拷走，
   软件坏了数据也不会坏。**这个软件管理的是学生的学习资料，
   一旦丢了对用户的信任是毁灭性的。**
2. **不需要写"导入导出"。** 数据本来就在文件系统里，
   想备份就用资源管理器复制。
3. **调试简单。** 出了问题，打开文件夹看一眼就知道状态，
   不用连数据库、写 SQL 查。

代价也有：**没有事务、没有并发控制、没有查询语言**。
所以要用一章（第 5 章）专门讲"怎么在没有数据库的情况下保证数据不出错"——
这是这本书里最实用的一章。

> **选型心法**：先问"我的数据有多大、多少人在同时改、要不要复杂查询"。
> 这个软件的数据是"几十个科目、几千个文件、只有一个人用"，
> 上数据库纯属自找麻烦。

### 1.5 自己动手

1. 找一个你天天在用的小工具（哪怕是手机上的待办清单），
   试着回答：**它的数据存在哪？** 是文件、数据库还是云端？
2. 列出你最近想做的一个小软件，写下它的**约束**（谁用、几个平台、数据多大、
   要不要联网），然后**先别选技术**，只看约束排在纸上。
3. 找一段你自己写过的代码，问："如果需求加一项，我要改几个文件？"
   如果超过 3 个，那就是你第一个值得重构的地方。

---

## 第 2 章　需求分析：把"想要"变成"要做"

### 2.1 原始需求长什么样

这个项目拿到的原始需求，开头是这样的：

> 按照文档需求开发软件，有任何不懂或者模糊的地方，请调用你的提问工具向我提问。
> 同时，**不要把代码写死**，便于开发完成升级和修改。

三句话，但每一句都是**关键信息**：

| 原话 | 真实含义 |
| --- | --- |
| "按照文档需求开发" | 有一份需求文档，是**主要依据** |
| "有模糊的地方要提问" | 需求方**知道**文档不完整，愿意澄清 |
| "不要把代码写死" | 需求方**预期未来会改**，这是硬性架构约束 |

**新手最容易忽略第三句。** 很多人看到"不要把代码写死"会想
"这不废话吗，谁会把代码写死"——然后写出满屏的
`if subject_type == "diary"`。

而正确的读法是：**这一句直接决定了架构选型**（回到 1.2 的声明表）。

### 2.2 需求文档里"没写"的部分才是重点

需求文档写了 14 节，但**没写**的东西包括：

* 科目删除后数据怎么办？（回收站还是永久删除？）
* 两个窗口同时打开同一份数据怎么办？
* AI 调用失败、断网了怎么办？
* 用户电脑没装 Python 怎么办？
* PDF 里的图片怎么处理？

**这些不是文档的缺陷，而是所有需求文档的常态。**
写文档的人只能写"想清楚的部分"，剩下的要靠**做的时候问**。

### 2.3 澄清提问的方法

问问题也有技术含量。**差的提问和好的提问差别巨大**：

| ❌ 差的提问 | ✅ 好的提问 | 为什么 |
| --- | --- | --- |
| "删除功能怎么做？" | "删除科目时，是移入回收站还是永久删除？" | 给出选项，对方 1 秒能答 |
| "AI 用哪个？" | "AI 提供方要支持几个？只接 DeepSeek 够不够，还是以后可能换 GPT？" | 问的是**边界**，决定要不要抽象 |
| "界面要好看吗？" | "卡片上要显示几个文件吗？要显示科目类型吗？" | 可验证、能直接变成字段 |

**提问的三个原则**：

1. **给选项而不是开放式问。** 对方是决策者，不是设计师。
2. **问边界。** "以后可能变成两个吗？" 这个问题的答案决定了要不要抽象。
3. **问可验证的东西。** "卡片副标题显示『日记 · 5 个文件』"能直接写成断言；
   "界面要友好"不能。

### 2.4 需求会变，而且会一直变

这个项目在初版需求之外，**追加了 20 多项需求**。看一部分真实记录：

```
错题/易错 改为 易错题
AI总结要在第一个
资料概览要求可折叠 → 不要这样 直接放在右侧 默认折起
生成一个 PDF → 要
加入背景图（data\else data\background，旧图不要删，只往后加编号）
作业 要放在 笔记 后面（不是 AI 总结里）
加一个 日记 类型的 Subject
自学课 / 校修课 的「其它文件」栏目，可以右键新建文件夹
自学 Subject 和校修 Subject 允许右键改类型
校修 Subject 的作业栏目改为「创建作业」：作业内容 / DDL / 提交方式
首页右侧增建任务栏，显示日程（作业 + 其它日程），按 DDL 排序，有完成按键
日程栏上方增设 日期-时间-天气
首页菜单增加 论坛
新创建的 Subject / Book 默认排在列表最后
不要弹出这个窗口，在软件内部打开文件夹，JSON 用 VSCode 打开
```

**请仔细看这份清单**，因为它揭示了真实开发的节奏：

* 大部分是**小调整**（文案、位置、排序）——这些不该伤筋动骨；
* 少部分是**新功能**（日程、天气、论坛）——这些会加新文件，但**不该改旧文件**；
* 还有**推翻前面的决定**（"不要这样，直接放在右侧"）——这最考验架构。

> **判断架构好坏的终极标准**：
> 当用户说"不要这样"时，你改起来有多痛。
> 架构好 = 用户改主意你只改一个文件；架构差 = 用户改主意你要重构三天。

### 2.5 把需求写成可执行的形式

需求分析的产出不是"我懂了"，而是**一份能照着做的东西**。这个项目用三种形式：

**① 需求文档**（`Document/Great_White_Planet_需求设计文档.md`）
——沟通用，写清"做什么、为什么"。

**② 目录结构约定**（第 1.4 节那张树）
——数据用，写清"东西放哪"。**这一份最不容易出歧义。**

**③ 声明表**（`gwp/core/constants.py`）
——代码用，写清"类型和栏目怎么对应"。

三者关系：

```
需求文档（人话）
   ↓ 翻译
目录结构 + 声明表（机器能执行）
   ↓ 驱动
界面与逻辑（不用再判断"这是什么类型"）
```

**关键设计**：第三层是"数据"，不是"代码"。
加一个栏目就是加一行数据，不需要写新的 if。

### 2.6 自己动手

1. 找一份你写过的需求/功能说明，**列出它没说的 5 个问题**，
   然后为每个问题写一个"给选项"的提问。
2. 拿你在 1.5 列的那个小软件，写出它的**目录结构**（如果不用数据库）
   或**表结构**（如果用）。
3. 假设用户第二天告诉你"那个功能我不要了，改成另一种做法"，
   问自己：**我需要改几个文件？**

---

## 第 3 章　整体设计：先把骨架搭对

### 3.1 从需求到架构的第一步：找出"名词"

架构不是凭空想出来的，它来自需求里的**名词**。看需求文档里的名词：

```
首页、Subject（科目）、Book（书目）、Summary（总结）、
Introduct.md、book、error-prone、notebook、AI、菜单栏
```

把这些名词**按"谁包含谁"排一排**，层级就出来了：

```
首页（Home）
 └── Subject 科目（一个文件夹）
      └── Book 书目（一个文件夹）
           ├── Introduct.md   简介
           ├── notebook/      笔记
           ├── error-prone/   易错题
           ├── book/          教材
           └── <书名>_summary.md  AI 总结
```

**这就是需求文档第二节"整体层级结构"的由来**，
也是整个软件的数据模型。**界面就是它的投影。**

> **一个屡试不爽的方法**：把需求里的名词画成一张树，这张树
> 既是数据存放结构，也是界面导航结构，还是代码模块划分的依据。
> 三者一致，软件就不会乱。

### 3.2 「磁盘即数据库」的后果：界面必须由扫描生成

如果数据就是文件夹，那么有一条铁律：

> **软件不能"记住"有哪些科目，必须每次去磁盘上看。**

因为用户可以：
* 在资源管理器里直接删掉一个科目文件夹；
* 手动改 `subject.json`；
* 从别的电脑拷一个科目目录进来。

如果软件维护一份自己的"科目列表"，它立刻会和磁盘不一致。

于是有了**第一条架构原则**：

```
原则 1：磁盘就是数据库
        —— 界面由扫描结果生成，不维护第二份真相。
```

代码上的体现（`gwp/data_manager/store.py`）：

```python
def subjects(self, refresh: bool = False, with_books: bool = True) -> list[Subject]:
    """扫描 subjects 目录，每个子目录 = 一个科目。"""
    if self._subjects is not None and not refresh:
        return list(self._subjects)          # 缓存
    result: list[Subject] = []
    for child in sorted(self.paths.subjects_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        meta = meta_io.load_subject_meta(child)     # 读 subject.json
        result.append(Subject(
            name=child.name,
            path=child,
            display_name=str(meta.get("display_name") or child.name),
            subject_type=str(meta.get("subject_type") or C.DEFAULT_SUBJECT_TYPE),
            order=int(meta.get("order", 0) or 0),
            ...
        ))
    subjects.sort(key=lambda s: (not s.pinned, s.order, s.title.lower()))
    self._subjects = result
    return list(result)
```

注意几个设计点：

* **没有 `if name not in known_subjects`** —— 磁盘上有就是有；
* **`subject.json` 缺失也不崩** —— `meta.get(..., 默认值)` 一路兜底，
  所以用户手工建的文件夹也能被识别（类型默认按"自学课"处理）；
* **`sorted()` 保证顺序稳定** —— 否则每次扫描顺序可能变，界面会闪。

### 3.3 第二条原则：不写死任何具体的名字

需求说"不要把代码写死"。具体到代码，就是：

```python
# ❌ 写死
if book == "高等代数":
    ...

# ✅ 由扫描/配置决定
for subject in library.subjects():
    ...
```

一个更细的例子——**界面标签也不写死**：

```python
# gwp/core/constants.py
#: 每个标签的含义：(key, 标签文案, 目录名)
BOOK_TABS_SELF_STUDY = (
    ("summary", "AI 总结", None),        # None = 不是真实目录（虚拟标签）
    ("intro", "简介", None),
    ("notebook", "笔记", NOTEBOOK_FOLDER),
    ("homework", "练习", HOMEWORK_FOLDER),   # 自学课叫「练习」
    ("error-prone", "易错题", ERROR_FOLDER),
    ("book", "教材", BOOK_FOLDER),
    ("root", "全部条目", None),
)
```

**注意 `homework` 这一项**：自学课叫「练习」，校修课叫「作业」，
但**目录名都是 `homework`**。这个设计的好处：

* 数据层不用知道有"类型"这回事；
* 剪贴板、导入导出、AI 总结全都不用判断类型；
* 只有**界面文案**分叉。

一句话总结这个原则：

> 原则 2：界面由扫描结果生成。
> —— 目录语义不分叉，界面用词才分叉。

### 3.4 第三条原则：整合而不是概括（AI 总结的定位）

需求文档第五节写得很明确。这是我见过**最有产品思维的一段需求**：

> Summary 不是摘要，而是一份**完整的学习文档**：
> * 把 `Introduct.md`（目标）+ `notebook`（笔记）+ `error-prone`（易错题）合并；
> * 补全缺失的推导、定理条件、常见陷阱与辨析；
> * 把易错题转成「错误表现 → 根本原因 → 正确做法 → 同类变形」的清单；
> * 列出「待确认问题」。

**为什么这段需求重要？** 因为它决定了代码怎么组织：

```python
# gwp/ai/summarizer.py
def build_prompt(self, book: Book, materials: list) -> str:
    parts = [
        self._system_prompt(),                       # 角色与要求
        self._intro_section(book),                   # 学习目标
        self._materials_section(materials, "笔记"),   # 笔记
        self._materials_section(materials, "易错题"), # 易错题
        self._output_format_section(),               # 输出格式约束
    ]
    return "\n\n".join(p for p in parts if p)
```

如果是"摘要"，代码会是"把资料塞进去，让 AI 压一压"。
因为是"整合扩展"，代码必须**分节、让 AI 知道每一块是什么、以及要补什么**。

> **需求的一句话，往往决定一段代码的结构。**
> 这就是为什么第 2 章那么重要。

### 3.5 分层：把"会变的东西"和"不变的东西"分开

三条原则之后，架构自然浮出来了。核心思路是：

> **按"变化的速度"分层。**
> 变得慢的在下层，变得快的在上层；上层依赖下层，下层不认识上层。

```
        ui/            ← 变得最快（用户天天提界面意见）
         ↓
     services/         ← 较快（文件操作、导出、主题）
         ↓
        ai/            ← 中等（换提供方、改提示词）
         ↓
   data_manager/       ← 较慢（数据结构，改一次要迁移）
         ↓
       core/           ← 最慢（路径、常量、配置）
```

**依赖方向必须单向**。这条纪律带来的收益：

* 想换界面框架？只动 `ui/`；
* 想换 AI 提供方？只加一个 `ai/providers/xxx.py`；
* 想改数据格式？只动 `data_manager/`。

**违反这条纪律会怎样？** 举个真实的反例：

```python
# ❌ 数据层里 import Qt —— 依赖方向反了
from PyQt6.QtWidgets import QMessageBox

def delete_book(self, subject, book):
    if QMessageBox.question(None, "确认", "删除？") != QMessageBox.Yes:
        return
    shutil.rmtree(...)
```

后果是：

1. **数据层没法单独测试**（跑测试要起一个 Qt 应用）；
2. **没法在命令行里用**（CLI 工具一导入就崩）；
3. 界面和逻辑搅在一起，换界面就要动数据。

所以这个项目里有一条硬规则，写进了 `gwp/data_manager/__init__.py` 的注释：

```python
"""数据层：只依赖 core，**不允许 import Qt**。

这条纪律保证：
* data_manager 可以在没有图形环境的机器上测试；
* CLI（gwp/cli.py）能复用同一套逻辑；
* 将来换界面不必动数据层。
"""
```

> **怎么检查依赖方向？** 一条命令就够：
> ```powershell
> Select-String -Path "gwp\data_manager\*.py" -Pattern "^from PyQt6|^import PyQt6"
> ```
> 输出为空 = 纪律守住了。这个项目把它做成了自动检查（第 21 章）。

### 3.6 唯一允许的例外，以及为什么

规则总要有例外，但**例外必须写清楚理由**。这个项目唯一违反"层内不 import Qt"
的地方是 `gwp/ai/worker.py`：

```python
"""AI 后台工作线程。

这个文件是 ai/ 层里**唯一**允许 import Qt 的地方，因为它存在的意义
就是"把 Qt 的线程机制接到 AI 调用上"。AI 逻辑本身（summarizer、providers）
仍然完全不认识 Qt。
"""
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class AIWorker(QThread):
    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)
```

**为什么这是好设计？**

* 例外只有**一个文件**，而且它的职责就是"胶水"；
* 其他 AI 模块（提示词、适配器、总结逻辑）依然纯净；
* 这个例外被**明确写进了文档**，所以下次有人想"顺手 import 一下 Qt"
  时会看到这条注释并停下来。

> **架构纪律的落地方式**：
> 不是"绝对禁止"，而是"默认禁止 + 例外必须有名有姓、写明理由"。
> 绝对禁止的规则活不过三个月。

### 3.7 自己动手

1. 把你 2.6 里列的小软件的**名词树**画出来，标出哪些是"目录"、哪些是"文件"。
2. 给它分三层（界面 / 逻辑 / 数据），写下**依赖方向**。
3. 找出一个"可以接受的例外"，并写一句话理由。
（提示：几乎没有软件能做到零例外，关键是例外要**少、明确、有理由**。）

---

## 第 4 章　目录结构、启动流程与基础层

### 4.1 先看整棵树

```
code/
├── gwp_main.py              程序入口（打包成 exe 后直接跑它）
├── run.pyw                  Windows 上双击启动（不弹黑框）
├── gwp.spec                 PyInstaller 打包配置
├── gwp/                     主程序
│   ├── __init__.py
│   ├── app.py               创建 QApplication、单实例、把主窗口立起来
│   ├── bootstrap.py         组装 AppContext（把所有管理器串起来）
│   ├── cli.py               命令行工具（不启动界面也能用）
│   ├── core/                ← 最底层：常量、路径、配置、日志、事件总线
│   ├── data_manager/        ← 数据层：扫描、读写、备份、日程、收纳箱
│   ├── ai/                  ← AI 层：提供方适配器、总结、聊天、后台线程
│   ├── services/            ← 服务层：文件操作、剪贴板、PDF 导出、主题、背景
│   ├── ui/                  ← 界面层：主窗口、视图、对话框、控件
│   └── resources/           ← 图标等资源
├── tests/                   自检脚本（smoke_core / smoke_gui / lint_report）
└── installer/               安装器与打包脚本
```

**这个结构本身就是一份设计说明。** 你打开项目第一眼就应该能回答
"界面代码在哪"（`ui/`）、"数据怎么存"（`data_manager/`）、
"AI 怎么接"（`ai/`）。

> **目录结构的评判标准**：一个新人拿到项目，**30 秒内**能不能找到
> "我要改的那个东西"在哪。找不到，说明结构按"技术"分了（比如 `utils/`、
> `helpers/`），而不是按"职责"分。

### 4.2 启动流程：把所有东西串起来

启动是最容易被忽视、却最影响"第一印象"的部分。
这个项目把它拆成三段，每段职责单一：

```
gwp_main.py    →  进程入口：异常兜底、单实例检查、交给 app.py
   ↓
app.py         →  创建 QApplication、设置高 DPI、把窗口立起来
   ↓
bootstrap.py   →  组装 AppContext（配置、数据路径、各管理器）
```

**为什么拆三段？** 因为它们的**生命周期不同**：

| 阶段 | 什么时候跑 | 能不能有 Qt |
| --- | --- | --- |
| `bootstrap` | 可能在命令行里跑（`gwp export ...`） | **不能** |
| `app` | 只在启动界面时跑 | 必须 |
| `gwp_main` | 只在打包成 exe 后跑 | 必须 |

关键是我把**组装逻辑（`bootstrap`）和 Qt 解耦**了。看 `bootstrap.py`：

```python
def bootstrap(argv: list[str] | None = None) -> AppContext:
    """初始化软件运行时。可在创建 QApplication 之前调用。"""
    argv = list(argv if argv is not None else sys.argv[1:])

    config = Config.load()                    # 读配置（纯 Python）
    paths = set_current(DataPaths(config))    # 解析数据路径

    setup_logging(paths.log_dir, log_level, keep_days)
    paths.ensure()                            # 建好目录
    ...
    return AppContext(
        config=config, paths=paths,
        library=Library(config, paths),       # 数据层
        ai=AIManager(config),                 # AI 层
        summarizer=Summarizer(config, library, ai),
        backups=BackupManager(config, paths),
        chats=ChatStore(config, paths),
        cache=ScanCache(paths),
        root=..., argv=argv,
    )
```

`AppContext` 是个**纯数据类**，持有所有管理器：

```python
@dataclass
class AppContext:
    """运行时的共享上下文。所有界面控件都持有它的引用。"""
    config: Config
    paths: DataPaths
    library: Library
    ai: AIManager
    summarizer: Summarizer
    backups: BackupManager
    chats: ChatStore
    cache: ScanCache
    root: Path
    argv: list[str] = field(default_factory=list)
    services: dict = field(default_factory=dict)
```

**为什么用"一个 Context 传下去"，而不是到处写 `import` 全局单例？**

* **可测试**：测试里可以造一个假的 Context，指向临时目录；
* **可多实例**：理论上能同时开两套（虽然本软件用单实例限制）；
* **依赖显式**：看函数签名 `def refresh(self)` 里的 `self.context.library`
  就知道它用了什么，不用去猜全局状态。

这是**依赖注入**的最朴素形式，不需要任何框架。

### 4.3 懒加载：让启动变快

`AppContext` 里有几个成员不是构造时就建的。看 `services` 字段的用法：

```python
@property
def clipboard(self):
    """文件剪贴板。全局共享，切换书目时内容不丢。"""
    from gwp.services.file_clipboard import FileClipboard
    clipboard = self.services.get("clipboard")
    if clipboard is None:
        clipboard = FileClipboard()
        self.services["clipboard"] = clipboard
    return clipboard

@property
def schedule(self):
    """首页右侧日程栏用的"其它日程"存储。"""
    from gwp.data_manager.schedule import ScheduleStore
    store = self.services.get("schedule")
    if store is None:
        store = ScheduleStore(self.paths.data_root)
        self.services["schedule"] = store
    return store
```

**三个设计点**：

1. **`import` 写在使用它的函数里面**（叫"惰性导入"）——
   这样启动时不用把所有模块都加载一遍；
2. **用 `services` 字典缓存** —— 只在第一次访问时创建；
3. **`reload_paths()` 里要清掉这些缓存**，否则切换数据目录后
   还指着老目录：

```python
def reload_paths(self) -> None:
    """数据根目录被改动后重新解析路径。"""
    self.paths = set_current(DataPaths(self.config))
    self.paths.ensure()
    self.library = Library(self.config, self.paths)
    ...
    self.services.pop("backgrounds", None)   # 重建背景管理器指向新目录
    self.services.pop("schedule", None)      # 日程也指向新的数据根目录
```

> **踩坑提醒**：只要你用了"懒加载 + 缓存"，就一定要找到
> **所有让缓存失效的时机**（换目录、换配置、删数据）。
> 这类 bug 的共同症状是："重启一下就好了。"

### 4.4 基础层：`core/` 里放什么

`core/` 是最底层，**不依赖任何其他层**。它只有 8 个文件：

| 文件 | 职责 | 为什么放在最底层 |
| --- | --- | --- |
| `constants.py` | 所有常量与声明表 | 全项目都要用，且不依赖任何东西 |
| `paths.py` | 路径解析（数据根、配置、日志、文档） | 所有层都要知道"文件在哪" |
| `config.py` | 配置读写的深合并 | 所有层都要读配置 |
| `logging_setup.py` | 日志 | 所有层都要记日志 |
| `eventbus.py` | 极简事件总线 | 解耦"谁改了数据"和"谁要刷新" |
| `errors.py` | 自定义异常 | 统一错误类型 |

**注意 `paths.py` 的职责边界**：它只回答"文件在哪"，
**不负责创建目录**（那是 `DataPaths.ensure()` 的事），
**不负责读写**（那是 `data_manager` 的事）。职责越窄，越好复用。

### 4.5 `paths.py`：一个"跨机器"的实战问题

路径处理听起来简单，其实是**最容易出跨机器 bug** 的地方。
看这个项目遇到的一组真实约束：

| 约束 | 后果 |
| --- | --- |
| 开发时源码在 `code/`，数据在 `../data/` | 路径不能写死 |
| 打包成 exe 后没有 `code/` 目录了 | 要用**不同的规则**找资源 |
| 用户可能把数据放到 D 盘、移动硬盘 | 数据根目录必须可配置 |
| 首次运行时数据目录还不存在 | 找不到时不能崩，要能"预判" |

代码怎么解决（`gwp/core/paths.py`）：

```python
ENV_ROOT = "GWP_ROOT"          # 环境变量可覆盖（测试与便携模式用）

def is_frozen() -> bool:
    """是不是打包成 exe 在跑。"""
    return bool(getattr(sys, "frozen", False))

def project_root() -> Path:
    """项目根目录。打包后 = exe 所在目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

def bundle_dir() -> Path:
    """随包资源目录。PyInstaller 解包到 sys._MEIPASS。"""
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        return Path(meipass)
    return project_root()
```

**关键技巧**：**判断"是不是打包环境"只写一处**（`is_frozen()`），
其他所有地方都调它。这样将来换打包工具，只改一个函数。

再看"首次运行时数据目录还不存在"这个坑。朴素写法会这样：

```python
if not candidate.is_dir():          # ❌ 不存在就退回默认位置
    return default_data_root()
```

问题：用户把数据根目录设到 `E:\我的资料`，**第一次**跑（目录还没建），
这段代码会认为路径无效，退回默认位置——**用户设置被"吃"了**。

正确做法是**区分"不存在"和"不可用"**（`DataPaths._resolve_data_root()`）：

```python
def _resolve_data_root(self, configured: str) -> Path:
    """解析数据根目录。

    关键区别：
    * 目录**不存在** → 保留这个路径（首次运行，待会儿 ensure() 会建）；
    * 路径被**文件占住**、或祖先目录不可写 → 退回默认位置并记日志。
    """
    candidate = Path(configured).expanduser()
    if candidate.exists():
        if not candidate.is_dir():
            log.warning("数据根目录被文件占用，改用默认位置：%s", candidate)
            return default_data_root()
        return candidate
    # 不存在：看看它的祖先能不能建
    ancestor = candidate
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if ancestor.is_dir() and os.access(ancestor, os.W_OK):
        return candidate                 # ✅ 保留用户设置
    log.warning("数据根目录不可用，改用默认位置：%s", candidate)
    return default_data_root()
```

> **这一段的经验价值极高**：区分"**不存在**"和"**不合法**"是
> 数据处理的基本功。把两者混为一谈，就会做出"用户第一次设置无效"
> 这种让人莫名其妙的行为。

### 4.6 配置：深合并与"密钥分离"

配置用 JSON，但要解决三个问题。

**问题 1：加了新配置项，老用户的配置文件里没有。**
解决：**默认值深合并**。

```python
DEFAULT_CONFIG = {
    "ui": {
        "theme": "light",
        "font_family": "Microsoft YaHei UI",
        "font_size": 10,
        "card": {"width": 190, "height": 118, "radius": 14},
        "show_clock_bar": True,
        "weather_enabled": True,
    },
    "forum": {"laoda_cs_url": "https://cs9.x-way.work/"},
    "startup": {"autostart": False, "prewarm_scan": True},
    ...
}

def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并：override 里有就用 override，没有就保留 base。

    这样"加了一个新配置项"对老用户是**透明**的 —— 他不用改配置文件，
    软件会用默认值，而他改过的项一个都不会丢。
    """
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

**问题 2：API Key 不能和普通配置混在一起。**
因为配置文件用户会分享、会截图、会发给别人排错。所以密钥单独存：

```python
# 读取顺序：环境变量 > secrets.json > config.json
def get_secret(self, key: str, default: str = "") -> str:
    env_name = _ENV_NAMES.get(key)
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]          # 1. 环境变量（CI/临时用）
    secrets = self._load_secrets()
    if secrets.get(key):
        return str(secrets[key])             # 2. data/else data/secrets.json
    return str(self._data.get(key, default) or default)   # 3. 配置文件（兼容旧版）
```

**问题 3：配置写坏了不能让软件起不来。**
解决：读配置失败时用默认值并记日志，同时**把坏文件改名备份**
（不是删掉），让用户能自己看。

### 4.7 事件总线：让"改了数据"通知到"该刷新的人"

一个现实问题：用户在书目页生成了 AI 总结，
**首页的日程栏/统计**要不要跟着变？**资料概览面板**要不要更新？

朴素做法是在每个改数据的地方，手动调用所有需要刷新的地方：

```python
# ❌ 改一处数据要记得通知五个人，早晚漏
def generate_summary(self):
    ...
    self.refresh()
    self.home_view.refresh()
    self.subject_view.refresh()
    self._refresh_side_panel()
```

这个项目用了一个**极简事件总线**（`gwp/core/eventbus.py`，几十行）：

```python
class EventBus:
    def subscribe(self, event: str, handler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event: str, **payload) -> None:
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(**payload)
            except Exception:
                # 一个监听者出错不能影响其他监听者，更不能影响"改数据"本身
                log.exception("事件处理失败：%s", event)

bus = EventBus()
```

发布方只管发：

```python
bus.emit(BOOK_CONTENT_CHANGED, subject=self.subject_name, book=self.book_name)
```

订阅方各管各的：

```python
# home_view 里
bus.subscribe(BOOK_CONTENT_CHANGED, lambda **_: self.refresh_schedule())
```

**收益**：加一个新的"需要刷新的东西"时，
**不用改任何已有的发布方**——只在订阅方写一行。

> **什么时候该用事件总线？**
> 当"一个动作要触发多个不相干的反应"时。
> 反过来，如果只是 A 调用 B，就直接调用——**不要为了解耦而解耦**，
> 事件总线最大的缺点是"代码跳转不好追"。

### 4.8 自己动手

1. 给你自己的项目画一棵**按职责分层**的目录树，写一句话说明每层职责。
2. 找出你代码里"判断运行环境"的地方（是不是打包、是不是测试），
   把它们收敛到**一个函数**。
3. 检查你的路径处理：**用户第一次设置一个新目录时会不会被"吃掉"？**
4. 找一处"改一个东西要手动通知好几处"的代码，用事件总线（或观察者）重写它。

---

## 第 5 章　数据层：不用数据库怎么保证不丢数据

> **这是全书最重要的一章。**
>
> 软件的烂，八成烂在数据层：状态对不上、改了没保存、并发写坏文件、
> 用户数据被覆盖。界面丑只是体验问题，数据丢是信任问题。
>
> 这一章讲的就是"没有数据库兜底时，要自己补上哪些东西"。

### 5.1 先明确：我们用文件系统换来了什么、失去了什么

回顾 1.4 的决策：数据就是文件夹和文件。换来的是"用户能看懂、
能直接拷走、能用记事本改"。**失去的是数据库免费提供的东西**：

| 数据库免费给你 | 文件系统不给你 | 本书的补法 |
| --- | --- | --- |
| 事务（要么全成、要么全不成） | 写到一半断电就坏了 | 5.3 原子写 |
| 并发控制 | 两个进程同时写会互相覆盖 | 5.4 单实例 + 生成号 |
| 缓存一致性 | 改了文件内存里还是旧的 | 5.4 生成号 |
| 类型约束 | 字段写错没人管 | 5.2 兜底读取 |
| 查询 | 找数据要自己遍历 | 5.5 扫描 + 缓存 |

**这一章的每一节，都是在给一个数据库特性写"穷人替代版"。**

### 5.2 元数据：小 JSON 文件，但读取必须"永不崩"

每个科目一个 `subject.json`，每本书一个 `book.json`，
每个作业一个 `homework.json`。看读取函数（`gwp/data_manager/metadata.py`）：

```python
def read_json(path: Path, default: Any) -> Any:
    """读 JSON。**任何异常都返回 default**，并记日志。

    为什么不抛异常：这些文件用户会手工编辑（这是我们的设计卖点），
    编辑出错是常态。一个逗号写错就让整个科目在界面上消失，
    对用户来说是"软件坏了 + 数据丢了"的双重打击。
    """
    if not path.is_file():
        return copy.deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        log.warning("元数据读取失败，使用默认值：%s", path, exc_info=True)
        return copy.deepcopy(default)
    if not isinstance(data, dict):
        log.warning("元数据格式不对（不是对象），使用默认值：%s", path)
        return copy.deepcopy(default)
    return data
```

**三个关键决定**：

1. **返回 `deepcopy(default)`** —— 不是 `default` 本身。
   否则调用方一改返回值，就把"默认值模板"改污染了，
   下一个读不到文件的科目会莫名其妙继承上一个的值。
   （这个 bug 我确实写过。）
2. **只记日志、不弹窗** —— 元数据读不到不影响使用（有默认值兜底），
   弹窗只会烦人。真正需要用户知道的事（比如数据目录不可写）才弹。
3. **校验类型** —— `isinstance(data, dict)`。
   如果有人把 JSON 写成了数组，后面 `.get()` 就会 `AttributeError`，
   在深层代码里炸开，比在这里挡住难查得多。

> **数据层的黄金法则**：
> **对外部输入（用户编辑的文件、网络数据、第三方格式）永远不信任。**
> 每一个 `load` 函数都要能回答："如果这个文件是垃圾，会怎样？"
> 答案必须是"用默认值继续跑"，而不是"崩"。

### 5.3 原子写：不许出现"写了一半"的文件

`json.dump` 直接写目标文件有一个致命窗口：**写到一半断电/崩溃，
文件就废了**，连旧数据都一起丢。

正确做法是**临时文件 + 原子替换**：

```python
def write_json(path: Path, data: Any) -> None:
    """原子写 JSON。

    先写 <name>.json.tmp，成功后 os.replace 覆盖正式文件。
    Windows 上 os.replace 是**原子**的：要么看到旧文件，要么看到新文件，
    永远不会看到"半个文件"。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)          # 原子替换
```

**为什么 `ensure_ascii=False`？**
默认 `True` 会把中文写成 `\u5b66\u79d1`。用户打开文件看到一片转义码，
"能看懂、能手工改"这个卖点就没了。

**同样的技巧用在作业元数据和日程上**：

```python
# gwp/data_manager/homework.py
def save(homework: Homework) -> Path:
    target = meta_path(homework.path)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(homework.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(target)            # Path.replace → os.replace
    return target
```

> **这个技巧的适用范围远不止 JSON**：
> 任何"覆盖写一个文件"的场景（配置、缓存、导出结果）都该这么做。
> 成本是几行代码，收益是"再也不会因为断电丢掉全部数据"。

### 5.4 缓存与失效：一个生成号解决一类 bug

数据层为了性能要缓存（扫描整棵目录树不便宜），
但缓存最大的问题是**什么时候该失效**。看这个项目踩过的坑：

```python
# ❌ 早期写法：每个"写方法"自己去清缓存
def create_subject(self, name, ...):
    ...
    self._subjects = None        # 清自己的
def create_book(self, subject_name, book_name, ...):
    ...
    self._subjects = None        # 又要记得清
def move_subjects(self, box_id, names):
    ...
    self._subjects = None        # 忘了就出 bug
```

问题很明显：**写方法有十几个，漏一个就是"数据改了但界面没变"的幽灵 bug**。

改成**全局生成号**（`gwp/data_manager/boxes.py` 里的做法）：

```python
#: 全局写计数器。任何写操作都 +1；缓存记下自己是用哪一代做的，
#: 对不上就重新读。
_WRITE_GENERATION = 0

def _bump_generation() -> None:
    global _WRITE_GENERATION
    _WRITE_GENERATION += 1

class BoxStore:
    def __init__(self, subjects_dir: Path) -> None:
        self._boxes: list[Box] | None = None
        self._generation = -1

    def load(self, refresh: bool = False) -> list[Box]:
        # 缓存还有效的条件：有缓存 + 没强制刷新 + 生成号没变
        if (self._boxes is not None and not refresh
                and self._generation == _WRITE_GENERATION):
            return [self._copy(box) for box in self._boxes]
        ...读文件...
        self._boxes = boxes
        self._generation = _WRITE_GENERATION     # 记下"我是第几代"
        return [self._copy(box) for box in boxes]

    def _save(self, boxes: list[Box]) -> None:
        ...写文件...
        _bump_generation()                       # 全局作废所有缓存
```

**为什么这个设计好？**

* 新增写方法时**只要它调 `_save`**，失效自动生效，不可能忘；
* 缓存逻辑只在**一个地方**（`load`）；
* 一个类的缓存失效能影响另一个类（比如箱子变了，科目视图也该重扫）——
  因为生成号是**全局**的。

**还有一个容易忽略的点：`load()` 返回深拷贝。**

```python
@staticmethod
def _copy(box: Box) -> Box:
    """复制一个 Box（含 members 列表），用于隔离缓存与调用方。"""
    return Box(id=box.id, name=box.name, color=box.color,
               cover=box.cover, order=box.order, members=list(box.members))
```

如果返回共享对象，调用方一改（比如往 `members` 里 append），
缓存就被改坏了。症状是"文件里没有的箱子、内存里还在"。
**凡是"缓存 + 返回给外部"的地方，都要问一句：外面会不会改它？**

### 5.5 扫描与缓存：启动不能慢

首次启动要扫整棵 `subjects/` 树（每个科目每个书目的每个文件），
几百个文件还好，几千个就要几秒。所以加了**基于修改时间的扫描缓存**
（`gwp/data_manager/cache.py`）：

```python
class ScanCache:
    """记录每个目录的 mtime。mtime 没变就跳过重新扫描。

    存成 else data/cache/scan_cache.json。
    """
    def is_fresh(self, path: Path) -> bool:
        key = str(path)
        recorded = self._data.get(key)
        if recorded is None:
            return False
        try:
            current = path.stat().st_mtime
        except OSError:
            return False
        return abs(current - float(recorded)) < 1e-6
```

**加上两个优化**：

* **后台预扫描**：启动时开一个线程慢慢扫，用户看到界面时数据已经就绪
  （`startup.prewarm_scan` 配置项）；
* **只统计数量、不读内容**：扫描时 `sum(1 for p in folder.rglob("*") if p.is_file())`
  比读文件小得多。

### 5.6 删除：默认进回收站，而不是永久删

这是**用户体验上最重要的一个决定**。用户误删一个科目 =
丢失几个月整理的资料。所以：

```python
# gwp/data_manager/store.py
def _delete_dir(self, path: Path, to_recycle: bool) -> bool:
    """删除目录。优先送回收站，回收站不可用才真删。"""
    if to_recycle and shell_ops.can_use_recycle_bin():
        return shell_ops.send_to_recycle_bin(path)      # 可恢复
    shutil.rmtree(path, ignore_errors=True)             # 永久删除
    return True
```

送回收站用的是 Windows API（`gwp/services/shell_ops.py`）：

```python
def send_to_recycle_bin(path: Path) -> bool:
    """用 SHFileOperationW + FOF_ALLOWUNDO 把文件送进回收站。

    这是 Windows 上唯一"正确"的删法 —— 直接 shutil.rmtree 是永久删除，
    用户没有任何后悔的机会。
    """
    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", ctypes.c_uint),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_uint), ...]

    flags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    ...
    result = shell32.SHFileOperationW(ctypes.byref(operation))
    return result == 0
```

**配套的三件事**（缺一不可）：

1. **删除前确认**，而且确认框要"两段式"：普通提示 + 有内容时再确认一次；
2. **确认框的默认按钮是"取消"**（回车不会误删）；
3. **文案要诚实**：如果回收站不可用、真的会永久删除，
   必须**明确写"将永久丢失、无法还原"**，不能让用户以为还能找回。

```python
# gwp/ui/common.py
def confirm(parent, text, title="请确认", *, dangerous=False, detail=""):
    """确认对话框。

    dangerous=True 时：
    * 用警告图标；
    * 按钮是「取消」+「删除」，**默认焦点在取消**；
    * Esc 也是取消。
    """
```

> **这类细节决定用户敢不敢用你的软件。**
> 一个会"一不小心删掉全部资料"的软件，功能再多也没人敢用。

### 5.7 一个真实的数据事故，以及它教了什么

开发过程中发生过一次：**三个科目（英语、高等代数、数学分析）被删除**。
用户很紧张，怀疑是测试脚本误删。

**处理过程**（这部分比结论更有价值）：

1. **不猜，先查证据。** 软件的日志里记录了每一次删除操作，
   时间戳是 `13:23:50 / 13:23:53 / 13:23:56`——**间隔几秒**，
   这是人在界面上连续操作的节奏，不是脚本（脚本会连续执行）。
2. **核对回收站**，确认稍后被清空。
3. **查损失**：总大小约 510 字节，因为没有实质内容。
4. **如实报告**：确认是通过界面手动删除的，且**没有备份可恢复**。

**这件事带来的三条改进**：

1. **删除确认升级为"两段式 + 默认取消"**（5.6）；
2. **删书目也加同样的保护**，并显示"这本书里有多少文件"；
3. **打开了一个后续待办**：应用级删除安全网
   （`data/else data/deleted/<日期>-<名称>/` + 「恢复已删除」菜单）。

> **教学点**：
> * **日志是"事后查案"的唯一证据**，所以关键操作必须记日志；
> * 出错时**先找证据再改代码**，否则你改的可能是无关的地方；
> * 面对丢数据，**如实说"找不到备份"** 比找借口有用得多；
> * **任何"删除"功能都要假设用户会误触**。

### 5.8 自己动手

1. 检查你的项目：**所有"覆盖写文件"的地方都是原子的吗？**
   把所有 `open(path, "w")` 找出来，改成"临时文件 + replace"。
2. 你的数据读取函数，**输入一个垃圾文件会怎样？** 写个测试验证。
3. 你的缓存有"失效"机制吗？**列出所有会让缓存变旧的时机**，
   检查是否都覆盖了。
4. 你的删除操作**能后悔吗？** 如果不能，想想怎么加一层保护
   （回收站、备份目录、确认框默认取消）。

---

# 第二部分　界面层：把数据变成能用的东西

> 这一部分是篇幅最大的，因为**桌面软件的工作量八成在界面**。
>
> 但请注意：**界面代码多，不代表界面逻辑该复杂**。
> 好的界面层是"薄"的——它只负责"把数据画出来"和"把用户操作翻译成数据操作"，
> 真正的逻辑都在下面几层。

---

## 第 6 章　界面层架构与 Qt 基础

### 6.1 界面层的职责边界

先把纪律说清楚。界面层（`ui/`）**只做三件事**：

1. **把数据画出来**（读 `library`，生成控件）；
2. **把用户操作翻译成数据操作**（双击 → `library.create_book(...)`）；
3. **展示结果与错误**（弹窗、状态栏、日志）。

**界面层不做的事**：

* ❌ 不自己拼路径（用 `paths`）；
* ❌ 不自己读写文件（用 `library` / `file_ops`）；
* ❌ 不自己拼 AI 提示词（用 `summarizer`）；
* ❌ 不自己判断"这个科目是什么类型才能干什么"（用声明表）。

判断标准很简单：**如果换一套界面（比如网页版），`ui/` 之外的东西能不能原样复用？**
能，说明边界划对了。

### 6.2 视图基类：消灭重复的标题栏

这个软件有四个主要页面：首页、科目页、书目页、文档页。
它们都有"**标题 + 右边一排操作按钮**"这个结构。
如果每个页面自己搭一遍，会有四个几乎一样的 `__init__`。

所以抽了一个基类（`gwp/ui/views/base_view.py`）：

```python
class BaseView(QWidget):
    """所有页面视图的公共骨架。"""

    status_message = pyqtSignal(str)      # 想往状态栏说句话
    data_changed = pyqtSignal()           # 数据变了

    def __init__(self, context: AppContext, parent=None):
        super().__init__(parent)
        self.context = context
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 16, 18, 14)
        self._root.setSpacing(12)

        # ---- 标题栏：标题 + 副标题 + 搜索 + 操作按钮 ----
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.lbl_title = QLabel(""); self.lbl_title.setObjectName("Title")
        ...
        self.actions = QHBoxLayout()      # 操作按钮区
        self.header.addLayout(self.actions)

        self.header_bar = QWidget()
        self.header_bar.setObjectName("HeaderBar")
        self.header_bar.setLayout(self.header)
        self._root.addWidget(self.header_bar)

        # ---- 内容区：子类往这里塞东西 ----
        self.body = QVBoxLayout()
        self._root.addLayout(self.body, 1)
```

子类只需要：

```python
class HomeView(BaseView):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)          # 拿到底座
        self.add_action("＋ 新建科目", self.create_subject)
        self.body.addWidget(self.grid)             # 往内容区塞东西
```

**收益**：改一次标题栏样式（比如加个背景），四个页面一起变。

> **判断"该不该抽基类"的标准**：
> 有三处以上**结构相同、只有内容不同**的代码，就该抽。
> 只有两处？先别抽——**过早抽象比重复更贵**。

### 6.3 信号与槽：Qt 的"回调"机制

Qt 用"信号（signal）—槽（slot）"代替回调函数。好处是**发送方不需要知道接收方是谁**。

这个项目里的用法：

```python
# 子控件声明信号（BookView 里）
class BookView(BaseView):
    open_document = pyqtSignal(Path)     # 我要打开一个文档，谁想接谁接
    back_requested = pyqtSignal()        # 用户点了返回

    def _on_item_double_clicked(self, item):
        if item.is_dir:
            self.enter_folder(item.path)         # 自己处理
        else:
            self.open_document.emit(item.path)   # 喊一声，不关心谁接
```

主窗口接上：

```python
# MainWindow
self.book_view.open_document.connect(self.open_document)
self.book_view.back_requested.connect(self.show_subject)
```

**为什么这样好？** `BookView` 完全不知道"文档要开在哪儿"（内嵌还是新窗口）。
后来需求变成"JSON 用 VSCode 打开"，只改了 `MainWindow.open_document`，
**`BookView` 一行没动**。

> **一个实战建议**：信号名要**描述事实**，不要描述动作接收方。
> `open_document` ✅ 好；`tell_main_window_to_open` ❌ 差。

### 6.4 布局：为什么按钮会被压扁（一个真实 bug）

这个 bug 值得专门讲，因为**很多人都遇到过但不知道为什么**。

**现象**：用户截图显示标题栏按钮文字被截断成「返回」「导入文」「版本管理…」。

**排查过程**（这个思路可以复用）：

1. **先量，不猜。** 写个脚本把每个按钮的"需要宽度"和"实际宽度"打出来：

```python
for button in view.findChildren(QPushButton):
    need = button.fontMetrics().horizontalAdvance(button.text()) + 22
    print(button.text(), button.width(), need, "OK" if button.width() >= need else "截断")
```

2. **结论**：按钮总共需要 **881px**，而窄窗口只给得起 873px。差一点点。

3. **根因**：Qt 的 `QHBoxLayout` 在空间不够时会**按各控件的"可压缩性"分配**。
   默认情况下按钮和标签**都能被压缩**，所以按钮被压扁了。

**修法三步**（`gwp/ui/views/base_view.py`）：

```python
# 第一步：按钮宽度按内容锁定，不可压缩
def add_action(self, text, callback, accent=False, tooltip="", checkable=False):
    button = QPushButton(text)
    ...
    self.actions.addWidget(button)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

def lock_action_widths(self) -> None:
    """把每个按钮的最小宽度锁定为"完整显示文字所需宽度"。

    必须在样式表生效之后调用（字体、内边距都会影响所需宽度）。
    """
    for index in range(self.actions.count()):
        widget = self.actions.itemAt(index).widget()
        if not isinstance(widget, QPushButton):
            continue
        hint = widget.sizeHint().width()
        widget.setMinimumWidth(hint)
        widget.setMaximumWidth(hint)
```

```python
# 第二步：让"标题"成为唯一可压缩的东西
self.lbl_title.setSizePolicy(QSizePolicy.Policy.Ignored,
                             QSizePolicy.Policy.Preferred)
self.lbl_title.setToolTip("")     # 截断时用悬浮提示补全

def set_title(self, title, subtitle="", breadcrumb=""):
    self.lbl_title.setText(title)
    self.lbl_title.setToolTip(title)      # ← 被省略也能看到全名
    ...

# 第三步：副标题/面包屑是"补充信息"，放不下就整个消失
for label in (self.lbl_subtitle, self.lbl_breadcrumb):
    has_text = bool(label.text())
    label.setVisible(has_text)
    label.setSizePolicy(
        QSizePolicy.Policy.Ignored if has_text else QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Preferred,
    )
```

**结果**：窗口变窄时标题先被省略（悬浮能看到全名），按钮永远完整。

**再加一层保险**：把按钮文案压到最省，完整含义放悬浮提示：

| 原 | 现 | 省下 |
| --- | --- | --- |
| `← 返回科目` | `← 返回` | 26px |
| `版本管理…` | `版本管理` | 13px |
| `导出 PDF…` | `导出 PDF` | 13px |
| `打开文件夹` | `打开目录` | 13px |

**总需求从 881px 降到 813px。**

> **这个 bug 的通用教训**：
> 1. **"文字被截断"几乎总是布局压缩问题**，不是字体问题；
> 2. **量数据比看现象有用**——`fontMetrics().horizontalAdvance()` 是精确的；
> 3. **设计上要明确"谁可以让位"**：主信息（按钮文字）不能让，
>    次要信息（标题、副标题）可以让，而且让的方式要体面（省略号 + 悬浮补全）。

**配套的自动化测试**（第 21 章会细讲）：

```python
def _clipped_buttons(view) -> list[tuple[str, int, int]]:
    out = []
    for button in view.findChildren(QPushButton):
        if not button.isVisible():
            continue
        need = button.fontMetrics().horizontalAdvance(button.text()) + 22
        if button.width() < need:
            out.append((button.text(), button.width(), need))
    return out

for width in (960, 1014, 1280):
    window.resize(width, 700)
    app.processEvents()
    check(f"{width}px 窗口下按钮文字完整", not _clipped_buttons(window.book_view))
```

**这个断言以后再也不会让按钮被压扁**——不管以后加多少按钮、改多大字号。

### 6.5 主窗口：把各块拼起来

`MainWindow` 的职责是**布局 + 路由**，不含业务逻辑：

```python
class MainWindow(QMainWindow):
    def __init__(self, context: AppContext):
        ...
        # 1) 用 QStackedWidget 做"页面切换"（首页 / 科目 / 书目 / 文档）
        self.stack = QStackedWidget()
        self.home_view = HomeView(context)
        self.subject_view = SubjectView(context)
        self.book_view = BookView(context)
        for view in (self.home_view, self.subject_view, self.book_view):
            view.status_message.connect(self.show_status)
            self.stack.addWidget(view)
        self.setCentralWidget(self._wrap(self.stack))

        # 2) 页面之间的跳转在这里接线
        self.home_view.subject_opened.connect(self.show_subject)
        self.subject_view.book_opened.connect(self.open_book)
        self.book_view.back_requested.connect(self.show_subject)

        self._build_menus()
```

**注意 `QStackedWidget` 的用法**：所有页面**一次性创建好**，切换只是换显示的那个。
好处是切页面几乎瞬间（不用重建控件），代价是启动稍慢、内存多占一点。
对这个规模的软件，体验收益更大。

### 6.6 样式：用 QSS 而不是硬编码颜色

Qt 支持类似 CSS 的 **QSS**。项目把样式集中在
`gwp/services/themes.py`，支持浅色/深色两套：

```python
def app_qss(theme: str, accent: str, font_family: str, font_size: int) -> str:
    colors = THEMES[theme]
    return f"""
QWidget {{ font-family: "{font_family}"; font-size: {font_size}pt;
           color: {colors['text']}; }}
QLabel#Title {{ font-size: 1.35em; font-weight: 600; }}
QLabel#Muted {{ color: {colors['text_muted']}; }}
QLabel#EmptyHint {{ color: {colors['text_muted']}; font-size: 1.05em; }}
QFrame#Panel {{ background: {colors['surface']};
                border: 1px solid {colors['border']}; border-radius: 12px; }}
QFrame#AgendaRow[entryState="overdue"] {{ border-left-color: #B3261E; }}
QFrame#AgendaRow[entryState="soon"] {{ border-left-color: #E0A100; }}
"""
```

**两个关键技巧**：

1. **用 `objectName` 做选择器**（`QLabel#Title`）——
   不需要给每个控件设 class，`setObjectName("Title")` 就能套上样式；
2. **用属性选择器表达状态**（`QFrame#AgendaRow[entryState="overdue"]`）——
   状态由代码设 `setProperty("entryState", "overdue")`，
   样式在 QSS 里定义。**逻辑与样式分离。**

**深色主题的一个坑**：有些控件需要"重新套一遍样式"才会生效：

```python
self.content_area.setProperty("floating", margin > 0)
self.content_area.style().unpolish(self.content_area)   # ← 必须先 unpolish
self.content_area.style().polish(self.content_area)     # ← 再 polish
```

> **记不住就记这一条**：Qt 里"改了 QSS 选择器依赖的属性"，一定要
> `unpolish` + `polish`。否则要重启才生效。

### 6.7 自己动手

1. 给你的界面找一处"三个页面长得差不多"的结构，抽成基类。
2. 找一个你自己的"文字被截断/被压扁"的问题，用
   `fontMetrics().horizontalAdvance()` 量一量，然后按 6.4 的三步修。
3. 把散落在代码里的颜色值收进一个 `themes.py`，并做一套深色版。
4. 用信号把一个"子控件直接调主窗口"的地方改成解耦写法。

---

## 第 7 章　自定义控件：卡片、拖拽与网格

### 7.1 为什么需要自定义控件

Qt 自带的控件能覆盖 90% 的需求，剩下 10% 要自己画。
这个项目的首页卡片就是那 10%：需求说"**彩色长方体卡片**"，
标准 `QPushButton` 做不出渐变、圆角、封面图和阴影。

自定义控件的套路（`gwp/ui/widgets/cards.py`）：

```python
class InfoCard(QFrame):
    """卡片基类：渐变背景 + 圆角 + 可选封面图 + 标题/副标题 + 徽标。"""

    clicked = pyqtSignal(object)
    card_dropped = pyqtSignal(str, str, object)   # mime, payload, self

    def __init__(self, parent=None, *, width=190, height=118, radius=14):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._radius = radius
        self._hover = False
        self._dragged = False
        ...

    # -- 绘制：全部在 paintEvent 里自己画 --
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)   # 抗锯齿

        # 1) 渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(self._color_top))
        gradient.setColorAt(1.0, QColor(self._color_bottom))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)

        # 2) 封面图（有就画，按比例裁切填满）
        if self._cover is not None and not self._cover.isNull():
            painter.setClipPath(self._rounded_path())
            painter.drawPixmap(self.rect(), self._cover)

        # 3) 文字
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(...)
```

**要点**：

* **`setFixedSize`**：卡片尺寸固定，因为网格布局要靠它算行列；
* **`Antialiasing`** 必须开，否则圆角会有锯齿；
* **`setClipPath` + 圆角路径** 让封面图也是圆角的（不然图片四个直角会露出来）。

### 7.2 拖拽：三件事必须都对

Qt 拖拽是最容易"看起来对、实际上不工作"的功能。要三件事**同时对**：

**① 发起方**：按下记录起点，移动超过阈值才启动拖拽。

```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_origin = event.position().toPoint()
        self._dragged = False
        # ⚠️ 注意：这里**不发出 clicked**！否则单击就触发"打开"
    super().mousePressEvent(event)

def mouseMoveEvent(self, event):
    if not (event.buttons() & Qt.MouseButton.LeftButton):
        return
    if self._drag_origin is None:
        return
    distance = (event.position().toPoint() - self._drag_origin).manhattanLength()
    if distance < QApplication.startDragDistance():
        return                        # 还没到阈值，不算拖拽
    self._dragged = True
    drag = QDrag(self)
    mime = QMimeData()
    mime.setData(SUBJECT_MIME, self._payload.encode("utf-8"))
    drag.setMimeData(mime)
    drag.exec(Qt.DropAction.MoveAction)

def mouseReleaseEvent(self, event):
    super().mouseReleaseEvent(event)
    if not self._dragged:
        self.clicked.emit(self)       # 只有"没拖动"才算点击
    self._dragged = False
    self._drag_origin = None
```

> **这个 `_dragged` 标志是关键。** 我第一版在 `mousePressEvent` 里就
> `emit(clicked)`，结果**一按卡片就展开**，根本没法拖。
> 因为"按下"和"点击"不是一回事——**按下后可能拖走**。

**② 接收方**：声明接受哪种 MIME，并画出落点提示。

```python
SUBJECT_MIME = "application/x-gwp-subject"
BOX_MIME = "application/x-gwp-box"

class InfoCard(QFrame):
    def dragEnterEvent(self, event):
        if self._accepts_drag(event.mimeData()):
            event.acceptProposedAction()
            self._drop_active = True          # 高亮自己
            self.update()

    def dragMoveEvent(self, event):
        if not self._accepts_drag(event.mimeData()):
            return
        # 落点在左半边还是右半边 —— 决定"插到前面还是后面"
        self._drop_before = event.position().x() < self.width() / 2
        event.acceptProposedAction()
        self.update()                          # 重画落点指示条

    def dropEvent(self, event):
        self._drop_active = False
        event.acceptProposedAction()
        mime = event.mimeData()
        if mime.hasFormat(SUBJECT_MIME):
            payload = bytes(mime.data(SUBJECT_MIME)).decode("utf-8")
            self.card_dropped.emit(SUBJECT_MIME, payload, self)

    def paint_drop_indicator(self, painter):
        """在左/右边缘画一条黄色竖条，告诉用户会插到哪。"""
        if not self._drop_active:
            return
        width = 4
        x = 0 if self._drop_before else self.width() - width
        painter.setBrush(QColor("#FFB020"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(x, 0, width, self.height())
```

**③ 数据结构**：payload 用什么表示"被拖的东西"。

```python
mime.setData(SUBJECT_MIME, self._payload.encode("utf-8"))
# _payload 是科目名（字符串）
```

> **MIME 的 MIME 类型要自定义**（`application/x-gwp-subject`），
> **不要用 `text/plain`** —— 否则从记事本拖一段文字过来也会被当成科目。

### 7.3 网格：自动换行的卡片排列

卡片要"一行放不下就换行"。Qt 有 `QGridLayout`，但**列数必须自己算**
（取决于窗口宽度和卡片宽度）。

这个项目写了个 `CardGrid`：

```python
class CardGrid(QWidget):
    card_opened = pyqtSignal(object)
    card_activated = pyqtSignal(object)
    card_context = pyqtSignal(object, QPoint)

    def set_cards(self, cards: list[QWidget]) -> None:
        self._cards = cards
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()                  # 窗口变宽变窄都重排

    def _relayout(self):
        if not self._cards:
            return
        card_width = self._cards[0].width()
        spacing = 14
        available = max(1, self.width() - 2 * self.MARGIN)
        # 一行能放几个
        columns = max(1, (available + spacing) // (card_width + spacing))
        ...
        for index, card in enumerate(self._cards):
            row, column = divmod(index, columns)
            self._layout.addWidget(card, row, column)
```

**要点**：`resizeEvent` 里重排。Qt 的布局不会因为你"觉得"该换行就换行，
**列数必须自己算**。

### 7.4 一个特殊的信号路由 bug（值得警惕）

这个 bug 让两个功能同时"点不动"，很典型。

**现象**：右键科目卡片没反应；从科目页打开书目也没反应。

**代码**（错误版本）：

```python
# CardGrid
def _on_clicked(self, card):
    self.card_opened.emit(self._card_model(card))      # ← 发的是"模型"
```

```python
# 接收方
def _on_card_opened(self, card):
    if isinstance(card, BoxCard):        # ← 但这里期待"卡片控件"
        self.enter_box(card.box.id)
```

`_card_model(card)` 返回的是数据模型（`Subject`），
而接收方判断的是控件类型（`BoxCard`），**类型不匹配 → 静默什么都不做**。

**为什么难查？** 因为**没有报错**。信号发出去了，槽也执行了，
只是 `isinstance` 判断失败，一声不响地返回。

**修法**：**信号参数只发一种东西**，并且全项目统一。

```python
# 统一都发"卡片控件"，接收方自己从卡片上取它需要的东西
self.card_opened.emit(card)

def _on_card_opened(self, card):
    if isinstance(card, BoxCard):
        self.enter_box(card.box.id)
    elif isinstance(card, SubjectCard):
        self.subject_opened.emit(card.subject.name)
```

同时把 `_card_model` 这个函数**删掉**——留着就会有人再用错。

> **教训**：
> 1. **Qt 信号是弱类型的**，参数类型错了不报错，只是"没反应"；
> 2. **"点了没反应"的第一嫌疑是信号参数类型不匹配**，
>    而不是"信号没连上"；
> 3. **删掉容易用错的辅助函数**，比写注释说"别用它"有效。

**另一个同类 bug**：单击展开收纳箱也"没反应"。
排查发现 `grid.card_activated` 信号**压根没有接收方**——
发出去没人接。这类"漏接"用一条命令就能查：

```powershell
Select-String -Path "gwp\ui\**\*.py" -Pattern "card_activated"
# 如果只有 declare 和 emit，没有 connect，就是漏接
```

### 7.5 自己动手

1. 写一个自定义控件：圆角矩形 + 渐变 + 一行文字（用 `paintEvent`）。
2. 给它加拖拽：能拖动自己、能被同类接收、落点有视觉提示。
3. 写一个"自动换行的卡片网格"，窗口拉伸时重排。
4. 检查你自己的信号：**有没有"发了没人接"或"参数类型不匹配"的？**
   用上面的 `Select-String` 思路查一遍。

---

## 第 8 章　首页：卡片、收纳箱与拖拽排序

### 8.1 首页要展示什么

首页是最复杂的一个视图，因为它要同时处理：

* **科目卡片**（一个文件夹一个）
* **收纳箱卡片**（把若干科目收在一起）
* **两者的混排顺序**（箱子可以和科目交错排列）
* **拖拽排序**（把卡片拖到别的位置）
* **拖进箱子**（把科目拖到箱子上）
* **搜索过滤**

**这一章的核心是"混排顺序"**——它是这个项目里最难的一段逻辑，
也是最有教学价值的一段。

### 8.2 卡片从哪里来

```python
def refresh(self) -> None:
    library = self.context.library
    keyword = self.search.text().strip().lower()

    # 如果在箱子里，但箱子被删了，自动回最外层
    if (self.current_box_id is not None
            and library.boxes.get(self.current_box_id) is None):
        self.current_box_id = None

    width = int(self.context.config.get("ui.card.width", 196))
    height = int(self.context.config.get("ui.card.height", 124))
    radius = int(self.context.config.get("ui.card.radius", 14))

    if self.current_box_id is not None:
        cards, shown = self._build_box_cards(keyword, width, height, radius)
    else:
        cards, shown = self._build_top_level_cards(keyword, width, height, radius)

    self.grid.set_cards(cards)
    self._update_header(shown, keyword)
    self.refresh_schedule()
```

**注意第一件事**：检查"当前所在的箱子是否还存在"。
因为用户可能在资源管理器里改了 `boxes.json`，
或者撤消了一个操作。**任何"当前状态"都要在使用前校验。**

### 8.3 混排顺序：问题的本质

先明确数据长什么样（`data/boxes.json`）：

```json
{
  "version": 1,
  "boxes": [
    {"id": "b1", "name": "次要科目", "order": 0, "members": ["习概", "英语"]}
  ]
}
```

科目自己的顺序在 `subject.json` 的 `order` 字段。
**箱子有自己的 `order`，科目也有自己的 `order`**——问题就出在这里。

**第一版的做法**：箱子按箱子的 `order` 排，科目按科目的 `order` 排，
然后把"箱子"和"科目"两个列表**首尾拼接**。

结果：**箱子和科目无法交错**。用户想把箱子放到"高等代数"和"数学分析"中间
——做不到，因为两个列表各自独立。

**正确的做法**：**箱子和"未收纳的科目"共用一套 order 编号**。

```python
def home_sequence(self, refresh: bool = True) -> list[tuple[str, str]]:
    """首页最外层的当前混排序列 [(kind, key)]（按 order 排好）。

    只包含**真正的顶层项**：所有收纳箱 + **未收纳**的科目。
    在箱子里的科目不属于顶层（它们显示在箱内），如果算进来，
    拖拽时会按错误的相对位置计算，箱子就会移错地方。
    """
    items: list[tuple[int, int, tuple[str, str]]] = []
    counter = 0
    for box, _members in self.boxes_with_members(refresh=refresh):
        items.append((int(box.order or 0), counter, ("box", box.id)))
        counter += 1
    for subject in self.unboxed_subjects(refresh=refresh):
        items.append((int(subject.order or 0), counter, ("subject", subject.name)))
        counter += 1
    items.sort(key=lambda item: (item[0], item[1]))   # order 相同则按扫描顺序
    return [item[2] for item in items]
```

**关键点**：`counter` 是"稳定排序的第二关键字"。
如果两个项 `order` 相同（老数据很常见，都是 0），
就按扫描顺序排，**保证每次刷新顺序一致**（否则界面会闪）。

### 8.4 改顺序：为什么"重编号"会出错

有了混排序列，改顺序就变成"重写所有顶层项的 order"：

```python
def set_home_order(self, items: list[tuple[str, str]]) -> None:
    """按给定顺序重写首页最外层的混排顺序。

    这是首页顺序的**唯一权威**：箱子和科目共用一套 0..N-1 编号，
    因此可以表达任意交错顺序。

    关键点：**两个列表各自单独编号会互相碰撞** —— 箱子编成 0..n-1、
    科目也编成 0..m-1，于是"箱子排到科目前面"根本表达不出来。
    """
    cleaned = [...]                        # 去重、剔除箱内科目、补齐漏掉的
    order_of = {item: index for index, item in enumerate(cleaned)}
    ...
```

**这里踩过一个更隐蔽的坑**：`BoxStore.set_order()` 内部会"把传入的
箱子列表重新编号为 0..n-1"。所以当你只想移动**一个**箱子时：

```python
# 用户把"箱子"拖到最前面
store.set_order([box_id])       # ❌ 只有一个，于是它被编成 0
```

**一个箱子 → 编号 0**，看起来没问题。但如果它原本order是 3（排在科目后面），
这一下就跳到最前面了——**用户只是想在它当前位置微调，结果跳了**。

修法是给 `set_order` 加一个"不要重编号"的模式：

```python
def set_order(self, box_ids, absolute: bool = False, positions=None):
    """重写箱子顺序。

    ``absolute=True`` 时把 ``positions`` 直接当作 order 写入，
    **不**重编号成 0..n-1 —— 首页的箱子/科目混排需要跨两个列表比较 order，
    重编号会把混排信息抹掉。
    """
```

然后首页调用时就传 `absolute=True` + 完整的 `positions`：

```python
self.context.library.boxes.set_order(
    box_ids, absolute=True, positions=positions
)
```

> **这个坑的通用形态**：
> **一个"局部操作"的函数，内部却做了"全局规范化"。**
> 调用方以为只改了一个元素，实际上所有元素都被重排了。
>
> 遇到这类 bug 的信号是："我明明只改了一点点，为什么整个顺序都变了？"

### 8.5 箱内排序：另一个"看起来对但被覆盖"的 bug

用户反馈：**"收纳箱内也要实现用户拖拽排序"**。
实现了，但**拖了没效果**。

排查发现：箱内顺序确实存下来了（`box.members` 的顺序），
但**读出来的时候被重新排过了**：

```python
# ❌ 错误：按"科目的全局 order"排箱内成员
def boxes_with_members(self, refresh=False):
    for box in self.boxes.load(refresh=refresh):
        members = [self.subject(name) for name in box.members]
        members = [m for m in members if m is not None]
        members.sort(key=lambda s: (s.order, s.title.lower()))   # ← 这里！
        result.append((box, members))
```

**为什么错？** 因为 `subject.order` 是**顶层混排的坐标系**，
和"箱子内部的顺序"完全是两码事。按它排，用户在箱内的拖拽结果每次都被覆盖。

修法：**箱内顺序就以 `box.members` 的顺序为准**。

```python
# ✅ 正确：箱内顺序 = box.members 的顺序
def boxes_with_members(self, refresh: bool = False):
    result = []
    for box in self.boxes.load(refresh=refresh):
        members = []
        for name in box.members:          # ← 按存储顺序，不重排
            subject = self.subject(name)
            if subject is not None:
                members.append(subject)
        result.append((box, members))
    return result
```

> **这条经验非常通用**：
> **同一个"顺序"字段，只能在它所属的坐标系里解释。**
> `subject.order` 属于"首页顶层坐标系"，不属于"箱内坐标系"。
> 混用就会互相覆盖。
>
> 排查这类 bug 的方法是问："**这个值是谁写的？谁在读的时候又改了？**"

### 8.6 右键菜单：数据驱动的菜单构建

首页卡片的右键菜单项很多（重命名、换图、颜色、说明、移入/移出收纳箱、
置顶、打开文件夹、删除）。而且菜单项**随状态变化**：

```python
def _subject_menu_entries(self, subject: Subject) -> list:
    entries: list = []

    # 移入/移出收纳箱 —— 根据"当前在不在箱子里"给不同菜单项
    box_of_me = self.context.library.boxes.box_of(subject.name)
    if box_of_me is not None:
        entries.append((
            f"移出收纳箱：{box_of_me.name} → 最外层",
            lambda: self.remove_from_box(subject.name),
        ))
    else:
        submenu = []
        for box in self.context.library.boxes.load():
            submenu.append((box.name, lambda b=box: self.move_into_box(b.id, [subject.name])))
        if not submenu:
            submenu.append(("（还没有收纳箱）", None, False))   # 禁用项
        entries.append(("移入收纳箱 …", submenu))

    entries.extend([
        None,                                             # None = 分隔线
        ("编辑名称/类型…", lambda: self._rename_subject(subject)),
        self._subject_type_entry(subject),
        ("更换卡片图片…", lambda: self._set_cover(subject)),
        ...
        (f"删除科目（{subject.book_count} 本书目）…", lambda: self._delete_subject(subject)),
    ])
    return entries
```

`build_context_menu` 支持三种形式：

```python
("打开", callback)              # 普通项
("（还没有收纳箱）", None, False) # 禁用项
("移入收纳箱 …", submenu_list)   # 子菜单
None                            # 分隔线
```

**为什么要"数据驱动"？** 因为菜单项会**随需求一直加**。
如果写成：

```python
# ❌ 硬编码的菜单构建（加一项要改这段 + 记得连信号）
menu = QMenu(self)
act = menu.addAction("重命名…")
act.triggered.connect(lambda: self._rename_subject(subject))
act2 = menu.addAction("更换图片…")
act2.triggered.connect(lambda: self._set_cover(subject))
...
```

那么"根据状态显示不同项"会变得很难（要写一堆 `if` 和 `setEnabled`）。
数据驱动写法把"菜单长什么样"变成**一个纯函数的返回值**，
**这让它可以被测试**：

```python
def test_menu():
    entries = home._subject_menu_entries(subject)
    titles = [e[0] for e in entries if e is not None]
    check("右键菜单有「修改类型…」", any("修改类型" in t for t in titles))
```

> **可测试性是设计质量的试金石。**
> 一段逻辑如果需要"真的弹出菜单、真的点一下"才能验证，
> 它就已经很难维护了。把"要显示什么"抽成纯数据，
> 测试就变成"检查一个列表"。

### 8.7 自己动手

1. 给一个列表加"拖拽排序"，并想清楚：**顺序存在哪、谁读谁写**。
2. 找出你项目里"两个列表各有各的顺序"的地方，
   问：**它们需要混排吗？** 如果需要，改成共用一套坐标。
3. 把你的右键菜单改成"数据驱动"（一个函数返回菜单项列表），
   然后为它写一个纯数据的测试。

---

## 第 9 章　书目页：标签驱动的多栏目界面

### 9.1 问题：栏目会一直加

书目页是这个软件的核心工作面。它的结构是一个**标签页 + 表格**：

```
AI 总结 | 简介 | 笔记 | 练习 | 易错题 | 教材 | 其它文件 | 全部条目
─────────────────────────────────────────────────────────
名称            类型   大小    修改时间
第二章笔记.md   MD     2.1 KB  2026-10-09 16:16
...
```

需求一路加过来，栏目从 5 个变成了 8 个，而且不同科目类型**栏目不同**：

| 科目类型 | 栏目 |
| --- | --- |
| 自学课 | AI 总结 / 简介 / 笔记 / **练习** / 易错题 / 教材 / 其它文件 / 全部条目 |
| 校修课 | AI 总结 / 简介 / 笔记 / **作业** / 易错题 / 教材 / 其它文件 / 全部条目 |
| 日记 | AI 思想总结 / AI 日记 / 我的日记 / 其它日记 / 全部条目 |

**关键设计问题**：怎么让"加一个栏目"成本最低、让"不同类型的差异"不扩散？

### 9.2 答案：把栏目写成声明表

回到 3.3 的原则——**目录语义不分叉，界面用词才分叉**。
具体做法（`gwp/core/constants.py`）：

```python
#: 每个标签的含义：(key, 标签文案, 目录名)
#: * 自学课：作业 -> 练习（需求：自学课的作业改为练习，功能性质不变）
#: * 日记：没有教材与易错题，改为 AI 总结 / AI 日记 / 我的日记 / 其它日记
BOOK_TABS_SELF_STUDY = (
    ("summary",     "AI 总结",   None),
    ("intro",       "简介",      None),
    ("notebook",    "笔记",      NOTEBOOK_FOLDER),
    ("homework",    "练习",      HOMEWORK_FOLDER),
    ("error-prone", "易错题",    ERROR_FOLDER),
    ("book",        "教材",      BOOK_FOLDER),
    ("others",      "其它文件",  OTHERS_FOLDER),
    ("root",        "全部条目",  None),
)

BOOK_TABS_BY_TYPE = {
    SUBJECT_SELF_STUDY: BOOK_TABS_SELF_STUDY,
    SUBJECT_SCHOOL:     BOOK_TABS_SCHOOL,
    SUBJECT_DIARY:      BOOK_TABS_DIARY,
}
```

**三个字段各自的含义**：

| 字段 | 含义 | 为什么要它 |
| --- | --- | --- |
| `key` | 内部标识 | 表格控件按 key 索引；**不随文案变化** |
| `标签文案` | 界面上显示的 | 以后改文案不影响代码 |
| `目录名` | 对应的真实目录，`None` 表示虚拟栏目 | **驱动"导入文件放哪"** |

**"虚拟栏目"这个概念很重要**：`AI 总结`、`简介`、`全部条目`
不对应任何子目录（它们的内容来自特殊位置或聚合），
所以目录名是 `None`。代码里所有"往当前栏目导文件"的地方
都要处理 `None`：

```python
def _target_folder(self) -> Path | None:
    """当前分类对应的真实目录（用于导入）。"""
    key = self._current_tab_key()
    for tab_key, _title, folder in self._tab_defs:
        if tab_key == key and folder:
            return book.path / folder
    return None                    # 虚拟栏目：没有对应目录
```

### 9.3 表格控件：一个控件，两种模式

`FileTable` 是个 `QTableWidget`，但它有两种形态：

```python
class FileTable(QTableWidget):
    """条目列表：名称 / 类型 / 大小 / 修改时间。

    set_homework_mode(True) 后会追加两列 —— 「DDL」与「提交方式」，
    并按截止情况给整行上色。
    """
    COLUMNS = ("名称", "类型", "大小", "修改时间")
    _DUE_COLUMN_TITLE = "DDL"
    _SUBMIT_COLUMN_TITLE = "提交方式"

    def set_homework_mode(self, enabled: bool) -> None:
        if enabled == self._homework_mode:
            return
        self._homework_mode = enabled
        titles = list(self.COLUMNS)
        if enabled:
            titles += [_DUE_COLUMN_TITLE, _SUBMIT_COLUMN_TITLE]
        self.setColumnCount(len(titles))
        self.setHorizontalHeaderLabels(titles)
        ...
```

**为什么用"模式"而不是两个控件类？** 因为 90% 的行为是一样的
（双击打开、右键菜单、选择、剪贴板）。两个类会带来大量重复。

**但模式也有代价**：多了一堆 `if self._homework_mode`。
**判断标准**：差异集中在"渲染"上就用模式；
如果差异扩散到"交互"上，就该拆成两个类。

### 9.4 标签上的数量：一个"顺带更好"的设计

原来标题栏有一行长文字显示统计：

```
习概 / 习近平新时代中国特色社会主义概论  校修课 · 笔记 0 · 作业 0 · 易错题 0 · 教材 0 · 其它文件 0
```

**两个问题**：

1. 太长，把右边的按钮挤到截断（就是 6.4 那个 bug 的起因）；
2. 信息位置不对——「笔记有几个」这件事，**属于"笔记"这个标签**。

**改成把数量标在标签上**：

```python
def _tab_label(self, key: str, title: str, count: int | None) -> str:
    """标签文字：把条目数量接在栏目名后面。

    数量为 0 时不显示，避免一排 0 造成视觉噪声。
    """
    if count is None or count <= 0:
        return title
    return f"{title} {count}"

def _update_tab_labels(self, book: Book) -> None:
    counts = dict(book.item_counts or {})
    counts["root"] = len(self.context.library.list_items(book))
    blocker = self.tabs.blockSignals(True)      # 改文字别触发 tabChanged
    try:
        for index, (key, title, _folder) in enumerate(self._tab_defs):
            self.tabs.setTabText(index, self._tab_label(key, title, counts.get(key, 0)))
    finally:
        self.tabs.blockSignals(blocker)
```

效果：

```
AI 总结 | 简介 | 笔记 2 | 作业 | 易错题 1 | 教材 | 其它文件 3 | 全部条目 6
```

**注意 `blockSignals`**：改标签文字会触发 `currentChanged` 信号，
如果不挡住，就会递归调用刷新逻辑。**凡是"程序改控件"的地方都要想一下会不会触发信号。**

**顺带发现一个 bug**：`item_counts` 的统计循环里**漏了 `others`**，
所以「其它文件」的数量永远是 0。

```python
# 修之前
for key in (C.BOOK_FOLDER, C.ERROR_FOLDER, C.NOTEBOOK_FOLDER, C.HOMEWORK_FOLDER):
# 修之后
for key in (C.BOOK_FOLDER, C.ERROR_FOLDER, C.NOTEBOOK_FOLDER,
            C.HOMEWORK_FOLDER, C.OTHERS_FOLDER):
```

> **加栏目时最容易漏的地方**：
> 1. 声明表（肯定记得）；
> 2. **统计/缓存这类"遍历所有栏目"的循环**（最容易漏）；
> 3. 导入时的目标目录映射；
> 4. AI 总结的"参与目录"列表（这个**故意不加**，见第 13 章）。
>
> 这也是为什么要写测试：第 2 条漏了，界面不报错，只是数字永远是 0。

### 9.5 一个列表，两种语义：作业栏目的特例

作业栏目的表格要显示"每个作业一行"，但通用的 `list_folder`
会**递归展开子目录两层**（这对"按章节分的笔记"很有用）：

```python
def list_folder(self, folder: Path) -> list[BookItem]:
    """列出某个子目录内的内容，**递归两层**。"""
    ...
    for entry in entries:
        result.append(BookItem(name=entry.name, ...))
        if entry.is_dir():
            for sub in entry.iterdir():       # ← 子文件也铺出来
                if sub.is_dir():
                    continue
                result.append(BookItem(name=f"{entry.name}/{sub.name}", ...))
```

于是作业栏目会显示成这样（很难看）：

```
2.4 作业
2.4 作业/2.4 作业.md        ← 噪音
2.4 作业/homework.json      ← 噪音
```

**修法**：给作业栏目单独一个列表函数，**只列一层**：

```python
def list_homework_items(self, book: Book) -> list[BookItem]:
    """列出作业栏目的条目：**一个作业一行**。

    list_folder 会把子目录里的文件也递归铺出来（笔记里这样方便），
    但作业栏目不行：每个作业内部有 homework.json 和作业内容文件，
    全铺出来会变成一长串「第一次作业/homework.json」这种噪音。
    """
    ...
    for entry in entries:
        if entry.is_dir():
            items.append(BookItem(name=entry.name, path=entry, is_dir=True, ...))
        else:
            items.append(BookItem(name=entry.name, ...))   # 散文件仍列出
    return items
```

> **这条经验值得记住**：
> **同一个数据结构，在不同栏目里可能需要不同的"投影"。**
> 不要为了复用硬把一个函数套到两种语义上——
> 那样你会在函数里加一堆 `if is_homework`，最后谁都看不懂。
>
> 正确做法是：**共享底层读取，各自组装视图。**

### 9.6 文件打开：把"双击"做成可扩展的

`BookItem` 双击后干什么，取决于类型：

```python
def _on_item_double_clicked(self, item: BookItem) -> None:
    if item is None:
        return
    if item.is_dir:
        self.enter_folder(item.path)      # 需求：软件内部进文件夹，不弹资源管理器
        return
    self.open_file(item.path)

def open_file(self, path: Path) -> None:
    """在软件内部打开一个文件。

    * Markdown / 纯文本：走内置文档视图；
    * JSON：用 VSCode 打开（找不到 VSCode 时退回内置文本查看器）；
    * 其它文本：内置只读查看器；
    * 图片、PDF 等：交给系统默认程序。
    """
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown", ".txt"):
        self.open_document.emit(path)
        return
    if suffix in C.JSON_EXTENSIONS:
        if self.open_in_vscode(path):
            return
        self.open_text.emit(path)         # 兜底
        return
    if suffix in C.CODE_EXTENSIONS:
        self.open_text.emit(path)
        return
    file_ops.open_with_system(path)
```

**这段代码的设计要点**：

1. **判断顺序体现优先级**（Markdown 最高，系统程序最低）；
2. **每一种类型都有兜底** —— JSON 的兜底是"内置查看器"，
   **绝不会**变成"弹回资源管理器"或"让系统随便找个程序打开"；
3. **用常量集合而不是散落的字符串**（`C.JSON_EXTENSIONS`），
   要加一种扩展名就改一处。

**需求变更的痕迹也在这里**：用户先说"在软件内部打开文件夹"，
后来说"JSON 用 VSCode 打开"。
两次都只改了 `open_file` 和 `enter_folder`，
**表格控件、右键菜单、导入逻辑都没动**。

### 9.7 文件夹内部浏览：一个小型状态机

"双击文件夹在软件内部打开"听起来简单，实现要处理状态：

```python
#: 在软件内部进到了哪个文件夹（None = 正常按栏目显示）
self._current_folder: Path | None = None

def enter_folder(self, folder: Path) -> None:
    if not folder.is_dir():
        common.warn(self, f"文件夹不存在：\n{folder}", "无法打开")
        self.refresh()
        return
    self._current_folder = folder
    self._render_current_tab()
    self.status_message.emit(f"已进入文件夹：{folder.name}")

def leave_folder(self) -> None:
    """从当前文件夹退回它所在的分类目录。"""
    current = self._current_folder
    if current is None:
        return
    root = self._folder_root()
    parent = current.parent
    # 退到栏目根目录就结束内部浏览
    if root is None or parent == root or root not in parent.parents:
        self._current_folder = None
    else:
        self._current_folder = parent
    self._render_current_tab()
```

**必须处理的四个边界**（每一个都是真实 bug 的来源）：

| 边界 | 不处理的后果 | 代码位置 |
| --- | --- | --- |
| 文件夹被删了 | 显示空白，用户不知道怎么回去 | `refresh()` 里检查 `is_dir()` |
| 切栏目 | 看到另一个目录的内容（串了） | `_on_tab_changed` 里清空状态 |
| 换书目 | 状态残留 | `refresh()` 里检查书目存在性 |
| 退到栏目根 | 无限往上退 | `leave_folder` 里的 root 判断 |

```python
def _on_tab_changed(self, _index: int) -> None:
    # 切栏目就退出"文件夹内浏览"，否则会看到另一个目录的内容
    if self._current_folder is not None:
        self._current_folder = None
        self._update_folder_hint()
        self.refresh()
    ...
```

> **"状态机"思维**：任何"当前处于某种模式"的功能
> （编辑中、在文件夹里、正在加载、已登录），
> 都要**列出所有进入和离开这个状态的方式**，逐一处理。
> 漏掉一个，用户就会遇到"卡住"或"串了"的 bug。

### 9.8 自己动手

1. 把你界面里的"栏目/标签"写成声明表（key、文案、数据源），
   然后让"加一个栏目"只改这张表。
2. 找出你项目里"遍历所有栏目"的循环（统计、导出、校验），
   检查加栏目时会不会漏。
3. 挑一个你有的"模式"（编辑中、加载中、多层级导航），
   把它当状态机，**列出所有进出的路径**。

---

## 第 10 章　文件管理：导入、剪贴板与回收站

### 10.1 为什么文件操作要单独一层

"复制文件"看起来是一行 `shutil.copy`。但真实的文件管理要处理：

* 目标有同名文件怎么办？（覆盖？改名？问用户？）
* 剪切到一半失败了，源文件还在吗？
* 把文件夹粘到它自己里面怎么办？
* 用户从资源管理器复制了文件，能在软件里粘吗？
* 反过来，软件里复制的能粘到资源管理器吗？
* 粘错了能撤消吗？

**这些问题不解决，用户就会丢文件。** 所以文件操作集中在
`gwp/services/file_ops.py` 和 `gwp/services/file_clipboard.py` 两个文件里，
**界面层只负责"调用"和"显示结果"**。

### 10.2 导入：默认不覆盖，自动改名

最核心的一条规则：**永不覆盖用户的文件**。

```python
def unique_path(target: Path, suffix_style: str = "_1") -> Path:
    """目标已存在时，返回一个不冲突的新路径。

    规则：名称_1、名称_2 …（**序号递增，不累积成 名称_1_1**）。

    为什么这么做而不是覆盖或问用户：
    * 覆盖 = 丢数据，绝对不能默认；
    * 每次问用户 = 拖 20 个文件要点 20 次，太烦。
    自动改名是唯一"既不丢数据、又不打断用户"的选择。
    """
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    index = 1
    while True:
        candidate = target.with_name(f"{stem}{suffix_style.format(index)}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1
```

**注意"不累积成 `名称_1_1`"这个细节**。
朴素实现是"在前面已有的名字上加后缀"，如果用户重复导入同一个文件三次，
会得到 `笔记_1.md`、`笔记_1_1.md`、`笔记_1_1_1.md`——又长又乱。

正确做法是**基于原始名字找空位**：

```
笔记.md → 笔记_1.md → 笔记_2.md → 笔记_3.md
```

### 10.3 剪贴板：与系统互通

用户期望的行为是：**在资源管理器里 Ctrl+C，切到软件里 Ctrl+V 能粘**。
反过来也应该可以。所以剪贴板不能只是软件内部的一个列表。

```python
class FileClipboard:
    """文件剪贴板。同时写系统剪贴板（带"移动/复制"标记），
    所以能在资源管理器里 Ctrl+V。"""

    def set(self, paths: list[Path], mode: str = COPY) -> None:
        self._paths = [Path(p) for p in paths]
        self._mode = mode
        self._to_system_clipboard()

    def _to_system_clipboard(self) -> None:
        """写系统剪贴板。

        用 CF_HDROP + "Preferred DropEffect"：
        * CF_HDROP 是文件列表；
        * DropEffect 决定资源管理器粘贴时是"复制"还是"移动"。
        少了 DropEffect，剪切会被当成复制（源文件不删）。
        """
```

**读系统剪贴板**（用户从资源管理器复制的文件）：

```python
def read_system_clipboard_files() -> list[Path]:
    """读系统剪贴板里的文件列表。没有就返回空。"""
```

**"剪切失败不丢文件"的策略**（非常重要）：

```python
def paste_files(self) -> None:
    """粘贴到当前分类目录。"""
    ...
    # 1) 先全部复制成功
    for source in sources:
        destination = unique_path(target_dir / source.name)
        _transfer(source, destination, copy=True)
    # 2) 全部成功后才删源文件（剪切的情况）
    if was_cut:
        for source in sources:
            delete_path(source, to_recycle=False)
    # 3) 全部成功后才清空剪贴板
    if not failed:
        self.clipboard.clear()
```

**顺序是关键**：

```
复制成功 → 删源 → 清剪贴板
```

如果先删源再复制，一旦复制失败（磁盘满、权限不足），**文件就没了**。

> **所有"移动"操作都要遵守这个顺序**：先复制、验证成功、再删源。
> 这叫"**copy-then-delete**"，是文件操作里最基本的自保手段。

### 10.4 保护书目结构：不许把骨架剪走

书目的目录结构（`book`、`error-prone`、`notebook`、`homework`、`others`）
是软件功能的基础。如果用户把它们剪切走，整本书就废了。

```python
def copy_selection(self, mode: str = COPY) -> None:
    ...
    # 不允许把书目的结构目录剪走，否则整本书就废了
    protected = {
        (self.book().path / key).resolve()
        for key in C.BOOK_TEMPLATE_DIRS
        if self.book() is not None
    }
    chosen, blocked = [], []
    for item in items:
        resolved = item.path.resolve()
        if resolved in protected:
            blocked.append(item.name)
            continue
        chosen.append(item.path)
    if blocked:
        common.warn(self, "以下目录是书目的固定结构，不能剪切或复制：\n"
                          + "、".join(blocked), "无法操作")
```

**注意"子文件夹可以剪"**：用户自己建的 `第一章` 是可以剪的，
只有那五个**固定目录**受保护。这个区分很重要——
保护太严会让用户觉得"这软件处处不让动"。

### 10.5 防止"粘到自己里面"

一个经典的死循环场景：

```
用户复制了文件夹 A
进入 A 的子目录 B
粘贴
→ A 要被复制进 B，而 B 在 A 里面 → 无限递归 / 崩溃
```

修法是**在粘贴前检查路径包含关系**：

```python
# 防止粘到源文件所在目录时产生"自己复制自己"的一堆副本
for source in sources:
    if target_dir == source.parent:
        # 粘到原目录：会产生一堆 _1、_2，几乎肯定是误操作
        common.warn(self, "这些文件本来就在这个目录里，无需粘贴。", "无法粘贴")
        return
    if source.is_dir() and (target_dir == source or source in target_dir.parents):
        common.warn(self, "不能把文件夹粘贴到它自己（或它的子目录）里面。", "无法粘贴")
        return
```

> **`Path.parents` 是个好用的东西**：
> `target in source.parents` 就是"target 是 source 的祖先"。
> 比字符串比较可靠（不会把 `A` 和 `AB` 搞混）。

### 10.6 删除：三档保护

回顾 5.6 的结论。删除在这里的实现要区分三档：

| 场景 | 做法 | 为什么 |
| --- | --- | --- |
| 删除文件/文件夹 | 直接进回收站，**不弹确认** | 回收站可恢复，弹窗太烦 |
| 删除书目 | **弹确认**，显示"里面有多少文件" | 一次可能丢很多 |
| 删除科目 | **两段式确认**（有内容再确认一次），**默认按钮是取消** | 最重的操作 |

而且文案必须**诚实**：

```python
def _subject_delete_warning(self, subject: Subject) -> str:
    lines = [f"删除科目「{subject.title}」？", ""]
    lines.append(f"它下面有 {subject.book_count} 本书目。")
    if can_recycle:
        lines.append("会移入**回收站**，可以从回收站还原。")
    else:
        lines.append("⚠️ 回收站不可用，将**永久删除、无法还原**。")
    return "\n".join(lines)
```

**"回收站不可用"这个分支必须写**。因为有些环境（网络盘、某些策略限制）
`SHFileOperationW` 会失败，那时是 `shutil.rmtree`——**真的永久删了**。
如果文案还写"可以还原"，用户就失去了最后一次警惕的机会。

### 10.7 自己动手

1. 检查你项目里所有"移动文件"的代码，**是不是先复制后删除**？
2. 你的"另存/导出"遇到同名文件怎么处理？
   改成"自动改名"（`名称_1`）而不是覆盖。
3. 找出你项目里"不能动的结构"（配置文件、数据库、骨架目录），
   加一层保护 + 一句解释性提示。
4. 写一个"粘贴到自身子目录"的测试，确保不会死循环。

---

## 第 11 章　AI 总结与 PDF 导出

### 11.1 需求：整合而不是概括

再贴一次需求（因为它决定了整个实现）：

> Summary 不是摘要，而是**完整的学习文档**：
> 合并 `Introduct.md` + `notebook` + `error-prone`，
> 补全推导、定理条件、常见陷阱，把易错题转成清单，列出待确认问题。

**这个需求直接否掉了"把资料丢给 AI 让它压缩"的做法。**
因为"压缩"会丢掉细节，而用户要的是"更完整的文档"。

### 11.2 收集资料：谁参与、谁不参与

第一件事是**明确哪些目录参与总结**。这个决定放在声明表里：

```python
#: 参与 AI 总结的内容目录。
#: 注意 HOMEWORK_FOLDER（练习/作业）、BOOK_FOLDER（教材）与
#: OTHERS_FOLDER（其它文件）都**不在**这里 —— 它们不参与 AI 总结。
SUMMARY_SOURCE_DIRS = (ERROR_FOLDER, NOTEBOOK_FOLDER)
```

**"不参与"这件事的两种实现方式，差别很大**：

```python
# ❌ 方式一：先全收，再排除
sources = [p for p in all_files if "homework" not in str(p)
           and "book" not in str(p) and "others" not in str(p)]
# 问题：加一个新目录，必须记得改这里；漏了就悄悄参与总结了
```

```python
# ✅ 方式二：白名单（只收声明过的）
sources = []
for folder in C.SUMMARY_SOURCE_DIRS:        # ✅ 白名单
    sources.extend(collect(book.path / folder))
# 加新目录时默认**不参与**：想参与必须显式加进 SUMMARY_SOURCE_DIRS
```

**为什么白名单更好？**

* 加一个栏目的默认行为是"不参与总结"，**这符合直觉**
  （新栏目往往是"其它东西"，不该污染总结）；
* 排除法要在多处维护（收集、统计、界面提示），**白名单只有一处**；
* 白名单可以**被测试直接断言**：

```python
check("「其它文件」不参与 AI 总结", C.OTHERS_FOLDER not in C.SUMMARY_SOURCE_DIRS)
```

> **这是"默认安全"的一个例子**：
> 设计默认值时，要选"出错时影响最小"的那个。
> 新目录默认不参与总结 → 最坏情况是"用户发现新目录没被总结"（可发现、可修）；
> 新目录默认参与总结 → 最坏情况是"课件里的杂乱内容污染了总结"（难发现）。

### 11.3 分块：长资料怎么办

AI 的上下文长度有限。所以超过阈值时要**切块 → 逐块提炼 → 合并**：

```python
def generate(self, book, on_progress=None) -> str:
    materials = self.collect_materials(book)
    total_chars = sum(len(m.text) for m in materials)
    limit = int(self.config.get("summary.chunk_chars", 12000))

    if total_chars <= limit:
        return self._single_pass(book, materials)      # 一次搞定
    return self._multi_pass(book, materials, limit)    # 分块
```

**分块策略**（这是有讲究的）：

```python
def _chunk(self, materials: list, limit: int) -> list[list]:
    """按字符数切块，但**不切开单个文件**。

    为什么不切文件：文件是有语义的单元（比如"第二章的笔记"），
    从中间切开会让 AI 看到半截内容，提炼出错误结论。
    """
    chunks, current, size = [], [], 0
    for item in materials:
        if current and size + len(item.text) > limit:
            chunks.append(current)
            current, size = [], 0
        current.append(item)
        size += len(item.text)
    if current:
        chunks.append(current)
    return chunks
```

**多轮流程**：

```
第 1 轮：每块 → "提炼这一块的知识点，保留推导与结论"
第 2 轮：所有提炼结果 + 简介 → "整合成一份完整文档，补全缺失"
```

**为什么第二轮还要带简介？** 因为简介里写着**学习目标**，
它决定了"哪些内容是重点"。没有它，AI 会把所有东西一视同仁。

### 11.4 提示词：怎么写才能得到结构化输出

需求要的是"结构化文档"，所以提示词必须**明确输出格式**：

```python
SUMMARY_SYSTEM_PROMPT = """你是一位严谨的学科助教，正在帮学生整理复习资料。

要求：
1. **整合，不要概括**：把资料合并成一份更完整的学习文档，可以补充推导、
   定理成立条件、常见陷阱，但**不要删掉原有结论**；
2. **易错题转清单**：把易错题整理成
   「错误表现 → 根本原因 → 正确做法 → 同类变形」四段式；
3. **标注来源**：引用资料时注明来自哪个文件；
4. **列出待确认问题**：资料里没说清的地方，集中列在最后一节；
5. 输出用 Markdown，标题层级从 ## 开始。"""
```

**几个实战要点**：

| 要点 | 为什么 |
| --- | --- |
| 说清"不要做什么"（不要概括） | 只正面描述时，AI 很容易走回"摘要"这个默认行为 |
| **给输出格式**（标题层级、四段式） | 格式约束能极大提升可用性 |
| 要求**标注来源** | 便于用户回查原始资料 |
| 要求**列出不确定的地方** | 这是防止 AI 编造的实用手段 |

### 11.5 可插拔的 AI 提供方

需求要支持 DeepSeek / GPT / 本地 / 网页版。硬编码会变成：

```python
# ❌ 每加一个提供方要改一堆地方
if provider == "deepseek":
    url, key = "https://api.deepseek.com", config.get("ai.deepseek_key")
elif provider == "gpt":
    ...
```

正确的做法是**注册表 + 自动发现**（`gwp/ai/providers/`）：

```python
# 每个提供方一个文件，例如 gwp/ai/providers/deepseek_api.py
@register_provider
class DeepSeekProvider(BaseProvider):
    name = "deepseek_api"
    label = "DeepSeek API"

    def available(self) -> bool:
        return bool(self.api_key())

    def chat(self, messages, on_chunk=None) -> str:
        ...
```

```python
# gwp/ai/registry.py
_PROVIDERS: dict[str, type] = {}

def register_provider(cls):
    """装饰器：把提供方登记进注册表。"""
    _PROVIDERS[cls.name] = cls
    return cls

def discover() -> None:
    """扫描 providers 包，把所有模块导入一遍（触发注册）。"""
    import pkgutil, importlib
    package = importlib.import_module("gwp.ai.providers")
    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"gwp.ai.providers.{module.name}")
```

**加一个提供方 = 加一个文件**，不改任何已有代码。这就是"开放-封闭原则"
（对扩展开放，对修改封闭）的落地。

**兜底链**：用户配的提供方挂了怎么办？按配置顺序依次尝试：

```python
def chat(self, messages, on_chunk=None) -> str:
    errors = []
    for name in self.fallback_chain():          # 例如 [deepseek, gpt, local]
        provider = self.provider(name)
        if provider is None or not provider.available():
            continue
        try:
            return provider.chat(messages, on_chunk)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            log.warning("提供方 %s 失败，尝试下一个", name, exc_info=True)
    raise AIError("所有 AI 提供方都失败了：\n" + "\n".join(errors))
```

**关键细节**：错误信息要**汇总所有失败原因**，
而不是只报最后一个。否则用户排查时信息不全。

### 11.6 后台线程：界面不能卡

AI 调用要几秒到几十秒。放主线程界面会"假死"。
所以用 `QThread`（这是 `ai/` 层唯一允许 import Qt 的文件，见 3.6）：

```python
class AIWorker(QThread):
    chunk = pyqtSignal(str)              # 流式文本片段
    progress = pyqtSignal(str, int, str) # 消息, 百分比, 详情
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def run(self):
        try:
            result = self._task(on_chunk=self.chunk.emit,
                                on_progress=self.progress.emit,
                                should_cancel=lambda: self._cancelled)
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
```

**流式输出**的价值：用户看到文字一个个蹦出来，**知道它在工作**，
心理等待时间大幅缩短。这是体验上性价比最高的一个功能。

### 11.7 PDF 导出：为什么"改成绝对路径"不管用

导出 PDF 是这一章技术上最有意思的部分。管线是：

```
Markdown → HTML（markdown 库 + Pygments 代码高亮）
        → PyMuPDF Story 排版
        → DocumentWriter 写 PDF
```

**第一个坑：中文字体**。PyMuPDF 的 `Story` 需要能拿到中文字体，
否则全是方框。解决办法是在 CSS 里指定字体族，并在排版时提供字体文件。

**第二个坑（花了很久才找到）：图片出不来。**

朴素的想法是"把 HTML 里的 `<img src="相对路径">` 改成绝对路径"。
**结果一张图都出不来。**

真正的原因是：PyMuPDF 的 `Story` **不通过文件系统解析图片**，
它要通过一个 **`Archive`（归档）** 来解析资源：

```python
def render_pdf(html_text: str, output: Path, asset_dir: Path) -> int:
    """用 Story 分页写出 PDF。

    asset_dir 交给 pymupdf.Archive，这样 HTML 里的**相对路径**图片才能被找到
    —— 只给 src 绝对路径是**不生效**的。
    """
    archive = pymupdf.Archive(str(asset_dir))
    story = pymupdf.Story(html=html_text, archive=archive)
    writer = pymupdf.DocumentWriter(str(output))
    ...
```

**这个坑的教训**：

> 当一个"看起来应该对"的做法完全不起作用时，
> **不要微调参数，去找这个库的设计意图**。
> `Archive` 参数的存在本身就说明"资源解析要走它"，
> 只是文档没写得那么显眼。

**第三个坑：页码**。加页码要在 PDF 写完之后，用底层 API 画上去：

```python
def add_page_numbers(path: Path, numbers=None, total=None) -> None:
    """在每页底部画页码。"""
    document = pymupdf.open(path)
    for index, page in enumerate(document):
        rect = page.rect
        text = f"{numbers[index] if numbers else index + 1} / {total or len(document)}"
        page.insert_text(
            pymupdf.Point(rect.width / 2 - 12, rect.height - 28),
            text, fontsize=9, color=(0.45, 0.45, 0.45),
        )
    document.saveIncr()          # 增量保存，不重写整个文件
```

### 11.8 自己动手

1. 给你自己的"数据收集"逻辑改写成**白名单**，并加一条断言
   "新目录默认不参与"。
2. 写一个"长文本分块"函数，**保证不切开单个文件**。
3. 用装饰器 + `pkgutil` 做一个插件注册表，实现"加一个文件就多一个实现"。
4. 如果你用 PyMuPDF，试着用 `Archive` 解决图片问题（别改路径）。

---

## 第 12 章　AI 提供方的适配细节与降级

### 12.1 四种提供方，四套脾气

这个项目支持四类 AI 接入，它们的差异**不能靠一个通用 HTTP 客户端抹平**：

| 提供方 | 接入方式 | 特点 |
| --- | --- | --- |
| DeepSeek API | HTTPS + API Key | 中文好、便宜、流式支持好 |
| GPT API | HTTPS + API Key | 生态成熟 |
| 本地命令 | 起子进程 | 断网可用，但要处理进程与编码 |
| 网页版 | **剪贴板桥接** | 不需要 Key，但要人参与 |

### 12.2 适配器协议：只抽公共部分

```python
class BaseProvider:
    """AI 提供方协议。"""

    name: str = ""
    label: str = ""

    def available(self) -> bool:
        """现在能不能用（有没有 Key、命令在不在）。"""
        return False

    def chat(self, messages: list[dict], on_chunk=None) -> str:
        """发一轮对话，返回完整回复。on_chunk 给流式用。"""
        raise NotImplementedError

    def describe(self) -> str:
        """给设置界面显示的一行状态。"""
        return self.label
```

**只抽四件事**：能不能用、发消息、流式回调、描述。
**没有硬塞"模型列表""温度参数"这些** —— 因为不同提供方差别太大，
强行统一会变成"一大堆可选参数"。

> **抽象的经验**：
> 抽**调用方式**（`chat`），不要抽**配置项**。
> 前者各家都一样，后者各家都不一样。

### 12.3 本地命令：子进程的三个坑

```python
class LocalCommandProvider(BaseProvider):
    """通过命令行调用本地模型（例如 ollama run llama3）。"""

    def chat(self, messages, on_chunk=None) -> str:
        command = self._command()          # 例如 ["ollama", "run", "llama3"]
        prompt = self._flatten(messages)   # 把多轮对话拼成一个字符串
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # 坑 1：编码。Windows 默认不是 UTF-8，中文会变乱码
            encoding="utf-8", errors="replace",
            # 坑 2：不能弹黑框（否则每次调用闪一个 CMD 窗口）
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        # 坑 3：大输出可能死锁 —— 必须边读边发，不能等它结束再全读
        chunks = []
        for line in process.stdout:
            chunks.append(line)
            if on_chunk:
                on_chunk(line)
        process.wait(timeout=self._timeout())
        return "".join(chunks)
```

**三个坑都是真实的**：

1. **编码**：不指定 `encoding="utf-8"`，中文输出在 Windows 上会乱码；
2. **黑框**：不加 `CREATE_NO_WINDOW`，每次调用闪一个控制台窗口；
3. **死锁**：如果输出很大而你不读，子进程写满了管道缓冲区就卡住，
   你在 `wait()` 上永远等下去。**必须边读边处理。**

### 12.4 网页版：用剪贴板做桥

最巧的一个设计。有些用户不想配 API Key，但愿意用网页版 AI。怎么接？

**答案是"提问块 + 剪贴板"**：软件把提示词复制到剪贴板，
用户粘贴到网页版 AI，再把回复粘回来。

看起来"很土"，但它解决了两个真问题：

* **零配置**：不用 Key、不用网络代理；
* **用户可控**：用户能看到发给 AI 的原文，能改。

实现上要能被程序识别（用户可能粘回来一大堆别的东西），
所以约定一个标记：

````markdown
```gwp:ask
{"question": "这段推导的第二步是怎么来的？", "options": ["A. 由定理2", "B. 由定义"]}
```
````

程序解析这个块 → 生成提示词 → 复制到剪贴板 → 等用户粘贴回复。
**协议要简单、要人能看懂**，因为用户会手工改它。

> **设计"人在环路"（human-in-the-loop）功能的要点**：
> 协议要**人类可读可改**，程序只做"识别与提取"。
> 用 JSON 而不是二进制、用 Markdown 代码块而不是特殊分隔符。

### 12.5 降级：核心是"告诉用户现在是什么状态"

降级的正确做法不是"静默换一个"，而是**在界面上如实显示**：

```python
def describe(self) -> str:
    """状态栏显示，例如：
    AI：DeepSeek API（deepseek-chat）  |  AI：本地命令 ollama（未检测到）
    """
```

**三条降级原则**：

1. **绝不静默降级**。用户以为在用 A，实际在用 B，会得出错误结论；
2. **失败要给出可操作的下一步**（"去设置里填 Key"而不是"调用失败"）；
3. **降级链要有序且可见**（Fallback 顺序写在配置里，能在界面上看到）。

### 12.6 自己动手

1. 给你的"外部调用"（API、命令行）写一个统一接口，
   但**只抽调用方式，不抽配置项**。
2. 检查你起子进程的地方：**指定编码了吗？会弹窗吗？会不会死锁？**
3. 找一个你做"静默降级"的地方，改成"明确告知用户"。

---

## 第 13 章　版本管理：给"不可逆操作"留退路

### 13.1 为什么 AI 生成的东西要备份

AI 总结有个特性：**每次重新生成结果都不一样**。
用户可能觉得"上一版更好"——但如果没有备份，那就永久丢了。

所以生成本身不是难点，**"可回退"才是**。这一章讲备份机制。

### 13.2 备份策略：按时间戳快照

```python
class BackupManager:
    """总结的版本备份。

    目录结构：
        else data/summary_backup/<科目>/<书目>/<时间戳>/<文件名>
    """

    def backup(self, subject: str, book: str, files: list[Path]) -> Path | None:
        """把待覆盖的文件备份到时间戳目录。返回备份目录。"""
        existing = [f for f in files if f.is_file()]
        if not existing:
            return None                      # 没东西可备份（首次生成）
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self._dir(subject, book) / stamp
        target.mkdir(parents=True, exist_ok=True)
        for source in existing:
            shutil.copy2(source, target / source.name)
        return target
```

**三个设计决定**：

| 决定 | 理由 |
| --- | --- |
| 备份**放在 `else data/`**（软件数据区），不是用户数据区 | 这是软件的辅助产物，不是用户内容 |
| 用**时间戳命名** | 一眼知道哪版是哪版，也能按时间排序 |
| **首次生成不备份** | 没有"上一版"，备份只会产生空目录 |

### 13.3 恢复：必须能"先看再恢复"

直接覆盖回去风险太大——用户可能恢复了错的那一版。
所以要有**预览与对比**：

```python
class BackupDialog(QDialog):
    """版本管理对话框：列表 + 预览 + 对比 + 恢复。"""

    def _load_versions(self) -> list[VersionInfo]:
        ...
    def _on_select(self):
        """选中一版：右边显示内容；如果和当前不同，标出差异。"""
```

**行级差异对比**用标准库 `difflib`，不需要第三方库：

```python
import difflib

def unified_diff(old: str, new: str) -> str:
    """生成行级差异（和 git diff 一样的格式）。"""
    return "\n".join(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile="备份版本", tofile="当前版本", lineterm="",
    ))
```

**为什么差异对比重要？** 用户面对两份长文档，
**肉眼看不出哪里不一样**。差异对比把"找不同"变成"看标记"。

> **"不可逆操作"的三件套**（任何软件都该有）：
> 1. **备份**（出事能回去）；
> 2. **预览**（操作前能看清）；
> 3. **对比**（能看出差异）。
>
> 缺任何一个，用户都会因为"怕出错"而不敢用这个功能。

### 13.4 保留策略：不能无限增长

每次都备份，一年后会有几千个目录。所以要清理：

```python
def prune(self, subject: str, book: str, keep: int = 30) -> int:
    """只保留最近 keep 版，删掉更早的。返回删掉的数量。

    注意：**删备份是安全的**（它不是用户数据），
    所以这里直接 rmtree，不用回收站。
    """
    versions = sorted(self._dir(subject, book).iterdir(), reverse=True)
    removed = 0
    for old in versions[keep:]:
        shutil.rmtree(old, ignore_errors=True)
        removed += 1
    return removed
```

**"删备份不用回收站"这个判断值得说明**：
备份是软件自己产生的、可以重建（虽然内容不同）的辅助数据。
如果每个备份都进回收站，回收站会被几千个目录塞满，
用户清理起来更痛苦。**分清"用户数据"和"软件数据"，
在删除策略上体现出来。**

### 13.5 自己动手

1. 给你项目里"不可逆"的操作（覆盖文件、清空数据、重新生成）
   加一个时间戳备份。
2. 用 `difflib` 给两份文本做一个差异对比界面。
3. 给备份加一个"只留最近 N 版"的清理策略。

---

## 第 14 章　Markdown 编辑器与 AI 双栏

### 14.1 三种模式

需求要"查看模式 / 编辑模式 / AI 双栏"。本质是**同一个文档的三种呈现**：

| 模式 | 左 | 右 |
| --- | --- | --- |
| 查看 | 渲染后的 Markdown | — |
| 编辑 | 编辑器（源码） | — |
| 双栏 | 编辑器 | 渲染预览 + AI 面板 |

```python
class MarkdownEditor(QWidget):
    MODE_PREVIEW = "preview"
    MODE_EDIT = "edit"
    MODE_SPLIT = "split"

    def apply_mode(self, mode: str) -> None:
        self.mode = mode
        is_preview = mode == self.MODE_PREVIEW
        self.editor.setVisible(not is_preview)       # 源码区
        self.preview.setVisible(mode != self.MODE_EDIT)  # 渲染区
        self.splitter.setOrientation(
            Qt.Orientation.Horizontal if mode == self.MODE_SPLIT
            else Qt.Orientation.Vertical
        )
```

**"模式"而不是"三个控件类"**：因为文档对象、撤销栈、滚动位置
都该在切换时保留。三个类会导致"切换模式丢光标位置"这类问题。

### 14.2 编辑与预览同步：别每次按键都重渲染

朴素做法是 `textChanged → 重新渲染`。问题：大文档渲染慢，
用户打字会卡。

**用定时器做防抖**（debounce）：

```python
self._render_timer = QTimer(self)
self._render_timer.setSingleShot(True)
self._render_timer.setInterval(300)          # 停手 300ms 后才渲染
self._render_timer.timeout.connect(self._render_preview)
self.editor.textChanged.connect(self._render_timer.start)   # 只重置计时器
```

**防抖的通用模式**：

```python
def on_change():
    timer.start()        # 每次变化都"重新计时"
# 只有"安静了 interval 毫秒"才真正执行
```

这个模式在**自动保存、搜索、实时校验**里都能用。

### 14.3 语法高亮：用 QSyntaxHighlighter

```python
class MarkdownHighlighter(QSyntaxHighlighter):
    """Markdown 语法高亮。规则：标题、加粗、代码、链接…"""

    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._build_rules()

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            match = pattern.match(text)
            while match.hasMatch():
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, fmt)
                match = pattern.match(text, start + length)
```

**注意 `highlightBlock` 会被频繁调用**（每次内容变化、每行一次），
所以规则要预编译（`QRegularExpression` 在 `__init__` 里建好），
**不要在里面现编译正则**。

### 14.4 查找替换：一个"看起来简单"的功能

查找要做到：

* 高亮所有匹配；
* 上一个/下一个跳转时**自动滚动到可见**；
* 替换当前 / 全部替换；
* **替换全部要能被撤消**（否则用户手滑就完了）。

```python
def replace_all(self, old: str, new: str) -> int:
    """全部替换。用一次 beginEditBlock 让整个替换**成为一步撤销**。"""
    cursor = QTextCursor(self.editor.document())
    cursor.beginEditBlock()                  # ← 关键
    count = 0
    while True:
        cursor = self.editor.document().find(old, cursor)
        if cursor.isNull():
            break
        cursor.insertText(new)
        count += 1
    cursor.endEditBlock()
    return count
```

**`beginEditBlock` / `endEditBlock`** 是 `QTextDocument` 提供的
"把多个编辑合成一步撤销"的机制。**没有它，用户替换 500 处后
要按 500 次 Ctrl+Z。**

> **凡是"批量修改用户内容"的功能，都必须考虑撤销粒度。**
> 用户的心理模型是"我刚才做了一件事"，不是"我做了 500 件事"。

### 14.5 自己动手

1. 给一个"输入即处理"的功能加**防抖**（搜索框、实时预览、自动保存）。
2. 用 `QSyntaxHighlighter` 做一份简单的语法高亮（先编译正则）。
3. 做一个"批量替换"，并确保**一步就能撤销**。

---

# 第三部分　需求变更实战

> 前面 14 章讲的是"按计划做"。真实项目里，超过一半的时间在**应对变化**。
>
> 这一部分用四个真实的需求变更案例，讲"怎么改而不改坏"。
> **这是全书最接近真实工作的部分。**

---

## 第 15 章　实战一：新增一种科目类型（日记）

### 15.1 需求

> 增加一个「日记」类型的 Subject。日记的用法：把每天写的放进「我的日记」，
> AI 负责两件事——**归纳思想**（AI 总结）与**合并整理**（AI 日记）。
> 日记不需要「AI 总结」和「简介」栏目。

### 15.2 先分析：这次变更的"影响面"

动手前先画一张影响图。**这是需求变更最重要的一步**：

```
新增类型要动的东西：
├─ 1. 类型常量（SUBJECT_TYPES）
├─ 2. 类型标签（新建对话框里显示什么）
├─ 3. 该类型的目录结构（日记用 AI summary / AI diary / ...）
├─ 4. 该类型的界面栏目
├─ 5. 该类型的"参与 AI 总结的目录"
├─ 6. 该类型的特殊按钮（生成思想总结 / 生成日记）
├─ 7. 新建日记时自动建默认书目（MyBook）
└─ 8. 数据兼容：老数据没有 type 字段怎么办？
```

**其中 1–5 都是"数据"**，如果前面架构对了，这些只是往声明表里加行。
只有 6、7 需要写新代码。

### 15.3 第一步：加常量与标签（纯数据）

```python
SUBJECT_DIARY = "diary"
SUBJECT_TYPES = (SUBJECT_DIARY, SUBJECT_SCHOOL, SUBJECT_SELF_STUDY)

SUBJECT_TYPE_LABELS = {
    SUBJECT_DIARY:     ("日记",   "按天记录的文字；AI 归纳思想并合并整理成册"),
    SUBJECT_SCHOOL:    ("校修课", "学校开设的课程；含教材、易错题、作业"),
    SUBJECT_SELF_STUDY:("自学课", "自己找资料学习的课程；含教材、易错题、练习"),
}
```

**注意 `SUBJECT_TYPES` 的顺序就是新建对话框的显示顺序。**
把"日记"放第一个是有意的——需求里说"日记的用法…"，
说明它是用户最常新建的类型之一。

### 15.4 第二步：声明日记的目录与栏目

```python
#: 日记科目的文件夹名（位于 Book 目录下）
DIARY_AI_SUMMARY_FOLDER = "AI summary"   # AI「思想总结」的产出
DIARY_AI_DIARY_FOLDER   = "AI diary"     # AI「文档合并 + 格式统一」的产出
DIARY_MINE_FOLDER       = "my diary"     # 用户自己写的
DIARY_OTHERS_FOLDER     = "else diary"   # 其它来源

DIARY_TEMPLATE_DIRS = (
    DIARY_AI_SUMMARY_FOLDER, DIARY_AI_DIARY_FOLDER,
    DIARY_MINE_FOLDER, DIARY_OTHERS_FOLDER,
)
#: 日记的 AI 读哪些目录（注意：只读用户写的两个，不读自己的产出）
DIARY_SOURCE_DIRS = (DIARY_MINE_FOLDER, DIARY_OTHERS_FOLDER)

BOOK_TABS_DIARY = (
    ("diary-ai-summary", "AI 思想总结", DIARY_AI_SUMMARY_FOLDER),
    ("diary-ai",         "AI 日记",     DIARY_AI_DIARY_FOLDER),
    ("diary-mine",       "我的日记",    DIARY_MINE_FOLDER),
    ("diary-others",     "其它日记",    DIARY_OTHERS_FOLDER),
    ("root",             "全部条目",    None),
)
```

**两个关键决定**：

1. **日记没有「AI 总结」和「简介」栏目** —— 因为日记不写"学习目标"，
   这两个栏目没有意义。**栏目是类型的一部分，不是所有类型共有的。**
2. **`DIARY_SOURCE_DIRS` 不包含 AI 自己的产出** —— 否则会"AI 读自己上次写的东西"，
   越写越偏。（这个坑很隐蔽：第二轮总结会基于第一轮的输出，
   产生自我强化。）

### 15.5 第三步：让类型驱动行为

到此为止，**界面代码一行都没改**。因为前面已经写好了这些"按类型取配置"的函数：

```python
def tabs_for_type(subject_type: str) -> tuple:
    """按科目类型取 Book 页的标签定义。未知类型按自学课处理。"""
    return BOOK_TABS_BY_TYPE.get(subject_type or DEFAULT_SUBJECT_TYPE,
                                 BOOK_TABS_SELF_STUDY)

def template_dirs_for_type(subject_type: str) -> tuple[str, ...]:
    """按科目类型取 Book 的标准目录。"""
    if (subject_type or "") == SUBJECT_DIARY:
        return DIARY_TEMPLATE_DIRS
    return BOOK_TEMPLATE_DIRS

def summary_sources_for_type(subject_type: str) -> tuple[str, ...]:
    """按科目类型取"参与 AI 总结"的目录。"""
    if (subject_type or "") == SUBJECT_DIARY:
        return DIARY_SOURCE_DIRS
    return SUMMARY_SOURCE_DIRS
```

**三个"unknown 兜底"**：`or DEFAULT_SUBJECT_TYPE`。
作用见 15.7。

### 15.6 第四步：需要写新代码的部分

只有两处：

**① 日记自动建默认书目**（因为日记是"打开就要写"的东西）：

```python
# create_subject 里
if kind == C.SUBJECT_DIARY:
    try:
        self.create_book(clean, C.DIARY_DEFAULT_BOOK, subject_type=kind)
    except Exception:  # noqa: BLE001 - 建默认书目失败不该让新建科目失败
        log.warning("为日记科目创建默认书目失败：%s", clean, exc_info=True)
```

**注意那个 `except Exception`**：日记科目建好了但默认书目没建成，
比"整个新建失败"要好。**辅助功能失败不应该让主功能失败。**

**② 日记专属的两个生成按钮**：

```python
self.btn_diary_thought = self.add_action(
    "思想总结", self.generate_diary_thought, accent=True,
    tooltip="读「my diary」的全部日记，归纳成思想小结，写入「AI summary」",
)
self.btn_diary_book = self.add_action(
    "整理日记", self.generate_diary_book, accent=True,
    tooltip="把「my diary」的全部内容按日期合并成格式统一的日记，写入「AI diary」",
)
# 默认隐藏，切到日记科目时才显示
self.btn_diary_thought.setVisible(False)
self.btn_diary_book.setVisible(False)

def apply_subject_type(self, subject_type: str) -> None:
    """按科目类型切换标签与按钮。"""
    self.subject_type = subject_type or C.DEFAULT_SUBJECT_TYPE
    is_diary = self.subject_type == C.SUBJECT_DIARY
    self._apply_tabs(C.tabs_for_type(self.subject_type))
    self.btn_summary.setVisible(not is_diary)          # 普通科目的按钮
    self.btn_diary_thought.setVisible(is_diary)
    self.btn_diary_book.setVisible(is_diary)
```

### 15.7 第五步（最关键）：向后兼容

**老数据没有 `subject_type` 字段**（那时还没这个功能）。
如果不处理，所有老科目会变成"未知类型"。

处理方式**只有一行兜底**，但它出现在所有读取处：

```python
# 读取时
subject_type=str(meta.get("subject_type") or C.DEFAULT_SUBJECT_TYPE)
```

```python
# 使用处
kind = subject.subject_type if subject is not None else C.DEFAULT_SUBJECT_TYPE
```

```python
# 取配置时
def tabs_for_type(subject_type: str) -> tuple:
    return BOOK_TABS_BY_TYPE.get(subject_type or DEFAULT_SUBJECT_TYPE,
                                 BOOK_TABS_SELF_STUDY)     # ← 第二个兜底
```

**为什么"默认自学课"是对的？**

因为在这个功能出现之前，**所有科目在行为上都等价于自学课**。
选这个默认值，老用户升级后**什么都感觉不到**——这就是最好的兼容。

> **向后兼容的通用方法**：
> 1. 找出"这个字段出现之前，所有数据实际上等价于哪个值"；
> 2. 把那个值当作默认；
> 3. 在老数据的读取路径上（**通常只有一处**）加兜底。
>
> 最后一定要写一条测试：**"造一条没有该字段的老数据，验证行为正确"**。

### 15.8 复盘：这次变更改了什么

| 类别 | 内容 | 数量 |
| --- | --- | --- |
| 纯数据 | 常量、标签、目录、栏目、来源 | 5 处（都在 constants.py） |
| 新逻辑 | 自动建默认书目、两个生成按钮 | 2 处 |
| 兼容兜底 | 读取处 + 取配置处 | 3 行 |
| **已有界面代码** | — | **0 处** |

**"已有界面代码 0 处改动"就是架构成功的证据。**
如果当初把栏目写死在 `BookView.__init__` 里，这次要改的就不止 5 处了。

---

## 第 16 章　实战二：给现有栏目加能力（创建作业）

### 16.1 需求

> 校修 Subject 的「作业」栏目，把「导入文件」改成「创建作业」。
> 作业包括：作业内容、DDL、作业（文件）、提交方式。
> **作业内容和作业是文件，DDL 是时间，提交方式是网址（用户提交网址，生成超链接，允许更改）。**

### 16.2 先问清楚：这是"改按钮"还是"改数据模型"

第一直觉是"把按钮文案改一下，弹个对话框"。但仔细看需求：

> 作业 **包括** 作业内容 / DDL / 提交方式

**这是说"作业"这个实体多了三个属性。**
而现在的"作业"只是一个文件夹。**所以这是一次数据模型变更**，
不是界面变更。

**判断依据**：需求里出现"包括/包含/有…字段"，就是数据模型变更。

### 16.3 数据模型设计：一个作业 = 一个文件夹

有三个可选方案：

| 方案 | 结构 | 评价 |
| --- | --- | --- |
| A. 一个文件 | `2.4作业.md`，用 YAML front matter 存 DDL | 简单，但一个作业要交多个文件时不方便 |
| B. **一个文件夹 + 元数据文件** | `2.4作业/homework.json` + 内容文件 | ✅ 灵活，能放多个文件 |
| C. 集中一个清单文件 | `homework/index.json` 描述所有作业 | ❌ 清单和实际内容会不一致 |

**选 B**，理由：

* 一个作业常常要交好几样东西（报告 + 代码 + 截图），**文件夹最直观**；
* 元数据**跟着作业走**：改文件夹名、搬到别的书目、整个拷走，元信息都不丢；
* 和"磁盘即数据库"的整体设计一致。

```python
# gwp/data_manager/homework.py
@dataclass
class Homework:
    """一个作业的元信息。"""
    name: str
    path: Path
    content: str = ""          # 作业内容（正文）
    due: str = ""              # 截止时间（ISO 字符串，可为空）
    submit_url: str = ""       # 提交网址（可为空）
    done: bool = False         # 是否已完成（第五次需求时加的）
    created_at: str = ""
    updated_at: str = ""
```

存到 `homework.json`：

```json
{
  "name": "2.4 作业",
  "content": "课本 P80 第 3、5、7 题",
  "due": "2026-10-11T23:15",
  "submit_url": "https://spocnew.example.edu/...",
  "done": false
}
```

### 16.4 "可为空"是需求的一部分

需求把 DDL 和提交方式都列为"包括"，但**用户很可能不想填**。
所以两者都必须**可以为空**：

```python
def state(self, now=None) -> str:
    """返回 overdue / soon / ok / none（无 DDL）。"""
    moment = self.due_at
    if moment is None:
        return "none"                       # 没设 DDL 是一个合法状态
    ...
```

界面上也要体现：

```python
due_text = homework.due_label        # 没设时返回 "未设 DDL"
if state == "overdue":
    due_text += "（已过期）"
elif state == "soon":
    due_text += "（即将截止）"
```

**"没设"要作为一个显式状态显示出来**，而不是留空。
留空用户会以为"坏了/没读到"。

### 16.5 时间：能填也能不填

时间输入有个细节：用户可能只想填日期，不想填时分。

```python
_TIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y/%m/%d",
)

def parse_due(text: str) -> datetime | None:
    """把用户输入解析成 datetime。空或无法识别返回 None。"""
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:                                  # 兜底：ISO 8601（含时区）
        return datetime.fromisoformat(raw)
    except ValueError:
        return None
```

**为什么接受这么多格式？** 因为用户**可能手工改 `homework.json`**
（这是设计卖点）。手工填的时候他写 `2026/10/11` 也很正常，
不能因为格式不对就当没有。

```python
def format_due(moment: datetime | None) -> str:
    """写回 ISO 字符串。含时分就带时分，否则只写日期。"""
    if moment is None:
        return ""
    if (moment.hour, moment.minute, moment.second) == (0, 0, 0):
        return moment.strftime("%Y-%m-%d")          # 只填了日期
    return moment.strftime("%Y-%m-%dT%H:%M")
```

**"不填时分就不写时分"** 这个小细节让文件更干净可读。

### 16.6 网址：要校验，也要容错

```python
def is_valid_url(text: str) -> bool:
    """只接受 http/https，并要有主机名。"""
    raw = (text or "").strip()
    if not raw:
        return True                      # 允许留空
    parsed = urlparse(raw)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def normalize_url(text: str) -> str:
    """补全用户常漏的 https:// 前缀。"""
    raw = (text or "").strip()
    if not raw or is_valid_url(raw):
        return raw
    if "://" not in raw and "." in raw.split("/")[0]:
        candidate = f"https://{raw}"
        if is_valid_url(candidate):
            return candidate
    return raw
```

**为什么要 `normalize_url`？** 用户输入 `course.example.edu/upload`
（忘了写 `https://`）非常常见。自动补全比报错友好。

**为什么只允许 http/https？** 因为提交方式是"点一下就打开"的链接。
如果允许 `file://` 或自定义协议，就等于给了"点一下执行本机程序"的口子。
**安全约束要在数据层做**（不在界面做），这样任何调用路径都被保护。

### 16.7 界面：长网址不能直接显示

第一版把网址直接显示在表格里。结果用户截图反馈：

```
提交方式
/spocnew/mycourse/coursecenter/2026-2027-1-B090011036-095101/notice/...（一屏都放不下）
```

**修法**：显示成一个**按钮**，网址放悬浮提示里。

```python
if homework.submit_url:
    # 提交网址往往很长（教务系统那种上百字符），
    # 直接显示会把表格撑得没法看 —— 换成一个「提交作业」按钮，
    # 完整网址放在悬浮提示里，需要复制时用右键菜单。
    button = QPushButton("提交作业")
    button.setToolTip(f"打开提交网址：\n{homework.submit_url}")
    button.clicked.connect(lambda: self.submit_link_clicked.emit(path, url))
    holder = QWidget(); ...
    self.setCellWidget(row, submit_column, holder)
else:
    # 没填提交方式：不摆一个点了没反应的按钮，直接说明
    empty_cell = QTableWidgetItem("未填写")
```

**两个设计决定**：

1. **没填时不放按钮**（放了会让人以为能点，点了没反应）；
2. **这一列固定宽度**（`setSectionResizeMode(Fixed)`），
   否则多长的网址都能把列撑开。

**还要点一下确认再跳转**（用户后来提的需求）：

> 点「提交作业」**不会直接跳走**，而是先弹一个确认框，
> 把**这个作业文件夹的完整路径**摆在最显眼的位置。

**为什么这个需求合理？** 因为用户点"提交"时，往往还没把附件放进文件夹。
先看到路径 → 去放附件 → 再点确认提交。**这是一个工作流需求，不是界面偏好。**

```python
def _on_submit_link(self, folder: Path, url: str = "") -> None:
    """点「提交作业」：**先弹框**显示作业文件夹路径，再让用户决定是否跳转。"""
    ...
    dialog = SubmitHomeworkDialog(self, homework=homework, folder=folder, url=target)
    dialog.exec()
    if dialog.choice != "submit" or not target:
        return
    shell_ops.open_url(target)
```

### 16.8 只有校修课有这个栏目

需求明确说"校修 Subject 的作业栏目"。所以自学课的同一目录
（显示为「练习」）不应该有"创建作业"：

```python
def _sync_homework_buttons(self) -> None:
    """「创建作业」与「导入文件」按当前标签互斥显示。

    作业是**校修课的作业栏目**专属：自学课的同一目录叫「练习」，
    仍然按普通文件夹用（导入文件），不做作业管理。
    """
    is_homework_tab = self._current_tab_key() == "homework"
    manageable = (is_homework_tab
                  and self.subject_type == C.SUBJECT_SCHOOL
                  and self.book() is not None)
    self.btn_homework.setVisible(manageable)
    self.btn_import.setVisible(not manageable)
```

**注意 `and self.book() is not None`**：没有打开书目时不能显示
"创建作业"（点了不知道往哪建）。**按钮的可见性要包含"前置条件是否满足"。**

### 16.9 复盘

| 类别 | 内容 |
| --- | --- |
| 新数据模型 | `Homework` dataclass + `homework.json` + 读写函数 |
| 新界面 | 创建/编辑对话框、提交确认框、表格的 DDL/提交方式两列 |
| 改已有逻辑 | 「导入文件」按钮改为按条件互斥显示；作业列表只列一层 |
| **没动** | 数据结构（还是 `homework/` 目录）、导入导出、剪贴板、AI 总结 |

**注意最后一行的"没动"**：因为"作业"仍然是 `homework/` 目录下的东西，
所有基于目录的功能自动适用。**这就是"目录语义不分叉"的回报。**

---

## 第 17 章　实战三：跨模块的新功能（日程栏）

### 17.1 需求

> 首页右侧创建任务栏，显示日程。日程包括**作业**和**其他日程**。
> 任务栏支持创建日程，日程要有按键用于完成日程，日程按照 DDL 排序。
> 作业也要添加按键（完成作业）。

### 17.2 分析：这是一个"聚合视图"

关键句是"日程**包括**作业和**其他日程**"。这说明：

* 作业**已经有数据了**（第 16 章建的）——不需要重新录入；
* "其他日程"是**新数据**；
* 日程栏是一个**聚合视图**：把两个来源合起来按时间排。

**这是一个非常好的需求**，因为它避免了数据重复：
用户不会"在作业里填一遍，又在日程里填一遍"。

**设计决定**：
* 作业的完成状态 → 存在 `homework.json` 的 `done` 字段（**状态跟着数据走**）；
* 其他日程 → 新文件 `schedule.json`，放在**数据根目录**
  （因为日程可能和任何科目都无关）。

### 17.3 为什么 `schedule.json` 不和作业放一起

这是一个值得讲的架构判断：

| 放哪 | 好处 | 坏处 |
| --- | --- | --- |
| 某个书目下 | 和作业一致 | 日程可能跟哪门课都无关（"交学费"） |
| **数据根目录** | 跨科目的东西放同一层；一次读完 | 需要新文件 |

**更关键的理由**：首页那一栏是**跨科目视图**，
要同时列出不同科目、不同书目的作业。
如果日程散落在各书目里，**凑齐一栏就得扫描整棵树**。

```python
class ScheduleStore:
    """其它日程的读写（读-改-原子写，可安全手工编辑该文件）。"""

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)

    @property
    def path(self) -> Path:
        return self.data_root / SCHEDULE_FILE      # data/schedule.json
```

**放在和 `boxes.json` 同一层**，因为它们性质相同：
都是"用户的组织方式"，不属于任何具体科目。

### 17.4 统一排序：两个来源用一套规则

两个来源要混排，所以必须有**统一的排序键**：

```python
def sort_key(done: bool, due_at: datetime | None, title: str):
    """统一排序键：**未完成在前 → DDL 早的在前 → 没 DDL 的排最后 → 名称**。

    没设 DDL 的排在有 DDL 的后面（而不是当成"很早"），
    否则一堆没时间的日程会顶到最前面，把真正临近截止的挤下去。
    """
    return (
        1 if done else 0,
        0 if due_at is not None else 1,
        due_at or datetime.max,
        (title or "").lower(),
    )
```

**这个 `sort_key` 有四个层次，每一层都有理由**：

| 层次 | 规则 | 理由 |
| --- | --- | --- |
| 1 | 未完成在前 | 已完成的不该占视线 |
| 2 | 有 DDL 的在前 | 没时间的"待办"不该挤掉有截止日期的 |
| 3 | DDL 早的在前 | 最要紧的排最上面 |
| 4 | 按名称 | 保证顺序**稳定**（否则每次刷新都在跳） |

**第 4 层容易被忽略。** 没有它，两个 `due` 相同的项每次排序结果可能不同，
界面会"自己抖"。**任何排序函数都要有"最终决定性"的兜底键。**

### 17.5 聚合：一个函数把两个来源合起来

```python
def collect_entries(library, store, now=None) -> list[AgendaEntry]:
    """把全部作业 + 全部其它日程收集成一个按 DDL 排好序的列表。"""
    entries: list[AgendaEntry] = []

    # 作业：走已有的科目/书目扫描，不在界面上自己遍历文件系统
    for subject in library.subjects(refresh=True):
        for book in getattr(subject, "books", []):
            for item in hw.list_homework(book.path):
                entries.append(AgendaEntry(
                    kind="homework", title=item.name, due=item.due, done=item.done,
                    folder=item.path, subject=subject.name, book=book.name,
                    submit_url=item.submit_url,
                ))

    for item in store.load():
        entries.append(AgendaEntry(
            kind="schedule", title=item.title, due=item.due,
            done=item.done, item_id=item.id, note=item.note,
        ))

    entries.sort(key=lambda entry: entry.sort_key())
    return entries
```

**关键设计**：引入一个 **`AgendaEntry` 中间结构**，
把两种来源"翻译"成同一种形状。这样**界面代码不用判断来源**：

```python
@dataclass
class AgendaEntry:
    kind: str            # "homework" | "schedule"
    title: str
    due: str = ""
    done: bool = False
    folder: Path | None = None      # 作业专用
    item_id: str = ""               # 日程专用
    ...
    @property
    def origin_label(self) -> str:
        """来源说明：作业显示「科目 / 书目」，日程显示「其它日程」。"""
        if self.is_homework:
            return f"{self.subject} / {self.book}" if self.subject else "作业"
        return "其它日程"
```

> **这个模式叫"适配器"或"统一视图模型"**：
> 当你要展示多个来源的同类东西时，**先翻译成统一结构，再喂给界面**。
> 界面里就永远不会出现 `if kind == "homework": ... else: ...` 这种分支。

### 17.6 完成按键：写回各自的数据源

```python
def _on_schedule_completion(self, kind: str, key: str, done: bool) -> None:
    """日程栏里的完成/取消完成。"""
    try:
        if kind == "homework":
            hw.set_done(Path(key), done)
            book = self._book_of_homework(Path(key))
            if book is not None:
                bus.emit("book_content_changed", subject=book[0], book=book[1])
        else:
            self.context.schedule.set_done(key, done)
    except Exception as exc:
        common.error(self, str(exc), "更新完成状态失败")
        return
    self.refresh_schedule()
```

**"写回各自的数据源"是关键**：完成状态不会被复制到日程数据里，
而是**改原始数据**。这样：

* 在书目页看那个作业，它也是"已完成"；
* 把作业文件夹拷到别的电脑，完成状态跟着走。

### 17.7 界面：三个按钮横排（一次真实的布局返工）

第一版每个日程把按钮**竖着排**（完成 / 打开 / 提交）。
截图发现**只显示一个按钮**，另外两个被裁掉了。

**排查**：量几何。

```
面板 300px | 行 510px | 行最小需求 510px
```

**根因**：三个按钮竖排 + QLabel 的 `sizeHint` 被当作最小宽度 →
**行的最小宽度被撑到 510px**，而面板只有 300px，
Qt 无法压缩（因为按钮和标签都是"不可压缩"的默认策略），于是内容溢出。

**修法三步**：

```python
# ① 按钮改横排（省掉一整行高度，也降低最小宽度）
buttons = QHBoxLayout()
buttons.setSpacing(4)
...
meta.addStretch(1)
meta.addLayout(buttons)

# ② 让文字标签可压缩（否则 sizeHint 就是最小宽度）
title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
due.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
origin.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

# ③ 允许整行被压缩
row.setMinimumWidth(0)
```

**修复后**（实测）：

```
窗口 1000px | 面板 336 | 视口 310 | 行 310 | 行最小需求 238 | 被裁按钮 []
窗口 1400px | 面板 405 | 视口 379 | 行 379 | 行最小需求 238 | 被裁按钮 []
窗口 1700px | 面板 480 | 视口 454 | 行 454 | 行最小需求 238 | 被裁按钮 []
```

**行宽随面板缩放，按钮永不被裁。**

**还加了测试防回归**：

```python
check("按钮是横排的（不会被面板宽度裁掉）",
      all(b.geometry().right() <= hw_row.width()
          for b in hw_row.findChildren(QPushButton)))
```

> **这一节的模式重复了 6.4 的教训**：
> Qt 里"内容被裁"几乎总是"最小宽度被某个 sizeHint 撑住"。
> **修法是让次要元素可压缩，主元素锁死。**
> 这个模式你在整个职业生涯里会反复遇到。

### 17.8 复盘

| 类别 | 内容 |
| --- | --- |
| 新数据 | `schedule.json` + `ScheduleStore` + `ScheduleItem` |
| 新中间层 | `AgendaEntry`（统一视图模型） |
| 新界面 | 首页右侧栏 + 新建/编辑日程对话框 + 完成按键 |
| 改已有 | 首页从单栏改为 `QSplitter` 双栏；`homework.json` 加 `done` 字段 |
| 学到的 | 按钮横排、`Ignored` 尺寸策略、统一排序键要有兜底 |

### 17.9 追加：日程行的 DDL 显示与行高（一次真实的"布局三连修"）

**需求**（用户两次反馈的原话）：

> 这里要显示 DDL
> 可以加高单个任务的大小

#### 第一步：DDL 根本没显示出来

现象：日程栏每行只有标题和三个按钮，看不到截止时间。

**排查**（还是"量数据"）：把行内所有 `QLabel` 的**实际宽度**打出来：

```
'2.4 作业'          geom=(41,7,329,13)
'2026-10-11 18:18'  geom=(41,22,0,32)   ← 宽度是 0！
'习概 / 书'          geom=(47,22,0,32)   ← 也是 0
按钮                 geom=(194..370)      ← Fixed 策略先分走了空间
```

**根因**：元信息和按钮在**同一个 `QHBoxLayout`** 里。
按钮设了 `Fixed` 尺寸策略（这是之前为了"按钮文字不被截断"特意加的），
布局先把宽度分给按钮，剩下的给标签 —— 而标签当时是 `Ignored`，
**"可以缩到 0"就被真的缩到 0 了**。

**这是两个正确决定撞在一起产生的 bug**：

* 决定 A：按钮要锁死宽度（6.4 节，为了让文字完整）；
* 决定 B：标签可压缩（7.4 节，为了让行能变窄）；
* 两者在同一行里同时生效 → 空间全给按钮，标签归零。

#### 第二步：修 DDL 时又踩了三个坑

| 尝试 | 做法 | 结果 |
| --- | --- | --- |
| ① | 元信息拆成独立一行，两个 `QLabel`，都用 `Ignored` | DDL 仍然 0 宽（`Ignored` = 布局可以完全忽略我的尺寸） |
| ② | 元信息标签改成 `Fixed` | DDL 显示了，但**行被撑到 583px，反过来撑破 310px 的面板** |
| ③ | 标题和元信息合并成**一个富文本 `QLabel`**（自己换行） | 行宽对了，但标签仍被压到 **37px**，只显示开头几个字 |
| ④ **最终** | 富文本标签**外面包一层 `Ignored` 容器** | ✅ 行宽由"勾选框+按钮+边距"决定（约 220px），容器把列宽全给标签 |

**为什么第 ④ 版是对的** —— 它把两个互相冲突的目标**分给了两个控件**：

```
row（QHBoxLayout）
├── QCheckBox            勾选框
├── text_holder          ← 容器：Ignored（行宽不受内容影响）
│   └── QLabel(富文本)    ← 在容器内部拿到全部列宽，自己换行
└── buttons              ← Fixed（按钮文字永不被压）
```

* **行的最小宽度**只由"勾选框 + 按钮 + 边距"决定 → 面板能自由变窄；
* **标签**在容器内部总是拿到完整列宽 → 内容永远看得见。

**第 ④ 版实测**（四个窗口宽度）：

```
窗口 1500 | 面板 434 | 视口 408 | 行 408 | 文本宽 234 | 有 DDL  OK
窗口 1400 | 面板 405 | 视口 379 | 行 379 | 文本宽 205 | 有 DDL  OK
窗口 1100 | 面板 336 | 视口 310 | 行 310 | 文本宽 136 | 有 DDL  OK
窗口  950 | 面板 336 | 视口 310 | 行 310 | 文本宽 136 | 有 DDL  OK
```

> **这一节的通用经验（比那段代码值钱）**：
>
> 1. **`QSizePolicy` 是"布局契约"，不是"外观设置"。**
>    * `Ignored`：布局**完全忽略**我的 sizeHint（我会被压到 0）
>    * `Preferred`：按 sizeHint 分配（我会**顶大**父容器的最小宽度）
>    * `Fixed`：我的宽度就是 sizeHint，不伸不缩（我会**抢走**别人的空间）
>
>    选错一个，就会出现"看不见"或"撑破"这两种对称的 bug。
>
> 2. **当两个正确决定撞车时，要"分层"而不是"改参数"。**
>    前三次都在调参数（Ignored → Fixed → Ignored），
>    第四次才想到**引入一层容器**把冲突隔开。
>    遇到"怎么调都不对"时，往往说明**缺一个结构**，而不是缺一个数值。
>
> 3. **修复要靠"真实几何数据"，不靠肉眼看截图。**
>    整个排查只用了 `label.width()` 和 `row.width()` 两个数。

#### 第三步：加高任务行

行高原来由内容决定（约 61px，三行文字挤在一起）。改法很轻：

```python
# gwp/ui/widgets/schedule_panel.py
row.setMinimumHeight(self._row_height())
layout.setContentsMargins(8, 6, 8, 6)

def _row_height(self) -> int:
    """单个任务行的最小高度。

    需求："可以加高单个任务的大小"。所以做成**可调**的：
    配置项 ``ui.schedule_row_height``（默认 76px）。
    下限 44，避免配置写了个离谱的小数字把内容挤没。
    """
    try:
        value = int(self._config.get("ui.schedule_row_height", 76) or 76)
    except (TypeError, ValueError, AttributeError):
        value = 76
    return max(44, value)
```

**三个设计点**：

1. **做成配置项而不是写死** —— 用户可能想再高或矮一点，
   而且以后要在设置界面加滑块时不用改逻辑；
2. **夹住下限（44px）** —— 配置是用户可以手改的，
   `0` 或 `"abc"` 都要能兜住；
3. **`except` 里连 `AttributeError` 都接** —— 因为控件要能脱离主程序
   单独构造（`config=None`），这样才好测。

实测：

```
配置 76px -> 实际行高 [76, 76, 76] | 首个标签宽 159 高 62
配置 92px -> 实际行高 [92, 92, 92] | 首个标签宽 159 高 78
配置 60px -> 实际行高 [60, 74, 60] | 首个标签宽 159 高 46
```

> **可调参数的三条纪律**：
> ① 一定给下限（或上限），别信配置里写的是合法值；
> ② 解析失败要走默认值，不能崩；
> ③ 让控件能脱离主程序单独构造（`config=None`），这样才好测。

#### 补充：DDL 要"单独一行 + 加粗"

用户看了上一版截图后又提了两点：

> DDL 单独一行 加粗 空间不够可以加高单个任务

**为什么"单独一行"是必要的**（不只是审美）：

上一版把「来源」和「DDL」放在同一行，用户截图里出现了这种情况：

```
高等代数 / 高等代
数  DDL 10-11
23:15
```

来源名字（`高等代数 / 高等代数`）太长换行后，把 DDL 挤到了下一行，
**看起来像排版坏了**。拆成两行之后两者互不影响 ——
这又是"两个元素抢同一行宽度"的问题，和本节主 bug **同源**。

**改法是把富文本的分行改掉，同时要处理三件事**：

```python
# 之前：标题 / 来源 + DDL（同一行）/ 备注
lines = [f"<b>{title_html}</b>", f"{origin_html} &nbsp; {due_html}"]

# 之后：标题 / 来源 / **DDL（加粗）** / 备注
lines = [f"<b>{title_html}</b>", origin_html, due_html]
```

```python
# DDL 那一行整体加粗（四种状态都要加粗）
if entry.done:
    due_html = f"<b><span style='color:{_MUTED};'>已完成</span></b>"
elif state == "overdue":
    due_html = (f"<b><span style='color:{_OVERDUE};'>"
                f"DDL {due_short}（已过期）</span></b>")
elif state == "soon":
    due_html = (f"<b><span style='color:{_SOON};'>"
                f"DDL {due_short}（即将截止）</span></b>")
...
```

**第三件事：多了一行，行高必须跟着涨。**

我把最小高度从 76 提到 88，但**没有把行高改成固定值** —— 这一点很关键：

```python
row.setMinimumHeight(self._row_height())     # 最小高度，不是固定高度
```

内容比 88px 还多时（长标题换行、有备注），**Qt 的布局会让行自动变高**，
不需要用户去改配置。实测：

```
窗口 1500 | 行高  88 | 标签 234x74  (需要高 45) | 竖裁=False
窗口 1200 | 行高 104 | 标签  85x90  (需要高 45) | 竖裁=False  ← 长标题换行
窗口 1200 | 行高 149 | 标签  85x135 (需要高 60) | 竖裁=False  ← 有备注
窗口 1050 | 行高 134 | 标签  76x120 (需要高 45) | 竖裁=False  ← 面板更窄
```

> **"最小高度 vs 固定高度"是个容易搞错的选择**：
> * `setFixedHeight` → 内容多了就被裁掉，用户看到文字消失；
> * `setMinimumHeight` → 内容多了行自己长高，永远不会裁。
>
> **绝大多数情况都该用后者。** 用固定高度的场景只有一种：
> 内容必须严格截断（比如表格里的单行摘要），而且那时也得给省略号。

#### 复盘

| 类别 | 内容 |
| --- | --- |
| 改已有 | 日程行从"三个标签 + 元信息行"改为"一个富文本标签 + 容器"；<br>DDL 从与来源同行改为独立一行并加粗 |
| 新增配置 | `ui.schedule_row_height`（默认 88，下限 44；**是最小高度，不是固定高度**） |
| 新增测试 | 11 条（DDL 可见、独立一行、加粗、三种文案、竖向不被裁、行高可调、离谱值被夹住） |
| 学到的 | `QSizePolicy` 三种策略的语义；冲突时**分层**而不是调参数；<br>优先用 `setMinimumHeight` 而不是 `setFixedHeight` |

### 17.11 追加：「即将截止」的阈值从 24 小时改为 48 小时

**需求**（用户反馈的原话）：

> 这里的 DDL 已经进入距离现在 48 小时而没有变红 我忘记了之前是多少小时变红
> 但是现在改为 48 小时内变红

**这句话里有两个值得注意的地方。**

**第一，"我忘记了之前是多少小时"** —— 用户自己都不记得阈值是多少。
这说明这个参数**在界面上是不可见的**：他只能靠"红了没有"反推。
这不是用户的问题，是设计的问题：

> **一个会定期触发的提醒阈值，应该让用户能看到它，或者能改它。**
> 看不到又改不了的阈值，用户只能靠试错去理解，而他很快就会忘掉结论。

所以正确的做法不是"记住 24 小时"，而是**把阈值集中成一个有名字、有注释、
可被引用（将来可被配置）的常量**：

```python
#: "即将到期"的判定阈值：距离 DDL 还剩不到这个时长就标黄/标红提醒。
#:
#: 需求（用户反馈）：原来是 24 小时，太紧 —— 用户看到"距现在 48 小时"的作业
#: 还是普通颜色，以为没到提醒范围。改成 48 小时，
#: 与"提前两天开始留意作业"这个实际习惯对齐。
#:
#: 作业与日程**共用**这一个常量（`schedule.py` 与日程栏都从这里取），
#: 所以改一处两边一起变 —— 不要在两处各写一个阈值，那样迟早不一致。
DUE_SOON = timedelta(hours=48)
```

**第二，"48 小时"和原来的"24 小时"是同一个东西的两个值。**
所以改之前必须先确认：**这个阈值有几处在用？**

```
homework.py:38   DUE_SOON = timedelta(hours=24)      ← 定义（只有这一处）
homework.py:149  if moment - reference <= DUE_SOON   ← 作业状态判定
schedule.py:91   if moment - reference <= DUE_SOON   ← 日程状态判定
schedule_panel.py:107  ... <= hw.DUE_SOON            ← 日程栏渲染
```

**三处都在引用同一个常量**，所以**改一行就够了**。

这正是第 26 章那条经验的体现："**同一个概念在多处出现时，
最危险的不是算法错，而是算法不一致**"。
当时那个 bug 是三处各写各的计数逻辑；这次能一行改完，
是因为当初就把阈值收成了一个常量。**同一类问题，两种做法，两种代价。**

如果当初写成三处各自 `timedelta(hours=24)`，这次就会变成
"用户说 48 小时，我改了作业的、忘了日程的" —— 而且**测试很难发现**，
因为两边的测试值（3 小时）都远小于两个阈值，改不改都通过。

**第三，测试要覆盖"反馈里的那个具体数值"。**

原来的测试用的是"2 小时 / 3 小时"这种远小于阈值的时间 ——
它在 24 小时和 48 小时下**都通过**，所以改阈值时它给不出任何信号。

修法是把阈值本身和边界值都断言进去：

```python
check("「即将截止」的阈值是 48 小时", _hw.DUE_SOON == _td(hours=48))
check("2 小时内截止状态为 soon", soon_2h.state() == "soon")
check("**30 小时内截止也算 soon**（这正是用户反馈要改的那条）",
      soon_30h.state() == "soon")
check("47 小时内截止仍是 soon", soon_47h.state() == "soon")
check("72 小时外的不算临期", far_72h.state() == "ok")
```

界面侧也补了同一个数值的用例（"30 小时后到期的作业也标黄"）。

> **通用经验：测试要包含"需求里出现过的那个具体数值"。**
>
> 用户说"48 小时"，那测试里就该有一个 48 小时附近的用例。
> 只用"2 小时"这种安全值，测的是"这个功能没坏"，
> 而不是"这个阈值是用户要的那个"。
> 前者让你在改参数时一无所知，后者才是回归保护。

**复盘**

| 类别 | 内容 |
| --- | --- |
| 改动 | `DUE_SOON` 从 24 小时改为 48 小时（**一行**，三处引用同时生效） |
| 新增测试 | 7 条（阈值本身、30/47/72 小时边界、界面标黄） |
| 同步文档 | 功能说明 / 使用说明里三处"24 小时"文案 |
| 学到的 | ①会触发的阈值要可见或可改；②阈值收成一个常量，改一处生效；<br>③测试要包含需求里出现过的具体数值 |

---

## 第 18 章　实战四：接外部数据（天气）与菜单扩展（论坛）

### 18.1 天气：需求与约束

> 日程栏目上方增设 日期-时间-天气 **（选方案一：自动获取；把地区也显示一下）**。
> 刷新频率：**只在启动时拉一次天气**。
> 显示：日期+星期、时间、天气（温度+情况）、体感/湿度/风**悬浮显示**。

**从需求里提取的技术约束**：

| 需求 | 技术含义 |
| --- | --- |
| "自动获取" | 需要联网、需要定位 |
| "只在启动时拉一次" | 不能做定时刷新 |
| "悬浮显示"细节 | 主要信息占版面，次要信息进 tooltip |
| 天气可能获取失败 | **必须能优雅失败**（断网是常态） |

### 18.2 天气数据源：先验证接口存在

**第一版犯的错**：直接按记忆写了 Open-Meteo 的"反向地理编码"接口
`https://geocoding-api.open-meteo.com/v1/reverse`。
**实测 404 —— 这个接口根本不存在。**

**教训**：

> **接第三方 API 的第一件事是"用最小脚本验证接口真的能通"，
> 而不是写完整代码再调。** 一条 `urllib` 请求几行就能验证：

```python
def probe(url, label):
    try:
        with urlopen(Request(url, headers=UA), timeout=8) as r:
            print(label, "OK", r.read()[:200])
    except HTTPError as e:
        print(label, "HTTP", e.code)      # ← 一眼看出 404
```

**改用的方案**：用已知城市名去 `/v1/search?name=Beijing&language=zh`
换中文地名。**实测可行。**

### 18.3 定位：不能只依赖一个接口

实测发现 `ipapi.co` **经常返回 403**（限流 / 数据中心 IP 被拒）。
所以必须多接口兜底：

```python
def locate(cancelled=None, deadline=None) -> tuple[float, float, str, str]:
    """按出口 IP 定位。三个免费接口依次尝试，任一成功即可。

    用多个是因为实测 ipapi.co 会返回 403（数据中心 IP / 限流），
    不能只依赖一个。
    """
    errors = []
    for url, parse in ((IP_API_PRIMARY, _parse_ipapi),
                       (IP_API_FALLBACK, _parse_ipapi_fallback),
                       (IP_API_THIRD, _parse_ipwho)):
        try:
            data = _get_json(url, cancelled=cancelled, deadline=deadline)
            result = parse(data)
            if result:
                return result
            errors.append(f"{url}: 无坐标")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("定位失败；" + "；".join(errors))
```

**注意最后那行**：`"；".join(errors)` 把所有失败原因都报出来。
如果只报最后一个，用户排查时看不到"其实是第一个接口限流了"。

### 18.4 三个必须处理的技术问题

**① 气象代码要翻译。** Open-Meteo 返回 WMO 天气代码（数字），
要转成中文：

```python
WMO_TEXT = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "有雾", 51: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 95: "雷阵雨", 96: "雷阵雨伴冰雹",
    ...
}

def wmo_text(code: int | None) -> str:
    """未知代码返回「未知天气」，不抛异常。"""
    if code is None:
        return "未知天气"
    return WMO_TEXT.get(int(code), "未知天气")
```

**未知代码兜底很重要**：气象组织会加新代码，
你的映射表永远是旧的。**兜底比穷举可靠。**

**② 地名去重。** 实测得到 `中国 · 北京市 · 北京`（`admin1` 是"北京市"，
`name` 是"北京"）。要去重：

```python
# 中文结果里 admin1 常常是"北京市"、name 是"北京"（缩写），
# 直接拼会得到「中国 · 北京市 · 北京」这种重复。短的那个被长的包含时丢掉。
pieces = []
for piece in (origin, admin, name):
    if not piece:
        continue
    if any(piece in kept or kept in piece for kept in pieces):
        continue
    pieces.append(piece)
return " · ".join(pieces)
```

**③ 不能让界面卡住。** 实测这三个接口串行要 **20 秒**。
放主线程界面会假死。所以必须放后台线程：

```python
class WeatherWorker(QThread):
    fetched = pyqtSignal(object)
    def run(self):
        try:
            result = W.query_weather(cancelled=lambda: self._cancelled)
        except Exception as exc:
            result = W.Weather(ok=False, error="天气获取失败")
        if not self._cancelled:
            self.fetched.emit(result)
```

### 18.5 一个崩溃级 bug：QThread 不能带线程析构

**现象**：加了天气线程后，测试进程**直接崩溃**
（退出码 `-1073740791` = 栈缓冲区溢出），并打印
`QThread: Destroyed while thread is still running`。

**根因分析**：

1. `QThread.quit()` 对**阻塞在 socket 上的 `urlopen` 是无效的**；
2. 所以线程会一直挂到超时（20 秒）；
3. 而窗口关闭时，如果 QThread 对象被销毁，**Qt 会直接崩溃**。

**修法（两层）**：

```python
# ① 让请求"可取消"：短超时分片轮询，每片检查一次取消标志
def _get_json(url, timeout=TIMEOUT, cancelled=None, deadline=None) -> dict:
    slice_seconds = min(timeout, 0.4)          # 每片 0.4 秒
    started = time.monotonic()
    while True:
        if cancelled is not None and cancelled():
            raise TimeoutError("已取消")
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("已超过本次查询的时间预算")
        try:
            with urlopen(request, timeout=slice_seconds) as response:
                ...
            return data
        except (TimeoutError, socket.timeout):
            if time.monotonic() - started >= timeout:
                raise TimeoutError(f"请求超时：{url}") from None
            continue                            # 这一片没读到，继续等
```

```python
# ② 关闭时先取消，再等；等不到就"挂到保活表"里别丢引用
def stop(self, *, force: bool = False) -> None:
    worker = self._worker
    self._worker = None
    if worker is None:
        return
    worker.cancel()                    # 让它 0.4 秒内自己退出
    worker.quit()
    timeout = 30_000 if force else 3000
    if worker.wait(timeout):
        return
    # 极慢网络下还没回来：别丢引用，交给模块级集合，等它自己结束
    worker.setParent(None)
    _DETACHED.add(worker)
    worker.finished.connect(lambda w=worker: _DETACHED.discard(w))
```

**效果**：

```
修复前：关闭要等 20 秒，进程退出崩
修复后：stop() 1.35 秒干净收尾，连跑 3 次零警告
```

**顺带的收获**：分片轮询让正常查询**从 20 秒降到 5 秒**——
因为最快的那个接口先返回就赢了，不用等慢的。

> **这个 bug 的通用形状**：
> **"不可中断的阻塞调用" + "可能被销毁的容器" = 崩溃。**
> 解法只有两条：让它可中断，或者保证容器活得比它久。
> 后者（保活表）是兜底，前者（可取消）才是根本。

### 18.6 论坛：及时止损也是工程能力

需求是"在独立窗口里打开论坛，不要用浏览器"。
我试了两条路：

| 方案 | 结果 |
| --- | --- |
| 手写 WebView2（Edge 内核）的 COM 互操作 | 环境创建成功，但拿到的接口指针**不可用**，进程直接崩；还缺 `WebView2Loader.dll` |
| 引入 QtWebEngine（自带 Chromium） | **能跑通**，但安装包要加约 **130MB** |

**用户的最终决定**：

> 不要按照原计划弄了 太难了 直接在浏览器打开网页就行

**最终实现**只有二十几行：

```python
def open_forum(self, title: str = "牢大CS") -> None:
    """用系统默认浏览器打开论坛。

    用浏览器打开是**最省事、最不容易出问题**的做法：
    登录态、Cookie、字体、脚本全都和用户平时上网一致，
    不用担心内嵌内核的兼容性；代价只是会多一个浏览器窗口。
    """
    url = self.forum_url("laoda_cs")
    if not shell_ops.open_url(url):
        common.warn(self, f"无法打开网址：\n{url}\n\n可以手动复制到浏览器打开。",
                    "打开论坛失败")
        return
    self.statusBar().showMessage(f"已在浏览器中打开：{title}", 4000)
```

**而"止损"的动作是完整的**：

* 卸载 `PyQt6-WebEngine` + `PyQt6-WebEngine-Qt6`（**释放 126MB**）；
* 删掉三个实验文件（`webview2.py`、`win32window.py`、`forum_window.py`）；
* **把打包配置改回"排除 QtWebEngine"**（安装包从膨胀回 83.6MB）；
* 撤掉 `app.py` 里的 WebEngine 初始化（否则主程序启动会依赖它）；
* 删掉下载的 SDK 研究资料（57MB）。

> **这一节最想教的东西：知道什么时候停。**
>
> 工程师的美德不只是"能解决问题"，还包括**判断"这个方案值不值得继续"**。
> 判断标准是三个问题：
> 1. **用户真的需要这个特性吗**（还是"浏览器打开"就够了）？
> 2. **代价**（130MB 安装包 / 每天维护）**和收益匹配吗**？
> 3. **如果继续投入，最坏情况是什么**（我可能再花一天还搞不定 COM）？
>
> **及时止损不是失败，是节省了本该浪费的资源。**
> 但止损要做干净——**把试验代码、依赖、配置全部撤掉**，
> 不留"半成品垃圾"在项目里。

### 18.7 自己动手

1. 挑一个你想接的公开 API，用**最小脚本**先验证它能通
   （状态码、字段名），再写代码。
2. 给你的网络请求加"可取消"和"总时间预算"。
3. 找一个你用"线程/异步"的地方，检查：
   **关闭时会不会带活线程析构？**
4. 回顾你手上正在纠结的一个技术方案，用 18.6 的三个问题评估一遍。

---

# 第四部分　工程质量：让它靠得住、交得出去

> 到这一部分，功能已经做完了。真正决定这个软件"能不能给人用"的，
> 是接下来的五件事：调试、测试、打包、整洁、复盘。

---

## 第 19 章　调试：没有调试器时怎么定位问题

### 19.1 现实：桌面软件的 bug 大多在现场，不在你的断点上

用户不会给你一个断点。他给你的是：

* 一张截图；
* 一句"点了没反应"；
* 或者什么都不给，只说"有时候会闪一下"。

所以调试的**真正技能是"缩小范围"**，而不是"会用调试器"。
这一章讲这个项目里用过的所有排查手法。

### 19.2 手法一：先分类，别乱猜

遇到问题先问三个问题：

| 问题 | 用途 |
| --- | --- |
| **能稳定复现吗？** | 稳定 → 逻辑错；偶发 → 时序/状态错 |
| **和上次改动有关吗？** | 有关 → 先看 diff；无关 → 可能是环境 |
| **有没有报错？** | 有 → 读栈；**没有 → 更麻烦**（静默失败） |

**"没有报错"最麻烦**，因为找不到入口。这时靠"打点"。

### 19.3 手法二：日志要"够用且不吵"

这个项目用标准 `logging`，按天分文件、按级别过滤、自动清理旧日志：

```python
def setup_logging(log_dir: Path, level: str = "INFO", keep_days: int = 14) -> None:
    """配置日志：控制台 + 滚动文件，保留 keep_days 天。"""
    handler = logging.handlers.TimedRotatingFileHandler(
        log_dir / "gwp.log", when="midnight", backupCount=keep_days,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
```

**要点**：

* **记什么**：所有"改变状态"的操作（新建、删除、改名、生成、导出）；
* **不记什么**：界面刷新的细节、每次鼠标事件（会把日志淹掉）；
* **必须记**：失败原因的**完整异常**（`exc_info=True`）。

```python
def _delete_dir(self, path: Path, to_recycle: bool) -> bool:
    ...
    log.info("删除目录：%s（回收站=%s）", path, to_recycle)    # ← 可查案
```

**这就是第 5.7 节那次数据事故能查清的原因**：
日志里有删除记录和时间戳，才能分辨"是人点的还是脚本干的"。

### 19.4 手法三：加"追踪开关"，而不是到处 print

排查拖拽 bug 时，我需要知道消息走到了哪一步。
但**不能把 print 留在代码里**（会吵、会影响性能）。
所以加一个由环境变量控制的追踪函数：

```python
_TRACE_ENABLED = bool(os.environ.get("GWP_TRACE_DRAG"))

def _trace(message: str, *args) -> None:
    """拖拽流程追踪。设 GWP_TRACE_DRAG=1 才输出。

    为什么做成开关而不是直接 print：
    * 平时零开销、零噪音；
    * 出问题时用户/我只要设一个环境变量，不用改代码重新打包。
    """
    if _TRACE_ENABLED:
        log.info("[drag] " + message, *args)
```

用的时候：

```python
def dragEnterEvent(self, event):
    _trace("dragEnter %s accepted=%s", self._title, accepted)
    ...

def dropEvent(self, event):
    _trace("drop on %s before=%s", self._title, self._drop_before)
    ...
```

**这个手法的价值**：把"加日志 → 重跑 → 删日志"的循环，
变成"设环境变量 → 重跑"。

> **更正式的做法叫"结构化日志 + 级别"**。
> 核心思想一样：**日志是产品的一部分，不是临时垃圾。**

### 19.5 手法四：用"最小复现脚本"代替"改代码试"

界面 bug 有个难点：**你要点很多下才能到达出问题的状态**。
反复手点，效率极低。

正确做法是**写一个小脚本直接构造那个状态**：

```python
# tests/_tmp_folder.py —— 临时排查脚本（用完就删）
import sys, os, tempfile
from pathlib import Path
os.environ["QT_QPA_PLATFORM"] = "offscreen"     # ← 关键：不用真的显示窗口
sys.path.insert(0, r"D:\Great White Planet\code")
from gwp.app import create_application
app = create_application(["t"])

# 造数据
tmp = Path(tempfile.mkdtemp()); os.environ["GWP_ROOT"] = str(tmp)
...
lib.create_subject("文件夹科目")
(others / "第一章").mkdir(parents=True)

# 直接调用出问题的那个方法，不用点界面
bv._on_item_double_clicked(folder_item)
print("_current_folder:", bv._current_folder)
print("表格里只剩:", [table.item(r, 0).text() for r in range(table.rowCount())])
```

**三个好处**：

1. **到达状态只要几秒**（不用点 10 下）；
2. **`offscreen` 平台**让它能在没有显示的机器上跑（也能在 CI 里跑）；
3. **打印出内部状态**，比"看界面猜"精确得多。

> **这个手法的正式版本就是"测试"**（下一章）。
> 排查时写的复现脚本，**修完 bug 后应该直接变成测试用例**。
> 这样同一个 bug 再也不会回来。

### 19.6 手法五：二分法定位"从哪一版开始坏的"

如果 bug 是"以前好用，现在坏了"，最快的办法是**找分界线**：

```
如果用的是 git：
    git log --oneline                 # 看改动列表
    git bisect start                  # 自动二分
如果没版本控制：
    凭记忆列出最近改的 5 处 → 逐个注释掉试
```

**没有版本控制时怎么办？** 这个项目在开发期没有 git，
所以用**"改一处就验证一处"**的纪律替代：
每次改完立刻跑一遍自检（`smoke_core` + `smoke_gui`），
**这样坏了一定是刚才那一次改的**。

> **这一条是"没有版本控制时最重要的自救手段"**：
> 让"改动 → 验证"的间隔足够短，短到你能记住自己刚做了什么。

### 19.7 手法六：崩溃用"退出码 + 尾部日志"定位

Python 进程崩溃（段错误）不会给栈，只有退出码。
所以必须先知道**退出码代表什么**：

```powershell
& $py script.py
Write-Output "退出码: $LASTEXITCODE"
```

| 退出码 | 含义 | 常见原因 |
| --- | --- | --- |
| `0` | 正常 | — |
| `1` | Python 异常 | 有栈可看 |
| `-1073740791`（0xC0000409） | **栈缓冲区溢出** | 底层库（Qt/COM）被误用 |
| `-1073741819`（0xC0000005） | **访问违规** | 空指针 / 野指针 |

**实战例子**（第 18.5 节那个崩溃）：

```powershell
& $py tests/smoke_gui.py > out.txt 2>&1
Write-Output "退出码: $LASTEXITCODE"      # → -1073740791
Get-Content out.txt | Select-Object -Last 12
# → QThread: Destroyed while thread is still running
```

**这一个"退出码 + 最后几行"就够了**——它直接指出了根因（线程没停就析构）。
因为 stderr 和 stdout 混在一起时**顺序会乱、内容会被截断**，
所以**一定要重定向到文件再看**。

### 19.8 手法七：怀疑"信号路由"时，先数一数

界面"点了没反应"，八成是这三件事之一：

```powershell
# ① 信号有没有接上？（declare + emit 都有，但 connect 没有 = 漏接）
Select-String -Path "gwp\ui\**\*.py" -Pattern "card_activated"

# ② 同一个信号发了两种类型？（参数类型不匹配 → 静默失败）
Select-String -Path "gwp\ui\**\*.py" -Pattern "\.emit\("

# ③ 接收方的 isinstance 判断和发送方类型对不上？
```

**第 7.4 节那个 bug**就是第 ② 类：
发送方发 `Subject` 模型，接收方判断 `BoxCard` 控件，
`isinstance` 失败 → 什么都不做。

**修完之后我加了一条纪律**：
**一个信号只发一种东西**。这条纪律可以靠测试守住：

```python
check("card_opened 发的是卡片控件",
      isinstance(captured, (SubjectCard, BoxCard)))
```

### 19.9 手法八：用"真实事件"测试，别直接调处理函数

排查"右键没反应"时，我第一版测试是这样写的：

```python
# ❌ 直接调处理函数 —— 这样测不出"信号没接上"
view._on_item_context(item, pos)
```

它能通过，但用户那边仍然没反应。**因为这个测试绕过了信号机制。**

正确的测试要**发真实的 Qt 事件**：

```python
# ✅ 构造真实的右键事件，让它走完整的信号路由
event = QContextMenuEvent(
    QContextMenuEvent.Reason.Mouse, QPoint(10, 10), global_pos
)
view.table.viewport().contextMenuEvent(event)
```

**这条经验极其重要**：

> **测试要尽量靠近"用户真正做的动作"。**
> 直接调用内部函数，会绕过所有"胶水代码"——
> 而 bug 恰恰最爱藏在胶水里（信号连接、事件过滤、类型转换）。

### 19.10 自己动手

1. 给你的项目加一个"追踪开关"（环境变量控制），
   在关键流程上打点。
2. 找最近的一个 bug，**写出最小复现脚本**，然后把它变成测试。
3. 造一次崩溃（故意在有线程运行时退出），
   用"退出码 + 尾部日志"来定位。
4. 检查你的测试：**有多少是"直接调内部函数"的？**
   把它们改成"发真实事件"。

---

## 第 20 章　测试：怎么让"我改完了"变成"我知道它是对的"

### 20.1 先破除一个误解：测试不是"证明没 bug"

测试**不能证明没有 bug**。它能做的是：

* **防止回归**：这次修好的 bug，下次不会复活；
* **暴露设计的坏味道**：如果一个功能"没法测"，说明它和别的东西耦合太紧；
* **当文档**：测试名就是"这个功能应该做什么"的清单；
* **给你改代码的勇气**：有测试，你才敢重构。

**这个项目的测试有 900 多条断言**（395 + 508）。
它们不是"为了覆盖率"，而是**每一条都对应一个真实的功能点或踩过的坑**。

### 20.2 结构：三层，各管一段

```
tests/
├── lint_report.py     静态检查：未使用的 import、过长的函数、可疑写法
├── smoke_core.py      核心自检：不启动界面，跑数据层/AI 层/服务层（395 条）
└── smoke_gui.py       界面自检：真建窗口（offscreen），跑界面逻辑（508 条）
```

**为什么分两层而不是一个文件？**

| 层 | 能测出什么 | 跑得多快 | 什么时候跑 |
| --- | --- | --- | --- |
| `smoke_core` | 数据/逻辑错 | 快（几秒） | **每次改动后** |
| `smoke_gui` | 界面/信号/布局错 | 慢（10~20 秒） | 提交前 |
| `lint_report` | 代码卫生 | 极快 | 每次改动后 |

**"分层的意义在于跑得起"**：如果一个测试要 5 分钟，
你就不会每次都跑，它就失去了意义。

### 20.3 断言要"自带解释"

看两条对比：

```python
# ❌ 失败时只知道"不对"，不知道为什么
check("书目页标签正确", tabs == expected)

# ✅ 失败时直接看到实际值和期望值
check("书目页有 8 个标签",
      window.book_view.tabs.count() == 8,
      str(window.book_view.tabs.count()))
```

**这个项目的 `check` 函数**：

```python
def check(label: str, condition: bool, detail: str = "") -> None:
    """记录一条断言。失败时把 detail 一起打出来。"""
    if condition:
        print(f"[PASS] {label}")
    else:
        FAILURES.append(label)
        print(f"[FAIL] {label}" + (f" -> {detail}" if detail else ""))
```

**"detail 参数"是这套测试最有用的设计**。
失败输出长这样：

```
[FAIL] 标签顺序：AI 总结在最前，练习紧随笔记 -> ['AI 总结', '简介', '笔记', '练习', ...]
```

**一眼就知道期望和实际差在哪**，不用回去加 print 重跑。

### 20.4 界面测试的关键：offscreen 平台

界面测试最大的障碍是"要开窗口"。解决办法是 Qt 的 **offscreen 平台**：

```python
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"     # 渲染到内存，不显示
from PyQt6.QtWidgets import QApplication
app = QApplication(["gwp-test"])
```

**这样测试可以在没有桌面的环境里跑**（CI、远程机器）。

**但 offscreen 有三个已知限制**（踩过才知道）：

| 限制 | 表现 | 应对 |
| --- | --- | --- |
| QSS 背景色不生效 | `grab()` 出来的图没有样式背景 | 用"表格像素采样"而不是 `grab()` |
| 没有真实字体度量差异 | 极端字号下的问题测不出 | 显式设置字号再测 |
| 模态对话框会阻塞 | 测试卡死 | **打桩**（见 20.5） |

### 20.5 打桩：让测试不依赖"人点确定"

模态对话框（`QMessageBox`、`QDialog.exec()`）会阻塞，
测试里必须**替换掉**：

```python
def install_dialog_stubs() -> None:
    """把模态对话框替换成"自动回答"。"""
    real_exec = QMessageBox.exec
    QMessageBox.exec = lambda self: QMessageBox.StandardButton.Yes
    DIAG_LOG.append(("QMessageBox", self.text()))
```

**注意"记录调用"这一步**（`DIAG_LOG.append`）。
这让测试能验证"确实弹了正确的提示"，
而不只是"没有卡住"。

**打桩要打在"使用点"上**（这个坑我踩过）：

```python
# ❌ 打桩打在模块定义处 —— 没用，因为 worker 里用的是它自己 import 的那份绑定
_W2.query_weather = lambda: FakeWeather()

# ✅ 打桩打在使用点
from gwp.ui.widgets import clock_bar as _clock_mod
_clock_mod.W.query_weather = lambda: FakeWeather()
```

> **打桩原则**：**打到"谁在调用它"的那一层。**
> Python 的 `import` 是绑定名字，改定义处的名字不影响已绑定的引用。

### 20.6 测试的"确定性"：不许有时序依赖

一个测试如果"跑两次结果不同"，它比没有测试更糟（会让人不信任测试）。
这个项目遇到过的三种不确定性：

**① 时间相关**：测试在 23:59 跑和 00:01 跑结果不同。

```python
# ❌ 依赖真实当前时间
due = datetime.now() + timedelta(days=3)

# ✅ 造一个明确的未来时间
due = "2030-12-31T23:59"
```

**② 排序相关**：字典/集合的顺序不稳定。

```python
# ❌ 假定顺序
check("列出全部", [x.name for x in items] == ["甲", "乙", "丙"])

# ✅ 比较集合，或用 sorted
check("列出全部", sorted(x.name for x in items) == sorted(["甲", "乙", "丙"]))
```

**③ 异步相关**：线程/定时器还没跑完就断言。

```python
# ✅ 轮询等待，不写死 sleep
for _ in range(200):
    app.processEvents()
    time.sleep(0.01)
    if clock._worker is None:
        break
check("后台线程抓完后被清理", clock._worker is None)
```

**最后一条我特意连跑三次验证稳定**：

```
第 1 次: FAIL=0 QThread警告=0
第 2 次: FAIL=0 QThread警告=0
第 3 次: FAIL=0 QThread警告=0
```

> **偶发失败的测试是最危险的**——它会训练你"忽略失败"。
> 遇到偶发失败，**宁可删掉这条断言，也不要留着**，
> 然后去找到底是时序问题还是真的 bug。

### 20.7 测试要覆盖"边界"，不只是"正常路径"

看这个项目的边界测试清单（每一条都对应一个真实坑）：

```python
check("空 DDL 解析为 None", _hw.parse_due("") is None)
check("无法识别的时间返回 None", _hw.parse_due("下周三") is None)
check("非网址文本被拒绝", not _hw.is_valid_url("随便一段文字"))
check("危险协议被拒绝", not _hw.is_valid_url("file:///C:/Windows/system32"))
check("空提交方式允许（可以不填）", _hw.is_valid_url(""))
check("漏写协议的网址会被补全", _hw.normalize_url("a.edu/x") == "https://a.edu/x")
check("重名不会覆盖已有文件夹", len(list(folder.glob("课件资料*"))) == 1)
check("非法名称（含斜杠）被拒绝", not any("a_b" == p.name for p in folder.iterdir()))
check("取消输入时不创建任何东西", len(list(folder.iterdir())) == 1)
check("普通文件夹不会被误认成作业", _hw.load(folder / "老师发的资料") is None)
check("已有内容文件不会被覆盖", "我自己改过的内容" in content_path.read_text())
```

**边界的四个方向**（缺一个就会有 bug 漏到用户那里）：

| 方向 | 例子 |
| --- | --- |
| **空** | 空字符串、空列表、没有 DDL |
| **非法** | 含 `/` 的名字、无法解析的时间、危险协议 |
| **重复** | 重名文件、重复点击新建 |
| **竞态** | 取消操作、线程还在跑、文件被外部删掉 |

### 20.8 把纪律变成自动检查

第 3.5 节说过"数据层不许 import Qt"。这条纪律**不能靠自觉**，
要靠自动检查：

```python
# tests/lint_report.py 里
LAYER_RULES = (
    ("gwp/data_manager", ("PyQt6",), "数据层不允许依赖 Qt"),
    ("gwp/ai", ("PyQt6",), "AI 层不允许依赖 Qt（worker.py 除外）"),
    ("gwp/services", ("PyQt6",), "服务层不允许依赖 Qt"),
)

for folder, forbidden, message in LAYER_RULES:
    for path in Path(folder).rglob("*.py"):
        if path.name == "worker.py":            # 唯一允许的例外
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if any(line.startswith(f"from {f}") or line.startswith(f"import {f}")
                   for f in forbidden):
                issues.append(f"{path}: {message}")
```

**这个检查跑一次不到一秒，但它守住的是整个架构。**

`lint_report.py` 还检查：

* **未使用的 import**（会让代码显得不可信，也是重构残留的信号）；
* **过长的函数**（超过阈值就提示拆分）；
* 可疑写法（`except:` 裸捕获、可变默认参数等）。

> **"自动检查"是让纪律能活下来的唯一方式。**
> 写在文档里的规则三个月后就没人记得；
> 写在 CI/自检脚本里的规则会一直生效。

### 20.9 自己动手

1. 给你项目写一个 `check(label, condition, detail)` 风格的极简测试框架
   （不用 pytest 也能开始）。
2. 给你最核心的 3 个函数，各写 **4 条边界测试**（空/非法/重复/竞态）。
3. 把你的架构纪律（比如"某层不许依赖某库"）写成自动检查。
4. 找出你所有"偶发失败"的测试，**要么修到稳定，要么删掉**。

---

## 第 21 章　打包与交付：让别人也能用上

### 21.1 交付的三个硬约束

这个项目的交付要求是：

| 约束 | 含义 |
| --- | --- |
| **目标电脑可能没有 Python** | 必须自带运行时 |
| **不能要求管理员权限** | 装到用户目录 |
| **不能带走用户数据** | 安装包只含程序，不含 `data/` |

**第一条最硬**。它直接决定了技术方案：**必须打包成"自带解释器"的形式**。

### 21.2 PyInstaller：`--onedir` 还是 `--onefile`

| 方案 | 好处 | 坏处 |
| --- | --- | --- |
| `--onefile` | 单文件，好传 | **启动慢**（每次解压到临时目录）、**杀软敏感**、本机实测**静默失败** |
| `--onedir` | 启动快、稳定、便于排查 | 一个目录，文件多 |

**本项目的实测结论**：`--onefile` 在这台机器上**静默失败**
（退出码 `-1`，没有任何输出）。所以选 **`--onedir`**。

> **教训**：打包工具的行为**受本机安全软件、系统策略影响**。
> 别人说"能用"不代表你能用。**必须自己实测一遍**，
> 而且要看**退出码和输出**——静默失败最难查。

### 21.3 spec 文件：把"要带什么"写清楚

PyInstaller 的 `.spec` 就是构建脚本。关键是三块：

```python
# ① 显式声明"运行时按需导入"的模块
#    静态分析看不到它们（因为是动态 import 或插件发现的）
HIDDEN = [
    "gwp.ai.providers",                    # pkgutil 动态发现
    "gwp.services.markdown_renderer",      # PEP 562 惰性导入
    "docx", "pptx", "openpyxl", "pymupdf", # 按需导入的文档解析库
    "markdown", "pygments",                # 导出 PDF 用
    ...
]

# ② 排除体积大且用不到的东西
EXCLUDES = [
    "tkinter", "unittest", "numpy", "matplotlib", "pandas",
    "PyQt6.QtWebEngineCore",               # 内嵌浏览器方案已放弃
    "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtMultimedia", ...
]

# ③ 随包资源：图标 + 文档
datas = []
if resources.is_dir():
    datas.append((str(resources), "gwp/resources"))
for name in DOC_FILES:
    datas.append((str(document / name), "Document"))
```

**三个坑**：

1. **`numpy` 排除掉后，某个库可能仍然偷偷 import 它** → 启动就崩。
   这个项目遇到过：`gwp/resources/__init__.py` 里 **eager import**
   导致加载图标时连带加载 numpy。
   修法是**惰性导入**（PEP 562）：

```python
# gwp/resources/__init__.py
def __getattr__(name: str):
    """PEP 562：按需加载资源，避免启动时把所有依赖都拖进来。"""
    if name in ("planet_icon", "planet_pixmap"):
        import importlib
        module = importlib.import_module("gwp.resources.icons")
        return getattr(module, name)
    raise AttributeError(name)
```

**注意必须用 `importlib.import_module`，不能写
`from gwp.resources import icons`** —— 后者会**递归调用 `__getattr__`**，
直接死循环（这个坑我也踩了）。

2. **`console=False` 后不能再用 `print`**。
   Windows 的 GUI 程序没有 stdout，`print` 会抛
   `AttributeError` 或干脆静默挂住。修法是所有输出走日志/对话框：

```python
def say(message: str) -> None:
    """代替 print。GUI 程序里 print 没有输出去，还可能直接报错。"""
    try:
        print(message)
    except Exception:
        pass
    log.info(message)
```

3. **`os.startfile` / 子进程要小心冻结环境**。
   冻结后 `sys.executable` 是"你的 exe"，
   所以"用 `sys.executable` 起一个 Python 子进程"会变成**递归启动自己**。
   要改用 `sys._MEIPASS` 或显式路径。

### 21.4 安装器：用 tkinter 写一个"无依赖"的 GUI

**为什么不用 Inno Setup / NSIS？** 因为它们需要额外下载安装，
而且这个项目要"零构建依赖"。

**为什么用 tkinter？** 因为它是 Python 标准库自带的 GUI，
**打包进 exe 后不需要任何额外组件**。

安装器的核心逻辑：

```python
# code/installer/installer.py
def payload_path() -> Path:
    """找到随包的程序压缩包。

    注意顺序：打包后的安装器把 payload.zip 放在 sys._MEIPASS 里，
    直接跑源码时它在脚本旁边。
    """
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidate = Path(meipass) / "payload.zip"
        if candidate.is_file():
            return candidate
    return Path(__file__).resolve().parent / "payload.zip"
```

**安装器要处理的现实问题**：

| 问题 | 做法 |
| --- | --- |
| 装到哪 | 默认 `%LOCALAPPDATA%\Programs\Great White Planet`（**不需要管理员**） |
| 要不要快捷方式 | 问用户（复选框） |
| 静默安装 | 支持 `--silent --dir <路径> --no-shortcut`（便于自动化） |
| 卸载 | 写 `uninstall.json` 记录装了什么，并生成"卸载 xxx.exe" |
| **卸载绝不动数据** | 只删程序目录，`data/` 一律保留 |

**"卸载不动数据"这一条必须在文档里写清楚**，
因为用户最大的恐惧就是"卸载会不会把我资料删了"。

### 21.5 交付前的"验收脚本"：把"应该没问题"变成"验证过"

交付前最怕"在我机器上没问题"。所以写了一个**验收脚本**，
它真的装一遍、跑一遍、卸一遍：

```python
# code/installer/acceptance.py
# [验收 1/4] 检查安装包内容
#   OK  主程序 / 卸载器 / 安装记录 / 说明书 PDF / 三份 MD
#   OK  无 data 目录
#   OK  不含需求设计文档
#   OK  不含用户数据文件
# [验收 2/4] 静默安装到临时目录
# [验收 3/4] 启动安装好的程序
#   OK  进程存活: True
#   OK  自带运行时 python310.dll
#   OK  无 PYTHONPATH 也能启动
#   OK  自动创建 user data / else data
# [验收 4/4] 静默卸载
#   主程序已删除: True
#   用户数据保留: True
```

**这个脚本最大的价值是"证明不需要 Python"**。
做法是**临时把系统 Python 改名**，再用**清空环境变量**的方式启动：

```python
# code/installer/verify_no_python.py
# 1) 把 D:\Python\Python310 改名（让系统找不到 Python）
# 2) 用最小的环境变量（去掉 PYTHONPATH、PYTHONHOME）启动安装好的程序
# 3) 检查进程是否存活、日志有没有报错
# 4) 把 Python 改回来
```

> **"验收"和"测试"的区别**：
> * 测试验证**代码逻辑**对不对；
> * 验收验证**交付物**能不能用。
>
> 两者都要有。很多团队测试很全，但**交付物从没在干净环境里装过一遍**，
> 结果用户那边一装就是错。

### 21.6 交付清单

每次交付，这个项目都会检查这几样：

| 项目 | 检查方式 |
| --- | --- |
| 安装包能装、能跑、能卸 | `acceptance.py` |
| 目标机没有 Python 也能跑 | `verify_no_python.py` |
| 包里**不含**用户数据 | `acceptance.py` 里显式断言 |
| 文档是最新的 | 文档与代码一起改（见第 23 章） |
| 包体大小合理 | 打印实际 MB，异常增长就查原因 |

### 21.7 自己动手

1. 用 PyInstaller 把你的程序打成 `--onedir`，**在另一台没装运行环境的机器上试**。
2. 列出你项目里所有"动态导入"的模块，把它们加进 `hiddenimports`。
3. 写一个"干净环境验收脚本"：
   清空环境变量、用最简 PATH 启动，看能不能跑。
4. 检查你的安装/卸载：**会不会动用户数据？** 在界面上明确告知。

---

## 第 22 章　让代码保持整洁：纪律与自动化

### 22.1 "整洁"不是审美问题，是维护成本问题

看两段功能一样的代码：

```python
# A
def f(s, t):
    r = []
    for x in s:
        if x.t == t:
            r.append(x)
    return r

# B
def books_of_type(subject, subject_type):
    """取出某科目下指定类型的书目。"""
    return [b for b in subject.books if b.subject_type == subject_type]
```

**B 更好不是因为"好看"，而是因为**：

* 三个月后你能看懂 B；
* B 的名字能被搜索到（A 的 `f` 搜不出来）;
* B 的意图可以写成测试（"类型过滤"），A 不行。

### 22.2 命名：最容易做对、也最容易忽视

这个项目的命名约定：

| 种类 | 约定 | 例子 |
| --- | --- | --- |
| 模块 | 小写下划线 | `data_manager/boxes.py` |
| 类 | 大驼峰 | `ScheduleStore` |
| 函数/方法 | 小写下划线，**动词开头** | `collect_entries`、`list_homework` |
| 常量 | 全大写 | `SUMMARY_SOURCE_DIRS` |
| 布尔 | `is_/has_/can_/should_` | `is_frozen`、`can_use_recycle_bin` |
| 私有 | 前导下划线 | `_next_home_order` |

**两条最实用的命名经验**：

1. **函数名要能回答"它做了什么"**。
   `handle_data` ❌ / `list_homework_items` ✅
2. **布尔变量不要用否定**。
   `not_disabled` ❌ 双重否定读起来费脑 / `enabled` ✅

### 22.3 注释：写"为什么"，不写"是什么"

```python
# ❌ 废话注释
# 把 subjects 排序
subjects.sort(key=...)

# ✅ 有价值的注释：解释"为什么是这个顺序"
# 排序键四层，每层都有理由：
#   1. 未完成在前 —— 已完成的不该占视线
#   2. 有 DDL 的在前 —— 没时间的"待办"不该挤掉有截止日期的
#   3. DDL 早的在前 —— 最要紧的排最上面
#   4. 按名称 —— 保证顺序**稳定**（否则每次刷新都在跳）
subjects.sort(key=...)
```

**这个项目的注释有一条额外要求：踩过的坑要留在代码旁边。**

```python
# 注意：PyQt6 的 QThread.wait(-1) 会 OverflowError（无符号整数），
# 所以"无限等"用一个足够大的毫秒数。
timeout = 30_000 if force else 3000
```

```python
# 注意末尾是 bde7f68c —— 第一版写成了 bdEF3B68（错一位）。
# 现在 QueryInterface 按 IID 严格分派，写错会明确报"不支持该接口"而不是崩。
IID_CTRL_COMPLETED = "{6C4819F3-C9B7-4260-8127-C9F5BDE7F68C}"
```

> **"为什么"的注释有三种最有价值**：
> ① **反直觉的决定**（为什么不这么做）；
> ② **踩过的坑**（防止后人改回去）；
> ③ **外部约束**（"这个值必须 ≤ 3，因为旧版数据…"）。

### 22.4 函数长度与参数数量

**经验阈值**（不是硬指标）：

| 指标 | 舒适 | 警觉 | 该动手 |
| --- | --- | --- | --- |
| 函数行数 | < 30 | 30–60 | > 60 |
| 参数个数 | ≤ 3 | 4–5 | > 5 |
| 嵌套深度 | ≤ 3 | 4 | > 4 |
| 圈复杂度 | < 10 | 10–15 | > 15 |

**参数超过 5 个时的常见解法**：收成一个 dataclass。

```python
# ❌ 参数太多，调用方要记顺序
def create_homework(name, content, due, submit_url, subject, book, notify=True):

# ✅ 用对象
@dataclass
class HomeworkDraft:
    name: str
    content: str = ""
    due: str = ""
    submit_url: str = ""

def create_homework(draft: HomeworkDraft) -> Homework:
```

**好处**：加字段不改函数签名；调用方可以用关键字参数、有默认值。
这个项目的 `BookItem`、`AgendaEntry`、`Homework`、`PDFExportOptions`
都是这个用法。

### 22.5 静态检查：让工具替你盯

`lint_report.py` 检查的东西（每一条都对应一种真实问题）：

| 检查 | 为什么 |
| --- | --- |
| 未使用的 import | 重构残留，让人怀疑代码可信度 |
| 太长的函数 | 难测试、难复用 |
| `except:` 裸捕获 | 会吞掉 `KeyboardInterrupt`，调试时想哭 |
| 可变默认参数 `def f(x=[])` | 经典的 Python 陷阱 |
| **分层依赖违规** | 守住架构 |

**运行结果**：

```
检查了 88 个文件，共 0 处提示。
```

**为什么要求"0 提示"？** 因为**"有 3 个已知问题"会变成"有 30 个"**。
一旦容忍噪音，就再也看不出新问题。

> **这条经验叫"破窗效应"**：
> 允许少量的坏味道存在，坏味道就会快速增长。
> **要么清零，要么明确写进白名单并说明理由。**

### 22.6 一个"零依赖"的实用原则

这个项目有个贯穿始终的选择：**尽量不引入第三方库**。

| 需求 | 选择 | 理由 |
| --- | --- | --- |
| 文件送回收站 | 直接调 Windows API（`ctypes`） | 少一个依赖，行为可控 |
| 差异对比 | 标准库 `difflib` | 够用，不值得引库 |
| 天气数据 | 标准库 `urllib` | 为一个天气条引 `requests` 不值 |
| 事件总线 | 自己写 30 行 | 比引入框架更可控 |
| 安装器 GUI | 标准库 `tkinter` | 打包后零额外依赖 |

**判断标准**（引入依赖前问三个问题）：

1. **它解决的问题占我项目的多大比例？**（只用一个函数 → 自己写）
2. **它会不会引入新的传递依赖？**（会 → 谨慎）
3. **打包后它增加多少体积、有没有平台限制？**

**但这条原则不能走极端**：该用的还是要用。
这个项目引入了 `PyQt6`（GUI）、`PyMuPDF`（PDF）、
`markdown` + `pygments`（渲染）、`python-docx` 等（文档解析）——
因为这些自己写不划算。

> **"少依赖"的真正含义是"每一个依赖都是深思熟虑的结果"**，
> 不是"越少越好"。

### 22.7 自己动手

1. 给你的项目写一个 `lint_report`，先加三条检查
   （未用 import、函数过长、裸 except）。
2. 找三个"名字看不出在干什么"的函数，改名成动词短语。
3. 挑一个参数超过 5 个的函数，用 dataclass 重构。
4. 检查你项目里的依赖，**每一个都写一句"为什么需要它"**。
   写不出理由的就删掉。

---

## 第 23 章　踩坑清单与工程心法

这一章是全书经验的浓缩。**建议你隔一段时间翻一次。**

### 23.1 数据与状态（最贵的错误）

| # | 坑 | 症状 | 心法 |
| --- | --- | --- | --- |
| 1 | 非原子写文件 | 断电/崩溃后文件损坏，旧数据也没了 | **临时文件 + 原子替换** |
| 2 | 缓存未失效 | "重启一下就好了" | **全局生成号**，写操作自动作废 |
| 3 | 返回共享对象 | 缓存被调用方改坏 | **对外返回深拷贝** |
| 4 | 元数据读取遇错就崩 | 用户手改错一个逗号，科目消失 | **读取永不抛异常，用默认值** |
| 5 | 同一个"顺序"字段被两个坐标系使用 | 拖了没效果 / 顺序自己跳 | **一个字段只属于一个坐标系** |
| 6 | 局部操作做了全局重编号 | "我只改了一点点，为什么全变了" | 明确 `absolute=True` 这类模式 |
| 7 | 默认值"不安全" | 新目录悄悄参与 AI 总结 | **默认选"出错影响最小"的那个** |
| 8 | 把"不存在"和"不合法"混为一谈 | 用户第一次设置的新目录被忽略 | **区分两者** |
| 9 | 先删源再复制 | 复制失败时文件没了 | **copy-then-delete** |
| 10 | 覆盖用户文件 | 数据丢失，不可挽回 | **同名自动改名** |

### 23.2 界面与 Qt

| # | 坑 | 症状 | 心法 |
| --- | --- | --- | --- |
| 11 | 按钮被压扁 | 文字截断成「导入文」 | **锁死主元素宽度，让次要元素可压缩**（`Ignored` 策略） |
| 12 | 行最小宽度被 sizeHint 撑住 | 面板变窄后内容溢出被裁 | **文字标签设 `Ignored`，行 `setMinimumWidth(0)`** |
| 13 | 按下就发 clicked | 一按卡片就展开，没法拖 | **`mouseRelease` 且 `not _dragged` 才发** |
| 14 | 拖拽用 `text/plain` | 从记事本拖文字也当成科目 | **自定义 MIME 类型** |
| 15 | 信号参数类型不匹配 | "点了没反应"，无报错 | **一个信号只发一种东西** |
| 16 | 信号发了没人接 | "点了没反应" | `Select-String` 数一遍 connect |
| 17 | 直接调处理函数做测试 | 测试通过，用户还是没反应 | **发真实事件** |
| 18 | 程序改控件触发信号 | 递归刷新、卡死 | **`blockSignals`** |
| 19 | 改 QSS 依赖的属性没重套样式 | 要重启才生效 | **`unpolish` + `polish`** |
| 20 | 模态对话框在测试里阻塞 | 测试卡死 | **打桩（打在使用点）** |
| 21 | QSS 背景在 `grab()` 里不生效 | 像素测试误报 | 用表格采样，别用 `grab()` |
| 22 | `QApplication([])` 空 argv | 某些组件拒绝初始化 | 至少传一个程序名 |

### 23.3 线程与网络

| # | 坑 | 症状 | 心法 |
| --- | --- | --- | --- |
| 23 | 长任务放主线程 | 界面假死 | 后台线程 + 流式反馈 |
| 24 | `QThread.quit()` 对阻塞 socket 无效 | 关闭要等 20 秒 | **请求可取消（分片轮询）** |
| 25 | QThread 带线程析构 | **进程崩溃**（0xC0000409） | 先取消、再 `wait`，超时就保活 |
| 26 | 只依赖一个第三方接口 | 403/404 就全废 | **多接口兜底 + 完整错误汇总** |
| 27 | 按记忆写接口地址 | 404 才发现接口不存在 | **先写最小脚本验证** |
| 28 | 无限重试 | 断网时疯狂请求 | **总时间预算 + 明确失败态** |
| 29 | 静默降级 | 用户以为在用 A，其实在用 B | **状态可见** |

### 23.4 流程与协作

| # | 坑 | 症状 | 心法 |
| --- | --- | --- | --- |
| 30 | 需求没问清就开工 | 做一半返工 | **提问：给选项、问边界、问可验证的东西** |
| 31 | 需求写死在代码里 | 改一个功能要动十处 | **声明表驱动** |
| 32 | 默认参与（黑名单） | 新东西悄悄影响老功能 | **白名单** |
| 33 | 没有版本控制 | 出 bug 不知道改坏了什么 | **短"改动→验证"间隔**，或上 git |
| 34 | 测试偶发失败 | 训练你忽略失败 | **要么修到稳定，要么删掉** |
| 35 | 交付物没在干净环境装过 | 用户一装就错 | **验收脚本 + 无 Python 验证** |
| 36 | 文档和代码脱节 | 用户按文档做却发现功能变了 | **改代码时同步改文档** |
| 37 | 不肯止损 | 在一个方案上耗掉大量时间 | **评估"值不值得继续"** |
| 38 | 止损不彻底 | 项目里留下半成品和多余依赖 | **连依赖、配置、实验代码一起清** |

### 23.5 五条最值钱的工程心法

如果这本书你只记住五句话，我希望是这五句：

**心法一：让下一次修改便宜。**
> 评判代码的标准不是"现在能不能跑"，而是"需求变了要改几个文件"。
> 改 1 个文件是设计得好，改 10 个是该重构了。

**心法二：数据比代码重要。**
> 界面丑可以改，逻辑错可以修，**数据丢了就没了**。
> 所有"写盘"都要原子，所有"删除"都要能后悔，
> 所有"读取"都要能容错。

**心法三：一次只改一件事，改完立刻验证。**
> 这是没有版本控制时最重要的自救手段，
> 也是有了版本控制时最省时间的习惯。

**心法四：把"看起来对"变成"验证过"。**
> 量数据、写复现脚本、加断言、跑验收。
> "应该没问题"和"我知道它是对的"之间，隔着的是所有这些小动作。

**心法五：知道什么时候停。**
> 该做的功能要做完；不值得的方案要立刻放弃，并且**清干净**。
> 判断标准永远是：用户真的需要吗、代价配得上收益吗、
> 继续下去最坏会怎样。

### 23.6 关于"少 AI 辅助"下的开发

最后回到这本书的立意。经过这 23 章，你应该能看出：

**AI 最擅长的地方**：
* 写样板代码（一个 dataclass、一个对话框的骨架）；
* 解释一个陌生的 API；
* 把一段逻辑翻译成另一种写法；
* 查"这个报错是什么意思"。

**AI 最不擅长、也不该替你决定的地方**：

| 事情 | 为什么 AI 替不了 |
| --- | --- |
| **需求澄清** | 只有你知道用户的真实处境和隐含约束 |
| **架构取舍** | 取决于你的维护周期、团队规模、性能要求 |
| **数据设计** | 出错代价最大，必须自己想清楚"什么绝不能坏" |
| **边界与异常** | AI 默认写"正常路径"，边界要你主动要求 |
| **验收标准** | "什么算做完了"是你的判断，不是 AI 的 |
| **取舍与止损** | 涉及成本、时间、风险的权衡 |

**所以真正的技能结构是这样的**：

```
       ┌─────────────────────────────┐
       │  判断力（决定做什么、不做什么）│  ← 你自己，经验积累
       ├─────────────────────────────┤
       │  工程方法（怎么保证做对）      │  ← 这本书的主要内容
       ├─────────────────────────────┤
       │  编码能力（把想法变成代码）    │  ← 可以借助 AI 加速
       └─────────────────────────────┘
```

**AI 让最底下那层变快了，所以中间和上面那两层的重要性反而上升了。**

一个只会写代码的人，在 AI 时代会变得很便宜；
一个能判断"该写什么、怎么保证对、什么时候停"的人，会变得更值钱。

**这本书想帮你成为后者。**

---

## 第 24 章　后期追加的三个需求（人设一致性与输入体验）

项目交出去之后，需求还在来。这一章讲最后三条：**助手改名**、
**日期时间不要手打**、以及一个顺带暴露出来的**配置升级机制**。

### 24.1 需求：助手要自称「长庚」

> 软件里的所有 AI 助手要自称长庚，不要叫大白星球，那是太白金星

**先说这句需求里的知识**（很有意思）：

金星在中国古称**启明**（晨见东方）与**长庚**（昏见西方），
《诗经》「东有启明，西有长庚」说的就是它；
而**太白**也是金星 ——《史记·天官书》「太白者，西方之金也」。
所以 **Great White Planet ＝ 太白，助手 ＝ 长庚**：一个名字给产品，一个给助手。

**技术上其实是个"提示词一致性"问题**。原来的提示词是这样写的：

```python
SUMMARY_SYSTEM_PROMPT = """你是 Great White Planet 学习软件的「学习资料整合专家」。
```

模型看到「你是 Great White Planet 学习软件…」，**会把软件名当成自己的名字**。
所以用户问"你是谁"，它答"我是大白星球"。

**修法的关键决定：名字抽成常量，不要写 7 遍。**

```python
# gwp/core/constants.py

#: AI 助手的自称（需求：软件里的所有 AI 助手都自称「长庚」，不要叫「大白星球」）。
#:
#: 为什么不直接写进每段提示词里：
#: * 「长庚」是**人设名**，将来要改只改这一处；
#: * 提示词本身是「能力描述」，两者分开更好维护；
#: * 测试可以断言"每段提示词都带上了这个名字"。
AI_ASSISTANT_NAME = "长庚"

SUMMARY_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件的学习助手，现在担任「学习资料整合专家」。
...
9. 用户问起你是谁时，自称「{AI_ASSISTANT_NAME}」；不要把软件名当成你的名字。
"""
```

**7 段提示词全部改成 f-string 引用常量**，并且每段都补一句
"不要把自己叫成软件名"。

**还写了一条断言守住它**：

```python
prompt_names = [n for n in dir(C)
                if "PROMPT" in n and isinstance(getattr(C, n), str)]
check("每段 AI 提示词都自称「长庚」",
      all(C.AI_ASSISTANT_NAME in getattr(C, n) for n in prompt_names))
check("没有任何提示词把软件名当成助手名字",
      all("大白星球" not in getattr(C, n) for n in prompt_names))
```

> **为什么值得为一句"称呼"写测试**：
> 它属于**人设一致性**，散在 7 段提示词里，靠人眼看一定会漏；
> 而它又是用户**最先感知到**的东西 —— 助手开口第一句就是说自己是谁。
>
> **凡是"多处必须保持一致"的东西，都要用断言或常量强制，不能靠记性。**

**踩到的一个小坑**：我第一版在 `DAILY_CHAT_SYSTEM_PROMPT` 里写了
「不要把自己叫作『大白星球』」，结果断言"不含大白星球"失败了。
这说明**提示词里出现名字本身也是风险**（模型可能照抄），
改成「不要把**软件的名字**当成你的名字」——既表达了意思，又不喂名字。

### 24.2 顺带发现：改了默认提示词，对老用户不生效

改完代码，我去看用户真实的 `config.json`：

```json
"prompts": {
  "summary_system": "你是 Great White Planet 学习软件的「学习资料整合专家」。",
  "daily_chat_system": "你是 Great White Planet（大白星球）内置的 AI 助手…"
}
```

**旧提示词原样躺在那里。** 根因是配置的**深合并**策略：
用户值优先于默认值（这是好事，用户手改的设置不该被升级冲掉），
但代价是**改了默认值对老用户永远不生效**。

**解法：给默认值一个版本号。**

```python
# constants.py
#: 默认提示词的**版本号**。每次改动下面这些默认提示词就 +1。
#:
#: 为什么需要它：配置是"深合并"的 —— 用户 config.json 里已经落盘的 prompts
#: **不会被新的默认值覆盖**（这是好事，用户手改过的提示词要保住）。
#: 但代价是改了默认提示词对老用户不生效。所以用版本号区分：
#: "你这份 prompts 是我第几版写的"，落后了就整段换成新默认值。
PROMPT_REVISION = 2
```

```python
# config.py —— 加载时迁移
def _migrate_prompts(self, user_data: dict) -> bool:
    stored = user_data.get("prompts")
    if not isinstance(stored, dict):
        return False                     # 用户没写过 prompts，走默认值即可
    try:
        revision = int(stored.get("revision", 0) or 0)
    except (TypeError, ValueError):
        revision = 0
    if revision >= C.PROMPT_REVISION:
        return False                     # 已经是最新（或用户自己锁定过）
    defaults = DEFAULT_CONFIG["prompts"]
    for key, value in defaults.items():
        if key == "revision":
            continue
        if key in self._data.get("prompts", {}):   # 只覆盖"存在"的键
            self._data["prompts"][key] = value
    self._data["prompts"]["revision"] = C.PROMPT_REVISION
    log.info("检测到旧版提示词（第 %s 版），已升级到第 %s 版",
             revision, C.PROMPT_REVISION)
    return True
```

**三种情况的行为**（这是设计的关键）：

| 情况 | 行为 |
| --- | --- |
| 用户没写过 `prompts` | 直接用新默认值（什么都不用做） |
| `revision` 落后 | **整段换成新默认值**并落盘，**只动提示词** |
| `revision` 已是最新 | 一个字都不动 —— 用户想自己改就手动填当前版本号锁定 |

实测（真实配置）：

```
升级前 revision: （无）
升级后 revision: 2
升级后 daily_chat_system 首行: 你是「长庚」——Great White Planet 学习软件内置的 AI 助手…
磁盘含长庚: True      磁盘含大白星球: False
你的其它设置还在（ui.theme）: light     ← 只动了提示词
用户锁定后仍是自己的: 我自己的提示词，别动我
```

> **通用经验（不只适用于提示词）**：
> 任何"**默认值 + 用户可覆盖**"的配置体系，都需要一个**默认值版本号**。
> 否则你改了默认值，只有两种结果：要么用户永远用不到新值，
> 要么你粗暴覆盖把用户的自定义设置一起冲掉。
>
> 版本号给了第三条路：**"这份值是旧默认值"和"这份值是用户自己写的"
> 可以区分开** —— 前者升级，后者保留。

### 24.3 需求：日期时间不要手打

> 数字看不清 修改  后面几点几分也弄成这种选择/滚轮，而非手动填写

**先看原来的实现**（两个对话框各写了一遍，而且都很朴素）：

```python
self.edit_due = QDateTimeEdit()
self.edit_due.setDisplayFormat("yyyy-MM-dd HH:mm")
self.edit_due.setCalendarPopup(True)
```

**查问题**：

1. `QDateTimeEdit` **完全没被 QSS 覆盖** —— 样式表那组输入框只列了
   `QLineEdit/QTextEdit/QPlainTextEdit/QSpinBox/QDoubleSpinBox/QComboBox`，
   所以它是 Qt **默认外观**，和界面其它控件不一致；
2. 上下调节按钮是 Qt 默认的**极窄**样式，难点；
3. 日历弹窗用默认字号，格子挤 —— 这就是"数字看不清"。

**改法（四处）**：

**① 抽一个公共构造函数**（两个对话框各写一遍，就是会改漏一处）：

```python
# gwp/ui/common.py
def make_datetime_edit(moment=None, *, minutes_only: bool = True) -> QDateTimeEdit:
    """做一个"用鼠标选 / 滚轮调"的日期时间输入框（不用手打数字）。

    1. **日期用日历弹窗选**（setCalendarPopup）—— 不用手打年月日；
    2. **时分用上下按钮 / 滚轮调**：displayFormat 带明确的间隔符，
       Qt 会把每一段做成可单独点选、可滚轮的区段；
       再显式允许键盘跟踪，方向上/下键与鼠标滚轮都能加减；
    3. **日历弹窗加大字号、加宽**（QSS 在 themes.py）—— 数字看得清；
    4. **不做手打校验**：这几段只能从合法范围里调，用户写不出非法日期。
    """
    edit = QDateTimeEdit()
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("yyyy-MM-dd HH:mm" if minutes_only else "yyyy-MM-dd HH:mm:ss")
    edit.setDateTime(QDateTime(moment) if moment is not None
                     else QDateTime.currentDateTime())
    edit.setKeyboardTracking(True)   # 光标停在某一段，上下键/滚轮直接调这一段
    edit.setWrapping(True)           # 59 分再加到 0 分，符合"滚轮"直觉
    calendar = edit.calendarWidget()
    if calendar is not None:
        calendar.setMinimumWidth(360)          # 数字不挤
        calendar.setGridVisible(True)          # 行列看得清
        calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
    return edit
```

**② 把 `QDateTimeEdit` 加进 QSS 的输入框组**，并专门给上下按钮和日历写样式：

```css
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
QDateTimeEdit, QDateEdit, QTimeEdit { /* 统一外观 */ }

/* 调节按钮加宽到 26px，箭头用 CSS 三角形画，对比度足够 */
QDateTimeEdit::up-button, QDateTimeEdit::down-button { width: 26px; ... }
QDateTimeEdit::up-arrow { image: none; width: 0; height: 0;
  border-left: 4px solid transparent; border-right: 4px solid transparent;
  border-bottom: 5px solid <text_muted>; }

/* 月历弹窗：字号加大、格子留白 */
QCalendarWidget QAbstractItemView:enabled { font-size: 1.08em; ... }
```

**③ 两个对话框改用公共函数。**

**④ 写测试。** 界面测试没法真的"滚鼠标"，但可以测**控件的能力**：

```python
check("日期时间输入带日历弹窗", dt.calendarPopup())
check("时间精确到分钟（不给用户多余的秒）",
      dt.displayFormat() == "yyyy-MM-dd HH:mm")
check("支持键盘/滚轮分段调节", dt.keyboardTracking() is True)
check("该段可循环（59 分滚回 0 分）", dt.wrapping() is True)
check("日历弹窗有足够宽度（数字不挤）", _cal.minimumWidth() >= 340)
check("日历有网格线（行列看得清）", _cal.isGridVisible())
# 真正能"调"而不是"只能打"
dt.setCurrentSection(QDateTimeEdit.Section.MinuteSection)
_before = dt.dateTime().toString("HH:mm"); dt.stepUp()
check("分钟段可以用 stepUp 调整（= 滚轮/上下按钮）", _before != _after)
```

> **这里有个测试思路值得学**：
> "滚轮能不能调节"这件事**没法在离屏测试里模拟**，
> 但它的本质是"控件支不支持按段调整" —— 而那正是 `keyboardTracking()`
> 和 `stepUp()` 这两个 API 的语义。
> **测不了交互，就测"交互依赖的能力"。**

### 24.4 复盘

| 需求 | 改动 | 新增测试 |
| --- | --- | --- |
| 助手自称「长庚」 | 7 段提示词 + 1 个常量 | 4 条（含"不许出现软件名"） |
| 老用户提示词升级 | `PROMPT_REVISION` + `_migrate_prompts` | 6 条（升级/保留/锁定） |
| 日期时间不用手打 | 1 个公共函数 + QSS + 2 处调用 | 12 条（能力 + 两个对话框） |
| **没动** | 对话框布局、数据模型、存储格式 | — |

**这一章最值得记住的两条**：

1. **"多处必须一致"的东西要用常量 + 断言锁住**（人设名、栏目名、配置键）。
   靠人眼维护一致性，一定会漏。
2. **"默认值 + 用户覆盖"需要版本号**，
   否则你无法区分"这份值是旧默认值"和"这份值是用户自己写的"。

---

## 第 25 章　拖拽上传：一个"数据视角 vs 用户视角"的 bug

### 25.1 需求

> 作业以及其它文件夹都要支持拖拽上传 目前会传到上一目录

一句话里有两个问题：

1. **拖拽上传没在所有地方生效**（要"支持"）；
2. **传错了地方** —— 传到上一级目录。

第 2 条是重点，因为它是一个**语义错误**，不是崩溃、不是报错，
而是"东西放错地方了"，用户要靠翻文件夹才发现。

### 25.2 先量：它到底落在哪

老办法，写脚本按标签页逐个拖一遍，看文件落进哪个目录：

```
标签「AI 总结」  表格视口 接受拖拽=False 落入=[]
                 表格      接受拖拽=False 落入=[]
                 BookView  接受拖拽=True  落入=['notebook\外部资料.txt']
```

**两个发现**：

1. `FileTable`（以及它的 viewport）**不接受拖拽** —— 拖拽事件靠
   Qt 的冒泡机制传到父级 `BookView` 才生效。能工作，但很脆：
   以后一旦给表格加行内拖拽（比如排序），导入就会先被表格吃掉。
2. 更重要的：落点算错了。看那段代码：

```python
def dropEvent(self, event):
    book = self.book()
    if book is None:
        return
    folder = self._target_folder() or (book.path / C.NOTEBOOK_FOLDER)
    ...
```

而 `_target_folder()` 是这样的：

```python
def _target_folder(self):
    """当前分类对应的真实目录（用于导入）。"""
    key = self._current_tab_key()
    for tab_key, _title, folder in self._tab_defs:
        if tab_key == key and folder:
            return book.path / folder
    return None
```

**它只看"标签登记了哪个目录"，完全不看你浏览到了哪一层。**

所以：进入 `others/第一章` 之后拖文件 → `_target_folder()` 仍然返回
`others` → **文件被丢到上一级**。这就是用户说的现象。

### 25.3 根因：拿"数据视角"回答了"用户视角"的问题

这个 bug 值得单独命名，因为它会反复出现：

> **界面上"操作作用于哪里"，必须由"用户此刻看到的位置"决定，
> 而不是由"数据模型里的归属"决定。**

两个视角在这个功能里是分开的：

| 视角 | 在这个功能里是什么 |
| --- | --- |
| **数据视角** | 这个标签登记的目录是 `others` |
| **用户视角** | 我现在正看着 `others/第一章` 里的文件 |

用数据视角回答"拖到哪"，就会得到 `others` —— **在用户眼里就是"上一级"**。

有意思的是，`BookView` 里**早就有用户视角的状态**：

```python
#: 在软件内部进到了哪个文件夹（None = 正常按栏目显示）
self._current_folder: Path | None = None
```

它被用于标题显示、`leave_folder()` 回退、"只列出该文件夹内容"，
**唯独漏了拖拽落点**。

> **教训**：新功能要接进已有状态时，先问一句
> **"这个操作有没有'当前位置'的概念？如果有，它应该读哪个字段？"**
> 这个项目里"当前位置"就是 `_current_folder`，
> 拖拽、导入、新建、粘贴……凡是"往这里放东西"的功能都该读它。
>
> （顺带发现：`create_folder` / `create_markdown` 用的是 `_creation_dir()`，
> 它**已经**正确处理了 `_current_folder`。所以漏掉的只有拖拽 ——
> 一个人漏、一个人没错，正说明"该读哪个字段"这件事没有统一约定。）

### 25.4 修法

**第一步：新增语义明确的落点函数，别改老函数。**

```python
def _target_folder(self) -> Path | None:
    """当前分类对应的真实目录（用于**新建**条目）。
    虚拟栏目（AI 总结 / 简介 / 全部条目）返回 None。
    """

def drop_target_folder(self) -> Path | None:
    """拖拽上传 / 导入的**真正落点**。

    和 _target_folder 的区别很关键（这是一个真实 bug 的修复）：

    * _target_folder() 只看标签登记，**完全不管你浏览到哪一层**。
      于是"进入 others/第一章 之后拖文件进来"，文件会被丢到
      others（也就是**上一级目录**）——用户反馈的正是这个现象。
    * 这里改成：**正在浏览某个文件夹时，落点就是那个文件夹**；
      只有在栏目根目录时才回退到标签登记的目录。
    """
    book = self.book()
    if book is None:
        return None
    if self._current_folder is not None:
        return self._current_folder
    return self._target_folder() or (book.path / C.NOTEBOOK_FOLDER)
```

**为什么不直接改 `_target_folder()`** —— 因为"新建条目"和"拖拽导入"
的语义**确实不同**：在虚拟栏目（AI 总结）下新建内容时不该乱放，
而拖拽导入时又需要一个兜底目录。**两个语义给两个函数名**，
比在一个函数里加 `if 是拖拽` 干净得多。

**第二步：表格自己也接受拖拽，落点规则只写一份。**

```python
# file_table.py
self.setAcceptDrops(True)
self.viewport().setAcceptDrops(True)

def dropEvent(self, event):
    if self._has_local_files(event.mimeData()):
        event.acceptProposedAction()
        # 落点用**视口坐标**交给 BookView，它据此判断是否落在某个文件夹行上
        self.files_dropped.emit(event.position().toPoint(), event.mimeData())
        return
    super().dropEvent(event)
```

```python
# book_view.py
table.files_dropped.connect(self.handle_file_drop)

def handle_file_drop(self, pos, mime) -> bool:
    """处理一次外部文件拖入。返回是否消费了这次拖拽。

    由 BookView 和 FileTable 共用 —— 表格上的拖拽先走这里，
    没消费掉才冒泡到视图，两条路径的落点规则完全一致。
    """
    paths = self._drop_paths(mime)
    if not paths:
        return False
    folder = self._row_folder_at(pos) or self.drop_target_folder()
    if folder is None:
        common.warn(self, "当前栏目没有对应的文件夹，无法导入。", "无法导入")
        return True
    self._do_import(paths, folder)
    return True
```

**关键点**：落点规则**只有一份实现**，表格和视图都调它。
如果两边各写一份，早晚会不一致。

**第三步：再加一个"拖到某一行"的便利。**

```python
def _row_folder_at(self, pos) -> Path | None:
    """拖拽落点正好在某个文件夹那一行上时，返回那个文件夹。

    用途：把文件**直接拖进某个作业 / 子文件夹**，
    省掉"先传到当前目录、再手工移进去"这一步。
    """
    table = self._current_table()
    row = table.row_at(pos)
    if row < 0:
        return None
    item = table.item_at(row)
    return item.path if item is not None and item.is_dir else None
```

顺带给 `FileTable` 补了两个**公开**方法（原来只能读私有 `_items`）：

```python
def item_at(self, row: int) -> BookItem | None: ...
def row_at(self, pos) -> int:
    """某个坐标在哪一行上；不在任何行上返回 -1。

    接受 QPoint 或 QPointF —— 拖拽事件给的是 QPointF，
    而 indexAt 只认 QPoint，必须显式取整。
    """
    if hasattr(pos, "toPoint"):
        pos = pos.toPoint()
    index = self.indexAt(pos)
    return index.row() if index is not None and index.isValid() else -1
```

**第四步：给用户反馈。** 这个 bug 之所以能活到用户报障，
一半原因是**拖拽时没有任何提示**，用户根本不知道会落到哪。

```python
def _set_drop_hint(self, folder: Path | None) -> None:
    """拖拽过程中显示"会传到哪"。

    文案复用 _folder_label（``others / 第一章``），和导入完成后
    状态栏里的说法一致 —— 两处一样，用户才能把"拖的时候看到的"
    和"传完之后看到的"对上。
    """
    if folder is None or self.book() is None:
        self.lbl_drop_hint.setVisible(False)
        return
    self.lbl_drop_hint.setText(f"拖到这里 → {self._folder_label(folder)}")
    self.lbl_drop_hint.setVisible(True)
```

还把导入完成的提示从"只给文件夹名"改成**相对书目的完整路径**：

```python
# 之前：message = f"已导入 {len(ok)} 个文件到 {folder.name}"
message = f"已导入 {len(ok)} 个文件到 {self._folder_label(folder)}"
# → 已导入 2 个文件到 others / 第一章
```

> **一个通用判断**：**如果用户无法在操作前知道会发生什么、
> 也无法在操作后验证做了什么，那这个功能的 bug 就永远只能靠用户报障。**
> 反馈不是"锦上添花"，它是**错误检测机制**的一部分。

### 25.5 配一个明确入口（不是所有人都爱拖）

```python
def upload_files(self, inside: Path | None = None) -> None:
    """用文件选择框"上传"文件到指定文件夹（或当前浏览的目录）。

    拖拽上传之外再给一个明确入口：有些人不用拖拽，
    触控板拖文件也不方便。落点规则和拖拽**完全一致**。
    """
    target = Path(inside) if inside is not None else self.drop_target_folder()
    if target is None:
        common.warn(self, "请先进入某个书目，并切到有对应目录的分类。", "无法上传")
        return
    paths = common.pick_files(self, "选择要上传的文件", multiple=True)
    if not paths:
        return
    self._do_import([Path(p) for p in paths], target)
```

右键文件夹即可看到「**上传文件到「第一章」…**」。

### 25.6 写测试时踩的三个坑（这部分同样值钱）

修完要写回归测试。界面拖拽的测试不好写，我踩了三个坑，
**每一个都是"测试自己写错"而不是"代码错"**：

**坑 1：信号参数类型没注册，emit 被静默丢弃。**

```python
# ❌ 槽函数永远不执行，且不报错
files_dropped = pyqtSignal(QPoint, object)
```

原因：`PyQt6.QtCore.QPoint` **不是默认注册的信号参数类型**。
改成 `object` 就正常了：

```python
# ✅ object 收什么都行
#: 第一个参数用 object 而不是 QPoint：QPoint 不是默认注册的信号参数类型，
#: 用 QPoint 声明时 emit 会被**静默丢弃**（不报错、槽不执行 —— 实测踩过，很难查）
files_dropped = pyqtSignal(object, object)
```

> **这是 Qt 的一个真陷阱**：信号声明里的类型不只是"给 IDE 看的注解"，
> 它参与运行时的类型检查。用未注册类型会**静默失败**。
> 遇到"信号发了槽不执行"，先怀疑这里；不确定就用 `object`。

**坑 2：测试里 `disconnect()` 把被测代码的连接也摘了。**

我写了个辅助函数，为了干净地测量，它先 `disconnect()` 再连自己的监听器：

```python
# ❌ 这一行把视图自己的连接一起摘掉了
widget.files_dropped.disconnect()
widget.files_dropped.connect(my_probe)
```

结果：**后面的所有拖拽用例全部失败**（视图再也收不到信号了），
表现为"一连串神秘失败"。修法是**只换被测逻辑的下一层**，
别动信号连接：

```python
def _capture_drop(widget, pos):
    """拖一次，并记下真正用于导入的目标目录。

    实现要点（踩过坑）：**不要** files_dropped.disconnect() ——
    那会把视图自己的连接一起摘掉，之后所有拖拽都不再走导入，
    表现为"一连串用例神秘失败"。只换 _do_import 就够了。
    """
    seen: list[Path] = []
    real = fbv._do_import
    fbv._do_import = lambda paths, folder: (seen.append(Path(folder)), None)[1]
    try:
        dropper(widget, pos)
    finally:
        fbv._do_import = real
    return seen
```

> **教训**：测试辅助函数里凡是"改全局状态"的操作（disconnect、
> monkeypatch、改环境变量），都必须**只碰最小范围并确保还原**。
> 摘掉整个信号连接属于"影响面远大于需要"。

**坑 3：落点坐标选在了文件夹那一行上，测试互相干扰。**

`_QPoint(40, 20)` 正好是第一行 —— 而第一行很可能是**文件夹**。
于是"拖到栏目根目录"的用例实际测的是"拖到那个文件夹里"，
断言自然不成立（更糟的是它掩盖了真正的行为：

```python
def _empty_pos(table) -> _QPoint:
    """表格**下方空白处**的坐标 —— 用来测"落在当前栏目根目录"。

    为什么不能用 (40, 20)：那正好是第一行（很可能是个文件夹），
    而"拖到文件夹行上"是**另一种**语义。两个用例必须用不同落点。
    """
    rows_height = sum(table.rowHeight(r) for r in range(table.rowCount()))
    y = min(rows_height + 12, max(0, table.viewport().height() - 6))
    return _QPoint(40, y)
```

**另外一个真正的状态坑**：那个书目属于**自学课**科目，
它的作业栏目显示为「**练习**」而不是「作业」（这是需求）。
测试里按显示文案找标签就会 `StopIteration`。
改成按**内部 key** 找：

```python
_homework_idx = next(
    i for i, (key, _title, _folder) in enumerate(fbv._tab_defs)
    if key == "homework"
)
```

> **"文案"和"标识"必须分开**：文案是给用户看的、会改；
> 标识是程序用的、不该改。测试（以及一切程序逻辑）
> 都该按标识找东西。这个项目里栏目定义是三元的
> `(key, 文案, 目录名)` —— 就是为了这个。

### 25.7 最难的一步：别用"文件出现在哪"当断言

我最初的断言是"**文件出现在目标文件夹里**"。它把三件事混在一起：

1. 落点算对了没；
2. 导入有没有真的执行；
3. 同名冲突时改名规则对不对。

结果：三者中任何一个出问题，测试都只告诉你"文件不在那儿"。
更糟的是它**依赖落点坐标和行高**，行高一变断言就飘。

后来改成**直接断言"传给导入函数的目录"**：

```python
def _capture_drop(widget, pos):
    """拖一次，并记下**真正用于导入的目标目录**。

    为什么断言"目标目录"而不是"文件出现在哪"：
    * 目标目录就是这段逻辑的产出，断言它最直接；
    * 不受同名字自动改名、对话框打桩、行高变化等无关因素干扰。
    """
```

**测试写成这样，七条用例一次全绿**，而且连跑三次稳定：

```
[PASS] 文件表格接受外部拖入（否则导入会被表格吃掉）
[PASS] 表格接受外部拖入后会通知视图处理
[PASS] 栏目根目录的拖拽落点 = 该栏目目录
[PASS] 拖到「其它文件」根目录 → 目标目录是 others/
[PASS] 进入子目录后拖拽落点 = 该子目录
[PASS] 拖到子目录里 → 目标目录是那个子目录（不是上一级）
[PASS] 拖到子目录里 → 目标**不是**上一级 others/
[PASS] 拖到文件夹行上 → 目标目录是那个文件夹
[PASS] 作业栏目的拖拽落点是 homework 目录
[PASS] 作业栏目支持拖拽上传（目标 homework 目录）
[PASS] 拖拽落点提示控件存在且默认隐藏
[PASS] 拖拽时会显示落点提示
[PASS] 离开拖拽后落点提示隐藏
[PASS] 右键菜单有「上传文件」入口
```

> **"断言什么"比"断言哪一段代码"更重要。**
> 好的断言直接命中**这个功能的产出**（这里是"算出来的目标目录"），
> 而不是它的副作用（文件出现在某处）。
> 副作用牵扯的东西太多，会让测试变脆、也会让失败信息变模糊。

### 25.8 复盘

| 类别 | 内容 |
| --- | --- |
| 修 bug | 新增 `drop_target_folder()`：落点以"当前浏览的目录"为准 |
| 新增能力 | 表格自己接受拖入；拖到文件夹行上进那个文件夹；右键「上传文件」 |
| 新增反馈 | 拖拽时显示落点提示；导入完成提示完整相对路径 |
| 新增测试 | 14 条（落点、行级落点、作业栏目、提示、菜单入口） |
| **没动** | 导入实现、数据模型、存储格式、其它界面 |
| 学到的 | ①用户视角 vs 数据视角；②`QPoint` 信号静默丢弃；<br>③测试里别 `disconnect()`；④断言"产出"而不是"副作用" |

**这一章最值钱的一条**：

> **凡是"操作作用于哪里"的问题，界面的答案永远是"用户此刻看到的位置"。**
>
> 数据模型知道"归属"，但只有界面知道"用户站在哪"。
> 这个项目里"用户站在哪"就是 `_current_folder` 一个字段 ——
> 拖拽漏读了它，于是文件跑到了上一级。

---

## 第 26 章　"同一个数字，两种算法"：标签计数不一致

### 26.1 需求

用户发来截图，指着书目页的标签说：

> 作业栏目无上传文件按钮 而且作业后面的数量统计异常 修复一下

截图里能看到两个现象：

1. 标题是 `高等代数 › homework\2.4 作业`（**已经进了某个作业里面**），
   而顶部按钮是「创建作业」—— 在作业里面"创建作业"是**不合语境**的，
   而且这里正是最需要"上传附件"的地方，却没有任何导入入口；
2. 标签写着「**作业 2**」，但表格里只有 **1 行**。

第 2 条是这一章的重点：它是一个**一致性问题**，不是崩溃。

### 26.2 先把"数量异常"量出来

老规矩，先量数据，不猜：

```
作业目录: ...\高等代数\高等代数\homework
顶层条目（表格会显示的行）:
  DIR  2.4 作业  (内含 2.4 作业.md, homework.json)

旧算法(rglob 数文件) = 2      ← 标签显示的就是这个
新算法(顶层条目)     = 1      ← 表格实际显示 1 行
```

**根因**：两个地方对"作业栏目有几个条目"的定义不一样。

```python
# 表格用这个：只列**一层**
def list_homework_items(self, book: Book) -> list[BookItem]:
    """列出作业栏目的条目：**一个作业一行**。

    list_folder 会把子目录里的文件也递归铺出来（笔记里这样方便），
    但作业栏目不行：每个作业内部有 homework.json 和作业内容文件，
    全铺出来会变成一长串「第一次作业/homework.json」这种噪音。
    """
```

```python
# 而计数用的是这个：**递归数所有文件**
book.item_counts[key] = sum(1 for p in folder.rglob("*") if p.is_file())
```

于是「2.4 作业」目录里的 `homework.json` + `2.4 作业.md`
被算成了 2 —— 而表格只显示 1 行。**标签上的数字在骗人。**

### 26.3 定规则：数字 = 点进去能看到几行

修法本身只有几行，难的是**先把规则说清楚**：

> **栏目标签上的数字 = 点进这个栏目能看到几行。**

这条规则对两类栏目给出的算法不同，但**口径统一**：

| 栏目 | 表格怎么显示 | 所以数字怎么数 |
| --- | --- | --- |
| 笔记 / 易错题 / 教材 / 其它文件 | 子目录里的文件**会铺开**成多行 | **数文件**（`rglob`） |
| **作业** | **一个作业一行**（内部文件不铺开） | **数顶层条目** |

```python
for key in (C.BOOK_FOLDER, C.ERROR_FOLDER, C.NOTEBOOK_FOLDER,
            C.HOMEWORK_FOLDER, C.OTHERS_FOLDER):
    folder = book_dir / key
    if folder.is_dir():
        try:
            if key == C.HOMEWORK_FOLDER:
                # 作业栏目**单独处理**：一个作业 = 一个子目录 = 一行，
                # 所以只数顶层条目。
                # 这里曾经用 rglob 递归数文件，于是"2.4 作业"目录里的
                # homework.json + 作业内容文件被算成 2，而表格只显示 1 行
                # —— 标签上的数字和点进去看到的内容对不上（用户报障）。
                # 规则：**标签上的数字永远等于点进去能看到几行。**
                book.item_counts[key] = sum(
                    1 for p in folder.iterdir()
                    if not p.name.startswith(".")
                )
            else:
                book.item_counts[key] = sum(
                    1 for p in folder.rglob("*") if p.is_file()
                )
        except OSError:
            book.item_counts[key] = 0
    else:
        book.item_counts[key] = 0
```

> **注意这里的判断顺序**：`key == C.HOMEWORK_FOLDER` 是**按标识**判断，
> 不是按显示文案（"作业"/"练习"）。文案会随科目类型变，标识不会。

### 26.4 测试立刻抓出第二个不一致

修完跑的第一次测试就红了，**而且红在一个我根本没改的地方**：

```
[FAIL] stats 报告作业的真实数量（不误导为 0）
       -> {'intro': 1, 'notebook': 0, 'error-prone': 0, 'total': 1,
           'chars': 0, 'homework': 6, 'book': 0}
```

`homework: 6` —— 书目的**资料概览**面板也用了 `rglob`：

```python
# gwp/ai/summarizer.py（修之前）
# 不参与总结的目录：单独统计，仅供界面显示
for key in (C.HOMEWORK_FOLDER, C.BOOK_FOLDER):
    folder = book.path / key
    ...
    result[key] = sum(1 for child in folder.rglob("*") if child.is_file())
```

**这就是"同一个概念出现在多处"的典型后果**：
我只知道 `store.py` 里有一处，测试告诉我还有一处。
如果没写"数字必须一致"这条断言，这个不一致会一直留着。

修法一样，并把这个理由写在代码里：

```python
if key == C.HOMEWORK_FOLDER:
    # 作业栏目在界面上是"一个作业一行"，所以这里也必须数**顶层条目**：
    # 用 rglob 会把每个作业内部的 homework.json + 内容文件都算进来，
    # 于是标签/概览显示的数字和表格行数对不上（用户报障的那个 bug）。
    # 规则统一为：**这里报的数字 = 点进该栏目能看到几行**。
    result[key] = sum(
        1 for child in folder.iterdir()
        if not child.name.startswith(".")
    )
```

最后一条断言把三处口径钉在一起：

```python
check("作业标签的计数 = 表格行数（一个作业一行）",
      count == rows, f"计数={count} 表格行数={rows}")
check("作业计数不再等于内部文件总数（那正是 bug）",
      files != count and files > count, f"内部文件数={files} 计数={count}")
check("stats 的作业数与表格行数一致",
      int(stats.get(C.HOMEWORK_FOLDER, -1))
      == len(library.list_homework_items(reloaded)), ...)
```

### 26.5 顺便修掉"作业里面没有上传入口"

按钮原来是这样决定的：

```python
# 修之前：只看"当前是不是作业栏目"
manageable = (is_homework_tab and self.subject_type == C.SUBJECT_SCHOOL
              and self.book() is not None)
self.btn_homework.setVisible(manageable)
self.btn_import.setVisible(not manageable)
```

**它漏了"在哪一层"** —— 和第 25 章拖拽那个 bug **完全同源**
（都是没读 `_current_folder`）。于是进了作业里面，
顶部还是「创建作业」，而"上传附件"没有任何入口，只能靠拖拽。

```python
def _sync_homework_buttons(self) -> None:
    """「创建作业」与「上传文件」按**当前位置**决定显示哪个。

    * **作业栏目的根目录** → 显示「创建作业」+「上传文件」。
    * **已经进了某个作业（或子文件夹）里** → 只显示「上传文件」。
      原因：在 homework/2.4 作业 里面再点「创建作业」是**不合语境**的
      （新作业只能建在作业栏目根目录）；而且这里正是最需要上传附件的地方。
    """
    is_homework_tab = self._current_tab_key() == "homework"
    can_manage = (is_homework_tab
                  and self.subject_type == C.SUBJECT_SCHOOL
                  and self.book() is not None)
    at_root = self._current_folder is None       # ← 新增的判据
    self.btn_homework.setVisible(can_manage and at_root)
    self.btn_import.setVisible(not (can_manage and at_root))
```

**同时修掉同源的另一处**：`import_files()`（点「导入文件」按钮走的那条路）
读的也是 `_target_folder()`：

```python
# 修之前：进了子文件夹再点「导入文件」，还是导到上一级
folder = self._target_folder()

# 修之后：和拖拽用同一套落点规则
folder = self.drop_target_folder()
```

> **这是分组修复（cluster fix）的价值**：
> 第 25 章修了拖拽的落点，当时我**没有**回头检查"同一个字段还被谁读过"。
> 结果这一章又因为同一个原因修了第二次。
>
> **修完一个"漏读状态"的 bug 后，应该全局搜一下这个状态字段，
> 把所有"操作作用于哪里"的地方都过一遍。** 这一次就是因为没做，
> `import_files` 又多活了一轮。

**一个测试基础设施的坑（也记下来）**：我一开始在
`_update_folder_hint()` 里加按钮同步，但 `enter_folder()` 当时并没有调它 ——
那是**先有鸡还是先有蛋**的问题。最后把同步放进 `_update_folder_hint()`
（`refresh` / `enter_folder` / `leave_folder` 都会经过它），
这样"进入/离开文件夹"一定会刷新按钮，不会再漏。

### 26.6 顺手统一路径显示

截图里标题是 `homework\2.4 作业`（Windows 反斜杠），
而状态栏和拖拽提示用的是 `homework / 2.4 作业`。
**同一个位置、两套写法**，用户会犯迷糊。统一成一种：

```python
def _update_folder_hint(self) -> None:
    """在标题上提示"正在文件夹里看"，并保持"返回上一层"按钮可用。

    路径用 _folder_label() 转成 ``homework / 2.4 作业`` 这种写法 ——
    直接插 Path 会显示 Windows 的反斜杠（``homework\\2.4 作业``），
    和状态栏、拖拽提示里的说法不一致。
    """
    ...
    self.set_title(f"{book.title} › {self._folder_label(folder)}")
```

> **"同一种信息只有一种呈现"** 和"同一个数字只有一种算法"是同一类原则。
> 用户看到两套写法时的第一反应是"这两个是不是不同的东西"。

### 26.7 复盘

| 类别 | 内容 |
| --- | --- |
| 修 bug | 作业计数改为"数顶层条目"（`store.py` + `summarizer.py` 两处） |
| 修 bug | 进子文件夹后显示「导入文件」、隐藏「创建作业」 |
| 修 bug | `import_files()` 也改用 `drop_target_folder()`（与拖拽同规则） |
| 统一 | 标题路径分隔符与状态栏一致（`/` 而不是 `\`） |
| 新增测试 | 9 条（计数一致、按钮切换、导入落点、tooltip 写明位置） |
| 学到的 | ①同一个数字只能有一种算法；②"漏读状态"要全局排查；<br>③测试基础设施本身也会先有鸡后有蛋 |

**这一章最值钱的一条**：

> **"同一个概念在多处出现"时，最危险的不是算法错，而是算法不一致。**
>
> 三处都在算"作业有几个"，两处用 `rglob`、一处只列一层。
> 单看任何一处都"没错"，但它们**互相矛盾**，
> 结果就是标签上的数字和表格内容对不上。
>
> 解法不是"把三处都改对"，而是**先定义清楚规则
> （数字 = 点进去能看到几行），再让三处共用同一个口径**，
> 最后用断言把口径钉住。第 22 章讲的"零依赖原则"、
> 第 24 章讲的"常量 + 断言锁住一致性"，都是同一件事的不同侧面。

---

## 第 27 章　AI 读图：不可靠时宁可缺，不可编

### 27.1 需求与它的隐藏难点

> 增加文件夹内多图片AI提取内容（无把握识别准确就直接插入图片）并合并为md功能

需求本身很平常：把一堆照片（黑板照、扫描讲义、PPT 截图）变成一份 Markdown。
但它藏着一个真正的设计问题，而且**用户已经用括号点出来了**：

> （无把握识别准确就直接插入图片）

**为什么用户会主动加这一句？** 因为他知道 AI 看图片一定会看错。
而这一类功能有两种失败方式，代价相差极大：

| 失败方式 | 用户会怎么发现 | 代价 |
| --- | --- | --- |
| 少写了内容 | 对着原图一看就发现缺了 | 小，随手补 |
| **编了一段看着很像的内容** | **几乎发现不了**，还以为是真的 | **极大** |

第二行的可怕之处在于：用户拿这份 md 当复习资料，
**把 AI 编的"定理条件"背下来了**。而它看起来完全正常 —— 格式对、
术语对、语气对。**这是"缺失"和"幻觉"的根本区别：
缺失是可见的，幻觉是不可见的。**

所以这一章的核心不是"怎么调用多模态模型"，而是
**怎么让一个不可靠的组件（AI 读图）在不可靠时安全地退化**。

### 27.2 先解决"能不能做"

动手前先查清基础设施（这一步省掉了很多返工）：

```
各提供方是否支持图片输入？
  deepseek_api:  supports_vision = False   ← 只能读文字
  gpt_api:       supports_vision = True    ← 但没配密钥
用户实际可用的视觉模型：**没有**
```

**结论：如果只做"API 直连"，这个功能对当前用户是死的。**
所以必须**同时**提供一条零密钥的路。最终方案是双路：

```
能看图吗？
├─ 有（声明支持视觉 + 用户打开「发送图片」）→ 直连模型，全自动，用户零操作
└─ 没有（默认）→ 网页版桥接：图片/提示词进剪贴板 → 打开网页
                → 用户 Ctrl+V 两次 → 把回答粘回来
```

**为什么"用户必须显式打开 send_images"**：图片可能是作业照片、
证件、手写笔记，发出去有隐私含义。**"配了个支持视觉的模型"不等于
"用户同意把图外发"** —— 这两件事必须分开确认。所以默认关闭。

### 27.3 把不可靠的判断做成纯函数

整个功能里最值钱的部分是**判断"这次识别可不可信"**。
它必须是**纯函数**：不碰界面、不碰网络、可以被穷举测试。

```python
def evaluate_extraction(text, *, min_chars=MIN_CHARS, user_unsure=False) -> Verdict:
    """判断一次 AI 提取结果**够不够可信**。

    宁可误判为"不可信"（那就插图片），也不要误判为"可信"（那会留下幻觉）。
    所以这里的阈值都偏保守。
    """
```

判定规则（五条，全部**偏向不可信**）：

| 规则 | 为什么 |
| --- | --- |
| 调用方标了 `user_unsure` | 用户看过原文，他说不准就是不准 |
| 正文过短 | 连一行都没读出来，等于没提取 |
| 出现"无法辨认/看不清/抱歉" | AI **自己承认**失败，最可靠的信号 |
| 出现 `[[无法辨认]]` 占位符 | 提示词要求它标盲区，它标了 |
| 乱码字符占比过高 | 通常是编码/字体问题，转写必然不可信 |

**中文的"自认失败"措辞是这张表里最实用的一条。**
模型不会主动说"我置信度 0.3"，但它会说"抱歉，这张图片无法辨认"。
**把它的自然语言当置信度用** —— 这比逼它输出一个分数可靠得多。

还有一条**优先级规则**值得单说：

```python
@property
def verdict(self) -> Verdict:
    if self.edited and self.text.strip():
        return Verdict(reliable=True, reasons=[])   # 人改过的就是权威
    return evaluate_extraction(self.text, user_unsure=self.user_unsure)
```

**人手动改过的正文不再被自动判死。** 因为用户可能有过一次提取其实是对的、
只是触发了某个启发式规则（比如正文里恰好引用了"看不清"这三个字）。
**启发式规则永远会有假阳性，所以必须留一个"人说了算"的出口。**

### 27.4 不可信时怎么"退化"

这里是需求的原话落地：**直接插入图片本身**。

```python
for order, result in enumerate(results, start=1):
    lines += [f"## {order}. {result.image.name}", ""]
    verdict = result.verdict
    if verdict.reliable:
        lines += [_demote_headings(result.text.strip(), 2), ""]
    else:
        lines += [
            UNSURE_BANNER.format(reason=verdict.reason_text).rstrip(),
            "",
            f"![{result.image.name}]({_relative_url(result.image, base)})",
            "",
        ]
```

生成的片段长这样：

```markdown
## 2. 第2页.png

> ⚠️ **这一页没能可靠识别**，因此直接插入原图，请自行查看。
> 原因：AI 自己表示看不清：无法辨认、抱歉

![第2页.png](第2页.png)
```

三个设计点：

1. **写明原因**。只说"没识别"用户会反复重试；说了"AI 自己表示看不清"，
   他就知道该自己看原图了。
2. **图片用相对路径**（`_relative_url`）。整个文件夹搬到别处链接不失效 ——
   这个项目所有图片嵌入都遵守这条（见第 11 章 PDF 导出的 `Archive` 坑）。
3. **`_demote_headings`**：AI 转写出来的正文里常有 `## 一节`，
   会和我的 `## 2. 第2页.png` 撞级、把文档结构弄乱。统一降两级。

顺带一个"小功能里的大讲究"：**自然排序**。

```python
def natural_key(path) -> tuple:
    """自然排序键：``第2页`` 在 ``第10页`` 之前。

    朴素的 sorted() 按字符比较，会把 第10页 排到 第2页 前面 ——
    对"按页拍的课件照片"来说顺序全乱。所以把连续数字当整数比。
    """
```

实测：

```
朴素排序: ['第1页', '第10页', '第2页', '第3页']     ← 顺序全乱
自然排序: ['第1页', '第2页', '第3页', '第10页']     ← 正确
```

**这个细节决定了功能可用不可用**：顺序乱了的合并 md 没有任何价值。

### 27.5 两个真实的空白：图片剪贴板与多行输入

走网页版桥接需要两个能力，项目里**都没有**：

**① 把图片放进剪贴板。** 全项目只有文本剪贴板和 `CF_HDROP`（文件列表），
没有任何 `setImage`。

```python
def copy_image_to_clipboard(path) -> bool:
    """把一张图片放进系统剪贴板，供用户直接粘到网页版 AI 的输入框。

    * **超大图先缩放**：手机拍的课件照片动辄 4000px/8MB，
      整张塞进剪贴板会让部分网页版拒收或上传极慢；
      缩到 2048 对"看清文字"完全够用。
    * 失败一律返回 False，由调用方提示"手动拖图"，不要抛异常。
    """
```

实测：3000×1500 进剪贴板后回读为 **2048×1024**（自动缩放生效）；
不存在文件 / 传目录 / 传 `None` 全部安全返回 `False`。

**② 多行"等用户粘贴"的对话框。** 项目原有的 `ask_text` 走
`QInputDialog.getText`，**只有单行**（`AiQuestionDialog` 也是 `QLineEdit`）——
用来粘一段 Markdown 完全不够。所以新写了 `ask_multiline` 与
`ask_paste_reply`（后者是网页版桥接的通用接收端）。

`ask_paste_reply` 里有个贴心的小设计：

```python
clipboard = QApplication.clipboard()
if clipboard is not None:
    existing = clipboard.text() or ""
    # 只自动填"看起来像回答"的内容，避免把上一次复制的提示词又粘一遍
    if existing.strip() and existing.strip() != prompt.strip():
        box.setPlainText(existing)
```

**打开弹窗时如果剪贴板里已经有文字就自动填进去** ——
用户刚在网页里 Ctrl+C 过，能省一步。而**排除掉等于提示词的内容**，
避免把刚复制出去的提示词又粘回来变成"回答"。

对话框里还写了一句很关键的话：

> 识别不了可以直接留空 —— 留空的图片会**原样插入到结果里**，不会编内容。

**这句话是在明确告诉用户"跳过是受支持的操作"。**
否则用户会觉得"我必须编点什么进去"，那就绕过了整个安全机制。

### 27.6 收在一个函数里的"能力判断"

界面层不应该知道"哪个 provider 支持视觉"。所以有一个统一入口：

```python
def send_to_ai(prompt, *, provider_id="", url="", image_path=None,
               context=None, parent=None, title="网页版 AI",
               open_browser=True) -> str:
    """把一段提示词（可选带一张图片）送进 AI，返回回答。

    **这是界面层统一应该调用的入口**：

    * 若配置的提供方支持直接看图片，就直接调用它，完全不需要用户粘贴；
    * 否则走网页版桥接。

    这样"以后填了视觉模型密钥"时，同一段界面代码自动变成全自动，
    不用改任何界面 —— 这是把"能力判断"收在一个函数里的好处。
    """
```

判据只有两条，缺一不可：

```python
def _provider_sees_images(context, provider_id, provider) -> bool:
    """两个条件都要满足：
    1. 它**声明**支持视觉（supports_vision）；
    2. 用户**允许发送图片**（ai.send_images）—— 发图有隐私含义，
       必须由用户显式开启，不能悄悄发。
    """
```

顺带补上了设置界面里缺的开关（原来 `ai.send_images` 这个键
**在设置里根本没有入口**，用户想开都开不了）：

```python
self.check_send_images = QCheckBox(
    "允许把图片发送给 AI（「图片提取为 Markdown」需要它；支持视觉的模型才有效）"
)
self.check_send_images.setChecked(bool(self.config.get("ai.send_images", False)))
```

> **这一条值得单独记**：一个"支持视觉"的配置项如果界面上没有开关，
> 那这条代码路径就是**死的**。加功能时要顺着配置项走一遍，
> 确认用户**有能力**打开它。

### 27.7 复盘

| 类别 | 内容 |
| --- | --- |
| 新增服务层 | `gwp/services/image_digest.py`：收集/提示词/可靠性判断/组装 md |
| 新增界面 | `gwp/ui/dialogs/image_digest_dialog.py`（列表 + 逐张处理 + 手动干预 + 落盘） |
| 新增桥接能力 | `copy_image_to_clipboard`、`send_to_ai`（自动选直连/网页桥接） |
| 新增界面基建 | `common.ask_multiline`、`common.ask_paste_reply` |
| 补缺口 | 设置界面加「允许把图片发送给 AI」开关（原来没入口） |
| 入口 | 工具菜单 + 文件夹右键 |
| 新增测试 | 44 条（核心 29 + 界面 15） |
| 学到的 | ①AI 不可靠时要"安全退化"；②把模型的话当置信度用；<br>③启发式必有假阳性，必须给人留否决权；④配置项要有界面入口 |

**这一章最值钱的一条**：

> **AI 功能的设计重点不是"让它更准"，而是"它不准的时候会发生什么"。**
>
> 识别率从 90% 提到 95% 是工程优化；
> 而"不确定时插原图而不是编内容"是**安全设计**。
> 后者一次做对，永久受益；前者永远追不完。
>
> 判断标准很简单：**问一句"如果它错了，用户多久能发现、代价多大"。**
> 如果答案是"很久才发现、代价很大"，那这个失败路径就必须被设计掉，
> 而不是靠提高准确率去赌。

---

## 第 28 章　"本地有内容但软件不显示"：列表的层级问题

### 28.1 需求

用户发来截图，左边是软件（作业栏目，**一片空白**），
右边是资源管理器（同一个文件夹，**4 个文件**）：

> 本地文件夹有内容 但是软件内不显示 要显示出来该作业文件夹的所有文件

这是最让人不信任软件的一类 bug：**数据在，界面说没有**。
用户的第一反应是"软件把我的东西弄丢了"。

### 28.2 定位：一行过滤条件

先量。把"当前层该显示什么"打出来：

```
作业根目录: homework
根目录下的条目（表格会显示）:
    2.4 作业 (dir) | parent = homework

进入: 2.4 作业
该目录下真实文件: ['2.4 作业.md', '69425..._compress.jpg',
                  '69425..._compress_1.jpg', 'homework.json']
当前代码过滤出的条目: []            <-- 空就是 bug
```

代码只有几行：

```python
if key == "homework":
    # 作业栏目：列结构不同（有 DDL/提交方式），只列本层文件夹
    items = [
        item for item in self.context.library.list_homework_items(book)
        if item.path.parent == folder
    ]
    table.set_items(items)
```

**根因**：`list_homework_items()` 返回的是**作业根目录下第一层的作业文件夹**
（这是"一个作业一行"所必需的）。进了 `homework/2.4 作业` 之后，
那个文件夹里的 md、图片、`homework.json` **都不是"作业条目"**，
所以 `path.parent == folder` 这个过滤条件**永远不成立** → 结果恒为空。

### 28.3 根因的根因：两个层级的视图共用了一套规则

这才是值得记的部分。这个列表其实要在**两个不同层级**上工作：

| 层级 | 用户想看什么 | 正确的数据来源 |
| --- | --- | --- |
| 作业栏目**根目录** | 我有哪些作业 | `list_homework_items()`（一个作业一行） |
| **进了某个作业里面** | 这个作业文件夹里有什么 | `list_folder()`（真实列目录） |

原代码的错在于：**它在两个层级上用同一份数据，只换了个过滤条件。**
而这两层需要的其实是**不同的数据来源**。

修法就是在"进入下一层"时切换数据源：

```python
key = self._current_tab_key()
if key == "homework" and folder == book.path / C.HOMEWORK_FOLDER:
    # 作业**栏目根目录**：一个作业一行，走专门的列表函数
    table.set_items(self.context.library.list_homework_items(book))
else:
    # 其它情况（含**进了某个作业里面**）一律列该目录的真实内容。
    #
    # 这里曾经是一个 bug：作业栏目无论在哪一层都用 list_homework_items
    # 再按 path.parent == folder 过滤，而那个函数只列作业根目录下第一层的
    # 作业文件夹 —— 进了 homework/2.4 作业 之后，里面的 md、图片、
    # homework.json 都不是"作业条目"，过滤结果恒为空，界面一片空白
    # （用户反馈："本地文件夹有内容 但是软件内不显示"）。
    items = [
        item for item in self.context.library.list_folder(folder)
        if item.path.parent == folder
    ]
    table.set_items(items)
```

> **通用教训**：
> **凡是支持"进入下一层"的列表，进入时都要换数据来源，
> 而不是在同一份数据上换个过滤条件。**
>
> 换个过滤条件看起来"复用得很优雅"，但那份数据本身可能**根本不包含
> 下一层的东西** —— 这时过滤条件怎么改都是空。
> 判断方法：问一句"我要显示的东西，**在这一份数据的定义域里吗**"。

### 28.4 顺带暴露的第二个问题：软件自己的文件算不算内容

修好之后，作业文件夹里的 4 个文件都会列出来 —— 包括 `homework.json`。
这引出一个必须回答的设计问题：**软件自己的元数据文件要不要显示？**

两个选择都有坑：

| 选择 | 好处 | 坏处 |
| --- | --- | --- |
| 不显示 | 界面干净 | **用户看到文件夹里"少了东西"，以为软件藏了文件** |
| 显示，和普通文件一样 | 完整、诚实 | 用户可能删它 —— 而删掉会让这条作业**悄悄丢掉 DDL 与提交网址** |

**这个关联用户是看不出来的**：`homework.json` 这个名字和"DDL 显示在表格里"
之间没有任何可见的联系。所以第三个选择才对：

**显示，但明确标注它是"软件的东西"。**

```python
# models.py：按项目既有的 is_summary / is_intro 模式加一个 is_meta
#: 软件自己的内部文件（例如作业的 homework.json）。
#: 这些文件**必须能列出来**（用户打开作业文件夹时要看到里面的东西），
#: 但它们是元数据、不是用户内容，界面应置灰并禁止改名/删除，
#: 计数也不该把它们算成条目。
is_meta: bool = False

@property
def kind_label(self) -> str:
    if self.is_meta:
        return "作业信息"
    ...
```

```python
# file_table.py：置灰 + 说明用途
if item.is_meta:
    # 软件自己的内部文件（如作业的 homework.json）：
    # **必须列出来**（用户要能看到作业文件夹里的东西），
    # 但置灰表示"这不是你的内容，别动它"。
    name_item.setForeground(QBrush(QColor("#8A8F98")))
    name_item.setToolTip(
        "这是软件用来记录这条信息的文件（DDL、提交网址等），"
        "不是你的作业内容，请勿删除或改写。"
    )
```

```python
# book_view.py：右键菜单直接不给改名/删除入口
if item.is_meta:
    actions.extend([
        None,
        ("查看内容（只读）", lambda: self.open_file(item.path)),
        ("在资源管理器中显示", lambda: file_ops.reveal_in_explorer(item.path)),
        None,
        ("这是软件的作业信息文件，只读、不可改动", None, False),   # 禁用项
    ])
    menu = common_menu(self, actions)
    menu.exec(global_pos)
    return
```

> **"隐含关联"是危险的设计**：当 A 文件的存在决定了 B 界面能显示什么，
> 而用户在界面上**看不到这个联系**时，就必须用"置灰 + 说明 + 去掉危险入口"
> 三件事把它说清楚。否则用户删了一个"没用的 json"，
> 第二天发现 DDL 全没了，只会认为是软件的 bug。

### 28.5 一个"计数口径"的连带确认

这个 bug 和第 26 章（计数一致）有同一个根源的两个侧面，所以修完要**同时确认**：

```
标签计数 homework = 1   ← 作业个数
作业个数           = 1
实际内部文件总数   = 4   ← 4 个文件只算 1 个作业
进入作业后表格行数 = 4   ← 进去之后要看的就是 4 行
```

**三个数字都对，而且互不矛盾**：
"根目录 1 行"和"里面 4 行"不冲突 —— 它们是两个层级。
这也说明第 26 章定的口径（**标签数字 = 点进去能看到几行**）
需要补一句限定：**指的是点进这个栏目本身，不是点进某一项里面。**

### 28.6 测试这一章要写什么

核心断言只有一条，但必须写得**具体到"本地有几个文件就显示几行"**，
否则很容易写出"看起来过了其实没测到"的测试：

```python
_assignment_dir.mkdir(parents=True, exist_ok=True)
(_assignment_dir / "第一次作业.md").write_text("# 作业\n", encoding="utf-8")
(_assignment_dir / "老师发的图1.png").write_bytes(b"\x89PNG\r\n\x1a\n")
(_assignment_dir / "老师发的图2.jpg").write_bytes(b"\xff\xd8\xff")
(_assignment_dir / "homework.json").write_text("{}", encoding="utf-8")
...
window.book_view.enter_folder(_assignment_dir)
_inner_names = [hw_table.item(r, 0).text() for r in range(hw_table.rowCount())]

check("进入作业文件夹后列出本地全部文件（不再空白）",
      len(_inner_names) == 4, str(_inner_names))
check("作业文件夹里的图片也显示出来了",
      "老师发的图1.png" in _inner_names and "老师发的图2.jpg" in _inner_names, ...)
check("进入作业后 homework.json 也列出来（用户要能看到文件夹里的东西）",
      "homework.json" in _inner_names, ...)
check("退回作业栏目根目录后仍是「一个作业一行」",
      not any(name.endswith(".json") for name in _back_names), ...)
```

**最后一条很重要**：修"进去要看到文件"时，
很容易把"根目录一个作业一行"也一起改坏。**两个方向都要断言。**

写测试时又踩了一个小坑，顺手记下：

```python
check("右键内部文件时没有「删除」入口",
      not any("删除" in text for text in _meta_actions), ...)
```

这条一开始**失败**了 —— 因为那条**禁用项的文案**里写了"不能改名或删除"，
于是"删除"两个字被匹配到了。改成「只读、不可改动」后既通过，
文案也更直接。**断言用的关键词要避开"说明文字里可能顺带提到它"的情况。**

### 28.7 复盘

| 类别 | 内容 |
| --- | --- |
| 修 bug | 作业栏目进入子文件夹后改用 `list_folder` 列真实内容（不再恒空） |
| 新增模型字段 | `BookItem.is_meta`（按既有 `is_summary`/`is_intro` 模式） |
| 新增界面行为 | 内部文件置灰 + 类型「作业信息」+ 悬浮说明 + 右键无改名/删除 |
| 新增测试 | 16 条（核心 7 + 界面 9），含"退回根目录仍是一行"的反向断言 |
| 学到的 | ①进下一层要换数据来源；②隐含关联要显式说明；③断言关键词要避开说明文字 |

**这一章最值钱的一条**：

> **"数据在、界面说没有"是最伤信任的一类 bug —— 用户会以为东西丢了。**
>
> 它的技术根因往往很小（一个恒为假的过滤条件），
> 但排查时要**先把"这一层该显示什么"量出来**，
> 再问"这份数据的定义域包含这些东西吗"。
> 单看代码那几行是看不出问题的 —— 因为那个过滤条件**写得很合理**，
> 只是它作用在了一份不包含目标的数据上。

---

## 第 29 章　"附件上传"：当需求的名词实现不了时怎么办

### 29.1 需求里的字面陷阱

> AI助手新增附件上传功能 如果无法实现，想一个替代方案

用户很聪明，自己留了后路（"如果无法实现"）。而事实确实是：
**"上传"这个词在这个软件里没有对应的动作**。

先查清约束（这一步必须做，否则会写出假功能）：

```
用户可用的 AI：
  deepseek_api   supports_vision = False   ← 文本模型，API 收不了文件
  gpt_api        supports_vision = True    ← 但没配密钥
```

聊天接口是 `chat_with_fallback(messages)`，`ChatMessage` 只接受
``content: str`` 和 ``images: list[str]``。**没有任何"文件"字段**，
也没有一个标准能把"一个 PDF"塞进这个接口。

### 29.2 把需求拆成"用户要什么"和"能用什么"

关键的一步是**把名词（上传）换成目标（让 AI 看到内容）**：

> 用户真正想要的不是"上传"，而是**"让 AI 看到这个文件里的东西"**。

换成这个说法之后，方案就自己出来了 —— 因为"看到内容"有两种手段，
而且**各有所长**：

| 类型 | 做法 | 为什么这样选 |
| --- | --- | --- |
| PDF / Word / PPT / Excel | **本地提取正文**，转成 Markdown 一起发 | 确定性：PDF 有文字层、docx 有结构化段落，**同一份文件每次都得到同样结果**；离线、免费、用户能自己核对 |
| 图片 | 视觉模型，或人工粘贴 | 图片没有可提取的文本层，只能靠"看" |

**这里有一个值得展开的判断**：文档内容为什么不也交给 AI 去"看"？

因为那会把一件**确定性的事变成概率性的事**。
`pdfplumber` 提一份有文字层的 PDF，结果是确定的、可复现的、可核对的；
而让模型"读"同一份 PDF（如果它支持），结果是概率性的、
可能每次不同、还可能悄悄漏掉一页。

> **能用确定性方法解决的事，不要交给 AI。**
> AI 应该用在"没有确定解法"的地方（识别潦草手写、理解模糊表述），
> 而不是用在"本来就能精确算出来"的地方。

项目里早就有这个能力（第 11 章提到过）：`document_reader.extract()`
支持 `.pdf .docx .pptx .xlsx .csv .md .txt .doc .ppt .xls`
以及图片，返回一个 `ExtractedDocument(path, markdown, kind, reliable, notes, ...)`。
**所以这一章的新代码主要是"接线"和"如实告知"，不是解析。**

实测各类文件的提取质量：

```
md:   kind=text    reliable=True  len=11
csv:  kind=xlsx    reliable=True  len=33
xlsx: kind=xlsx    reliable=True  →  | 科目 | 分数 |
                                     | 数学 | 95 |
docx: kind=docx    reliable=True  →  讲义\n\n第一段内容
```

### 29.3 服务层：一个纯函数搞定"这份附件能不能用"

和上一章同一个套路：**判断逻辑做成纯函数**，不碰界面、可以穷举测试。

```python
@dataclass
class Attachment:
    path: Path
    kind: str = KIND_TEXT          # text / image / unsupported
    markdown: str = ""             # 提取出来的正文
    original_chars: int = 0        # 截断前的字数
    truncated: bool = False
    reliable: bool = True
    error: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        """这份附件能不能真的给 AI 提供信息。"""
        return self.kind == KIND_TEXT and self.has_text
```

`describe()` 给用户看一行状态（`已提取 1234 字（原文 5000 字，超出部分未发送）`），
`build_attachment_block()` 把所有附件拼成一段可以直接塞进提示词的文本。

**写这一层时踩到的一个坑**（值得记）：最初判断"有没有内容"用的是
"`markdown` 非空"。结果传一个 `.xyz` 文件进去，它被判成
`kind=text, usable=True, 已提取 21 字` —— 而那 21 个字其实是
`document_reader` 写的一句说明：

```
> 暂不支持的文件类型：`怪东西.xyz`
```

**这句说明会被当成正文喂给 AI**：白占 token，还会误导它。
而且这种错误**不会报错**，只会让回答质量悄悄变差。

修法是"双保险"：

```python
# 1) reader 自己会标 kind="binary"（不认识的类型）
is_binary = str(getattr(document, "kind", "")) == "binary"

# 2) 再按**内容**兜底：万一将来换了措辞或注册了新 reader，
#    句首的引用行仍然能识别出来
unsupported_markers = ("无法解析的文件类型", "暂不支持的文件类型")
looks_like_notice = any(
    markdown.lstrip().startswith(f"> {marker}") for marker in unsupported_markers
)
```

> **教训**：判断"有没有内容"时，**不能只看"非空"**。
> 库返回的"失败说明"也是非空的字符串。
> 凡是"由外部库返回的可变文本"，都要想一下"它失败时会返回什么"。

### 29.4 界面层：一条原则 —— 不假装读过

附件区就是一个按钮加一条标签行：

```python
self.btn_attach = QPushButton("附件")
self.btn_attach.setToolTip(
    "添加附件给 AI 看：\n"
    "· PDF / Word / PPT / Excel / CSV / 文本 / 代码 → **本地提取正文**后一起发送；\n"
    "· 图片 → 需要视觉模型（或用「工具 → 图片提取为 Markdown」）"
)
```

真正重要的是**三种状态都要说清楚**：

```python
class _AttachmentChip(QFrame):
    """输入框上方那一条附件标签（名字 + 状态 + 删除按钮）。"""
    ...
    # 状态直接写出来 —— 用户必须知道"这份附件到底传没传进去"，
    # 否则会相信一个其实没读过文件的回答。
    state = QLabel(item.describe())
    if item.kind == attach.KIND_TEXT and item.usable:
        state.setStyleSheet("color: #1B7F3B;")     # 绿：真的读到了
    else:
        state.setStyleSheet("color: #B26A00;")     # 橙：没读到，要处理
```

图片加进来时**明确弹窗警告**（这是最关键的一处）：

```python
def _warn_about_images(self, images):
    vision = self._vision_provider_label()
    if vision:
        common.info(..., f"会用「{vision}」直接识别（已在设置里允许发送图片）。")
        return
    common.warn(
        self,
        f"{names}\n\n"
        "**这些图片的内容不会包含在对话里** —— 当前的 AI 看不了图片。\n\n"
        "你有两个办法：\n"
        "1. 在「设置 → AI」里勾选「允许把图片发送给 AI」，"
        "并配一个支持视觉的模型；\n"
        "2. 用「工具 → 图片提取为 Markdown」先把图片转成文字，"
        "再把生成的 md 作为附件发给我。",
        "图片没法直接发送",
    )
```

并且**在提示词里也如实说明**：

```python
if attachment.kind == KIND_IMAGE:
    blocks.append(
        f"{head}\n"
        "（这是一张图片，**内容没有包含在本次对话里**："
        "当前 AI 模型看不了图片。……）"
    )
```

**为什么要在提示词里也说一遍**（而不只是弹窗告诉用户）：
因为弹窗关掉就忘了，而提示词里的这句话会让模型**主动承认自己看不到**，
而不是对着一个文件名编内容。用户随后看到的回答里就会带着
"我看不到这张图"，**这句话本身就是最后一道防线**。

如果一份可用的附件都没有，开场白也换掉：

```python
if usable:
    intro = ("用户上传了 N 份附件，下面是它们的内容。"
             "请**基于这些内容**回答，不要假装读过没给到你的部分。\n\n")
else:
    intro = ("用户上传了 N 份附件，但**没有任何一份的内容成功传给了你**"
             "（原因见下）。请如实告诉用户你看不到这些文件，"
             "并建议他改用能读取的方式，不要编造文件内容。\n\n")
```

### 29.5 两个体验上的决定

**① 附件放在用户消息里，不放在系统提示词里。**

```python
# 附件内容拼进**这一条**用户消息里，而不是塞进系统提示词 ——
# 这样它只影响本次提问，不会在后续对话里反复占用上下文。
block = self.attachment_block()
payload = f"{text}\n\n{block}" if block else text
...
messages[-1] = ChatMessage(role="user", content=payload,
                           images=self._vision_image_paths())
```

**② 发送后清空输入区的附件。**

```python
# 附件内容已经进了聊天记录（后续追问仍能看到），
# 所以把输入区的附件**清掉**：否则用户每问一句都会重发一遍全文，
# 既烧 token 又会把上下文挤满、让回答变差。
if self.attachments:
    self.clear_attachments()
```

**"发送后清空"是个容易做错的地方**：不清空看起来"贴心"（用户还能再发），
但一次 20000 字的附件在十轮对话里就是 20 万字，模型早就被淹了。
**用户看不到 token 在燃烧，所以这个决定必须由实现者来做。**

顺带加了截断与上限，而且**截断必须说出来**：

```python
#: 单个附件最多送进对话的字符数。
#: 取 20000 是因为：一份 20 页的讲义正文大约就是这个量级，
#: 再长的部分对问答帮助有限，却会把上下文挤满、让回答变差。
DEFAULT_PER_FILE_CHARS = 20_000
DEFAULT_TOTAL_CHARS = 60_000
```

状态里会写 `已提取 100 字（原文 5000 字，超出部分未发送）`。

### 29.6 这一章最有价值的一段：查一个"测试自己坏了"的假象

写测试时遇到一个**极难查的假象**，值得单独讲，因为它会浪费掉一整天。

**现象**：附件内容明明拼进了用户消息（断言通过），
但——

```
[FAIL] AI 的回复正常显示 -> ['这份讲义讲了什么？', '']
[FAIL] 回答完成后不再处于忙状态 -> False
```

AI 的回答是空的、界面一直停在"忙"。看着**完全像产品代码的 bug**。

**排查过程**（一路都在怀疑产品代码，全部落空）：

1. 打桩被调用了吗？→ 是的（`task_runs=1`）；
2. 桩抛异常了吗？→ 没有（`finally` 都没执行完，说明卡在别处）；
3. `finished_ok` 发了吗？→ 挂上探针，**一个信号都没收到**；
4. 换个最小例子：**裸 `QThread`，什么都不做，只 emit 一个信号** ——
   `processEvents()` 循环里也收不到。

到第 4 步才确认：**问题不在被测代码，而在"怎么等"**。

**根因**：

```python
# 离屏（offscreen）平台上，processEvents() 不会派发跨线程排队信号
for _ in range(300):
    app.processEvents()        # ← 收不到后台线程 emit 的信号
    time.sleep(0.01)
    if worker.isRunning(): break
```

实测三种写法（同一个 `QThread`，只发一个信号）：

| 等待方式 | 结果 |
| --- | --- |
| `for: app.processEvents()` | **收不到** |
| `QEventLoop.exec()`（用 `QTimer.singleShot` 定时退出） | 收到 |
| 先 `thread.wait()` 再 `processEvents()` | 收到 |

**为什么这个假象特别危险**：
它**没有任何报错**，表现是"界面一直忙"，
而这**恰好也是产品代码真出 bug 时的表现** ——
于是你会去翻产品代码，越翻越糊涂。
更糟的是：测试里那个桩根本没生效、**真的去调了网络**
（所以日志里出现过 "AI 调用失败"），这又会把你引向"是不是密钥问题"。

**修法**：给测试加一个"泵事件循环"的辅助函数，凡是要等后台线程的地方都用它：

```python
def pump(ms: int = 200) -> None:
    """让事件循环真的转起来一段时间。

    **为什么不能只用 app.processEvents()**（这是个真坑，查了很久）：

    离屏（offscreen）平台上，processEvents() **不会派发跨线程排队信号** ——
    后台线程 emit 出来的 finished_ok 会一直排队，槽函数永不执行。
    表现为"任务明明跑完了、界面却一直显示正在处理"，
    而且**没有任何报错**。更糟的是它会让人误判被测代码有 bug。
    """
    loop = QEventLoop()
    QTimer.singleShot(max(0, int(ms)), loop.quit)
    loop.exec()
```

顺手把**已有的天气测试也改成了 `pump`** —— 它用的是同一套写法，
只是碰巧因为时序而对（属于"早晚会偶发失败"的那类测试）。

并且把这个坑写进了 `gwp/ai/worker.py` 的模块文档里 ——
**那是下一个在这个项目里写测试的人最先会打开的文件**。

> **这一节的通用经验**：
> 当一个测试"看起来在测产品 bug"时，**先验证测试基础设施本身**。
> 最快的办法是**构造一个最小的、确定正确的例子**（裸 QThread 发一个信号），
> 看它在这个测试环境里能不能工作。
> 如果连最小例子都不工作，那就不是产品的问题。
>
> 另外：**"没有报错但结果不对"的测试基础设施问题，比产品 bug 更值得优先怀疑** ——
> 因为它会持续产生假信号，污染后面所有的判断。

### 29.7 复盘

| 类别 | 内容 |
| --- | --- |
| 新增服务层 | `gwp/services/attachment.py`：提取、截断、拼块、状态文案 |
| 新增界面 | `chat_panel` 加「附件」按钮 + 附件条 + 移除/清空 |
| 新增行为 | 图片缺视觉模型时明确警告并给替代做法；发送后清空附件 |
| 新增配置 | `ai.attach_chars_per_file`（20000）/ `ai.attach_chars_total`（60000） |
| 补齐覆盖 | `ChatPanel` 此前**完全没有测试**，本次一并补上 |
| 新增测试 | 46 条（核心 27 + 界面 19） |
| 顺带修 | 测试里等后台线程的方式（`pump`）；天气测试同款隐患 |
| 学到的 | ①需求名词≠设计单位；②确定性的事别交给 AI；<br>③"非空"不等于"有内容"；④先怀疑测试基础设施 |

**这一章最值钱的两条**：

> **一、"用确定性方法能解决的事，不要交给 AI。"**
>
> 提取 PDF 正文是确定性的（每次结果一样、可核对），
> 让 AI 去看 PDF 是概率性的（可能漏、可能编）。
> AI 该用在没有确定解法的地方 —— 识别潦草手写、理解模糊表述 ——
> 而不是用在本来就能精确算出来的地方。
>
> **二、当测试"看起来在测产品 bug"时，先验证测试本身。**
>
> 构造一个最小的、确定正确的例子。如果最小例子在同样的等待方式下
> 也收不到信号，那问题就在"怎么等"，不在"被测的代码"。
> 这类问题没有任何报错，却会持续产生假信号，
> **污染你后面所有的判断** —— 它比一个普通 bug 更该优先解决。

---

## 第 30 章　"关闭"不等于"退出"：一个由优化引出的新问题

### 30.1 需求

> 考虑到软件启动慢 当主界面关闭，软件在后台运行，
> 除非用户手动用任务资源管理器将其任务终止

用户给的方案很直接（而且自己补了后路）：**别退出，留在后台**。

### 30.2 先量：到底慢不慢

动手前先量一遍启动耗时（这一章的第一个教训就在这里）：

```
  import PyQt6.QtWidgets                  0.03s
  create_application                      0.14s
  bootstrap（日志/配置/路径/库/缓存）        0.01s
  MainWindow 构造（建所有控件）             0.26s
  show + 首次布局                          0.44s
  后台预扫描完成                            6.27s   ← 看着很慢
  >>> 到"能看见界面"为止: 7.15s
```

**6.27 秒的预扫描**看着是罪魁祸首。但单独测一下扫描本身：

```
  subjects(refresh=False)    0.03s  科目 7
  subjects(refresh=True)     0.03s  科目 7
  全数据目录节点总数: 75
```

**扫描只要 0.03 秒。** 那 6.27 秒是**测量方式**造成的假象 ——
`processEvents()` 在离屏下不派发 `StartupWorker` 的跨线程信号
（**第 29 章刚踩过的同一个坑**），所以循环一直等到 200 次用光才退出。

> **这一节的价值在于"先量"**：如果不量就动手优化，
> 很可能去优化一个只用 0.03 秒的扫描，而真正该做的是
> "让窗口从隐藏状态回来"（那才是用户感知的部分）。
> 顺带也说明：**同一个坑会在不同地方重复出现** ——
> 上一章刚记下"测试里别用 processEvents 等后台线程"，这一章量启动时又踩了一次。

所以真实情况是：**界面 0.89 秒就出来了，启动并不算慢**。
但用户的感受是真的 —— 冷启动要重建整个界面并预热，而"从后台唤回"
只是把窗口显示出来。**留在后台在感知上确实接近免费**，方案是成立的。

### 30.3 实现：一个 `hide()` 加一个标志位？

代码量很小。核心就一行：

```python
if (
    not self._really_quit
    and self._close_to_background_enabled()
    and self.hide_to_background()
):
    event.ignore()              # 不真正关闭窗口，只是藏起来
    return
```

**但真正的难点不在这一行，而在三个"如果不做就会出问题"的地方。**

### 30.4 坑一：Qt 会在最后一个窗口关闭时退出

第一个必须处理的：

```python
# app.py 的 create_application 里
# **绝不允许"最后一个窗口关闭就退出"**。
# 原因：主窗口关闭时会隐藏到后台（需求），如果 Qt 在这里自动退出，
# 进程会立刻死掉，"后台驻留"就完全失效 —— 而且表现为
# "点了关闭软件就没了"，看起来就像隐藏功能没实现。
# 放在 create_application 而不是 run() 里，是为了让测试也走同一条路径。
app.setQuitOnLastWindowClosed(False)
```

**这个坑的特点是"看起来生效了、其实没生效"**：
窗口确实隐藏了，然后进程立刻退出 —— 用户看不到任何区别。

### 30.5 坑二：托盘不可用时不能静默退化

进程留在后台，就必须有**回收路径**。标准做法是系统托盘图标：

```python
def _ensure_tray(self) -> QSystemTrayIcon | None:
    """按需创建托盘图标。

    延迟创建（而不是启动时就建）有两个好处：
    * 不占启动时间；
    * 托盘只在"真的用到后台运行"时才出现，不会平白多一个常驻图标。
    """
```

但托盘**可能不可用**（远程桌面、某些系统策略、精简版 Windows）。
我第一版的处理是"不可用就返回 False，让调用方真正退出"。
写测试时才发现这很糟：在离屏环境里托盘不可用，于是
**关闭事件直接放行 → 进程退出 → 整个功能等于没有**。

改成降级：

```python
tray = self._ensure_tray()
if tray is None:
    # 降级：最小化而不是隐藏，保住任务栏入口
    self.showMinimized()
    self.show_status("托盘不可用，已最小化到任务栏；再双击一次快捷方式也能唤回")
    log.info("托盘不可用，改为最小化到任务栏（进程继续运行）")
    return True
```

> **降级要"保住用户能操作的东西"，而不是"悄悄少做一件事"。**
> 隐藏窗口没有托盘 = 用户彻底失去入口；
> 最小化到任务栏至少还有一个可点的地方。

### 30.6 坑三（最重要）：改掉"关闭"的含义，就必须补回"退出"

这是这一章真正想讲的。

一旦 `✕` 从"退出"变成"藏起来"，**"退出"这个动作就消失了**。
而菜单里原来那一项是这么写的：

```python
self._add_action(menu, "退出", self.close, QKeySequence.StandardKey.Quit)
```

它接的是 `self.close` —— 加了后台驻留之后，点「退出」**也只会藏起来**。
用户想关掉软件，会发现**怎么点都关不掉**（除了任务管理器）。

这比启动慢糟糕得多：**启动慢只是慢，退不掉是失控。**

所以完整的实现是**三件套**：

| 能力 | 给谁 |
| --- | --- |
| `✕` = 隐藏到后台 | 让"下次打开"变快 |
| **托盘图标**（双击唤回 / 右键「完全退出」） | 一个看得见的回收路径 |
| 菜单「文件 → 退出」+ **「文件 → 隐藏到后台」** | 把两个动作**都**摆出来 |

```python
# 「隐藏到后台」与「退出」要分开、并且都写明白：
# 开了后台驻留后，点窗口的关闭按钮 = 隐藏（不是退出），
# 所以菜单里必须有一个**明确的**退出入口，否则用户会以为退不掉。
self.act_hide_background = self._add_action(
    menu, "隐藏到后台（继续运行）", self.hide_to_background, ...)
self.act_hide_background.setVisible(self._close_to_background_enabled())
self._add_action(menu, "退出", self.quit_completely, QKeySequence.StandardKey.Quit)
```

**并且退出逻辑只有一份**：

```python
def quit_completely(self) -> None:
    """真正退出进程（托盘菜单入口 / 程序化退出）。

    置标志位后走 close()，让 closeEvent 里的
    "确认未保存文档 → 清理 → 释放资源"这条既有链路照常执行，
    不另写一份退出逻辑（两份一定会不一致）。
    """
    self._really_quit = True
    if self._tray is not None:
        self._tray.hide()
    self.close()
```

**注意 `closeEvent` 里隐藏分支的位置** —— 它必须在"检查未保存文档"**之后**：

```python
# 1) 检查未保存的文档
for view in list(self._documents):
    if not view.confirm_close():
        event.ignore()
        return

# 1.8) **隐藏到后台**（需求：主界面关闭后进程继续运行）。
#      放在"检查未保存文档"之后：有未保存内容时仍要先问用户，
#      不能因为"反正不退出"就跳过保存确认。
if not self._really_quit and self._close_to_background_enabled() \
        and self.hide_to_background():
    event.ignore()
    return

# 2) 保存聊天记录并按配置清空
cleanup_on_exit(self.context)
...
```

**"隐藏"能跳过保存确认吗？** 不能 —— 用户以为关闭会保存，
下次回来发现改动没了。**任何路径上的"未保存数据"都要问。**

实测确认清理时机正确：

```
隐藏到后台时清理被调用: []            ← 隐藏不等于退出
隐藏后清理调用记录:   []              ← 仍然没有
quit_completely 后:  ['cleanup_on_exit']   ← 真正退出才清理
```

> **这一节的通用规律**：
> **凡是把某个常用操作的含义改掉，就必须同时提供它原来的含义。**
>
> 改掉 `✕` 的含义 → 补一个明确的「退出」。
> 改掉"保存"的含义（比如改成异步）→ 补一个"确认已保存"的反馈。
> 改掉"删除"的含义（比如改成软删除）→ 补一个"彻底删除"。
>
> 否则你优化的那个功能会**吞掉**另一个功能，
> 而用户只会总结成一句："这软件关不掉了。"

### 30.7 坑四：检查顺序引出的一个真回归（而且是危险的）

需求里还有一条隐藏要求：**"再双击一次快捷方式就能唤回窗口"**
（否则用户只能靠托盘，托盘的发现性并不好）。

原来的启动顺序是：**先建 MainWindow，再做单实例检查**。
于是第二个实例会白白把整个界面建一遍才走到"唤回"那一步 ——
实测**要 8.1 秒**，用户双击后 8 秒窗口才出来，体验完全不对。

所以我把它改成"**先检查、再建界面**"：

```python
# 先做单实例检查，再决定要不要建界面
existing = running_instance(context.paths.else_data)
if existing is not None:
    ...
    return EXIT_ALREADY_RUNNING
```

**然后我制造了一个比原来的问题更严重的回归**：
单实例检查**不再抢锁**了。原来的 `check_single_instance()` 会真的
`acquire()` 一个锁；而 `running_instance()` 只是**读一下**。
两个进程如果几乎同时启动，都会读到"没人占"→ **两个主窗口都建出来**。

真机测试立刻暴露了它（日志里两次"预扫描完成"，进程数 4）：

```
  进程数（父+子算一个）: 2    ← 期望
  实际: 4                     ← 两个独立实例
```

**修法**：早期检查也必须走**抢锁**那条路，而不是读锁：

```python
# **顺序很重要**（这里踩过一个回归）：原来先建 MainWindow、再检查单实例……
# 但**不能只是"读一下锁"**（那样等于没抢）：必须真的走
# check_single_instance 把锁拿到手，否则两个进程可能同时判定
# "没人占" —— 结果是**两个主窗口都建出来**，比慢一点严重得多。
already_running = check_single_instance(context, hwnd=0)
if already_running is not None:
    ...
    return already_running
...
window = MainWindow(context)
hwnd = _pin_window_to_current_desktop(window)
publish_instance_window(context, hwnd)      # 锁先拿到，句柄后补
```

注意 `hwnd=0`：窗口还没建，先拿到锁，**之后再补句柄**。
这样"锁归谁"在很早就定了，`_report_already_running` 也能从锁里
读到已有实例的句柄来完成唤回。

**优化后实测**：

| 版本 | 双击快捷方式到窗口出现 |
| --- | --- |
| 优化前（先建界面再检查） | **8.1s** |
| 优化后（先抢锁再决定） | **0.3s** |

> **这一节最值得记的**：我为了"让唤回更快"动了启动顺序，
> 结果**削弱了单实例保护**。
>
> **优化一个"性能"问题时，很容易顺手改掉某个"安全/正确性"保证。**
> 所以每次改流程顺序，都要问一句：
> **"原来这个顺序保证了什么？我把它挪走之后，那个保证还在吗？"**
>
> 另一个教训：这个回归**只在真机上跑两次启动才看得出来**。
> 离屏单测全绿（因为它只测一个实例）。**该手测的地方必须手测。**

### 30.8 真机验证（离屏测不了托盘）

托盘、窗口隐藏、跨进程唤回这几件事**离屏环境都测不了**
（`QSystemTrayIcon.isSystemTrayAvailable()` 在离屏下是 False）。
所以这部分必须上真机，用 Win32 API 从外部观察：

```powershell
# 启动 -> 记下锁文件里的 hwnd -> 用 PostMessage 发 WM_CLOSE（等于点关闭按钮）
[void][W4]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
```

实测结果：

```
1) 启动:      pid=4568 hwnd=2426994 可见=True
2) 点关闭后:  进程存活=True 窗口可见=False     ← 隐藏成功、进程还在
3) 再双击快捷方式: 窗口可见=True 用时=0.3s
             原进程还在=True  进程数=2（仍是一个实例）
```

日志也印证了走的是"直接唤回、没弹提示"：

```
已有实例在后台运行，已直接把窗口唤回（未弹提示框）
```

> **"能自动化测试的部分"和"必须手测的部分"要分开**：
> 逻辑（开关两种行为、清理时机、菜单项可见性、隐藏后进程不退出）
> 全部写成断言进了测试套件；
> 而**托盘 + 跨进程唤回**只能手测，我就老老实实测一遍并把结果记下来。
> 假装它也能自动测（或者干脆不测）都会留下隐患。

### 30.9 复盘

| 类别 | 内容 |
| --- | --- |
| 新增行为 | `✕` 隐藏到后台；托盘图标（双击唤回 / 右键完全退出） |
| 新增入口 | 菜单「文件 → 隐藏到后台」；关闭事件与「退出」共用一条清理链路 |
| 新增设置 | `ui.close_to_background`（默认开）+ 首次提示只弹一次 |
| 关键修复 | `setQuitOnLastWindowClosed(False)`；托盘不可用时降级为最小化 |
| 性能优化 | 单实例检查提前到建界面之前：唤回 **8.1s → 0.3s** |
| 修回归 | 提前检查必须**抢锁**而不是**读锁**，否则会开出两个主窗口 |
| 新增测试 | 13 条（开关两种行为、清理时机、菜单项、进程不退出） |
| 学到的 | ①改掉一个操作的含义就要补回它的原义；<br>②优化性能时别弄丢正确性保证；<br>③降级要保住用户能操作的东西；④该手测的必须手测 |

**这一章最值钱的一条**：

> **凡是把某个常用操作的含义改掉，就必须同时提供它原来的含义。**
>
> 用户说"留在后台"时，他描述的是**期望**，不是完整需求。
> 完整需求是"留在后台，**而且我还能随时关掉它**"。
> 少做后半句，用户对你的评价不会是"启动变快了"，
> 而是"这软件**关不掉**" —— 一个被吞掉的功能，
> 比一个没做的功能更让人恼火。

---

## 第 31 章　单词书：交互需求如何规定数据结构

### 31.1 需求

> 在英语科目中新增单词书栏目 书内部可以添加单词卡 单词卡可折叠
> 我只需要添加英文单词/短语 就可以自动补齐中文解释/例句等等
> 单词卡折叠后只显示英语 单击后展开

读一遍，划出四件事：

1. 新的**栏目**（单词书）；
2. 新的**实体**（单词卡）；
3. **交互**：可折叠、折叠时只显示英语、单击展开；
4. **输入约定**：用户只填英文，其余自动补齐。

第 3 条看起来是纯界面要求。**但这一章主要就是讲它其实不是。**

### 31.2 第 3 条在悄悄规定数据结构

"折叠后只显示英语"这句话，翻译成设计约束是这样的：

> 每张卡必须有**一个字段**，它在折叠状态下就足以让用户认出这张卡。

于是：

* `english` 是**唯一必填字段**，也是**唯一的折叠标题**；
* 其余字段（音标 / 词性 / 释义 / 例句 / 搭配 / 记忆提示）都是**可选补充**。

**这个约束反过来让第 4 条成立了。** 想想如果不这么设计：

```
❌ 按"字段都要填"设计：
   添加单词 → 弹出表单：英文__ 音标__ 词性__ 释义__ 例句__ 搭配__
   → 用户每次加词填七八个框 → "自动补齐"这个需求根本没意义了
   → 而且"折叠后只显示英语"还得再想一个"用哪个字段当标题"
```

```
✅ 按"一个必填字段"设计：
   添加单词 → 只问英文 → 存盘 → 交给 AI 补齐
   → 折叠标题天然就是 english，不用另外决定
```

> **通用教训：交互需求经常在悄悄规定数据结构。**
> 读需求时要主动做这个翻译：
> **"界面上要这样显示" → "数据里必须有什么"。**
>
> 反过来也成立：**如果你发现某个需求实现起来别扭，检查一下数据结构是否与它冲突。**
> 这个例子里，"只显示英语"和"只填英文"其实是同一条约束的两个侧面 ——
> 认出来之后，两个需求一起就落地了。

### 31.3 一张卡一个文件

```python
#: 单词卡信息文件名。一张卡是 `wordbook/<英文>.json`（**一个文件一张卡**）。
#: 一个文件一张卡是有意的：方便单独手工改、单独拷给同学、也能直接进版本管理。
WORD_CARD_SUFFIX = ".json"
```

**为什么不放进一个大 json**：

| 方案 | 单独改一条 | 拷给同学一个词 | Git diff |
| --- | --- | --- | --- |
| 一个文件一张卡 | 直接改那个文件 | 直接拷那个文件 | 只动一行 |
| 全部塞一个 json | 要小心别改坏别的 | 得手工摘出来 | 一次改一大片 |

这和整个项目"磁盘即数据库"（第 3 章）是同一个取向：
**让磁盘上的东西本身就是可用的**，而不是"必须通过软件才能读"。

**文件名要保留词条原样**：

```python
def sanitize_english(text: str) -> str:
    """把用户输入的英文变成安全的文件名主干。

    只去掉**文件名非法字符**和首尾空白，**不改大小写、不删标点**：
    ``don't`` / ``give up`` / ``a.m.`` / ``well-known`` 都要原样保留 ——
    它们是词条本身，不是标识符。**不要在这里做"美化"**，
    否则 ``a.m.`` 会变成 ``a.m``，和词条就对不上了。
    """
```

这一条是我自己先写错、后来改回来的：第一版加了 `.strip(" .")`，
于是 `a.m.` 变成了 `a.m`。**"清理"和"破坏"之间只差一个字符**，
而判断标准是：**这个字符是数据的一部分吗？** 是，就不能动。

### 31.4 解析 AI 的回答：必须容忍脏格式

只要让模型返回 JSON，就一定会遇到这些：

```
纯 JSON                                    ✅
```json {...} ```                          ← 常见
``` {...} ```                              ← 不写语言
好的，这是结果：{...} 希望有帮助！           ← 前后有寒暄
{... 里面还有嵌套对象 ...}                  ← 需要配对扫描
这个单词的意思是放弃。                       ← 根本不是 JSON
```

**如果只做 `json.loads()`，一半的调用都会失败** ——
而用户只会看到"AI 补齐失败"，完全不知道是格式问题。

所以 `extract_json()` 分三级降级尝试：

```python
1. 去掉 ``` 围栏后整体解析；
2. 正则找第一个 {...} 片段解析；
3. 逐行扫描累积括号配对（对付多层嵌套 + 前后有杂文字的情况）。
```

第 3 级要**正确处理字符串里的花括号和转义引号**，否则会被
`{"meaning": "用 { 表示集合"}` 这种内容骗到：

```python
depth = 0
in_string = False
escaped = False
for index in range(start, len(raw)):
    char = raw[index]
    if in_string:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            in_string = False
        continue
    if char == '"':
        in_string = True
    elif char == "{":
        depth += 1
    elif char == "}":
        depth -= 1
        if depth == 0:
            ...   # 到这里才是一个完整的对象
```

测试覆盖了六种格式，全部能解析：

```
AI 回答格式「纯 JSON」能被解析              ✅
AI 回答格式「带 ```json 围栏」能被解析        ✅
AI 回答格式「围栏没写语言」能被解析          ✅
AI 回答格式「前后有寒暄」能被解析            ✅
AI 回答格式「带嵌套对象」能被解析            ✅
AI 回答格式「字段缺失」能被解析              ✅
完全不是 JSON 时明确失败（不瞎猜）           ✅
```

**但"能解析"不等于"要采信"** —— 这是下一节。

### 31.5 AI 说查不到时，不能往卡片里写

用户输入的可能是拼错的词、或者根本不存在。这时 AI 会老老实实说
"未查到该词，请确认拼写"。**这种回答不能写进卡片**，否则单词书里会积累
一堆内容是"我查不到"的卡片，看起来像有内容、其实没用。

```python
#: AI 明说查不到词时的标志（这种情况下不该把卡片标成"已补齐"）
_NOT_FOUND_MARKERS = ("未查到该词", "请确认拼写", "无法确认", "not found")

def parse_completion(text: str, english: str) -> tuple[WordCard | None, str]:
    """把 AI 的回答解析成卡片。返回 ``(卡片, 错误说明)``。

    成功时错误说明为空串。失败时**不编内容**，只给出可操作的原因。
    """
```

而且提示词里就把话说明白：

```python
1. 释义必须准确，**不确定时宁可少写也不要猜**；确实是生僻/不存在的词，
   在 meaning 里写「未查到该词，请确认拼写」。
```

**注意这是在用"让 AI 主动报告失败"来换取可靠性** ——
和第 27 章"图片提取"里"把模型的自然语言当置信度用"是同一个手法。
模型不会给你一个置信度分数，但它会很老实地告诉你"我查不到"。

### 31.6 人改过的内容不能被自动覆盖

这和"图片提取"里"人改过的正文不再被自动判死"是同一条原则，
但这里的形态是**默认只填空白字段**：

```python
def merge_into(existing: WordCard, fresh: WordCard, *, force: bool = False) -> WordCard:
    """把 AI 的新结果合并进已有卡片。

    **默认只填空白字段**（``force=False``）：用户手改过的内容不能被
    重新补齐悄悄冲掉。要看新结果得显式 ``force=True``。
    ``english`` / ``note`` / ``locked`` 永远保留用户这边的值。
    """
```

界面上对应两个不同的菜单项，**并且把后果写清楚**：

```python
("AI 补齐释义与例句", "complete"),
("重新补齐（覆盖现有内容）", "recomplete"),      # 走 confirm(dangerous=True)
```

```
重新补齐「give up」？

**会覆盖现有的释义与例句**（你自己写的笔记不受影响）。
```

> **"重新生成"类功能永远要给两个入口**：
> 一个"只补缺"（默认、安全）、一个"整个重来"（显式、说清后果）。
> 只给前者，用户改坏了没法回退；只给后者，用户改过的东西会被冲掉。

### 31.7 界面：折叠态的点击判定

单击卡片任意位置就展开。实现上有一处容易写错：

```python
def mousePressEvent(self, event) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
        self._pressed = True
        self._dragged = False
        self._origin = event.position().toPoint()      # 记住按下点
    super().mousePressEvent(event)

def mouseReleaseEvent(self, event) -> None:
    super().mouseReleaseEvent(event)
    if event.button() != Qt.MouseButton.LeftButton or not self._pressed:
        return
    self._pressed = False
    if self._dragged:
        # 拖动过就不当点击（以后加拖拽排序时不会被误触发）
        self._dragged = False
        return
    # 点在详情区里不该折叠 —— 用户可能正在选中文字
    if self._expanded and self.detail.geometry().contains(event.position().toPoint()):
        return
    self.toggle()
```

**三点**：

1. **在 release 而不是 press 里判定**（第 7 章首页卡片踩过的坑）；
2. **记住"按下点"来算拖动距离**。我第一版写成了和 `self.rect().center()`
   比较 —— 那个判断在卡片边缘怎么拖都算"点击"，完全不对。
   同一份代码在两个项目里，**这种"看起来差不多"的算错方式是重复出现的**；
3. **展开态的详情区里不响应折叠**：用户可能在选中文字准备复制，
   一点就折起来会让人很烦。

### 31.8 一个"跳过坏数据"的细节，和它引出的教训

`load_card()` 一开始复用了项目里通用的 `meta_io.read_json()`：

```python
data = meta_io.read_json(target, default=None)
```

而它是这么实现的：

```python
except (OSError, json.JSONDecodeError) as exc:
    log.warning("元数据损坏，已忽略: %s (%s)", path, exc)
    return dict(default or {})          # ← 损坏时也返回一个空 dict
```

于是**"文件损坏"和"合法但内容为空"变得无法区分**。
测试立刻抓到了后果：

```
[FAIL] 损坏的 json 被跳过而不是让整本书报错 -> ['broken', 'give up']
```

`broken.json`（内容是 `{不是合法 json`）被当成了一张
"英文为空"的卡，然后 `from_dict` 用**文件名**当兜底词条 ——
单词书里就凭空多出一张叫 `broken` 的怪卡。

修法是让 `load_card` 自己严格读、解析失败就明确返回 `None`：

```python
def load_card(path: Path) -> WordCard | None:
    """读一张卡。**读取永不抛异常**（与项目其它元数据读取一致）。

    这里**不用** ``meta_io.read_json``：它对损坏文件会返回一个空 dict，
    和"合法但内容为空的 json"就区分不开了 —— 那样一张读坏的卡会被
    当成"英文为空的卡"，然后在列表里冒出一个用文件名当词条的怪东西。
    所以这里自己读，解析失败就明确返回 ``None``。
    """
```

并且**不再用文件名兜底当词条**，而是显式校验：

```python
# **校验它真的像一张单词卡**：json 合法但内容不是卡片
# （例如用户手工丢进来的普通 json）时，不能把文件名当成词条 ——
# 那会凭空多出一张没有释义的怪卡。
if not str(card.english or "").strip():
    log.warning("跳过不像单词卡的 json：%s", entry)
    continue
```

> **教训：一个"容错"的通用函数，会把"错误"和"合法但为空"抹平成同一种东西。**
>
> `read_json` 的行为对元数据（科目、书目）是合理的：配置坏了就用默认值，
> 软件照常能用。但对"**列表项**"就不合理了 —— 列表里多出一个
> 由错误造成的空项，用户看到的是"莫名其妙多了一张卡"。
>
> **判断标准**：这个数据是"**唯一的一份配置**"还是"**一堆同类项之一**"？
> * 前者：容错返回默认值（坏了大不了用默认值）；
> * 后者：**必须能区分"这项坏了"和"这项是空的"**，然后跳过坏的。

### 31.9 复盘

| 类别 | 内容 |
| --- | --- |
| 新增数据层 | `gwp/data_manager/wordbook.py`：卡片模型、读写、AI 解析、合并 |
| 新增控件 | `gwp/ui/widgets/word_card.py`：可折叠卡片（单击展开、右键菜单） |
| 新增视图 | `gwp/ui/views/wordbook_view.py`：卡片列表、添加、补齐、搜索 |
| 接入方式 | 所有书目的栏目表加 `WORDBOOK_TAB`；模板目录加 `wordbook/` |
| 页面容器 | `BookView` 的每个标签页改为 `QStackedWidget`（文件表格 / 单词书） |
| 新增测试 | 58 条（核心 41 + 界面 17） |
| 顺带修正 | 三处既有测试的标签数量断言（新增栏目必然影响） |
| 学到的 | ①交互需求在悄悄规定数据结构；②"清理"别破坏数据；<br>③容错函数会抹平"错误"与"空"；④重新生成要给两个入口 |

**这一章最值钱的一条**：

> **交互需求经常在悄悄规定数据结构。**
>
> "折叠后只显示英语" + "我只需要添加英文" —— 这两句话看起来
> 一个讲界面、一个讲输入，其实是**同一条约束的两个侧面**：
> **英文是这张卡唯一必填的字段**。
>
> 认出这条约束之后，两个需求一起就落地了：
> 折叠标题天然是 `english`，添加表单只需要一个输入框，
> 其余全部可以后补。**如果没认出它**，就会做出一张七八个输入框的表单，
> 然后纳闷"自动补齐"这个需求该怎么塞进去。

---

## 第 32 章　两个"只在我这儿出现的 bug"

用户报了两个 bug：

> 作业栏目存在bug 1 json无法用vscode打开 2 文件操作（如删除文件）后会返回上一层页面，改成保持在该文件夹内

**它们在开发者的机器上都不会出现** —— 或者说，不会以我测试的方式出现。
这一章讲两个 bug 的根因，以及它们共同的教训。

### 32.1 Bug 1：JSON 点了没反应

#### 32.1.1 先确认代码逻辑对不对

按老规矩，先看"选择哪条路"的逻辑。用打桩记录调用了谁：

```
META_IS_META True 作业信息
DOUBLE_CLICK_CALLS [('vscode', '...homework.json')]
OPEN_FILE_CALLS    [('vscode', '...homework.json')]
```

**逻辑完全正确**：双击和右键都走了 VSCode，没走到内置查看器。
所以问题在 `open_in_vscode()` **真正执行**的那一步。

#### 32.1.2 抓真实错误

单独调一次，并且**不吞掉 stderr**：

```python
r = subprocess.run(['cmd', '/c', editor, str(target)], capture_output=True)
print(r.returncode, r.stderr)
```

```
=== 用 cmd /c 调 code.CMD（当前实现）===
返回码: 1
stderr: 'D:\VS' is not recognized as an internal or external command,
```

**一句话就定位了。** 根因是我自己写的那层 `cmd /c`：

```python
# code.cmd 是批处理，通过 cmd 调用更稳          ← 这个"更稳"是错的
command = (
    [editor, str(target)]
    if editor.lower().endswith((".exe",))
    else ["cmd", "/c", editor, str(target)]       # ← bug
)
```

`cmd /c` 收到的是 Python 拼好的命令行字符串，**它要自己解析引号**。
编辑器路径是 `D:\VS Code\bin\code.CMD`（含空格），于是 cmd 把
`D:\VS` 当成了命令名。

#### 32.1.3 为什么我一直没发现

**这个 bug 只在"安装路径含空格"时出现，而我的测试环境不含空格。**

我第一轮测试用的是临时目录：

```
editor = 'D:\\VS Code\\bin\\code.CMD'
target = 'C:\\Users\\<用户>\\AppData\\Local\\Temp\\tmpk89o1w9v\\homework.json'
Popen 返回码（None=还在跑）: 0          ← 成功！
```

**返回码 0，一切正常。** 于是我说过"VSCode 单独调用是成功的" ——
那句话在当时是**真的**，但它证明不了一台装了
`D:\VS Code\` 的机器上的行为。

> **教训一：只在"某个环境条件下"出现的 bug，必须在那个条件下构造测试。**
>
> 我用一个"干净"的路径去测，等于没测。后来的回归测试里，
> 我**刻意**用 `D:\VS Code\bin\code.CMD` 这个带空格的路径来构造命令。

#### 32.1.4 修法：把多余的中间层删掉

```python
def vscode_command(editor: str, target: Path | str) -> list[str]:
    """拼出"用 VSCode 打开文件"的命令行。抽成函数是为了**能被测试断言**。

    这里**刻意不判断扩展名、也不套任何 shell**：直接给出
    ``[编辑器, 文件]`` 两个参数，交给 Windows 自己去处理引号。
    """
    return [str(editor), str(target)]
```

于是 `open_in_vscode` 里只剩：

```python
subprocess.Popen([editor, str(target)], ...)
```

**为什么这样就是对的**：`subprocess` 在 Windows 上走 `CreateProcessW`，
它按 Windows 自己的规则给**每个参数**加引号（这是它的本职工作），
`.cmd` / `.bat` 由系统处理。**我们不需要、也不应该再套一层 shell。**

实测（把 VSCode 完全关掉，做一次决定性验证）：

```
=== 修复前（cmd /c）===
返回码: 1         Code.exe 进程数: 0      ← VSCode 根本没启动

=== 修复后（直接启动）===
返回码: 0         Code.exe 进程数: 11
窗口标题: homework.json - Visual Studio Code     ← 文件真的被打开了
```

> **教训二：返回 0 不等于任务完成。**
>
> `Popen` 只要能把进程创建出来就算"成功"，哪怕那个进程**立刻失败退出**。
> 修复前的代码**返回了 True**、界面上什么都不提示 ——
> 表现为"点了没反应"。这类"成功了但没生效"的失败最难查，因为它不留痕迹。
>
> 两条应对：
> 1. **能被断言的地方不要靠"跑起来看看"** —— 把命令拼接抽成
>    `vscode_command()`，测试直接断言"第一个参数不是 cmd、命令只有两个参数"；
> 2. **只在人看得见的地方做"尽力而为"** —— 外部程序是否真的打开了
>    无法从返回值判断，那就把**日志**写清楚
>    （`已用 VSCode 打开：…（编辑器=…）`），出问题时至少有一条线索。

#### 32.1.5 我自己的测试也写错过一次

第一版回归测试写成：

```python
check("命令不能套 cmd /c",
      not any(part.lower().endswith("cmd") for part in _cmd_line))
```

它**失败**了，因为编辑器自己就叫 `code.CMD` ——
`.lower().endswith("cmd")` 对它是 `True`。

修法是**只看第一个参数**：

```python
# 不能对整个列表做 endswith("cmd") —— 编辑器自己叫 code.CMD，
# 那样写会把正确的命令判成错的（我第一版就写错了）。
_first = Path(_cmd_line[0]).name.lower()
check(..., _first not in ("cmd", "cmd.exe") and "/c" not in _cmd_line
          and len(_cmd_line) == 2)
```

> **同一天里的第三次"我的测试写错了"**（第 31 章有两次）。
> 这说明不了测试没用，恰恰说明**测试失败时先怀疑测试**是对的：
> 这三条里有两条是测试的错、一条是真 bug，而真 bug 那一条正是靠
> "不吞掉 stderr"抓出来的。

### 32.2 Bug 2：删完文件被弹回上一层

#### 32.2.1 复现，并注意一个细节

```
进入作业文件夹后: cur=2.4 作业 rows=['2.4 作业.md', 'homework.json', '图.png', '笔记.md']
      标题='英语1 › homework / 2.4 作业' 上一层按钮可见=True
删除 图.png ...
删除后: cur=2.4 作业 rows=['2.4 作业']            ← 变成上一层的内容了！
      标题='英语1 › homework / 2.4 作业'           ← 标题还是对的
      上一层按钮可见=True                          ← 位置状态也是对的
```

**注意这个细节**：`_current_folder` 和标题**一直是对的**，
只有**表格内容**错了。

所以这个 bug 的现象不是"位置跳了"，而是**"位置没变、但东西变了"** ——
界面上自相矛盾。这也解释了为什么它容易被误判（我一开始还怀疑是删除事件
触发了什么重置逻辑）。

#### 32.2.2 根因：刷新只覆盖了两处显示中的一处

`_delete_item` 之后调 `refresh()`，而 `refresh()` 做的是：

```python
self._tables["root"].set_items(items)                    # 全部条目：根目录
for key, _title, folder in self._tab_defs:
    if not folder or key not in self._tables:
        continue
    self._tables[key].set_items(
        self.context.library.list_folder(book.path / folder)   # 各标签：根目录
    )
```

**全是"根目录"。** 而 `enter_folder()` 设的 `_current_folder` 是**第二层视图**，
`refresh()` 里根本没有考虑它 —— 于是表格被填成了根目录的列表。

> **这一条值得单独记**：
> **当一个状态在界面上有两处体现时（这里是"标题"和"表格内容"），
> 刷新只更新了其中一处，就会产生自相矛盾的界面。**
>
> 用户看到标题写着"2.4 作业"、列表却列着作业名 —— 他会说
> "怎么跳回上一层了"，因为**列表比标题更有存在感**。

#### 32.2.3 修法：在 refresh() 末尾统一收口

```python
# **重新画出"当前所在文件夹"的内容**（用户报障：删除文件后会跳回上一层）。
#
# 上面的代码只填了**各标签的根目录**；如果用户是靠 enter_folder()
# 进到某个子文件夹里，那么刷新后表格里就变成了根目录的列表 ——
# 看起来就是"被弹回上一层"。
#
# 凡是"在某个目录里做的操作"（删除、重命名、导入、拖拽、新建文件夹）
# 都要走 refresh()，所以修在这里能一次覆盖全部操作。
if self._current_folder is not None:
    self._render_current_tab()
```

**为什么修在这里、而不是在 `_delete_item` 里补一句？**

因为"在某个目录里做的操作"有一串：删除、重命名、导入文件、
拖拽上传、新建文件夹…… **它们最后都会调 `refresh()`。**
在 `refresh()` 里收口，一次覆盖全部；
在每个操作后面各补一句，就会漏 —— 而且**漏的那个很难发现**
（用户得逐个功能试一遍）。

> **教训：修 bug 要修在"所有出问题路径的公共汇合点"，而不是出问题的那一条路径上。**
>
> 用户只报了"删除"，但同一个根因会影响所有走 `refresh()` 的操作。
> 如果我只在 `_delete_item` 里补一句，用户过两天会来报
> "导入文件后也会跳回上一层" —— 而那是**同一个 bug 的第二次表现**。

#### 32.2.4 测试也要用真实删除

第一版 GUI 用例**假失败**了：

```
[FAIL] 删除后目标文件从列表里消失
       -> ['homework.json', '待删除的附件.md', ...]     ← 文件还在
```

因为我为了"不污染用户回收站"把 `delete_path` 打了桩 ——
**文件根本没被删掉**，那自然测不出"列表里少了它"。

而"留在当前文件夹"和"文件真的消失了"是**两件不同的事**，
只测前者会漏掉后者。改成真实删除（数据都在临时目录里，删掉无副作用）后：

```
[PASS] 删除动作真的把文件从磁盘移走了
[PASS] **删除文件后仍留在该文件夹内**（不跳回上一层）
[PASS] 删除后表格里是该文件夹的内容，而不是上一层的列表
[PASS] 删除后目标文件从列表里消失
[PASS] 同文件夹里的其它文件还在（没被连带清掉）
```

> **打桩要打在"不关心的部分"，不要打在"要验证的部分"。**
> 这里要验证的是"删完之后界面留在哪"，所以我该打桩的是
> **界面之外**的东西；而"文件是否真的消失"正是行为的一部分，
> 打桩它就等于把这个断言删掉了。

### 32.3 复盘

| 类别 | 内容 |
| --- | --- |
| Bug 1 根因 | `cmd /c` 调 `.cmd` 时，cmd 自己解析引号 → 含空格路径被拆断 |
| Bug 1 修法 | 去掉 `cmd /c` 那层，让 `subprocess` 直接启动（新增 `vscode_command()`） |
| Bug 2 根因 | `refresh()` 只重填各标签的根目录，没重画"当前所在文件夹" |
| Bug 2 修法 | `refresh()` 末尾统一收口：在文件夹里就重画该文件夹 |
| 新增测试 | 16 条（VSCode 命令拼接 6 条 + 删除后留在原文件夹 5 条 + 既有断言更新） |
| 学到的 | ①只在特定环境出现的 bug，要在那个环境构造测试；<br>②返回 0 不等于任务完成；<br>③一个状态有两处显示，刷新只更新一处就会自相矛盾；<br>④修在所有路径的汇合点，不修在报障那一条；<br>⑤打桩别打在要验证的那部分 |

**这一章最值钱的两条**：

> **一、只在"某个环境条件下"出现的 bug，必须在那个条件下构造测试。**
>
> 我在 `C:\Users\...\Temp\` 里测试，全是好的；用户的路径里有空格，100% 失败。
> 用干净数据测试，会得到一个"看起来通过"的结论 —— 这比没测试更危险，
> 因为它给了你虚假的信心。

> **二、修 bug 要修在"所有出问题路径的公共汇合点"。**
>
> 用户只报了"删除后会跳回上一层"，但同一个根因会让
> 删除、重命名、导入、拖拽、新建文件夹**全都**跳回上一层。
> 修在 `refresh()` 里一次全好；修在 `_delete_item` 里，
> 用户过两天会拿"导入文件也会跳"再来找你一次。

---

## 第 33 章　把"自由度"收掉：固定宽度与就近跳转

需求两句话，看起来只是两个小改动：

> 调节日程栏宽度固定，只有全部折叠和完全展开 不能调整宽度
> 日程栏打开按键点击后在软件内打开对应 Book 的 homework 栏目，不是打开本地文件夹

**第一句是"把已经给出的自由度收回去"，第二句是"换一个更近的目的地"。**
两句都值得单独写，因为它们反映的不是功能缺失，而是**设计的取舍被用户修正**。

### 33.1 "不能调整宽度"其实是在说"我不需要这个自由度"

原来的实现是一个普通 `QSplitter`：用户可以把日程栏从 336px 拖到 480px。

**我当初为什么允许拖？** 因为"能让用户调"通常被认为是好设计 ——
多一个自由度似乎总比少一个好。

**用户为什么不要？** 因为在这个具体面板上：

* 内容只有**三行文字 + 三个按钮**，宽度在 336～480 之间变化**没有实际收益**；
* 但拖窄**有实际损失** —— 把最右边的「提交」按钮挤出面板（第 17 章踩过这个坑）；
* 而"拖"这个动作**很容易被误触发**（点在分隔条附近就会开始拖）。

所以正确的形态不是"更宽的调节范围"，而是**没有连续调节，只有两个确定的状态**：

```python
#: 日程栏的**两个固定宽度**（像素）。
#:
#: 需求："调节日程栏宽度固定，只有全部折叠和完全展开 不能调整宽度"。
#: 所以宽度只有这两个确定的值，由 :meth:`set_collapsed` 在两者之间切换；
#: 分隔条不再允许拖动（原来宽度是连续的，用户明确不要这个自由度）。
EXPANDED_WIDTH = 380
COLLAPSED_WIDTH = 48
```

> **这一条要单独记：自由度不是越多越好。**
>
> "让用户能调"是一个默认正确的设计直觉，但它有前提：
> **这个自由度要有用，而且不能带来新的坑。**
> 在一个只有三个按钮的面板上，连续的宽度调节属于
> "看起来灵活、实则只有坏处"的自由度。
>
> 判断方法很简单：**问一句"用户会用它来干什么？"**
> 如果答案是"其实也没什么用"，那就该把它收掉，换成几个确定的状态。

#### 实现：把"拖"这条路径彻底堵死

只把面板的 `minimumWidth == maximumWidth` 还不够 ——
`QSplitter` 的 handle 仍然可以被拖动。所以三处一起关：

```python
self.splitter.setStretchFactor(0, 1)
self.splitter.setStretchFactor(1, 0)      # 右侧不参与拉伸
self.splitter.setCollapsible(1, False)    # 折叠由按钮控制，不靠拖到 0
self.splitter.setChildrenCollapsible(False)
self.splitter.setHandleWidth(0)           # 分隔条宽度 0
for _index in range(1, self.splitter.count()):
    _handle = self.splitter.handle(_index)
    if _handle is not None:
        _handle.setEnabled(False)         # 连鼠标交互也关掉
        _handle.setCursor(Qt.CursorShape.ArrowCursor)
```

外加 `side.setSizePolicy(Fixed, Preferred)`，让这一列不被内容撑宽/压窄。

**测试也直接断言这几件事**（而不是"看起来挺窄的"）：

```python
check("日程栏的宽度固定（min == max）", ...)
check("分隔条不再允许拖动（handle 宽度为 0 且被禁用）", ...)
check("分隔条不再允许把面板拖到 0（childrenCollapsible 关闭）", ...)
check("强行 resize 也改不动宽度", _home_panel.width() == _home_panel.EXPANDED_WIDTH)
```

最后那条是"模拟用户硬来"：直接 `resize(900)` 也不该动。

#### 折叠态怎么做：**同一套控件，只是显隐 + 换宽度**

一个自然的做法是"折叠时换一个专门的窄控件"。我没这么做：

```python
# 折叠态和展开态用**同一套控件**，只是显隐 + 改宽度。
# 换成两套控件会让"折叠时日程还在不在列表里"变得含糊，
# 也会让测试和外部代码摸不到 schedule_panel 的成员。
```

代价是控件里多了一层（`self.expanded` 包住原来的内容），
换来的是**外部代码和测试看到的 `schedule_panel` 一直是同一个对象**，
`set_entries` 与那些信号都不受影响。

折叠窄条上还显示了**未完成的条数**，不至于折叠后完全看不到信息。

#### 踩到的坑：`setSizes()` 会被"旧约束"算一遍

折叠后面板**实际宽度是 48（对了）**，但 `splitter.sizes()` 报 `[1035, 329]`。
我一度以为 `setSizes` 没生效，加了第二次调用才明白：

```python
def _apply_schedule_width(self) -> None:
    """把分隔条设成"左侧自适应、右侧固定"。

    **为什么要设两次**（第二次用 ``QTimer.singleShot(0, …)``）：
    ``setSizes()`` 是按"当时的控件约束"来分配的，而我们在折叠时刚刚
    改了 ``minimum/maximumWidth``，Qt 还没来得及重新布局 ——
    于是第一次调用会被它按**旧约束**算出来。
    等一个事件循环、约束生效后再设一次才准。
    """
    self._do_apply_schedule_width()
    QTimer.singleShot(0, self._do_apply_schedule_width)
```

> **顺带一个测量的教训**：`splitter.sizes()` 量的是**整列**
> （右侧那一列还包含上面的时钟/天气条），不是面板本身。
> 我差点因为这个"数字不对"去改一个其实已经正确的 `_apply_schedule_width` ——
> **断言要看对对象**：要验证"日程栏的宽度"，就该问 `panel.width()`。

### 33.2 "在软件内打开对应 Book 的 homework 栏目"

原来「打开」按钮做的是：

```python
file_ops.reveal_in_explorer(Path(folder))     # 打开本地资源管理器
```

**用户不要弹资源管理器** —— 这和前面那条"不要弹出这个窗口，
在软件内部打开文件夹"是同一个诉求，只是我当时只改了**双击**那条路，
**漏了日程栏这一个入口**。

#### 新实现

日程栏里的 `AgendaEntry` 早就带了 `subject` / `book` / `folder`
（当初收集数据时就有），所以不用去推导路径 —— 直接把它们传上去：

```python
# widgets/schedule_panel.py
open_btn.setToolTip(
    f"在软件内打开「{entry.subject} / {entry.book}」的作业栏目"
    + (f"，定位到「{entry.title}」" if entry.title else "")
)
open_btn.clicked.connect(
    lambda _checked=False, e=entry: self.homework_opened.emit(e)
)
```

主窗口接住并做三级跳转：

```python
def open_homework_in_app(self, subject_name, book_name, folder="") -> None:
    """在软件内打开某本书目的**作业栏目**，并定位到某个作业。

    顺序很重要：``show_book()`` 内部会 refresh（把当前浏览位置重置），
    所以**必须**先切书目、再 ``enter_folder()``；反过来的话
    ``enter_folder`` 设的位置会被随后的 refresh 冲掉。
    """
    self.open_book(subject_name, book_name)
    view = self.book_view
    # 切到作业栏目（按内部 key 找，不要按显示文案 ——
    # 自学课同一栏目叫「练习」，按文案找会漏）
    view._select_tab_key("homework")
    if folder_path is not None and folder_path.is_dir():
        view.enter_folder(folder_path)
```

**三个细节都是以前踩过的坑，这次直接复用**：

| 细节 | 来自哪次教训 |
| --- | --- |
| 先切书目再进文件夹（顺序） | 本章 —— refresh 会重置浏览位置 |
| 按内部 key 找标签，不按文案 | 第 26 章 —— 自学课的作业叫「练习」 |
| 兼容 `AgendaEntry` 和裸路径两种入参 | 便于测试与旧调用方 |

**验证时我特意监控了 `reveal_in_explorer` 有没有被调用**：

```
OPEN_TOOLTIP 在软件内打开「高等代数 / 高等代数」的作业栏目，定位到「2.4 作业」
STACK_IS_BOOK True
TAB_KEY homework
CUR_FOLDER 2.4 作业
VISIBLE_ROWS ['2.4 作业.md', 'homework.json', '我的解答.md']
EXPLORER_CALLS []          ← 一次都没被调用，这才是"没打开本地文件夹"的证据
```

> **"不做某事"也要有证据。** 用户说"不是打开本地文件夹"，
> 那么测试就该盯住"打开资源管理器"这个动作有没有发生 ——
> 光断言"跳到了作业栏目"只证明了一半。

#### 顺手修掉一个"会瞎猜"的兜底

老数据可能没写 `subject` / `book`，所以我加了一个从路径反推的兜底。
第一版是：

```python
if len(parts) >= 2:
    return parts[-2], parts[-1]          # ← 会瞎猜
```

测试立刻抓到它的后果：

```
[FAIL] 路径看不出结构时返回空（不瞎猜） -> ('D:\\', 'x')
```

`D:\x` 被猜成"科目 `D:\`、书目 `x`"。虽然不会崩，但会弹出一个
莫名其妙的提示。改成**只在能认出结构时才给答案**：

```python
1. 有 ``homework`` 这一段 → 取它前面两段（最可靠）；
2. 没有的话，找 ``subjects`` 这一段 → 取它后面两段；
3. **都找不到就返回空**，绝不"取最后两段"硬凑。
   宁可让调用方明确报"定位失败"，也不要猜错。
```

> **兜底逻辑要"能失败"，不要"总能给出点什么"。**
> 一个总会返回值的兜底，会把"我不知道"伪装成"我知道"，
> 让错误跑到更远的地方才暴露。

### 33.3 我这次又写错了一条测试

「打开」的用例里我断言：

```python
check("列表里是该作业文件夹的内容", "第一次作业.md" in _nav_rows)
```

它**失败**了，实际列表是 `['homework.json', '状态-过期.md']`。
原因是日程栏**按 DDL 排序**，第一条不一定是"第一次作业"。修法是
断言"**看起来像某个作业文件夹的内容**"而不是某个具体文件：

```python
# 不断言具体是哪个作业（日程栏按 DDL 排序，第一条不一定是"第一次作业"），
# 只断言"列表里就是那个作业文件夹的内容"。
check("列表里是该作业文件夹的内容（不是栏目根目录）",
      _nav_rows and not any(
          name in ("第一次作业", "2.4 作业") for name in _nav_rows))
```

> **这是第 31 章以来的第四次"测试写错"**。
> 四次的共同点：**断言依赖了一个我没验证过的前提**
> （子串连着、第一个参数不是 cmd、文件真删了、第一条就是那个作业）。
>
> 得到一个可用的经验：**写断言时，把"这个断言依赖哪些前提"想一遍。**
> 只依赖被测代码本身的前提是安全的前提；
> 依赖"数据顺序""字符串形状""上一步真的执行了"的前提，都要先确认。

### 33.4 复盘

| 类别 | 内容 |
| --- | --- |
| 宽度 | 两态固定（380 / 48）；分隔条宽度 0、禁用交互、禁止拖到 0 |
| 折叠实现 | 同一套控件显隐 + 换宽度；折叠窄条显示未完成条数 |
| `setSizes` 坑 | 改约束后要等一个事件循环再设一次（`QTimer.singleShot(0, …)`） |
| 「打开」 | 改为软件内三级跳转（书目 → 作业栏目 → 该作业文件夹） |
| 兜底 | 路径反推只在认得出结构时给答案，否则返回空 |
| 新增测试 | 28 条 |
| 学到的 | ①自由度不是越多越好，要问"用户拿它干什么"；<br>②同一诉求会有多个入口，改一处要顺一遍全部入口；<br>③兜底要"能失败"；④断言要先想清依赖的前提 |

**这一章最值钱的两条**：

> **一、把自己的自由度收回去，是用户在设计上对你的修正。**
>
> "让用户能调"是默认正确的直觉，但要看**这个调有没有用**。
> 在只有三个按钮的面板上，连续宽度调节没有收益、只有坑
> （拖窄会挤掉按钮，还容易被误触发）。
> 换成两个确定状态之后，**功能没少，坑没了**。
>
> 问法只有一个：**"用户会拿这个自由度干什么？"**

> **二、同一个诉求往往有多个入口，改的时候要顺一遍全部入口。**
>
> "不要弹资源管理器、在软件内打开"这个诉求，用户**早就提过一次**，
> 我当时改了**双击文件夹**那条路，就以为改完了。
> 结果日程栏的「打开」按钮还留着 `reveal_in_explorer` ——
> 于是同一个诉求被提了第二次。
>
> **改一类行为时，先搜一遍这个行为在代码里出现了几次**
> （`grep reveal_in_explorer`），比等用户第二次报障便宜得多。

---

## 第 34 章　"白色竖条要靠右"：一个位置 bug 的完整推理

用户报了一句很短的话：

> 白色竖条要靠右 适度美化一下

**"要靠右"三个字描述的是现象，不是原因。** 这一章把它查到底 ——
因为根因和我一开始的猜测**完全不同**。

### 34.1 先量，别猜

我的第一反应是"布局里没加 stretch，所以控件贴在左边"。
这是 `QLayout` 的常见坑，但不一定就是这次的原因。**先量一下几何**：

```
=== 折叠态 ===
  splitter   x=18 w=1364 右=1382
  side       x=1035 w=329 右=1364
  panel      x=0 w=48 右=48
```

**数字一眼看出问题**：`panel` 只有 48px（对的），
但它的**父容器 `side` 还有 329px 宽**。

所以"白色竖条"（48px 的折叠条）贴在 `side` 的左边，
右边空出 `329 - 48 = 281px` —— 这就是用户看到的"没靠右"。

> **教训：`width()` 量的是控件自己，`x()` 是它在父容器里的位置。**
> 当"控件位置不对"时，要**同时**量它和它的父容器 ——
> 只量控件会发现"宽度 48 是对的"，从而完全看不到问题。

### 34.2 是谁把父容器撑住的

继续量：`side` 是右列，里面装着**时钟条 + 日程栏**两个东西。

```
CLOCK  minSizeHint.w: 329       ← 就是它
PANEL  minSizeHint.w: 394
折叠后 SIDE minSizeHint.w: 329
折叠后 SIDE w: 329 | PANEL w: 48
```

**验证**：把时钟条藏起来再量：

```
把时钟条藏起来后:
  SIDE minSizeHint.w: 48
  SIDE w: 48 | PANEL w: 48
  SPLITTER sizes: [1316, 48]
```

根因确认：**"日期/时间/天气"那条时钟条的最小宽度是 329px。**
日程栏折叠到 48px 之后，时钟条仍然把整列撑在 329px。

**这就是"看起来是日程栏的问题、其实是它上面那个控件的问题"。**
用户看到的是竖条没靠右，而竖条本身完全正常。

> **一个通用的排查手法：把可疑的兄弟控件逐个藏起来再量。**
> 我一开始怀疑是 `QSplitter`、怀疑是缺少 stretch、
> 怀疑是 `SizePolicy` —— 都错了。
> 用"藏掉一个再量"这个动作，一次就定位到了真凶。

### 34.3 修法：让时钟条和日程栏成为**一个整体**

有三种修法，我选了第三种：

| 方案 | 问题 |
| --- | --- |
| ① 折叠时把时钟条 `hide()` | 时间/天气就没了 —— 用户会问"我的时钟去哪了" |
| ② 加 stretch 把竖条推到右边 | 右边仍然会留一条**空白带**（父容器还是 329 宽），只是从"左边空"变成"右边空" |
| ③ **把时钟条并进日程栏面板** | 两者一起显隐，整列真的只剩 48px |

方案 ③ 之所以对，是因为它**修的是"谁决定这一列的宽度"**，
而不是"让那个 48px 的条在这一列里靠哪边"。
前两个方案都还在 329px 的框子里想办法。

实现很小：

```python
# widgets/schedule_panel.py —— 展开态的最上面留一个挂载点
self.clock_holder = QWidget()
clock_layout = QVBoxLayout(self.clock_holder)
clock_layout.setContentsMargins(0, 0, 0, 0)
layout.addWidget(self.clock_holder)

def set_clock_bar(self, bar: QWidget) -> None:
    """把日期 / 时间 / 天气条挂进展开态。"""
    self.clock_bar = bar
    bar.setParent(self.clock_holder)
    self.clock_holder.layout().addWidget(bar)
```

```python
# views/home_view.py —— 右列现在只有一个子控件
side_layout.setContentsMargins(0, 0, 0, 0)   # 不留边距，竖条才贴得住右缘
side_layout.setSpacing(0)
self.schedule_panel.set_clock_bar(self.clock_bar)
side_layout.addWidget(self.schedule_panel)
```

**验证**：

```
=== 折叠态 ===
  side   w=48 右缘=1364
  panel  w=48 | fold_bar w=46
  竖条在窗口里的右缘 = 1381 | 窗口宽 = 1400 | 空隙 = 19
```

从"离右缘 300px 的空白"变成"离右缘 19px"，
而这 19px 就是内容区自己的外边距（和其他页面一致），**不是多余的空白**。

> **注意这 19px 是必要的**：如果把竖条真的贴到窗口物理边缘，
> 它会和窗口边框粘在一起、看起来像被裁掉了。
> "靠右"的正确含义是"靠内容区的右边"，而不是"靠窗口的物理边缘"。

### 34.4 适度美化：让折叠条**自己说明自己是什么**

原来折叠后只剩一个孤零零的 `‹` 箭头 ——
**用户看不出那一条是什么**（这是比位置更严重的问题）。

改成一条"竖向页签"：

```
   ‹        ← 展开箭头
   日
   程       ← 竖排字样
   ⋯
  (1)       ← 未完成条数的圆角徽标
```

同时按"页签"调整样式：左侧不留圆角（贴着内容区）、右侧圆角、
底色比面板略深一点，让它看起来是**从右边抽出来的一张卡片**：

```css
QFrame#ScheduleFoldBar {
  background: surface_alt;
  border: 1px solid border;
  border-top-left-radius: 8px;    border-bottom-left-radius: 8px;
  border-top-right-radius: 0px;   border-bottom-right-radius: 0px;
}
QLabel#ScheduleFoldCaption { color: text_muted; font-weight: 600; }
QLabel#ScheduleFoldCount {           /* 未完成数量做成小徽标 */
  color: accent; background: surface;
  border: 1px solid border; border-radius: 8px;
}
```

> **"美化"里最有价值的部分往往不是好看，而是"可读"。**
> 加竖排字样花了几行代码，但它解决的是
> "折叠后这一条是什么"这个**认知问题**；
> 圆角和底色只是让它看起来像个页签。
>
> 顺序也应该是这样：**先让人看懂，再让人看着舒服。**

#### 竖排文字为什么用 `\n` 而不是旋转

用 `QPainter` 旋转文字是"更地道"的做法，但我选了两行 `QLabel`：

```python
self.lbl_fold_caption = QLabel("日\n程")
```

理由很实际：

* 旋转绘制在**离屏渲染下不好断言**（测试拿不到"文字是不是竖的"）；
* 两行 `QLabel` 可以被测试直接读 `text()`，
  断言"折叠后能看出是日程栏"变成一行代码；
* 视觉上，两个中文字上下排列**读起来就是竖排**，不需要真的旋转。

第 31 章说过"交互需求在悄悄规定数据结构"，这里是同一件事的另一面：
**测试可行性也在悄悄规定实现方式** —— 当两种实现视觉上等价时，
选那个**能被断言**的。

### 34.5 顺手修掉一条被自己改坏的旧断言

把时钟条搬进面板之后，原来的断言失败了：

```
[FAIL] 信息条在日程栏上方 -> clock.y=0 panel.y=0
```

它原来是这么写的：

```python
check("信息条在日程栏上方", clock.y() < panel.y())     # 两者曾经是兄弟节点
```

**`y()` 只有在同一个父容器里比较才有意义。** 现在时钟条的父容器
变成了 `panel.clock_holder`，`panel.y()` 则是 `panel` 在 `side` 里的位置 ——
两个数字来自不同的坐标系，`0 < 0` 自然不成立。

改成验证**真正关心的事实**：

```python
check("信息条在日程栏上方",
      clock.parent() is panel.clock_holder
      and panel.clock_holder.y() < panel.scroll.y(), ...)
check("时钟条是日程栏的一部分（折叠时一起收起）",
      panel.clock_bar is clock and clock.parent() is panel.clock_holder, ...)
```

> **坐标系是布局断言里最容易出错的地方。**
> 凡是比较两个控件的 `x()` / `y()`，先问一句
> **"它们在同一个父容器里吗？"** 不是的话，用 `mapTo()` 换算，
> 或者干脆改成断言"结构关系"（谁是谁的子控件）——
> 后者更稳定，也不会因为以后搬位置又坏一次。

### 34.6 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | 折叠后 48px 的竖条贴在左、右边空出 281px |
| 真根因 | **上面的时钟条最小宽度 329px 把整列撑住**（不是日程栏自己的问题） |
| 定位手法 | 量控件 **和它的父容器**；把可疑的兄弟控件逐个藏起来再量 |
| 修法 | 时钟条并进日程栏面板（一起显隐），整列因此真的只剩 48px |
| 美化 | 折叠条做成竖向页签：箭头 + 竖排「日程」+ 未完成徽标 |
| 顺带修 | 一条用 `y()` 比较跨父容器控件的旧断言 |
| 新增测试 | 6 条 |
| 学到的 | ①位置不对要量父容器；②先让人看懂再让人舒服；<br>③视觉等价时选能被断言的实现；④跨父容器别直接比 `x()/y()` |

**这一章最值钱的两条**：

> **一、"控件没靠右"要量它的父容器。**
>
> `panel.width()` 是 48（正确），`side.width()` 是 329（问题所在）。
> 只量控件本身，会得出"尺寸没问题"的结论然后束手无策；
> **量一层父容器，"真凶是谁"就浮出来了** ——
> 而且这次的真凶根本不在我怀疑的范围内（我以为在调日程栏，
> 实际要动的是它上面的时钟条）。

> **二、"美化"的第一层是让人看懂，第二层才是好看。**
>
> 折叠后只剩一个 `‹` 箭头时，用户既不知道位置对不对、
> 也不知道那是什么。加一行竖排「日程」字样解决的是**认知**问题，
> 圆角与底色解决的是**观感**问题。
> 先做前者，后者顺手。
>
> 顺带一条实现建议：**当两种实现视觉上等价时，选能被测试断言的那个**
> （两行 `QLabel` 而不是旋转绘制）。

---

## 第 35 章　全黑窗口与必崩的 `nativeEvent`

用户报了一句：

> 关闭主界面 再次在桌面双击快捷方式时会异常

配图是一个**全黑的窗口** —— 标题栏正常，客户区什么都没有。

这一章记两个坑，它们是同一个功能的两次失败尝试。
**两次都不是"代码写错了"，而是"用错了机制"** ——
这种错误编译能过、逻辑测试也能过，只有真机上才暴露。

### 35.1 现象与第一条（错的）思路

"关闭到后台"实现之后，唤回是这么做的：

```python
# 第二个进程里
user32.ShowWindowAsync(hwnd, SW_SHOW)
user32.ShowWindowAsync(hwnd, SW_RESTORE)
user32.SetForegroundWindow(hwnd)
```

**当时的验证是"通过"的**：

```
1) 启动:      pid=4568 hwnd=2426994 可见=True
2) 点关闭后:  进程存活=True 窗口可见=False
3) 再双击快捷方式: 窗口可见=True 用时=0.3s      ← 看起来完美
```

`IsWindowVisible` 返回 `True`，窗口"确实显示出来了"。
但用户看到的是一片**全黑**。

> **`IsWindowVisible` 只说明"这个窗口没有被隐藏"，
> 完全不说明"它被画过"。**
> 我当时的断言测的是前者，而用户关心的是后者 ——
> **"可见"和"画出来了"是两件事**，
> 这个区别就是整章的起点。

### 35.2 为什么全黑：可见性有两个主人

窗口的可见性有两个"主人"：

* **操作系统**（`ShowWindow` 管的那一层）；
* **Qt**（`show()` / `hide()` 管的那一层，它还负责布局与重绘）。

第二个进程调 `ShowWindowAsync` 只通知了**第一个主人**。
Qt 这边完全不知道窗口被显示了，于是：不发 `QShowEvent`、
不重新布局、**不重绘**。
结果就是"原生窗口可见、内容一片空白（黑）"。

> **一条可以直接拿去用的原则**：
> **当一个属性有两个主人时，只能让"负责渲染的那个"去改它。**
>
> 在这里，Qt 是渲染的主人，所以显示/隐藏必须由 Qt 来做。
> 从外面强行改原生状态，得到的永远是"看起来动了、其实没动"。

### 35.3 第二条（看起来更专业、但必崩）思路

要让 Qt 自己显示窗口，就得**通知那个进程**。Windows 上最正统的做法是
发一条自定义消息：

```python
# 双方用同一个名字注册，拿到同一个消息 id —— 不需要约定魔法数字
msg = user32.RegisterWindowMessageW("GreatWhitePlanet.RestoreMainWindow.v1")
user32.PostMessageW(hwnd, msg, 0, 0)
```

然后第一个进程在窗口的 `nativeEvent` 里接住它：

```python
def nativeEvent(self, event_type, message):
    if wakeup.is_wake_message(event_type):
        self.restore_from_background()
        return True, 0
    return super().nativeEvent(event_type, message)
```

注册部分**实测没问题**：

```
RegisterWindowMessageW: 50167 50167 | 同一个名字两次一致: True
是否在 WM_APP 以上（>=0xC000）: True
```

但接住的部分 —— **进程启动几秒后直接崩溃**：

```
第 3 秒: 仍在运行 ✓
!! 第 6 秒时已退出，退出码 = -1073740791     # 0xC0000409
锁文件: {"pid": 7048, "hwnd": 0, ...}       # 窗口句柄从未发布 -> 崩在建窗口期间
```

而且**日志里没有任何 traceback**，`stderr` 也是空的 ——
典型的"死在这一层之下"。

#### 怎么确认不是我的返回值写错了

`QWidget.nativeEvent` 的签名是：

```
nativeEvent(self, eventType: QByteArray, message: sip.voidptr) -> (bool, sip.voidptr)
```

文档说第二个返回值是 `sip.voidptr`，我写的是 Python `int` 的 `0` ——
很自然会怀疑是这里。于是做最小复现，逐级对照：

| 模式 | 做了什么 | 结果 |
| --- | --- | --- |
| `base` | **完全不覆盖** `nativeEvent` | 退出码 0 ✅ |
| `passthru` | 覆盖，但只 `return super().nativeEvent(...)` | **-1073740771** ❌ |
| `returnfn` | 覆盖，直接 `return False, None` | **-1073740771** ❌ |
| `readtype` | 覆盖，只读一下 `event_type` 的类型 | **-1073740771** ❌ |

**关键那一行是 `passthru`：什么都不做、只是转发给父类，照样崩。**
所以这不是返回值类型的问题，而是**在 PyQt6 6.11 + Qt 6.11 上
覆盖 `QWidget.nativeEvent` 这条路本身走不通**。

> **最小对照实验的价值就在这里。**
> 如果我只试了 `(True, 0)` 和 `(True, None)` 两种返回值，会得出
> "返回值写法不对"这个**错误结论**，然后继续在这条死路上试。
> 加上"完全不动"这一档作对照，才看清是机制本身的问题。
>
> 一般化的做法：**怀疑某个细节时，一定要加一档"把这个细节整个去掉"的对照。**
> 它告诉你"是细节问题"还是"是机制问题"。

### 35.4 最终方案：文件 + 轮询

放弃原生事件，改成一个**笨但可靠**的做法：

```
第二个进程                          第一个进程
    │                                   │
    │ 发现"已有实例且窗口不可见"          │
    │ 写 else data/wake.request  ───────▶│ 600ms 定时器看到 mtime 变新
    │ （只写文件，然后退出）               │ 在自己的 Qt 事件循环里 show()
    │                                   │ （布局 + 重绘都是 Qt 自己在做）
```

实现分两半，**刻意分开**以便测试：

```python
class WakeWatcher:
    """盯着"唤回标记"文件，发现变化就回调。**不依赖 Qt 定时器**。

    刻意把"判断有没有新请求"（本类）和"隔多久看一次"（界面里的 QTimer）
    分开：这样文件比较逻辑可以在无界面环境下单独测试，
    而界面那边只需要一个定时器调 poll()。
    """
```

界面侧只有十几行：

```python
self._wake_timer = QTimer(self)
self._wake_timer.setInterval(600)
self._wake_timer.timeout.connect(self._poll_wake_request)
```

**关键点：判定"新请求"靠 mtime 变化，不是靠文件存在。**
启动时先 `mark_current()` 建立基准 ——
否则**每次启动都会因为"看到一个旧请求文件"而多唤回一次**。

**真机实测**（三个来回）：

```
1) 启动:      pid=25292 hwnd=6491692 可见=True
2) 点关闭:    进程存活=True 可见=False
3) 再双击:    窗口可见=True 用时=0.63s
   第二次唤回: 用时=0.82s
   第三次唤回: 用时=0.82s
   进程存活=True          ← 一直没换进程，是同一个实例
```

日志证明是**第一个进程自己**在 Qt 里唤回的：

```
已请求它把窗口唤回（未弹提示框）    ← 第二个进程（写完就退了）
收到另一个进程的唤回请求            ← 第一个进程轮询到
主窗口已从后台唤回                  ← Qt 自己 show()
```

#### 但"可见 = True"这个断言，这次不能再用了

第 35.1 节说过：`IsWindowVisible` 不说明"画出来了"。
所以这次换一种验证方式 —— **把窗口抓成图，然后数像素**：

```
采样点: 23865 | 近黑: 244 (1%) | 近白: 3743 (15.7%)
不同颜色数: 13839
```

**13839 种颜色**、近黑只占 1% —— 说明界面完整画出来了
（背景图、卡片、菜单都在）。

> **这个验证方式的转变才是这一章的核心。**
>
> 第一次我用了"窗口可见吗"这个代理指标，它和用户关心的东西**不是一回事**，
> 于是漏掉了全黑。第二次我直接量"画出来了吗"（像素统计 + 看图）。
>
> **代理指标要为结论负责。** 当你发现某个断言"通过了但用户还是不满意"，
> 第一件要做的事就是回头问：**这个断言到底在测什么？它离用户的感受有多远？**

### 35.5 顺便修掉一个"读锁不抢锁"的隐患

改这一段时还发现：早期单实例检查在**没有窗口句柄**时（前一个实例刚启动、
或锁是旧格式）会走"保守认为可能藏在后台"这条路，于是**每次启动都会写一次
唤回请求**。

这不会出错（`show()` 是幂等的），但它会掩盖"其实窗口就在眼前"这种情况。
所以现在只对**确实不可见**的窗口写请求；只有"拿不到句柄"时才保守处理。

> 顺带说明为什么可以直接返回而不弹框：
> 用户刚双击了快捷方式，**他的意图就是"我要用软件"** ——
> 这时弹一个"软件已在运行"才是最打扰的做法（第 30 章已经定过这条原则）。

### 35.6 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | 唤回后窗口全黑（标题栏正常、客户区空白） |
| 原因一 | 第二个进程用 `ShowWindow` 显示窗口，Qt 不知道 -> 不布局不重绘 |
| 原因二 | 改用 `nativeEvent` 接自定义消息 -> PyQt6 6.11 上**必崩**（连透传都崩） |
| 定位手法 | **最小对照实验**：加一档"把可疑细节整个去掉"，区分"细节问题"还是"机制问题" |
| 最终方案 | 请求文件 + 600ms 轮询；判定靠 mtime 变化；启动时先建基准 |
| 实测 | 三个来回全部 0.6–0.8 秒唤回，同一个进程、画面完整 |
| 验证升级 | 从"`IsWindowVisible`"改成"抓图 + 数像素 + 看图" |
| 新增测试 | 21 条（核心 10 + 界面 7 + 调整 4） |
| 学到的 | ①可见 ≠ 画出来了；②一个属性两个主人时只能让渲染方去改；<br>③最小对照实验要含"整个去掉"那一档；④代理指标要为结论负责 |

**这一章最值钱的两条**：

> **一、"可见"和"画出来了"是两件事。**
>
> 我的第一版验证是 `IsWindowVisible(hwnd) == True` ——
> 它测的是"窗口没被隐藏"，而用户要的是"界面上有东西"。
> 这个差别让我把一个**全黑窗口**判成了"通过"。
>
> 一般化：**当你发现某个断言过了但用户还是不满意，
> 先回头问"这个断言到底在测什么"。**
> 代理指标（proxy metric）很方便，但它必须为结论负责 ——
> 而"画出来了吗"这种问题，唯一的可靠答案就是**把画面拿出来看**。

> **二、怀疑某个细节时，一定要加一档"把这个细节整个去掉"的对照。**
>
> 覆盖 `nativeEvent` 崩溃时，最自然的怀疑是"第二个返回值不该是 `int`"。
> 如果只对照 `0` 和 `None` 两种写法，我会得出"写法不对"的结论，
> 然后继续在这条死路上试。
>
> 加上 **"完全不覆盖"** 这一档（退出码 0），才看清
> **问题在机制本身，不在写法** —— 于是果断换方案，没有浪费时间。

---

## 第 36 章　需求改了数据的"归属"：单词书从每本一份改成全局一份

用户先确认了现状，然后给出决定：

> 单词书现在是否公用一个文件夹
> ……
> 所有科目公用一个文件夹

**这不是加功能，是改"数据归谁"。** 这一章记这类改动的做法 ——
它比新增功能危险，因为它要动**用户已经在用的数据**。

### 36.1 先回答"现在是什么样"，再动手

用户第一句是**提问**，不是需求。这时最重要的不是改代码，而是**给出准确的现状**。
所以直接去磁盘上看：

```
=== 数据目录里所有 wordbook 文件夹 ===
  数学分析 \ 数学分析上 \ wordbook   卡片数=0
  高等代数 \ 高等代数 \ wordbook   卡片数=0

=== 科目目录本身有没有 wordbook（即是否科目级共享）===
  习概: 无   单片机: 无   我的日记: 无   数学分析: 无
  英语: 无   计算机导论: 无   高等代数: 无
```

现状很清楚：**每本书一个 `wordbook/`**，而且**不在科目目录上**。

> **用户问"现在是不是 X"时，答案必须是查出来的，不能是回忆出来的。**
> 我如果凭印象回答"是共用的"（因为我写的时候觉得"所有书目都有"就是共用），
> 就会把用户带向一个错误的决定。

### 36.2 改"归属"之前，先把数据拿出来

改数据结构的第一条纪律：**先备份，再动手**。

```
=== 备份现有 wordbook 目录 ===
  数学分析 \ 数学分析上: 0 个文件
  高等代数 \ 高等代数: 0 个文件
  备份目录: DeepseekData\wordbook_backup_20261010_022253
  备份文件数: 0
```

这次运气好 —— **一张卡都没有**，所以改动零风险。
但"运气好"不能当成流程：如果当时有 200 张卡，而这些命令是在改完代码之后才跑的，
那就来不及了。

> **顺序永远是：先备份 → 再改代码 → 再迁移 → 最后验证。**
> 备份这一步的价值不在于"每次都用得上"，而在于**它是唯一不可补救的环节**。

### 36.3 位置选择：放 `user data` 还是 `else data`？

新位置有两个候选：

| 位置 | 含义 | 适不适合 |
| --- | --- | --- |
| `user data/wordbook/` | 用户自己的内容 | ✅ 单词卡是用户手写的学习资料 |
| `else data/wordbook/` | 软件的配置/缓存/日志/资源 | ❌ 那里放的是 `config.json`、`chats`、`assets`、`logs` |

按项目里已有的分工（`user data` = 用户数据，`else data` = 软件自己的东西），
单词卡显然属于前者。于是：

```python
# core/paths.py
# **单词书是所有科目共用的一个目录**（需求："所有科目公用一个文件夹"），
# 放在 user data 下、**不在 subjects 里面** ——
# 它不属于任何科目或书目，而是跨教材累积的生词本。
self.wordbook_dir: Path = self.user_data / str(
    paths.get("wordbook_dir", "wordbook")
)
```

注意这里**沿用了"可在配置里改名"的既有约定**（`wordbook_dir`
和 `subjects_dir`、`backup_dir` 完全同构），而不是硬编码字符串。

> **新目录要跟着既有的目录约定走。**
> 项目里所有目录名都能在 `config.json` 里改，我如果为新目录写死一个常量，
> 就制造了一个"唯一的例外"—— 以后有人想改会很别扭。

### 36.4 连带要改的地方（一个都不能漏）

"单词书不在书目下面了"这件事，影响面比想象的大：

| 位置 | 原来 | 现在 |
| --- | --- | --- |
| `BOOK_TEMPLATE_DIRS` / `DIARY_TEMPLATE_DIRS` | 含 `wordbook` | **去掉** —— 否则每本书还会建一个空目录 |
| 标签定义 `WORDBOOK_TAB` | `("wordbook", "单词书", "wordbook")` | 第三个字段改 **`None`**（这个标签没有书目内目录） |
| `DataPaths` | 无 | **新增 `wordbook_dir`**，并加进 `all_dirs()` 一起创建 |
| `WordbookView.folder()` | `book.path / "wordbook"` | `paths.wordbook_dir` |
| 迁移逻辑 | 无 | **新增**：启动时把旧卡片搬过来 |

**其中最容易漏的是标签定义那一行。** 标签的第三个字段是"这个标签对应书目下的哪个目录"，
被很多地方用着（导入文件、拖拽落点、`tooltip` 文案）。
如果继续写 `"wordbook"`：

* 拖文件到单词书页会把文件丢进 `book/wordbook/`（一个不再被读的目录）；
* 「导入文件」会指向那里；
* 而真正的卡片在别处 —— **用户会看到"文件放进去了但列表没变"**。

改成 `None` 之后，那些地方会走"这个标签没有对应目录"的既有分支
（弹窗让用户选分类），**行为是安全的**。

> **改一个数据的"归属"时，要顺着它被引用的地方走一遍。**
> 我这次是先把 `WORDBOOK_FOLDER` 这个常量的所有引用 `grep` 出来，
> 才发现标签定义里也有一个 —— 而它不是"路径"，是"目录映射"，
> 很容易被当成路径改掉、或者干脆漏掉。

### 36.5 迁移：三条原则

有旧数据就一定要迁移，否则用户的老卡片会留在旧目录里 —— **看得见目录、看不见卡片**。

```python
def migrate_legacy_wordbooks(target_dir, subjects_dir) -> dict:
    """把旧布局的单词卡**移动**到全局单词书。返回一份迁移报告。

    三条原则：

    1. **绝不覆盖**：目标已存在同名卡时，把新来的改名为
       ``<名字> (来自<科目>-<书目>).json`` 保留下来 ——
       两张卡都有价值，"谁赢"不该由我们决定。
    2. **移动而不是复制**：成功后删掉旧目录，避免留下两份让人困惑
       （"我改了这张卡怎么没生效"通常是改到了另一份上）。
    3. **失败就留着**：移动不了的（占用、权限）原样留在旧目录，只记日志。
       宁可留着旧数据，也不要"为了干净"把它删掉。
    """
```

实测（构造了三本书，其中两本都有 `give up`）：

```
迁移结果:
  移动: 3 张
    give up.json
    give up (来自英语-英语1).json      ← 重名的那张，改名保留
    abandon.json
  冲突保留: ['give up (来自英语-英语1).json']
  删掉的旧目录: 3
  失败: []
共用单词书现在有:
  abandon      英语2 里的释义
  give up      英语1 里的释义
  give up      上 里的释义
旧目录还在吗: 都不在了 ✓
再跑一次迁移（应无事发生）: {'moved': [], 'kept': [], 'removed_dirs': [], 'failed': []}
```

**注意最后一行：迁移是幂等的。** 它挂在每次启动的 `bootstrap` 上，
所以"跑很多次"是常态，必须保证第二次什么也不做。

> **"绝不覆盖"是这类迁移里最容易做错、后果最重的一条。**
>
> 一个"把 A 目录的文件移到 B 目录"的循环，如果直接 `shutil.move`
> 到同名目标，第二次运行就会**静默覆盖** B 里已有的卡。
> 这次没有旧数据，所以怎么写都不会出事 ——
> 但正因为如此，**这个 bug 会一直潜伏到有老用户升级时才爆发**，
> 那时候数据已经没了。
>
> 判断标准很简单：**这个操作第二次运行时，还会不会做出"破坏性"的事？**

### 36.6 测试要覆盖"迁移"这件事本身

迁移逻辑最容易写的两个 bug 是"覆盖"和"不幂等"，所以测试直指它们：

```python
check("重名的卡**改名保留**而不是覆盖", ...)
check("两张同名卡的内容都在（没丢一张）", ...)
check("旧目录被清掉（不留两份让人困惑）", ...)
check("迁移是幂等的（再跑一次什么都不做）", ...)
check("目录全空时迁移也不会出错", ...)
```

界面侧则验证**"共用"这件事真的发生了** —— 这是需求的核心，
只测"路径变量指向哪"是不够的：

```python
check("新建书目**不会**在书目下建 wordbook（已改成共用目录）", ...)
check("单词书视图用的就是共用目录", ...)
check("**在另一本书里也能看到同一批单词卡**", ...)
check("另一本书里的卡片内容与刚才那张一致", ...)
```

**最后两条是"用户视角"的验证**：我打开另一本书，能不能看到刚才记的词。
它比"`folder()` 返回了正确的 Path"强得多 —— 后者只是中间量。

### 36.7 复盘

| 类别 | 内容 |
| --- | --- |
| 起因 | 用户**先问现状**，再给决定："所有科目公用一个文件夹" |
| 改前 | 先备份现有卡片（这次恰好 0 张，但仍走流程） |
| 新位置 | `<data>/user data/wordbook/`（用户数据侧；可配置改名） |
| 连带改动 | 模板目录去掉它；标签的目录字段改 `None`；`DataPaths` 新增并加入 `all_dirs` |
| 迁移 | 移动 + 重名改名保留 + 失败留着；**幂等**，挂在每次启动 |
| 新增测试 | 21 条（核心迁移 8 + 界面 8 + 结构性断言 5） |
| 学到的 | ①用户问现状时要查不能说；②改归属先备份；<br>③新目录跟着既有约定；④顺着引用走一遍（标签的"目录映射"最容易漏）；<br>⑤迁移必须"绝不覆盖"且幂等 |

**这一章最值钱的三条**：

> **一、用户问"现在是不是 X"时，答案必须是查出来的。**
>
> 我如果凭印象回答"是共用的"（因为我实现时想的是"所有书目都有这个栏目"），
> 用户就会在一个错误前提上做决定。**查一下磁盘，只要十秒钟。**

> **二、改数据的"归属"，要顺着它的引用走一遍，而不是只改路径。**
>
> 这次漏掉的话，最有问题的是**标签定义里那个"目录映射"** ——
> 它看着像路径，实际是"这个标签对应书目下的哪个目录"，
> 漏改会让拖拽和导入把文件丢到一个不再被读取的目录里，
> 而且现象是"操作成功了但列表没变"，很难查。
>
> 做法：把旧常量 `grep` 一遍，逐个判断"这是路径还是别的语义"。

> **三、迁移代码要问："第二次运行会做什么？"**
>
> "把 A 的文件移到 B"这种循环，直接 `shutil.move` 到同名目标
> 就会在第二次运行时**静默覆盖**。
> 这次没有旧数据，所以怎么写都不会暴露 ——
> 而它只会在**老用户升级的那一天**爆发，那时数据已经没了。
>
> 所以：**绝不覆盖（重名就改名保留）+ 幂等（第二次什么都不做）**，
> 并且这两条都要有测试盯着。

---

## 第 37 章　互相依赖的两个尺寸，只能一起打破

用户报障：

> 当页面大小调整后 日程栏目打开肯会遮挡Subject

**"遮挡"这个用词把注意力引向了日程栏** —— 而真凶在科目卡片那一侧。

### 37.1 先量：是遮挡还是裁掉

第一件事是分清楚现象。量一下几个关键宽度：

```
GRID minHint 816 sizeHint 816        ← 网格的最小宽度
GRID cards: 6 card w: 190
SPLIT 700 -> sizes=[320, 380] 左W=320 gridW=816 列数=4
```

**一眼就看出问题**：`gridW=816` 而它所在的滚动区只有 **320**。
所以不是"日程栏画在卡片上面"，而是**网格比可见区域宽，右边的列被裁掉了** ——
用户看到的"被遮住"其实是"第三列整个看不到"。

**这类"看起来像 A 的问题、实际是 B"的报障，第一步永远是量出坐标，
而不是去改那个被点名的控件。**

### 37.2 真凶：两个互相依赖的尺寸

看代码就明白了：

```python
def minimumSizeHint(self) -> QSize:
    return self._compute_size()          # ← 用 self._columns()

def _columns(self) -> int:
    available = max(card_width, self.width() - padding * 2)   # ← 用 self.width()
    ...

def _compute_size(self) -> QSize:
    columns = self._columns()
    width = columns * card_width + ...   # ← 反过来决定 minimumSizeHint
```

**三者构成一个环**：

```
minimumSizeHint  ←  _compute_size  ←  _columns  ←  self.width()
       ↑                                                  │
       └──────────── 布局按 minHint 给宽度 ←───────────────┘
```

于是得到一个**自我实现**的结果：`minimumSizeHint` 说"我要 816"，
布局就给它 816；它再看自己的 816 算出 4 列，于是更加确信自己该有 816。
**在这个过程中 `self.width()` 永远没有机会变小**，
所以它永远学不会"其实我只能排 2 列"。

> **这是一个可以推广的模式：当"算尺寸"依赖"已有尺寸"、
> 而"已有尺寸"又由"算出来的尺寸"决定时，它就锁死了。**
>
> 打破的办法只有一个：**让其中一端的外部输入变成"外面告诉我的可用宽度"，
> 而不是"我自己现在的宽度"。**

### 37.3 打破环：引入"可用宽度"这个外部输入

改动的核心是给网格一个**来自外部**的数字：

```python
def __init__(...):
    #: 外面告诉我们的"最多能有多宽"（0 = 还没告诉，按自身宽度算）。
    #:
    #: **为什么需要它**：列数原来是按 self.width() 算的，而宽度又由
    #: minimumSizeHint()（= 所有卡片排成一行的宽度）决定 —— 两者互相
    #: 依赖，网格就永远"不肯变窄"。
    self._available_width = 0

def set_available_width(self, width: int) -> None:
    """告诉网格"你最多能有多宽"，并立即重新排布。"""
    ...

def _layout_width(self) -> int:
    """算列数时该用的宽度：优先用外面告诉我们的可用宽度。"""
    if self._available_width > 0:
        return self._available_width
    return self.width()
```

同时把 `minimumSizeHint()` 从"排成一行"改成 **"只放一列"**：

```python
def minimumSizeHint(self) -> QSize:
    """**最小**需求：只放一列。

    这一点很关键：以前这里返回的是"排成一行"的宽度，
    于是整个科目区的最小宽度被钉在 816px —— 窗口再窄、
    右侧日程栏再怎么占地方，布局都不肯把科目区压小，
    结果就是卡片被裁掉。
    """
    return self._compute_size(columns=1)
```

而"理想宽度"仍然是排成一行（大屏要能多排几列）：

```python
def sizeHint(self) -> QSize:
    """理想尺寸：所有卡片排成一行。
    这只是"如果空间足够，我想这么宽"，**不是最小需求**。"""
    return self._compute_size(columns=len(self._cards) or 1)
```

**实测效果**（改完之后）：

```
SPLIT 700:  vp=309 cols=1 卡片最右=194 超出=-115
SPLIT 900:  vp=520 cols=2 卡片最右=400 超出=-120
SPLIT 1100: vp=720 cols=3 卡片最右=606 超出=-114
SPLIT 1400: vp=1020 cols=4 卡片最右=812 超出=-208
SPLIT 1800: vp=1420 cols=6 卡片最右=1224 超出=-196
```

**每一档"超出"都是负数** —— 卡片永远落在可见区域内。

### 37.4 第二个坑：`QSplitter` 分配尺寸时**不发** Resize 事件

"告诉网格可用宽度"需要一个触发时机。我第一版挂在视口的 `Resize` 事件上：

```python
self.scroll.viewport().installEventFilter(self)
```

**结果它只触发了一次。** 因为 `QSplitter` 给子控件分配尺寸时，
**不走它们的 resize 请求路径** —— 视口拿不到 Resize 事件。
（实测：改完宽度后网格一直用着几十秒前的旧值，列数不变。）

所以把触发时机改到**分隔条自己身上**：

```python
class ReportingSplitter(QSplitter):
    """会在"分配完尺寸"之后发信号的 QSplitter。

    为什么需要它：QSplitter 重新分配子控件宽度时，
    **不会**让子控件（比如 QScrollArea 的 viewport）收到 Resize 事件。
    于是"科目区现在有多宽"这个信息没有可靠的获取时机。
    """

    sizes_applied = pyqtSignal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizes_applied.emit()

    def moveSplitter(self, pos, index):
        super().moveSplitter(pos, index)
        self.sizes_applied.emit()
```

> **这是"谁改变了尺寸，就该由谁通知"的一个具体例子。**
> 我一开始把监听挂在**结果**上（视口变宽了），
> 但那个结果并不总是由"尺寸变化"这条路产生。
> 挂在**原因**上（分隔条重新分配了）才可靠。

### 37.5 第三层：空间实在不够时，日程栏该让位

网格会换行之后，还剩一个边界情况：窗口窄到连**一列卡片 + 380px 的日程栏**
都放不下时怎么办？

答案是**日程栏让位** —— 科目卡片是主内容，日程栏是辅助信息：

```python
#: 科目区的最小宽度：一张卡片（约 190px）+ 内边距 + 一点余量。
SUBJECT_MIN_WIDTH = 260

def auto_collapse_for_room(self) -> bool:
    """空间不够时自动把日程栏折叠起来。返回是否发生了折叠。"""
    total = self.splitter.width()
    # 还没有真实宽度（启动早期、或当前不是首页）时不要动 ——
    # 否则布局尚未完成就会被判成"空间不够"，日程栏会莫名其妙地折起来。
    if total <= 0 or not self.isVisible():
        return False
    if total - panel.EXPANDED_WIDTH >= self.SUBJECT_MIN_WIDTH:
        return False
    panel.set_collapsed(True)
    self.status_message.emit("空间不够，日程栏已自动折叠（点 ‹ 可展开）")
```

两个细节都是刻意的：

* **`total <= 0 or not self.isVisible()` 就直接返回**：启动早期布局还没完成，
  `splitter.width()` 是 0，如果不判断就会"一启动就把日程栏折起来"。
  （这是实际踩到的：我第一次测的时候它没折叠，就是因为宽度是 0；
  反过来说，**没有这个保护时它在真实启动里可能会误折叠**。）
* **变宽之后不自动弹回来**：否则用户拖动窗口时会看到日程栏反复折叠/展开。
  让用户自己点一下，行为是确定的。

### 37.6 我又一次写出"依赖未验证前提"的断言

写测试时我假设"`window.resize()` 会让布局传导下去"，于是断言：

```python
window.resize(760, 820)
check("窗口变窄后网格重新计算了宽度", _grid._available_width <= 800)
```

**它失败了**：`avail=864 splitter=1244` —— 离屏环境下改窗口宽度**不会**
传导到子控件。我接着试了 `splitter.resize()`、`setFixedWidth()`，
都被父布局改了回去。

最后改成**只断言我已经验证过的事实**：
`set_available_width()` 是"可用宽度"的**单一入口**，灌进去就必须重排 ——
这条在独立脚本里已经亲眼看到数字变了。而窗口 resize 只留一个"不崩"的冒烟断言。

> **这是本书里第 N 次同一个错误**（第 31、32、33、35 章都有）：
> **断言依赖了一个我没验证过的前提。**
>
> 这次的新体会是：**当测试环境不方便复现真实路径时，
> 就去断言那条路径的"汇合点"** ——
> 在这里就是 `set_available_width()`。真实布局和测试都从它进来，
> 所以测它就等于测了"列数会不会跟着宽度变"这个核心逻辑。
>
> 反过来，**不要为了测试方便去造假一个环境**（比如硬改 splitter 宽度），
> 那只会得到一条既不可靠、又和真实行为无关的断言。

### 37.7 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | 展开日程栏后，科目卡片的右边几列看不到 |
| 真因一 | `minimumSizeHint` ↔ `_columns` ↔ `self.width()` **互相依赖成环**，网格不肯变窄 |
| 修法一 | 引入外部输入 `set_available_width()`；`minimumSizeHint` 改为"一列" |
| 真因二 | `QSplitter` 分配尺寸时**不发** Resize 事件，监听视口拿不到时机 |
| 修法二 | 让分隔条自己在分配完尺寸后发信号（`ReportingSplitter`） |
| 边界 | 放不下"一列卡片 + 日程栏"时自动折叠日程栏；宽度未确定时不误判 |
| 新增测试 | 14 条 |
| 学到的 | ①互相依赖的尺寸会锁死，要打破环；②监听"原因"而不是"结果"；<br>③边界条件要防"启动早期"；④测试环境不便复现时，去断言那条路径的汇合点 |

**这一章最值钱的两条**：

> **一、当"算尺寸"依赖"已有尺寸"、"已有尺寸"又由它决定时，尺寸就锁死了。**
>
> `minimumSizeHint` 说"我要 816"，布局给它 816，它再按 816 算出 4 列 ——
> 更加确信自己该有 816。**自我实现的预言。**
>
> 唯一的解法是给环里接一个**外部输入**（"外面告诉我可用宽度是多少"），
> 让判断依据不再是自己当前的大小。
> 这类环在布局代码里很常见（表格列宽、自适应画布、文本换行），
> 见到"算出来的值又参与下一轮计算"就要警惕。

> **二、监听"原因"，不要监听"结果"。**
>
> 我想在"科目区宽度变了"时重排列数，于是去监听**视口**的 Resize ——
> 那是**结果**，而结果并不总是由这条路产生
> （`QSplitter` 分配尺寸时压根不发这个事件）。
> 改成监听**分隔条自己**"我分配完了"，一次就对了。
>
> 一般化：**当你发现通知偶尔不来，先问"这件事的源头是谁"**，
> 把钩子挂到源头上去。

---

## 第 38 章　任务栏图标：一个"返回成功"却查不回来的设置

用户报障（附了一张 58×64 的任务栏图标截图，是 **Python 的蛇形图标**）：

> 将任务栏的图标改成快捷方式现在的图标

### 38.1 先确认"窗口图标"这一侧是对的

第一步排除最明显的可能：窗口自己有没有设对图标？答案是**已经设了**：

```python
app.setWindowIcon(common.app_icon(config=context.config))   # app.py
self.setWindowIcon(common.app_icon(config=context.config))  # MainWindow
```

而 `common.app_icon()` 读的正是 `gwp/resources/icons/planet.ico` ——
和桌面快捷方式用的是**同一个文件**：

```
快捷方式: Great White Planet.lnk
  图标: D:\...\gwp\resources\icons\planet.ico,0
```

所以"改成快捷方式现在的图标"这句需求，**从图标文件的角度看已经满足了**。
问题不在图标，在**身份**。

### 38.2 真因：任务栏按"应用标识"分组

Windows 的任务栏按钮图标**不是**由窗口自己画的那个决定的：

1. 系统先按 **AppUserModelID（应用标识）** 把窗口归到一个"应用"；
2. 再用那个应用的图标画按钮。

从源码运行时进程是 `venv\Scripts\pythonw.exe`，而我们**没有设过标识** ——
于是 Windows 把窗口归到 **Python** 名下，任务栏显示解释器的蛇形图标。

修法是官方的 `SetCurrentProcessExplicitAppUserModelID`，
而且**必须在建窗口之前**调用（Windows 是在窗口出现时读取进程标识的）：

```python
def create_application(argv):
    # **必须在建窗口之前**设应用标识：
    # 不设的话 Windows 会把窗口归到 pythonw.exe 名下，
    # 任务栏显示的是 Python 解释器的图标。
    from gwp.core.app_identity import set_app_user_model_id

    set_app_user_model_id()
    ...
```

同理，桌面快捷方式也要写**同一个**标识，否则"双击快捷方式启动"
与"已在运行的实例"会被当成两个应用。

### 38.3 差点走进死胡同：用错的 API 验证

改完代码要验证"设置生效了吗"。我最自然的做法是找一个读取端 API，
于是用了 `GetApplicationUserModelId()` —— 它**返回 15703**：

```
设置前: '<失败 HRESULT=15703 (0x00003D57)>'
set_app_user_model_id() -> True          ← 设置本身返回成功
设置后: '<失败 HRESULT=15703 (0x00003D57)>'
与期望一致: False
```

**两个信号互相矛盾**：设置返回成功，读取说没有。我当时的判断是
"读法写错了"，于是花了好几轮去试 `argtypes`、缓冲区大小、句柄类型，
甚至去查真实运行的应用进程 —— 全都是 15703。

最后去查权威文档
（[GetApplicationUserModelId](https://learn.microsoft.com/en-us/windows/win32/api/appmodel/nf-appmodel-getapplicationusermodelid)），
在**示例代码**里看到了决定性的一行：

```c
if (rc == APPMODEL_ERROR_NO_APPLICATION)
    wprintf(L"Desktop application\n");      // ← 就是这个
```

**`APPMODEL_ERROR_NO_APPLICATION` 对未打包的桌面应用是正常状态**，
官方示例直接把它打印成 "Desktop application"。

也就是说：**这个 API 根本不是"设置显式标识"的读取端**。
我拿一个语义不对的 API 当验证手段，然后在那上面纠缠了太多轮。

> **教训：验证一个设置时，要先确认"这个读取端 API 读的就是我写的那个东西"。**
>
> 它们的名字很像（`SetCurrentProcessExplicitAppUserModelID` /
> `GetApplicationUserModelId`），但语义不同：后者反映的是**包标识**，
> 不是"显式设置的那个值"。
>
> 更重要的做法是：**当"设置返回成功"与"读取说没有"矛盾时，
> 先去查文档确认读取端的语义**，而不是假定读取端调用姿势不对。
> 我在这上面绕的弯，比一次文档查询贵得多。

### 38.4 改用能验证的那一半：快捷方式的标识

进程侧读不回来，但**快捷方式侧是可以读写的**，而且它同样必要
（决定任务栏分组）。于是我把重心换到这边，
并且发现了一条**真正会坏**的代码。

第一版我图省事，用 PowerShell 的 `ExtendedProperty` 去写：

```powershell
$item = $folder.ParseName('xxx.lnk')
$item.ExtendedProperty('System.AppUserModel.ID') = 'GreatWhitePlanet...'
```

**实测直接报错**：

```
Error while invoking ExtendedProperty. Could not find member.
```

`FolderItem.ExtendedProperty` 是**只读**的 —— 赋值根本不支持。
（更糟的是它没让整条命令失败，快捷方式照样建出来了，
所以这个错误很容易被忽略过去，而标识一直没写进去。）

正确做法是 Shell 的正规接口 `IPropertyStore`：

```python
shell32.SHGetPropertyStoreFromParsingName(path, None, GPS_READWRITE,
                                          IID_IPropertyStore, ...)
# 然后 vtable[6] = SetValue, vtable[7] = Commit
```

用 ctypes 按 vtable 下标调用，**先独立验证再用**：

```
写入前: ''
set_app_user_model_id -> True
写入后: 'GreatWhitePlanet.LocalKnowledge'
PowerShell 读回: 'GreatWhitePlanet.LocalKnowledge'     ← 换一条路复核
```

**最后那行是刻意的**：我不用自己写的读函数去验证自己写的写函数 ——
用 PowerShell 这个**独立的读取端**复核一遍，才排除"两边一起错"。

> **验证要尽量用"不同来源"的手段。**
> 自写读 + 自写写 = 一对可能同错的东西；
> 自写写 + 系统工具读 = 至少证明"系统认了这个值"。

### 38.5 顺手补上"已有的旧快捷方式"

还有一件容易漏的事：**用户桌面上那个快捷方式是我上一版代码创建的，
它没有标识**。新代码只在"创建快捷方式"时写标识，
所以光改代码**修不了用户当前那个文件**。

于是加了一个幂等的启动整理：

```python
def ensure_shortcut_identity(name: str = "Great White Planet") -> bool:
    """如果桌面上已经有快捷方式，但缺应用标识，就补上。

    为什么需要：用户桌面上那个快捷方式可能是**旧版本**创建的（没有标识）。
    不补的话，双击它启动的进程与快捷方式不是同一个任务栏分组，
    任务栏仍然可能显示解释器图标 —— 那正是用户报的问题。
    """
```

实测（对真实桌面）：

```
补之前 AUMID: ''
需要补吗: True
ensure_shortcut_identity() -> True
补之后 AUMID: 'GreatWhitePlanet.LocalKnowledge'
再调一次（应无事发生）: False
```

> **这一条通用性很强：修了"生成逻辑"，还要修"已经生成出来的东西"。**
> 数据迁移如此（第 36 章），快捷方式、注册表项、配置文件也一样。
> 判断方法：**这次改动会让"用旧版本产出的文件"和新版本不一致吗？**
> 会的话就得有一个"就地补齐"的路径。

### 38.6 测试暴露的副作用

加完启动整理之后，界面测试**从 26 秒变成跑不完**（10 分钟超时）。
原因很直接：测试会反复建 `MainWindow`，每个实例的 `_post_start()`
都会去读/写**用户真实的桌面快捷方式**。

（那条 COM 调用本身很快，但测试里建了几十个窗口，累积起来再加上
PowerShell 的子进程开销，就把测试拖爆了。）

修法是让测试环境**直接跳过**：

```python
if os.environ.get("GWP_ROOT"):
    log.debug("检测到 GWP_ROOT（测试环境），跳过快捷方式整理")
    return False
```

测试从"跑不完"回到 **26 秒**。

> **自动化测试不该修改用户桌面（或任何真实环境）。**
> 这条不是"性能优化"，而是**测试的边界** —— 一旦测试会改真实环境，
> 它就不再是"可以随便跑"的了，而人就会开始不敢跑它。
>
> 判断起来很简单：**这个测试如果连跑一百次，会在我的机器上留下什么？**

### 38.7 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | 任务栏显示 Python 蛇形图标，而不是 planet.ico |
| 真因 | 任务栏按 AppUserModelID 分组；未设标识时归到 `pythonw.exe` 名下 |
| 修法一 | 建窗口前设进程标识（`SetCurrentProcessExplicitAppUserModelID`） |
| 修法二 | 快捷方式写同一个标识（COM `IPropertyStore`，**不是** ExtendedProperty） |
| 修法三 | 启动时给**已有**的旧快捷方式就地补齐标识（幂等） |
| 走的弯路 | 用 `GetApplicationUserModelId` 当验证手段 —— 它对桌面应用本就返回 `NO_APPLICATION` |
| 新增测试 | 15 条 |
| 学到的 | ①验证设置前先确认读取端的语义；②验证尽量用不同来源的手段；<br>③改生成逻辑还要补已生成的东西；④测试不该改真实环境 |

**这一章最值钱的三条**：

> **一、当"写返回成功"与"读说没有"矛盾时，先查文档确认读取端的语义。**
>
> `SetCurrentProcessExplicitAppUserModelID` 返回 0，
> `GetApplicationUserModelId` 返回 `APPMODEL_ERROR_NO_APPLICATION` ——
> 我花了七八轮去怀疑"读取端调用姿势不对"（argtypes、缓冲区、
> 句柄、甚至去查别的进程），最后在微软文档的**示例代码**里
> 看到那行 `wprintf(L"Desktop application\n")` 才明白：
> **这个 API 对未打包桌面应用本来就返回这个值。**
>
> 名字相似 ≠ 语义对应。**先确认读取端读的就是你写的那个东西。**

> **二、验证要用"不同来源"的手段，而不是自己验自己。**
>
> 写完 `set_app_user_model_id`，最省事的验证是调自己写的
> `read_app_user_model_id` —— 但那两个函数可能**一起错**
> （比如都误解了字节序）。
> 所以我用 PowerShell 的 Shell COM **独立读了一遍**，
> 两条路都得到 `GreatWhitePlanet.LocalKnowledge`，才敢说"系统认了这个值"。

> **三、改了"生成逻辑"，还要补"已经生成出来的东西"。**
>
> 新代码现在会带标识创建快捷方式 —— 但用户桌面上那个
> 是旧版本创建的、没有标识，光改代码只对"以后新建的"生效。
> 所以加了一个启动时的幂等补齐。
>
> 这和移植数据的迁移是同一件事（第 36 章）：
> **判断方法就一句 —— 这次改动会让"旧版本产出的文件"和新版本不一致吗？**

---

## 第 39 章　"功能异常"：一个功能被两个缺陷同时掐死

用户报障只有四个字：

> 更改作业名称功能异常

没有截图、没有复现步骤。这一章讲怎么从这么一句话查到根因 ——
以及**为什么它其实不是一个 bug，而是两个**。

### 39.1 先找"改名"这条路在哪

作业在界面上是一个文件夹。它有两种"改名"的可能：

* 普通的**重命名**（`_rename_item`，右键菜单里有）；
* 作业特有的**编辑作业**（`HomeworkDialog`，里面有"作业名称"一栏）。

点开对话框代码，第一眼就看到了问题：

```python
default_name = "" if self.is_new else homework.name
self.input_name = QLineEdit(default_name)
self.input_name.setPlaceholderText("例如：第三章习题（会成为文件夹名）")
self.input_name.setEnabled(self.is_new)      # 改名会动文件夹，编辑时不允许 ←
form.addRow("作业名称", self.input_name)
```

**编辑模式下，名称输入框是禁用的。** 也就是说：界面上有一栏写着"作业名称"，
但它是灰的、点不动 —— 这正是"功能异常"最直白的样子。

### 39.2 但把它放开还不够

如果只把 `setEnabled(True)`，会得到什么？看保存那一段：

```python
def edit_homework(self, item):
    ...
    dialog = HomeworkDialog(self, homework=existing)
    if not dialog.exec():
        return
    existing.content = dialog.content_text
    existing.due = dialog.due_text
    existing.submit_url = dialog.submit_url
    # ← 没有 dialog.input_name / dialog.folder_name
```

**它从来没读过作业名。** 所以第二个缺陷是：
即使输入框能改，点保存也不会生效。

> **"功能异常"的报障，往往不是一个缺陷，而是一串。**
> 用户看到的是"改不了"，但中间可能有**两道**门都关着：
> 一处在界面（输入框禁用），一处在逻辑（没读取）。
>
> 所以第一步不是"修那处显眼的"，而是**把这条路径从头到尾读一遍**，
> 看它经过几个环节、每个环节是否通。

### 39.3 改名要动文件夹：三处名字必须一起改

作业的"名字"就是它的**文件夹名** —— 界面上显示的、日程栏引用的、
扫描时找到的，全都是它。所以改名必须：

1. 移动文件夹；
2. 改 `homework.json` 里的 `name`；
3. 改内容 Markdown（默认与文件夹同名）。

只改第 2 步会让两者不一致 —— 而**下次扫描又变回文件夹名**，
用户会觉得"改了又回去了"。

实现里加了**回滚**：元信息写失败就把文件夹挪回去，
绝不留"文件夹名和元信息不一致"的半成品。

```python
os.replace(folder, target)
moved = Homework.from_dict(target, {...})
try:
    save(moved)
except OSError:
    # 元信息没写成 -> 把文件夹挪回去，别留下不一致的状态
    try:
        os.replace(target, folder)
    except OSError:
        log.exception("回滚作业改名失败：%s -> %s", target, folder)
    raise
```

### 39.4 两个真实的实现陷阱（我各踩了一次）

#### 陷阱一：移动之后才判断"文件在不在"

第一版我这么写：

```python
old_markdown = content_file(folder)
os.replace(folder, target)                    # 整个目录被搬走了
...
if old_markdown.is_file():                    # ← 永远 False
    os.replace(old_markdown, new_markdown)
```

`os.replace` 把**整个目录**搬走之后，`old_markdown` 这个路径已经不存在了 ——
`is_file()` 永远返回 False，于是 **Markdown 永远不跟着改名**。

实测结果正是如此：

```
改名后: ['homework.json', '第三章习题.md']      ← 文件夹改了，md 还是旧名字
```

修法：**在移动之前**把"要不要改 Markdown"这个判断做掉。

#### 陷阱二：判断改对了，但路径用错了

改成移动前判断之后，第二版又错在路径上：

```
FileNotFoundError: [WinError 3] 系统找不到指定的路径。:
  '...\第三章习题\第三章习题.md' -> '...\第三章作业\第三章作业.md'
```

因为文件已经**在移动文件夹时被一起搬走**了。所以必须用
**新目录 + 旧文件名**去操作它：

```python
old_markdown_name = content_file(folder).name
old_markdown_at_new = target / old_markdown_name          # ← 关键
has_markdown = (folder / old_markdown_name).is_file()     # 移动前判断

os.replace(folder, target)
...
if has_markdown:
    os.replace(old_markdown_at_new, new_markdown)
```

> **这两个陷阱是同一个根源：一次"移动整个目录"之后，
> 里面所有文件的路径都变了、而文件名没变。**
>
> 所以代码里凡是"移动目录 + 单独处理其中一个文件"的组合，
> 都要问清楚：**我现在这个路径，是移动前的还是移动后的？**
> 这类错误不会有编译错误、也不会有明显异常
> （第一个甚至完全静默），只能靠实测发现。

### 39.5 尊重用户改过的文件名

还有一个边界：用户可能把 `第三章习题.md` 自己改名成了 `我的笔记.md`。
这时改作业名，**不该**把它强行拽回 `新名字.md`：

```python
if has_markdown and new_markdown.exists():
    log.info("改名后目标 Markdown 已存在，保留原文件：%s", old_markdown_name)
elif has_markdown:
    os.replace(old_markdown_at_new, new_markdown)
```

因为 `old_markdown_name` 是**按旧文件夹名算出来**的，
用户改过名之后就"算不出来"了 → `has_markdown` 为 False → 不动它。
实测：

```
用户改过 md 名后，改作业名 -> ['homework.json', '我自己改的.md', '补充材料.txt']
  （应保留 我自己改的.md）
```

> **这是"文件名既是标识又是用户数据"时的通用难题。**
> 判断标准：这个文件的名字是**我们生成的**，还是**用户起的**？
> 我们生成的才跟着改；用户起的一律不动。

### 39.6 测试里我自己踩的坑（最值得记的一个）

写完代码写测试，测试自己错了三次。前两次比较常规：

* **假失败**：我先用 `hw_dir / "第一次作业"` 去找作业，但那个目录里的
  `homework.json` 只是个占位 `{}`，不是真正的作业 ——
  于是"准备一个可编辑的作业"直接失败。改成用 `hw.create()` 建一个规范的。
* **作用域**：`_hw` 在函数**后面**才导入，Python 把整个函数里的 `_hw`
  当成局部变量，我在前面用它就 `UnboundLocalError`。就近导入解决。

第三次很值得记，因为它是**"打桩看起来成功了、其实没打上"**：

```python
# 我第一版这么打桩
_bv_mod.HomeworkDialog = _RenameDialog      # 改"模块上的属性名"
```

跑出来：

```
RN_DEBUG module attr is _RenameDialog        ← 补丁确实生效了
EH_DEBUG dialog = HomeworkDialog             ← 但实际用的还是真实类！
```

原因：`edit_homework` 里是

```python
from gwp.ui.dialogs.homework_dialog import HomeworkDialog
```

**函数内的 `from ... import X` 把名字绑定到"当时那个类对象"上**，
改模块属性名影响不到已经绑定好的那个名字。

正确做法是**替换类本身**：

```python
from gwp.ui.dialogs import homework_dialog as _hd_mod_rn
_real_dialog_cls = _hd_mod_rn.HomeworkDialog
_hd_mod_rn.HomeworkDialog = _RenameDialog
```

> **打桩要打在"被真正查找到的那个东西"上。**
>
> 同一个名字可能有两个可替换的位置：**模块的属性名**，和
> **已经导入到别处的那个对象**。改前者对后者无效。
> 判断方法：看被测代码是**模块级导入**（`import module` 然后
> `module.X`）还是**名字导入**（`from module import X`）——
> 后者要替换**源头模块里的类**。
>
> 更重要的教训是：**打桩之后要验证"桩真的被用上了"**。
> 我之所以能发现，是因为顺手打了个 `type(dialog).__name__` ——
> 如果只看"测试通过了没有"，这个假桩会一直骗下去，
> 而我可能得出"功能是好的"这个**完全相反**的结论。

### 39.7 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | "更改作业名称功能异常"（四个字，无截图） |
| 缺陷一 | 对话框在编辑模式下 `setEnabled(False)` 了名称输入框 —— 界面无入口 |
| 缺陷二 | `edit_homework` 从未读取作业名 —— 即使能改也不会生效 |
| 数据层 | 新增 `homework.rename()`：移动文件夹 + 改元信息 + 改 Markdown + **失败回滚** |
| 实现陷阱 | ①移动后才判断文件存在（永远 False）②路径必须是"新目录 + 旧文件名" |
| 边界 | 用户自己改过 md 名时不动它；重名时拦住不覆盖 |
| 测试坑 | 打桩打在了"模块属性名"上，而实际绑定的是类对象；**要验证桩被用上了** |
| 新增测试 | 27 条 |
| 学到的 | ①"功能异常"常是一串缺陷叠加；②移目录后路径要重新算；<br>③文件名属于用户时不要跟着改；④打桩要打在真正被查找的对象上 |

**这一章最值钱的三条**：

> **一、"功能异常"往往不是一个缺陷，而是两个同时掐住。**
>
> 界面上写着"作业名称"却是灰的（缺陷一），
> 而保存逻辑压根没读它（缺陷二）。
> 只修第一个，用户会发现"能输入了但不生效"；
> 只修第二个，用户会发现"还是灰的"。
>
> 所以拿到"功能异常"这种模糊报障，**先把那条路径从头到尾读一遍**，
> 数清楚中间有几个环节 —— 而不是直接去改最显眼的那一处。

> **二、移动整个目录之后，里面每个文件的路径都变了。**
>
> `os.replace(folder, target)` 之后，
> `folder / "x.md"` 已经不存在，正确的路径是 `target / "x.md"`。
> 这个错误非常隐蔽：第一版**完全静默**（判断永远 False），
> 第二版才以 `FileNotFoundError` 的形式暴露出来。
>
> 凡是"移动目录 + 单独处理其中某个文件"的组合，
> 都要明确回答：**这个路径是移动前的还是移动后的？**

> **三、打桩之后要验证"桩真的被用上了"。**
>
> 我把补丁打在 `book_view` 模块的 `HomeworkDialog` 属性上，
> 打印出来显示"补丁生效"，但 `edit_homework` 用的仍是真实类 ——
> 因为它是 `from module import X`，名字早就绑定到类对象上了。
>
> 如果我只关心"测试有没有变绿"，这个假桩会一直骗下去。
> 顺手打一行 `type(dialog).__name__` 是极便宜的保险。

---

## 第 40 章　公式、缓存与文档合并：一次四个需求

用户一口气提了四件事：

> 生成的AI总结在AI总结位置未显示   md预览时 数学符号，公式，拉丁字母内容显示异常
> summary中你补充的内容很不错，但是你补充的要标注（AI补充）
> 此外，更主要的功能是文档合并，你要把pdf以及其他文档插入到summary文档中

**四件事的难度差别很大**：一个是一行修复，一个是"框架能力不足"，
一个是提示词约束，一个是新功能。这一章按难度讲。

### 40.1 一行修复：缓存没失效

"生成的总结看不到"，但文件**确实在磁盘上**：

```
=== 数学分析 / 数学分析上 的书目目录 ===
  [文件] 数学分析上_summary.md  14201 字节
```

而数据层也认得它（`is_summary=True`）。所以问题在**界面这一侧**。

看 `Library`：

```python
def subjects(self, refresh: bool = False, with_books: bool = True):
    """扫描并返回全部科目。结果会被缓存，磁盘变化时用 refresh=True。"""
    with self._lock:
        if self._subjects is None or refresh:
            self._subjects = self._scan_subjects(with_books=with_books)
        ...
```

`book()` 是从这个缓存里取的。而生成完总结之后：

```python
def _on_summary_finished(self, result) -> None:
    self._close_progress()
    self.refresh()          # ← 只重画界面，读的还是旧缓存
```

**修法是一行**：

```python
# **先让缓存失效再刷新**。
#
# Library.subjects() 会缓存扫描结果，而 book() 是从缓存里取的 ——
# summary 文件此时刚写进磁盘，但缓存里的 Book 对象**还不知道**
# （它的 summary_path 是旧的、甚至是 None）。
self.context.library.invalidate()
self.refresh()
```

> 这个 bug 的现象很典型：**进程重启后就正常**（缓存重建），
> 在同一会话里却"怎么刷新都不出现"。
> 凡是遇到"重启就好"的显示问题，先怀疑**进程内缓存**。

### 40.2 框架能力不足：QTextBrowser 不认识 LaTeX

用户说"数学符号、公式、拉丁字母内容显示异常"。
先量，不猜 —— 用 `QTextDocument.toPlainText()` 反查"用户实际看到的字"：

```
[行内 LaTeX]  显示: '设 $\varepsilon > 0$，存在 $N$ 使 ...'   ← 原样显示！
[拉丁字母]    显示: '设函数 f(x) 在 x_0 处连续，则 f ∈ C^0。'  ← 正常
[Unicode 数学] 显示: '∀ε>0, ∃N, ∀n>N: |aₙ−A|<ε'              ← 正常
```

**结论很清楚**：拉丁字母没问题，Unicode 数学符号也没问题 ——
问题只有一条：**提示词要求"公式用 LaTeX"，而 QTextBrowser 不认识 LaTeX**。

真实数据里这个量很大：

```
美元号公式: 134 处
LaTeX 命令: 210 处（\varepsilon \frac \lim \int …）
```

所以只能**把公式渲染成图片**。选型时评估过三条路：

| 方案 | 结论 |
| --- | --- |
| 装 matplotlib（mathtext） | 排得好，但**明显增大安装包**（本项目一直控制在 ~77MB） |
| 只转 Unicode（`\varepsilon`→ε） | 分式、矩阵、积分上下限会变形 |
| **自己用 Pillow 排一个够用的子集** | ✅ 不加依赖，可控、可测试 |

于是写了 `gwp/services/math_render.py`：一个**盒子模型**排版器
（盒子有"基线以上/以下高度"，横向拼接时按基线对齐）。

**排版能力**：上下标、分式、根号、上下限堆叠（`\lim_{n\to\infty}` 的
`n→∞` 排在 `lim` **正下方**）、希腊字母、常用运算符、函数名正体。

**排不出的明确退化**：矩阵、多行对齐等**不猜** ——
整条按纯文本显示并标 `degraded=True`。
数学里**画错比画丑严重得多**。

### 40.3 一条"看起来对、其实不对"的排版

第一版渲染出来是这样（我真的把图存下来看了）：

```
lim  aₙ = A
n → ∞            ← 上下限跑到了右边、还带一个奇怪的偏移
Σ  aᵢ xⁱ
i=1
```

`\lim_{n \to \infty}` 里的 `_{...}` 被当成普通下标挂在了右边。
**数学排版里 `\lim` 的趋近条件必须在正下方**，挂右边是错的。

修法是给"可堆叠运算符"单独一条路径：

```python
#: 需要"上下堆叠上下标"的运算符（而不是放到右边）
_STACK_OPERATORS = {"lim", "min", "max", "sup", "inf", "sum", "prod",
                    "int", "iint", "oint", ...}
```

另外两个细节：

* `\mathbb{N}` 这种**字体命令**不该让整条公式退化 —— 取内容继续排就行；
* 真正不认识的命令（`\foobarcmd`）只把**那一条**画成原文并标灰，
  其余部分照常排（第一版是整条退化，一个 `\mathbb` 就让整行变成源码）。

> **"渲染出来看一眼"是这一节的关键动作。**
> 如果只跑断言（"能渲染成图片"= True），我会得到一个
> **排版错误但测试全绿**的渲染器。

### 40.4 图片放进 HTML 的两个坑

公式渲染成图片之后，要嵌进 HTML 给 `QTextBrowser` / `PyMuPDF Story` 看。

**坑一：`Story` 不加载 `file://` 图片。** 实测三种 archive 写法都不行：

```
无 archive                文本='设 [image]。'
Archive(source.parent)    文本='设 [image]。'
Archive() 空              文本='设 [image]。'
```

**修法**：把图片**内嵌成 `data:` URI**（base64）—— 它不依赖任何文件访问：

```
文本: '设 \n 成立。'
图片对象数: 1
非白像素: 2648      ← 图确实画上了
```

**坑二：裸 HTML 会被当成字面文本。** 我为了给公式图加对齐用的 class，
写了裸 `<img class='gwp-eq' ...>`，结果整段标签被打在了正文里 ——
因为本项目启用了 `attr_list` 扩展。

**修法**：用 Markdown 图片语法生成，然后在**渲染后的 HTML** 上正则加 class。

**坑三（观感）：图太大。** 公式图是 15 号字 × scale=3 渲染的
（约 84×57 像素），HTML 里 1:1 显示就比正文大好几倍、把行撑开。
修法是 CSS 按 `em` 缩回文字大小：

```css
.gwp-doc img.gwp-eq { height: 1.05em; width: auto; vertical-align: -0.22em; }
```

> **注意这里的取舍**：图片本身必须是**高分辨率**的（PDF 导出才清晰），
> 而显示尺寸要**跟着字体走**。所以"渲染分辨率"和"显示尺寸"必须是
> **两个独立的量** —— 我第一版把它们当成一个，于是要么模糊要么过大。

### 40.5 文档合并：一个需求、四种文件、一条统一的路

需求最关键的一句是"**如果插入困难，便以图片插入**"。
它其实给了一个**统一的降级策略**，顺着它设计反而最简单：

```
PDF                     → 每页栅格化成 PNG        （需求直接指定）
图片                    → 原样复制
Word/PPT/Excel/纯文本   → 抽成 Markdown → PyMuPDF Story 排版 → 逐页栅格化
```

**为什么连"能抽文字"的 Word 也走图片**：抽 Markdown 是为了**内容不丢**，
渲染成图片是为了**版面不丢**（表格、图表）。两者结合才既完整又能看。

排版这一步又踩了一次 `Story` 的 API：

* `write_with_links(rectfn)` 的 `rectfn` 会收到**两个参数**
  （`rect_num, filled`）—— 我第一版写了个零参回调，`TypeError`；
* 它**直接返回 `Document`**，不是 PDF 字节 —— 我当成字节又 `fitz.open` 了一次，
  于是每份文档都报 `bad stream`。

两次都**没有让功能失败**，因为兜底路径接住了（"插入困难就以图片插入"）：

```
OK   教材.pdf     图片= 3
OK   示意图.png   图片= 1
OK   笔记.md      图片= 1  （排版器不支持其中部分格式，已按纯文本合并）
OK   讲义.docx    图片= 1  （同上）
失败数: 0
```

> **兜底路径的价值在这一节体现得很直接：**
> 排版器两次因为 API 用法错误而失败，但**用户侧一份资料都没丢** ——
> 只是那几份退成了"纯文本画成图片"。
> 如果当时没有兜底，这两次都是"功能不可用"。

**幂等**也是刻意做的（和之前的迁移一样）：

```python
def append_to_summary(summary_text: str, section: str) -> str:
    """把合并小节追加到总结末尾。

    **重复合并不会越插越多**：上一次生成的整段（从标记到文件末尾）会被替换掉。
    """
```

实测：合并两次，标记数仍是 1、长度不变。

### 40.6 "AI 补充"要标注：这是提示词约束，不是代码

需求："你补充的要标注（AI 补充）"。

这件事**只能靠提示词**：软件不知道总结里哪句话是 AI 新写的、哪句来自用户笔记 ——
只有模型自己知道。所以在三个总结提示词里都加了明确约定：

```
10. **你自己新增的内容必须标注**（需求："你补充的要标注（AI 补充）"）：
    * 每一处由你新增/推导/扩展的内容，紧跟在那处后面写（AI 补充）；
    * 引用用户原文的部分不要加这个标记，也不要把原文改写成别的说法；
    * 如果整节都是你新增的，在小标题后面写（AI 补充）就行；
    * 标记要**少而准**：只标你真正新增的东西，不要每段都标。
```

注意最后一条 —— **不加"少而准"，模型会把每一段都标上**，
于是标记失去信息量（等于没标）。

> **凡是要模型"区分信息的来源"，都必须在提示词里明确规则，
> 而且要包含"不要过度标注"这一面。** 只说要标，就一定会标满。

### 40.7 复盘

| 类别 | 内容 |
| --- | --- |
| 需求① | summary 不显示 → `Library` 缓存没失效，加 `invalidate()`（一行） |
| 需求② | 公式显示异常 → QTextBrowser/PyMuPDF 都不认识 LaTeX → 自己排版成图片 |
| 需求② | 新增 `services/math_render.py`（Pillow 盒子模型，**不加 matplotlib**） |
| 需求② | 图片嵌入的两条路：预览用 `file://`，Story 必须用 `data:` URI |
| 需求③ | "AI 补充"标注 → 三个提示词加明确规则（含"不要过度标注"） |
| 需求④ | 新增 `services/source_merge.py`：PDF 每页转图、其它排成图、图片集中存放 |
| 需求④ | 合并幂等 + 自动备份 + 单份失败不中断 |
| 新增测试 | 65 条 |
| 学到的 | ①"重启就好"的问题先怀疑缓存；②渲染出来的东西要**看一眼**；<br>③把"渲染分辨率"和"显示尺寸"分开；④兜底路径让 API 用错也不丢数据 |

**这一章最值钱的三条**：

> **一、"重启后就正常"的显示问题，先怀疑进程内缓存。**
>
> 文件在磁盘上、数据层也认得，唯独界面上看不到 ——
> 因为界面读的是**几十秒前**的缓存对象。
> 判断方法：**如果重启能解决，那就不是"没生成"，而是"没看到"。**

> **二、做"渲染/排版"这类功能时，一定要把产物拿出来看。**
>
> 我的公式排版器断言全绿（"能渲染成图片"= True），
> 但第一版的 `\lim_{n\to\infty}` 把趋近条件挂在了右边 ——
> **排版错了，测试照样过**。
> 是我把图存下来打开看，才发现"lim 下面应该有一行 n→∞"。
>
> 断言能证明"没崩"，只有眼睛能证明"对不对"。

> **三、"渲染分辨率"和"显示尺寸"必须是两个独立的量。**
>
> 公式图为了 PDF 清晰必须高分辨率（84×57 像素），
> 但在 HTML 里 1:1 显示就比正文大好几倍。
> 正确做法是**渲染时给足像素、显示时用 `em` 跟着字体缩**。
> 把两者当成一个量的结果是：要么模糊、要么过大 —— 我两种都试过。

---

## 第 41 章　排版器不收敛：一次 12 GB 的清理

这一章讲一个**我没有修好、但成功限制住**的问题。它比前面任何一章都更
贴近真实的工程处境：**有些 bug 你查不到底，但你必须让它不再造成伤害。**

### 41.1 现象：书稿 PDF 变成 987 MB

重新生成书稿之后，我注意到产物大小完全不对：

```
=== 三处书稿 PDF 的大小 ===
  987.53 MB   10/10/2026 11:50:58   Document\开发实践——Great White Planet.pdf
  991.75 MB   10/10/2026 12:09:01   D:\Great White Planet\开发实践——Great White Planet.pdf
 9610.91 MB   10/10/2026 12:12:13   DeepseekData\开发实践——Great White Planet.pdf
```

而这次构建**打印的却是** `(225 页, 8065 KB)`。也就是说：
脚本报的是正常结果，磁盘上却是 1 GB 的文件。

先看内部：

```
开发实践——Great White Planet.pdf: 5013 页
  内嵌图片总字节: 0.0 MB，共 0 张
```

**5013 页、没有一张图**。而源 Markdown 只有 **249299 字符 / 10563 行** ——
正常排出来是 225 页左右。这个 `5013` 是个很可疑的数字。

在排版代码里找到了它：

```python
if pages > 5000:      # 防御性上限
    break
```

**5013 = 撞到了"防御性上限"。** 说明排版循环**根本没打算结束**。

### 41.2 定位：先用真实导出器，别自己造判定函数

我一开始写了个自建的判定函数（`story.place()` 循环 N 次看 `more` 是否变 0）。
它给出的结论**自相矛盾**：

```
前  40 行 -> 1          （说 OK）
前  51 行 -> 排不完      （说挂了）
前  60 行 -> 排不完
```

可同一份内容用**真实导出器**跑：

```
    60 行 ->     2 页  (0.3s)
```

60 行明明是 2 页就结束的。**是我的判定函数不可靠。**

问题出在我给循环设了太小的上限（40 次），又把"没在上限内结束"当成
"排不完" —— 而真实排版可能只是需要更多轮，或者我复用了同一个矩形对象
（`story.place(rect)` 会**就地改写**传进去的 rect）。

> **教训一：能调用真实代码路径时，绝不要自己写一个"近似版"来下结论。**
>
> 我的自建判定函数不仅慢，还把我引向了**错误的行号**（第 51 行），
> 我在那上面浪费了好几轮。换成"把内容写成文件、调用和
> `make_dev_book.py` 完全相同的导出函数"之后，结论立刻稳定可复现。

改用权威判定后，二分很快就收敛了：

```
     60 行 ->     2 页
     70 行 ->     2 页
     73 行 ->  5001 页     ← 只多 3 行
    400 行 ->  5001 页
```

**第 70 行和 73 行之间**，就翻了 2500 倍。

### 41.3 排除：不是 CSS，不是宽度，不是某个字符

第 71 行是本书开头那个 34 行的大表格的最后一行，第 73 行是紧跟其后的
`### 怎么读这本书`。看起来像"表格 + 标题"触发的。于是逐个排除：

| 假设 | 实验 | 结论 |
| --- | --- | --- |
| 是 CSS 的锅 | 换空 CSS / 加 `page-break-inside: avoid` / 改 `table-layout` | **都卡**，无关 |
| 是版心太窄 | 版心 559 / 700 / 1000 / 1600 | **都卡**，无关 |
| 是某个字符 | 删掉 `` `900+` `` 的反引号 | **还卡** |
| 是那一行 | 整行删掉 | **还卡** |
| 是标题层级 | `###` 改 `##` / 标题前加空行 | **还卡** |
| 是表格后面的内容 | 只保留到第 71 行 | **还卡** |

而与此同时，这些**单独**跑全都正常：

```
表格 32 行                    -> 2 页
表格 + 空行 + ### 标题         -> 2 页
表格 + 标题 + 更多             -> 3 页
```

**单独都正常，合起来就卡死。** 删掉任何一个特征都不解决 ——
这是 PyMuPDF 1.28.2 的 `Story` 排版器在这个特定内容组合下的**不收敛缺陷**。

那么"不收敛"具体长什么样？每轮的返回值是：

```
第1轮 more=1 filled=(36.0, 36.0, 559.0, 832.7)
第2轮 more=1 filled=(36.0, 36.0, 559.0, 832.7)
第3轮 more=1 filled=(36.0, 36.0, 559.0, 832.7)
...
```

`more` 永远是 1，而且**每页的填充区域一模一样** —— 它在无限重复
"又排满了一页"，永远排不完。

### 41.4 处置：修不了，就让它不造成伤害

追到这个程度，成本已经明显超过收益了。于是我改变目标：
**不再试图让它排对，而是保证它不会写出一个 1 GB 的废文件。**

在 `gwp/services/pdf_exporter.py` 的排版循环里加了**不收敛检测**：

```python
# ---- 不收敛检测 ----
#
# 实测：某些内容组合会让 PyMuPDF 的 Story **永远返回 more=1**，
# 而且每页都填满同样的高度 —— 于是一路排到 5001 页、
# 产出近 1 GB 的废 PDF（书稿就这样坏过一次）。
#
# 正常文档每页的填充高度都在变；连续几百页"填充高度一模一样"
# 只可能是排版器卡住了。这里宁可报错，也不要写出一个
# 几百 MB、打开就卡死的文件。
current = tuple(round(float(v), 1) for v in filled)
if current == last_filled:
    stall += 1
    if stall >= _STALL_PAGE_LIMIT:
        raise PDFExportError(
            f"排版无法收敛：连续 {_STALL_PAGE_LIMIT} 页内容完全重复"
            f"（已排到第 {pages} 页）。这通常意味着文档里有"
            "排版器处理不了的元素组合，请把内容拆成几个较小的文件，"
            "或先导出其中一部分。"
        )
else:
    stall = 0
    last_filled = current
```

`_STALL_PAGE_LIMIT = 120`：正常文档不会有 120 页填充区域一模一样，
所以阈值很宽松；但它必须在"排到 5001 页"之前生效。

> **教训二：判断"卡住了"比判断"排错了"容易得多，而且往往就够了。**
>
> 我不需要知道排版器**为什么**不收敛，只需要知道
> "**连续 120 页一模一样**"这件事在正常文档里不可能发生。
> 这个信号便宜、可靠、立刻可用。
>
> 工程上和"我要修好它"同样重要的一件事是：
> **给失败设一个能被发现的边界**。原来的代码也有边界（5000 页），
> 但它的处置是 `break` —— **默默产出一个坏文件**；
> 现在改成"报错并丢弃"，失败就变成了用户看得见的一句话。

顺手还修了一处：`story.place(rect)` 会**就地改写**传入的矩形，
原代码在循环外只建一次 `where` 并反复传入。虽然实测它不是本次的原因，
但那个写法本身就是错的，已改成每页新建。

### 41.5 决定：不要 PDF，只留 Markdown

把根因查清、把伤害限制住之后，我向用户说明了情况。用户的决定很干脆：

> 直接删掉 pdf 不要了，留下 md 就行

于是：

```
删除前：
  987.5 MB  Document\开发实践——Great White Planet.pdf
  991.7 MB  D:\Great White Planet\开发实践——Great White Planet.pdf
 9610.9 MB  DeepseekData\开发实践——Great White Planet.pdf
  合计: 11.32 GB
```

再加上构建中断留下的中间产物（`.pages.pdf` 820 MB、`_front.pdf` 3.6 MB），
**一共释放约 12.1 GB**。

同时把 `make_dev_book.py` 的默认行为改成**只同步 Markdown、不生成 PDF**
（`--pdf` 才排），这样以后不会再有脚本悄悄把 1 GB 的废文件写回来。

> **教训三：交付物里"你以为必须的"那部分，可能根本没人要。**
>
> 我为这个 PDF 花了十几轮去查一个第三方库的排版缺陷。
> 而用户的真实需求从头到尾只是"**书稿要能持续增补**" ——
> Markdown 完全满足，PDF 只是我自己加的仪式感。
>
> **在深挖一个技术问题之前，值得先问一句：这个产物真的需要吗？**
> 我要是早问，能省下大半的时间。

### 41.6 复盘

| 类别 | 内容 |
| --- | --- |
| 现象 | 书稿 PDF 变成 987 MB / 5013 页（脚本却报"225 页"） |
| 真凶 | PyMuPDF 1.28.2 `Story` 在某些内容组合下不收敛：`more` 永远为 1、每页填充区域相同 |
| 排除项 | CSS、版心宽度、单个字符、标题层级、表格之后的任何内容（全部无关） |
| 修不了的部分 | 未定位到最小触发条件 —— 单独都正常、合起来卡死 |
| 限制伤害 | `_STALL_PAGE_LIMIT = 120`：连续 120 页填充一致就报错并丢弃产物 |
| 顺带修 | `story.place(rect)` 会改写矩形，改为每页新建 |
| 最终决定 | 用户不要 PDF，只留 Markdown；删除 3 份 PDF + 中间产物，**释放约 12.1 GB** |
| 默认行为 | `make_dev_book.py` 默认不再排 PDF（`--pdf` 才排） |
| 学到的 | ①有真实路径就别自造判定函数；②给失败设一个能发现的边界比修好更容易也更必要；<br>③动手前先问"这个产物真的需要吗" |

**这一章最值钱的三条**：

> **一、能调用真实代码路径时，绝不要自己写"近似版"来下结论。**
>
> 我自建的判定函数给出了**错误的行号**，把我引到第 51 行、浪费了好几轮。
> 换成直接调用导出函数之后，同样的二分几轮就收敛。
> 近似版的每一个简化（循环上限、复用对象、跳过某些步骤）
> 都可能成为错误结论的来源。

> **二、给失败设一个能被发现的边界，比修好它更容易，也常常同样必要。**
>
> 原代码其实**已经有**边界（5000 页），但它的处置是 `break` ——
> 于是"出错了"被翻译成"产出一个 987 MB 的坏文件"，
> 用户只会觉得软件卡，不会知道发生了什么。
> 把 `break` 换成 `raise`，同一件事就从"静默的数据灾难"
> 变成"一句能读懂的错误提示"。
>
> **凡是兜底逻辑，都要问一句：它兜住之后，用户知道出问题了吗？**

> **三、动手深挖之前，先问"这个产物真的需要吗"。**
>
> 我为一个"书稿 PDF"投入了十几轮，去查一个第三方排版库的缺陷；
> 而用户的需求从来只是"书稿要能持续增补"。
> 我删掉 12 GB 文件的那一刻，才意识到这一章本来可以不存在。
>
> 这不是说要偷懒，而是说 **"把它做对"和"它是否必要"是两个不同的问题，
> 后者应该先问。**

---

## 第 42 章　把 AI 从主流程里拿出来

用户对刚做好的「文档合并」提了修改：

> summary中板块，不需要你补充内容了（或者你可以仅仅在文档末尾补充tips），
> 按照用户上传的文件来，不要AI识别文字了，直接插入图片或文件
> AIsummary中 AI可以根据自己的理解改变图片插入顺序，
> 实现不同文件夹内容，的混排插入

**这不是加功能，是改职责。** AI 从"写正文的人"变成"排顺序的人" ——
而且要默认不参与。

### 42.1 先分清"哪些还能留"

四条要求里其实混了三件不同的事：

| 要求 | 性质 |
| --- | --- |
| 不要 AI 补充内容 | **减法**：把 AI 从主流程里拿掉 |
| 可以直接插入图片或文件 | **已有能力**：上一章刚做的 |
| 末尾可以补充 tips | **加法**（但很小） |
| AI 可以改变图片插入顺序实现混排 | **加法**（新能力） |

先做减法那部分，因为它决定了另外两件事放在哪里。

### 42.2 减法要减干净，否则会留后门

「生成总结」原来走的是"收集资料 → 交给 AI → AI 写出一份正文"。
现在改成"收集资料 → 转成图片 → 插进 summary"。

改完主按钮之后，我在代码里搜了一遍，找到一个**必须处理的东西**：

```
book_view.py:1982:  self._start_generation(dialog.extra_instruction)
```

这是「预览将总结的资料」那个入口 —— 它让用户填"额外要求"，
然后走**老的 AI 写正文**那条路。

也就是说：**主按钮改了，但另一个入口还通着老行为。**
用户从菜单点进去，AI 又开始写正文了。

> **教训：改"行为"的时候，要按"行为"去搜，而不是按"按钮"去搜。**
>
> 我一开始只改了 `generate_summary`。但"让 AI 写正文"这件事有**两个**
> 调用点。正确的搜法是找**那个行为的实现函数**
> （这里是 `_start_generation`），看谁在调它 —— 一搜就露出来了。

处理方式：

* `preview_materials` 改成**只列清单**（文件名、来自哪个栏目、多大、几页），
  不再显示"发送给 AI 的内容"，也不再让填额外要求；
* **把 `_start_generation` 整个删掉**。它已经没有调用方了，
  而留着的风险是：以后有人顺手用它，就又绕过新行为了。

那个 `MaterialsDialog` 我也顺手改了名（`SummarySourcesDialog`），
因为它的**用途**变了 —— 名字还叫"材料/提示词预览"会误导后来的人。

> **删掉没有调用方的"死代码"，不是洁癖。**
> 一个还能工作的旧路径，就是一个**随时会被重新接错的旧路径**。

### 42.3 加法要放对位置：AI 只在"可选步骤"里出现

新的 AI 职责是"排页序"。这里有几个设计决定值得说：

**一、默认关闭。** 因为用户明确说了"不要 AI 识别文字了"。
所以确认框里那个复选框默认是**不勾**的；不勾就**完全不发请求**。
（勾过一次会记住偏好，下次默认勾上 —— 用户的意图应该被记住。）

**二、只读每页开头一小段（160 字）。** 目的是判断"这页讲什么"，
不是理解全文。取多了会让请求变贵变慢，而对判断几乎没有帮助。

**三、只输出顺序，不输出内容。** 提示词明确要求：

```
1. 目标是**混排**：不要把同一个文件的页全部堆在一起……
2. **不能增删、不能重复、不能改编号** —— 你只输出顺序。
3. 每页都必须出现在结果里，一次且仅一次。
```

**四、校验必须严，而且失败要整体退回。**

```python
missing = valid - set(seen)
unknown = set(seen) - valid
if unknown:
    return None, f"AI 给出了不存在的页编号：{sorted(unknown)[:5]}"
if missing:
    return None, f"AI 漏掉了 {len(missing)} 页（例如 {sorted(missing)[:5]}）"
if len(seen) != len(valid):
    return None, "AI 返回的页编号有重复"
```

为什么这么严：**排序排错一份就会丢页或重复页**，
那比"不混排"严重得多。所以宁可整条不用、退回原顺序。

而且混排失败**不算错误** —— 它只是锦上添花：

```python
except Exception as exc:
    log.warning("AI 混排请求失败", exc_info=True)
    return False, f"AI 不可用（{type(exc).__name__}），已按原顺序"
```

> **给 AI 的任务，要区分"错一点点可以接受"和"错一点点就毁了"。**
>
> 让 AI 写正文：写得差一点还能用，所以失败了可以重试、可以兜底。
> 让 AI 排页序：漏一页就是**数据丢失**，所以必须**全对或不用**。
>
> 这两类任务的校验强度应该完全不同 —— 而很多"AI 功能"出问题，
> 就是因为对第二类用了第一类的宽松标准。

### 42.4 混排之后，"一份资料一个小节"就不成立了

原来的 summary 是这么组织的：

```markdown
### 笔记 · notebook/1集合与映射.pdf
![...](p1.png)
![...](p2.png)

### 易错题 · error-prone/易错.md
![...](p1.png)
```

每份资料一个 `###` 小节。但**混排之后资料被打散了**：
甲的第 1 页、乙的第 2 页、甲的第 3 页可能连着出现 ——
再用"一份资料一个小节"就表达不了。

所以 `build_section` 要分支：

```python
if report.mixed and report.ordered_pages:
    return _with_failed(_mixed_lines(report, lines), report)
```

`_mixed_lines()` 按**整体页序**输出，只在"来源发生变化"时插一行小标题：

```python
current_label = ""
for page in report.ordered_pages:
    if page.label != current_label:
        lines.append(f"### {page.label}")
        current_label = page.label
    ...
```

> **一个数据结构变了，输出格式往往也得跟着变。**
> 我一开始只改了"生成顺序"，忘了"组织方式"也依赖那个假设 ——
> 结果是混排后仍然按资料分块输出，等于白混。

### 42.5 一个字符串包含另一个：计数陷阱

这次我又在一个**测试断言**上栽了，而且栽得很典型。

标记常量是两个：

```python
MERGE_MARKER = "<!-- GWP:MERGED-SOURCES -->"
MERGE_END_MARKER = "<!-- GWP:MERGED-SOURCES-END -->"
```

测试里我写：

```python
_again.count("GWP:MERGED-SOURCES") == 1      # 期望 1
```

结果得到 **2**：

```
[FAIL] **重复生成不会越插越多（资料段被替换）** -> 2 / 1
```

看起来像"产品写出了两份标记"这种严重问题。实际上 ——
**`"GWP:MERGED-SOURCES"` 是 `"GWP:MERGED-SOURCES-END"` 的子串**，
所以那一个结束标记也被数进去了。

我用一个独立的单元探针验证了产品逻辑：

```
build_section 里 marker 数: 1 0
compose 后: 1 1
append 后: 1 1
长度: 356 -> 356
```

**产品是对的，错的是我的计数方式。**

> **教训：拿一个标记/前缀去 `count` 之前，先问"它是不是别的东西的子串"。**
>
> 我给两个常量起了只差 `-END` 的名字，于是"起始标记"这个名字
> 天然是"结束标记"的前缀。这种命名很自然，但让 `count` 变得危险。
>
> 更值得记的是**排查顺序**：断言失败时，先怀疑**断言**，再怀疑产品。
> 我这次的失败信息"2 / 1"看着像产品 bug，
> 但一个 10 行的独立探针 30 秒就证明了产品没问题。

### 42.6 一个字符的幂等差异

同一次改动里还有一处更细的：

```
[FAIL] **重复合并不会越插越多** -> 936 vs 937
```

差**一个字符**。原因是"首次追加"和"后续替换"两条分支补的换行数不一样：

```python
# 首次
return text.rstrip() + "\n\n" + body + "\n"
# 替换
return text[:start] + body + "\n\n" + tail
```

修法是让两条分支**产出完全一致**，最后统一收尾：

```python
if start >= 0 and end > start:
    result = text[:start] + body + "\n\n" + tail
else:
    result = text.rstrip() + "\n\n" + body + "\n\n"
return result.rstrip() + "\n"
```

> **幂等这种东西，很容易做到"差不多幂等"。**
>
> 差一个换行，肉眼看不出来，用户也永远不会发现 ——
> 但断言会发现，而断言是对的：**一个说"重复执行结果一样"的功能，
> 就应该真的一个字节都不差**。差别小不是理由。

### 42.7 复盘

| 类别 | 内容 |
| --- | --- |
| 需求性质 | **改职责**，不是加功能：AI 从"写正文"改为"排页序（可选）" |
| 减法 | 「生成总结」不再调用 AI 写正文；删掉无调用方的 `_start_generation` |
| 减法（易漏） | `preview_materials` 是**第二个**老行为入口 —— 按"行为"搜才找得到 |
| 加法 | AI 混排：默认关闭、只读每页 160 字、只输出顺序 |
| 加法校验 | 漏页/多页/重复/非 JSON → **整条拒绝**，退回原顺序（排序错=丢页） |
| 结构 | 混排后改用"整体页序 + 来源变化时插标题"，不再一份资料一小节 |
| 提示 | 「使用提示」固定文字，用一对标记固定在**文档末尾** |
| 测试坑① | `count` 一个标记时踩了子串（起始标记是结束标记的前缀）→ 2/1 |
| 测试坑② | 首次追加与后续替换差 1 个换行 → 幂等断言挂 |
| 学到的 | ①按"行为"搜调用点，别按按钮搜；②死代码要删；<br>③AI 任务的容错标准分两类；④断言失败先怀疑断言 |

**这一章最值钱的三条**：

> **一、改行为时，按"那个行为的实现函数"去搜调用点。**
>
> 我只改了 `generate_summary`，但"让 AI 写正文"还有第二个入口
> （菜单里的"预览将总结的资料"）。要是没搜出来，
> 用户从菜单进去就会看到 AI 又开始写正文 —— 而"我明明说过不要了"。
>
> 搜按钮名只会找到按钮；搜**行为**才能找到所有出口。

> **二、让 AI 干活之前，先定清楚"错了会怎样"。**
>
> 写正文：差一点能接受 → 可以重试、可以兜底、可以只警告。
> 排页序：漏一页 = 丢内容 → 必须**全对，否则不用**。
>
> 这两类用同一套宽松校验，是很多 AI 功能悄悄丢数据的根源。

> **三、断言失败时，先怀疑断言。**
>
> `2 / 1` 看起来像"产品写了两份标记"这种严重 bug。
> 一个 10 行的独立探针就证明了产品没问题 ——
> 错的是我拿一个**前缀**去数了包含它的字符串。
>
> 这个错误的代价本来很小（改一行断言），
> 但如果我先去"修产品"，就会把一处正确的代码改坏。

---

## 第 43 章　闪退：Qt 在"线程还在跑"时会直接中止进程

用户报了两个症状：

> 修改作业名称仍然异常　1 作业文件夹名称未改变　2 会闪退

**两个症状，两个完全不同的原因。** 而且第二个比第一个严重得多。

### 43.1 先分辨：哪些证据是真的

这次排查里，**"证据"本身骗了我两次**，值得先讲清楚。

**第一次骗我的是我自己写的判定函数。** 我先写了个脚本模拟"改名"，
它报告"改名成功"。但那是个**假对话框** —— 我替换掉了真实的
`HomeworkDialog`，于是压根没走真实路径。换成真对话框才确认。

**第二次骗我的是我自己的测试脚本。** 我注意到每次跑测试脚本，
退出码都是 `-1073740791`（= `0xC0000409`）。我差点把它当成"用户遇到的闪退"，
但**它其实是我脚本自己的问题**：我建了 `MainWindow` 就直接结束，
而预扫描线程还在跑 —— 脚本自己触发了那个崩溃。

真正的用户证据是 **Windows 事件日志**：

```
[10-10 11:19:33] Application Error
  出错应用程序名称： pythonw.exe
  出错模块名称： Qt6Core.dll
  异常代码： 0xc0000409     （BEX64）
```

这才证明"用户的软件确实硬崩溃过"，而且崩在 **Qt 内部**，
不是我们的 Python 代码 —— 这解释了**为什么日志里一个字都没有**。

> **教训一：报"闪退"时，日志里什么都没有，本身就是最重要的线索。**
>
> Python 异常一定会留痕（哪怕只是 `pythonw` 吞掉）。
> 而"什么都没有 + 进程消失"只有一种可能：**不是 Python 异常**，
> 是原生层的硬崩溃。
> 这时候该查的是 **Windows 事件日志**，不是应用日志。

### 43.2 把它复现出来

硬崩溃最难的地方是"没法调试"。所以先做一件事：
**写一个十来行、必定崩的最小脚本**。

```python
class Slow(QThread):
    def run(self):
        time.sleep(6)          # 模拟"预扫描还没跑完"

app = QApplication(["t"])
w = QWidget()
w.show()
t = Slow(w)                    # parent=w -> Qt 会随 w 一起销毁它
t.start()
QTimer.singleShot(2000, w.deleteLater)     # 模拟退出
QTimer.singleShot(2500, app.quit)
app.exec()
```

跑出来：

```
QThread: Destroyed while thread '' is still running
退出码 -1073740791        ← 0xC0000409，和用户事件日志里一模一样
```

**这就是根因。** Qt 有一条会**直接中止进程**的检查：
如果一个 `QThread` 对象被析构时它还在运行，Qt 调 `qFatal` 然后杀进程。

复现的价值在这一步体现得最明显：**从"随机闪退"变成了"必然复现"**，
接下来每一步修改都能立刻验证。

### 43.3 为什么原代码没防住

原代码其实是**防过的** —— `MainWindow.closeEvent` 里有：

```python
if self._startup_worker is not None and self._startup_worker.isRunning():
    self._startup_worker.wait(3000)
```

问题在两个地方：

1. **3 秒不够。** 预扫描 7 个科目实测要 20 多秒。3 秒一到就放弃，
   窗口照常销毁 —— 线程还在跑。
2. **只等了这一个线程。** 项目里有 5 个 `QThread` 子类
   （`AIWorker`、`SimpleWorker`、`PrepareWorker`、`WeatherWorker`、`StartupWorker`），
   而"退出时还在跑"的可能是**任何一个**：用户在 AI 回答时关窗口、
   在天气请求进行中关窗口……

> **教训二：这种"每个资源都要在某处记得释放"的写法，一定会漏。**
>
> 它把"正确性"分散到了每一个调用点。今天补一个 `wait`，
> 明天加了新线程就又漏一个 —— 而漏掉的后果是**随机闪退**，
> 用户完全无法描述、开发者完全无法复现。

### 43.4 修法：一个登记处，一个退出入口

不再"在某一个地方记得等某一个线程"，改成集中管理（`core/threads.py`）：

```python
def register(thread):      # 线程创建时登记
def unregister(thread):    # 线程结束时注销
def shutdown():            # 退出时统一处理
```

**关键在 `shutdown` 的顺序，而且这个顺序是实测出来的：**

```python
def shutdown(...):
    detach_all()      # 先 setParent(None)：Qt 不再连带销毁它
    stop_all(...)     # 再 quit() + wait()：等它自己收工
```

为什么**必须先脱钩**：项目里的线程几乎都带父对象
（`AIWorker(task, parent=self)` 这类）。这是好习惯 ——
父窗口一销毁 Qt 就顺手回收它。但在**退出**时它变成了坑：

> 窗口 `deleteLater()` → Qt 销毁它的子 `QThread` → 线程还在跑
> → `qFatal` → **进程被中止**。
>
> 而这一切发生在 **Qt 内部**，我们**还没机会**去 `wait()`。

我实测过两种顺序：

| 做法 | 结果 |
| --- | --- |
| 只 `wait()`，不脱钩 | 仍然崩（Qt 先销毁了它） |
| **先 `setParent(None)`，再 `wait()`** | **退出码 0** ✅ |

脱钩之后线程对象仍被登记表持有（**强引用**，不是弱引用 ——
弱引用在这里毫无意义，线程会被回收掉），所以不会被 Python 垃圾回收。

**等待也分两轮**：先 2 秒的正常预算，没结束再给 20 秒兜底。
宁可退出慢几秒，也不要闪退。

### 43.5 两个必须补上的东西

#### 一、全局异常钩子（`core/logging_setup.py`）

软件用 `pythonw.exe` 启动 —— **它没有 stderr**。
所以任何未捕获的异常都不会打印到任何地方，进程直接退出。

```python
sys.excepthook = _main_hook            # 主线程
threading.excepthook = _thread_hook    # 后台线程（AI 请求、天气、唤回都在线程里）
```

装上之后，"静默消失"至少会变成日志里的一条 `CRITICAL`。
（它抓不到 Qt 的硬崩溃 —— 那种只有 Windows 事件日志有记录。）

#### 二、Windows 本地崩溃转储

为了今后再遇到硬崩溃能查，我打开了 WER LocalDumps：

```powershell
HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\pythonw.exe
    DumpFolder = ...\DeepseekData\crashes
    DumpType   = 2      # 完整转储
```

这样下次硬崩溃会留下一个可以用调试器打开分析的 `.dmp`
（这次没生成是因为 BEX64 走的是另一条上报路径，但配置留着有用）。

### 43.6 另一个症状：文件夹名没变

"闪退"查清之后回头看第一个症状。数据层是好的：

```
改名前: ['homework.json', '作业甲.md', '附件.pdf']
改名后磁盘上: ['新作业名']
新目录内容: ['homework.json', '新作业名.md', '附件.pdf']
    homework.json 里的 name: 新作业名
```

那就只剩一个解释：**用户点的不是这条路**。

我按"改名"这个**行为**去搜调用点（不是按按钮搜），果然找到**两个**：

| 入口 | 实现 | 行为 |
| --- | --- | --- |
| 「编辑作业…」 | `edit_homework` → `hw.rename()` | 文件夹 + 元信息 + 内容 md ✅ |
| 「重命名…」 | `_rename_item` → `file_ops.rename_path()` | **只改文件夹** ❌ |

第二条是通用文件操作，它不知道"作业文件夹"还有元信息要同步 ——
于是文件夹改了名，`homework.json` 里的名字还是旧的。

**修法是让 `_rename_item` 先判断"这是不是一个作业"**：

```python
if item.is_dir:
    existing = hw.load(item.path)
    if existing is not None:
        moved = hw.rename(existing, new_name)   # 走作业自己的改名
        ...
```

顺手也把菜单文案改了 —— 让用户知道点下去会改哪些东西：

```
重命名作业…（同时改文件夹与作业信息）
```

> **教训三：同一个"动作"有两个入口时，它们必须走同一个实现。**
>
> 界面上看起来都是"改名"，但一个走作业逻辑、一个走通用文件逻辑。
> 用户不可能知道这个区别，他只会说"改名不好使"。
>
> 判断方法：搜**那个行为的实现函数**（这里是"谁来动 homework.json"），
> 而不是搜按钮文案。

### 43.7 复盘

| 类别 | 内容 |
| --- | --- |
| 症状一 | 文件夹名没变 → 右键「重命名…」走的是通用文件改名，不同步元信息 |
| 症状一修法 | `_rename_item` 对作业目录改走 `hw.rename()`；菜单文案写明 |
| 症状二 | 闪退（窗口突然消失，日志无痕迹） |
| 症状二根因 | Qt 在"QThread 还在跑时被析构"会 `qFatal` **直接中止进程**（0xC0000409） |
| 为什么没防住 | 只在 `closeEvent` 里 `wait(3000)` 了一个线程，而预扫描要 20+ 秒、共有 5 个线程类 |
| 修法 | 新增 `core/threads.py`：登记 + 退出时**先脱钩再等待**（分两轮） |
| 关键顺序 | `setParent(None)` 必须**在** `wait()` 之前（实测：反了仍然崩） |
| 顺带补 | 全局异常钩子（`pythonw` 没有 stderr）+ Windows 本地崩溃转储 |
| 新增测试 | 21 条 |
| 学到的 | ①日志全无 = 原生崩溃，去查事件日志；②复现比读代码值钱；<br>③"每个资源都要记得释放"一定会漏；④同一动作两个入口必须同一个实现 |

**这一章最值钱的三条**：

> **一、"闪退且日志里什么都没有"，这个组合本身就是诊断结论。**
>
> Python 异常一定会留痕。什么都没有 + 进程消失，
> 只可能是**原生层硬崩溃**（Qt/C 库/驱动）。
> 这时候正确的工具是 **Windows 事件日志**：
> 它会告诉你崩溃模块（这里是 `Qt6Core.dll`）和异常代码（`0xC0000409`）。
>
> 我差点被自己测试脚本的崩溃码带偏 —— 直到把
> "用户的 `pythonw.exe`" 和"我的 `python.exe`"分开看，才看清真正的证据。

> **二、先做出一个"必定复现"的最小例子，再动手改。**
>
> 硬崩溃最难的是没法调试。但一旦能用十行代码复现，
> 它就变成一个普通的 bug：改一次、跑一次、看退出码。
>
> 我验证"必须先脱钩再等待"这件事，就是靠反复跑那个十行脚本
> 对比退出码 —— 而不是靠推理。

> **三、凡是"每个地方都要记得做某件事"的设计，都一定会漏。**
>
> 原代码是"在 `closeEvent` 里记得 `wait` 那个线程"。
> 它其实**做对了**，只是：等的时间不够、覆盖的线程不全。
> 这种设计的问题不在于写得对不对，而在于**它无法规模化** ——
> 每加一个线程就多一个可能漏的地方，而漏掉的代价是随机闪退。
>
> 改成"线程自己登记 + 退出统一处理"之后，
> **新的线程只要登记一次就自动被保护**。

---

## 第 44 章　后台监听文件变化，同时把 CPU 压到 0.16%

需求：

> 软件后台要不断扫描user data文件夹，更新文件变动，但不要耗费cpu太多性能

这一章讲一件"看起来简单、做起来全是取舍"的事。
**需求里那两句话是互相拉扯的** —— "不断扫描"要花 CPU，"别耗太多"要省 CPU。
所以整章的核心就是：**把"扫描"这件事变成几乎免费的**。

### 44.1 先量，再设计

我没有直接写代码，而是先测了三件事（本机真实数据）：

```
  数据规模: 7 科目, 38 文件, 38 目录
  完整重扫一次:      26.1 ms      ← 会重新解析每个书目的元信息
  只读 mtime 快照:   10.8 ms      ← rglob + Path.stat
  只读顶层目录 mtime: 0.59 ms
```

于是定下策略：

> **每次 tick 只做最便宜的事（拿 mtime 快照并比较）；
> 只有真的变了，才去做昂贵的事（让缓存失效 + 重建界面）。**

26 ms 的那一步绝不能每 5 秒做一次 —— 没有任何变化时它做的全是白工，
纯烧 CPU。

### 44.2 决定性的一次对比：rglob vs scandir

假数据下再看一遍，我才发现真正的瓶颈不在"扫几次"，而在**怎么扫**：

```
  假数据规模: 5100 项
  rglob+stat       243.19 ms  -> 每 5 秒约占 4.86% 单核   ← 不可接受
  os.scandir        10.39 ms  -> 每 5 秒约占 0.21% 单核   ← 可以长期开着
```

**差 23 倍。** 原因在 Windows 上很清楚：

* ``Path.stat()`` 每次都要**向文件系统问一遍**；
* ``os.scandir`` 返回的 ``DirEntry`` 里**已经带了**从目录项读到的信息，
  ``entry.stat()`` 直接用它，**不再发起系统调用**。

> **教训一："省 CPU"往往不是"少做几次"，而是"每次做得更便宜"。**
>
> 我本来打算靠"把间隔从 5 秒调成 30 秒"来省 CPU —— 那是拿
> **响应速度**去换 CPU。换成 `scandir` 之后，
> **同样的 5 秒间隔，开销降到 1/23**，响应速度一点没损失。
>
> 所以在调参数之前，先问一句：**这件事本身有没有更便宜的等价做法？**

### 44.3 两个"差点搞错"的细节

#### 一、目录自己的 mtime 该不该算进快照

第一版我把**根目录自己也**放进了快照。结果一条测试挂了：

```
[FAIL] 同样的目录，两次快照一致（这是'没变化'的判据）
```

因为根目录的 mtime 会随子项增删变化，而我并不读它的**内容**。
更要紧的是：**"新增一个文件再删掉"会让目录 mtime 永远回不到原值**
（NTFS 每次目录项增删都推进它），于是快照永远判"有变化"。

处置分两半：

* **根目录自己不收录**（它的变化必然伴随子项变化，不会漏）；
* **子目录的 mtime 保留**（目录 mtime 变了确实意味着结构改动，
  多刷新一次界面是良性的）。

我一开始想把"子目录 mtime"也去掉，但那样就**漏掉了重命名/移动**这类
"内容没变、位置变了"的改动。所以保留。

> **教训二：测试挂了先分清"代码错"还是"断言的预期错"。**
>
> 这两条断言我第一版都写错了（把目录数量写成 3，实际是 4；
> 以为"加了再删"会回到原值）。**代码是对的，错的是我的预期。**
> 如果我当时去"修代码"，就会把正确的行为改坏。
>
> 判断方法：**看这条断言描述的规律是不是真的成立**。
> "加了再删，目录 mtime 不变" —— 这条规律本身就不成立，
> 那它就是一条错误的断言，与代码无关。

#### 二、防抖：连续两次一致才认账

本软件自己保存笔记、生成总结也会改文件时间。
如果一发现不同就通知界面，可能正好抓到"写到一半"的中间状态 ——
界面闪一下再变回来。所以要求**连续两次看到同一个新状态**才认账。

这里我写错了一版：

```python
if self._pending is None or current != self._pending:
    self._pending = current
    return False
```

看起来对，但它把"第一次看到不同"和"又变了"合并成一条 ——
于是**待确认值已经是最新时，仍然拿它跟旧基线比**，
结果永远判成"还在变"，一条通知都发不出来。

修法是把三种情况分开：

```python
if current == self._baseline:      # 与已认账状态一致 -> 无变化
    self._pending = None
    return False
if self._pending is None:          # 第一次看到不同 -> 记下，等确认
    self._pending = current
    return False
if current != self._pending:       # 又变了（还在写）-> 更新，继续等
    self._pending = current
    return False
# 连续两次看到同一个新状态 -> 认账
```

还有一件事值得记：这个防抖的断言我一开始写成
**"正好第 2 次认账"**，结果在同一个进程里跑三轮会随机挂两轮。
打出来才发现：有时需要第 3 次 —— 文件系统对同一目录的可见性有极短的延迟，
某一轮快照可能还没看到新文件。

改成"**最多驱动 N 次，看它在第几次认账**"之后，断言就稳了。
这不是放松要求 —— 防抖本来就没规定"必须第 2 次"，
它规定的是"**状态稳定之后才认账**"。

### 44.4 看不见就不扫（省 CPU 最狠的一刀）

前面两条是"做得便宜"，这一条是**真的不做**：

* 窗口隐藏到后台（"关闭到后台"功能）-> 定时器 `stop()`
* 最小化 -> 同样 `stop()`
* 恢复显示 -> `start()`，并立刻补扫一次

实测效果：**隐藏时占用 0%**，而恢复后不会漏掉隐藏期间的改动
（因为基准快照**刻意不清**，一恢复就发现和基准不同）。

**用 Qt 事件而不是手动在每个调用点补调用**：

```python
def showEvent(self, event): ...   # 显示
def hideEvent(self, event): ...   # 隐藏
def changeEvent(self, event): ... # 最小化/还原
```

> **教训三：这个"别在每个调用点记得做同一件事"的教训，
> 上一章（线程）刚踩过一次。**
>
> 上章是"每个线程都要记得等"，这章是"每个隐藏入口都要记得停"。
> 同一个坑换了个地方出现 —— 而解法也一样：
> **挂到一个必然会经过的钩子上**（Qt 事件 / 登记表），
> 而不是散在调用点。

### 44.5 一个"我差点写成固定次数"的地方

防抖一开始我写的是"**连续两次看到同一个新状态就认账**"。逻辑没错，
但**实测发现一个很小的改动也要 10~14 秒才被发现** —— 因为"两次一致"
等于把间隔翻倍，而且偶尔还要第三次（文件系统对同一目录的可见性有极短延迟）。

于是改成**固定的时间窗口**：新状态稳定 ``间隔 × 2`` 秒之后才认账。
这个改动带来两个好处：

* 间隔可以取到 **2 秒**（原来是 5 秒），改动最多约 6 秒可见；
* 断言不再写"正好第几次"，而是"**最多驱动 N 次，看它第几次认账**"，
  于是随机失败消失了。

> **"等够时间"比"看够次数"更稳。** 次数取决于轮询频率和调度抖动，
> 时间才是用户真正感受到的那个量。

### 44.6 结果

```
  间隔 5 秒:  20 秒内 CPU 增量 31 ms  -> 单核 0.16%
  间隔 2 秒:  20 秒内 CPU 增量 109 ms -> 单核 0.55%（整机 0.017%）
```

日志里能直接看到它的工作痕迹：

```
[INFO] gwp.ui.data_watcher: 已开始监听数据目录变化（每 5000 ms 一次）：...
[INFO] gwp.ui.data_watcher: 数据目录有变化：新增/改动 4 项，消失 0 项（例如 ...）
[INFO] gwp.ui.main_window: 检测到数据目录变化，刷新界面（+4 / -0）
```

端到端也验过：外部新建一个科目目录 -> 界面自动刷新、
缓存里立刻能看到它 -> 隐藏后停止扫描 -> 显示后恢复 -> 退出码 0。

### 44.7 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 后台不断扫描 user data，但别耗 CPU（两句话互相拉扯） |
| 先做的事 | **测成本**：完整重扫 26 ms、mtime 快照 10.8 ms |
| 决定性能的一步 | `os.scandir` 替 `rglob`：5000 项 **243 ms → 10.4 ms（23×）** |
| 分层策略 | 每 tick 只做便宜的快照比较；只有真变化才重建界面 |
| 防抖 | 连续两次看到同一个新状态才认账（过滤"写到一半"） |
| 省 CPU 最狠的一刀 | 隐藏/最小化时**完全停掉**；用 Qt 事件挂钩子，漏不掉 |
| 实测结果 | 间隔 2 秒时空闲 0.55% 单核（整机 0.017%）；隐藏时 0% |
| 测试坑 | 两条断言把预期写错了（目录数算错、"加了再删"不会回到原值） |
| 学到的 | ①省 CPU 先想"更便宜的等价做法"再想"少做几次"；<br>②测试挂了先分清代码错还是预期错；③同一类坑会换地方重现 |

**这一章最值钱的三条**：

> **一、"省 CPU"往往不是"少做几次"，而是"每次做得更便宜"。**
>
> 我本来的方案是"把间隔从 5 秒调成 30 秒" —— 那是拿响应速度换 CPU。
> 换成 `scandir` 之后，**同样的 5 秒间隔，开销降到 1/23**，
> 响应速度一点没损失。
>
> 调参数之前先问：**这件事有没有更便宜的等价做法？**

> **二、测试失败时，先分清"代码错"还是"断言的预期错"。**
>
> 我这一章挂的两条断言，**代码都是对的**：
> 一条把目录数量算错了（3 vs 4），
> 一条假定"新增再删除"能让目录 mtime 回到原值（NTFS 上不成立）。
>
> 如果我直接去"修代码"，就会把两处正确的行为改坏。
> 判断方法：**看断言描述的那条规律本身是否真的成立。**

> **三、同一个"别在每个调用点记得做同一件事"的坑，会换着地方重现。**
>
> 上一章（线程退出）是"每个线程都要记得等"，
> 这一章（省 CPU）是"每个隐藏入口都要记得停"。
>
> 解法是同一个：**挂到一个必然会经过的钩子上**
> （Qt 事件、全局登记表），而不是散在各处调用点。
> 认出"这又是那类坑"能省掉一整轮返工。

---

## 第 45 章　技术路线变更：从"AI 写文档"到"合并成一个 PDF"

用户用了几天之后做了个决定：

> 由于AI生成功能持续不理想，现在改变技术路线：AI总结实现方法：
> 将所有待总结文件转化并合并为一个pdf文档，
> 结束后删除中间可能产生的废弃文档和数据
>
> （补充）生成结束后，我的本地只是多了一个独立的 summary 的 pdf 文档，
> 其他的所有只要是之前没有的都删
> 不再生成md文档，旧的md之间删掉

**这一章的核心不是"怎么写 PDF"，而是"怎么把一件事做减法"。**
前面几章一直在给这个功能加东西（分流、公式、混排、提示）；
这一章把它砍回一件事：**把文件合并成一个 PDF，别留下别的。**

### 45.1 先想清楚"不留中间物"该怎么保证

需求里最容易被忽略的一句是"结束后删除中间可能产生的废弃文档和数据"。

最直觉的做法是：**生成，然后删掉生成过程中产生的东西。**

我一开始就是这么想的，然后立刻意识到这条路有问题：
**"记得删什么"是一份清单，而清单一定会漏。**
这个项目已经因为"每个调用点都要记得做某件事"栽过两次
（第 43 章的线程、第 44 章的隐藏入口）。

所以换成一个**结构上**就不会漏的做法：

```
1. 所有页面图片、公式图片 -> 放进一个本次专用的临时目录
2. 全部内容 -> 先写进一个临时 PDF（*.building.pdf）
3. 只有全部成功，才把临时 PDF 替换到目标位置
4. finally: 整个临时目录删掉、临时 PDF 删掉
```

关键是这三点的组合效果：

* 中途失败 → 临时 PDF 被删，**目标文件一个字节都没动过**
  （所以根本不需要"回滚"这件事）；
* 成功 → 中间物随临时目录一起消失；
* 无论成败 → `finally` 都跑。

> **教训一：把"记得清理"换成"清理是结构的必然结果"。**
>
> 差别在于：前者要维护一份"什么算中间物"的清单，
> 后者只需要保证"所有中间物都写在同一个会被删掉的目录里"。
> 后者不会漏 —— 因为**没有地方可漏**。

### 45.2 一个"看起来对"但会留下垃圾的写法

"合并 PDF"最自然的实现是**追加到已存在的 PDF**：

```python
with fitz.open(target) as out, fitz.open(new_pdf) as src:
    out.insert_pdf(src)              # 把新内容插进去
    out.save(target, incremental=True)
```

需求里说"删除中间可能产生的废弃文档" —— 我一开始以为这指的是
"生成失败时要把刚插进去的页删掉"。于是测了一下删页：

```
初始:          2 页, 1133 字节
追加 2 页后:   4 页, 2175 字节
删除那 2 页后: 2 页, 2427 字节   ← 页数对了，体积反而更大了
```

**页删掉了，数据没删掉。** 增量保存只是"把改动追加到文件尾部"，
旧内容仍然在文件里 —— 于是文件越用越大，而且**里面留着本该删掉的内容**。

改用"另存到临时文件 + `garbage=4` + 原子替换"之后：

```
另存法: 原始 1133 -> 追加后 2018 -> 删页后 1120 字节   OK 回收干净
对照组（不带 garbage）: 原 786 -> 删后 1884 字节        X 反而更大
```

**但更有价值的结论是：用了"临时文件 + 原子替换"之后，
根本不需要"删页回滚"这件事了** ——
失败时直接把临时文件丢掉，目标从头到尾没被碰过。

> **教训二：换一种实现方式，可能让一整类问题消失，而不是被解决。**
>
> "怎么安全地回滚"这个问题，在"就地修改"的方案里必须回答；
> 在"构建到临时文件再替换"的方案里**根本不存在**。
>
> 遇到需要小心翼翼维护状态的地方，先问一句：
> **能不能换个做法，让这个状态不必存在？**

### 45.3 目标文件被占用：一个必须处理的真实情况

替换那一步第一次跑就报错了：

```
PermissionError: [WinError 5] 拒绝访问
  '...数学分析上_summary.pdf.building.pdf' -> '...数学分析上_summary.pdf'
```

原因是**目标 PDF 正被占用**：生成后软件会按配置**自动打开**它，
系统阅读器就一直占着这个文件。

处理方式分两层：

* **重试**：占用常常只持续几百毫秒（阅读器刚在读盘）；
  每轮先试 `os.replace`，再试"先删目标再改名"
  （有些阅读器允许删除、不允许覆盖），一共试 6 轮；
* **明确报错**：实在替换不了就说清"请先关闭正在打开它的阅读器"，
  并强调**原始文件没有被改动** —— 用户需要知道自己的数据是安全的。

> 顺带一提：这次的报错信息里我特意加了"（原始文件没有被改动。）"
> ——**失败时告诉用户"你的东西还在"，比告诉他"失败了"重要得多。**

### 45.4 减法的连带工作

产物从 Markdown 变成 PDF，接口上牵动了一圈。值得记的是**哪些地方必须一起改**：

| 位置 | 为什么必须改 |
| --- | --- |
| `constants.SUMMARY_PDF_SUFFIX` | 新增后缀，而不是复用 `_summary.md` + `.pdf` —— 后者会拼出 `xxx_summary.md.pdf`（实测踩过） |
| `store.find_summary` | 要**优先**认 PDF；同一本书以前是 md、现在是 PDF 时，界面该显示新的 |
| `store` 的书目改名 | 总结文件跟着改名时，要按**实际那个**后缀改（一律改成 md 会让 PDF 变成孤儿） |
| 界面按钮与提示 | 产物变了，文案必须跟上，否则用户找不到东西 |

那个 `xxx_summary.md.pdf` 的 bug 很典型：

```python
return Path(book.path) / f"{book.name}{C.SUMMARY_SUFFIX}.pdf"   # 错
return Path(book.path) / f"{book.name}{C.SUMMARY_PDF_SUFFIX}"   # 对
```

因为 `SUMMARY_SUFFIX` 本身**带着 `.md`**。名字里带扩展名的常量，
和"再拼一个扩展名"是冲突的。

> **教训三：后缀常量只该有一处定义，而且不该"再拼一次"。**

### 45.5 顺手清掉了旧路线留下的垃圾

新流程不再往 `else data/equations` 写公式图片了，
但那个目录还留着**之前**生成的 183 个 PNG（约 900 KB）。

严格按"只要是之前没有的都删"来说，它是"之前**有**的"，
似乎不该删。但它的**生产者已经不存在了**（旧流程已删除），
留着只会让人以为新流程还在用它。所以我删掉了，
并在说明里写明"新流程不再使用这个目录"。

**这类判断没有标准答案，关键是说清楚为什么。**
我把理由写在文档里，而不是默默删掉 —— 用户有权知道什么东西被动过。

### 45.6 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 产物改成**一个合并 PDF**；中间物全删；不再生成 md 并删掉旧的 |
| 关键设计 | **临时目录 + 临时 PDF + 原子替换 + finally 清理** -> 不留中间物是结构必然 |
| 排除的方案 | 增量追加到目标 PDF：删页后体积反而变大（数据没回收），且需要回滚逻辑 |
| 真实坑一 | `SUMMARY_SUFFIX` 自带 `.md`，再拼 `.pdf` 得到 `xxx_summary.md.pdf` |
| 真实坑二 | 目标被阅读器占用（WinError 5 / 32）-> 重试 + 明确报错 + 声明原文件安全 |
| 连带修改 | 新增 PDF 后缀、store 优先认 PDF、改名按实际后缀、界面文案 |
| 新增测试 | 22 条（含"书目目录里只多出 summary.pdf"这类结构断言） |
| 学到的 | 把"记得清理"变成"结构必然"；换实现方式能让一整类问题消失；<br>失败时要告诉用户"你的数据还在" |

**这一章最值钱的三条**：

> **一、把"记得清理"换成"清理是结构的必然结果"。**
>
> 生成到临时目录、成功才替换、finally 一律删除 ——
> 这样"不留中间物"不需要任何清单。有清单就会漏，没清单就没得漏。

> **二、换一种实现方式，可能让一整类问题消失。**
>
> "怎么安全回滚"在就地修改的方案里是个必须回答的难题；
> 在"构建到临时文件"的方案里连问题都不存在。
> 遇到需要小心维护状态的地方，先问：**能不能换个做法让这个状态不必存在？**

> **三、失败时要告诉用户"你的数据还在"。**
>
> 报错信息里加一句"原始文件没有被改动"，成本几乎为零，
> 但它决定了用户是"有点烦但放心"还是"慌了，我的东西是不是没了"。

---

## 第 46 章　「长庚知道」：让 AI 只写它该写的那一小段

新需求（很短，但信息量不小）：

> 小改进：生成AI总结时，可以在文档最后加入一些关于知识点的你的补充
> （标记 "长庚知道" 在页面左上角）

上一章刚把 AI 从主流程里拿出来（总结正文=用户资料，AI 只排页序）。
这一章又要让 AI 写字 —— 但**只在最后加一小段补充**。

关键就在于：**怎么让"AI 写字"这件事不把上一章的成果毁掉。**

### 46.1 边界比功能重要

用户说的是"补充"。但"补充"和"重写"之间的界线，模型自己是分不清的
—— 你只要给它内容，它很乐意把整本书复述一遍。

所以提示词里花最多篇幅的不是"写什么"，而是**"不要写什么"**：

```
# 只写"补充"，不要复述
* **不要**重复资料里已经写过的内容 —— 复述一遍没有任何价值；
* 只写下面这几类：
  1. 概念辨析 / 2. 常见误区 / 3. 知识联系 / 4. 延伸
```

还有一个容易漏的点：**不能让它抢资料的位置**。
所以补充固定接在**所有资料页之后**，而且首页就写明
"以下内容由 AI 根据资料主题补充，**不属于你的原始资料**"。

> **教训一：给 AI 加功能时，"边界"比"能力"更值得写进提示词。**
>
> 用户的话里藏着一个约束（"补充"），但对模型来说那个约束几乎不存在
> —— 它不知道"资料页"是什么，也不知道自己不该替代它们。
> 把边界写成**硬性要求**，它才会守。

### 46.2 线索是从哪儿来的：一个顺手省掉的重复劳动

要写"补充"，至少得知道这本书讲什么。第一版我打算在补充模块里
重新提取一遍资料文字 —— 然后发现这是**纯浪费**：
转页面的时候（第 45 章）已经把文字读出来了。

于是给 `ChapterPlan` 加了一个字段：

```python
#: 提取到的正文（只留开头一小段就够）。
#: **为什么要存下来**：转页面时已经读过一次正文，
#: 生成「长庚知道」补充又要知道"这份资料讲什么"。
#: 不存的话同一个 PDF 会被**提取两次** —— 扫描件还好，
#: 几百页的文字版 PDF 就是白等一场。
hint_text: str = ""
```

**扫描件怎么办？** 它没有文字层，什么也提取不到。
答案是**用文件名**：

```python
def _fallback_hint(source: Path) -> str:
    return source.stem
```

这能用吗？能用。学生给资料命名通常就是章节名（"第二章 导数与微分.pdf"），
比什么都不给强得多。

> **教训二：兜底方案不一定要"完整"，够用就行，但必须存在。**
>
> 如果扫描件没有线索就让整个补充功能失败，那用户手里全是扫描件时
> 这个功能就等于不存在。用文件名兜一下，功能就能用 —— 质量差一点，
> 好过完全不可用。

### 46.3 盖章：需求说"左上角"，就得真的是左上角

需求明确说"标记 长庚知道 在页面左上角"。这句话有三种可能的理解：

* 页眉区（页边距之外）；
* 正文区左上角；
* 每个大标题旁边。

我选了**正文区左上角**（页宽的 10%、页高的 5.5% 左右）——
理由是页眉区可能被某些阅读器裁掉，而"页面左上角"最直白的理解
就是在纸面的左上部分。

盖章本身很简单：

```python
page.insert_text((x, baseline), LABEL, fontname="china-s",
                 fontsize=9.5, color=(0.55, 0.40, 0.12))
```

用 PyMuPDF 内置的 `china-s`（宋体）而不是自带字体文件 ——
**安装包里少一个字体文件，就少一份"用户机器上字体缺失"的可能。**

还有一个细节：光有一行字看起来像正文误入，所以底下加了一条细线，
让它读起来是个**栏目标记**。

### 46.4 一个"测试写得太脆"的教训

我给盖章写了断言，第一版是这样的：

```python
# 写一段很长的内容，期望它排成多页
render_supplement_pdf("# 一

" + "这是用来撑到多页的正文。" * 60 + ...)
check("每一页都带标记", 页数 >= 2 and 每页都命中)
```

结果那段内容**只排出 1 页**，断言就红了。

问题不在产品，而在**测试**：我让"内容够不够长"来决定"能不能测多页"，
这是把测试建立在一个我不控制的条件上。

改成直接造一个**确定有 5 页**的 PDF 去盖章：

```python
_mk = fitz.open()
for _i in range(5):
    _mk.new_page(width=595, height=842)
_mk.save(str(_multi)); _mk.close()
check("盖章会盖到每一页", _ks._stamp_label(_multi) == 5)
```

测的就是盖章本身，不再依赖排版结果。

> **教训三：测试要测"你要测的那个东西"，而不是它的副产品。**
>
> "内容够长 -> 排出多页 -> 每页有标记"看起来是在测盖章，
> 其实一大半在测排版。一旦排版行为变化（换个字号、换个模板），
> 断言就红，而盖章明明是对的。

### 46.5 一个藏了两轮的测试配置 bug

加完功能后 gui 测试开始报：

```
OSError: 目标 PDF 正被其它程序占用，替换失败：[WinError 32]
```

我一开始怀疑是新功能（补充分支）引入了句柄泄漏，查了半天：
先验证 `fitz.open` 读 PDF 会不会留句柄（**不会**，三种读法都能删），
再写隔离探针（**两次连续生成都成功**）。

最后在测试里插了个探针，发现**第二次生成之后文件就已经不可替换了** ——
跟补充功能无关。打印出占用者列表，看到一堆 `fastpdf`。

根因：这台机器上「生成总结」会按配置**自动打开** PDF，交给系统阅读器，
而阅读器**一直占着文件**。**测试里本该关掉这个配置，但那次补丁静默失败了**
（我用脚本改测试文件时，替换的字符串没匹配上，脚本却只打印"没找到"就过去了）。

产品行为是对的：替换不了就重试 6 轮，然后明确告诉用户
"请先关闭正在打开它的阅读器（原始文件没有被改动）"。
**要修的是测试**：把 `summary.auto_open_after_generate` 设为 `False`。

> **教训四：脚本改文件必须校验结果，不能只打印"没找到"就继续。**
>
> 这次的代价是我在错误的方向上查了很久。
> 后来我在这个项目的所有自动改写脚本里都加了一句
> `assert 替换后的内容 != 替换前` —— 静默失败比报错危险得多。

### 46.6 顺手修掉一个"公式根本没渲染"的老问题

把第一版补充内容渲染成图片检查时，我看到的不是公式，而是**一串 LaTeX 源码**：

```
证明 $\lim(a_n+b_n)=A+B$ 时，把两个不等式各取 $\varepsilon/2$ ...
```

原因是 `pdf_exporter._build_html` 里**没设 `equation_dir`**：

```python
render_options = RenderOptions(base_dir=..., theme=..., resolve_images=True)
# 少了这个 -> markdown_renderer 里的公式替换**整个没启用**
```

也就是说：**导出 PDF 这条路上，公式从来都是显示源码的** ——
不是这次新引入的 bug，而是一个一直存在、只是没人用带公式的文档导出过的问题。
（补一句：软件里的 Markdown 预览是有公式图片的，所以问题只藏在这条路上。）

修法是在导出器里先把公式换成图片、再内联成 data URI：

```python
equation_dir = _prepare_equation_dir(options)   # 临时目录
render_options.equation_dir = equation_dir
...
body = _embed_images(body, options.base_dir)    # 图片内联进 HTML
```

**关键细节：用完要删。** 公式图片只在排版期间有用，
所以 `finally` 里清掉那个目录 —— 而且**只在"目录是我们自己建的"时才删**：

```python
if equation_dir_owned:          # 调用方指定了 equation_dir 就不能动
    _discard_equation_dir(Path(output_path))
```

「长庚知道」那边就是显式指定 `equation_dir` 的调用方（它把公式和补充 PDF
放在同一个工作目录里，由第 45 章那套 `finally` 统一清理）。
如果导出器无脑删，就会把别人的目录删掉。

> **教训五：修一个 bug 时，先问"这个 bug 的形状说明什么"。**
>
> 公式显示成源码，说明"公式 → 图片"这一步在**这条渲染路径上不存在**。
> 那么只要有人在这条路上渲染任何带公式的东西，都会看到源码 ——
> 这不是"补充功能的问题"，而是"导出路径缺了一步"。
> 在**正确的那一层**修（导出器），所有走这条路的场景一起被修好。

### 46.7 一个还没解决的问题：公式图片偏小

修完之后公式**内容是对的**（分式、上下标、ε 都对），但**尺寸偏小** ——
`equation_size=15` 这个值配上 PDF 的页面比例，看起来像"脚注里的公式"。

我没有顺手改大它，原因是：这个值同时用在 Markdown 预览里，
改它会影响所有地方；而"多大才算合适"是**需要看实际效果**才能定的，
不该由我拍一个数字。所以这里如实记下来，交给用户决定。

> **教训六：能修的和该由用户决定的，要分开。**
>
> "公式根本不该显示成源码"是明确的 bug，该修；
> "公式应该多大"是偏好，改了会影响别处。**把后者留给用户**，
> 比自作主张改成另一个数字更有价值。

### 46.8 复盘


| 类别 | 内容 |
| --- | --- |
| 需求 | 文末加知识点补充；标记「长庚知道」在页面左上角 |
| 边界设计 | 只补充不复述；固定在最后；首页声明是 AI 写的；失败不致命 |
| 关键实现 | 线索复用 `ChapterPlan.hint_text`（省一次提取）；扫描件用文件名兜底 |
| 排版 | 复用 Markdown → PDF 导出器；`china-s` 内置字体盖章 + 细底线 |
| 真实坑一 | 测试靠"内容够长"来保证多页 -> 改成直接造 5 页 PDF 测盖章 |
| 真实坑二 | 导出 PDF 时公式一直显示 LaTeX 源码（既有缺陷，在导出器那一层修好） |
| 真实坑三 | 测试漏设 `auto_open=False`，被系统阅读器占住文件 -> 重试 6 轮后报错 |
| 新增测试 | 20 条（线索构造、优雅跳过、盖章覆盖每页、左上角位置、只增不减） |
| 学到的 | 给 AI 加功能要写"不要做什么"；兜底方案要存在；<br>测试要测本体而不是副产品；脚本改文件必须校验 |

**这一章最值钱的三条**：

> **一、给 AI 加功能时，"边界"比"能力"更值得写进提示词。**
>
> 用户说"补充"，模型不知道"补充"意味着"别替代原文"。
> 把边界写成硬性要求（不要重复、不要客套、看不见的宁可不说），它才会守。

> **二、兜底方案不一定要"完整"，够用就行，但必须存在。**
>
> 扫描件没有文字层，用文件名当线索质量不高 —— 但如果没有这个兜底，
> 用户手里全是扫描件时功能就等于不存在。

> **三、测试要测"你要测的那个东西"，而且脚本改文件必须校验结果。**
>
> 我这一章踩的两个坑都不是产品 bug：一个是让测试依赖了不受控的条件，
> 一个是自动改写脚本静默失败导致我在错的方向上查了很久。

---

## 第 47 章　同一个错误犯两次之后：把保护放到解释器那一层

这一章记的是一段"我搞砸了两次"的经历。它不在功能清单里，
但这个项目后面每一次改动都会用到它的成果。

### 47.1 两次都是同一件事

做端到端验证时，我两次改到了用户**真实的**数据：

**第一次**：我写了个探针脚本，把用户真实书目的目录复制进沙箱，
然后调用「生成总结」。问题是 —— 我随后传进 `_build_summary` 的是
**真实的 Book 对象**（`book.path` 指向真实目录），
于是用户真实的 summary 被就地重写了。

**第二次**（两天后，同一天里第二次）：换了个写法，看起来更稳妥 ——

```python
cfg = Config.load(sandbox / "code" / "else data" / "config.json", force=True)
cfg.set("paths.data_root", str(sandbox / "data"))
```

我以为这样就隔离了。但 `Config.load(..., force=True)` 里，
**如果沙箱里那份配置还不存在，它会去载入真实的那份**，
而真实配置里的 `paths.data_root` 就指向真实数据目录。
我设的那一行确实执行了 —— 但读取它的是另一个对象，
整个脚本其实一直在操作**真实数据**。

两次都靠"生成前自动备份"救回来了（这个设计在第 45 章之前就有了），
两次我都从备份里恢复了用户的文件。

但两次事故说明的**不是**"我不够小心"，而是：

> **"每写一处都记得检查"这种保护，靠不住。**
>
> 我确实检查过。第一次之后我甚至专门加了一道检查
> （写在 `book_view._build_summary` 里，检查目标路径是否在沙箱内）。
> 然后第二次绕过去了 —— 因为脚本根本**没走那条路**。

### 47.2 换一层：让解释器自己拒绝

第 45 章学到的是"把记得清理换成结构必然"。这里是同一个道理：

> **不要在任何一条业务路径上加检查，要放在所有路径都必须经过的地方。**

Python 有一个几乎没人用的机制正好合适：`sys.addaudithook`。

```python
import sys

def _hook(event, args):
    if event not in {"open", "os.replace", "os.remove", "os.rename", ...}:
        return
    path = args[0]
    if not _is_allowed(path, allowed_roots):
        raise PermissionError(...)

sys.addaudithook(_hook)
```

它会在**每一次**文件写入时被调用 —— 不管是哪个模块、
哪条代码路径、谁写的代码、甚至第三方库。于是"忘记检查"这件事
在这个结构里**不可能发生**。

完整的实现在 `gwp/core/write_guard.py`，规则很短：

| 条件 | 行为 |
| --- | --- |
| 没有 `GWP_ROOT` 也没有哨兵文件 | **完全不启用**（正常使用零影响） |
| 目标在 `GWP_ROOT` 之下 | 允许 |
| 目标在系统临时目录之下 | 允许（测试大量用 `tempfile`） |
| 其它任何位置 | **拒绝并抛异常** |
| 设了 `GWP_ALLOW_REAL_WRITE=1` | 放行（开发调试用，必须显式） |

### 47.3 几个必须踩对的细节

**一、只拦"写"，不拦"读"。** 审计钩子对 `open` 事件也会触发，
所以必须检查 mode：

```python
if event == "open":
    path_text, mode = args[0], args[1]
    if not any(ch in mode for ch in "wax+"):
        return          # 只读不算
```

不这么做的话，测试连自己的代码都 import 不了。

**二、系统临时目录必须放行。** 测试大量用 `tempfile`，
而且 Windows 上 temp 往往不在 `GWP_ROOT` 之下。
第一版我漏了这条，测试立刻全线报错。

**三、钩子装上就卸不掉。** `sys.addaudithook` 没有对应的 remove。
所以我的**测试**里不能在主进程装它 —— 那一节必须起**子进程**：

```python
_proc = subprocess.run([sys.executable, "-c", _guard_script], ...)
```

**四、安装时机要最早。** 我把 `install_test_write_guard()`
放在 `bootstrap()` 的**第一行**，在所有磁盘操作之前 ——
一旦开始读配置、建目录，就已经有写入可能了。

**五、测试自己也会犯"用错的路径当外面"的错。** 我第一版断言是这样写的：

```python
outside = Path(tempfile.mkdtemp(prefix="gwp_outside_")) / "x.md"
```

结果断言显示 `outside=allowed`，看起来像保护失效 ——
其实是**temp 本身就在允许列表里**，拿它当"外面"根本测不出东西。
改成用**真实数据目录**当"外面"，才真的在测这件事。

> **教训一：测"保护有没有生效"，必须用真的应该被拦住的目标。**
>
> 用一个"本来就被允许"的路径去测"有没有被拦住"，
> 永远不会失败，也永远不会证明任何事。

### 47.4 复盘

| 类别 | 内容 |
| --- | --- |
| 事故 | 两次端到端验证改到用户真实书目数据（都从自动备份恢复） |
| 第一次根因 | 误用真实 Book 对象（目标路径检查在业务层，绕得过去） |
| 第二次根因 | `Config.load(force=True)` 回退到真实配置，`data_root` 指向真实目录 |
| 修法 | `sys.addaudithook` 拦所有写操作；装在最优先位置 |
| 规则 | 无 `GWP_ROOT` -> 不启用；沙箱内/系统 temp -> 允许；其余 -> 拒绝 |
| 调试出口 | `GWP_ALLOW_REAL_WRITE=1`（必须显式） |
| 测试 | 在**子进程**里验证（钩子卸不掉）；用真实数据目录当"外面" |
| 新增测试 | 9 条 |
| 学到的 | ①一个错误犯两次说明修的位置不对；②把保护放到所有路径都经过的那一层；<br>③测保护必须用真的该被拦的目标 |

**这一章最值钱的三条**：

> **一、同一个错误犯两次，说明你上一次修错了地方。**
>
> 第一次之后我加了一道检查，第二次绕过去了。这不是"不够小心"，
> 而是那道检查装在了**某一条路**上，而问题出在"路可以绕"。
> 正确的问法是：**有没有一个地方，所有路径都必须经过？**

> **二、保护要装在"绕不过去"的那一层。**
>
> `sys.addaudithook` 之所以合适，不是因为它强大，而是因为
> **没有任何正常代码能绕过它**。这跟第 45 章的"临时目录 + finally"
> 是同一种思路：不靠纪律，靠结构。

> **三、测保护时，必须用真的应该被拦住的目标。**
>
> 我拿临时目录当"沙箱外"，断言就永远通过、也永远证明不了什么。
> 一条不会失败的测试，等于没有测试。

---

## 第 48 章　「取消颜色标记」和「还是要染色」：先把规则说清，再动手

这是个小需求，但里面有一个值得记下来的沟通问题：

> 已完成的作业取消颜色标记 用绿色字体标已完成
> 未完成的作业用红色字体标未完成

（我照做之后）

> 但是未完成 快到DDL的还是要染色

### 48.1 我第一版做过头了

第一版我的理解是：「**取消颜色标记**」 = 取消整行底色，
完成状态**只用字体颜色**表达。于是：

* 已完成 -> 绿色字、无底色；
* 未完成 -> 红色字、**无底色**。

看起来完全照做了。但用户的第二句话点出问题：**「快到 DDL 的还是要染色」** ——
我以为「取消颜色标记」是在否定**所有**底色，其实它否定的是
**「已完成」那一类的底色**。

两条需求合起来，真正的规则是：

> **只有「未完成」才染色。** 已完成的一律没底色。

### 48.2 为什么这个规则更合理

想清楚之后会发现它不只是「用户这么说的」，它本身有道理：

**底色的唯一作用是催办。** 交完就不需要催了。

已完成的作业如果还挂着浅红底，会让人以为「这条还没处理」 ——
底色从「提醒」变成了「噪音」。这就是为什么用户会先说
「已完成的取消颜色标记」。

而「未完成 + 快到 DDL」必须染色，因为那正是**唯一需要你动手**的那一类。

顺带理清两个容易混的概念：

| | 说的是什么 | 表现 |
| --- | --- | --- |
| **完成状态** | 「你交了没有」 | 名字的**字色**（绿 / 红） |
| **DDL 紧急度** | 「期限本身怎么样」 | DDL 格的文字 + **整行底色**（未完成时） |

两件事会重合（比如「未完成 + 已过期」是红字 + 浅红底），
但它们不是一件事：**已完成的作业也可能过期**（迟交），
那时应该是绿字、无底色、DDL 格写「已过期」。

> **教训一：用户说「取消 X」时，问清楚取消的是「全部」还是「某一类」。**
>
> 「已完成的作业取消颜色标记」这句话里，「已完成的」是限定语还是场景说明？
> 我按「取消所有底色」理解，就多做了一半。**先按字面做最小改动，
> 然后请用户确认范围**，比一次做过头更省事 ——
> 做过头了用户还得再提一次需求（这次就是）。

### 48.3 实现：一条判断，别写成两处

改动很小，就一个条件：

```python
if not is_done:                 # 只有未完成才染
    brush = None
    if state == "overdue":
        brush = _OVERDUE_BRUSH
    elif state == "soon":
        brush = _SOON_BRUSH
    if brush is not None:
        for column in range(self.columnCount()):
            ...                      # 整行刷底色
```

**判断只写一处**（`not is_done`），而不是在「已完成」和「未完成」
两个分支里各写一遍 —— 后者早晚会出现「改了一个忘了另一个」。

### 48.4 测试里两个自己踩的小坑

**坑一：名称格现在是「名字（未完成）」，按名字找行就找不到了。**

原来的测试：

```python
rows = {table.item(r, 0).text(): r for r in range(table.rowCount())}
check("三个作业都在列表里", {"已过期作业", ...} <= set(rows))
```

名称格里加了状态之后，键变成了 `"已过期作业（未完成）"`，
`set` 包含判断直接失败（报错信息里能看到那串带括号的名字，
一眼就明白是键变了，不是功能坏了）。改成按前缀找：

```python
def _find_row(name):
    for r in range(table.rowCount()):
        cell = table.item(r, 0)
        if cell is not None and cell.text().startswith(name):
            return r
    return None
```

**坑二：判断「有没有底色」不能用 `background().color()`。**

我第一版这么写：

```python
bg = table.item(r, 0).background().color().name().upper()
if bg == "#FFFFFF":        # 以为没底色就是白色
```

结果**所有行都显示 `#000000`** —— 因为没设过底色时 Qt 返回的是
`NoBrush`，它的颜色是默认的黑色，跟「白色底」完全不是一回事。
正确的判断是看**画刷样式**：

```python
painted = int(brush.style().value) != 0     # NoBrush == 0
```

我因为这个错误判断，一度以为「染色全都没生效」，
其实界面上一切正常（表里明明有 `#FFF4D6` / `#FFE1E1`）。
**是断言错了，不是代码错了。**

> **教训二：断言读到的值不符合预期时，先确认「我读对了吗」。**
>
> `background().color()` 读出来是 `#000000`，我的第一反应是「底色没设上」。
> 实际上「没设底色」在 Qt 里的表示是 `NoBrush` —— 一个**样式**，
> 不是一个颜色。读错属性会造出一个不存在的 bug，然后花时间去查它。

### 48.5 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 完成状态用字体颜色（绿=已完成、红=未完成）；未完成且临近/逾期 DDL 仍要染色 |
| 最终规则 | **只有未完成才染色**；已完成一律无底色 |
| 概念区分 | 完成状态（字色）与 DDL 紧急度（DDL 格的文字 + 底色）是两件事 |
| 实现 | 一个 `if not is_done` 判断，只写一处 |
| 真实坑一 | 名称格加了状态，测试按名字找行全部失效 -> 改前缀匹配 |
| 真实坑二 | 用 `background().color()` 判断「有没有底色」是错的，要看 `style()` |
| 新增测试 | 10 条（绿/红字色、两类染色、无 DDL 不染色、完成后取消染色） |
| 学到的 | ①「取消 X」要问清是全部还是某一类；②断言不符预期时先确认自己读对了没有 |

**这一章最值钱的两条**：

> **一、用户说「取消 X」时，要问清取消的是「全部」还是「某一类」。**
>
> 我按「取消所有底色」做了，结果用户要的是「只取消已完成那类的底色」。
> 多做的一半不但白费，还让用户不得不再提一次需求。

> **二、断言读到的值不符合预期时，先确认「我读对了吗」。**
>
> 读错一个属性（`color()` 而不是 `style()`）就能造出一个不存在的 bug，
> 然后花时间去查它。**先怀疑断言，再怀疑代码。**

---

## 第 49 章　两个"右键"bug：一个是我铺平了层级，一个是空白处根本没菜单

用户一次报了两个：

> 1个bug  Book内部各个栏目 目前右键新建文件夹存在异常
> 另外，在本地建立文件夹后，文件夹里面的内容在软件里会和文件夹平行显示

两个都跟"列表"有关，但根因完全不同。

### 49.1 bug 一：我把层级铺平了

`list_folder` 里有一段"递归铺平"：

```python
result.append(BookItem(name=entry.name, path=entry, is_dir=True, ...))
if entry.is_dir():
    for sub in entry.iterdir():
        result.append(BookItem(name=f"{entry.name}/{sub.name}", path=sub, ...))
```

于是表格变成：

```
第二章
第二章/2.1 极限.md     <- 和文件夹平行
```

我当初写它是有理由的：**"最近"列表**要"所有文件按修改时间排"，
铺平之后正好一把捞出深层文件。

但用户看到的是**假的层级**：那一行根本不在这一层。
更糟的是它带来的**行为错乱** —— 右键删它，删的是子文件夹里的文件；
拖拽排序排不动它；双击它打开的是一个"不在当前目录"的文件。
用户那句"内容会和文件夹平行显示"，说的就是这种错乱感。

**修法：默认只列一层，加一个 `recursive=True` 给"最近"用。**

```python
def list_folder(self, folder: Path, *, recursive: bool = False) -> list[BookItem]:
```

判断依据是**这个参数只该有一个调用点**。改完我发现确实只有一个
（`_refresh_recent`），其余三处都该只看当前层。

> **教训一：一个"为了方便"的默认行为，如果让别处产生了假的语义，就该改成可选。**
>
> 铺平不是错，错在它是**默认**。默认的东西会被所有调用点继承，
> 而"当前目录的列表"这个语义是不该被铺平污染的。

### 49.2 bug 二："右键新建文件夹存在异常"其实是三件事

用户说的"异常"，我一开始以为是报错。查下去发现是三件叠在一起：

**(1) 空白处右键什么都不弹。**

```python
def _on_context(self, pos):
    item = self.current_item()
    if item is None:
        return          # <- 空白处直接走人
    self.context_requested.emit(item, ...)
```

列表下方的空白区域右键**没有任何反应**。而"在空白处右键 -> 新建"
是文件管理器的通用习惯，用户当然会先试这个。

**(2) 新建的落点不看"你现在在哪一层"。**

```python
def _creation_dir(self, inside=None):
    if inside is not None:
        return Path(inside)
    return self._target_folder()      # <- 只看标签，不看当前目录
```

于是进了 `notebook/第一章` 之后在空白处新建，东西会落到 **`notebook`**
—— 也就是**上一级**。用户看到的和实际发生的不是一回事。

**(3) 在虚拟栏目里，新建是"做不到"的，却只给一句没用的话。**

`_target_folder()` 是靠标签登记的目录名工作的：

```python
for tab_key, _title, folder in self._tab_defs:
    if tab_key == key and folder:
        return book.path / folder
return None          # AI 总结 / 简介 / 全部条目：这些栏目没有对应目录
```

所以在「AI 总结」标签下右键新建，得到的是：

> 请先进入某个书目，并切到有对应目录的分类。

**可用户明明就在一个书目里。** 这句话既没解释清楚，也没给出下一步。

### 49.3 修法：把"落点"抽成一条规则，把"能不能"提前告诉用户

落点按**从最具体到最笼统**排：

```python
if inside is not None:                    # 1. 右键文件夹 -> 建在里面
    return Path(inside)
if self._current_folder is not None:      # 2. 正在浏览 -> 建在这一层
    return self._current_folder
if item is not None:                      # 3. 右键文件 -> 建在它旁边
    parent = Path(item.path).parent
    if parent.is_dir():
        return parent
folder = self._target_folder()            # 4. 栏目登记的目录
if folder is None:                        # 5. 虚拟栏目 -> 兜底
    folder = book.path / C.NOTEBOOK_FOLDER
```

第 3 条要注意用 `.parent` 而不是条目本身 ——
"右键一个文件夹"有两种意图："建在**它里面**"（走第 1 条）
和"建在**它旁边**"（走第 3 条）。菜单里两件事都提供，不会猜错。

**"做不到"要提前说，而不是点了才说：**

```python
_can_new = self._creation_dir(inside=_new_inside, item=item) is not None
_new_hint = "" if _can_new else "（当前栏目不支持）"
actions.append((f"新建文件夹…{_new_hint}", callback, _can_new))
```

`build_context_menu` 早就支持第三项 `False` 表示禁用（第 43 章前后加的），
所以这里只是**用上**它。菜单项灰掉 + 写明原因，
比"点了再弹一句看不懂的提示"好得多。

**空白处右键补一条通路：**

```python
def _on_context(self, pos):
    item = self.current_item()
    if item is None:
        self.clearSelection()        # 顺手清掉选中，免得动作作用在看不见的项上
        self.setCurrentCell(-1, -1)
    self.context_requested.emit(item, ...)   # item 可以是 None
```

然后在 `BookView` 里把 `item is None` 路由到一个专门的"目录级菜单"
（新建 / 上传 / 粘贴 / 刷新）。

> **教训二：用户说"异常"时，要问自己"他做了什么、期望什么、实际得到什么"。**
>
> 这里"实际得到什么"有三种：什么都没发生（空白处）、
> 建到了上一级（落点错）、弹一句看不懂的话（虚拟栏目）。
> 三种都被用户归成了同一个词"异常"。**如果只按字面理解去查报错，会一个都找不到。**

### 49.4 我修 bug 时又踩的两个测试坑

**坑一：切标签不会重填表格。**

我写了：

```python
window.book_view.tabs.setCurrentIndex(_nb_index)
_nb_names = [... for r in range(_nb_table.rowCount())]
```

读到空表。因为**各标签各有自己的表格**，`setCurrentIndex` 只是切换显示，
表格内容要靠 `refresh()` 重填。补一句 `refresh()` 就好了。

**坑二：我在 A 书里建文件夹，却去 B 书的表格里断言。**

测试里的 `book` 是「界面测试书目」，而这一段运行时窗口打开的是
「作业测试校修课 / 作业书目」—— 两个不同的书。
我一直在给 A 加文件、看 B 的表格，当然永远是空的。

改用**当前打开的书**：

```python
_cur_book = window.book_view.book()
_nb_root = _cur_book.path / C.NOTEBOOK_FOLDER
```

> **教训三：测试里要断言"当前打开的那个对象"，而不是"我手上恰好有的那个对象"。**
>
> 这个错误和功能 bug 长得一模一样（都是"什么也没有"）。
> 区别在于：查功能时会看到数据明明在盘上，
> **数据在、界面空**，那就是取错了对象或没刷新 —— 不是功能坏了。

### 49.5 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 右键新建文件夹异常；本地建的文件夹内容与文件夹平行显示 |
| bug 一 | `list_folder` 默认递归铺平 -> 假层级行；改成默认一层，`recursive=True` 只给「最近」 |
| bug 二(1) | 空白处右键 `item is None` 直接 return -> 补"目录级菜单" |
| bug 二(2) | 新建落点只看标签 -> 改成"从最具体到最笼统"四级 + 兜底 |
| bug 二(3) | 虚拟栏目新建只弹无用提示 -> 菜单项禁用 + 写明原因，并给兜底目录 |
| 测试坑一 | 切标签不会重填表格 -> 必须 `refresh()` |
| 测试坑二 | 在 A 书建、去 B 书断言 -> 用"当前打开的书" |
| 新增测试 | 16 条（层级、假层级、进入后可见、四种落点、空白处菜单） |
| 学到的 | ①方便但不能当默认；②"异常"要还原成"做了什么/期望/实际"；<br>③断言要用当前对象，数据在而界面空 = 取错对象 |

**这一章最值钱的三条**：

> **一、一个"为了方便"的行为，如果让别处产生了假的语义，就该改成可选而不是默认。**
>
> 铺平对「最近」是对的，对"当前目录"是错的。错不在功能，错在它是默认。

> **二、用户说"异常"时，要还原成"做了什么 / 期望什么 / 实际得到什么"。**
>
> 同一个词背后可能是"什么都没发生"、"结果去了别处"、"弹了句看不懂的话"。
> 只按字面去找报错，一个都找不到。

> **三、数据在盘上、界面却是空的 —— 先查"取错了对象"或"没刷新"。**
>
> 这一条能省下大量"怀疑功能坏了"的时间。

---

## 第 50 章　从"写死一条"到"用户自己维护"：论坛列表

需求很短：

> 论坛添加新增/删除论坛功能，需要用户提供论坛名称 网址

原来的实现是**菜单里写死一条**：

```python
menu = bar.addMenu("论坛(&O)")
self._add_action(menu, "牢大CS", lambda: self.open_forum("牢大CS"),
                 tooltip="用系统默认浏览器打开 https://cs9.x-way.work/")
```

加上从配置读网址的 `forum_url()`。也就是说：**想换一个论坛，得改代码**。

### 50.1 先想清楚"存哪"

第一件事是决定这份列表放哪儿。候选有两个：

* 单独一个文件，比如 ``data/else data/forums.json``；
* 放进 ``config.json`` 的一个数组。

选了后者，理由很实际：**这是设置，不是用户资料**。

* 它是"这台机器上我想用哪几个网址"，不是"我的学习内容"；
* 跟着配置走，就自动被配置的备份/迁移覆盖到，不用再补一处；
* 少一个文件就少一处"忘了备份它"的可能。

> **教训一：先分清"这是资料还是设置"。**
>
> 资料（笔记、错题）要能被单独拷走、单独版本管理；
> 设置（偏好、列表）跟着配置走最省心。
> 分类分对了，存储位置基本就定了。

### 50.2 老数据怎么办：把"搬家"放在读里

老配置只有一条 ``forum.laoda_cs_url``。要不要写一个迁移脚本？

**不写。** 因为迁移脚本**要有人去调** —— 而且这个人多半会忘。
改成放在"读"里：

```python
def load(config):
    raw_items = config.get(CONFIG_KEY)
    if isinstance(raw_items, list):
        ...                      # 以列表为准
        return forums
    # 只有键不存在时才搬家
    legacy = config.get(LEGACY_URL_KEY, LEGACY_URL)
    ...
```

「读」是**每次打开菜单都会走**的路径，所以这段代码一定会被执行到。
这就是第 45 章那条思路的又一次应用：**让正确的事成为必然，而不是靠记得。**

### 50.3 一个"删不掉的幽灵"：我实现时踩的真 bug

第一版的判定是"**列表为空就搬家**"：

```python
if forums:                       # 有内容就用它
    return forums
...                              # 空 -> 去搬老配置
```

看起来没问题，直到我把论坛**全删光**测了一下：

```
删完 -> []
再读第1次: ['牢大CS']      <- 它自己回来了
再读第2次: ['牢大CS']
```

**「牢大CS」复活了。** 因为"空列表"被当成了"还没搬过家"。

这个 bug 的形状很典型：**"没有"和"没有过"是两件事，而我把它们当成了同一件。**

正确判据是区分三个状态：

| `config.get("forum.list")` | 含义 | 该做什么 |
| --- | --- | --- |
| `None`（键不存在） | 从没设置过（老版本升级上来） | **搬家** |
| `[]` | 用户主动删光了 | **就应该是空的**，不许复活 |
| 有内容 | 用户的列表 | 直接用 |

```python
raw_items = config.get(CONFIG_KEY)
if isinstance(raw_items, list):
    return forums          # 键存在（哪怕解析后为空）就以此为准
if raw_items is not None:
    return []              # 坏数据也不搬家，免得出现删不掉的幽灵
# 只有 None 才走搬家
```

修完之后连读 5 次、重启软件，都老老实实是空的。

> **教训二：区分"没有"和"没有过"。**
>
> 很多"删了又回来"的 bug 都出于此：默认值填充、自动补建、
> 首次运行初始化 —— 只要判定写成"空就补"，用户主动清空的东西就会复活。
> 正确的判据通常是"**这个键有没有被写过**"，而不是"它现在是不是空的"。

### 50.4 输入校验：把用户当正常人

用户填网址的习惯是``cs9.x-way.work``（不写协议）。直接拿去打开会失败。
所以：

```python
def normalize_url(raw):
    text = "".join(raw.split())      # 去掉中间的空格
    if "://" not in text:
        text = "https://" + text      # 自动补协议
    return text
```

但"自动改用户的输入"要**让用户看见**，否则他会以为软件乱改东西。
所以对话框里实时显示一句「将打开：https://cs9.x-way.work」。

校验只挡真的会出错的：

| 输入 | 结果 |
| --- | --- |
| `cs9.x-way.work` | OK（自动补协议） |
| `abc` | 拦下：域名里缺少点 |
| `ftp://x.com` | 拦下：只支持 http / https |
| 空 | 拦下：不能为空 |
| 重名 | 拦下：已经有一个叫「…」的论坛了 |

`abc` 那条（域名里没有点）挡的是手滑 —— 它技术上是个合法 URL，
但填成这样基本一定是打错了。

> **教训三：能自动修的自动修，但要**让用户看见**；只挡真正会出错的。**
>
> 自动补协议是帮忙；如果顺手把 `ftp://` 也"修"成 `https://`，那才是乱改。

### 50.5 删除要有确认，但不是所有操作都要

删除论坛**要确认**（用户选的），因为删掉之后得重新输名称和网址，
成本不高但很烦。而"上移/下移"不确认 —— 点错了再点回来就行。

判据是：**这个操作重做一次要多少代价。** 代价高的才值得打断用户。

确认文案里还特意写了"只是从菜单里去掉，不会影响那个网站本身"
—— 用户看到"删除"两个字会紧张，说清楚**删的是什么、不影响什么**，
比一句"确定吗？"有用。

### 50.6 定稿 v2.1

这次一并把版本号从 `1.0.0` 定稿到 `2.1.0`，并整理更新记录。
版本号只有一个来源（`gwp/__init__.py` 的 `__version__`），
窗口标题、关于框、日志、安装包信息都从它取。

顺手修了文档里一处**过时信息**：打包说明写着"版本号在
`gwp/core/constants.py` 的 `APP_VERSION`"—— 那是旧位置，早就搬走了。
按旧说明去找会找不到。

> **教训四：文档里的"位置信息"最容易过期。**
>
> 代码搬了家、文档没跟上，比没有文档更糟 —— 用户会照着找，然后怀疑自己。
> 所以我把"版本号在哪"这句话连同"**这里原先写错了**"一起写进文档，
> 让它下次不会再被抄错。

### 50.7 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 论坛支持新增 / 删除，用户提供名称与网址 |
| 存储选择 | 放 `config.json` 的 `forum.list`（这是设置，不是用户资料） |
| 老数据 | 搬家逻辑放在 `load()` 里（「读」一定会被执行到），不写迁移脚本 |
| 真实 bug | "列表为空就搬家"导致**删光后幽灵复活**；判据改成"键是否存在" |
| 输入校验 | 自动补 `https://` 并**显示给用户看**；只挡真会出错的输入 |
| 删除确认 | 要确认（用户选的），文案说清"删的是什么、不影响什么" |
| 界面 | 菜单每次展开时重建，增删改立刻生效、不用重启 |
| 定稿 | 版本号 `1.0.0` -> `2.1.0`；整理更新记录；修正文档里的过时位置 |
| 新增测试 | 28 条（搬家、校验、增改删调序、不复活、菜单、版本号） |
| 学到的 | ①先分清资料还是设置；②区分"没有"和"没有过"；<br>③自动修要让用户看见；④文档里的位置信息最容易过期 |

**这一章最值钱的两条**：

> **一、区分"没有"和"没有过"。**
>
> "删了又回来"的 bug 几乎都是这个形状：判定写成"空就补"，
> 于是用户主动清空的东西会复活。正确判据通常是
> **"这个键有没有被写过"**，而不是"它现在是不是空的"。

> **二、能自动修的自动修，但要**让用户看见**；只挡真正会出错的。**
>
> 自动补 `https://` 是帮忙；对话框里实时显示"将打开：…"，
> 用户才知道软件替他做了什么。静默地改用户输入，比不改更让人不安。

---

## 第 51 章　日程栏只显示「还要动手的事」

需求两条，很短：

> 日程默认 隐藏已完成  超过DDL后，日程栏不再显示

合起来是一件事：**日程栏不是记录栏，是待办栏。**

### 51.1 「默认勾上」和「记住选择」是两件事

第一条看着只是"把复选框默认值改成 True"。但这里有个容易做错的地方：

```python
self.check_hide_done = QCheckBox("隐藏已完成")
self.check_hide_done.setChecked(True)      # 这样写是错的
```

这么写的话，用户**每次启动**都会被掰回"隐藏" —— 他上次特意取消勾选
想看已完成的，下次打开又没了。他会觉得"软件不听话"。

正确做法是**分清"默认值"和"用户的选择"**：

```python
# 默认值只在"从没设置过"时生效
_hidden = self._config.get("ui.schedule_hide_done", True)
self.check_hide_done.setChecked(bool(_hidden))
```

然后在用户切换时写回配置：

```python
def _on_hide_done_toggled(self, checked):
    self._config.set("ui.schedule_hide_done", bool(checked))
    self._config.save()
```

> **教训一：需求说"默认如何"时，要问一句"那用户改过之后呢"。**
>
> "默认隐藏"是初始状态；"我改成显示"是用户的意思表示。
> 把默认值当成每次启动都执行的赋值，就是在**覆盖用户的设置** ——
> 这类 bug 用户很难描述，他只会说"它老是自己变回去"。

### 51.2 过滤规则要写清楚"什么不算过期"

第二条的关键不在"过滤"本身，而在**边界**：

| 情形 | 显示吗 |
| --- | --- |
| 未完成 + 已过 DDL | 不显示 |
| **未完成 + 没有 DDL** | **显示** |

第二行是我特意保住的。因为"没有 DDL"和"DDL 已经过了"在代码里很容易被写成
同一件事：

```python
moment = entry.due_at
if moment is None or moment < now:      # 错的
    return False
```

这么写会把**所有没设时间的日程**一起藏掉 —— 用户新建一条"记得买牙膏"，
下一秒它就不见了。那是个比原需求严重得多的 bug。

正确的写法是**分开判断**：

```python
if entry.done:
    return not hide_done
moment = entry.due_at
if moment is not None and moment < now:
    return False          # 过了 DDL 且未完成 -> 不显示
return True
```

> **教训二：写过滤条件时，先列出"哪些不该被过滤掉"。**
>
> `None or 过期` 这种"把缺失值并进条件里"的写法特别顺手，也特别危险：
> 缺失值（没设时间）和条件值（过期）语义完全不同，
> 合并之后缺失的那一类会被静默吃掉。

### 51.3 东西消失了，必须给个交代

过滤掉条目有个副作用：用户会觉得"我的记录呢？"

所以被"过期"藏起来的未完成条目要**数出来告诉他**：

```
另有 2 项已过 DDL，不再显示
```

鼠标停上去还能看到具体是哪几条（tooltip 里列出来）。

为什么不干脆留一行"已过期"的灰条？因为那正是需求要清掉的东西。
**信息要给，但不能占着待办列表的位置** —— 一句话加一个 tooltip，
既不干扰"现在该做什么"，也不让人以为数据丢了。

> **教训三：隐藏信息时，要给一个"它们还在"的信号。**
>
> 用户看不到的东西，默认会理解成"没有了"。一句计数提示的成本几乎为零，
> 但它把"数据丢了"变成"哦，被收起来了"。

### 51.4 两个测试把我拦了下来

这次改动让两条**既有测试**失败了，而且两条都是"测试写死了旧行为"：

**(1) 一条断言写的是"标完成后排到未完成之后"。**

它点击「完成」按钮，然后检查那一行还在列表里、只是排在后面。
可新需求是"完成了就不显示"。所以正确的断言变成两步：

```python
# 默认隐藏 -> 它应该消失
check("标完成后默认就从日程栏消失", "日程作业甲" not in _row_titles())
# 取消勾选 -> 它回来，并且排在未完成之后、带划线
panel.check_hide_done.setChecked(False)
check("完成后排到未完成之后", moved.index("甲") > moved.index("乙"))
```

**(2) 另一条断言写的是"过期的 DDL 标注「已过期」"。**

它收集面板上所有文字，断言里面含有"已过期"。但新规则下过期条目
**根本不在面板上**，这句话永远不会出现。改成验证新行为：

```python
check("已过 DDL 的条目不再出现", "状态-过期" not in _visible_names)
check("但它被数进了「已过 DDL」提示", "已过 DDL" in panel.lbl_expired.text())
```

> **教训四：需求改变了行为，失败的老测试是"信息"而不是"障碍"。**
>
> 这两条失败恰好把"旧行为是什么"写得很清楚。
> 我的处理不是删掉它们，而是**把断言改写成对新行为的描述** ——
> 这样测试的意图和用户的话始终对得上。

### 51.5 一个"偶发失败"背后的真问题

改完之后 `smoke_core` 里有两条断言开始偶发失败（数据监听那节：
"第二次改动同样被发现"）。这种"改 A 却让 B 偶发失败"的情况最容易
被当成环境抖动糊过去。我按三步查了：

1. **停掉正在运行的软件**（排除后台扫描抢 IO）-> 仍然稳定失败，不是它；
2. **单独写一个最小诊断脚本** -> 竟然**通过**了；
3. 于是问题在**测试的上下文**里。

最后定位到真正的原因，而且它比"测试抖动"重要：

> **快照存的是 `{路径: mtime_ns}`，而 Windows 对极快连续的同文件重写
> 有时不更新 mtime。**

实测：

```
先写 3 字节、紧接着写 27 字节（长度都变了）
-> st_mtime_ns 仍然是上一毫秒的那个值
-> 两次快照看起来一模一样 -> 这次改动发现不了
```

影响面我也测了：

| 两次写入的间隔 | 能发现吗 |
| --- | --- |
| 完全不等（脚本紧循环） | **可能漏** |
| 50 ms | 能 |
| 1 秒（人手速） | 能 |

**结论：真实使用不受影响**（人不可能在 1 毫秒内保存两次），
但这个边界必须写下来，而且**测试必须显式推进 mtime**，
否则断言会偶发失败 —— 那看起来像防抖逻辑坏了，其实只是文件系统
没给出可分辨的时间戳。

为什么不干脆给每个文件算哈希来彻底解决？因为那要把每次扫描
从 `os.scandir` 的 10 毫秒变成读 5100 个文件的内容，
第 44 章辛苦压下来的 CPU 占用会前功尽弃。**为一个 1 毫秒的边界付这个代价不值得。**

> **教训五："偶发失败"值得查到底，它常常指向一个真实的边界。**
>
> 如果当时我写一句"这是时序抖动"就放过，就永远不知道
> "mtime 可能不变"这件事 —— 而它正好解释了为什么监听偶尔会晚一拍。

### 51.6 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 日程默认隐藏已完成；超过 DDL 后日程栏不再显示 |
| 关键区分 | **默认值**（初始状态）与**用户的选择**（写回配置，不被覆盖） |
| 过滤边界 | 未完成 + 过期 -> 隐藏；**没有 DDL 的永远显示** |
| 信息交代 | 面板提示「另有 N 项已过 DDL」+ tooltip 列出具体条目 |
| 测试影响 | 两条旧断言写死了旧行为 -> 改写成对新行为的描述 |
| 真问题 | 快照只比 `mtime_ns`；Windows 对极快同文件重写可能不更新 mtime -> 该次改动发现不了（实测：只有 <1ms 才可能漏） |
| 为什么不为它加哈希 | 会把每次扫描从 10ms 变成读 5100 个文件，CPU 前功尽弃 |
| 新增测试 | 11 条（默认勾选、记住选择、过期不显示、无 DDL 仍显示、提示计数、提示细节） |
| 学到的 | ①"默认"不等于"每次赋值"；②过滤条件要列"什么不该被过滤"；<br>③隐藏要给信号；④老测试失败是信息；⑤偶发失败常常是真边界 |

**这一章最值钱的三条**：

> **一、需求说"默认如何"时，要问"那用户改过之后呢"。**
>
> "默认隐藏"是初始状态，"我改成显示"是用户的意思表示。
> 把默认值当成每次启动都执行的赋值，就是在覆盖用户的设置。

> **二、写过滤条件时，先列出"哪些不该被过滤掉"。**
>
> `if moment is None or moment < now` 这种把缺失值并进条件的写法特别顺手，
> 也特别危险 —— 缺失值（没设时间）和条件值（过期）语义完全不同，
> 合并之后缺失的那一类会被静默吃掉。

> **三、"偶发失败"值得查到底，它常常指向一个真实的边界。**
>
> 我这次因此发现了"Windows 对极快同文件重写可能不更新 mtime"。
> 查清楚之后才能做出正确的取舍（不为 1 毫秒的边界加哈希），
> 而不是含糊地"重跑一次就过了"。

---

## 第 52 章　AI 让软件去问：一条被"只管图片"卡住的岔路

需求只有一句：

> 单词卡那里，你用API问AI，不要让用户自己问

功能本来就有 —— "点添加单词，AI 自动补齐音标、释义、例句"。
但它**在有 API Key 的机器上仍然要用户手动粘贴**。这一章记的就是
"为什么一个看起来已经做好的功能，实际用起来是错的"。

### 52.1 两条路，只有一条接了直连

补齐单词卡时，界面调用的是一个统一入口：

```python
reply = web_bridge.send_to_ai(prompt, provider_id=..., context=self.context, ...)
```

它内部有两条路：

* **① 直连 API** —— 全自动，零粘贴；
* **② 网页版桥接** —— 把提示词复制到剪贴板、打开网页、弹窗让你把回答粘回来。

问题在于 ① 的入口条件：

```python
if image_path is not None and context is not None:      # <- 只在"带图片"时才试直连
    ...
    return reply
# 否则一律走 ②
```

**只有带图片的请求才会尝试直连。** 而单词卡是**纯文本**，
于是永远掉进 ② —— 哪怕用户早就把 DeepSeek 的 Key 填好了。

这不是"没做"，而是"做了一半"：直连这条路修好之后，**只给图片开了门**。

> **教训一：一个"已经做好了"的功能，要问清它**在什么条件下**才走好路。**
>
> 代码里明明有"直连 API"这段，单元测试大概也能过 —— 因为它们会传 `image_path`。
> 真实使用中单词卡不传图片，于是从来走不到那段。
> **"有没有这个能力"和"这条路径会不会被走到"是两个问题。**

### 52.2 修法：把判据按"隐私含义"分级

直接放开"纯文本也直连"很简单，但不能一把梭 —— 因为图片和文本的隐私含义不同：

| 请求类型 | 直连条件 |
| --- | --- |
| **纯文本** | 提供方**已配置好**即可（用户填了 Key 就是想让软件去问） |
| **带图片** | 提供方**声明支持视觉** **且** 用户**显式允许发图** |

于是把判断抽成一个函数：

```python
def _call_direct(context, text, *, provider_id="", image_path=None) -> str:
    for candidate_id in _direct_candidates(context, provider_id):
        if image_path is not None:
            if not _provider_sees_images(context, candidate_id, provider): continue
        elif not _provider_ready(context, candidate_id):      # 纯文本：只要配好了
            continue
        reply, used = manager.chat_with_fallback([message])
        if reply: return reply
    return ""        # 拿不到就返回空，由调用方决定要不要兜底
```

**失败仍然退回 ②**：没配 AI 的用户照样有手工那条路，不会被堵死。

> **教训二：放宽权限时要按"数据敏感度"分级，而不是一律放开。**
>
> "文本能直连"和"图片能直连"应该有两套判据。一把梭放开图片直连，
> 等于替用户决定"可以把它屏幕上的东西发出去"。

### 52.3 顺手挖出一个真 bug：模型不听 schema 时写进乱码

测试时我盯着落盘的卡片看了一眼，发现例句字段是

```
[{'en': 'Smartphones are ubiquitous today.', 'zh': '如今智能手机无处不在。'}, ...
```

**141 个字符的人形乱码。** 原因：提示词要求

```
"examples": "2~3 个例句。每行一句，格式：英文句子 —— 中文翻译"
```

（**字符串**），但模型返回了**数组**；而 `from_dict` 里是

```python
examples=str(data.get("examples") or ""),      # 对列表调用 str() 就是这结果
```

`str(列表)` 把 Python 的表示形式直接写进了用户的卡片文件。

修法是把"值转文本"这件事收成一个函数，按形状处理：

```python
def _as_text(value) -> str:
    if isinstance(value, str):    return value.strip()
    if isinstance(value, (list, tuple)):
        # 字典按 en/zh 拼成 "英文 —— 中文"（正好是提示词要求的行格式）
        ...
        return "\n".join(lines)
    return str(value).strip()
```

**为什么值得容忍这么多种形状**：模型不听 schema 是常态，
但**用户的卡片文件必须是干净的**。在边界上多写十行容错，
好过让乱码进到用户的资料里。

> **教训三：AI 的输出是"外部输入"，要用对待外部输入的严格程度去清洗。**
>
> 我们在第 12 章就学过"外部文件要校验"；AI 的回答同样是外部输入，
> 而且它**更不可控**（同一个提示词，今天返回字符串、明天返回数组）。
> 直接 `str()` 存进用户文件 = 把不可控的东西当可信数据。

### 52.4 一个把自检搞崩的 Qt 陷阱

改完之后，`smoke_core`（无界面自检）**直接崩溃**，退出码 `0xC0000409`，
日志里只有一行：

```
QWidget: Cannot create a QWidget without QApplication
```

原来是：写保护触发时调用了 `common.error(...)`，而**没有 QApplication 时
创建任何 QWidget，Qt 会直接中止进程**（不是抛 Python 异常）。

修法是在 `common.py` 里加一道判断，**所有消息框都过它**：

```python
def has_gui() -> bool:
    app = QApplication.instance()
    return isinstance(app, QApplication)     # 注意 must-be-instance
```

这里的细节值得单独记一笔：**第一版我写的是 `app is not None`**，
结果 `has_gui()` 返回 True、放行建 QMessageBox、进程照崩。
因为那个 `instance()` 返回的是 **`QCoreApplication`**（某些 Qt 模块或
测试代码会建一个），不是 `QApplication` —— **它非空，但不能建控件**。

```python
return QApplication.instance() is not None        # 错：QCoreApplication 也算
return isinstance(QApplication.instance(), QApplication)   # 对
```

`confirm()` 在没有界面时一律返回 `False`（视为"取消"）——
**无人确认时不做破坏性操作**，这个默认方向是有意的。

> **教训四：检查"能力是否存在"时，要检查**具体那个能力**，不是它的父类。**
>
> "有 app 实例"和"能建窗口"是两件事。写成 `is not None` 就是把
> QCoreApplication 也算进来了 —— 而它在无界面场景里经常存在。

### 52.5 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 单词卡由软件调用 API 补齐，不要让用户自己去问 |
| 根因 | `send_to_ai` 的直连通道**只对带图片的请求**开放；纯文本一律走手工粘贴 |
| 修法 | 抽出 `_call_direct`；**按数据敏感度分级**：文本只看"配没配好"，图片还要"声明支持 + 用户允许" |
| 兜底保留 | 直连不可用时仍退回"复制提示词 + 粘贴"，没配 AI 的用户照样能用 |
| 顺带修真 bug | 模型把 `examples` 当数组返回时，`str(list)` 会把乱码写进用户卡片 -> 加 `_as_text` 按形状归一 |
| 自检崩溃 | 无 QApplication 时建 QMessageBox -> Qt 直接中止进程；加 `has_gui()`，判据必须是 `isinstance(app, QApplication)` |
| 测试踩坑 | 探针的假 config 没返回 active provider -> 候选为空、断言失败（测试桩不像真实配置，不是功能问题） |
| 新增测试 | 14 条（数组形状归一、直连不弹粘贴、有界面时退回粘贴、无界面不建控件、has_gui 判据） |
| 学到的 | ①"有这能力"≠"这条路会被走到"；②放宽权限要按敏感度分级；<br>③AI 输出要当外部输入清洗；④检查能力要检查具体那个 |

**这一章最值钱的三条**：

> **一、一个"已经做好了"的功能，要问清它**在什么条件下**才走好路。**
>
> 直连 API 那段代码一直都在，只是入口条件写成了"必须带图片"。
> 单词卡不传图片，于是永远走不到 —— 功能在，路径不在。

> **二、AI 的输出是外部输入，而且比文件更不可控。**
>
> 同一个提示词，今天返回字符串、明天返回数组。
> 直接 `str()` 存进用户文件，就是把不可控的东西当可信数据 ——
> 结果是用户卡片里出现 141 个字符的人形乱码。

> **三、检查"能力是否存在"时，要检查具体那个能力，不是它的父类。**
>
> `QApplication.instance() is not None` 会把 `QCoreApplication` 也算进来，
> 而后者**不能建窗口**。判据松一格，进程就当场中止。

---

## 第 53 章　把阻塞调用挪到后台：单词补齐卡死

用户报障，只有一句：

> 单词补齐功能障碍，会导致程序卡死，检查修复一下

这句是我自己上一章埋的雷。

### 53.1 我上一章改了什么，为什么埋雷

第 52 章的需求是"单词卡那里用 API 问 AI，不要让用户自己问"。
我改了 「send_to_ai」：纯文本也走直连 API。

但**我只看改了"能不能直连"，没看"在哪个线程里直连"**。

调用它的地方是这样的：

```python
def complete_card(self, card):
    reply = web_bridge.send_to_ai(prompt, ...)      # ← 网络请求，同步
    ...
def complete_all(self):
    for card in pending:                            # ← UI 线程里循环
        self.complete_card(card)
```

于是：

* 单张：界面线程一路等网络，点完那一下就没反应；
* 补齐全部：**逐张串行**，界面被冻住的时间 = 所有请求时间之和。

而改动之前它是"复制提示词 + 弹窗等粘贴"——**本来也是阻塞的**，
但那是用户主动参与的过程（他知道在等自己）。改成后台 API 调用之后，
阻塞就变成了纯粹的假死：没有任何提示，界面就是不动。

> **教训一：改"走哪条路"时，要重新检查这条路的**耗时特征**。
>
> 粘贴是"等人"，是慢但可感知的；API 是"等网络"，是慢且不可感知的。
> 同样的同步代码，前者用户能忍，后者就是卡死。

### 53.2 修法：线程边界要划清楚，而不是加个进度条

第一反应是"加个进度框"。但那不解决问题：进度框自己就在界面线程里，
调 `processEvents()` 也救不了**一次同步网络请求**。

真正的修法是把**线程边界**画出来：

| 谁 | 只干这些 |
| --- | --- |
| **后台线程** | 发请求、等回答（唯一允许阻塞的地方） |
| **界面线程** | 解析、合并、读写文件、刷新界面（都是毫秒级） |

于是补齐变成：

```python
def task(*, on_progress, should_cancel, **_):
    results = []
    for index, name in enumerate(names, 1):
        if should_cancel():            # 可取消
            break
        on_progress(f"正在补齐 {index}/{total}：{name}", ...)
        reply = web_bridge.send_to_ai(..., allow_paste=False)
        results.append((name, reply.strip(), ""))
    return results
```

界面线程只接结果：

```python
worker = AIWorker(task, parent=self, label="补齐单词")
worker.progress.connect(self._on_completion_progress)
worker.finished_ok.connect(self._on_completion_finished)   # 写盘在这里
worker.start()
```

`AIWorker` 是项目里早就有的东西（AI 总结、AI 对话、AI 摘要都用它），
所以这次**没有新增基础设施**，只是把该用的地方用上了。

> **教训二：项目里已经有"正确做法"时，先找它，别新造。**
>
> 我如果一开始就照 AI 总结的写法（`AIWorker` + 进度 + 取消），
> 这个 bug 根本不会出现。第 52 章我只盯着"能力判断"，
> 完全没去看同目录下别的 AI 功能是怎么起线程的。

### 53.3 一个必须加的开关：后台线程里不许弹窗

后台任务里调用 `send_to_ai` 有个致命风险：**它的兜底路径会弹粘贴框**。

Qt 在非 GUI 线程里创建 QWidget，不会抛 Python 异常 ——
它会直接打印一行然后**中止进程**。于是给入口加了个显式开关：

```python
send_to_ai(..., allow_paste=False)   # 后台任务一律这样传
```

`allow_paste=False` 时它**绝不**碰剪贴板、不开浏览器、不弹框，直连拿不到就返回空串。

批量场景还有第二个理由：如果允许粘贴，十张卡就是**十个浏览器窗口**。

> **教训三：会被后台线程调用的函数，必须能"关掉一切界面行为"。**
>
> 不能靠"调用方记得别传 parent"这种约定 —— 要在函数签名上给出开关，
> 让"我此刻在后台"这件事变成显式参数。

### 53.4 顺带修的两个跨线程隐患

**(1) 事件总线的通知**

`AIWorker` 里调 `chat_with_fallback`，主 AI 失败时会发 `AI_FALLBACK`。
处理函数里要改状态栏、要弹提示框 —— **那是后台线程在执行**。

修法是给 `common` 加一个闸门：

```python
def run_in_gui(context, fn):
    if is_gui_thread():
        fn()
    else:
        QTimer.singleShot(0, context, fn)   # 挂到 context 所在线程
```

两个 `_on_fallback` 都改成走它。

**(2) 信号连接别用 lambda**

跨线程信号要投递回界面线程，需要一个 QObject 接收者来确定线程归属。
连成员方法最稳；连普通函数/lambda 时 PyQt 的语义更微妙，可能变成直接调用。
所以 `finished_ok` 连的是 `self._on_completion_finished`，
"是否强制覆盖"这种参数改成实例字段传递。

> **教训四：跨线程 signal/slot 是"约定"而不是"魔法"。**
>
> 自动连接（AutoConnection）的判定依赖接收者的线程归属。
> 用一个 `lambda` 就把这个信息丢掉了 —— 看起来更短，实际更脆。

### 53.5 怎么证明"真的不卡"

原来的测试打桩的假 AI 是**瞬时返回**的 —— 那种情况下同步和异步没区别，
阻塞也测不出来。所以专门加了一条：

```python
def _slow_word_ai(prompt, **kwargs):
    _wb_threads.append(QThread.currentThread())
    time.sleep(0.4)          # 模拟慢网络
    return json.dumps({"meaning": "伽马", ...})

view.complete_card(card)
assert 派发耗时 < 300ms                      # 立即返回
assert 期间界面线程还在处理定时器事件         # 没被冻住
assert 所有 AI 调用都不在 GUI 线程上          # 真的在后台
```

三个断言分别对应"派发不阻塞""界面能转""线程确实换了"。

> **教训五：测"不卡"必须让假实现**真的慢**，并且校验线程身份。**
>
> 秒回的假 AI 只能证明"结果对"，证明不了"没有阻塞"。

### 53.6 我自己又踩的一个测试坑

加批量补齐用例时，我把 `send_to_ai` 打桩还原之后**忘了重新打桩**。
症状很有迷惑性：断言说"AI 被调用了"（因为调用记录里还有上一条），
但卡片就是没补齐、而且进程退出时还有一个后台线程在跑。

原因：那一次走的是**真实网络调用**（测试环境里没有 Key，它就慢慢等）。
所以"测试里忘了打桩"的表现不是报错，而是**变慢 + 结果不对**。

> **教训六：测试里"恢复打桩"要成对出现，跨用例时更要小心。**
>
> 我的做法是把打桩/还原写在同一段 `try/finally` 里，
> 并在注释里写明"这里必须重新打桩，我漏过一次" ——
> 让下一个人（或半年后的我）一眼看到陷阱在哪。

### 53.7 复盘

| 类别 | 内容 |
| --- | --- |
| 需求 | 单词补齐卡死 -> 修复 |
| 根因 | 第 52 章把补齐改成同步 API 调用，但仍在 UI 线程执行；「补齐全部」还是逐张串行 |
| 修法 | 照 `AIWorker` 的既有模式：后台只取回答，UI 线程解析/写盘；带进度与取消 |
| 新开关 | `send_to_ai(allow_paste=False)`：后台线程绝不碰剪贴板/浏览器/弹窗 |
| 批量门槛 | 没有可直连 AI 时**明确拒绝**并说明原因（否则会开 N 个浏览器窗口） |
| 顺带修 | `AI_FALLBACK` 通知从后台线程到达 -> `common.run_in_gui` 切回 GUI 线程；跨线程信号连成员方法而非 lambda |
| 新增测试 | 8 条（派发立即返回、期间界面仍转、AI 在非 GUI 线程、结果写回、批量拒绝、批量补齐、allow_paste 闸门、has_direct_provider） |
| 学到的 | ①改路径要看耗时特征；②先找项目里已有的正确做法；③后台调用要有"关界面"开关；④跨线程连接别用 lambda；⑤测不卡要让假实现真慢；⑥测试打桩要成对 |

**这一章最值钱的三条**：

> **一、改"走哪条路"时，要重新检查这条路的耗时特征。**
>
> "等人粘贴"和"等网络"在代码里都是同步调用，但对用户完全是两件事：
> 前者他知道在等自己，后者就是假死。

> **二、项目里已经有正确做法时，先找它。**
>
> `AIWorker` 早就在那儿，AI 总结、AI 对话都在用。
> 我第 52 章只盯着能力判断，没抬头看一眼同目录怎么起线程 ——
> 于是把一个已验证过的模式又踩了一遍。

> **三、会被后台线程调用的函数，要能"关掉一切界面行为"。**
>
> 不是靠调用方自觉，而是签名上的显式开关（`allow_paste=False`）。
> Qt 在非 GUI 线程建控件是直接中止进程，没有异常可以捕获。

---

## 附录 A　本项目的代码地图（速查）

```
code/
├── gwp_main.py          进程入口
├── gwp/
│   ├── app.py           创建 QApplication、单实例
│   ├── bootstrap.py     组装 AppContext
│   ├── cli.py           命令行工具
│   ├── core/            ← 常量、路径、配置、日志、事件总线
│   │   ├── constants.py     所有声明表（栏目/目录/提示词）★
│   │   ├── paths.py         路径解析（含冻结环境）
│   │   ├── config.py        深合并配置 + 密钥分离
│   │   └── eventbus.py      极简事件总线
│   ├── data_manager/    ← 数据层（不许 import Qt）
│   │   ├── store.py         Library：科目/书目扫描与增删改 ★
│   │   ├── metadata.py      元数据原子读写
│   │   ├── boxes.py         收纳箱（含全局生成号缓存）★
│   │   ├── homework.py      作业（内容/DDL/提交方式/完成）
│   │   ├── schedule.py      其它日程
│   │   ├── cache.py         扫描缓存
│   │   └── summary_backup.py 总结的版本备份
│   ├── ai/              ← AI 层（仅 worker.py 可用 Qt）
│   │   ├── manager.py       提供方管理与兜底链 ★
│   │   ├── registry.py      注册表 + 自动发现
│   │   ├── providers/       各提供方适配器（加文件即扩展）
│   │   ├── summarizer.py    总结：收集/分块/提示词 ★
│   │   ├── chat_session.py  聊天记录
│   │   └── worker.py        后台线程（唯一的 Qt 例外）
│   ├── services/        ← 服务层
│   │   ├── file_ops.py      文件操作（原子、改名、回收站、VSCode）
│   │   ├── file_clipboard.py 剪贴板（与系统互通）
│   │   ├── pdf_exporter.py  Markdown→PDF（页码、切页）★
│   │   ├── markdown_renderer.py 渲染
│   │   ├── themes.py        QSS 主题（浅/深）
│   │   ├── background.py    背景图
│   │   ├── weather.py       日期/时间/天气 ★
│   │   └── shell_ops.py     回收站、快捷方式、开机自启、打开网址
│   ├── ui/
│   │   ├── main_window.py   主窗口 + 菜单 + 路由 ★
│   │   ├── views/
│   │   │   ├── base_view.py     视图基类（标题栏/按钮锁宽）★
│   │   │   ├── home_view.py     首页（卡片/收纳箱/日程栏）★
│   │   │   ├── subject_view.py  科目页
│   │   │   ├── book_view.py     书目页（栏目/文件/作业）★
│   │   │   ├── document_view.py 文档查看/编辑 + AI 双栏
│   │   │   └── text_view.py     纯文本只读查看器
│   │   ├── widgets/
│   │   │   ├── cards.py         卡片 + 拖拽 + 网格 ★
│   │   │   ├── file_table.py    文件表格（含作业模式）
│   │   │   ├── schedule_panel.py 日程栏
│   │   │   ├── clock_bar.py     日期/天气条
│   │   │   └── md_editor.py     Markdown 编辑器
│   │   ├── dialogs/         各对话框（科目/书目/作业/日程/设置…）
│   │   └── windows/         独立窗口（文档窗口、AI 对话窗口）
│   └── resources/       图标（PEP 562 惰性加载）
├── tests/
│   ├── lint_report.py   静态检查（含分层依赖检查）★
│   ├── smoke_core.py    核心自检（395 条）
│   └── smoke_gui.py     界面自检（508 条，offscreen）
└── installer/
    ├── installer.py     安装器（tkinter，零额外依赖）
    ├── acceptance.py    验收：装→跑→卸
    ├── verify_no_python.py 验证"目标机没有 Python 也能跑"
    └── make_*.py        生成说明书与本书的 PDF
```

（★ = 最值得先读的文件）

---

## 附录 B　术语表

| 术语 | 含义 |
| --- | --- |
| **声明表** | 把"类型与行为的对应关系"写成数据，而不是 `if/else` |
| **原子写** | 先在临时文件写，再原子替换，避免"写了一半" |
| **生成号** | 全局计数器，写操作 +1，用来一次性作废所有缓存 |
| **白名单 / 黑名单** | 默认不参与 / 默认参与；前者更安全 |
| **惰性导入** | 在函数内 import，避免启动时加载全部模块 |
| **防抖（debounce）** | 输入停止一段时间后才执行，避免频繁触发 |
| **打桩（stub）** | 测试里替换掉真实实现（比如模态对话框） |
| **验收（acceptance）** | 验证交付物本身能用，而非验证代码逻辑 |
| **止损** | 判断某个方案不值得继续，及时放弃并清理 |
| **人在环路** | 流程中有人的参与（如网页版 AI 的剪贴板桥） |

---

## 附录 C　如何继续补充这本书

这本书**不是一次写完的**。项目还在改，书就要跟着长。约定如下：

**每次新增功能时，在相应位置补一节**，结构固定为四段：

```markdown
### N.M 功能名

**需求**（原话引用，不要转述）

**分析**：这次变更的影响面是什么？
     是数据模型变更、界面变更，还是纯数据？
     要动几个文件？

**实现**：
    1. 关键代码（带文件路径）
    2. 为什么这么写（而不是另一种写法）

**复盘**：
    * 改了哪些文件
    * 哪些**没动**（这是架构好坏的证据）
    * 踩到的坑 / 学到的通用经验
```

**每次踩到新坑时，在附录 A 的三张表里加一行**：

| # | 坑 | 症状 | 心法 |
| --- | --- | --- | --- |
| 39 | （新坑） | （现象） | （一句话经验） |

**每次改变架构约定时，在相应章节更新说明**，
并检查附录 A 的代码地图是否需要同步。

**排版命令**：

```powershell
code\venv\Scripts\python.exe code\installer\make_dev_book.py
```

它会把 Markdown 源排版成 PDF，并同时写到三个位置：

* `Document\开发实践——Great White Planet.pdf`（主）
* `开发实践——Great White Planet.pdf`（项目根目录备份）
* `DeepseekData\开发实践——Great White Planet.pdf`（随交付包）

> **一条纪律**：**改代码的同时改文档。**
> 事后补文档的成本高十倍，而且一定会漏。
> 把"更新书稿"当成提交前检查清单里的一项（就像跑测试一样）。

---

**（全书完）**

*本书对应 Great White Planet v1.0，代码规模：88 个模块 / 约 21,500 行主程序，
900+ 条自检断言。书稿会随项目持续补充。*
