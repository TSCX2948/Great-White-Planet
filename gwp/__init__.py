"""Great White Planet - 本地知识管理与 AI 辅助学习软件.

模块划分（全部可替换、可扩展，不在代码中写死任何科目/书目名称）:

    gwp.core         基础层：常量、路径解析、配置、日志、事件总线
    gwp.data_manager 数据层：Subject / Book 的扫描与增删改、Summary 备份
    gwp.ai           AI 层：可插拔的 Provider 适配器（自动发现）
    gwp.services     服务层：文件导入、文档文本提取、Markdown 渲染、PDF 导出、平台集成
    gwp.ui           界面层：PyQt6 视图与控件
"""

__all__ = ["__version__", "__app_name__", "__app_name_cn__"]

__app_name__ = "Great White Planet"
#: 软件的中文名。**Great White Planet = 太白金星**（金星）。
#: 金星在中国古称「启明」（晨见东方）与「长庚」（昏见西方）——
#: 软件里的 AI 助手叫「长庚」，就是从这里来的（见设计思想第四节）。
#:
#: 早期文档里写的是「大白星球」，那是把 Great White 直译错了；
#: v2.1 起统一为「太白金星」。书稿里的历史叙述仍保留旧称。
__app_name_cn__ = "太白金星"
__version__ = "2.1.0"
