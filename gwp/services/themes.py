"""界面与导出用到的样式（CSS）。

集中放在这里，改观感不用碰逻辑代码。需求文档要求"界面尽量美观"，
因此这里定义了两套主题（light / dark）以及打印用样式。
"""

from __future__ import annotations

#: 主色调（浅色主题）
LIGHT = {
    "app_bg": "#F4F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F9FC",
    "border": "#DFE5F0",
    "text": "#1F2733",
    "text_muted": "#6B7787",
    "accent": "#4F7CFF",
    "accent_soft": "#E8EFFF",
    "code_bg": "#F5F7FA",
    "quote_bg": "#F8FAFF",
    "quote_border": "#9FB8FF",
    "table_header": "#EEF3FF",
    "danger": "#D9534F",
    "success": "#3E9E5F",
}

#: 深色主题
DARK = {
    "app_bg": "#171B22",
    "surface": "#1F242D",
    "surface_alt": "#252B35",
    "border": "#323A47",
    "text": "#E6EAF0",
    "text_muted": "#9BA6B5",
    "accent": "#6E96FF",
    "accent_soft": "#26304A",
    "code_bg": "#141920",
    "quote_bg": "#1B212B",
    "quote_border": "#4C63A8",
    "table_header": "#242C3A",
    "danger": "#E06C75",
    "success": "#6FBF8B",
}


def palette(theme: str = "light") -> dict[str, str]:
    return DARK if str(theme).lower() == "dark" else LIGHT


# --------------------------------------------------------------------------
# Markdown 正文样式
# --------------------------------------------------------------------------

