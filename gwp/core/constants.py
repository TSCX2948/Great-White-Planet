"""全局常量：文件名、目录名、支持的扩展名、默认提示词。

这里是唯一的“约定”来源。任何模块需要使用固定文件名（例如 Introduct.md）
都必须引用本模块的常量，不要在各处硬编码字符串。
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# 固定的文件名 / 目录名（对应需求文档第四节的 Book 目录结构）
# --------------------------------------------------------------------------

INTRO_FILE = "Introduct.md"          # 用户自行编辑的书目简介
BOOK_FOLDER = "book"                 # 电子教材，不参与 AI 总结
ERROR_FOLDER = "error-prone"         # 错题、易错内容，参与 AI 总结
NOTEBOOK_FOLDER = "notebook"         # 用户笔记，参与 AI 总结
HOMEWORK_FOLDER = "homework"         # 作业，**不参与 AI 总结**（需求明确要求）
#: 其它文件：放不进取材/笔记/易错题/作业的资料（课件、扫描件、图片…）。
#: **不参与 AI 总结**；用户可以在这里自由新建文件夹分门别类。
OTHERS_FOLDER = "others"
#: 单词书目录名。
#:
#: **所有科目、所有书目共用同一个单词书**（需求原话："所有科目公用一个文件夹"）。
#: 它位于 ``<data_root>/user data/wordbook/``，**不在任何科目/书目下面** ——
#: 因为"生词本"是跨教材累积的东西：在「英语1 视听说」里记的 `abandon`，
#: 打开「英语2 阅读」时也要能看到。
#:
#: 历史上它曾经是**每本书一个** ``<书目>/wordbook/``，那个布局会把生词切开，
#: 所以改成全局共享；旧布局的卡片会在启动时自动迁移过来
#: （见 :func:`gwp.data_manager.wordbook.migrate_legacy_wordbooks`）。
WORDBOOK_DIR = "wordbook"
#: 旧布局的目录名（每本书一个）。保留它只为了**迁移与识别旧数据** ——
#: 新代码不应该再往书目下面建这个目录。
WORDBOOK_LEGACY_FOLDER = "wordbook"
SUBJECT_META = "subject.json"        # 科目元数据（名称、图片、颜色）
BOOK_META = "book.json"              # 书目元数据
#: 作业信息文件名。作业是 `homework/<作业名>/` 子文件夹，
#: 这个文件记录 DDL 与提交方式，放在子文件夹里。
HOMEWORK_META = "homework.json"
#: 单词卡信息文件名。一张卡是 `wordbook/<英文>.json`（**一个文件一张卡**）。
#: 一个文件一张卡是有意的：方便单独手工改、单独拷给同学、也能直接进版本管理。
WORD_CARD_SUFFIX = ".json"
SUMMARY_SUFFIX = "_summary.md"       # 旧的 Markdown 总结（保留用于读旧数据）
#: 「AI 总结」现在的产物：**一个合并出来的 PDF**。
#:
#: 需求："AI总结实现方法：将所有待总结文件转化并合并为一个pdf文档，
#: 结束后删除中间可能产生的废弃文档和数据"。
#: 所以新的总结是 ``<书名>_summary.pdf``；旧的 ``_summary.md``
#: 只在读取历史数据时认得（见 store.find_summary），生成时不再产生。
SUMMARY_PDF_SUFFIX = "_summary.pdf"

# --------------------------------------------------------------------------
# 科目类型（需求：Subject 分为 日记 / 校修课 / 自学课）
# --------------------------------------------------------------------------

#: 自学课：用户自己找资料学的课（原有的默认类型）
SUBJECT_SELF_STUDY = "self-study"
#: 校修课：学校开设、跟着老师上的课
SUBJECT_SCHOOL = "school"
#: 日记：按天记录，AI 负责归纳思想与合并整理
SUBJECT_DIARY = "diary"

#: 全部类型（顺序即新建对话框里的显示顺序）
SUBJECT_TYPES = (SUBJECT_DIARY, SUBJECT_SCHOOL, SUBJECT_SELF_STUDY)

#: 类型的显示名与说明
SUBJECT_TYPE_LABELS = {
    SUBJECT_DIARY: ("日记", "按天记录的文字；AI 归纳思想并合并整理成册"),
    SUBJECT_SCHOOL: ("校修课", "学校开设的课程；含教材、易错题、作业"),
    SUBJECT_SELF_STUDY: ("自学课", "自己找资料学习的课程；含教材、易错题、练习"),
}

#: 默认类型（不写 type 的旧数据都按这个处理，保证向后兼容）
DEFAULT_SUBJECT_TYPE = SUBJECT_SELF_STUDY

# --------------------------------------------------------------------------
# 日记类型专用的目录与文件
# --------------------------------------------------------------------------

#: 日记科目的文件夹名（位于 Book 目录下）
DIARY_AI_SUMMARY_FOLDER = "AI summary"   # AI「思想总结」的产出目录
DIARY_AI_DIARY_FOLDER = "AI diary"       # AI「文档合并 + 格式统一」的产出目录
DIARY_MINE_FOLDER = "my diary"           # 用户自己写的日记
DIARY_OTHERS_FOLDER = "else diary"       # 其它来源的日记

#: 日记类型 Book 的标准目录
DIARY_TEMPLATE_DIRS = (
    DIARY_AI_SUMMARY_FOLDER,
    DIARY_AI_DIARY_FOLDER,
    DIARY_MINE_FOLDER,
    DIARY_OTHERS_FOLDER,
)

#: 日记类型参与 AI 处理的目录（没有教材、没有易错题）
DIARY_SOURCE_DIRS = (DIARY_MINE_FOLDER, DIARY_OTHERS_FOLDER)

#: 日记科目下自动创建的默认 Book 名称
DIARY_DEFAULT_BOOK = "MyBook"

#: 日记条目文件的默认内容模板（手写图里的 "年x月x日 / 天气：" 格式）
DIARY_ENTRY_TEMPLATE = "# {date}\n\n天气：\n\n"

#: Book 创建时自动生成的完整结构。
#: **不含单词书** —— 单词书是所有科目共用的一个目录（见 ``WORDBOOK_DIR``），
#: 不在书目下面，所以不该出现在这里。
BOOK_TEMPLATE_DIRS = (
    BOOK_FOLDER,
    ERROR_FOLDER,
    NOTEBOOK_FOLDER,
    HOMEWORK_FOLDER,
    OTHERS_FOLDER,
)
BOOK_TEMPLATE_FILES = (INTRO_FILE,)

#: 参与 AI 总结的内容目录。
#: 注意 ``HOMEWORK_FOLDER``（练习/作业）、``BOOK_FOLDER``（教材）与
#: ``OTHERS_FOLDER``（其它文件）都**不在**这里 —— 它们不参与 AI 总结。
SUMMARY_SOURCE_DIRS = (ERROR_FOLDER, NOTEBOOK_FOLDER)


# --------------------------------------------------------------------------
# 各类型对应的 Book 结构（界面标签 / 目录 / 是否参与 AI 处理）
# --------------------------------------------------------------------------

#: 每个标签的含义：(key, 标签文案, 目录名)
#: * 自学课：作业 -> 练习（需求：自学课的作业改为练习，功能性质不变）
#: * 校修课：保持"作业"
#: * 日记：没有教材与易错题，改为 AI 总结 / AI 日记 / 我的日记 / 其它日记
#: * **所有类型都带「单词书」** —— 它是独立的一种浏览方式（折叠卡片 +
#:   单击展开），而且内容来自**全局共用的**单词书目录，
#:   所以第三个字段是 ``None``（这个标签**没有**属于自己的书目内目录）。
WORDBOOK_TAB = ("wordbook", "单词书", None)

BOOK_TABS_SELF_STUDY = (
    ("summary", "AI 总结", None),
    ("intro", "简介", None),
    ("notebook", "笔记", NOTEBOOK_FOLDER),
    ("homework", "练习", HOMEWORK_FOLDER),
    ("error-prone", "易错题", ERROR_FOLDER),
    ("book", "教材", BOOK_FOLDER),
    ("others", "其它文件", OTHERS_FOLDER),
    WORDBOOK_TAB,
    ("root", "全部条目", None),
)

BOOK_TABS_SCHOOL = (
    ("summary", "AI 总结", None),
    ("intro", "简介", None),
    ("notebook", "笔记", NOTEBOOK_FOLDER),
    ("homework", "作业", HOMEWORK_FOLDER),
    ("error-prone", "易错题", ERROR_FOLDER),
    ("book", "教材", BOOK_FOLDER),
    ("others", "其它文件", OTHERS_FOLDER),
    WORDBOOK_TAB,
    ("root", "全部条目", None),
)

#: 日记类型：没有「AI 总结」与「简介」——日记不写学习目标，输出都在自己的目录里。
BOOK_TABS_DIARY = (
    ("diary-ai-summary", "AI 思想总结", DIARY_AI_SUMMARY_FOLDER),
    ("diary-ai", "AI 日记", DIARY_AI_DIARY_FOLDER),
    ("diary-mine", "我的日记", DIARY_MINE_FOLDER),
    ("diary-others", "其它日记", DIARY_OTHERS_FOLDER),
    WORDBOOK_TAB,
    ("root", "全部条目", None),
)

#: 类型 -> 标签定义
BOOK_TABS_BY_TYPE = {
    SUBJECT_SELF_STUDY: BOOK_TABS_SELF_STUDY,
    SUBJECT_SCHOOL: BOOK_TABS_SCHOOL,
    SUBJECT_DIARY: BOOK_TABS_DIARY,
}


def tabs_for_type(subject_type: str) -> tuple:
    """按科目类型取 Book 页的标签定义。未知类型按自学课处理。"""
    return BOOK_TABS_BY_TYPE.get(subject_type or DEFAULT_SUBJECT_TYPE, BOOK_TABS_SELF_STUDY)


def template_dirs_for_type(subject_type: str) -> tuple[str, ...]:
    """按科目类型取 Book 的标准目录。"""
    if (subject_type or "") == SUBJECT_DIARY:
        return DIARY_TEMPLATE_DIRS
    return BOOK_TEMPLATE_DIRS


def summary_sources_for_type(subject_type: str) -> tuple[str, ...]:
    """按科目类型取"参与 AI 处理"的目录。"""
    if (subject_type or "") == SUBJECT_DIARY:
        return DIARY_SOURCE_DIRS
    return SUMMARY_SOURCE_DIRS


def type_label(subject_type: str) -> str:
    """类型的中文名。"""
    label, _description = SUBJECT_TYPE_LABELS.get(
        subject_type or DEFAULT_SUBJECT_TYPE, SUBJECT_TYPE_LABELS[DEFAULT_SUBJECT_TYPE]
    )
    return label

# --------------------------------------------------------------------------
# 目录名（位于数据根目录之下，均可在 config.json 中改名）
# --------------------------------------------------------------------------

DEFAULT_USER_DATA_DIR = "user data"
DEFAULT_ELSE_DATA_DIR = "else data"
DEFAULT_SUBJECTS_DIR = "subjects"
DEFAULT_BACKUP_DIR = "summary_backup"
DEFAULT_ASSETS_DIR = "assets"
DEFAULT_CHAT_DIR = "chats"
DEFAULT_LOG_DIR = "logs"

# --------------------------------------------------------------------------
# 文件类型
# --------------------------------------------------------------------------

TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
#: 可以在软件内部用**纯文本查看器**打开的类型（JSON 等配置文件/源码）。
#: 其中 JSON 优先用 VSCode 打开（见 book_view.open_file），
#: 找不到 VSCode 时退回内置查看器。
CODE_EXTENSIONS = {
    ".json", ".jsonc", ".json5", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".xml", ".csv", ".tsv", ".log", ".py", ".js", ".ts", ".css", ".html",
    ".bat", ".ps1", ".sh", ".c", ".h", ".cpp", ".java", ".sql",
}
#: 内置查看器能打开的全部类型
VIEWABLE_EXTENSIONS = TEXT_EXTENSIONS | CODE_EXTENSIONS
#: JSON 系（优先 VSCode）
JSON_EXTENSIONS = {".json", ".jsonc", ".json5"}
DOCX_EXTENSIONS = {".docx"}
LEGACY_DOC_EXTENSIONS = {".doc"}
PPTX_EXTENSIONS = {".pptx"}
LEGACY_PPT_EXTENSIONS = {".ppt"}
XLSX_EXTENSIONS = {".xlsx", ".xlsm"}
LEGACY_XLS_EXTENSIONS = {".xls"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}

#: 允许用户导入到书目的文件类型
IMPORTABLE_EXTENSIONS = (
    TEXT_EXTENSIONS
    | DOCX_EXTENSIONS
    | LEGACY_DOC_EXTENSIONS
    | PPTX_EXTENSIONS
    | LEGACY_PPT_EXTENSIONS
    | XLSX_EXTENSIONS
    | LEGACY_XLS_EXTENSIONS
    | PDF_EXTENSIONS
    | IMAGE_EXTENSIONS
)

#: 可作为科目卡片图片的扩展名（需求文档：jpg / png）
COVER_EXTENSIONS = {".jpg", ".jpeg", ".png"}

#: 明确“不支持解析，只能作为图片插入或跳过”的旧格式
UNSUPPORTED_BINARY_EXTENSIONS = LEGACY_DOC_EXTENSIONS | LEGACY_PPT_EXTENSIONS | LEGACY_XLS_EXTENSIONS

# --------------------------------------------------------------------------
# 科目卡片默认配色（用户可改；新增科目按顺序取色，可循环）
# --------------------------------------------------------------------------

DEFAULT_CARD_COLORS = (
    "#4F7CFF",
    "#00A6A6",
    "#F2814B",
    "#8E63CE",
    "#D9536F",
    "#3E9E5F",
    "#C99A2E",
    "#2F7FA8",
    "#B05AA8",
    "#6E7B8B",
)

# --------------------------------------------------------------------------
# 默认提示词（可在 config.json 的 prompts 段整段替换）
# --------------------------------------------------------------------------

#: AI 助手的自称（需求：软件里的所有 AI 助手都自称「长庚」，不要叫「大白星球」）。
#:
#: 为什么不直接写进每段提示词里：
#: * 「长庚」是**人设名**，将来要改只改这一处；
#: * 提示词本身是「能力描述」，两者分开更好维护；
#: * 测试可以断言"每段提示词都带上了这个名字"。
AI_ASSISTANT_NAME = "长庚"

#: 默认提示词的**版本号**。每次改动下面这些默认提示词就 +1。
#:
#: 为什么需要它：配置是"深合并"的 —— 用户 config.json 里已经落盘的 prompts
#: **不会被新的默认值覆盖**（这是好事，用户手改过的提示词要保住）。
#: 但代价是改了默认提示词对老用户不生效。所以用版本号区分：
#: "你这份 prompts 是我第几版写的"，落后了就整段换成新默认值。
PROMPT_REVISION = 2

SUMMARY_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件的学习助手，现在担任「学习资料整合专家」。

你的任务不是做简单概括，而是把用户提供的多份零散资料**整合并扩展**成一份完整、自洽、可直接用来复习的学习文档（Markdown 格式）。

硬性要求：
1. 输出必须是**纯 Markdown**，不要包裹 ```markdown 代码块，不要输出任何与文档无关的寒暄。
2. 以一级标题开头，标题使用书目名称。
3. 必须整合用户提供的**全部**资料：书目的简介与学习目标、笔记、易错题内容。不要遗漏任何一份材料。
4. 在整合的基础上**扩展**：补全缺失的推导、定义、定理条件、常见陷阱与辨析，让文档可以作为一条完整的学习主线使用。
5. 易错题要转化为「易错点清单」，给出：错误表现 → 根本原因 → 正确做法 → 同类变形。
6. 如果不同资料之间出现冲突或信息不足，**不要臆造**：在文档末尾的「待确认问题」小节中列出，等待用户澄清。
7. 保留用户笔记中的原始关键结论与自己的表述习惯，不要改写成无法追溯的空话。
8. 中文输出，术语可保留英文原词。公式使用 LaTeX（行内 $...$，独立 $$...$$）。
9. 用户问起你是谁时，自称「{AI_ASSISTANT_NAME}」；不要把软件名当成你的名字。
10. **你自己新增的内容必须标注**（需求："你补充的要标注（AI 补充）"）：

    * 每一处由你**新增/推导/扩展**的内容，紧跟在那一处后面写一个行内标记
      ``（AI 补充）``；
    * **引用用户原文的部分不要加这个标记**，也不要把原文改写成别的说法；
    * 如果整节都是你新增的（例如补全的推导、联系、同类变形），
      在小标题后面写 ``（AI 补充）`` 就行，不必逐句标；
    * 标记要**少而准**：只标你真正新增的东西，不要每段都标。

推荐结构（可按内容实际需要增删小节）：
# <书目名称>
## 一、学习目标与简介
## 二、知识框架总览
## 三、核心内容详解
## 四、易错点与易错题精讲
## 五、方法与解题模板
## 六、复习清单
## 七、待确认问题
"""