def markdown_css(theme: str = "light", for_pdf: bool = False) -> str:
    """Markdown 正文的 CSS。for_pdf=True 时去掉界面专用的滚动/阴影。"""
    colors = palette(theme)
    base_font = (
        "-apple-system, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif"
        if for_pdf
        else "'Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', sans-serif"
    )
    code_font = "Consolas, 'Cascadia Mono', 'Courier New', monospace"
    size = "11pt" if for_pdf else "10.5pt"
    line = "1.75" if for_pdf else "1.7"

    return f"""
.gwp-doc {{
  font-family: {base_font};
  font-size: {size};
  line-height: {line};
  color: {colors['text']};
  background: transparent;
  word-wrap: break-word;
}}
.gwp-doc h1, .gwp-doc h2, .gwp-doc h3, .gwp-doc h4, .gwp-doc h5, .gwp-doc h6 {{
  font-weight: 600;
  line-height: 1.35;
  margin: 1.2em 0 0.6em;
  color: {colors['text']};
}}
.gwp-doc h1 {{ font-size: 1.9em; border-bottom: 2px solid {colors['border']}; padding-bottom: 0.3em; }}
.gwp-doc h2 {{ font-size: 1.5em; border-bottom: 1px solid {colors['border']}; padding-bottom: 0.25em; }}
.gwp-doc h3 {{ font-size: 1.25em; color: {colors['accent']}; }}
.gwp-doc h4 {{ font-size: 1.1em; }}
.gwp-doc p {{ margin: 0.6em 0; }}
.gwp-doc a {{ color: {colors['accent']}; text-decoration: none; }}
.gwp-doc strong {{ font-weight: 600; }}
.gwp-doc ul, .gwp-doc ol {{ margin: 0.5em 0 0.5em 1.4em; }}
.gwp-doc li {{ margin: 0.25em 0; }}
.gwp-doc blockquote {{
  margin: 0.8em 0;
  padding: 0.5em 0.9em;
  color: {colors['text_muted']};
  background: {colors['quote_bg']};
  border-left: 4px solid {colors['quote_border']};
  border-radius: 4px;
}}
.gwp-doc code {{
  font-family: {code_font};
  font-size: 0.92em;
  background: {colors['code_bg']};
  padding: 0.12em 0.35em;
  border-radius: 4px;
}}
.gwp-doc pre {{
  background: {colors['code_bg']};
  border: 1px solid {colors['border']};
  border-radius: 8px;
  padding: 0.8em 1em;
  margin: 0.8em 0;
  overflow-x: auto;
  {'white-space: pre-wrap;' if for_pdf else ''}
}}
.gwp-doc pre code {{
  background: transparent;
  padding: 0;
  font-size: 0.9em;
  line-height: 1.55;
}}
.gwp-doc table {{
  border-collapse: collapse;
  margin: 0.9em 0;
  width: 100%;
  font-size: 0.95em;
}}
.gwp-doc th, .gwp-doc td {{
  border: 1px solid {colors['border']};
  padding: 0.42em 0.6em;
  text-align: left;
  vertical-align: top;
}}
.gwp-doc th {{ background: {colors['table_header']}; font-weight: 600; }}
.gwp-doc img {{ max-width: 100%; height: auto; border-radius: 6px; margin: 0.5em 0; }}
/* 连续图片成组（由 markdown_renderer._group_image_runs 生成）。
   需求："图片之间不要有间隙，图片结尾与下面的文字不要有间隙"。
   组内图片的上下外边距一律归零；组自身只在**底部**留一个很小的间距 ——
   完全贴死会让最后一张图读到下一段时挤在一起。 */
.gwp-doc .gwp-figure {{
  margin: 0;
  padding: 0;
  line-height: 0;          /* 去掉行盒带来的额外行高缝隙 */
  font-size: 0;            /* 同理：图片是行内元素，会被字体行高撑开 */
}}
.gwp-doc .gwp-figure img {{
  display: block;
  margin: 0;
  padding: 0;
  border-radius: 0;
  width: 100%;
}}
.gwp-doc .gwp-figure:last-child {{ margin-bottom: 0.35em; }}
/* 组后面接标题/段落时，给一点点呼吸空间 */
.gwp-doc .gwp-figure + p,
.gwp-doc .gwp-figure + h1,
.gwp-doc .gwp-figure + h2,
.gwp-doc .gwp-figure + h3 {{ margin-top: 0.35em; }}
/* 行内公式（LaTeX 渲染出来的高分辨率图片）：
   图是按 15 号字 + scale=3 渲染的（约 84×57 像素），1:1 显示会比正文大好几倍，
   所以这里用 em 把它**缩回"和文字一样高"** —— 既清晰又不撑开行距。
   独立公式稍微大一点，并且单独成段居中。 */
.gwp-doc img.gwp-eq {{
  height: 1.05em;
  width: auto;
  margin: 0 1px;
  vertical-align: -0.22em;
  border-radius: 0;
}}
.gwp-doc p > img.gwp-eq:only-child {{
  display: block;
  height: 1.5em;
  margin: 0.6em auto;
}}
/* 表格单元格里空间紧张，公式要更小一点，否则会把行高撑开、列宽挤歪 */
.gwp-doc td img.gwp-eq,
.gwp-doc th img.gwp-eq {{
  height: 0.92em;
  vertical-align: -0.18em;
}}
/* 标题里的公式跟着标题字号 */
.gwp-doc h1 img.gwp-eq,
.gwp-doc h2 img.gwp-eq,
.gwp-doc h3 img.gwp-eq {{ height: 0.95em; vertical-align: -0.2em; }}
.gwp-doc hr {{ border: none; border-top: 1px solid {colors['border']}; margin: 1.4em 0; }}
.gwp-doc .footnote {{ font-size: 0.9em; color: {colors['text_muted']}; }}
""" + _pygments_css(theme)