SUMMARY_CHUNK_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件的学习助手，现在担任「学习资料整合专家」。

用户资料很长，本轮只提供其中**一部分**。请对这一部分做「结构化提炼」：
- 保留全部知识点、定义、定理、条件、公式、结论与例题要点；
- 保留笔记中的个人理解与易错题信息，不要丢弃细节；
- 用 Markdown 小标题组织，允许比原文更紧凑，但**不允许丢失信息**；
- 不要写总结性寒暄，不要写"以上是第一部分"之类的话。
直接输出提炼后的 Markdown 内容。
"""

SUMMARY_MERGE_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件的学习助手，现在担任「学习资料整合专家」。

用户会给你同一本书的多个「分块提炼结果」。请把它们**合并并扩展**为一份完整的学习文档。

要求：
1. 输出纯 Markdown，一级标题为书目名称，不要包裹代码块，不要寒暄。
2. 先去重合并同类内容，再按知识逻辑重排，而不是按分块顺序堆叠。
3. 在整合基础上扩写：补全推导、定理条件、常见陷阱、辨析。
   **你新增的这部分要标注 ``（AI 补充）``**（整节新增就标在小标题后，
   逐句新增就标在句后）；引用分块提炼结果的原文**不要**加标记。
4. 统一术语与符号；冲突之处放入「待确认问题」小节，不要臆造。
5. 中文输出，公式用 LaTeX。
"""

# --------------------------------------------------------------------------
# 日记类型专用的两套提示词
# --------------------------------------------------------------------------

#: 一、「AI 思想总结」：读 my diary 的全部内容，归纳成思想/主题小结。
#:    要求是"提炼"而不是"复述"：可以引用原句，但不必体现全部内容。
DIARY_THOUGHT_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」，Great White Planet 学习软件的学习助手，现在担任「日记思想总结助手」。

用户会给你他本人一段时间内写的全部日记（my diary）。你的任务**不是复述日记**，
而是把这些日记里反复出现的东西提炼出来：

硬性要求：
1. 输出必须是**纯 Markdown**，不要包裹 ``` 代码块，不要寒暄。
2. **不要逐篇复述**。日记里的具体事情只在需要说明观点时引用，
   引用要短（一句话以内），并且要能看出是引自哪一天。
3. 重点归纳：
   - 反复出现的**主题**（在关心什么、在纠结什么、在推进什么）；
   - **情绪与心态的走势**（什么时候低落、什么时候好转，可能与什么有关）；
   - **想法/观念的变化**（前后看法不一致的地方，这也是最有价值的部分）；
   - **重复出现的模式**（同样的坑、同样的拖延、同样的自我要求）；
   - 只在日记里出现过一次的琐事不要写进来。
4. 该指出问题时直说，不要一味安慰；但也不做心理诊断，只描述你从文字里看到的东西。
5. 结尾给出一小节「值得继续想的问题」，3~5 条，具体、可回答，不要空话。

推荐结构（可按内容增删）：
# <日记本名称> · 思想总结
## 一、这段时间的主线
## 二、反复出现的主题
## 三、情绪与心态走势
## 四、想法的变化
## 五、重复出现的模式
## 六、值得继续想的问题
"""

#: 二、「AI 日记」：把 my diary 的全部内容**整合成一篇**格式统一的日记册。
DIARY_BOOK_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」，Great White Planet 学习软件的学习助手，现在担任「日记整理助手」。

用户会给你他本人写的全部日记（my diary，可能分散在多个文件里）。你的任务是
把它们**按时间顺序合并成一篇格式统一的日记文档**。

硬性要求：
1. 输出必须是**纯 Markdown**，不要包裹 ``` 代码块，不要寒暄，不要写"以下是整理结果"。
2. **保留日记的全部内容** —— 这件事和"写摘要"相反：不要删减事实、感受、细节，
   不要替用户改写他的语气。你只做"合并 + 统一格式 + 轻微的语句通顺"。