def _pygments_css(theme: str = "light") -> str:
    """Pygments 代码高亮配色，与主题保持一致。"""
    if str(theme).lower() == "dark":
        return """
.highlight .k, .highlight .kd, .highlight .kn { color: #C792EA; }
.highlight .s, .highlight .s1, .highlight .s2 { color: #C3E88D; }
.highlight .c, .highlight .c1, .highlight .cm { color: #6A7A8C; font-style: italic; }
.highlight .n, .highlight .nf { color: #82AAFF; }
.highlight .m, .highlight .mi, .highlight .mf { color: #F78C6C; }
.highlight .o, .highlight .ow { color: #89DDFF; }
.highlight .nc, .highlight .nn { color: #FFCB6B; }
"""
    return """
.highlight .k, .highlight .kd, .highlight .kn { color: #A626A4; }
.highlight .s, .highlight .s1, .highlight .s2 { color: #50A14F; }
.highlight .c, .highlight .c1, .highlight .cm { color: #8A94A6; font-style: italic; }
.highlight .n, .highlight .nf { color: #4078F2; }
.highlight .m, .highlight .mi, .highlight .mf { color: #986801; }
.highlight .o, .highlight .ow { color: #0184BC; }
.highlight .nc, .highlight .nn { color: #C18401; }
"""


# --------------------------------------------------------------------------
# 应用整体样式（QSS）
# --------------------------------------------------------------------------