3. 每一天的格式严格统一为：

   ## 2026年5月1日

   天气：

   （这一天的正文，可以有多段）

   * 日期写成 `## YYYY年M月D日`（有星期就补上，例如 `## 2026年5月1日 星期五`）。
   * 原日记里的天气/地点等元信息放到「天气：」这一行；原文没写就留空，不要编造。
   * 同一天的多个片段要合并到同一个日期小节下，不要出现两个相同日期。
4. 严格按日期**从早到晚**排列。日期缺失的条目放到最前面，标题写 `## 日期不详`。
5. 原文里的错别字、口头语、情绪化表达**保持原样**，只修明显不通顺的地方。
6. 不要加自己的评论、总结或建议 —— 这份文档是用户自己的日记。

文档开头可以有一行标题：

# <日记本名称> · 合并日记

然后直接按日期小节往下排。
"""

CHAT_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件内置的 AI 学习助手。
- 用户正在阅读或编辑一份 Markdown 文档，文件内容会随对话提供给你。
- 回答要具体、可操作，中文优先，公式用 LaTeX。
- 当用户要求修改文档时，直接给出可以整段替换进 Markdown 的内容。
- 如果信息不足或存在歧义，先提问再回答，不要凭空猜测。
- 用户问起你是谁时，自称「{AI_ASSISTANT_NAME}」；不要把软件名当成你的名字。
"""