def app_qss(theme: str = "light", accent: str = "", font_family: str = "", font_size: int = 10) -> str:
    """整个软件的 Qt 样式表。改观感只改这里。"""
    colors = dict(palette(theme))
    if accent:
        colors["accent"] = accent
        colors["accent_soft"] = _mix(accent, colors["surface"], 0.86)
    family = font_family or "'Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', sans-serif"

    return f"""
QWidget {{
  font-family: {family};
  font-size: {max(8, int(font_size))}pt;
  color: {colors['text']};
}}
QMainWindow, QDialog {{ background: {colors['app_bg']}; }}

QMenuBar {{ background: {colors['surface']}; border-bottom: 1px solid {colors['border']}; padding: 2px 6px; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {colors['accent_soft']}; color: {colors['accent']}; }}
QMenu {{ background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {colors['accent_soft']}; color: {colors['accent']}; }}
QMenu::separator {{ height: 1px; background: {colors['border']}; margin: 6px 8px; }}

QToolBar {{ background: {colors['surface']}; border-bottom: 1px solid {colors['border']}; spacing: 6px; padding: 6px 8px; }}
QToolButton {{ padding: 6px 10px; border-radius: 8px; background: transparent; }}
QToolButton:hover {{ background: {colors['accent_soft']}; }}
QToolButton:pressed {{ background: {colors['border']}; }}
QToolButton:checked {{ background: {colors['accent_soft']}; color: {colors['accent']}; }}

/* 菜单栏右上角的 AI 入口（见 MainWindow._build_menu_corner） */
QWidget#MenuCorner {{ background: transparent; }}
QPushButton#CornerPrimary {{
  background: {colors['accent_soft']};
  color: {colors['accent']};
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 4px 12px;
  font-weight: 600;
}}
QPushButton#CornerPrimary:hover {{
  background: {colors['accent']};
  color: #FFFFFF;
  border-color: {colors['accent']};
}}
QPushButton#CornerPrimary:pressed {{ background: {colors['accent']}; color: #FFFFFF; }}
QToolButton#CornerDrop {{
  padding: 4px 6px;
  border-radius: 8px;
  color: {colors['accent']};
  font-weight: 600;
}}
QToolButton#CornerDrop:hover {{ background: {colors['accent_soft']}; }}
QToolButton#CornerDrop::menu-indicator {{ image: none; width: 0; }}

QStatusBar {{ background: {colors['surface']}; border-top: 1px solid {colors['border']}; color: {colors['text_muted']}; }}

/* 书目页的剪贴板操作条 */
QWidget#ClipboardBar {{ background: transparent; }}
QWidget#ClipboardBar QPushButton {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 7px;
  padding: 4px 12px;
}}
QWidget#ClipboardBar QPushButton:hover:enabled {{
  border-color: {colors['accent']};
  color: {colors['accent']};
}}

/* 资料概览的折叠按钮 */
QToolButton#CollapseToggle {{
  color: {colors['accent']};
  font-weight: 700;
  padding: 0 6px;
  border-radius: 6px;
}}
QToolButton#CollapseToggle:hover {{ background: {colors['accent_soft']}; }}

QPushButton {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 8px;
  padding: 6px 14px;
  min-height: 18px;
}}
QPushButton:hover {{ border-color: {colors['accent']}; color: {colors['accent']}; }}
QPushButton:pressed {{ background: {colors['accent_soft']}; }}
QPushButton:disabled {{ color: {colors['text_muted']}; border-color: {colors['border']}; background: {colors['surface_alt']}; }}

/* 勾选态（例如书目页的「资料概览」开关）：明显一点，表示面板已展开 */
QPushButton:checked {{
  background: {colors['accent_soft']};
  border-color: {colors['accent']};
  color: {colors['accent']};
  font-weight: 600;
}}
QPushButton:checked:hover {{
  background: {colors['accent']};
  border-color: {colors['accent']};
  color: #FFFFFF;
}}
QPushButton[accent="true"] {{
  background: {colors['accent']};
  border-color: {colors['accent']};
  color: #FFFFFF;
  font-weight: 600;
}}
QPushButton[accent="true"]:hover {{ background: {colors['accent']}; color: #FFFFFF; opacity: 0.9; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
QDateTimeEdit, QDateEdit, QTimeEdit {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 8px;
  padding: 6px 8px;
  selection-background-color: {colors['accent']};
  selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QComboBox:focus, QDateTimeEdit:focus, QDateEdit:focus, QTimeEdit:focus {{
  border-color: {colors['accent']};
}}

/* ---------------- 日期 / 时间输入 ----------------
   需求："数字看不清 修改  后面几点几分也弄成这种选择/滚轮，而非手动填写"

   原来 QDateTimeEdit 完全没被样式覆盖（用的是 Qt 默认外观），
   而且上下调节按钮很小、日期时间混在一起。这里：
   * 把 QDateTimeEdit 加进上面那组输入框样式，外观统一；
   * 把调节按钮**加宽**（26px）并给足对比度，点起来容易；
   * 日历弹窗加大字号与格子上限，数字看得清。 */
QDateTimeEdit::up-button, QDateTimeEdit::down-button,
QDateEdit::up-button, QDateEdit::down-button,
QTimeEdit::up-button, QTimeEdit::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
  subcontrol-origin: border;
  width: 26px;
  background: {colors['surface_alt']};
  border-left: 1px solid {colors['border']};
}}
QDateTimeEdit::up-button, QDateEdit::up-button, QTimeEdit::up-button,
QSpinBox::up-button {{
  subcontrol-position: top right;
  border-top-right-radius: 7px;
  border-bottom: 1px solid {colors['border']};
}}
QDateTimeEdit::down-button, QDateEdit::down-button, QTimeEdit::down-button,
QSpinBox::down-button {{
  subcontrol-position: bottom right;
  border-bottom-right-radius: 7px;
}}
QDateTimeEdit::up-arrow, QDateEdit::up-arrow, QTimeEdit::up-arrow,
QSpinBox::up-arrow {{
  image: none;
  width: 0; height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-bottom: 5px solid {colors['text_muted']};
}}
QDateTimeEdit::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow,
QSpinBox::down-arrow {{
  image: none;
  width: 0; height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid {colors['text_muted']};
}}
QDateTimeEdit::drop-down {{
  subcontrol-origin: padding;
  subcontrol-position: center right;
  width: 26px;
  border-left: 1px solid {colors['border']};
  border-top-right-radius: 7px;
  border-bottom-right-radius: 7px;
  background: {colors['surface_alt']};
}}
/* 月历弹窗：字号加大、格子留白，数字才看得清 */
QCalendarWidget QWidget {{ alternate-background-color: {colors['surface']}; }}
QCalendarWidget QAbstractItemView:enabled {{
  font-size: 1.08em;
  color: {colors['text']};
  background: {colors['surface']};
  selection-background-color: {colors['accent']};
  selection-color: #FFFFFF;
  outline: none;
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {colors['text_muted']}; }}
QCalendarWidget QToolButton {{
  font-size: 1.06em;
  font-weight: 600;
  color: {colors['text']};
  background: transparent;
  padding: 4px 8px;
}}
QCalendarWidget QToolButton:hover {{ background: {colors['accent_soft']}; border-radius: 6px; }}
QCalendarWidget QMenu {{ background: {colors['surface']}; color: {colors['text']}; }}
QCalendarWidget QSpinBox {{ font-size: 1.06em; }}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  selection-background-color: {colors['accent_soft']};
  selection-color: {colors['accent']};
  outline: none;
}}

QListWidget, QTreeWidget, QTableWidget, QListView, QTreeView {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 10px;
  outline: none;
  padding: 4px;
}}
QListWidget::item, QTreeWidget::item {{ padding: 6px 8px; border-radius: 8px; }}
QListWidget::item:selected, QTreeWidget::item:selected {{
  background: {colors['accent_soft']};
  color: {colors['accent']};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{ background: {colors['surface_alt']}; }}
QHeaderView::section {{
  background: {colors['surface_alt']};
  border: none;
  border-bottom: 1px solid {colors['border']};
  padding: 6px 8px;
  font-weight: 600;
}}

QTabWidget::pane {{ border: 1px solid {colors['border']}; border-radius: 10px; background: {colors['surface']}; }}
QTabBar::tab {{
  background: transparent;
  padding: 7px 16px;
  margin-right: 4px;
  border-radius: 8px;
  color: {colors['text_muted']};
}}
QTabBar::tab:selected {{ background: {colors['accent_soft']}; color: {colors['accent']}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {colors['accent']}; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {colors['text_muted']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {colors['border']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: {colors['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

QGroupBox {{
  border: 1px solid {colors['border']};
  border-radius: 10px;
  margin-top: 14px;
  padding: 12px 10px 10px;
  background: {colors['surface']};
}}
QGroupBox::title {{
  subcontrol-origin: margin;
  left: 12px;
  padding: 0 6px;
  color: {colors['accent']};
  font-weight: 600;
}}

QProgressBar {{
  background: {colors['surface_alt']};
  border: 1px solid {colors['border']};
  border-radius: 7px;
  text-align: center;
  height: 14px;
}}
QProgressBar::chunk {{ background: {colors['accent']}; border-radius: 6px; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QToolTip {{
  background: {colors['text']};
  color: {colors['surface']};
  border: none;
  padding: 5px 8px;
  border-radius: 6px;
}}

/* 自定义控件 */
QFrame#Card {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 14px;
}}
QFrame#Card:hover {{ border-color: {colors['accent']}; }}
QFrame#Panel {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 12px;
}}
QLabel#Title {{ font-size: 1.35em; font-weight: 600; }}
QLabel#Subtitle {{ color: {colors['text_muted']}; }}
QLabel#SectionTitle {{ font-size: 1.05em; font-weight: 600; color: {colors['accent']}; }}
QLabel#Muted {{ color: {colors['text_muted']}; }}
QLabel#CardTitle {{ font-size: 1.02em; font-weight: 600; }}
QLabel#CardCaption {{ color: {colors['text_muted']}; font-size: 0.88em; }}
QLabel#EmptyHint {{ color: {colors['text_muted']}; font-size: 1.05em; }}
/* 首页右侧日程栏的条目：与卡片同样的圆角底，逾期/临期用左边框强调 */
QFrame#AgendaRow {{
  background: {colors['surface_alt']};
  border: 1px solid {colors['border']};
  border-left: 3px solid {colors['border']};
  border-radius: 8px;
}}
QFrame#AgendaRow[entryState="overdue"] {{ border-left-color: #B3261E; }}
QFrame#AgendaRow[entryState="soon"] {{ border-left-color: #E0A100; }}
QFrame#AgendaRow[entryState="done"] {{ border-left-color: #3FA65C; }}
QLabel#AgendaTitle {{ font-weight: 600; }}
/* 首页右上角的日期/时间/天气条 */
QFrame#ClockBar {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 12px;
}}
QLabel#ClockDate {{ font-size: 1.02em; font-weight: 600; }}
QLabel#ClockTime {{ font-size: 1.12em; font-weight: 600; color: {colors['accent']}; }}
QLabel#ClockWeather {{ font-weight: 600; }}
/* 单词卡（单词书栏目）：折叠时只显示英文，展开后显示释义/例句等。
   [expanded="true"] 由控件在切换时设置（并 unpolish/polish 重新套样式）。 */
QFrame#WordCard {{
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 8px;
}}
QFrame#WordCard[expanded="true"] {{
  background: {colors['surface_alt']};
  border-left: 3px solid {colors['accent']};
}}
/* 折叠时这一行就是全部内容，所以字号给足、加粗，扫一眼就能认词 */
QLabel#WordEnglish {{ font-size: 1.06em; font-weight: 600; }}
QLabel#WordSectionLabel {{
  color: {colors['text_muted']};
  font-size: 0.86em;
  font-weight: 600;
}}
QLabel#WordSectionBody {{ color: {colors['text']}; font-size: 0.96em; }}
QToolButton#WordCardMore {{
  border: none;
  background: transparent;
  color: {colors['text_muted']};
  font-size: 1.0em;
  padding: 2px 6px;
}}
QToolButton#WordCardMore:hover {{ color: {colors['accent']}; }}
/* 日程栏的折叠控制。
   折叠后是一条**贴住窗口右缘的竖向页签**：顶部展开箭头、中间竖排「日程」、
   底部未完成数量。所以样式上要让它像"页签"而不是一块空白面板：
   左侧不留圆角（贴着内容区），右侧圆角；底色比面板略深一点，有边界感。 */
QFrame#ScheduleFoldBar {{
  background: {colors['surface_alt']};
  border: 1px solid {colors['border']};
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
  border-top-right-radius: 0px;
  border-bottom-right-radius: 0px;
}}
QToolButton#ScheduleFold, QToolButton#ScheduleUnfold {{
  border: none;
  background: transparent;
  color: {colors['text_muted']};
  font-size: 1.15em;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 6px;
}}
QToolButton#ScheduleFold:hover, QToolButton#ScheduleUnfold:hover {{
  color: {colors['accent']};
  background: {colors['surface']};
}}
/* 竖排的「日程」：字距拉开来显得是刻意的排版，而不是被挤成两行 */
QLabel#ScheduleFoldCaption {{
  color: {colors['text_muted']};
  font-size: 0.86em;
  font-weight: 600;
  letter-spacing: 1px;
}}
/* 未完成数量做成一个小圆角徽标 */
QLabel#ScheduleFoldCount {{
  color: {colors['accent']};
  background: {colors['surface']};
  border: 1px solid {colors['border']};
  border-radius: 8px;
  font-size: 0.8em;
  font-weight: 600;
  padding: 1px 4px;
}}
"""


def _mix(color_a: str, color_b: str, ratio: float) -> str:
    """把 color_a 以 ratio 的比例混到 color_b 上（用于生成浅色强调背景）。"""
    def _parse(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        try:
            return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        except (ValueError, IndexError):
            return 79, 124, 255

    a = _parse(color_a)
    b = _parse(color_b)
    mixed = tuple(int(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def severity_color(level: str, theme: str = "light") -> str:
    colors = palette(theme)
    return {
        "error": colors["danger"],
        "danger": colors["danger"],
        "warning": "#C99A2E",
        "success": colors["success"],
        "info": colors["accent"],
    }.get(level, colors["text"])


__all__ = ["DARK", "LIGHT", "app_qss", "markdown_css", "palette", "severity_color"]