DAILY_CHAT_SYSTEM_PROMPT = f"""你是「{AI_ASSISTANT_NAME}」——Great White Planet 学习软件内置的 AI 助手，正在和用户做日常对话。

- 用户问起你是谁时，自称「{AI_ASSISTANT_NAME}」。**不要把软件的名字当成你的名字** ——
  软件名只是个壳，你的名字是「{AI_ASSISTANT_NAME}」。
- 这里不绑定任何文件：用户可能问学习问题、让你解释概念、帮你梳理思路、写点东西，
  也可能只是随便聊聊。跟着用户的话题走，不要强行把对话拉回学习管理。
- 中文优先；回答简洁清楚，需要展开时用小标题或列表，公式用 LaTeX（行内 $...$）。
- 用户提到"那本书/我的笔记/上个总结"时，不要假装读过：说明你没有访问权限，
  并告诉他可以打开对应文档后用文档视图里的「AI 双栏」来谈内容。
- 信息不足或存在歧义时先问一句，不要凭空编造事实、数据或引用。
- 需要给可复制的代码时用围栏代码块并标注语言。
"""

DEFAULT_UNCERTAINTY_RULES = (
    "当你对以下情况不确定时，必须先向用户提问，不要直接猜测：",
    "1. 资料中出现无法辨认的文字、图片或公式；",
    "2. 同一知识点在不同资料中说法冲突；",
    "3. 需要知道用户的课程进度、考试范围或偏好才能决定详略；",
    "4. 需要确认某个符号/缩写在本课程中的约定含义。",
    "提问方式：每次只问一个问题，输出一个 JSON 对象，不要有其他文字：",
    '{"question": "你的问题", "options": ["可选项1", "可选项2"], "allow_custom": true}',
    "收到用户回答后再继续完成任务。如果确实无需提问，直接给出正常回答。",
)
